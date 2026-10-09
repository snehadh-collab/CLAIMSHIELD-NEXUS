"""In-memory claim store, loaded from the CSV dataset, plus investigator state from SQLite.

One place owns: the claims, per-claim rule and ML results, graph centrality, and the derived queue.
Everything else (routers, insight builders) reads from here, so the queue, forecast, copilot context,
graph and analyzer all describe the same data (previously two disjoint data sets, audit D-02).
"""
import os
import threading
from collections import defaultdict
from typing import Any, Dict, List, Optional

import pandas as pd

from app.models.schemas import AnomalyScore, Claim, ClaimInput, RuleFlags, SIUCase
from app.services import persistence
from app.services.forecasting import calculate_provider_exposure
from app.services.ml_engine import AnomalyDetector
from app.services.rules_engine import evaluate_claim_rules, rule_codes
from app.services.siu_ranking import (
    case_id_for,
    compute_composite_score,
    generate_siu_queue,
    npi_from_case_id,
    summarize_provider,
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_CLAIMS_CSV = os.path.join(PROJECT_ROOT, "data", "synthetic_claims.csv")


class CaseStore:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.loaded = False
        self._reset()

    def _reset(self) -> None:
        self.claims: List[Claim] = []
        self.claims_by_id: Dict[str, Claim] = {}
        self.by_provider: Dict[str, List[Claim]] = defaultdict(list)
        self.by_member: Dict[str, List[Claim]] = defaultdict(list)
        self.provider_names: Dict[str, str] = {}
        self.dataset_labels: Dict[str, str] = {}  # synthetic ground-truth label from the CSV (never used for scoring)
        self.rule_results: Dict[str, RuleFlags] = {}
        self.anomaly_results: Dict[str, AnomalyScore] = {}
        self.centrality: Dict[str, float] = {}
        self.centrality_raw: Dict[str, float] = {}
        self.graph_risk_color: Dict[str, str] = {}
        self.ml = AnomalyDetector()
        self.csv_claim_count = 0
        self.centrality_error: Optional[str] = None
        self._memory = None
        self._memory_error: Optional[str] = None
        self._queue_cache: Optional[List[SIUCase]] = None

    # ------------------------------------------------------------------ loading
    def ensure_loaded(self) -> "CaseStore":
        if not self.loaded:
            with self.lock:
                if not self.loaded:
                    self.load()
        return self

    def load(self, csv_path: Optional[str] = None) -> None:
        with self.lock:
            self._reset()
            path = csv_path or DEFAULT_CLAIMS_CSV
            df = pd.read_csv(path, dtype=str).fillna("")
            for row in df.itertuples(index=False):
                claim = Claim(
                    claim_id=row.claim_id,
                    provider_npi=row.provider_npi,
                    member_id=row.member_id,
                    facility_id=row.facility_id or None,
                    cpt_code=row.cpt_code,
                    claim_amount=float(row.claim_amount),
                    timestamp=row.claim_timestamp,
                    location=row.location_city,
                    diagnosis_code=None,
                )
                self._index(claim)
                if row.provider_name:
                    self.provider_names.setdefault(claim.provider_npi, row.provider_name)
                self.dataset_labels[claim.claim_id] = row.fraud_flag or "UNKNOWN"
            self.csv_claim_count = len(self.claims)

            # Claims submitted earlier through "create investigation" (persisted in SQLite).
            for r in persistence.query("SELECT payload FROM submitted_claims ORDER BY rowid"):
                claim = Claim.model_validate_json(r["payload"])
                if claim.claim_id not in self.claims_by_id:
                    self._index(claim)

            self.ml.fit(self.claims)
            for claim, score in zip(self.claims, self.ml.predict_many(self.claims)):
                self.anomaly_results[claim.claim_id] = score
            for claim in self.claims:
                self.rule_results[claim.claim_id] = evaluate_claim_rules(claim, self.by_member[claim.member_id])

            self._load_centrality(path)
            self.loaded = True

    def _index(self, claim: Claim) -> None:
        self.claims.append(claim)
        self.claims_by_id[claim.claim_id] = claim
        self.by_provider[claim.provider_npi].append(claim)
        self.by_member[claim.member_id].append(claim)

    def _load_centrality(self, csv_path: str) -> None:
        """Graph centrality from the dataset, scaled to 0-1 by the largest value in the dataset."""
        try:
            from app.services.graph_analytics import detect_coordinated_fraud_rings

            _, analysis, _ = detect_coordinated_fraud_rings(csv_path)
            raw = {str(p["provider_npi"]): float(p["composite_centrality"]) for p in analysis.values()}
            top = max(raw.values(), default=0.0) or 1.0
            self.centrality_raw = raw
            self.centrality = {npi: round(v / top, 4) for npi, v in raw.items()}
            self.graph_risk_color = {str(p["provider_npi"]): p["risk_color"] for p in analysis.values()}
        except Exception as exc:  # keep serving: providers without graph evidence get centrality 0
            self.centrality_error = f"{type(exc).__name__}: {exc}"

    @property
    def memory(self):
        """Historical precedent index (TF-IDF), built lazily once."""
        if self._memory is None and self._memory_error is None:
            with self.lock:
                if self._memory is None and self._memory_error is None:
                    try:
                        from app.services.historical_memory import HistoricalCaseMemory

                        self._memory = HistoricalCaseMemory()
                    except Exception as exc:
                        self._memory_error = f"{type(exc).__name__}: {exc}"
        return self._memory

    # ------------------------------------------------------------------ mutations
    def add_claim(self, claim: Claim) -> None:
        """Persist a submitted claim, index it and refresh rule results for the member's claims."""
        with self.lock:
            if claim.claim_id in self.claims_by_id:
                raise KeyError(claim.claim_id)
            persistence.execute(
                "INSERT INTO submitted_claims (claim_id, payload) VALUES (?, ?)",
                (claim.claim_id, claim.model_dump_json()),
            )
            self._index(claim)
            self.anomaly_results[claim.claim_id] = self.ml.predict(claim)
            for c in self.by_member[claim.member_id]:
                self.rule_results[c.claim_id] = evaluate_claim_rules(c, self.by_member[claim.member_id])
            self.invalidate()

    # ------------------------------------------------------------------ analysis
    def analyze(self, claim: Claim) -> Dict[str, Any]:
        """Evaluate a claim against stored data without storing it."""
        with self.lock:
            rules = evaluate_claim_rules(claim, self.by_member.get(claim.member_id, []))
            ml = self.ml.predict(claim)
            centrality = self.centrality.get(claim.provider_npi, 0.0)
            composite = compute_composite_score(rules.flag_count, ml.ml_score, centrality)
            return {"rules": rules, "ml": ml, "centrality": centrality, "composite": composite}

    # ------------------------------------------------------------------ state from SQLite
    def case_states(self) -> Dict[str, Dict[str, Any]]:
        return {r["case_id"]: r for r in persistence.query("SELECT * FROM case_state")}

    def last_actions(self) -> Dict[str, str]:
        rows = persistence.query("SELECT case_id, MAX(timestamp) AS ts FROM audit_events GROUP BY case_id")
        return {r["case_id"]: r["ts"] for r in rows}

    def watchlist(self) -> Dict[str, bool]:
        return {r["provider_npi"]: bool(r["enabled"]) for r in persistence.query("SELECT * FROM watchlist")}

    # ------------------------------------------------------------------ queue / lookup
    def invalidate(self) -> None:
        """Drop the cached queue; call after anything that changes claims or case state."""
        self._queue_cache = None

    def queue(self) -> List[SIUCase]:
        with self.lock:
            if self._queue_cache is not None:
                return self._queue_cache
            self._queue_cache = generate_siu_queue(
                self.claims,
                self.rule_results,
                self.anomaly_results,
                self.centrality,
                provider_names=self.provider_names,
                case_states=self.case_states(),
                last_actions=self.last_actions(),
            )
            return self._queue_cache

    def get_case(self, case_id: str) -> Optional[SIUCase]:
        npi = npi_from_case_id(case_id)
        if not npi or npi not in self.by_provider:
            return None
        with self.lock:
            return next((c for c in self.queue() if c.case_id == case_id), None)

    def resolve_provider(self, identifier: str) -> Optional[str]:
        """Accept a case ID, a provider NPI or a claim ID and return the provider NPI."""
        npi = npi_from_case_id(identifier)
        if npi and npi in self.by_provider:
            return npi
        if identifier in self.by_provider:
            return identifier
        claim = self.claims_by_id.get(identifier)
        return claim.provider_npi if claim else None

    def claim_risk(self, claim: Claim) -> float:
        flags = self.rule_results.get(claim.claim_id)
        ml = self.anomaly_results.get(claim.claim_id)
        return compute_composite_score(
            flags.flag_count if flags else 0,
            ml.ml_score if ml else 0.0,
            self.centrality.get(claim.provider_npi, 0.0),
        )

    def provider_summary(self, npi: str):
        return summarize_provider(npi, self.by_provider[npi], self.rule_results, self.anomaly_results, self.centrality)

    def exposure(self, npi: str):
        return calculate_provider_exposure(npi, self.by_provider.get(npi, []))


_store = CaseStore()


def get_store() -> CaseStore:
    """Return the shared store, loading it on first use (also works without the FastAPI lifespan)."""
    return _store.ensure_loaded()


def reload_store() -> CaseStore:
    _store.load()
    return _store

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from app.models.schemas import Claim, AnomalyScore

class AnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
        self._is_fitted = False

    def _extract_features(self, claims: list[Claim]) -> pd.DataFrame:
        features = []
        for c in claims:
            is_weekend = 1 if c.timestamp.weekday() >= 5 else 0
            features.append({
                "claim_amount": c.claim_amount,
                "is_weekend": is_weekend,
                "cpt_code_numeric": int(''.join(filter(str.isdigit, c.cpt_code)) or 0)
            })
        return pd.DataFrame(features)

    def fit(self, historical_claims: list[Claim]):
        if not historical_claims:
            return
        df = self._extract_features(historical_claims)
        self.model.fit(df)
        self._is_fitted = True

    def predict(self, claim: Claim) -> AnomalyScore:
        if not self._is_fitted:
            return AnomalyScore(ml_score=0.1, is_anomalous=False)

        df = self._extract_features([claim])
        raw_score = self.model.decision_function(df)[0]
        normalized_score = float(np.clip(1.0 - (raw_score + 0.5), 0.0, 1.0))
        is_anomalous = bool(self.model.predict(df)[0] == -1)

        return AnomalyScore(ml_score=round(normalized_score, 4), is_anomalous=is_anomalous)

ml_service = AnomalyDetector()
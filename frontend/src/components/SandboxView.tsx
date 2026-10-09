import { useEffect, useRef, useState, type ReactNode } from "react";
import { api, type ClaimAnalysisResult } from "../services/api";

/**
 * Real-Time Claim Sandbox (View 4).
 *
 * "1-Click Live Test Scenarios": each card fills the JSON editor with a claim payload, posts it to
 * POST /api/v1/analyze (dry run, nothing is stored) and shows the backend's findings in a drawer.
 *
 * Why the payloads look the way they do: the rules engine compares a claim with the claims already
 * stored for the same member. Duplicate and geography scenarios therefore anchor on a real claim
 * from the bundled dataset (CLM-B0C3F020 · MEM000258 · provider 1000000061 · CPT 71045 ·
 * Chennai · 2026-02-09T15:00Z), so the live rules engine really triggers.
 */

type ScenarioId = "upcoding" | "geography" | "duplicate";
type Action = "APPROVE" | "FLAG_FOR_SIU" | "PAUSE_PAYMENT";
type Claim = Record<string, unknown>;

interface Scenario {
  id: ScenarioId;
  title: string;
  tagline: string;
  detail: string;
  build: () => Claim;
}

const ANCHOR = { provider_npi: "1000000061", facility_id: "FAC042", diagnosis_code: "R05" };

const SCENARIOS: Scenario[] = [
  {
    id: "upcoding",
    title: "Upcoding Violation",
    tagline: "Inflated CPT code · high dollar amount",
    detail: "CPT 99215 billed at $4,860 — about 19× the $250 benchmark (rule trips at 4×).",
    build: () => ({
      claim_id: `CLM-SBX-UPC-${Date.now().toString(36).toUpperCase()}`,
      ...ANCHOR,
      member_id: "MEM-SBX-001",
      cpt_code: "99215",
      claim_amount: 4860,
      timestamp: new Date().toISOString().replace(/\.\d+Z$/, "Z"),
      location: "Chennai",
    }),
  },
  {
    id: "geography",
    title: "Impossible Geography",
    tagline: "Distant locations · impossible timeframe",
    detail: "Same member billed in Mumbai 60 minutes after a Chennai claim (limit: 2 hours).",
    build: () => ({
      claim_id: `CLM-SBX-GEO-${Date.now().toString(36).toUpperCase()}`,
      ...ANCHOR,
      member_id: "MEM000258",
      cpt_code: "99214",
      claim_amount: 180,
      timestamp: "2026-02-09T16:00:00Z",
      location: "Mumbai",
    }),
  },
  {
    id: "duplicate",
    title: "Duplicate Billing",
    tagline: "Identical provider · patient · date · service",
    detail: "Re-submits stored claim CLM-B0C3F020 one minute later (limit: 5 minutes).",
    build: () => ({
      claim_id: `CLM-SBX-DUP-${Date.now().toString(36).toUpperCase()}`,
      ...ANCHOR,
      member_id: "MEM000258",
      cpt_code: "71045",
      claim_amount: 73.18,
      timestamp: "2026-02-09T15:01:00Z",
      location: "Chennai",
    }),
  },
];

/**
 * The backend returns scores and rule flags but no action, so the recommendation is derived here:
 *  - PAUSE_PAYMENT: composite >= 70%, two or more rules, or a rule hit that the ML model also flags as anomalous
 *  - FLAG_FOR_SIU:  any rule triggered, ML-anomalous, or composite >= 40%
 *  - APPROVE:       otherwise
 */
function recommend(r: ClaimAnalysisResult): { action: Action; why: string } {
  const composite = r.composite_risk_score ?? 0;
  const rules = r.rule_flags.flag_count;
  const anomalous = r.anomaly_score.is_anomalous;
  if (composite >= 0.7) return { action: "PAUSE_PAYMENT", why: "Composite risk is 70% or higher." };
  if (rules >= 2) return { action: "PAUSE_PAYMENT", why: "Multiple rule violations were triggered." };
  if (rules >= 1 && anomalous) return { action: "PAUSE_PAYMENT", why: "A rule violation is corroborated by an ML anomaly." };
  if (rules >= 1) return { action: "FLAG_FOR_SIU", why: "A rules-engine violation needs investigator review." };
  if (anomalous || composite >= 0.4) return { action: "FLAG_FOR_SIU", why: "Elevated risk without a rule violation." };
  return { action: "APPROVE", why: "No rule violations and risk is below the review threshold." };
}

const ACTION_META: Record<Action, { tone: string; label: string }> = {
  APPROVE: { tone: "success", label: "APPROVE" },
  FLAG_FOR_SIU: { tone: "warning", label: "FLAG_FOR_SIU" },
  PAUSE_PAYMENT: { tone: "critical", label: "PAUSE_PAYMENT" },
};

const RULES: { key: "upcoding_anomaly" | "impossible_geography" | "is_duplicate"; label: string }[] = [
  { key: "upcoding_anomaly", label: "CPT upcoding" },
  { key: "impossible_geography", label: "Impossible geography" },
  { key: "is_duplicate", label: "Duplicate billing" },
];

const tier = (pct: number) => (pct >= 70 ? { tone: "critical", label: "CRITICAL" } : pct >= 40 ? { tone: "warning", label: "ELEVATED" } : { tone: "success", label: "LOW" });

function describeError(error: unknown): string {
  if (error instanceof DOMException && error.name === "AbortError") return "The analysis request timed out after 6 seconds. Check that the backend is running.";
  if (error instanceof TypeError) return "Cannot reach the ClaimShield backend. Start it (uvicorn app.main:app) and retry.";
  return error instanceof Error ? error.message : "Live claim analysis failed.";
}

const Spinner = () => <span className="spinner" aria-hidden="true" />;

interface Props {
  /** The existing manual analyzer form; rendered below the scenarios. */
  children?: ReactNode;
}

export default function SandboxView({ children }: Props) {
  const initial = SCENARIOS[0];
  const [active, setActive] = useState<ScenarioId | "custom" | null>(null);
  const [editor, setEditor] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ClaimAnalysisResult | null>(null);
  const [latency, setLatency] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const runId = useRef(0);
  const drawerRef = useRef<HTMLDivElement>(null);

  const execute = async (text: string, source: ScenarioId | "custom") => {
    let payload: unknown;
    try {
      payload = JSON.parse(text);
    } catch (e) {
      setActive(source);
      setResult(null);
      setError(`Invalid JSON — ${e instanceof Error ? e.message : "could not parse the claim."}`);
      setDrawerOpen(true);
      return;
    }
    if (payload === null || typeof payload !== "object" || Array.isArray(payload)) {
      setActive(source);
      setResult(null);
      setError("The claim must be a single JSON object.");
      setDrawerOpen(true);
      return;
    }
    const id = ++runId.current;
    setActive(source);
    setLoading(true);
    setError("");
    setResult(null);
    setDrawerOpen(true);
    const started = performance.now();
    try {
      const data = await api.analyzeRaw(payload as Claim);
      if (id !== runId.current) return; // a newer run superseded this one
      setLatency(Math.round(performance.now() - started));
      setResult(data);
    } catch (e) {
      if (id !== runId.current) return;
      setLatency(null);
      setError(describeError(e));
    } finally {
      if (id === runId.current) setLoading(false);
    }
  };

  const runScenario = (s: Scenario) => {
    const text = JSON.stringify(s.build(), null, 2);
    setEditor(text);
    void execute(text, s.id);
  };

  useEffect(() => {
    if (drawerOpen) drawerRef.current?.focus();
  }, [drawerOpen]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setDrawerOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const pct = result ? Math.round((result.composite_risk_score ?? 0) * 100) : 0;
  const risk = tier(pct);
  const rec = result ? recommend(result) : null;
  const activeTitle = active === "custom" ? "Custom claim" : SCENARIOS.find((s) => s.id === active)?.title ?? initial.title;

  return (
    <div className="page-content sandbox-page">
      <style>{CSS}</style>
      <div className="page-intro">
        <div>
          <p className="eyebrow">REAL-TIME CLAIM SANDBOX</p>
          <h2>1-Click Live Test Scenarios</h2>
          <p className="muted">Pick a scenario to load its claim JSON and run it through the live rules engine and anomaly model. Nothing is stored.</p>
        </div>
      </div>

      <section className="sbx-cards" aria-label="1-Click Live Test Scenarios">
        {SCENARIOS.map((s) => {
          const on = active === s.id;
          return (
            <button key={s.id} className={`sbx-card ${on ? "on" : ""}`} onClick={() => runScenario(s)} disabled={loading} aria-pressed={on}>
              <span className="sbx-card-top"><b>{s.title}</b>{loading && on ? <Spinner /> : <span className="sbx-run">RUN ▸</span>}</span>
              <span className="sbx-tag">{s.tagline}</span>
              <small>{s.detail}</small>
            </button>
          );
        })}
      </section>

      <section className="card sbx-editor">
        <div className="card-head">
          <div><p className="eyebrow">CLAIM PAYLOAD</p><h3>JSON editor</h3></div>
          <button className="btn btn-primary" onClick={() => void execute(editor, "custom")} disabled={loading || !editor.trim()}>
            {loading ? <Spinner /> : null}<span>{loading ? "Analyzing…" : "Analyze edited JSON"}</span>
          </button>
        </div>
        <textarea
          className="sbx-json"
          spellCheck={false}
          value={editor}
          placeholder={'Choose a scenario above, or paste a claim, e.g.\n{\n  "claim_id": "CLM-1",\n  "provider_npi": "1000000061",\n  "member_id": "MEM-1",\n  "cpt_code": "99215",\n  "claim_amount": 4860,\n  "timestamp": "2026-10-09T09:30:00Z",\n  "location": "Chennai",\n  "diagnosis_code": "R05"\n}'}
          onChange={(e) => setEditor(e.target.value)}
          aria-label="Claim JSON"
        />
      </section>

      {drawerOpen && (
        <aside className="sbx-drawer" ref={drawerRef} tabIndex={-1} role="dialog" aria-label="Analysis findings" aria-busy={loading}>
          <div className="sbx-drawer-head">
            <div><p className="eyebrow">LIVE ANALYSIS</p><h3>{activeTitle}</h3></div>
            {latency !== null && !loading && (
              <span className={`badge badge-${latency < 1000 ? "success" : "warning"}`}>{latency < 1000 ? "SUB-SECOND · " : "SLOW · "}{latency} ms</span>
            )}
            <button className="sbx-x" onClick={() => setDrawerOpen(false)} aria-label="Close findings">✕</button>
          </div>

          {loading && (
            <div className="sbx-state" role="status">
              <Spinner /><b>Analyzing claim…</b>
              <small>Running rules engine and anomaly model</small>
              <div className="sbx-skel"><i /><i /><i /></div>
            </div>
          )}

          {!loading && error && (
            <div className="sbx-error" role="alert">
              <b>Analysis failed</b><p>{error}</p>
              <button className="btn btn-secondary" onClick={() => void execute(editor, active ?? "custom")} disabled={!editor.trim()}>Retry</button>
            </div>
          )}

          {!loading && result && rec && (
            <div className="sbx-body">
              <div className="sbx-score">
                <div><span className="sbx-lbl">COMPOSITE RISK SCORE</span><strong>{pct}%</strong></div>
                <span className={`badge badge-${risk.tone}`}><span className="badge-dot" />{risk.label} · {pct}%</span>
              </div>
              <small className="sbx-note">Blend of rule flags (30%), ML anomaly (30%) and provider graph centrality (40%).</small>

              <div className="sbx-block">
                <span className="sbx-lbl">RULES ENGINE FINDINGS</span>
                <ul className="sbx-rules">
                  {RULES.map((r) => {
                    const hit = result.rule_flags[r.key];
                    return <li key={r.key} className={hit ? "hit" : ""}><span>{hit ? "⚠" : "✓"}</span>{r.label}<em>{hit ? "TRIGGERED" : "clear"}</em></li>;
                  })}
                </ul>
                {result.rule_flags.flag_reasons.length > 0 ? (
                  <ul className="sbx-reasons">{result.rule_flags.flag_reasons.map((t) => <li key={t}>{t}</li>)}</ul>
                ) : (
                  <small className="sbx-note">No violations triggered.</small>
                )}
              </div>

              <div className="sbx-block sbx-ml">
                <div><span className="sbx-lbl">ML ANOMALY SCORE</span><strong>{Math.round(result.anomaly_score.ml_score * 100)}%</strong></div>
                <span className={`badge badge-${result.anomaly_score.is_anomalous ? "critical" : "neutral"}`}>{result.anomaly_score.is_anomalous ? "ANOMALOUS" : "WITHIN NORMAL RANGE"}</span>
              </div>

              <div className={`sbx-block sbx-action ${ACTION_META[rec.action].tone}`}>
                <span className="sbx-lbl">RECOMMENDED ACTION</span>
                <strong>{ACTION_META[rec.action].label}</strong>
                <small>{rec.why}</small>
              </div>
              <small className="sbx-note">Claim {result.claim_id}{result.case_id ? ` · linked to ${result.case_id}` : " · provider has no existing case"} · dry run, not stored. The action is derived in the UI from the returned scores.</small>
            </div>
          )}
        </aside>
      )}

      {children && <div className="sbx-manual"><h3 className="sbx-manual-title">Manual claim analyzer</h3>{children}</div>}
    </div>
  );
}

const CSS = `
.sandbox-page .sbx-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-bottom:14px}
.sbx-card{display:flex;flex-direction:column;gap:7px;text-align:left;padding:15px;border-radius:9px;border:1px solid var(--border-soft);background:var(--surface);transition:border-color .15s,transform .15s}
.sbx-card:hover:not(:disabled){border-color:var(--green);transform:translateY(-1px)}
.sbx-card.on{border-color:var(--green-bright);background:var(--surface-2)}
.sbx-card:disabled{opacity:.7;cursor:progress}
.sbx-card-top{display:flex;justify-content:space-between;align-items:center;font:700 14px "Manrope",sans-serif}
.sbx-run{font-size:9px;letter-spacing:.1em;color:var(--green-bright)}
.sbx-tag{font-size:11px;color:var(--green-bright)}
.sbx-card small{font-size:10px;line-height:1.5;color:var(--muted)}
.sbx-editor{margin-bottom:16px;overflow:hidden}
.sbx-json{display:block;width:100%;min-height:210px;resize:vertical;border:0;background:var(--bg-deep);color:#d6e6e3;padding:14px 16px;font:12px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace}
.sbx-drawer{position:fixed;top:0;right:0;bottom:0;width:min(420px,100vw);z-index:40;background:#0d1e20;border-left:1px solid var(--border);box-shadow:-20px 0 50px rgba(0,0,0,.4);overflow:auto;padding:16px;outline:none;animation:sbxIn .18s ease-out}
@keyframes sbxIn{from{transform:translateX(24px);opacity:0}to{transform:none;opacity:1}}
.sbx-drawer-head{display:flex;align-items:center;gap:10px;margin-bottom:14px}.sbx-drawer-head>div{flex:1}
.sbx-x{width:28px;height:28px;border:1px solid var(--border);background:transparent;border-radius:6px}
.sbx-lbl{display:block;font-size:9px;letter-spacing:.1em;color:var(--muted);margin-bottom:5px}
.sbx-score{display:flex;justify-content:space-between;align-items:center;padding:14px;border:1px solid var(--border-soft);border-radius:9px;background:var(--surface)}
.sbx-score strong,.sbx-ml strong{font:700 34px "Manrope",sans-serif;line-height:1}.sbx-ml strong{font-size:24px}
.sbx-note{display:block;font-size:10px;color:var(--muted-2);line-height:1.5;margin:7px 0}
.sbx-block{margin-top:12px;padding:13px;border:1px solid var(--border-soft);border-radius:9px;background:var(--surface)}
.sbx-ml{display:flex;justify-content:space-between;align-items:center}
.sbx-rules,.sbx-reasons{list-style:none;margin:0;padding:0}
.sbx-rules li{display:flex;gap:8px;align-items:center;font-size:12px;padding:6px 0;color:var(--muted);border-bottom:1px solid var(--border-soft)}
.sbx-rules li.hit{color:#ffc45b;font-weight:600}.sbx-rules li em{margin-left:auto;font-size:9px;font-style:normal;letter-spacing:.08em}
.sbx-reasons{margin-top:9px}.sbx-reasons li{font-size:11px;line-height:1.5;color:#ffd9a0;padding:3px 0}
.sbx-action strong{display:block;font:700 20px "Manrope",sans-serif;margin-bottom:4px}.sbx-action small{font-size:11px;color:var(--muted)}
.sbx-action.success{border-color:rgba(72,201,79,.4)}.sbx-action.success strong{color:#74df7a}
.sbx-action.warning{border-color:rgba(245,158,11,.4)}.sbx-action.warning strong{color:#ffc45b}
.sbx-action.critical{border-color:rgba(239,68,68,.45)}.sbx-action.critical strong{color:#ff8585}
.sbx-state{display:grid;gap:8px;justify-items:center;padding:34px 0;text-align:center}.sbx-state small{color:var(--muted)}
.sbx-skel{display:grid;gap:8px;width:100%;margin-top:14px}.sbx-skel i{height:14px;border-radius:5px;background:linear-gradient(90deg,var(--surface),var(--surface-3),var(--surface));background-size:200% 100%;animation:sbxSh 1.1s linear infinite}
@keyframes sbxSh{to{background-position:-200% 0}}
.sbx-error{padding:14px;border:1px solid rgba(239,68,68,.4);background:rgba(239,68,68,.08);border-radius:9px;display:grid;gap:8px;justify-items:start}
.sbx-error p{font-size:12px;line-height:1.5;color:#ffb1b1;word-break:break-word}
.sbx-manual{margin-top:26px;padding-top:18px;border-top:1px solid var(--border-soft)}.sbx-manual-title{margin-bottom:12px;color:var(--muted)}
@media(max-width:900px){.sandbox-page .sbx-cards{grid-template-columns:1fr}}
@media(prefers-reduced-motion:reduce){.sbx-drawer,.sbx-skel i{animation:none}}
`;

import { useCallback, useEffect, useState } from "react";
import { api } from "../services/api";

/* ---------- Icons (inline SVG, no extra deps) ---------- */
const svgProps = { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true };

const AlertIcon = ({ size = 15 }) => (
  <svg {...svgProps} width={size} height={size}><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4M12 17h.01" /></svg>
);
const ShieldIcon = ({ size = 16 }) => (
  <svg {...svgProps} width={size} height={size}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" /><path d="M12 8v4M12 16h.01" /></svg>
);
const BookIcon = ({ size = 15 }) => (
  <svg {...svgProps} width={size} height={size}><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5v14Z" /><path d="M20 17v4H6.5A2.5 2.5 0 0 1 4 18.5" /></svg>
);
const DocIcon = ({ size = 14 }) => (
  <svg {...svgProps} width={size} height={size}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z" /><path d="M14 2v6h6M8 13h8M8 17h5" /></svg>
);

/* ---------- Payload mapping ---------- */
/**
 * Backend policy snippets are built in `insights.build_context` as
 * "<passage id> (<section title>): <passage text>", e.g.
 * "SECTION 102 · item 2 (UNBUNDLING & UPCODING ANOMALIES): Upcoding: ...".
 * We show "<passage id>: <passage text>" and keep the section title as a tooltip.
 */
export function parseCitation(raw) {
  const text = String(raw ?? "").trim();
  const match = text.match(/^(.+?)\s*\(([^)]*)\):\s*([\s\S]+)$/);
  if (!match) return { label: "", section: "", body: text };
  return { label: match[1].trim(), section: match[2].trim(), body: match[3].trim() };
}

const uniqueStrings = (list) =>
  Array.from(new Set((Array.isArray(list) ? list : []).map((s) => String(s ?? "").trim()).filter(Boolean)));

/* ---------- Data hook: GET /api/v1/copilot/context/{case_id} ---------- */
export function useCaseContext(caseId) {
  const [state, setState] = useState({ status: "loading", rules: [], citations: [], error: "" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading", rules: [], citations: [], error: "" });
    api
      .copilotContext(caseId)
      .then((ctx) => {
        if (cancelled) return;
        setState({
          status: "ready",
          rules: uniqueStrings(ctx?.rule_flag_reasons),
          citations: uniqueStrings(ctx?.policy_context_paragraphs).map(parseCitation),
          error: "",
        });
      })
      .catch((err) => {
        if (cancelled) return;
        const aborted = err?.name === "AbortError";
        setState({
          status: "error",
          rules: [],
          citations: [],
          error: aborted ? "The request timed out." : err instanceof Error ? err.message : "Unable to load case context.",
        });
      });
    return () => {
      cancelled = true;
    };
  }, [caseId, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  return { ...state, retry };
}

/* ---------- Shared bits ---------- */
function SkeletonRows({ count, label }) {
  return (
    <div role="status" aria-live="polite" aria-label={label} className="space-y-2">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="animate-pulse rounded-lg border border-slate-800 bg-slate-900/60 p-3">
          <div className="h-2.5 w-1/3 rounded bg-slate-800" />
          <div className="mt-2 h-2.5 w-full rounded bg-slate-800" />
          <div className="mt-1.5 h-2.5 w-4/5 rounded bg-slate-800" />
        </div>
      ))}
      <span className="sr-only">{label}</span>
    </div>
  );
}

function ErrorNotice({ message, onRetry, what }) {
  return (
    <div role="alert" className="rounded-lg border border-amber-900/40 bg-amber-950/10 p-3 text-[11px] text-amber-200">
      <b className="block text-[11px]">Unable to load {what}</b>
      <span className="mt-1 block text-slate-400">{message}</span>
      <button type="button" onClick={onRetry} className="mt-2 rounded border border-amber-700/50 px-2 py-1 text-[10px] font-semibold text-amber-200 hover:bg-amber-900/30">
        Retry
      </button>
    </div>
  );
}

/* ---------- 1. Triggered Deterministic Rules ---------- */
export function TriggeredRulesPanel({ status, rules, error, onRetry }) {
  const count = status === "ready" ? ` (${rules.length})` : "";
  return (
    <section aria-labelledby="triggered-rules-heading" className="mt-4">
      <h4 id="triggered-rules-heading" className="mb-2 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-red-400">
        <AlertIcon />
        <span>Triggered Deterministic Rules{count}</span>
      </h4>
      {status === "loading" && <SkeletonRows count={2} label="Loading triggered rules…" />}
      {status === "error" && <ErrorNotice what="triggered rules" message={error} onRetry={onRetry} />}
      {status === "ready" && rules.length === 0 && (
        <p className="rounded-lg border border-slate-800 bg-slate-900 p-3 text-[11px] text-slate-400">
          No deterministic rules were triggered for this case.
        </p>
      )}
      {status === "ready" && rules.length > 0 && (
        <ul className="space-y-2">
          {rules.map((rule) => (
            <li key={rule} className="flex items-start gap-2.5 rounded-lg border border-red-900/40 bg-red-950/10 p-3">
              <span className="mt-0.5 flex-none text-red-500"><ShieldIcon /></span>
              <span className="text-[11px] leading-relaxed text-slate-200">{rule}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/* ---------- 2. Federal Policy RAG Violations ---------- */
export function PolicyRagPanel({ status, citations, error, onRetry }) {
  return (
    <section aria-labelledby="policy-rag-heading" className="mt-4">
      <h4 id="policy-rag-heading" className="mb-2 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-green-400">
        <BookIcon />
        <span>Federal Policy RAG Violations</span>
      </h4>
      {status === "loading" && <SkeletonRows count={2} label="Retrieving policy citations…" />}
      {status === "error" && <ErrorNotice what="policy citations" message={error} onRetry={onRetry} />}
      {status === "ready" && citations.length === 0 && (
        <p className="rounded-lg border border-slate-800 bg-slate-900 p-3 text-[11px] text-slate-400">
          No policy passages were cited. Risk for this case comes from ML anomaly and graph signals only.
        </p>
      )}
      {status === "ready" && citations.length > 0 && (
        <div className="space-y-2">
          {citations.map((c, i) => (
            <article key={`${c.label}-${i}`} className="rounded-lg border border-slate-800 bg-slate-900 p-3" title={c.section || undefined}>
              <h5 className="flex items-center gap-1.5 text-[11px] font-bold text-green-400">
                <DocIcon />
                <span>Citation #{i + 1}</span>
              </h5>
              <p className="mt-1.5 text-[11px] leading-relaxed text-slate-300">
                {c.label && <b className="font-semibold text-slate-100">{c.label}: </b>}
                {c.body}
              </p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

/* ---------- Combined export used in the Case Workspace left column ---------- */
export default function CaseWorkspaceView({ caseId }) {
  const { status, rules, citations, error, retry } = useCaseContext(caseId);
  return (
    <div data-testid="case-context-cards">
      <TriggeredRulesPanel status={status} rules={rules} error={error} onRetry={retry} />
      <PolicyRagPanel status={status} citations={citations} error={error} onRetry={retry} />
    </div>
  );
}

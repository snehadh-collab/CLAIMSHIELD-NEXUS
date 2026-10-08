// Thin client for the ClaimShield Nexus FastAPI backend.
// In dev, Vite proxies /api -> http://localhost:8000 (see vite.config.ts).
const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export type ApiCase = {
  id: string;
  claim_id: string;
  provider: string;
  npi: string;
  member: string;
  facility: string;
  amount: number;
  cpt: string;
  city: string;
  timestamp: string;
  flag: "PHANTOM_BILLING" | "UPCODING" | "IMPOSSIBLE_GEOGRAPHY" | "CLEAN";
  score: number;
  risk_tier: string;
  confidence: number;
  variance: number;
  policy: string;
  citation: string;
  brief: string;
  flag_reasons: string[];
};

export type ApiMetrics = {
  total_analyzed: number;
  flagged_claims: number;
  flagged_exposure: number;
  flagged_exposure_pct: number;
  active_patterns: number;
  high_risk_hubs: number;
};

export type GraphPayload = {
  nodes: { id: string; node_type: string; label: string; city?: string | null; centrality?: number }[];
  edges: { source: string; target: string; edge_type: string }[];
  total_nodes: number;
  total_edges: number;
};

export type AuditAction = {
  case_id: string;
  action: string;
  investigator_id: string;
  notes?: string | null;
  timestamp: string;
};

export type AiBrief = {
  case_id: string;
  executive_summary: string;
  key_evidence: string[];
  policy_citations: string[];
  recommended_action: string;
  confidence_score: number;
};

export const api = {
  dashboard: () => request<{ metrics: ApiMetrics; cases: ApiCase[] }>("/api/v1/dashboard"),
  graph: (npi: string) => request<GraphPayload>(`/api/v1/graph/${encodeURIComponent(npi)}?radius=1`),
  audit: (caseId: string) =>
    request<{ case_id: string; actions: AuditAction[] }>(`/api/v1/cases/${encodeURIComponent(caseId)}/audit`),
  recordAction: (caseId: string, action: string, notes?: string) =>
    request<AuditAction>(`/api/v1/cases/${encodeURIComponent(caseId)}/action`, {
      method: "POST",
      body: JSON.stringify({ case_id: caseId, action, notes }),
    }),
  brief: (caseId: string, claimDetails: string, flaggedRules: string[]) =>
    request<AiBrief>("/api/v1/copilot/brief", {
      method: "POST",
      body: JSON.stringify({ case_id: caseId, claim_details: claimDetails, flagged_rules: flaggedRules }),
    }),
};

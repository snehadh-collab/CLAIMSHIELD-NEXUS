const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export type InvestigatorAction = "APPROVE_SIU" | "REQUEST_INFO" | "DISMISS";

export interface QueueCase {
  id: string;
  title: string;
  provider: string;
  npi: string;
  billed: string;
  risk: number;
  flag: string;
  status: string;
  updated: string;
}

interface BackendQueueCase {
  case_id: string;
  provider_npi: string;
  total_claim_amount: number;
  rule_flag_count: number;
  ml_anomaly_score: number;
  composite_risk_score: number;
  status: string;
}

export interface ClaimAnalysisInput {
  providerNpi: string;
  memberId: string;
  cptCode: string;
  claimAmount: number;
  timestamp: string;
  location: string;
  diagnosisCode: string;
  facilityId?: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 6000);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      let detail = "";
      try {
        const body = await response.json();
        if (typeof body?.detail === "string") detail = body.detail;
        else if (Array.isArray(body?.detail)) {
          detail = body.detail
            .map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).filter((p) => p !== "body").join(".")}: ${d.msg ?? "invalid"}`)
            .join("; ");
        }
      } catch { /* non-JSON error body */ }
      throw new Error(`API request failed with status ${response.status}${detail ? ` — ${detail}` : ""}`);
    }

    return response.json() as Promise<T>;
  } finally {
    window.clearTimeout(timeout);
  }
}

function money(value: number): string {
  const amount = Number(value);
  return Number.isFinite(amount)
    ? new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(amount)
    : String(value || "$0");
}

function normalizeQueueItem(item: BackendQueueCase): QueueCase {
  const riskValue = Number(item.composite_risk_score);
  const normalizedRisk = riskValue <= 1 ? riskValue * 100 : riskValue;

  return {
    id: item.case_id,
    title: item.rule_flag_count > 0 ? "Potential FWA investigation" : "Provider risk review",
    provider: `Provider ${item.provider_npi}`,
    npi: item.provider_npi,
    billed: money(item.total_claim_amount),
    risk: Math.round(normalizedRisk),
    flag: item.rule_flag_count > 0
      ? `${item.rule_flag_count} rule-based finding${item.rule_flag_count === 1 ? "" : "s"}`
      : item.ml_anomaly_score > 0
        ? `ML anomaly score ${Math.round(item.ml_anomaly_score * 100)}%`
        : "No active rule flags",
    status: item.status.replace(/_/g, " "),
    updated: "Live queue",
  };
}

/** Response of POST /api/v1/analyze (mirrors backend ClaimAnalysisResponse). */
export interface ClaimAnalysisResult {
  claim_id: string;
  provider_npi: string;
  rule_flags: {
    is_duplicate: boolean;
    impossible_geography: boolean;
    upcoding_anomaly: boolean;
    flag_count: number;
    flag_reasons: string[];
  };
  anomaly_score: { ml_score: number; is_anomalous: boolean };
  case_id?: string | null;
  graph_centrality?: number | null;
  composite_risk_score?: number | null;
  persisted: boolean;
}

export const api = {
  health: () => request<Record<string, unknown>>("/"),

  queue: async (): Promise<QueueCase[]> => {
    const payload = await request<BackendQueueCase[]>("/api/v1/siu/queue");
    return payload.map(normalizeQueueItem);
  },

  analyze: (claim: ClaimAnalysisInput) =>
    request<Record<string, unknown>>("/api/v1/analyze", {
      method: "POST",
      body: JSON.stringify({
        claim_id: `CLM-${crypto.randomUUID()}`,
        provider_npi: claim.providerNpi,
        member_id: claim.memberId,
        facility_id: claim.facilityId || undefined,
        cpt_code: claim.cptCode,
        claim_amount: claim.claimAmount,
        timestamp: claim.timestamp,
        location: claim.location,
        diagnosis_code: claim.diagnosisCode,
      }),
    }),

  /** Dry-run analysis of a raw claim payload (nothing is stored: no ?persist). */
  analyzeRaw: (payload: Record<string, unknown>) =>
    request<ClaimAnalysisResult>("/api/v1/analyze", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  forecast: (providerNpi: string) =>
    request<Record<string, unknown>>(`/api/v1/cases/${encodeURIComponent(providerNpi)}/forecast`),

  copilotContext: (caseId: string) =>
    request<Record<string, unknown>>(`/api/v1/copilot/context/${encodeURIComponent(caseId)}`),

  graph: (caseId: string) =>
    request<Record<string, unknown>>(`/api/v1/graph/export/${encodeURIComponent(caseId)}`),

  action: (
  caseId: string,
  action: InvestigatorAction,
  reason: string
) =>
  request<Record<string, unknown>>(
    `/api/v1/cases/${encodeURIComponent(caseId)}/action`,
    {
      method: "POST",
      body: JSON.stringify({
        action,
        investigator_id: "INV-DEFAULT",
        notes: reason,
      }),
    }
  ),

  audit: (caseId: string) =>
    request<Record<string, unknown>>(`/api/v1/cases/${encodeURIComponent(caseId)}/audit`),

  brief: (caseId: string) =>
  request<Record<string, unknown>>(
    `/api/v1/cases/${encodeURIComponent(caseId)}/brief`,
    {
      method: "POST",
      body: JSON.stringify({
        case_id: caseId,
        claim_details: `Investigation details for case ${caseId}`,
        flagged_rules: ["ANOMALOUS_BILLING"],
      }),
    }
  ),

  chat: (
  caseId: string,
  message: string,
  history: Array<{ role: string; content: string }> = []
) =>
  request<Record<string, unknown>>("/api/v1/copilot/chat", {
    method: "POST",
    body: JSON.stringify({
      case_id: caseId,
      message,
      chat_history: history,
    }),
  }),
};

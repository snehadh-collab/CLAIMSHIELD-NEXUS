import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.schemas import CopilotContextPayload, SIUBriefAI
from app.services import llm
from app.services.guardrails import apply_responsible_ai_guardrails
from app.services.llm import get_gemini_client  # re-exported for callers/tests that patch it
from app.services.policy_rag import get_relevant_policies


def _fallback_action(flagged_rules: List[str], ctx: Optional[CopilotContextPayload]) -> str:
    text = " ".join(flagged_rules).upper()
    if "UPCODING" in text or "DUPLICATE" in text or "PHANTOM" in text:
        return "PAYMENT_HOLD"
    if flagged_rules or (ctx and ctx.composite_risk_score >= 0.5):
        return "AUDIT"
    return "DISMISS"


def _fallback_brief(case_id, claim_details, flagged_rules, policies, ctx, reason) -> Dict[str, Any]:
    if ctx:
        evidence = [r for r in ctx.rule_flag_reasons[:6]] or ["No rule-based finding for this case."]
        evidence.append(
            f"Composite risk {ctx.composite_risk_score:.2f}; max claim ML anomaly {ctx.ml_anomaly_score:.2f}; "
            f"graph centrality {ctx.graph_centrality_score:.2f}."
        )
        evidence.append(f"Projected 90-day billing exposure ${ctx.projected_90d_loss:,.0f} (linear run-rate).")
    else:
        evidence = [f"Flagged rule violation: {r}" for r in flagged_rules] if flagged_rules else [claim_details]
    summary = (
        f"Rule-based summary for {case_id} (not AI-generated): {claim_details}"
        if claim_details
        else f"Rule-based summary for {case_id}: flagged for {', '.join(flagged_rules) or 'anomalous billing patterns'}."
    )
    return {
        "case_id": case_id,
        "executive_summary": summary,
        "key_evidence": evidence,
        "policy_citations": policies,
        "recommended_action": _fallback_action(flagged_rules, ctx),
        "confidence_score": 0.0,
        "source": "FALLBACK",
        "ai_error": reason,
    }


def generate_siu_brief(
    case_id: str,
    claim_details: str,
    flagged_rules: List[str],
    ctx: Optional[CopilotContextPayload] = None,
    policy_passages: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build an investigation brief.

    With a Gemini key it asks Gemini for a structured brief grounded in the supplied case facts and
    retrieved policy passages. Without one (or on any failure) it returns a deterministic, clearly
    labelled FALLBACK brief assembled from the same facts: `source` says which one you got, and
    `confidence_score` is only meaningful when `source == "GEMINI"`.
    """
    if policy_passages:
        policies = [f"{p['id']} ({p['section_title']}): {p['text']}" for p in policy_passages]
    else:
        policies = get_relevant_policies(f"{claim_details} {' '.join(flagged_rules)}")

    prompt = f"""
    You are an expert Special Investigations Unit (SIU) Healthcare Fraud Analyst.
    Produce a structured investigation brief for case {case_id}. Use ONLY the facts below; do not invent
    claims, amounts, people or regulations. Cite policy only from the list provided.

    CASE FACTS:
    {claim_details}

    FLAGGED RULE VIOLATIONS:
    {', '.join(flagged_rules) or 'none'}

    RELEVANT POLICY PASSAGES (the only citations you may use):
    {chr(10).join(policies) or 'none'}

    The recommended_action must be one of PAYMENT_HOLD, AUDIT, DISMISS. confidence_score is your own
    0-1 estimate of how well the facts support the summary.
    """

    text, error = llm.generate(prompt, temperature=0.2, response_schema=SIUBriefAI, client_factory=get_gemini_client)
    brief: Dict[str, Any]
    if text:
        try:
            ai = SIUBriefAI.model_validate_json(text) if hasattr(SIUBriefAI, "model_validate_json") else SIUBriefAI(**json.loads(text))
            brief = ai.model_dump()
            brief["case_id"] = case_id  # the model must not rename the case
            brief["source"] = "GEMINI"
            brief["ai_error"] = None
        except Exception as exc:
            brief = _fallback_brief(case_id, claim_details, flagged_rules, policies, ctx, f"AI response was not a valid brief ({type(exc).__name__})")
    else:
        brief = _fallback_brief(case_id, claim_details, flagged_rules, policies, ctx, error)

    guarded = apply_responsible_ai_guardrails(brief, "")
    if brief["source"] == "FALLBACK":
        guarded["status"] = "AI_UNAVAILABLE"
        guarded["confidence_score"] = 0.0
    guarded["generated_at"] = datetime.now(timezone.utc).isoformat()
    return guarded


# Quick local test
if __name__ == "__main__":
    result = generate_siu_brief(
        "CLAIM-9042",
        "Billed CPT 99215 twice for member M-102 within 4 hours across two facilities.",
        ["IMPOSSIBLE_GEOGRAPHY", "DUPLICATE_BILLING"],
    )
    print(json.dumps(result, indent=2))

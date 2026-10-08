from typing import Dict, Any

def apply_responsible_ai_guardrails(brief: Dict[str, Any], query_text: str = "") -> Dict[str, Any]:
    """Applies Responsible AI guardrails to check for safety, clinical boundary compliance,

    and synthetic data disclaimers.
    """
    blocked_keywords = ["diagnose patient", "prescribe medication", "treatment plan", "medical advice"]
    
    query_lower = query_text.lower()
    for kw in blocked_keywords:
        if kw in query_lower:
            return {
                "status": "SAFETY_REFUSAL",
                "message": f"Guardrail Refusal: Copilot is restricted to SIU Fraud Investigation analysis and cannot provide clinical {kw}."
            }
            
    return {
        "status": "PASSED_GUARDRAILS",
        "disclaimer": "CONFIDENTIAL SIU BRIEF — Generated using 100% synthetic healthcare claims data. No real PHI present."
    }

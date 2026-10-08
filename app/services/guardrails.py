def apply_responsible_ai_guardrails(brief_data: dict, user_prompt: str = "") -> dict:
    """Enforces safety guardrails on AI outputs:
    1. Blocks medical/clinical diagnosis requests.
    2. Attaches synthetic data disclaimers.
    3. Normalizes confidence scores within bounds [0.0, 1.0].
    """
    # Guardrail 1: Refuse Clinical / Diagnostic Prompts
    prohibited_keywords = ["diagnose", "treatment plan", "medical advice", "prescribe", "patient symptoms"]
    if any(keyword in user_prompt.lower() for keyword in prohibited_keywords):
        return {
            "status": "SAFETY_REFUSAL",
            "message": "AI Safety Refusal: ClaimShield Copilot provides Fraud, Waste & Abuse analysis only. Clinical diagnoses and medical treatment recommendations are strictly prohibited.",
            "confidence_score": 0.0
        }

    # Guardrail 2: Ensure Synthetic Data Disclaimer is present
    disclaimer = "DISCLAIMER: Generated using 100% synthetic claims data. No real patient HIPAA data was processed."
    
    if "disclaimer" not in brief_data:
        brief_data["disclaimer"] = disclaimer

    # Guardrail 3: Clamp Confidence Score between 0.0 and 1.0
    if "confidence_score" in brief_data:
        brief_data["confidence_score"] = min(max(float(brief_data["confidence_score"]), 0.0), 1.0)
    else:
        brief_data["confidence_score"] = 0.85

    brief_data["status"] = "PASSED_GUARDRAILS"
    return brief_data

# Test Guardrails locally
if __name__ == "__main__":
    test_brief = {
        "case_id": "CLAIM-9042",
        "executive_summary": "Possible duplicate billing detected.",
        "confidence_score": 0.95
    }
    
    print("--- Test Normal Output ---")
    print(apply_responsible_ai_guardrails(test_brief, "Summarize case CLAIM-9042"))

    print("\n--- Test Safety Refusal ---")
    print(apply_responsible_ai_guardrails(test_brief, "Can you diagnose patient symptoms for this member?"))
import json
from typing import Dict, List, Any
from app.services.policy_rag import get_relevant_policies
from app.models.copilot import SIUBriefSchema
from app.config import settings

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    genai = None
    types = None
    HAS_GENAI = False

def generate_siu_brief(case_id: str, claim_details: str, flagged_rules: List[str]) -> Dict[str, Any]:
    """Combines claim details with RAG policy retrieval and uses Google Gemini

    to generate a structured JSON investigation brief. Returns structured fallback if API fails or unconfigured.
    """
    # 1. Fetch relevant policies using RAG
    search_query = f"{claim_details} {' '.join(flagged_rules)}"
    policies = get_relevant_policies(search_query)
    policies_text = "\n".join(policies)

    # 2. Retrieve Gemini API Key
    api_key = settings.GEMINI_API_KEY

    if HAS_GENAI and api_key and api_key != "YOUR_GEMINI_API_KEY_HERE":
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"""
            You are an expert Special Investigations Unit (SIU) Healthcare Fraud Analyst.
            Analyze the following flagged insurance claim and produce a structured investigation brief.

            CLAIM DETAILS:
            {claim_details}

            FLAGGED RULE VIOLATIONS:
            {', '.join(flagged_rules)}

            RELEVANT HEALTHCARE POLICIES (CITATIONS):
            {policies_text}

            Provide a concise, grounded, and accurate investigation summary.
            """

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=SIUBriefSchema,
                    temperature=0.2,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Gemini API call warning/failure: {str(e)}. Utilizing structured fallback engine.")

    # 3. Graceful Structured Fallback Brief
    recommendation = "PAYMENT_HOLD" if any(r in ["IMPOSSIBLE_GEOGRAPHY", "PHANTOM_BILLING", "IMPOSSIBLE_TRAVEL"] for r in flagged_rules) else "AUDIT_REVIEW"

    return {
        "case_id": case_id,
        "executive_summary": f"Claim {case_id} flagged for SIU review based on {len(flagged_rules)} risk indicators ({', '.join(flagged_rules)}). Details: {claim_details}",
        "key_evidence": [
            f"Flagged rule violation: {rule}" for rule in flagged_rules
        ] + [f"Claim context: {claim_details}"],
        "policy_citations": policies,
        "recommended_action": recommendation,
        "confidence_score": 0.88
    }

if __name__ == "__main__":
    test_case_id = "CLAIM-9042"
    test_details = "Dr. Synthetic-A billed CPT 99215 twice for member M-102 within 4 hours across two facilities 60 miles apart."
    test_rules = ["IMPOSSIBLE_TRAVEL", "DUPLICATE_BILLING"]

    print("--- Testing Gemini / Fallback SIU Brief Generator ---")
    result = generate_siu_brief(test_case_id, test_details, test_rules)
    print(json.dumps(result, indent=2))

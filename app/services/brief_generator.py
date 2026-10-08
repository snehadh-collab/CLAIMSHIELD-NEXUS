import os
import json
from dotenv import load_dotenv
load_dotenv()
from google import genai
from google.genai import types
from app.services.policy_rag import get_relevant_policies
from app.models.schemas import SIUBriefSchema

# Initialize Google Gemini Client
# Make sure GEMINI_API_KEY is set in your environment or pass api_key directly
api_key = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
client = genai.Client(api_key=api_key)

def generate_siu_brief(case_id: str, claim_details: str, flagged_rules: list[str]) -> dict:
    """Combines claim details with RAG policy retrieval and uses Gemini

    to generate a structured JSON investigation brief.
    """
    # 1. Fetch relevant policies using RAG (Feature 1.7)
    search_query = f"{claim_details} {' '.join(flagged_rules)}"
    policies = get_relevant_policies(search_query)
    policies_text = "\n".join(policies)

    # 2. Construct Structured System & User Prompt
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

    try:
        # 3. Call Gemini API with Structured Output enforcement
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SIUBriefSchema,
                temperature=0.2,
            ),
        )
        
        # Return parsed JSON response
        return json.loads(response.text)

    except Exception as e:
        # Fallback dictionary if API call fails or key is missing
        return {
            "case_id": case_id,
            "executive_summary": f"Error generating brief: {str(e)}",
            "key_evidence": [f"Flagged rule: {r}" for r in flagged_rules],
            "policy_citations": policies,
            "recommended_action": "MANUAL_REVIEW",
            "confidence_score": 0.5
        }

# Quick local test
if __name__ == "__main__":
    test_case_id = "CLAIM-9042"
    test_details = "Dr. Synthetic-A billed CPT 99215 twice for member M-102 within 4 hours across two facilities 60 miles apart."
    test_rules = ["IMPOSSIBLE_TRAVEL", "DUPLICATE_BILLING"]

    print("--- Testing Gemini SIU Brief Generator ---")
    result = generate_siu_brief(test_case_id, test_details, test_rules)
    print(json.dumps(result, indent=2))
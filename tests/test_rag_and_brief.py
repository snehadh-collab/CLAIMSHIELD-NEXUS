from app.services.policy_rag import get_relevant_policies
from app.services.brief_generator import generate_siu_brief

def test_policy_rag_retrieval():
    sample_query = "duplicate billing CPT code 24-hour window"
    matches = get_relevant_policies(sample_query)
    assert len(matches) > 0
    assert "DUPLICATE BILLING" in matches[0] or "Policy" in matches[0]

def test_brief_generation_fallback():
    test_case_id = "CLAIM-TEST-9042"
    test_details = "Dr. Synthetic-A billed CPT 99215 twice for member M-102 within 4 hours across two facilities 60 miles apart."
    test_rules = ["IMPOSSIBLE_TRAVEL", "DUPLICATE_BILLING"]

    brief = generate_siu_brief(test_case_id, test_details, test_rules)
    assert brief["case_id"] == test_case_id
    assert "recommended_action" in brief
    assert len(brief["key_evidence"]) > 0
    assert len(brief["policy_citations"]) > 0

import os
from typing import List
from app.config import settings

def get_relevant_policies(query_text: str, max_results: int = 2) -> List[str]:
    """Keyword-matching RAG retriever to retrieve relevant healthcare policy rules

    from synthetic_policies.md based on claim details and flagged rule names.
    """
    policy_path = settings.POLICIES_MD
    if not os.path.exists(policy_path):
        return ["Policy documentation file synthetic_policies.md not found."]

    with open(policy_path, "r", encoding="utf-8") as f:
        content = f.read()

    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    matched_paragraphs = []
    keywords = query_text.lower().split()

    for p in paragraphs:
        p_lower = p.lower()
        score = sum(1 for kw in keywords if kw in p_lower)
        if score > 0:
            matched_paragraphs.append((score, p))

    matched_paragraphs.sort(key=lambda x: x[0], reverse=True)

    results = [p[1] for p in matched_paragraphs[:max_results]]

    if not results:
        results = [
            "General FWA Policy: All submitted claims are subject to standard fraud, waste, and abuse audit protocols."
        ]

    return results

if __name__ == "__main__":
    sample_query = "duplicate billing CPT code 24-hour window"
    matches = get_relevant_policies(sample_query)
    print("--- RAG Policy Match Test ---")
    for idx, match in enumerate(matches, 1):
        print(f"\n[Match {idx}]\n{match}")

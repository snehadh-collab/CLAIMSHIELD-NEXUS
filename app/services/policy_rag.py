import os

# Path to the synthetic policies file
POLICY_FILE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "synthetic_policies.md"
)


def get_relevant_policies(query_text: str, max_results: int = 2) -> list[str]:
    """Simple keyword-matching RAG function to retrieve relevant healthcare policy rules

    based on flagged claim details.
    """
    if not os.path.exists(POLICY_FILE_PATH):
        return ["Policy documentation file not found."]

    with open(POLICY_FILE_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Split policy document by sections or numbered points
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    matched_paragraphs = []
    keywords = query_text.lower().split()

    for p in paragraphs:
        # Score each paragraph based on keyword occurrences
        p_lower = p.lower()
        score = sum(1 for kw in keywords if kw in p_lower)
        if score > 0:
            matched_paragraphs.append((score, p))

    # Sort paragraphs by highest relevance score
    matched_paragraphs.sort(key=lambda x: x[0], reverse=True)

    results = [p[1] for p in matched_paragraphs[:max_results]]

    # Fallback default if no keywords matched
    if not results:
        results = [
            "General FWA Policy: All submitted claims are subject to standard fraud, waste, and abuse audit protocols."
        ]

    return results


# Quick test run when executing this file directly
if __name__ == "__main__":
    sample_query = "duplicate billing CPT code 24-hour window"
    matches = get_relevant_policies(sample_query)
    print("--- RAG Policy Match Test ---")
    for idx, match in enumerate(matches, 1):
        print(f"\n[Match {idx}]\n{match}")
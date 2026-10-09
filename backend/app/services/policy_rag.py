import os
from typing import List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
POLICY_FILE_PATH = os.path.join(PROJECT_ROOT, "data", "synthetic_policies.md")


def get_relevant_policies(query_text: str, max_results: int = 2) -> List[str]:
    """Simple keyword-matching RAG function to retrieve relevant healthcare policy rules
    based on flagged claim details.
    """
    path_to_use = POLICY_FILE_PATH
    if not os.path.exists(path_to_use):
        # Fallback relative to current working directory
        cwd_candidate = os.path.join(os.getcwd(), "data", "synthetic_policies.md")
        if os.path.exists(cwd_candidate):
            path_to_use = cwd_candidate
        else:
            return ["Policy documentation file not found."]

    with open(path_to_use, "r", encoding="utf-8") as f:
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


# ---------------------------------------------------------------------------------------------
# Structured passage retrieval (TF-IDF cosine over individual policy items).
# This is real retrieval over the policy corpus; it generates nothing. Citations returned here
# always exist verbatim in data/synthetic_policies.md.
# ---------------------------------------------------------------------------------------------
import re
import threading
from typing import Dict, Any, Optional

_HEADING_RE = re.compile(r"^##\s*SECTION\s+(\d+)\s*:\s*(.+?)\s*$", re.IGNORECASE)
_ITEM_RE = re.compile(r"^(\d+)\.\s+(.*)$")

_index_lock = threading.Lock()
_index: Dict[str, Any] = {"mtime": None, "passages": [], "vectorizer": None, "matrix": None}


def load_policy_passages() -> List[Dict[str, Any]]:
    """Parse the policy markdown into one passage per numbered item, with its section."""
    if not os.path.exists(POLICY_FILE_PATH):
        return []
    passages: List[Dict[str, Any]] = []
    section_id, section_title = "", ""
    with open(POLICY_FILE_PATH, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            heading = _HEADING_RE.match(line)
            if heading:
                section_id, section_title = heading.group(1), heading.group(2).title()
                continue
            item = _ITEM_RE.match(line)
            if item and section_id:
                number, text = int(item.group(1)), item.group(2).strip()
                passages.append({
                    "id": f"SECTION {section_id} · item {number}",
                    "section_id": section_id,
                    "section_title": section_title,
                    "item": number,
                    "text": text,
                })
    return passages


def _ensure_index() -> Optional[Dict[str, Any]]:
    from sklearn.feature_extraction.text import TfidfVectorizer

    if not os.path.exists(POLICY_FILE_PATH):
        return None
    mtime = os.path.getmtime(POLICY_FILE_PATH)
    with _index_lock:
        if _index["mtime"] != mtime:
            passages = load_policy_passages()
            if not passages:
                return None
            vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
            docs = [f"{p['section_title']}. {p['text']}" for p in passages]
            _index.update(mtime=mtime, passages=passages, vectorizer=vectorizer, matrix=vectorizer.fit_transform(docs))
        return _index


def retrieve_policy_passages(query_text: str, top_k: int = 3, min_score: float = 0.05) -> List[Dict[str, Any]]:
    """Return the top policy passages for a query with their cosine score (0-1).

    Passages scoring below `min_score` are dropped, so an unrelated query returns an empty list
    instead of an arbitrary paragraph.
    """
    from sklearn.metrics.pairwise import cosine_similarity

    index = _ensure_index()
    if not index or not (query_text or "").strip():
        return []
    sims = cosine_similarity(index["vectorizer"].transform([query_text]), index["matrix"]).flatten()
    ranked = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:top_k]
    results = []
    for i in ranked:
        if sims[i] >= min_score:
            results.append({**index["passages"][i], "score": round(float(sims[i]), 4)})
    return results


# Quick test run when executing this file directly
if __name__ == "__main__":
    sample_query = "duplicate billing CPT code 24-hour window"
    matches = get_relevant_policies(sample_query)
    print("--- RAG Policy Match Test ---")
    for idx, match in enumerate(matches, 1):
        print(f"\n[Match {idx}]\n{match}")

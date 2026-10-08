import os
import pytest
from generate_claims import generate_synthetic_dataset
from historical_memory import HistoricalCaseMemory


def test_historical_memory_search_precision():
    if not os.path.exists("synthetic_claims.csv"):
        generate_synthetic_dataset(num_claims=5000)

    memory = HistoricalCaseMemory("synthetic_claims.csv")

    # Search for known injected pattern
    results = memory.search_similar_precedents(
        "Dr. Synthetic-A Phantom billing", top_k=3
    )

    assert len(results) > 0
    assert results[0]["match_score"] > 0.1
    assert "Phantom" in results[0]["summary"] or "PHANTOM" in results[0]["summary"]
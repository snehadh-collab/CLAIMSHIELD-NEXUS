import os
import pytest
from generate_claims import generate_synthetic_dataset
from graph_analytics import (
    detect_coordinated_fraud_rings,
    export_case_graph_json,
)


def test_graph_cluster_and_fraud_ring_detection():
    # 1. Ensure dataset exists
    if not os.path.exists("synthetic_claims.csv"):
        generate_synthetic_dataset(num_claims=5000)

    # 2. Run graph analytics
    G, analysis, rings = detect_coordinated_fraud_rings()

    # Verify connected components detected
    assert len(rings) > 0

    # 3. Assert Dr. Synthetic-A (1999999999 - Phantom Doctor) has high centrality score
    phantom_key = "PROV_1999999999"
    assert phantom_key in analysis
    phantom_metrics = analysis[phantom_key]

    # Must be marked with RED or AMBER risk color due to high degree/pagerank hub
    assert phantom_metrics["risk_color"] in ["RED", "AMBER"]
    assert phantom_metrics["composite_centrality"] > 0.005


def test_case_graph_json_export_structure():
    if not os.path.exists("synthetic_claims.csv"):
        generate_synthetic_dataset(num_claims=5000)

    G, _, _ = detect_coordinated_fraud_rings()

    # Test export for a sample case
    payload = export_case_graph_json(G, case_id="CLM-GEO-CHN-0")

    assert "case_id" in payload
    assert "nodes" in payload
    assert "edges" in payload

    # Ensure nodes payload contains target flag and valid color fields
    assert len(payload["nodes"]) > 0
    assert len(payload["edges"]) > 0
    assert "color" in payload["nodes"][0]
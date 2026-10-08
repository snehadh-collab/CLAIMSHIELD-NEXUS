import os
import networkx as nx
import pandas as pd
import pytest
from generate_claims import generate_synthetic_dataset
from graph_engine import build_claim_graph, get_degree_centrality


def test_data_integrity_and_null_keys():
    # 1. Generate fresh data
    df = generate_synthetic_dataset(num_claims=5000)

    # 2. Check files exist
    assert os.path.exists("synthetic_claims.csv")
    assert os.path.exists("synthetic_claims.json")

    # 3. Verify zero null values in primary keys
    assert df["claim_id"].isnull().sum() == 0
    assert df["provider_npi"].isnull().sum() == 0
    assert df["member_id"].isnull().sum() == 0

    # 4. Verify all injected fraud patterns are present
    flags = df["fraud_flag"].unique()
    assert "PHANTOM_BILLING" in flags
    assert "UPCODING" in flags
    assert "IMPOSSIBLE_GEOGRAPHY" in flags
    assert len(df[df["fraud_flag"] != "CLEAN"]) >= 140


def test_graph_topology_and_centrality():
    if not os.path.exists("synthetic_claims.csv"):
        generate_synthetic_dataset(num_claims=5000)

    G = build_claim_graph("synthetic_claims.csv")

    # Verify edge threshold >= 5,000 edges
    assert G.number_of_edges() >= 5000
    assert G.number_of_nodes() >= 1000

    # Verify degree centrality runs without errors
    centrality = get_degree_centrality(G)
    assert len(centrality) > 0
    assert centrality[0][1] > 0.0  # Top node has >0 centrality
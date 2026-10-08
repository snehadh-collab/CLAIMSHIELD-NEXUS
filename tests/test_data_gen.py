import os
import networkx as nx
import pandas as pd
import pytest
from pathlib import Path
from app.config import settings
from scripts.generate_claims import generate_synthetic_dataset
from app.services.graph_service import build_claim_graph, get_degree_centrality

def test_data_integrity_and_null_keys(tmp_path):
    # 1. Generate fresh data
    df = generate_synthetic_dataset(num_claims=5000, output_dir=str(tmp_path))

    # 2. Check files exist
    assert os.path.exists(tmp_path / "synthetic_claims.csv")
    assert os.path.exists(tmp_path / "synthetic_claims.json")
    project_root = Path(__file__).resolve().parents[1]
    assert not (project_root / "synthetic_claims.csv").exists()
    assert not (project_root / "synthetic_claims.json").exists()

    # 3. Verify zero null values in primary keys
    assert len(df) == 5000
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
    csv_path = settings.CLAIMS_CSV
    if not os.path.exists(csv_path):
        generate_synthetic_dataset(num_claims=5000, output_dir=settings.DATA_DIR)

    G = build_claim_graph(csv_path)

    # Verify edge threshold >= 5,000 edges
    assert G.number_of_edges() >= 5000
    assert G.number_of_nodes() >= 1000

    # Verify degree centrality runs without errors
    centrality = get_degree_centrality(G)
    assert len(centrality) > 0
    assert centrality[0][1] > 0.0  # Top node has >0 centrality

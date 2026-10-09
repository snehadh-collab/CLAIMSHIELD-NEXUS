import os
from scripts.generate_claims import generate_synthetic_dataset
from app.services.graph_engine import build_claim_graph, get_degree_centrality


def test_data_integrity_and_null_keys(tmp_path):
    # Writes into tmp_path so running the tests never replaces the project's dataset (audit D-28).
    df = generate_synthetic_dataset(num_claims=5000, output_dir=str(tmp_path))
    assert os.path.exists(tmp_path / "synthetic_claims.csv")
    assert os.path.exists(tmp_path / "synthetic_claims.json")
    assert df["claim_id"].isnull().sum() == 0
    assert df["provider_npi"].isnull().sum() == 0
    assert df["member_id"].isnull().sum() == 0
    flags = df["fraud_flag"].unique()
    assert "PHANTOM_BILLING" in flags and "UPCODING" in flags and "IMPOSSIBLE_GEOGRAPHY" in flags
    assert len(df[df["fraud_flag"] != "CLEAN"]) >= 140


def test_graph_topology_and_centrality():
    G = build_claim_graph()
    assert G.number_of_edges() >= 5000
    assert G.number_of_nodes() >= 1000
    centrality = get_degree_centrality(G)
    assert centrality[0][1] > 0.0

import os
import networkx as nx
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DEFAULT_CLAIMS_CSV = os.path.join(DATA_DIR, "synthetic_claims.csv")


def resolve_data_path(file_path: str) -> str:
    if os.path.isabs(file_path) and os.path.exists(file_path):
        return file_path
    if os.path.exists(file_path):
        return file_path
    candidate = os.path.join(DATA_DIR, os.path.basename(file_path))
    if os.path.exists(candidate):
        return candidate
    return file_path


def build_claim_graph(claims_csv_path=None):
    if claims_csv_path is None:
        path_to_use = DEFAULT_CLAIMS_CSV
    else:
        path_to_use = resolve_data_path(claims_csv_path)

    df = pd.read_csv(path_to_use)
    G = nx.DiGraph()

    for _, row in df.iterrows():
        provider_node = f"PROV_{row['provider_npi']}"
        member_node = f"MEM_{row['member_id']}"
        facility_node = f"FAC_{row['facility_id']}"

        # Add Nodes with Metadata
        G.add_node(
            provider_node,
            node_type="PROVIDER",
            label=row["provider_name"],
            city=row["location_city"],
        )
        G.add_node(member_node, node_type="MEMBER", label=row["member_id"])
        G.add_node(facility_node, node_type="FACILITY", label=row["facility_id"])

        # Add Directed Edges (Member -> Provider -> Facility)
        G.add_edge(
            member_node,
            provider_node,
            edge_type="BILLED_TO",
            claim_id=row["claim_id"],
            amount=row["claim_amount"],
            cpt=row["cpt_code"],
            timestamp=row["claim_timestamp"],
        )

        G.add_edge(
            provider_node,
            facility_node,
            edge_type="OPERATES_AT",
            claim_id=row["claim_id"],
        )

    print(
        f" Graph Loaded Successfully: {G.number_of_nodes()} Nodes, {G.number_of_edges()} Edges"
    )
    return G


def get_degree_centrality(G):
    """Calculates Degree Centrality to identify high-density hubs (potential fraud rings)"""
    centrality = nx.degree_centrality(G)
    sorted_centrality = sorted(
        centrality.items(), key=lambda x: x[1], reverse=True
    )
    return sorted_centrality


if __name__ == "__main__":
    graph = build_claim_graph()
    top_central = get_degree_centrality(graph)[:5]
    print("\nTop 5 Highest Centrality Nodes (Hubs):")
    for node, score in top_central:
        print(f"Node: {node} | Degree Centrality: {score:.4f}")

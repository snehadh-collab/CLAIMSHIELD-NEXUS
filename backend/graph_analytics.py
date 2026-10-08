import networkx as nx
import pandas as pd


def detect_coordinated_fraud_rings(claims_csv_path="synthetic_claims.csv"):
    """Analyzes the network graph for high-density billing loops,

    shared entity hubs, and suspicious provider-patient clusters.
    """
    df = pd.read_csv(claims_csv_path)
    G = nx.Graph()  # Undirected graph for component/cluster analysis

    # Build entity relationships
    for _, row in df.iterrows():
        provider_node = f"PROV_{row['provider_npi']}"
        member_node = f"MEM_{row['member_id']}"
        facility_node = f"FAC_{row['facility_id']}"

        G.add_node(
            provider_node,
            node_type="PROVIDER",
            name=row["provider_name"],
            city=row["location_city"],
        )
        G.add_node(member_node, node_type="MEMBER", name=row["member_id"])
        G.add_node(facility_node, node_type="FACILITY", name=row["facility_id"])

        G.add_edge(
            member_node,
            provider_node,
            edge_type="BILLED_TO",
            claim_id=row["claim_id"],
            amount=row["claim_amount"],
        )
        G.add_edge(
            provider_node,
            facility_node,
            edge_type="OPERATES_AT",
            claim_id=row["claim_id"],
        )

    # 1. Calculate PageRank Centrality
    pagerank_scores = nx.pagerank(G, weight="amount")

    # 2. Calculate Degree Centrality
    degree_scores = nx.degree_centrality(G)

    # 3. Detect Connected Components (Sub-networks/Rings)
    connected_components = list(nx.connected_components(G))

    # Combine scores for Provider nodes
    provider_analysis = {}
    for node, data in G.nodes(data=True):
        if data.get("node_type") == "PROVIDER":
            pr_score = pagerank_scores.get(node, 0.0)
            deg_score = degree_scores.get(node, 0.0)

            # Combined graph risk metric
            composite_centrality = round((pr_score * 0.5 + deg_score * 0.5), 4)

            # Assign risk color based on threshold
            risk_color = (
                "RED"
                if composite_centrality > 0.015
                else "AMBER" if composite_centrality > 0.008 else "GREEN"
            )

            provider_analysis[node] = {
                "provider_npi": node.replace("PROV_", ""),
                "provider_name": data.get("name"),
                "pagerank": round(pr_score, 4),
                "degree_centrality": round(deg_score, 4),
                "composite_centrality": composite_centrality,
                "risk_color": risk_color,
            }

    return G, provider_analysis, connected_components


def export_case_graph_json(
    G, case_id, claims_df_path="synthetic_claims.csv", max_neighbors=25
):
    """Exports node and edge payload formatted for React-Flow / PyVis frontend visualizer."""
    df = pd.read_csv(claims_df_path)

    # Find target claim
    claim_match = df[df["claim_id"] == case_id]
    if claim_match.empty:
        # Fallback to first claim if ID not found
        claim_row = df.iloc[0]
    else:
        claim_row = claim_match.iloc[0]

    target_provider = f"PROV_{claim_row['provider_npi']}"
    target_member = f"MEM_{claim_row['member_id']}"
    target_facility = f"FAC_{claim_row['facility_id']}"

    # Extract sub-graph surrounding target entities
    subgraph_nodes = {target_provider, target_member, target_facility}

    # Gather 1-hop neighbors
    for entity in list(subgraph_nodes):
        if G.has_node(entity):
            neighbors = list(G.neighbors(entity))[:max_neighbors]
            subgraph_nodes.update(neighbors)

    subgraph = G.subgraph(subgraph_nodes)

    # Format Nodes for Frontend
    nodes_payload = []
    for node_id, data in subgraph.nodes(data=True):
        node_type = data.get("node_type", "MEMBER")

        # Color mapping aligned with Acentra Brand guidelines
        if node_type == "PROVIDER":
            color = "#80C342" if "1999999999" in node_id else "#008751"  # Lime for high-risk / Emerald for normal
        elif node_type == "FACILITY":
            color = "#13583B"
        else:
            color = "#8FA29E"

        nodes_payload.append(
            {
                "id": node_id,
                "label": data.get("name", node_id),
                "type": node_type,
                "color": color,
                "is_target": node_id
                in [target_provider, target_member, target_facility],
            }
        )

    # Format Edges for Frontend
    edges_payload = []
    for u, v, data in subgraph.edges(data=True):
        edges_payload.append(
            {
                "source": u,
                "target": v,
                "label": data.get("edge_type", "CONNECTED"),
                "claim_id": data.get("claim_id", ""),
            }
        )

    return {"case_id": case_id, "nodes": nodes_payload, "edges": edges_payload}


if __name__ == "__main__":
    G, analysis, rings = detect_coordinated_fraud_rings()
    print(" Coordinated Fraud Ring Analysis Complete:")
    print(f"Total Sub-networks Detected: {len(rings)}")

    print("\nTop Provider Graph Risk Scores:")
    sorted_provs = sorted(
        analysis.values(), key=lambda x: x["composite_centrality"], reverse=True
    )[:5]
    for p in sorted_provs:
        print(
            f"Provider: {p['provider_name']} ({p['provider_npi']}) | Risk: {p['risk_color']} | Centrality: {p['composite_centrality']}"
        )
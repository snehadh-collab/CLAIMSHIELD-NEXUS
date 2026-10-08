import os
import networkx as nx
import pandas as pd
from typing import List, Dict, Tuple, Optional
from app.models.claim import Claim
from app.models.graph import GraphNode, GraphEdge, GraphPayload, CentralityHub
from app.config import settings

class GraphEngine:
    def __init__(self):
        self.G = nx.DiGraph()
        self.centrality_map: Dict[str, float] = {}

    def build_graph_from_claims(self, claims: List[Claim]) -> nx.DiGraph:
        self.G = nx.DiGraph()
        for c in claims:
            provider_node = f"PROV_{c.provider_npi}"
            member_node = f"MEM_{c.member_id}"
            facility_node = f"FAC_{c.facility_id or 'UNKNOWN'}"

            # Provider Name label fallback
            prov_label = c.provider_name or f"Dr. NPI-{c.provider_npi}"

            self.G.add_node(
                provider_node,
                node_type="PROVIDER",
                label=prov_label,
                city=c.location
            )
            self.G.add_node(member_node, node_type="MEMBER", label=c.member_id)
            self.G.add_node(facility_node, node_type="FACILITY", label=c.facility_id or "UNKNOWN")

            self.G.add_edge(
                member_node,
                provider_node,
                edge_type="BILLED_TO",
                claim_id=c.claim_id,
                amount=c.claim_amount,
                cpt=c.cpt_code,
                timestamp=c.timestamp.isoformat() if c.timestamp else None
            )

            self.G.add_edge(
                provider_node,
                facility_node,
                edge_type="OPERATES_AT",
                claim_id=c.claim_id
            )

        print(f" Graph Service: Loaded {self.G.number_of_nodes()} Nodes, {self.G.number_of_edges()} Edges")
        self.compute_centrality()
        return self.G

    def compute_centrality(self) -> Dict[str, float]:
        if self.G.number_of_nodes() > 0:
            self.centrality_map = nx.degree_centrality(self.G)
        return self.centrality_map

    def get_top_centrality(self, top_n: int = 10) -> List[CentralityHub]:
        if not self.centrality_map:
            self.compute_centrality()
        
        sorted_nodes = sorted(self.centrality_map.items(), key=lambda x: x[1], reverse=True)
        hubs = []
        for node_id, score in sorted_nodes[:top_n]:
            node_data = self.G.nodes.get(node_id, {})
            hubs.append(
                CentralityHub(
                    node_id=node_id,
                    degree_centrality=round(score, 6),
                    node_type=node_data.get("node_type", "UNKNOWN"),
                    label=node_data.get("label", node_id)
                )
            )
        return hubs

    def get_node_risk(self, provider_npi: str) -> float:
        node_id = f"PROV_{provider_npi}"
        return self.centrality_map.get(node_id, 0.0)

    def get_subgraph_payload(self, target_id: str, radius: int = 1) -> GraphPayload:
        target_node = target_id if (target_id in self.G) else f"PROV_{target_id}"
        if target_node not in self.G:
            target_node = f"MEM_{target_id}"
        
        if target_node not in self.G:
            # Return empty payload if not found
            return GraphPayload(nodes=[], edges=[], total_nodes=0, total_edges=0)

        subgraph_nodes = nx.single_source_shortest_path_length(
            self.G.to_undirected(), target_node, cutoff=radius
        ).keys()

        subgraph = self.G.subgraph(subgraph_nodes)

        nodes = []
        for n, data in subgraph.nodes(data=True):
            nodes.append(
                GraphNode(
                    id=n,
                    node_type=data.get("node_type", "UNKNOWN"),
                    label=data.get("label", n),
                    city=data.get("city"),
                    centrality=round(self.centrality_map.get(n, 0.0), 6)
                )
            )

        edges = []
        for u, v, data in subgraph.edges(data=True):
            edges.append(
                GraphEdge(
                    source=u,
                    target=v,
                    edge_type=data.get("edge_type", "CONNECTED"),
                    claim_id=data.get("claim_id"),
                    amount=data.get("amount"),
                    cpt=data.get("cpt"),
                    timestamp=data.get("timestamp")
                )
            )

        return GraphPayload(
            nodes=nodes,
            edges=edges,
            total_nodes=len(nodes),
            total_edges=len(edges)
        )

# Backward compatible helper functions for Member 1 unit tests
def build_claim_graph(claims_csv_path=settings.CLAIMS_CSV):
    if not os.path.exists(claims_csv_path):
        raise FileNotFoundError(f"Claims dataset not found: {claims_csv_path}")
    
    df = pd.read_csv(claims_csv_path)
    G = nx.DiGraph()
    for _, row in df.iterrows():
        provider_node = f"PROV_{row['provider_npi']}"
        member_node = f"MEM_{row['member_id']}"
        facility_node = f"FAC_{row['facility_id']}"

        G.add_node(provider_node, node_type="PROVIDER", label=row.get("provider_name", provider_node), city=row.get("location_city"))
        G.add_node(member_node, node_type="MEMBER", label=row["member_id"])
        G.add_node(facility_node, node_type="FACILITY", label=row["facility_id"])

        G.add_edge(member_node, provider_node, edge_type="BILLED_TO", claim_id=row["claim_id"], amount=row["claim_amount"], cpt=row["cpt_code"], timestamp=row["claim_timestamp"])
        G.add_edge(provider_node, facility_node, edge_type="OPERATES_AT", claim_id=row["claim_id"])
    return G

def get_degree_centrality(G):
    centrality = nx.degree_centrality(G)
    return sorted(centrality.items(), key=lambda x: x[1], reverse=True)

graph_service = GraphEngine()

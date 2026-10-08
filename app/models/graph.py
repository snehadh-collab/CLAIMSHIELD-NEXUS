from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class GraphNode(BaseModel):
    id: str
    node_type: str  # PROVIDER, MEMBER, FACILITY
    label: str
    city: Optional[str] = None
    centrality: Optional[float] = 0.0

class GraphEdge(BaseModel):
    source: str
    target: str
    edge_type: str  # BILLED_TO, OPERATES_AT
    claim_id: Optional[str] = None
    amount: Optional[float] = None
    cpt: Optional[str] = None
    timestamp: Optional[str] = None

class GraphPayload(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_nodes: int
    total_edges: int

class CentralityHub(BaseModel):
    node_id: str
    degree_centrality: float
    node_type: str
    label: str

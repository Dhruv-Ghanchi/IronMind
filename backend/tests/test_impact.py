from backend.impact.traversal import find_impacted_nodes
from backend.impact.scoring import calculate_risk_score
from backend.graph.graph_model import Node, Edge, NodeType, Layer

def test_impact_analysis():
    nodes = [
        Node(id="n1", name="n1", type=NodeType.TABLE, layer=Layer.DATABASE),
        Node(id="n2", name="n2", type=NodeType.CLASS, layer=Layer.BACKEND),
        Node(id="n3", name="n3", type=NodeType.ROUTE, layer=Layer.API)
    ]
    edges = [
        Edge(source="n1", target="n2", type="database_to_backend"),
        Edge(source="n2", target="n3", type="backend_to_api")
    ]
    
    impacted = find_impacted_nodes("n1", nodes, edges)
    assert "n2" in impacted
    assert "n3" in impacted
    assert len(impacted) == 2

def test_risk_scoring():
    impacted = ["n2", "n3", "n4", "n5"]
    result = calculate_risk_score(impacted)
    assert result["risk_score"] == 4
    assert result["severity"] == "MEDIUM"

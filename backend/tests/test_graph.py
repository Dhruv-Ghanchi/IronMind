import pytest
from backend.graph.node_builder import build_nodes
from backend.graph.edge_builder import build_edges
from backend.graph.graph_model import NodeType, Layer

def test_build_nodes():
    entities = {
        "tables": ["users"],
        "columns": ["users.email"],
        "routes": ["GET /profile"],
        "components": ["ProfilePage"]
    }
    nodes = build_nodes(entities)
    assert len(nodes) == 4
    types = {n.type for n in nodes}
    assert NodeType.TABLE in types
    assert NodeType.COLUMN in types
    assert NodeType.ROUTE in types
    assert NodeType.COMPONENT in types

def test_build_edges():
    entities = {
        "tables": ["users"],
        "columns": ["users.email"],
        "routes": ["GET /profile"],
        "components": ["ProfilePage"],
        "classes": ["UserService"]
    }
    nodes = build_nodes(entities)
    edges = build_edges(nodes, entities)
    
    # We expect some edges based on heuristic matching
    assert len(edges) > 0
    # Check for Column -> Class match (user.email -> UserService)
    db_to_be = [e for e in edges if e.type == "database_to_backend"]
    assert len(db_to_be) > 0

from .graph_model import Node, NodeType, Layer
from typing import List, Dict, Any

def build_nodes(entities: Dict[str, List[Any]]) -> List[Node]:
    nodes = []
    
    # 1. Database Layer
    for table in entities.get("tables", []):
        nodes.append(Node(id=table, name=table, type=NodeType.TABLE, layer=Layer.DATABASE))
    for col in entities.get("columns", []):
        nodes.append(Node(id=col, name=col, type=NodeType.COLUMN, layer=Layer.DATABASE))
        
    # 2. Backend Layer
    for cls in entities.get("classes", []):
        nodes.append(Node(id=cls, name=cls, type=NodeType.CLASS, layer=Layer.BACKEND))
    for func in entities.get("functions", []):
        nodes.append(Node(id=func, name=func, type=NodeType.FUNCTION, layer=Layer.BACKEND))
        
    # 3. API Layer
    for route in entities.get("routes", []):
        nodes.append(Node(id=route, name=route, type=NodeType.ROUTE, layer=Layer.API))
        
    # 4. Frontend Layer
    for comp in entities.get("components", []):
        nodes.append(Node(id=comp, name=comp, type=NodeType.COMPONENT, layer=Layer.FRONTEND))
        
    return nodes

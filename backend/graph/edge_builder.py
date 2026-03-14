from .graph_model import Node, Edge, NodeType, Layer
from typing import List, Dict, Any
import difflib
import re

def calculate_token_jaccard(s1: str, s2: str) -> float:
    """Token-based Jaccard similarity for naming convention mismatches."""
    def tokenize(s):
        return set(re.findall(r'[a-z0-9]+', s.lower()))
    
    set1, set2 = tokenize(s1), tokenize(s2)
    if not set1 or not set2: return 0.0
    intersection = len(set1.intersection(set2))
    union = len(set1) + len(set2) - intersection
    return intersection / union

def build_edges(nodes: List[Node], entities: Dict[str, List[Any]]) -> List[Edge]:
    edges = []
    
    # 1. DB -> Backend (Column referenced in backend code)
    # 2. Backend -> API (Route mapping)
    # 3. API -> Frontend (API fetch call)
    
    # Heuristic matching
    for source_node in nodes:
        for target_node in nodes:
            if source_node.id == target_node.id: continue
            
            confidence = 0.0
            
            # DB -> Backend (Column -> Python Class/Func)
            if source_node.type == NodeType.COLUMN and target_node.layer == Layer.BACKEND:
                source_name = source_node.name.lower()
                target_name = target_node.name.lower()
                table_name = source_name.split(".")[0]

                if source_name in target_name:
                    confidence = 1.0 if source_name == target_name else 0.8
                elif table_name and table_name in target_name:
                    confidence = 0.7
                elif calculate_token_jaccard(source_name, target_name) >= 0.5:
                    confidence = 0.6
                    
            # API -> Frontend (Route -> Component)
            if source_node.type == NodeType.ROUTE and target_node.layer == Layer.FRONTEND:
                # Check for path overlap
                if source_node.name in target_node.name:
                    confidence = 0.9

            if confidence > 0.5:
                edges.append(Edge(source=source_node.id, target=target_node.id, 
                                  type=f"{source_node.layer.value}_to_{target_node.layer.value}", 
                                  confidence=confidence))
                
    return edges

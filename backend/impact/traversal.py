from collections import deque
from .telemetry import telemetry
import time

def find_impacted_nodes(start_node_id, nodes, edges, max_depth=5):
    """BFS traversal to find all downstream impacted nodes."""
    start_time = time.time()
    impacted = []
    queue = deque([(start_node_id, 0)])
    visited = {start_node_id}
    
    edge_map = {}
    for edge in edges:
        if edge.source not in edge_map:
            edge_map[edge.source] = []
        edge_map[edge.source].append(edge.target)
        
    while queue:
        curr_id, depth = queue.popleft()
        if depth >= max_depth: continue
        
        for neighbor in edge_map.get(curr_id, []):
            if neighbor not in visited:
                visited.add(neighbor)
                impacted.append(neighbor)
                queue.append((neighbor, depth + 1))
                
    telemetry.log_traversal(time.time() - start_time, len(impacted), depth if 'depth' in locals() else 0)
    return impacted

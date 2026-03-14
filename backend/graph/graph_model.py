from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum

class NodeType(str, Enum):
    TABLE = "table"
    COLUMN = "column"
    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"
    ROUTE = "route"
    COMPONENT = "component"

class Layer(str, Enum):
    DATABASE = "database"
    BACKEND = "backend"
    API = "api"
    FRONTEND = "frontend"

class Node(BaseModel):
    id: str
    name: str
    type: NodeType
    layer: Layer
    metadata: Optional[Dict[str, Any]] = None

class Edge(BaseModel):
    source: str
    target: str
    type: str
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = None

class GraphResponse(BaseModel):
    nodes: List[Node]
    edges: List[Edge]
    summary: Dict[str, int]

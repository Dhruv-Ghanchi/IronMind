import React, { useMemo, useEffect, useCallback } from 'react';
import ReactFlow, { 
  Background, 
  Controls, 
  Panel,
  useReactFlow,
  type Node,
  type Edge,
  MarkerType,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import { FileNode } from './FileNode';

const nodeTypes = {
  fileNode: FileNode,
};

interface DependencyGraphProps {
  nodes: Node[];
  edges: Edge[];
  onNodeClick: (node: Node) => void;
  impactedNodeIds: string[];
}

const layerTitle = {
  database: 'Database Layer',
  backend: 'Backend Layer',
  api: 'API Layer',
  frontend: 'Frontend Layer',
};

const layerColor: Record<string, string> = {
  database: '#5361ff',
  backend: '#a3b8ff',
  api: '#10b981',
  frontend: '#8b5cf6',
};

const NODE_WIDTH = 220;
const NODE_HEIGHT = 100;
const LAYER_PADDING = 80;

const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'LR') => {
  const isHorizontal = direction === 'LR';
  
  // FIX: Create new graph instance per call to avoid state accumulation leak
  const dagreGraph = new dagre.graphlib.Graph({ compound: true });
  dagreGraph.setGraph({ rankdir: direction, ranksep: 120, nodesep: 80 });
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  // 1. Setup Dagre nodes and hierarchy
  const layers = ['database', 'backend', 'api', 'frontend'];
  layers.forEach(ly => {
    dagreGraph.setNode(`group_${ly}`, { label: ly, cluster: true });
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
    
    // Check for parent file (Symbols inside Files)
    const containsEdge = edges.find(e => e.target === node.id && e.label === 'CONTAINS');
    if (containsEdge) {
        dagreGraph.setParent(node.id, containsEdge.source);
    } else if (node.data?.layer) {
        // Otherwise, parent is the Layer group
        dagreGraph.setParent(node.id, `group_${node.data.layer}`);
    }
  });

  edges.forEach((edge) => {
    if (edge.label !== 'CONTAINS') {
        dagreGraph.setEdge(edge.source, edge.target);
    }
  });

  dagre.layout(dagreGraph);

  // 2. Map Positions and ParentIds
  const layoutedNodes = nodes.map((node) => {
    const nodeData = dagreGraph.node(node.id);
    node.targetPosition = isHorizontal ? Position.Left : Position.Top;
    node.sourcePosition = isHorizontal ? Position.Right : Position.Bottom;
    
    node.type = 'fileNode'; // FORCE custom node component
    
    node.position = {
      x: nodeData.x - NODE_WIDTH / 2,
      y: nodeData.y - NODE_HEIGHT / 2,
    };

    const containsEdge = edges.find(e => e.target === node.id && e.label === 'CONTAINS');
    if (containsEdge) {
        node.parentId = containsEdge.source;
    } else if (node.data?.layer) {
        node.parentId = `group_${node.data.layer}`;
    }

    return node;
  });

  // 3. Create Layer Group Nodes
  const nodeMap = new Map(layoutedNodes.map(n => [n.id, n]));
  
  const layerGroups: Node[] = layers.map(ly => {
    const lyNodes = layoutedNodes.filter(n => {
        if (n.data?.layer === ly) return true;
        if (!n.parentId) return false;
        const parent = nodeMap.get(n.parentId);
        return parent?.data?.layer === ly;
    });
    
    if (lyNodes.length === 0) return null;

    const minX = Math.min(...lyNodes.map(n => n.position.x)) - LAYER_PADDING;
    const minY = Math.min(...lyNodes.map(n => n.position.y)) - LAYER_PADDING;
    const maxX = Math.max(...lyNodes.map(n => n.position.x + NODE_WIDTH)) + LAYER_PADDING;
    const maxY = Math.max(...lyNodes.map(n => n.position.y + NODE_HEIGHT)) + LAYER_PADDING;

    // Relative positioning (Recursive Fix)
    lyNodes.filter(n => n.parentId === `group_${ly}`).forEach(file => {
        file.position.x -= minX;
        file.position.y -= minY;
        
        lyNodes.filter(sym => sym.parentId === file.id).forEach(sym => {
            sym.position.x -= (file.position.x + minX);
            sym.position.y -= (file.position.y + minY);
        });
    });

    return {
      id: `group_${ly}`,
      type: 'group',
      data: { label: layerTitle[ly as keyof typeof layerTitle] },
      position: { x: minX, y: minY },
      style: {
        width: maxX - minX,
        height: maxY - minY,
        backgroundColor: `${layerColor[ly]}03`,
        borderRadius: '32px',
        border: `1px dashed ${layerColor[ly]}20`,
        pointerEvents: 'none',
        zIndex: -1,
      }
    };
  }).filter(Boolean) as Node[];

  // 4. Manual Grid Layout Override (User Requested)
  layoutedNodes.forEach((node, i) => {
    node.position = {
      x: (i % 4) * 250,
      y: Math.floor(i / 4) * 150
    };
  });

  return { nodes: [...layerGroups, ...layoutedNodes], edges };
};

export const DependencyGraph: React.FC<DependencyGraphProps> = ({
  nodes: rawNodes,
  edges: rawEdges,
  onNodeClick,
  impactedNodeIds,
}) => {
  const { fitView } = useReactFlow();
  const [hiddenLayers, setHiddenLayers] = React.useState<string[]>([]);

  // 1. Filter Nodes/Edges based on layer visibility
  const filteredNodes = useMemo(() => {
    return rawNodes.filter(n => !hiddenLayers.includes(n.data?.layer));
  }, [rawNodes, hiddenLayers]);

  const filteredEdges = useMemo(() => {
    const nodeMap = new Map(rawNodes.map(n => [n.id, n]));
    return rawEdges.filter(edge => {
      const sourceNode = nodeMap.get(edge.source);
      const targetNode = nodeMap.get(edge.target);
      return (
        sourceNode && !hiddenLayers.includes(sourceNode.data?.layer) &&
        targetNode && !hiddenLayers.includes(targetNode.data?.layer)
      );
    });
  }, [rawEdges, rawNodes, hiddenLayers]);

  // 2. Apply Dagre Hierarchical Layout
  const { nodes: layoutedNodes, edges: layoutedEdges } = useMemo(() => {
    // Deep clone to prevent direct state mutation
    const nodesToLayout = JSON.parse(JSON.stringify(filteredNodes));
    const edgesToLayout = JSON.parse(JSON.stringify(filteredEdges));
    return getLayoutedElements(nodesToLayout, edgesToLayout);
  }, [filteredNodes, filteredEdges]);

  // 3. Apply Styling (Impact Analysis, etc.)
  const styledNodes = useMemo(() => {
    return layoutedNodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        isImpacted: impactedNodeIds.includes(node.id),
        selected: impactedNodeIds.includes(node.id),
      },
    }));
  }, [layoutedNodes, impactedNodeIds]);

  const styledEdges = useMemo(() => {
    return layoutedEdges
      .filter(edge => edge.label !== 'CONTAINS')
      .map((edge) => {
        const sourceNode = rawNodes.find(n => n.id === edge.source);
        const edgeColor = sourceNode?.data?.layer ? layerColor[sourceNode.data.layer] : '#475569';
        
        return {
          ...edge,
          animated: true,
          style: {
            stroke: edgeColor,
            strokeWidth: 2,
            opacity: impactedNodeIds.length > 0 ? (impactedNodeIds.includes(edge.source) || impactedNodeIds.includes(edge.target) ? 1 : 0.05) : 0.2,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: edgeColor,
          },
        };
      });
  }, [layoutedEdges, impactedNodeIds, rawNodes]);

  const stats = useMemo(() => {
    const counts: Record<string, number> = { database: 0, backend: 0, api: 0, frontend: 0 };
    rawNodes.forEach(n => {
      const layer = n.data?.layer;
      if (layer && layer in counts) counts[layer]++;
    });
    return counts;
  }, [rawNodes]);

  const toggleLayer = useCallback((layer: string) => {
    setHiddenLayers(prev => 
      prev.includes(layer) ? prev.filter(l => l !== layer) : [...prev, layer]
    );
  }, []);

  // 4. Center View on load or impact
  useEffect(() => {
    if (styledNodes.length > 0) {
      const timeoutId = setTimeout(() => {
        if (impactedNodeIds.length > 0) {
          fitView({ nodes: impactedNodeIds.map(id => ({ id })), duration: 800, padding: 0.5 });
        } else {
          fitView({ duration: 800, padding: 0.15 });
        }
      }, 100);
      return () => clearTimeout(timeoutId);
    }
  }, [styledNodes, impactedNodeIds, fitView]);

  return (
    <div className="w-full glass rounded-3xl overflow-hidden animate-fade-in" style={{ height: 'calc(100vh - 280px)', minHeight: '600px' }}>
      <ReactFlow
        nodes={styledNodes}
        edges={styledEdges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onNodeClick(node)}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.01}
        maxZoom={4}
        nodesDraggable={true}
        nodesConnectable={false}
        elementsSelectable={true}
        onlyRenderVisibleElements={true} // Performance Hack for 3k+ Nodes
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#1e293b" gap={20} size={1} />
        <Controls />
        <Panel position="top-right" className="flex flex-col gap-2 pointer-events-none">
            <div className="glass px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-widest text-brand-500">
                Live Architect
            </div>
        </Panel>
        
        {/* Layer Labels */}
        <Panel position="top-left" className="flex gap-8 p-4 bg-black/60 backdrop-blur-xl rounded-xl border border-white/10 ml-4 mt-4 shadow-2xl">
            {Object.entries(layerTitle).map(([key, label]) => {
                const isHidden = hiddenLayers.includes(key);
                const count = stats[key as keyof typeof stats] || 0;
                return (
                    <button 
                        key={key} 
                        onClick={() => toggleLayer(key)}
                        disabled={count === 0}
                        className={`
                          flex items-center gap-2 transition-all duration-300 px-3 py-1.5 rounded-lg
                          ${isHidden ? 'opacity-30' : 'opacity-100'} 
                          ${count === 0 ? 'cursor-not-allowed grayscale opacity-20' : 'hover:bg-white/5 hover:scale-105'}
                        `}
                    >
                        <div 
                          className="w-3 h-3 rounded-full border border-white/20 shadow-[0_0_10px_rgba(255,255,255,0.1)]" 
                          style={{ backgroundColor: isHidden ? '#334155' : (layerColor[key as keyof typeof layerColor] || '#5361ff') }} 
                        />
                        <div className="flex flex-col items-start leading-none gap-1">
                          <span className={`text-[10px] uppercase font-black tracking-tighter ${isHidden ? 'text-slate-500' : 'text-slate-200'}`}>
                              {label}
                          </span>
                          <span className="text-[8px] font-black text-brand-400">
                             {count} OBJECTS
                          </span>
                        </div>
                    </button>
                );
            })}
        </Panel>
      </ReactFlow>
    </div>
  );
};

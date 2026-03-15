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
  database: '#3b82f6', // Blue
  backend: '#10b981',  // Green
  api: '#f59e0b',      // Orange
  frontend: '#8b5cf6', // Purple
};

const LAYER_PADDING = 80;

const getLayoutedElements = (nodes: Node[], edges: Edge[]) => {
  const layers = ['database', 'backend', 'api', 'frontend'];
  const NODE_WIDTH = 220;
  const NODE_HEIGHT = 80;
  const HORIZONTAL_GAP = 120;
  const SYMBOL_VERTICAL_GAP = 40;
  const FILE_VERTICAL_GAP = 100;
  const LAYER_VERTICAL_GAP = 300;
  const COLS = 4;

  let currentY = 0;
  const layoutedNodes: Node[] = [];

  layers.forEach((ly) => {
    const nodesInLayer = nodes.filter((n) => n.data?.layer?.toLowerCase() === ly);
    if (nodesInLayer.length === 0) return;

    // 1. Identify Root Nodes (Files or Orphan Symbols)
    // A node is a root if it has NO "CONTAINS" parent in the same layer
    const rootNodes = nodesInLayer.filter(
      (n) => !edges.find((e) => e.target === n.id && e.label === 'CONTAINS')
    );

    // 2. Arrange Roots in a Grid and children beneath them
    const rowHeights: number[] = [];
    
    // First pass: Calculate row heights to avoid overlaps
    rootNodes.forEach((root, i) => {
      const row = Math.floor(i / COLS);
      const children = nodesInLayer.filter(
        (n) => edges.find((e) => e.source === root.id && e.target === n.id && e.label === 'CONTAINS')
      );
      const entryHeight = NODE_HEIGHT + children.length * SYMBOL_VERTICAL_GAP + FILE_VERTICAL_GAP;
      rowHeights[row] = Math.max(rowHeights[row] || 0, entryHeight);
    });

    // Second pass: Set positions
    rootNodes.forEach((root, i) => {
      const col = i % COLS;
      const row = Math.floor(i / COLS);
      const prevRowsHeight = rowHeights.slice(0, row).reduce((sum, h) => sum + h, 0);

      const x = col * (NODE_WIDTH + HORIZONTAL_GAP);
      const y = currentY + prevRowsHeight;

      root.position = { x, y };
      root.type = 'fileNode';
      root.targetPosition = Position.Top;
      root.sourcePosition = Position.Bottom;
      layoutedNodes.push(root);

      // Arrange Children (Symbols) vertically below the root
      const children = nodesInLayer.filter(
        (n) => edges.find((e) => e.source === root.id && e.target === n.id && e.label === 'CONTAINS')
      );

      children.forEach((child, j) => {
        child.position = { 
          x: x + 30, // Slight indent
          y: y + NODE_HEIGHT + j * SYMBOL_VERTICAL_GAP 
        };
        child.type = 'fileNode';
        child.targetPosition = Position.Top;
        child.sourcePosition = Position.Bottom;
        layoutedNodes.push(child);
      });
    });

    const layerHeight = rowHeights.reduce((sum, h) => sum + h, 0);
    currentY += layerHeight + LAYER_VERTICAL_GAP;
  });

  // 3. Create Static Layer Group Backgrounds
  const layerGroups: Node[] = layers.map(ly => {
    const lyNodes = layoutedNodes.filter(n => n.data?.layer?.toLowerCase() === ly);
    if (lyNodes.length === 0) return null;

    const minX = Math.min(...lyNodes.map(n => n.position.x)) - LAYER_PADDING;
    const minY = Math.min(...lyNodes.map(n => n.position.y)) - LAYER_PADDING;
    const maxX = Math.max(...lyNodes.map(n => n.position.x + NODE_WIDTH)) + LAYER_PADDING;
    const maxY = Math.max(...lyNodes.map(n => n.position.y + NODE_HEIGHT)) + LAYER_PADDING;

    return {
      id: `bg_group_${ly}`,
      data: { label: layerTitle[ly as keyof typeof layerTitle] },
      position: { x: minX, y: minY },
      zIndex: -1,
      draggable: false,
      selectable: false,
      style: {
        width: maxX - minX,
        height: maxY - minY,
        backgroundColor: `${layerColor[ly]}05`,
        borderRadius: '32px',
        border: `1px dashed ${layerColor[ly]}30`,
        pointerEvents: 'none',
        display: 'flex',
        alignItems: 'flex-start',
        padding: '24px',
        color: layerColor[ly],
        fontSize: '10px',
        fontWeight: '900',
        textTransform: 'uppercase',
        letterSpacing: '0.2em',
      }
    };
  }).filter(Boolean) as Node[];

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
    return rawNodes.filter(n => !hiddenLayers.includes(n.data?.layer?.toLowerCase()));
  }, [rawNodes, hiddenLayers]);

  const filteredEdges = useMemo(() => {
    const nodeMap = new Map(rawNodes.map(n => [n.id, n]));
    return rawEdges.filter(edge => {
      const sourceNode = nodeMap.get(edge.source);
      const targetNode = nodeMap.get(edge.target);
      return (
        sourceNode && !hiddenLayers.includes(sourceNode.data?.layer?.toLowerCase()) &&
        targetNode && !hiddenLayers.includes(targetNode.data?.layer?.toLowerCase())
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
        const sourceLayer = sourceNode?.data?.layer?.toLowerCase();
        const edgeColor = sourceLayer ? layerColor[sourceLayer] : '#475569';
        
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
      const layer = n.data?.layer?.toLowerCase();
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

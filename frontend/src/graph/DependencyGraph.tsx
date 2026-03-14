import React, { useMemo } from 'react';
import ReactFlow, { 
  Background, 
  Controls, 
  Panel,
  type Node,
  type Edge,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';

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
  frontend: '#5361ff',
};

export const DependencyGraph: React.FC<DependencyGraphProps> = ({
  nodes,
  edges,
  onNodeClick,
  impactedNodeIds,
}) => {
  const styledNodes = useMemo(() => {
    return nodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        isImpacted: impactedNodeIds.includes(node.id),
      },
      style: {
        ...node.style,
        opacity: impactedNodeIds.length > 0 && !impactedNodeIds.includes(node.id) ? 0.3 : 1,
        transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
        border: impactedNodeIds.includes(node.id) ? '2px solid #ef4444' : node.style?.border,
        boxShadow: impactedNodeIds.includes(node.id) ? '0 0 15px rgba(239, 68, 68, 0.4)' : node.style?.boxShadow,
      },
    }));
  }, [nodes, impactedNodeIds]);

  const styledEdges = useMemo(() => {
    return edges.map((edge) => ({
      ...edge,
      animated: impactedNodeIds.includes(edge.source) && impactedNodeIds.includes(edge.target),
      style: {
        ...edge.style,
        stroke: impactedNodeIds.includes(edge.source) && impactedNodeIds.includes(edge.target) ? '#ef4444' : '#64748b',
        strokeWidth: impactedNodeIds.includes(edge.source) && impactedNodeIds.includes(edge.target) ? 3 : 2,
        opacity: impactedNodeIds.length > 0 ? (impactedNodeIds.includes(edge.source) && impactedNodeIds.includes(edge.target) ? 1 : 0.1) : 0.6,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: impactedNodeIds.includes(edge.source) && impactedNodeIds.includes(edge.target) ? '#ef4444' : '#64748b',
      },
    }));
  }, [edges, impactedNodeIds]);

  return (
    <div className="w-full h-full glass rounded-3xl overflow-hidden animate-fade-in">
      <ReactFlow
        nodes={styledNodes}
        edges={styledEdges}
        onNodeClick={(_, node) => onNodeClick(node)}
        fitView
        minZoom={0.2}
        maxZoom={1.5}
      >
        <Background color="#1e293b" gap={20} size={1} />
        <Controls />
        <Panel position="top-right" className="flex flex-col gap-2 pointer-events-none">
            <div className="glass px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-widest text-brand-500">
                Live Dependency Graph
            </div>
        </Panel>
        
        {/* Layer Labels */}
        <Panel position="top-left" className="flex gap-8 p-4 bg-black/40 backdrop-blur-md rounded-xl border border-white/10 ml-4 mt-4">
            {Object.entries(layerTitle).map(([key, label]) => (
                <div key={key} className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: layerColor[key as keyof typeof layerColor] || '#5361ff' }} />
                    <span className="text-[10px] uppercase font-bold text-slate-400 tracking-tighter">{label}</span>
                </div>
            ))}
        </Panel>
      </ReactFlow>
    </div>
  );
};

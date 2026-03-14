import React, { useMemo, useEffect } from 'react';
import ReactFlow, { 
  Background, 
  Controls, 
  Panel,
  useReactFlow,
  type Node,
  type Edge,
  MarkerType,
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
  const { fitView } = useReactFlow();

  const styledNodes = useMemo(() => {
    return nodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        isImpacted: impactedNodeIds.includes(node.id),
      },
    }));
  }, [nodes, impactedNodeIds]);

  useEffect(() => {
    if (nodes.length > 0) {
      if (impactedNodeIds.length > 0) {
        fitView({ nodes: impactedNodeIds.map(id => ({ id })), duration: 800, padding: 0.5 });
      } else {
        fitView({ duration: 800, padding: 0.2 });
      }
    }
  }, [nodes, edges, impactedNodeIds, fitView]);

  const styledEdges = useMemo(() => {
    return edges.map((edge) => ({
      ...edge,
      animated: true,
      style: {
        stroke: '#475569',
        strokeWidth: 1.5,
        opacity: impactedNodeIds.length > 0 ? (impactedNodeIds.includes(edge.source) || impactedNodeIds.includes(edge.target) ? 1 : 0.1) : 0.4,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: '#475569',
      },
    }));
  }, [edges, impactedNodeIds]);

  return (
    <div className="w-full h-full glass rounded-3xl overflow-hidden animate-fade-in" style={{ minHeight: '500px' }}>
      <ReactFlow
        nodes={styledNodes}
        edges={styledEdges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onNodeClick(node)}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.05}
        maxZoom={1.5}
        nodesDraggable={true}
        nodesConnectable={false}
        elementsSelectable={true}
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

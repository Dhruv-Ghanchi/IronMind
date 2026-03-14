import React, { useState } from 'react';
import { Bug, FileCode, Database, Network, AlertCircle, ChevronDown, Copy } from 'lucide-react';
import type { Node, Edge } from 'reactflow';

interface DebugPanelProps {
  isOpen: boolean;
  analysisId: string | null;
  filesParsed: number;
  filesSkipped: number;
  nodes: Node[];
  edges: Edge[];
  lastImpactResult?: {
    node_id: string;
    impacted_nodes: string[];
    risk_score: number;
    severity: 'LOW' | 'MEDIUM' | 'HIGH';
  };
  pipelineLogs: string[];
  systemConfig?: {
    debug_mode_default: boolean;
    featherless_api_status: string;
    neo4j_status: string;
  } | null;
}

const StatCard: React.FC<{ 
  title: string; 
  value: string | number; 
  icon: React.ElementType; 
  color: string;
  subtitle?: string;
}> = ({ title, value, icon: Icon, color, subtitle }) => (
  <div className="bg-dark-800/40 backdrop-blur-md border border-white/10 rounded-2xl p-4 hover:border-white/20 transition-all flex flex-col justify-between group">
    <div className="flex justify-between items-start mb-4">
      <div className={`p-2 rounded-xl bg-${color}-500/10 border border-${color}-500/20 group-hover:scale-110 transition-transform`}>
        <Icon className={`w-5 h-5 text-${color}-400`} />
      </div>
      {subtitle && <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{subtitle}</span>}
    </div>
    <div>
      <div className="text-2xl font-black text-white tracking-tight">{value}</div>
      <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">{title}</div>
    </div>
  </div>
);

export const DebugPanel: React.FC<DebugPanelProps> = ({
  isOpen,
  analysisId,
  filesParsed,
  nodes,
  edges,
  lastImpactResult,
  pipelineLogs,
  systemConfig,
}) => {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    rawNodes: false,
    rawEdges: false,
    pipelineLogs: false,
  });

  if (!isOpen) return null;

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  // Calculate node counts by layer
  const nodesByLayer = {
    database: nodes.filter((n) => n.data?.layer === 'database').length,
    backend: nodes.filter((n) => n.data?.layer === 'backend').length,
    api: nodes.filter((n) => n.data?.layer === 'api').length,
    frontend: nodes.filter((n) => n.data?.layer === 'frontend').length,
  };

  // If no analysis loaded
  if (!analysisId) {
    return (
      <div className="fixed bottom-0 left-0 right-0 bg-dark-900/40 backdrop-blur-2xl border-t border-white/10 p-6 z-40">
        <div className="max-w-[1600px] mx-auto flex items-center gap-4">
          <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20">
            <Bug className="w-5 h-5 text-red-400" />
          </div>
          <div>
            <h3 className="font-black text-white tracking-tight">Debug Dashboard</h3>
            <p className="text-xs text-slate-400">Waiting for repository upload...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-dark-900/60 backdrop-blur-3xl border-t border-white/10 p-6 z-40 max-h-[60vh] overflow-y-auto animate-in slide-in-from-bottom duration-500">
      <div className="max-w-[1600px] mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-2xl bg-brand-500/10 border border-brand-500/20 shadow-lg shadow-brand-500/5">
              <Bug className="w-6 h-6 text-brand-400" />
            </div>
            <div>
              <h2 className="text-xl font-black text-white tracking-tighter">ENGINE DEBUGGER</h2>
              <div className="flex items-center gap-2 mt-1">
                <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">System Normal • Analysis Active</span>
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <code className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-[10px] font-mono text-emerald-300">
              ID: {analysisId.split('-')[0]}...
            </code>
          </div>
        </div>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard title="Total Nodes" value={nodes.length} icon={Network} color="blue" subtitle="Graph Depth" />
          <StatCard title="Dependencies" value={edges.length} icon={ChevronDown} color="purple" subtitle="Edge Count" />
          <StatCard title="Files Parsed" value={filesParsed} icon={FileCode} color="teal" subtitle="Source Control" />
          <div className="bg-dark-800/40 backdrop-blur-md border border-brand-500/30 rounded-2xl p-4 flex flex-col justify-between">
            <div className="flex justify-between items-start">
               <div className="p-2 rounded-xl bg-brand-500/10 border border-brand-500/20">
                <Database className="w-5 h-5 text-brand-400" />
              </div>
              <span className="text-[10px] font-bold text-brand-400 uppercase tracking-widest">Connectivity</span>
            </div>
            <div className="grid grid-cols-2 gap-2 mt-4">
              <div className="text-center p-2 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                <div className="text-emerald-400 font-bold text-xs uppercase">API</div>
                <div className="text-[9px] text-emerald-500/60 font-black">
                  {systemConfig?.featherless_api_status === 'configured' ? 'ONLINE' : 'MISSING'}
                </div>
              </div>
              <div className="text-center p-2 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                <div className="text-emerald-400 font-bold text-xs uppercase">DB</div>
                <div className="text-[9px] text-emerald-500/60 font-black">
                  {systemConfig?.neo4j_status === 'connected' ? 'STABLE' : 'OFFLINE'}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Layer Distribution & Impact */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Layer Breakdown */}
          <div className="lg:col-span-2 bg-white/5 border border-white/10 rounded-3xl p-6">
            <h4 className="text-xs font-bold text-white uppercase tracking-widest mb-6 flex items-center gap-2">
               <div className="w-1 h-3 bg-brand-500 rounded-full" />
               Entity Distribution
            </h4>
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: 'Database', count: nodesByLayer.database, colorClass: 'bg-blue-500' },
                { label: 'Backend', count: nodesByLayer.backend, colorClass: 'bg-teal-500' },
                { label: 'API Layer', count: nodesByLayer.api, colorClass: 'bg-amber-500' },
                { label: 'Frontend', count: nodesByLayer.frontend, colorClass: 'bg-purple-500' },
              ].map(layer => (
                <div key={layer.label} className="space-y-2">
                  <div className="flex justify-between items-end">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">{layer.label}</span>
                    <span className="text-sm font-black text-white">{layer.count}</span>
                  </div>
                  <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <div 
                      className={`h-full ${layer.colorClass} transition-all duration-1000`} 
                      style={{ width: `${(layer.count / (nodes.length || 1)) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Impact Snapshot */}
          <div className="bg-white/5 border border-white/10 rounded-3xl p-6">
            <h4 className="text-xs font-bold text-white uppercase tracking-widest mb-6 flex items-center gap-2">
               <div className="w-1 h-3 bg-orange-500 rounded-full" />
               Impact Snapshot
            </h4>
            {lastImpactResult ? (
              <div className="space-y-4">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Nodes Impacted</span>
                  <span className="text-emerald-400 font-bold">{lastImpactResult.impacted_nodes.length} items</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-slate-400">Risk Score</span>
                  <div className={`px-2 py-1 rounded text-[10px] font-black uppercase ${
                    lastImpactResult.risk_score > 7 ? 'bg-red-500/20 text-red-400' : 'bg-emerald-500/20 text-emerald-400'
                  }`}>
                    {lastImpactResult.risk_score.toFixed(1)} / 10.0
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-20 text-slate-400/80 space-y-2">
                <AlertCircle className="w-5 h-5 opacity-40" />
                <span className="text-[10px] font-bold uppercase tracking-widest">No Impact Cached</span>
              </div>
            )}
          </div>
        </div>

        {/* Collapsible Low-Level Data */}
        <div className="space-y-2 pb-8">
          <div className="bg-dark-800/20 border border-white/5 rounded-2xl overflow-hidden hover:border-white/10 transition-all">
            <button
              onClick={() => toggleSection('pipelineLogs')}
              className="w-full p-4 flex items-center justify-between group"
            >
              <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] group-hover:text-slate-300 transition-colors">Pipeline Stream</h4>
              <ChevronDown className={`w-3 h-3 text-slate-600 transition-transform ${expandedSections.pipelineLogs ? 'rotate-180' : ''}`} />
            </button>
            {expandedSections.pipelineLogs && (
              <div className="px-6 pb-6 pt-2 font-mono text-[9px] text-slate-400 max-h-40 overflow-y-auto space-y-1">
                {pipelineLogs.map((log, i) => (
                  <div key={i} className="flex gap-4">
                    <span className="text-slate-600">[{i}]</span>
                    <span>{log}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-2">
             <button
                onClick={() => toggleSection('rawNodes')}
                className="p-3 bg-dark-800/20 border border-white/5 rounded-2xl flex items-center justify-between group"
              >
                <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest group-hover:text-slate-300 transition-colors">Nodes JSON</span>
                <Copy onClick={(e) => { e.stopPropagation(); copyToClipboard(JSON.stringify(nodes, null, 2)); }} className="w-3 h-3 text-slate-600 hover:text-brand-400" />
              </button>
              <button
                onClick={() => toggleSection('rawEdges')}
                className="p-3 bg-dark-800/20 border border-white/5 rounded-2xl flex items-center justify-between group"
              >
                <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest group-hover:text-slate-300 transition-colors">Edges JSON</span>
                <Copy onClick={(e) => { e.stopPropagation(); copyToClipboard(JSON.stringify(edges, null, 2)); }} className="w-3 h-3 text-slate-600 hover:text-brand-400" />
              </button>
          </div>
        </div>
      </div>
    </div>
  );
};

import React from 'react';
import { Network, Database, Info } from 'lucide-react';

interface AnalysisSummaryProps {
  filesParsed: number;
  filesSkipped: number;
  nodesCount: number;
  edgesCount: number;
}

export const AnalysisSummary: React.FC<AnalysisSummaryProps> = ({
  filesParsed,
  filesSkipped,
  nodesCount,
  edgesCount
}) => {
  const stats = [
    { label: 'Files Analyzed', value: filesParsed, icon: Info, color: 'text-blue-400' },
    { label: 'Files Skipped', value: filesSkipped, icon: Info, color: 'text-amber-400' },
    { label: 'Graph Nodes', value: nodesCount, icon: Database, color: 'text-brand-500' },
    { label: 'Graph Edges', value: edgesCount, icon: Network, color: 'text-emerald-500' },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 animate-fade-in">
      {stats.map((stat, i) => (
        <div key={i} className="glass p-6 rounded-2xl">
          <div className="flex items-center justify-between mb-2">
            <stat.icon className={`w-5 h-5 ${stat.color} opacity-80`} />
            <span className="text-2xl font-bold">{stat.value}</span>
          </div>
          <p className="text-sm font-medium text-slate-400 uppercase tracking-wider">{stat.label}</p>
        </div>
      ))}
    </div>
  );
};

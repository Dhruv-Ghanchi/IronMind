import React from 'react';
import { Bug, FileCode, Database, Network, AlertCircle, CheckCircle2 } from 'lucide-react';

interface DebugPanelProps {
  isOpen: boolean;
  debugData: {
    filesScanned: number;
    filesParsed: number;
    filesSkipped: number;
    parseFailures: number;
    nodesCreated: number;
    edgesCreated: number;
    analysisTime: number;
    extractionLogs: string[];
  };
}

export const DebugPanel: React.FC<DebugPanelProps> = ({ isOpen, debugData }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-dark-900/95 backdrop-blur-xl border-t border-red-500/30 p-6 z-40 animate-fade-in max-h-[50vh] overflow-y-auto shadow-2xl">
      <div className="max-w-[1600px] mx-auto">
        <div className="flex items-center gap-3 mb-4">
          <Bug className="w-5 h-5 text-red-400" />
          <h3 className="font-bold uppercase tracking-widest text-sm text-red-400">Debug Mode</h3>
          <span className="text-xs text-slate-300 ml-auto">For development and diagnosis only</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* File Scanner Stats */}
          <div className="bg-dark-800/80 rounded-xl p-4 border border-blue-500/30 shadow-lg">
            <div className="flex items-center gap-2 mb-3">
              <FileCode className="w-4 h-4 text-blue-400" />
              <h4 className="font-bold text-xs uppercase tracking-wider text-blue-300">File Scanner</h4>
            </div>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-200">Scanned:</span>
                <span className="font-mono text-white font-bold">{debugData.filesScanned}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-200">Parsed:</span>
                <span className="font-mono text-emerald-300 font-bold">{debugData.filesParsed}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-200">Skipped:</span>
                <span className="font-mono text-amber-300 font-bold">{debugData.filesSkipped}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-200">Failures:</span>
                <span className="font-mono text-red-300 font-bold">{debugData.parseFailures}</span>
              </div>
            </div>
          </div>

          {/* Graph Stats */}
          <div className="bg-dark-800/80 rounded-xl p-4 border border-purple-500/30 shadow-lg">
            <div className="flex items-center gap-2 mb-3">
              <Network className="w-4 h-4 text-purple-400" />
              <h4 className="font-bold text-xs uppercase tracking-wider text-purple-300">Graph Builder</h4>
            </div>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-200">Nodes:</span>
                <span className="font-mono text-white font-bold">{debugData.nodesCreated}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-200">Edges:</span>
                <span className="font-mono text-white font-bold">{debugData.edgesCreated}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-200">Density:</span>
                <span className="font-mono text-slate-100 font-bold">
                  {debugData.nodesCreated > 0
                    ? (debugData.edgesCreated / debugData.nodesCreated).toFixed(2)
                    : '0.00'}
                </span>
              </div>
            </div>
          </div>

          {/* Performance */}
          <div className="bg-dark-800/80 rounded-xl p-4 border border-emerald-500/30 shadow-lg">
            <div className="flex items-center gap-2 mb-3">
              <Database className="w-4 h-4 text-emerald-400" />
              <h4 className="font-bold text-xs uppercase tracking-wider text-emerald-300">Performance</h4>
            </div>
            <div className="space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-200">Total Time:</span>
                <span className="font-mono text-white font-bold">{debugData.analysisTime}s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-200">Status:</span>
                <span className={`font-mono font-bold ${debugData.analysisTime < 20 ? 'text-emerald-300' : 'text-amber-300'}`}>
                  {debugData.analysisTime < 20 ? 'OPTIMAL' : 'SLOW'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-200">Target:</span>
                <span className="font-mono text-slate-200">&lt;20s</span>
              </div>
            </div>
          </div>

          {/* Health Check */}
          <div className="bg-dark-800/80 rounded-xl p-4 border border-amber-500/30 shadow-lg">
            <div className="flex items-center gap-2 mb-3">
              <AlertCircle className="w-4 h-4 text-amber-400" />
              <h4 className="font-bold text-xs uppercase tracking-wider text-amber-300">Health</h4>
            </div>
            <div className="space-y-2 text-xs">
              <div className="flex items-center gap-2">
                {debugData.parseFailures === 0 ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-amber-400" />
                )}
                <span className="text-slate-200">Parser</span>
              </div>
              <div className="flex items-center gap-2">
                {debugData.nodesCreated > 0 ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-red-400" />
                )}
                <span className="text-slate-200">Graph</span>
              </div>
              <div className="flex items-center gap-2">
                {debugData.analysisTime < 25 ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-amber-400" />
                )}
                <span className="text-slate-200">Speed</span>
              </div>
            </div>
          </div>
        </div>

        {/* Extraction Logs */}
        {debugData.extractionLogs.length > 0 && (
          <div className="mt-4 bg-dark-800/90 rounded-xl p-4 border border-white/20 shadow-lg">
            <h4 className="font-bold text-xs uppercase tracking-wider text-slate-200 mb-3">Extraction Logs</h4>
            <div className="space-y-1 max-h-32 overflow-y-auto font-mono text-xs text-slate-300">
              {debugData.extractionLogs.map((log, index) => (
                <div key={index} className="hover:text-white transition-colors py-0.5">
                  {log}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

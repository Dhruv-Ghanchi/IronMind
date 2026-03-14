import React from 'react';
import { X, BookOpen, Upload, MousePointer, Sparkles, AlertTriangle } from 'lucide-react';

interface DocumentationModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DocumentationModal: React.FC<DocumentationModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="glass rounded-3xl max-w-3xl w-full max-h-[80vh] overflow-y-auto p-8 relative">
        <button
          onClick={onClose}
          className="absolute top-6 right-6 p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <BookOpen className="w-8 h-8 text-brand-500" />
          <h2 className="text-3xl font-black">Documentation</h2>
        </div>

        <div className="space-y-6 text-slate-300">
          <section>
            <h3 className="text-xl font-bold text-white mb-3 flex items-center gap-2">
              <Upload className="w-5 h-5 text-brand-500" />
              Getting Started
            </h3>
            <p className="text-sm leading-relaxed mb-2">
              PolyglotAnalyzer helps you understand how changes propagate across your polyglot codebase.
            </p>
            <ol className="list-decimal list-inside space-y-2 text-sm">
              <li>Upload a ZIP file of your repository (max 40MB)</li>
              <li>Wait for the analysis to complete</li>
              <li>Explore the dependency graph visualization</li>
              <li>Click nodes to see impact analysis</li>
            </ol>
          </section>

          <section>
            <h3 className="text-xl font-bold text-white mb-3 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-brand-500" />
              Supported Languages
            </h3>
            <ul className="space-y-2 text-sm">
              <li><span className="text-emerald-500 font-bold">SQL</span> - Tables, columns, views, foreign keys</li>
              <li><span className="text-blue-500 font-bold">Python</span> - Routes, imports, classes, field references</li>
              <li><span className="text-amber-500 font-bold">JavaScript/TypeScript</span> - Components, API calls, field usage</li>
            </ul>
          </section>

          <section>
            <h3 className="text-xl font-bold text-white mb-3 flex items-center gap-2">
              <MousePointer className="w-5 h-5 text-brand-500" />
              Using the Graph
            </h3>
            <ul className="space-y-2 text-sm">
              <li><strong>Layers:</strong> Database → Backend → API → Frontend</li>
              <li><strong>Click a node:</strong> See all impacted downstream dependencies</li>
              <li><strong>Red highlights:</strong> Nodes affected by a change</li>
              <li><strong>Risk Score:</strong> Calculated based on impact scope</li>
              <li><strong>Zoom/Pan:</strong> Use mouse wheel and drag to navigate</li>
            </ul>
          </section>

          <section>
            <h3 className="text-xl font-bold text-white mb-3 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              Limitations
            </h3>
            <ul className="space-y-2 text-sm text-slate-400">
              <li>Maximum ZIP size: 40MB</li>
              <li>Maximum files scanned: 500</li>
              <li>Maximum files parsed: 180</li>
              <li>Target analysis time: under 20 seconds</li>
              <li>Ignored directories: node_modules, dist, build, venv, .git, __pycache__</li>
            </ul>
          </section>

          <section className="pt-4 border-t border-white/10">
            <p className="text-xs text-slate-500">
              Built for Hackathon 2026 • Polyglot Dependency Impact Analyzer
            </p>
          </section>
        </div>
      </div>
    </div>
  );
};

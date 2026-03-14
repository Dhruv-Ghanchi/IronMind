import { useState } from 'react';
import { UploadZone } from './components/UploadZone';
import { AnalysisSummary } from './components/AnalysisSummary';
import { SuggestedFixes } from './components/SuggestedFixes';
import { DocumentationModal } from './components/DocumentationModal';
import { DebugPanel } from './components/DebugPanel';
import { DependencyGraph } from './graph/DependencyGraph';
import { Search, Send, ShieldAlert, Layers } from 'lucide-react';
import { uploadRepo, analyzeImpact } from './api/client';
import type { Node, Edge } from 'reactflow';

// Initial Mock Data for UI Testing
const MOCK_NODES: Node[] = [
  { id: '1', position: { x: 0, y: 100 }, data: { label: 'users.email' }, style: { width: 150 }, type: 'input' },
  { id: '2', position: { x: 250, y: 100 }, data: { label: 'auth_service.py' }, style: { width: 150 } },
  { id: '3', position: { x: 500, y: 50 }, data: { label: 'GET /login' }, style: { width: 120 } },
  { id: '4', position: { x: 500, y: 150 }, data: { label: 'POST /token' }, style: { width: 120 } },
  { id: '5', position: { x: 750, y: 100 }, data: { label: 'LoginPage.tsx' }, style: { width: 150 }, type: 'output' },
];

const MOCK_EDGES: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', label: 'ref' },
  { id: 'e2-3', source: '2', target: '3' },
  { id: 'e2-4', source: '2', target: '4' },
  { id: 'e3-5', source: '3', target: '5' },
  { id: 'e4-5', source: '4', target: '5' },
];

// Mock Debug Data
const MOCK_DEBUG_DATA = {
  filesScanned: 54,
  filesParsed: 42,
  filesSkipped: 12,
  parseFailures: 2,
  nodesCreated: 28,
  edgesCreated: 24,
  analysisTime: 18.4,
  extractionLogs: [
    '[SQL] Extracted 3 tables, 15 columns from schema.sql',
    '[Python] Found 8 routes, 12 imports in auth_service.py',
    '[TypeScript] Parsed 5 components, 7 API calls from LoginPage.tsx',
    '[Graph] Built 28 nodes across 4 layers',
    '[Impact] Calculated risk scores for all nodes',
  ],
};

function App() {
  const [isUploaded, setIsUploaded] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [nodes] = useState<Node[]>(MOCK_NODES);
  const [edges] = useState<Edge[]>(MOCK_EDGES);
  const [impactedNodeIds, setImpactedNodeIds] = useState<string[]>([]);
  const [suggestions, setSuggestions] = useState<Array<{ target: string; suggestion: string }>>([]);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [isDocumentationOpen, setIsDocumentationOpen] = useState(false);
  const [isDebugMode, setIsDebugMode] = useState(false);

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    try {
      const data = await uploadRepo(file);
      setAnalysisId(data.analysis_id);
      setIsUploaded(true);
      // In a real app, we would then fetch the graph
    } catch (error) {
      console.error("Upload failed", error);
    } finally {
      setIsUploading(false);
    }
  };

  const handleNodeClick = async (node: Node) => {
    // Simulate impact analysis for demo if no real backend
    if (analysisId) {
        const result = await analyzeImpact(analysisId, node.id);
        setImpactedNodeIds(result.impacted_nodes || [node.id]);
    } else {
        // Local simulation for demo
        setImpactedNodeIds([node.id, '2', '3', '5']); 
    }
  };

  return (
    <div className="min-h-screen bg-dark-900 text-slate-100 font-inter selection:bg-brand-500/30">
      {/* Header */}
      <nav className="border-b border-white/5 bg-dark-800/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-[1600px] mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center">
              <Layers className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl tracking-tight">Polyglot<span className="text-brand-500 font-black">Analyzer</span></span>
          </div>
          
          <div className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-400">
            <button onClick={() => setIsDocumentationOpen(true)} className="hover:text-white transition-colors">
              Documentation
            </button>
            <div className="h-4 w-px bg-white/10" />
            <button
              onClick={() => setIsDebugMode(!isDebugMode)}
              className={`px-4 py-1.5 rounded-full border transition-all ${
                isDebugMode
                  ? 'bg-red-500/20 border-red-500/50 text-red-400'
                  : 'bg-white/5 hover:bg-white/10 border-white/10 text-white'
              }`}
            >
              Dev Mode {isDebugMode && '✓'}
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-[1600px] mx-auto p-6 space-y-8">
        {!isUploaded ? (
          <div className="max-w-3xl mx-auto pt-20">
            <div className="text-center mb-12 animate-fade-in">
              <h1 className="text-5xl font-black mb-4 tracking-tight">
                Trace Code Impact <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-indigo-400">Across Every Layer</span>
              </h1>
              <p className="text-slate-400 text-lg">
                Upload your repository and visualize how changes propagate from SQL columns to React components.
              </p>
            </div>
            <UploadZone onUpload={handleUpload} isUploading={isUploading} />
          </div>
        ) : (
          <div className="space-y-8 animate-fade-in">
            <AnalysisSummary 
              filesParsed={42} 
              filesSkipped={12} 
              nodesCount={28} 
              edgesCount={24} 
            />

            <div className="grid grid-cols-12 gap-8 h-[700px]">
              {/* Sidebar Panel */}
              <div className="col-span-12 lg:col-span-3 flex flex-col gap-6">
                <div className="glass p-6 rounded-2xl flex-1 flex flex-col">
                  <div className="flex items-center gap-3 mb-6 text-brand-500">
                    <ShieldAlert className="w-6 h-6" />
                    <h2 className="font-bold uppercase tracking-widest text-sm">Action Center</h2>
                  </div>

                  <div className="space-y-4 flex-1">
                    <div className="p-4 rounded-xl bg-white/5 border border-white/5">
                        <p className="text-xs text-slate-500 uppercase font-black mb-2">Simulate Change</p>
                        <p className="text-sm text-slate-300 mb-4">Click any node in the graph to see propagation impact.</p>
                        <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                            <div className="h-full bg-brand-500 w-1/3" />
                        </div>
                    </div>

                    <div className="p-4 rounded-xl bg-brand-500/10 border border-brand-500/20">
                        <p className="text-xs text-brand-500 uppercase font-black mb-1">Risk Score</p>
                        <p className="text-3xl font-black">{impactedNodeIds.length > 0 ? (impactedNodeIds.length > 5 ? '8.5' : '4.2') : '0.0'}</p>
                        <p className="text-xs text-slate-400 mt-1">Severity: <span className="text-amber-500 font-bold">MEDIUM</span></p>
                    </div>
                  </div>

                  <div className="mt-auto space-y-4">
                    <div className="relative">
                        <input
                            placeholder="Ask about dependencies..."
                            className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-11 pr-4 text-sm focus:border-brand-500/50 outline-none transition-all"
                        />
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                        <button className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-brand-500 rounded-lg">
                            <Send className="w-3.5 h-3.5" />
                        </button>
                    </div>
                    <button onClick={() => setIsUploaded(false)} className="w-full py-2.5 text-xs font-bold uppercase tracking-widest text-slate-500 hover:text-white transition-colors">
                        Re-upload Repo
                    </button>
                  </div>
                </div>
              </div>

              {/* Graph Area */}
              <div className="col-span-12 lg:col-span-9 h-full">
                <DependencyGraph
                  nodes={nodes}
                  edges={edges}
                  onNodeClick={handleNodeClick}
                  impactedNodeIds={impactedNodeIds}
                />
              </div>
            </div>

            {/* Suggested Fixes Section */}
            <div className="max-w-4xl mx-auto">
              <SuggestedFixes suggestions={suggestions} isLoading={isLoadingSuggestions} />
            </div>
          </div>
        )}
      </main>

      {/* Background Decor */}
      <div className="fixed top-0 left-0 w-full h-full -z-10 pointer-events-none opacity-20">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-brand-500 blur-[120px] rounded-full" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] bg-indigo-500 blur-[100px] rounded-full" />
      </div>

      {/* Documentation Modal */}
      <DocumentationModal isOpen={isDocumentationOpen} onClose={() => setIsDocumentationOpen(false)} />

      {/* Debug Panel */}
      {isUploaded && <DebugPanel isOpen={isDebugMode} debugData={MOCK_DEBUG_DATA} />}
    </div>
  );
}

export default App;

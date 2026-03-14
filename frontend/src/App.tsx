import { useState } from 'react';
import { UploadZone } from './components/UploadZone';
import { AnalysisSummary } from './components/AnalysisSummary';
import { SuggestedFixes } from './components/SuggestedFixes';
import { DocumentationModal } from './components/DocumentationModal';
import { DebugPanel } from './components/DebugPanel';
import { DependencyGraph } from './graph/DependencyGraph';
import GooeyNav from './components/GooeyNav';
import ClickSpark from './components/ClickSpark';
import GradientText from './components/GradientText';
import { Search, Send, ShieldAlert, Layers } from 'lucide-react';
import { uploadRepo, analyzeImpact, getGraph, queryNL } from './api/client';
import { ReactFlowProvider, type Node, type Edge } from 'reactflow';

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
  const [nodes, setNodes] = useState<Node[]>(MOCK_NODES);
  const [edges, setEdges] = useState<Edge[]>(MOCK_EDGES);
  const [impactedNodeIds, setImpactedNodeIds] = useState<string[]>([]);
  const [suggestions, setSuggestions] = useState<Array<{ target: string; suggestion: string }>>([]);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [isDocumentationOpen, setIsDocumentationOpen] = useState(false);
  const [isDebugMode, setIsDebugMode] = useState(false);
  const [filesParsed, setFilesParsed] = useState(0);
  const [filesSkipped, setFilesSkipped] = useState(0);
  const [nodesCount, setNodesCount] = useState(0);
  const [edgesCount, setEdgesCount] = useState(0);
  const [queryInput, setQueryInput] = useState('');
  const [queryResult, setQueryResult] = useState<string | null>(null);
  const [isQueryLoading, setIsQueryLoading] = useState(false);

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    try {
      const uploadData = await uploadRepo(file);
      const id = uploadData.analysis_id;
      setAnalysisId(id);
      setFilesParsed(uploadData.files_parsed || 0);
      setFilesSkipped(uploadData.files_skipped || 0);

      // Fetch the graph
      const graphData = await getGraph(id);
      console.log('Raw graph data:', graphData); // Debug log
      if (graphData.nodes) {
        console.log('Setting nodes:', graphData.nodes.length); // Debug log
        setNodes(graphData.nodes);
      }
      if (graphData.edges) setEdges(graphData.edges);
      setNodesCount(graphData.summary?.nodes || 0);
      setEdgesCount(graphData.summary?.edges || 0);

      setIsUploaded(true);
    } catch (error) {
      console.error("Upload failed", error);
      alert("Upload failed. Check console for errors.");
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

  const handleQuerySubmit = async () => {
    if (!queryInput.trim() || !analysisId) return;

    setIsQueryLoading(true);
    const question = queryInput.trim();
    setQueryInput(''); // Clear input immediately

    try {
      const result = await queryNL(analysisId, question);
      setQueryResult(result.answer);
      // Optionally highlight matched nodes
      if (result.matched_nodes && result.matched_nodes.length > 0) {
        setImpactedNodeIds(result.matched_nodes);
      }
    } catch (error) {
      console.error('Query failed:', error);
      setQueryResult('Sorry, I encountered an error processing your question.');
    } finally {
      setIsQueryLoading(false);
    }
  };

  const handleQueryKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleQuerySubmit();
    }
  };

  return (
    <ClickSpark sparkColor="#6366f1" sparkSize={10} sparkRadius={15} sparkCount={8} duration={400}>
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

          <div className="hidden md:flex">
            <GooeyNav
              items={[
                {
                  label: 'Documentation',
                  onClick: () => setIsDocumentationOpen(true),
                  type: 'button'
                },
                {
                  label: `Dev Mode ${isDebugMode ? '✓' : ''}`,
                  onClick: () => { if (isUploaded) setIsDebugMode(!isDebugMode); },
                  type: 'button',
                  isActive: isDebugMode,
                  disabled: !isUploaded
                }
              ]}
              particleCount={12}
              particleDistances={[70, 10]}
              particleR={80}
              animationTime={500}
              timeVariance={200}
            />
          </div>
        </div>
      </nav>

      <main className="max-w-[1600px] mx-auto p-6 space-y-8">
        {!isUploaded ? (
          <div className="max-w-3xl mx-auto pt-20">
            <div className="text-center mb-12 animate-fade-in">
              <h1 className="text-5xl font-black mb-4 tracking-tight">
                Trace Code Impact <br />
                <GradientText
                  colors={["#6366f1", "#ec4899", "#a855f7", "#3b82f6"]}
                  animationSpeed={3}
                  className="text-5xl font-black"
                >
                  Across Every Layer
                </GradientText>
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
              filesParsed={filesParsed}
              filesSkipped={filesSkipped}
              nodesCount={nodesCount}
              edgesCount={edgesCount}
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
                            value={queryInput}
                            onChange={(e) => setQueryInput(e.target.value)}
                            onKeyPress={handleQueryKeyPress}
                            placeholder="Ask about dependencies..."
                            className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-11 pr-4 text-sm focus:border-brand-500/50 outline-none transition-all"
                            disabled={!analysisId || isQueryLoading}
                        />
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                        <button
                          onClick={handleQuerySubmit}
                          disabled={!queryInput.trim() || !analysisId || isQueryLoading}
                          className={`absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-brand-500 rounded-lg transition-opacity ${
                            !queryInput.trim() || !analysisId || isQueryLoading ? 'opacity-50 cursor-not-allowed' : 'hover:bg-brand-600'
                          }`}
                        >
                            <Send className="w-3.5 h-3.5" />
                        </button>
                    </div>
                    {queryResult && (
                      <div className="bg-white/5 border border-white/10 rounded-xl p-3 text-sm">
                        <p className="text-brand-400 text-xs uppercase font-bold mb-1">Answer:</p>
                        <p className="text-slate-300">{queryResult}</p>
                      </div>
                    )}
                    <button onClick={() => setIsUploaded(false)} className="w-full py-2.5 text-xs font-bold uppercase tracking-widest text-slate-500 hover:text-white transition-colors">
                        Re-upload Repo
                    </button>
                  </div>
                </div>
              </div>

              {/* Graph Area */}
              <div className="col-span-12 lg:col-span-9 h-full">
                <ReactFlowProvider>
                  <DependencyGraph
                    nodes={nodes}
                    edges={edges}
                    onNodeClick={handleNodeClick}
                    impactedNodeIds={impactedNodeIds}
                  />
                </ReactFlowProvider>
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
    </ClickSpark>
  );
}

export default App;

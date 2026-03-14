import { useState, useEffect } from 'react';
import { UploadZone } from './components/UploadZone';
import { SuggestedFixes } from './components/SuggestedFixes';
import { DocumentationModal } from './components/DocumentationModal';
import { DebugPanel } from './components/DebugPanel';
import { DependencyGraph } from './graph/DependencyGraph';
import GooeyNav from './components/GooeyNav';
import ClickSpark from './components/ClickSpark';
import GradientText from './components/GradientText';
import { Search, ShieldAlert, Layers, Loader2, Sparkles } from 'lucide-react';
import { uploadRepo, analyzeImpact, getGraph, queryNL, suggestFix, fetchConfig } from './api/client';
import { ReactFlowProvider, type Node, type Edge } from 'reactflow';
import ErrorBoundary from './components/ErrorBoundary';


// Initial Mock Data for UI Testing
const MOCK_NODES: Node[] = [];
const MOCK_EDGES: Edge[] = [];

interface SystemConfig {
  debug_mode_default: boolean;
  featherless_api_status: string;
  neo4j_status: string;
}

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
  const [isDebugMode, setIsDebugMode] = useState(() => {
    return localStorage.getItem('isDebugMode') === 'true';
  });
  const [systemConfig, setSystemConfig] = useState<SystemConfig | null>(null);

  useEffect(() => {
    fetchConfig()
      .then((config) => {
        setSystemConfig(config);
        if (!localStorage.getItem('isDebugMode')) {
          setIsDebugMode(config.debug_mode_default);
        }
      })
      .catch((err) => {
        console.error("Failed to fetch system config", err);
      });
  }, []);


  /* Statistics used by the Debug Dashboard */
  const [filesParsed, setFilesParsed] = useState(0);
  const [filesSkipped, setFilesSkipped] = useState(0);
  const [queryInput, setQueryInput] = useState('');
  const [queryResult, setQueryResult] = useState<string | null>(null);
  const [isQueryLoading, setIsQueryLoading] = useState(false);
  const [pipelineLogs, setPipelineLogs] = useState<string[]>([]);
  const [lastImpactResult, setLastImpactResult] = useState<{ node_id: string; impacted_nodes: string[]; risk_score: number; severity: 'LOW' | 'MEDIUM' | 'HIGH' } | null>(null);

  const addPipelineLog = (message: string) => {
    setPipelineLogs((prev: string[]) => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`]);
  };

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    setPipelineLogs([]);
    addPipelineLog('ZIP uploaded successfully');
    try {
      const uploadData = await uploadRepo(file);
      const id = uploadData.analysis_id;
      setAnalysisId(id);
      setFilesParsed(uploadData.files_parsed || 0);
      setFilesSkipped(uploadData.files_skipped || 0);
      addPipelineLog(`Files ingested: ${uploadData.files_parsed} parsed, ${uploadData.files_skipped} skipped`);

      // Fetch the graph
      const graphData = await getGraph(id);
      if (graphData.nodes) {
        setNodes(graphData.nodes);
      }
      if (graphData.edges) setEdges(graphData.edges);
      addPipelineLog(`Graph built: ${graphData.summary?.nodes || 0} nodes, ${graphData.summary?.edges || 0} edges`);

      setIsUploaded(true);
    } catch (error) {
      console.error("Upload failed", error);
      addPipelineLog('❌ Upload failed - See console for details');
      alert("Upload failed. Check console for errors.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleNodeClick = async (node: Node) => {
    if (analysisId) {
        setImpactedNodeIds([node.id]); // Visual feedback
        setIsLoadingSuggestions(true);
        addPipelineLog(`Impact analysis run on: ${node.id}`);
        try {
            const impactResult = await analyzeImpact(analysisId, node.id);
            setImpactedNodeIds(impactResult.impacted_nodes || [node.id]);
            
            // Store impact result for debug panel
            setLastImpactResult({
              node_id: node.id,
              impacted_nodes: impactResult.impacted_nodes || [],
              risk_score: impactResult.risk_score || 0,
              severity: (impactResult.severity || 'LOW') as 'LOW' | 'MEDIUM' | 'HIGH'
            });
            
            const fixResult = await suggestFix(analysisId, node.id, "Impact Analysis");
            const mappedFixes = fixResult.suggestions.map((s: string) => ({
                target: node.data?.label || 'Target Node',
                suggestion: s
            }));
            setSuggestions(mappedFixes);
            addPipelineLog(`Found ${impactResult.impacted_nodes?.length || 1} impacted nodes (severity: ${impactResult.severity || 'LOW'})`);
        } catch (error) {
            console.error("Analysis failed", error);
            addPipelineLog('❌ Impact analysis failed');
        } finally {
            setIsLoadingSuggestions(false);
        }
    } else {
        setImpactedNodeIds([node.id, '2', '3', '5']);
    }
  };

  const handleQuerySubmit = async () => {
    if (!queryInput.trim() || !analysisId) return;

    setIsQueryLoading(true);
    const question = queryInput.trim();
    setQueryInput(''); // Clear input immediately
    try {
      setQueryResult(null); // Clear previous results while loading
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


  return (
    <ErrorBoundary>
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
                  onClick: () => { 
                    if (isUploaded) {
                      const newMode = !isDebugMode;
                      setIsDebugMode(newMode);
                      localStorage.setItem('isDebugMode', String(newMode));
                    } 
                  },
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

      <main className="max-w-[1600px] mx-auto p-6 space-y-8 pb-32">
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
            {/* Data summary is now handled by the Debug Dashboard */}
            <div className="space-y-8">
              {/* Full Width Graph Area */}
              <div className="w-full h-[600px] glass rounded-3xl overflow-hidden border border-white/10">
                <ReactFlowProvider>
                  <DependencyGraph
                    nodes={nodes}
                    edges={edges}
                    onNodeClick={handleNodeClick}
                    impactedNodeIds={impactedNodeIds}
                  />
                </ReactFlowProvider>
              </div>

              {/* Bottom Split Section */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-stretch">
                {/* Section A: Action Center */}
                <div className="glass p-6 rounded-2xl flex flex-col border border-white/10 relative overflow-hidden h-full">
                  <div className="absolute -top-10 -right-10 w-32 h-32 bg-brand-500/10 blur-[60px] rounded-full animate-pulse" />
                  
                  <div className="flex items-center gap-3 mb-8 text-brand-400">
                    <div className="p-2 rounded-lg bg-brand-500/10 border border-brand-500/20">
                      <ShieldAlert className="w-5 h-5" />
                    </div>
                    <div>
                      <h2 className="font-black uppercase tracking-[0.2em] text-[10px] text-slate-500">Security Node</h2>
                      <h3 className="font-bold text-sm text-slate-100">Action Center</h3>
                    </div>
                  </div>

                  <div className="space-y-6 flex-1">
                    <div className="p-6 rounded-2xl bg-gradient-to-br from-brand-500/10 to-indigo-500/5 border border-brand-500/20 shadow-2xl shadow-brand-500/5">
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <p className="text-[10px] text-slate-500 uppercase font-black tracking-widest mb-1">Threat Assessment</p>
                          <div className="flex items-center gap-2">
                            <span className={`text-3xl font-black tracking-tighter ${impactedNodeIds.length > 2 ? (impactedNodeIds.length > 10 ? 'text-red-500' : 'text-amber-500') : 'text-slate-500'}`}>
                              {impactedNodeIds.length > 0 ? (Math.min(10, (impactedNodeIds.length * 0.5)).toFixed(1)) : '0.0'}
                            </span>
                            <span className="text-xs text-slate-600 font-bold">/ 10</span>
                          </div>
                        </div>
                        <div className={`px-2 py-1 rounded-md text-[8px] font-black tracking-widest ${impactedNodeIds.length > 2 ? (impactedNodeIds.length > 10 ? 'bg-red-500/20 text-red-500 border border-red-500/30' : 'bg-amber-500/20 text-amber-500 border border-amber-500/30') : 'bg-slate-800 text-slate-500 border border-slate-700'}`}>
                          {impactedNodeIds.length > 10 ? 'CRITICAL' : (impactedNodeIds.length > 2 ? 'ELEVATED' : 'STABLE')}
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4 mt-6">
                        <div className="bg-black/20 p-3 rounded-xl border border-white/5">
                          <p className="text-[9px] text-slate-500 font-black uppercase mb-1">Blast Radius</p>
                          <p className="text-xl font-bold text-slate-200">{impactedNodeIds.length} <span className="text-[10px] text-slate-500 font-normal">nodes</span></p>
                        </div>
                        <div className="bg-black/20 p-3 rounded-xl border border-white/5">
                          <p className="text-[9px] text-slate-500 font-black uppercase mb-1">System Health</p>
                          <p className="text-[10px] font-bold text-emerald-500 uppercase flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> Live Sync
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-8 space-y-4">
                    <div className="relative group">
                      <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none transition-colors group-focus-within:text-brand-500">
                        <Search className="w-4 h-4 text-slate-500" />
                      </div>
                      <textarea
                        value={queryInput}
                        onChange={(e) => setQueryInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleQuerySubmit();
                          }
                        }}
                        placeholder="Neural Search Dependency... (e.g. 'What happens if I remove index.html?')"
                        className="w-full bg-white/5 border border-white/10 rounded-xl py-4 pl-12 pr-12 text-sm focus:border-brand-500/50 focus:bg-white/[0.08] outline-none transition-all placeholder:text-slate-600 resize-none h-20"
                        disabled={!analysisId || isQueryLoading}
                      />
                      <button
                        onClick={handleQuerySubmit}
                        disabled={!queryInput.trim() || !analysisId || isQueryLoading}
                        className={`absolute right-3 bottom-3 px-3 py-2 bg-brand-500 text-white text-[10px] font-black uppercase tracking-widest rounded-lg transition-all flex items-center gap-2 ${
                          !queryInput.trim() || !analysisId || isQueryLoading ? 'opacity-30 grayscale cursor-not-allowed' : 'hover:bg-brand-600 hover:scale-105 active:scale-95 shadow-lg shadow-brand-500/20'
                        }`}
                      >
                        {isQueryLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
                        {isQueryLoading ? 'Thinking' : 'Query'}
                      </button>
                    </div>
                      {isQueryLoading && (
                        <div className="bg-brand-500/5 border border-brand-500/20 rounded-xl p-4 text-sm animate-pulse">
                          <div className="flex items-center gap-2 mb-2">
                             <div className="w-1 h-3 bg-brand-500 rounded-full animate-bounce" />
                             <p className="text-brand-400 text-[10px] uppercase font-black tracking-widest">Architect Brain Processing</p>
                          </div>
                          <p className="text-slate-500 leading-relaxed text-xs italic">Consulting architectural graph and Featherless AI...</p>
                        </div>
                      )}
                      {queryResult && !isQueryLoading && (
                        <div className="bg-brand-500/5 border border-brand-500/20 rounded-xl p-4 text-sm animate-in fade-in slide-in-from-top-2">
                          <div className="flex items-center gap-2 mb-2">
                             <div className="w-1 h-3 bg-brand-500 rounded-full" />
                             <p className="text-brand-400 text-[10px] uppercase font-black tracking-widest">Intelligence Output</p>
                          </div>
                          <p className="text-slate-300 leading-relaxed text-xs whitespace-pre-wrap">{queryResult}</p>
                        </div>
                      )}
                    <button 
                      onClick={() => setIsUploaded(false)} 
                      className="w-full py-3 text-[10px] font-black uppercase tracking-[0.3em] text-slate-500 hover:text-white hover:bg-white/5 rounded-xl transition-all border border-transparent hover:border-white/5"
                    >
                      New Architecture
                    </button>
                  </div>
                </div>

                {/* Section B: Suggestion Box */}
                <div className="glass p-6 rounded-2xl flex flex-col border border-white/10 relative overflow-hidden h-full">                  <div className="absolute -top-10 -right-10 w-32 h-32 bg-indigo-500/10 blur-[60px] rounded-full animate-pulse" />
                  
                  <div className="flex items-center gap-3 mb-8 text-indigo-400">
                    <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
                      <Sparkles className="w-5 h-5" />
                    </div>
                    <div>
                      <h2 className="font-black uppercase tracking-[0.2em] text-[10px] text-slate-500">Architect Advice</h2>
                      <h3 className="font-bold text-sm text-slate-100">Suggested Fixes</h3>
                    </div>
                  </div>

                  <div className="flex-1 overflow-auto">
                    <SuggestedFixes suggestions={suggestions} isLoading={isLoadingSuggestions} />
                  </div>
                </div>
              </div>
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
      {isUploaded && (
        <DebugPanel
          isOpen={isDebugMode}
          analysisId={analysisId}
          filesParsed={filesParsed}
          filesSkipped={filesSkipped}
          nodes={nodes}
          edges={edges}
          lastImpactResult={lastImpactResult || undefined}
          pipelineLogs={pipelineLogs}
          systemConfig={systemConfig}
        />
      )}
    </div>
    </ClickSpark>
    </ErrorBoundary>
  );
}



export default App;

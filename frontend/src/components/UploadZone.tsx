import React, { useState } from 'react';
import { Upload, CheckCircle, Loader2, ArrowRight, Github, Key } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface UploadZoneProps {
  onUpload: (file: File) => Promise<void>;
  onGithubAnalyze?: (data: {
    analysisId: string;
    nodes: any[];
    edges: any[];
    repoMeta: any;
    filesParsed: number;
    filesSkipped: number;
    githubToken: string;
  }) => Promise<void>;
  isUploading: boolean;
}

export const UploadZone: React.FC<UploadZoneProps> = ({ onUpload, onGithubAnalyze, isUploading }) => {
  const [isDragActive, setIsDragActive] = useState(false);
  const [githubUrl, setGithubUrl] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [loadingStep, setLoadingStep] = useState('');
  const [error, setError] = useState('');

  const handleGithubAnalyze = async () => {
    // Validate URL
    if (!githubUrl.includes('github.com')) {
      setError('Please enter a valid GitHub URL');
      return;
    }

    if (!onGithubAnalyze) {
      setError('GitHub analysis is not configured');
      return;
    }

    setError('');

    try {
      // Progressive loading states
      const steps = [
        'Connecting to GitHub...',
        'Fetching repository files...',
        'Analyzing dependencies...',
        'Building knowledge graph...'
      ];

      let currentStep = 0;
      setLoadingStep(steps[0]);

      const stepInterval = setInterval(() => {
        currentStep++;
        if (currentStep < steps.length) {
          setLoadingStep(steps[currentStep]);
        }
      }, 2000);

      // Call github-analyzer backend with timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000);

      const response = await fetch('http://localhost:8001/api/analyze-github', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          github_url: githubUrl,
          github_token: githubToken || null
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);
      clearInterval(stepInterval);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to analyze repository' }));
        const status = response.status;
        if (status === 403) throw new Error('Repository is private. Add a GitHub token with repo access.');
        if (status === 404) throw new Error('Repository not found. Check the URL and try again.');
        throw new Error(errorData.detail || errorData.error || `Server error: ${status}`);
      }

      const data = await response.json();

      // Transform nodes
      const transformedNodes = data.nodes.map((n: any) => ({
        id: n.id,
        type: 'customNode',
        position: { x: 0, y: 0 },
        data: {
          label: n.name,
          layer: n.layer,
          path: n.path,
          lines: n.lines || 0,
          source: 'github'
        }
      }));

      // Transform edges
      const transformedEdges = data.edges.map((e: any, i: number) => ({
        id: `e-${i}`,
        source: e.source,
        target: e.target,
        animated: true,
        style: { stroke: '#6366f1' }
      }));

      // Call parent callback with transformed data
      await onGithubAnalyze({
        analysisId: data.analysis_id, // Use ID from backend
        nodes: transformedNodes,
        edges: transformedEdges,
        repoMeta: { ...data.repo_meta, analysis_id: data.analysis_id }, // Ensure it's in meta for query
        filesParsed: data.nodes.length,
        filesSkipped: 0,
        githubToken: githubToken
      });

      setLoadingStep('');
      setGithubUrl('');
      setGithubToken('');
    } catch (error: any) {
      setLoadingStep('');
      if (error.name === 'AbortError') {
        setError('Taking longer than expected... Try a smaller repository.');
      } else if (error.message === 'Failed to fetch') {
        setError('Cannot connect to GitHub Analyzer backend. Make sure it is running on port 8001.');
      } else {
        setError(`Could not analyze repository: ${error.message || 'Unknown error'}`);
      }
      console.error('GitHub analysis error:', error);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(true);
  };

  const handleDragLeave = () => {
    setIsDragActive(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file && (file.type === 'application/x-zip-compressed' || file.type === 'application/zip' || file.name.endsWith('.zip'))) {
      if (file.size > 40 * 1024 * 1024) {
        alert('File size exceeds 40MB limit. Please upload a smaller repository.');
        return;
      }
      await onUpload(file);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 40 * 1024 * 1024) {
        alert('File size exceeds 40MB limit. Please upload a smaller repository.');
        return;
      }
      await onUpload(file);
    }
  };

  return (
    <>
      <div
        className={cn(
          "relative group cursor-pointer transition-all duration-300 rounded-2xl border-2 border-dashed p-12 text-center",
          isDragActive ? "border-brand-500 bg-brand-500/10" : "border-white/10 hover:border-white/20 hover:bg-white/5",
          isUploading && "pointer-events-none opacity-60"
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => document.getElementById('file-upload')?.click()}
      >
      <input
        type="file"
        id="file-upload"
        className="hidden"
        accept=".zip"
        onChange={handleFileChange}
      />
      <div className="flex flex-col items-center">
        <div className={cn(
          "mb-6 p-4 rounded-full transition-transform duration-300",
          isDragActive ? "scale-110 bg-brand-500 text-white" : "bg-white/5 text-white/40 group-hover:text-white group-hover:scale-110"
        )}>
          {isUploading ? <Loader2 className="w-10 h-10 animate-spin" /> : <Upload className="w-10 h-10" />}
        </div>
        <h3 className="text-xl font-semibold mb-2">
          {isUploading ? "Analyzing Repository..." : "Upload Repository ZIP"}
        </h3>
        <p className="text-slate-400 max-w-xs mx-auto">
          Drag and drop your project ZIP or click to browse. Max size 40MB.
        </p>
        
        <div className="mt-8 flex gap-4 text-xs font-medium text-slate-500 uppercase tracking-widest">
            <span className="flex items-center gap-1.5"><CheckCircle className="w-3 h-3 text-emerald-500" /> SQL</span>
            <span className="flex items-center gap-1.5"><CheckCircle className="w-3 h-3 text-emerald-500" /> Python</span>
            <span className="flex items-center gap-1.5"><CheckCircle className="w-3 h-3 text-emerald-500" /> JS/TS</span>
        </div>
      </div>
      
      {/* Decorative corners */}
      <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-brand-500/20 rounded-tl-2xl" />
      <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-brand-500/20 rounded-br-2xl" />
    </div>

    {/* OR Divider */}
    <div className="relative my-8">
      <div className="absolute inset-0 flex items-center">
        <div className="w-full border-t border-white/10"></div>
      </div>
      <div className="relative flex justify-center text-sm">
        <span className="px-4 bg-dark-900 text-slate-400 font-medium">OR</span>
      </div>
    </div>

    {/* GitHub URL Section */}
    <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm p-8">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-lg bg-brand-500/10">
          <Github className="w-5 h-5 text-brand-500" />
        </div>
        <h3 className="text-lg font-semibold">Analyze from GitHub</h3>
      </div>

      <div className="space-y-4">
        {/* GitHub URL Input */}
        <div>
          <label htmlFor="github-url" className="block text-sm font-medium text-slate-300 mb-2">
            Repository URL
          </label>
          <div className="relative">
            <input
              type="text"
              id="github-url"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              placeholder="github.com/owner/repo"
              className="w-full px-4 py-3 bg-dark-800/50 border border-white/10 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all"
              disabled={isUploading}
            />
          </div>
        </div>

        {/* GitHub Token Input */}
        <div>
          <label htmlFor="github-token" className="block text-sm font-medium text-slate-300 mb-2">
            GitHub Token (optional)
          </label>
          <div className="relative">
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
              <Key className="w-4 h-4" />
            </div>
            <input
              type="password"
              id="github-token"
              value={githubToken}
              onChange={(e) => setGithubToken(e.target.value)}
              placeholder="ghp_••••••••••••••••"
              className="w-full pl-10 pr-4 py-3 bg-dark-800/50 border border-white/10 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent transition-all"
              disabled={isUploading}
            />
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Required for PR creation. Never stored on our servers.
          </p>
        </div>

        {/* Analyze Button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleGithubAnalyze();
          }}
          disabled={!githubUrl.trim() || isUploading}
          className={cn(
            "w-full flex items-center justify-center gap-2 px-6 py-3 rounded-lg font-medium transition-all duration-300",
            !githubUrl.trim() || isUploading
              ? "bg-slate-700 text-slate-500 cursor-not-allowed"
              : "bg-brand-500 hover:bg-brand-600 text-white shadow-lg shadow-brand-500/25 hover:shadow-brand-500/40"
          )}
        >
          {isUploading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              {loadingStep || 'Analyzing...'}
            </>
          ) : (
            <>
              Analyze Repository
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>

        {/* Error Message */}
        {error && (
          <div className="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p className="text-red-400 text-sm mb-3">{error}</p>
            <button
              onClick={() => {
                setError('');
                handleGithubAnalyze();
              }}
              className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-300 text-sm rounded-lg transition-all"
            >
              Retry
            </button>
          </div>
        )}
      </div>
    </div>
    </>
  );
};

import { Lightbulb } from 'lucide-react';

interface Suggestion {
  target: string;
  suggestion: string;
}

interface SuggestedFixesProps {
  suggestions: Suggestion[];
  isLoading: boolean;
}

export const SuggestedFixes: React.FC<SuggestedFixesProps> = ({ suggestions, isLoading }) => {
  if (isLoading) {
    return (
      <div className="glass p-6 rounded-2xl">
        <div className="flex items-center gap-3 mb-4">
          <Lightbulb className="w-5 h-5 text-amber-500" />
          <h3 className="font-bold text-sm uppercase tracking-widest">Suggested Fixes</h3>
        </div>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500"></div>
        </div>
      </div>
    );
  }

  if (suggestions.length === 0) {
    return (
      <div className="glass p-6 rounded-2xl h-full flex flex-col items-center justify-center text-center">
        <h3 className="font-bold text-sm uppercase tracking-widest mb-4 opacity-50">Suggested Fixes</h3>
        <p className="text-sm text-slate-400">
          Click any node in the graph to see AI-powered fix suggestions for that file
        </p>
      </div>
    );
  }

  return (
    <div className="glass p-6 rounded-2xl">
      <div className="flex items-center gap-3 mb-4">
        <Lightbulb className="w-5 h-5 text-amber-500" />
        <h3 className="font-bold text-sm uppercase tracking-widest">Suggested Fixes</h3>
      </div>
      <div className="space-y-3">
        {suggestions.map((suggestion, index) => (
          <div
            key={index}
            className="p-4 rounded-xl bg-white/5 border border-white/10 hover:border-amber-500/30 transition-colors"
          >
            <div className="flex flex-col">
              <p className="text-xs font-bold text-amber-500 mb-1">{suggestion.target}</p>
              <p className="text-sm text-slate-300">{suggestion.suggestion}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

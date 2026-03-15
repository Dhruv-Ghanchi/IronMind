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
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  if (suggestions.length === 0) {
    return (
      <div className="py-8 flex flex-col items-center justify-center text-center">
        <div className="p-3 rounded-full bg-white/5 mb-4">
          <Lightbulb className="w-6 h-6 text-slate-600 opacity-50" />
        </div>
        <p className="text-sm text-slate-400">
          Click any node in the graph to see AI-powered fix suggestions for that file
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3 pb-4">
      {suggestions.map((suggestion, index) => (
        <div
          key={index}
          className="p-4 rounded-xl bg-white/5 border border-white/5 hover:border-indigo-500/20 transition-all group"
        >
          <div className="flex flex-col">
            <p className="text-[10px] font-black text-indigo-400 mb-1 uppercase tracking-widest">{suggestion.target}</p>
            <p className="text-xs text-slate-400 leading-relaxed">{suggestion.suggestion}</p>
          </div>
        </div>
      ))}
    </div>
  );
};

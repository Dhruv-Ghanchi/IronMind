import React, { useState, useMemo, useEffect } from 'react';
import { 
  X, Search, ChevronRight, BookOpen
} from 'lucide-react';
import { fetchDocs } from '../api/client';

interface DocumentationModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface NavSection {
  title: string;
  id: string;
  content?: string;
  subsections?: { title: string; id: string; content?: string }[];
}



const LayerBox: React.FC<{ layer: string; description: string; examples: string[] }> = ({ layer, description, examples }) => {
  const colorClasses: Record<string, string> = {
    database: 'bg-blue-500/20 border-blue-500/30 text-blue-300',
    backend: 'bg-teal-500/20 border-teal-500/30 text-teal-300',
    api: 'bg-amber-500/20 border-amber-500/30 text-amber-300',
    frontend: 'bg-purple-500/20 border-purple-500/30 text-purple-300',
  };

  return (
    <div className={`border rounded-lg p-4 ${colorClasses[layer]}`}>
      <h4 className="font-bold text-sm mb-1 capitalize">{layer}</h4>
      <p className="text-xs opacity-75 mb-3">{description}</p>
      <ul className="space-y-1">
        {examples.map((ex, i) => (
          <li key={i} className="text-xs font-mono opacity-60">{ex}</li>
        ))}
      </ul>
    </div>
  );
};

export const DocumentationModal: React.FC<DocumentationModalProps> = ({ isOpen, onClose }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeSection, setActiveSection] = useState('overview');
  const [sections, setSections] = useState<NavSection[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    'getting-started': true,
    'api-reference': true,
    'entity-extraction': true,
  });

  useEffect(() => {
    let active = true;
    if (isOpen && sections.length === 0) {
      fetchDocs()
        .then((data) => {
          if (active) {
            setSections(data);
            setIsLoading(false);
          }
        })
        .catch((err) => {
          console.error("Failed to fetch documentation", err);
          if (active) setIsLoading(false);
        });
    }
    return () => { active = false; };
  }, [isOpen, sections.length, isLoading]);

  const filteredSections = useMemo(() => {
    if (!searchTerm.trim()) return sections;
    const query = searchTerm.toLowerCase();
    return sections.map(section => ({
      ...section,
      subsections: section.subsections?.filter(sub => 
        sub.title.toLowerCase().includes(query) || section.title.toLowerCase().includes(query)
      ) || [],
    })).filter(section => 
      section.title.toLowerCase().includes(query) || (section.subsections && section.subsections.length > 0)
    );
  }, [searchTerm, sections]);

  if (!isOpen) return null;


  return (
    <div className="fixed inset-0 z-50 flex bg-dark-900">
      {/* Close button */}
      <button
        onClick={onClose}
        className="fixed top-6 right-6 z-50 p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
      >
        <X className="w-5 h-5" />
      </button>

      {/* Left Sidebar */}
      <div className="w-[280px] border-r border-white/10 bg-dark-800/40 overflow-y-auto flex flex-col">
        {/* Logo */}
        <div className="sticky top-0 bg-dark-900/80 backdrop-blur-sm p-4 border-b border-white/10">
          <div className="flex items-center gap-2 mb-4">
            <BookOpen className="w-5 h-5 text-brand-500" />
            <span className="font-bold text-sm">Docs</span>
          </div>
          
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2 top-2.5 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-lg py-2 pl-8 pr-3 text-sm placeholder:text-slate-600 focus:border-brand-500/50 focus:bg-white/[0.08] outline-none transition-all"
            />
          </div>
        </div>

        {/* Navigation */}
        <div className="flex-1 overflow-y-auto p-4 space-y-1">
        {isLoading ? (
          <div className="flex items-center justify-center py-10">
            <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : filteredSections.map((section) => (
            <div key={section.id}>
              <button
                onClick={() => {
                  setActiveSection(section.id);
                  if (section.subsections) {
                    setExpandedSections(prev => ({
                      ...prev,
                      [section.id]: !prev[section.id]
                    }));
                  }
                }}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-all flex items-center justify-between ${
                  activeSection === section.id
                    ? 'bg-brand-500/30 text-brand-300 border border-brand-500/30'
                    : 'text-slate-300 hover:text-white hover:bg-white/5'
                }`}
              >
                <span>{section.title}</span>
                {section.subsections && (
                  <ChevronRight className={`w-4 h-4 transition-transform ${expandedSections[section.id] ? 'rotate-90' : ''}`} />
                )}
              </button>

              {section.subsections && expandedSections[section.id] && (
                <div className="pl-2 space-y-1 mt-1">
                  {section.subsections.map((sub) => (
                    <button
                      key={sub.id}
                      onClick={() => setActiveSection(sub.id)}
                      className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-all ${
                        activeSection === sub.id
                          ? 'bg-brand-500/20 text-brand-300'
                          : 'text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {sub.title}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-8 py-12 space-y-12">
          {sections.map(section => {
            // Find if active section is this main section or one of its subsections
            const isActive = activeSection === section.id || section.subsections?.some(s => s.id === activeSection);
            if (!isActive) return null;

            // Find the specific content to show
            const currentItem = activeSection === section.id 
              ? section 
              : section.subsections?.find(s => s.id === activeSection);

            return (
              <div key={section.id} className="space-y-8 animate-fade-in">
                <div className="space-y-4">
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/20 border border-brand-500/30">
                    <span className="w-2 h-2 rounded-full bg-brand-400" />
                    <span className="text-xs text-brand-300 font-bold uppercase tracking-widest">{section.title}</span>
                  </div>
                  <h1 className="text-5xl font-black text-white tracking-tight">
                    {currentItem?.title}
                  </h1>
                  <p className="text-xl text-slate-400 leading-relaxed max-w-3xl">
                    {currentItem?.content}
                  </p>
                </div>

                {/* Additional context based on section */}
                {section.id === 'architecture' && (
                   <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8">
                     <LayerBox 
                        layer="database" 
                        description="Data storage and schema definitions" 
                        examples={['Tables', 'Columns', 'Views']} 
                      />
                     <LayerBox 
                        layer="backend" 
                        description="Server-side logic and business rules" 
                        examples={['Functions', 'Classes', 'Services']} 
                      />
                     <LayerBox 
                        layer="api" 
                        description="HTTP endpoints and data contracts" 
                        examples={['GET /users', 'POST /auth/login']} 
                      />
                     <LayerBox 
                        layer="frontend" 
                        description="User interface and client logic" 
                        examples={['React components', 'Hooks']} 
                      />
                   </div>
                )}
              </div>
            );
          })}

          <div className="border-t border-white/10 pt-8 pb-8 mt-12">
            <p className="text-xs text-slate-500">
              Built for Hackathon 2026 • Polyglot Dependency Impact Analyzer • Zero-Config Implementation
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

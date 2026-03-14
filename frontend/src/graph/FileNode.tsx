import { memo } from 'react';
import { Handle, Position, useStore } from 'reactflow';
import { 
  FileCode, 
  Database, 
  Globe, 
  Terminal, 
  Hash,
  Box,
  Code,
  Share2
} from 'lucide-react';

const layerIcon: Record<string, any> = {
  database: Database,
  backend: Terminal,
  api: Globe,
  frontend: FileCode,
};

const kindIcon: Record<string, any> = {
  class: Box,
  function: Code,
  route: Share2,
};

const layerColor: Record<string, string> = {
  database: '#5361ff',
  backend: '#a3b8ff',
  api: '#10b981',
  frontend: '#8b5cf6',
};

const kindColor: Record<string, string> = {
  class: '#f59e0b',
  function: '#ec4899',
  route: '#10b981',
};

// Zoom selector for performance Optimization
const zoomSelector = (s: any) => s.transform[2];

export const FileNode = memo(({ data, selected }: any) => {
  const zoom = useStore(zoomSelector);
  const isLite = zoom < 0.4; // Performance Hack: Disable effects when zoomed out

  const Icon = kindIcon[data.nodeClass] || layerIcon[data.layer] || FileCode;
  const color = kindColor[data.nodeClass] || layerColor[data.layer] || '#5361ff';
  
  if (isLite) {
    return (
        <div className={`
          relative px-2 py-2 rounded-lg border flex items-center justify-center
          ${selected ? 'border-brand-500' : 'border-white/20'}
          ${data.isImpacted ? 'bg-red-500' : ''}
        `} style={{ width: 180, height: 60, backgroundColor: '#0f172a' }}>
            <div className="w-2 h-2 rounded-full mr-2" style={{ backgroundColor: color }} />
            <span className="text-[10px] text-slate-100 font-bold truncate">{data.label}</span>
            <Handle type="target" position={Position.Left} className="opacity-0" />
            <Handle type="source" position={Position.Right} className="opacity-0" />
        </div>
    );
  }

  return (
    <div className={`
      relative px-4 py-3 rounded-xl border transition-all duration-300
      backdrop-blur-md bg-dark-800/80
      ${selected ? 'border-brand-500 ring-4 ring-brand-500/20' : 'border-white/10 hover:border-white/20'}
      ${data.isImpacted ? 'border-red-500 ring-4 ring-red-500/40 bg-red-900/40 scale-110 z-50' : ''}
      group min-w-[180px]
    `}>
      {/* Glow Effect */}
      <div 
        className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-10 transition-opacity"
        style={{ backgroundColor: color, filter: 'blur(20px)' }}
      />
      
      <div className="flex items-center gap-3 relative z-10">
        <div 
          className="p-2 rounded-lg bg-white/5"
          style={{ color: color }}
        >
          <Icon size={18} />
        </div>
        
        <div className="flex flex-col">
          <span className="text-xs font-bold text-slate-100 truncate max-w-[120px]">
            {data.label}
          </span>
          <span className="text-[10px] text-slate-500 uppercase font-black tracking-tighter">
            {data.layer}
          </span>
        </div>
      </div>
      
      {data.lines && (
        <div className="mt-2 flex items-center gap-2 text-[9px] text-slate-500 border-t border-white/5 pt-2">
            <span className="flex items-center gap-1">
                <Hash size={10} /> {data.lines} lines
            </span>
        </div>
      )}

      <Handle
        type="target"
        position={Position.Left}
        className="!w-2 !h-2 !bg-slate-600 !border-none"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!w-2 !h-2 !bg-slate-600 !border-none"
      />
    </div>
  );
});

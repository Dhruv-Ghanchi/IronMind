import { memo } from 'react';
import { Handle, Position } from 'reactflow';
import { 
  FileCode, 
  Database, 
  Globe, 
  Terminal, 
  Hash
} from 'lucide-react';

const layerIcon: Record<string, any> = {
  database: Database,
  backend: Terminal,
  api: Globe,
  frontend: FileCode,
};

const layerColor: Record<string, string> = {
  database: '#5361ff',
  backend: '#a3b8ff',
  api: '#10b981',
  frontend: '#8b5cf6',
};

export const FileNode = memo(({ data, selected }: any) => {
  const Icon = layerIcon[data.layer] || FileCode;
  const color = layerColor[data.layer] || '#5361ff';
  
  return (
    <div className={`
      relative px-4 py-3 rounded-xl border transition-all duration-300
      backdrop-blur-md bg-dark-800/80
      ${selected ? 'border-brand-500 ring-2 ring-brand-500/20' : 'border-white/10 hover:border-white/20'}
      ${data.isImpacted ? 'border-red-500/50 bg-red-500/5' : ''}
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

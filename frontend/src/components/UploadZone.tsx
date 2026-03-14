import React, { useState } from 'react';
import { Upload, CheckCircle, Loader2 } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface UploadZoneProps {
  onUpload: (file: File) => Promise<void>;
  isUploading: boolean;
}

export const UploadZone: React.FC<UploadZoneProps> = ({ onUpload, isUploading }) => {
  const [isDragActive, setIsDragActive] = useState(false);

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
  );
};

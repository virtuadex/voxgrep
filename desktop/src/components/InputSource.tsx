import { AppStatus } from "../types";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { listen } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/plugin-dialog";
import { 
  Upload, Cpu, Link, Loader2, 
  FileVideo, FolderOpen, Sparkles, Zap, Check,
  HardDrive, Wifi, AlertTriangle
} from "lucide-react";

interface InputSourceProps {
  url: string;
  setUrl: (url: string) => void;
  useGPU: boolean;
  setUseGPU: (use: boolean) => void;
  status: AppStatus;
  progress: number;
  onDownload: () => void;
}

export function InputSource({
  url,
  setUrl,
  useGPU,
  setUseGPU,
  status,
  progress,
  onDownload,
}: InputSourceProps) {
  const isProcessing = status !== "idle" && status !== "error";
  const [isDragging, setIsDragging] = useState(false);
  const [inputType, setInputType] = useState<'url' | 'file' | null>(null);
  const [showValidation, setShowValidation] = useState(false);

  // Detect input type
  useEffect(() => {
    if (url.startsWith('/') || url.match(/^[A-Za-z]:\\/)) {
      setInputType('file');
    } else if (url.length > 0) {
      setInputType('url');
    } else {
      setInputType(null);
    }
    setShowValidation(false);
  }, [url]);

  useEffect(() => {
    const unlisteners: (() => void)[] = [];

    const setupListeners = async () => {
      const handleDrop = (event: any) => {
        setIsDragging(false);
        const payload = event.payload;
        let paths: string[] = [];
        
        if (Array.isArray(payload)) {
          paths = payload;
        } else if (payload?.paths && Array.isArray(payload.paths)) {
          paths = payload.paths;
        }
        
        if (paths.length > 0) {
          setUrl(paths[0]);
        }
      };

      const handleDragEnter = () => setIsDragging(true);
      const handleDragLeave = () => setIsDragging(false);

      try {
        unlisteners.push(await listen("tauri://drag-drop", handleDrop));
        unlisteners.push(await listen("tauri://drag-enter", handleDragEnter));
        unlisteners.push(await listen("tauri://drag-leave", handleDragLeave));
      } catch (e) {
        console.warn("Failed to register v2 events:", e);
      }

      try {
        unlisteners.push(await listen("tauri://file-drop", handleDrop));
        unlisteners.push(await listen("tauri://file-drop-hover", handleDragEnter));
        unlisteners.push(await listen("tauri://file-drop-cancelled", handleDragLeave));
      } catch (e) {
        console.warn("Failed to register v1 events:", e);
      }
    };

    setupListeners();
    return () => unlisteners.forEach(unlisten => unlisten());
  }, [setUrl]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragging) setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      const file = files[0] as any;
      if (file.path) {
        setUrl(file.path);
      }
    }
  };

  const handleBrowseFiles = async () => {
    try {
      const selected = await open({
        multiple: false,
        filters: [{
          name: 'Video Files',
          extensions: ['mp4', 'mov', 'avi', 'mkv', 'webm', 'flv', 'm4v']
        }]
      });
      
      if (selected) {
        const filePath = typeof selected === 'string' ? selected : selected[0];
        if (filePath) setUrl(filePath);
      }
    } catch (error) {
      console.error("File picker error:", error);
    }
  };

  const handleAnalyze = () => {
    if (!url.trim()) {
      setShowValidation(true);
      return;
    }
    onDownload();
  };

  return (
    <motion.section 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className={`glass-card rounded-xl p-5 relative overflow-hidden transition-all duration-300
        ${isDragging ? "border-accent-primary shadow-glow-primary" : ""}
      `}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drag Overlay */}
      <AnimatePresence>
        {isDragging && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-50 bg-accent-primary/90 backdrop-blur-lg flex flex-col items-center justify-center rounded-xl"
          >
            <motion.div
              animate={{ y: [0, -8, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
            >
              <FileVideo className="w-12 h-12 text-white mb-3" />
            </motion.div>
            <p className="text-lg font-bold text-white">Drop to Analyze</p>
            <p className="text-sm text-white/70 mt-1">MP4, MOV, MKV supported</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Section Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="section-label">
          <Upload className="w-4 h-4 text-accent-primary" />
          Add Video
        </div>
        {inputType && (
          <span className={`badge ${inputType === 'file' ? 'badge-info' : 'badge-warning'}`}>
            {inputType === 'file' ? <HardDrive className="w-3 h-3" /> : <Wifi className="w-3 h-3" />}
            {inputType === 'file' ? 'Local' : 'URL'}
          </span>
        )}
      </div>

      {/* URL/Path Input */}
      <div className="space-y-3">
        <div className="relative">
          <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
            <Link className={`w-4 h-4 transition-colors ${url ? 'text-accent-primary' : 'text-text-muted'}`} />
          </div>
          <input
            type="text"
            placeholder="YouTube URL or drag a file..."
            className={`input-field pl-10 pr-12 py-3 text-sm ${showValidation && !url ? 'border-accent-danger focus:border-accent-danger focus:ring-accent-danger/30' : ''}`}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={isProcessing}
          />
          <button
            onClick={handleBrowseFiles}
            disabled={isProcessing}
            className="absolute right-2 inset-y-2 px-2 text-text-muted hover:text-accent-primary transition-colors disabled:opacity-50"
            title="Browse files"
          >
            <FolderOpen className="w-4 h-4" />
          </button>
        </div>

        {/* Validation Message */}
        <AnimatePresence>
          {showValidation && !url && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="flex items-center gap-2 text-accent-danger text-xs"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Please enter a URL or select a file
            </motion.div>
          )}
        </AnimatePresence>

        {/* GPU Toggle - Compact */}
        <div className="flex items-center justify-between p-3 rounded-lg bg-bg-secondary/50 border border-border-subtle">
          <div className="flex items-center gap-2.5">
            <Cpu className={`w-4 h-4 transition-colors ${useGPU ? 'text-accent-primary' : 'text-text-muted'}`} />
            <div>
              <div className="text-sm font-medium text-text-primary">GPU Acceleration</div>
              <div className="text-[10px] text-text-muted">MLX / CUDA</div>
            </div>
          </div>
          <button
            onClick={() => setUseGPU(!useGPU)}
            disabled={isProcessing}
            className={`relative w-10 h-5 rounded-full transition-colors ${useGPU ? 'bg-accent-primary' : 'bg-border-strong'}`}
            role="switch"
            aria-checked={useGPU}
          >
            <motion.div 
              animate={{ x: useGPU ? 20 : 0 }}
              transition={{ type: "spring", stiffness: 500, damping: 30 }}
              className="absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow flex items-center justify-center"
            >
              {useGPU && <Check className="w-2.5 h-2.5 text-accent-primary" />}
            </motion.div>
          </button>
        </div>

        {/* Main Action Button */}
        <button
          onClick={handleAnalyze}
          disabled={isProcessing}
          className={`w-full py-3 rounded-lg font-bold text-sm uppercase tracking-wider transition-all flex items-center justify-center gap-2.5 ${
            isProcessing 
              ? 'bg-bg-elevated text-text-muted border border-border-default cursor-wait' 
              : 'btn-primary'
          }`}
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              {status === "downloading" ? "Downloading..." : status === "transcribing" ? "Transcribing..." : "Processing..."}
            </>
          ) : (
            <>
              <Zap className="w-4 h-4" />
              Analyze Video
            </>
          )}
        </button>
      </div>

      {/* Progress Section */}
      <AnimatePresence>
        {status !== "idle" && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-4 overflow-hidden"
          >
            <div className={`p-3 rounded-lg border-l-2 ${
              status === "error" 
                ? 'bg-accent-danger/10 border-accent-danger' 
                : status === "downloading"
                  ? 'bg-accent-secondary/10 border-accent-secondary'
                  : 'bg-accent-primary/10 border-accent-primary'
            }`}>
              <div className="flex justify-between items-center mb-2">
                <div className="flex items-center gap-2">
                  <div className={`w-1.5 h-1.5 rounded-full ${
                    status === "error" ? "bg-accent-danger" : "bg-current animate-pulse"
                  }`} style={{ color: status === "downloading" ? 'var(--color-accent-secondary)' : 'var(--color-accent-primary)' }} />
                  <span className={`text-xs font-semibold ${
                    status === "error" ? "text-accent-danger" :
                    status === "downloading" ? "text-accent-secondary" : "text-accent-primary"
                  }`}>
                    {status === "downloading" && "Downloading"}
                    {status === "transcribing" && "Whisper AI"}
                    {status === "exporting" && "Rendering"}
                    {status === "error" && "Failed"}
                  </span>
                </div>
                <span className="text-xs font-mono text-text-secondary">{Math.round(progress)}%</span>
              </div>
              
              <div className="progress-bar h-1.5">
                <motion.div
                  className="progress-bar-fill"
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  style={{ 
                    background: status === "error" 
                      ? 'var(--color-accent-danger)' 
                      : status === "downloading"
                        ? 'var(--color-accent-secondary)'
                        : undefined 
                  }}
                />
              </div>
              
              {status === "transcribing" && (
                <div className="mt-2 flex items-center gap-1.5 text-[10px] text-text-muted">
                  <Sparkles className="w-2.5 h-2.5 text-accent-primary" />
                  Extracting dialog...
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.section>
  );
}

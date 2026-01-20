import { AppStatus } from "../types";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { listen } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/plugin-dialog";
import { Download, Cpu, Activity, AlertCircle, Youtube, Loader2, File, FolderOpen } from "lucide-react";

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

  useEffect(() => {
    const unlisteners: (() => void)[] = [];

    const setupListeners = async () => {
      console.log("Setting up drag and drop listeners (Tauri v2)");
      
      // Handler for drop events - supports both v1 and v2 payload formats
      const handleDrop = (event: any) => {
        console.log("Tauri drop event:", event);
        setIsDragging(false);
        
        const payload = event.payload;
        let paths: string[] = [];
        
        // v1 format: payload is string[]
        // v2 format: payload is { paths: string[], position: { x, y } }
        if (Array.isArray(payload)) {
          paths = payload;
        } else if (payload?.paths && Array.isArray(payload.paths)) {
          paths = payload.paths;
        }
        
        if (paths.length > 0) {
          console.log("File dropped (Tauri):", paths[0]);
          setUrl(paths[0]);
        }
      };

      const handleDragEnter = (event: any) => {
        console.log("Tauri drag enter:", event);
        setIsDragging(true);
      };

      const handleDragLeave = (event: any) => {
        console.log("Tauri drag leave:", event);
        setIsDragging(false);
      };

      // Listen to Tauri v2 events (new names)
      try {
        unlisteners.push(await listen("tauri://drag-drop", handleDrop));
        unlisteners.push(await listen("tauri://drag-enter", handleDragEnter));
        unlisteners.push(await listen("tauri://drag-leave", handleDragLeave));
        console.log("✓ Tauri v2 drag events registered");
      } catch (e) {
        console.warn("Failed to register v2 events:", e);
      }

      // Also listen to v1 events for backward compatibility
      try {
        unlisteners.push(await listen("tauri://file-drop", handleDrop));
        unlisteners.push(await listen("tauri://file-drop-hover", handleDragEnter));
        unlisteners.push(await listen("tauri://file-drop-cancelled", handleDragLeave));
        console.log("✓ Tauri v1 drag events registered (fallback)");
      } catch (e) {
        console.warn("Failed to register v1 events:", e);
      }
    };

    setupListeners();

    return () => {
      unlisteners.forEach(unlisten => unlisten());
    };
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
    console.log("Drop event triggered", e);
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    console.log("Files from dataTransfer:", files);
    
    if (files.length > 0) {
      // In Tauri, the File object often has a 'path' property, 
      // but we need to cast to any to access it or check if it exists.
      const file = files[0] as any;
      console.log("First file object:", file);
      console.log("File path property:", file.path);
      console.log("File name property:", file.name);
      
      if (file.path) {
        console.log("File dropped (HTML5):", file.path);
        setUrl(file.path);
      } else if (file.name) {
          // Fallback might just be name, which isn't full path, 
          // but logging it helps debug.
          console.log("File dropped (HTML5 name only):", file.name);
          console.warn("File path not available, only have name. This won't work for processing.");
      }
    } else {
      console.log("No files in dataTransfer");
    }
  };

  const handleBrowseFiles = async () => {
    try {
      console.log("Opening file picker...");
      const selected = await open({
        multiple: false,
        filters: [{
          name: 'Video Files',
          extensions: ['mp4', 'mov', 'avi', 'mkv', 'webm', 'flv', 'm4v']
        }]
      });
      
      console.log("File picker result:", selected);
      
      if (selected) {
        // Handle both string and array returns
        const filePath = typeof selected === 'string' ? selected : selected[0];
        if (filePath) {
          console.log("File selected:", filePath);
          setUrl(filePath);
        }
      } else {
        console.log("No file selected (user cancelled)");
      }
    } catch (error) {
      console.error("File picker error:", error);
      alert(`Failed to open file picker: ${error}`);
    }
  };

  return (
    <section 
      className={`bg-bg-secondary p-6 technical-border shadow-technical relative overflow-hidden transition-colors ${isDragging ? "border-accent-orange" : ""}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {isDragging && (
        <div className="absolute inset-0 z-50 bg-accent-orange/90 flex flex-col items-center justify-center text-white backdrop-blur-sm animate-in fade-in duration-200">
          <File className="w-16 h-16 mb-4 animate-bounce" />
          <p className="font-bold text-lg tracking-widest uppercase">Drop File Here</p>
        </div>
      )}

      <div className="absolute top-0 right-0 p-2 opacity-50">
         <div className="w-16 h-16 rounded-full border border-border-main flex items-center justify-center">
             <div className="w-12 h-12 rounded-full border border-border-main" />
         </div>
      </div>
      
      <h2 className="text-sm font-bold mb-6 flex items-center gap-3 text-text-main uppercase tracking-widest border-b border-border-main pb-2">
        <Download size={16} />
        INPUT SOURCE
      </h2>

      <div className="space-y-6">
        <div className="space-y-2">
          <label className="technical-text text-text-muted ml-1">Video URL / Local Path</label>
          <div className="flex gap-2">
            <div className="relative group flex-1">
              <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none text-text-muted group-focus-within:text-accent-orange transition-colors">
                <Youtube size={18} />
              </div>
              <input
                type="text"
                placeholder="Paste YouTube URL or Local File..."
                className="w-full bg-white border border-border-strong rounded-none pl-12 pr-4 py-3 text-sm font-mono text-text-main focus:outline-none focus:border-accent-orange focus:ring-1 focus:ring-accent-orange transition-all placeholder:text-text-muted/50"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={isProcessing}
              />
            </div>
            <button
              onClick={handleBrowseFiles}
              disabled={isProcessing}
              className="px-4 py-3 bg-white border border-border-strong hover:border-accent-orange hover:text-accent-orange transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 text-sm font-medium text-text-main"
              title="Browse local files"
            >
              <FolderOpen size={18} />
              Browse
            </button>
          </div>
        </div>

        <div className="flex items-center gap-3 px-3 py-3 bg-white border border-border-main">
          <div className={`p-2 transition-colors ${useGPU ? "text-accent-orange" : "text-text-muted"}`}>
            <Cpu size={16} />
          </div>
          <div className="flex-1">
            <div className="technical-text text-text-muted">Acceleration</div>
            <label
              htmlFor="gpuToggle"
              className="text-xs text-text-main cursor-pointer select-none flex items-center justify-between font-medium"
            >
              Use GPU (Apple Silicon / CUDA)
              <input
                type="checkbox"
                id="gpuToggle"
                checked={useGPU}
                onChange={(e) => setUseGPU(e.target.checked)}
                className="w-4 h-4 accent-accent-orange cursor-pointer rounded-none"
                disabled={isProcessing}
              />
            </label>
          </div>
        </div>

        <button
          onClick={onDownload}
          disabled={isProcessing || !url}
          className={`w-full relative overflow-hidden group transition-all py-3 font-bold text-xs uppercase tracking-[0.2em] shadow-sm active:translate-y-px flex items-center justify-center gap-3 border border-transparent ${
            isProcessing 
              ? "bg-bg-main text-text-muted border-border-main cursor-wait" 
              : "bg-accent-orange hover:bg-orange-600 text-white shadow-md active:shadow-none"
          }`}
        >
          {isProcessing ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <Activity size={16} />
              Analyze Video
            </>
          )}
        </button>

        <AnimatePresence>
          {status !== "idle" && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-4 p-4 bg-white border border-border-main shadow-inner"
            >
              <div className="flex justify-between items-center mb-2">
                <div className="flex items-center gap-2">
                  {status === "error" ? (
                    <AlertCircle size={14} className="text-accent-red" />
                  ) : (
                    <div className={`w-2 h-2 rounded-full animate-pulse ${
                      status === "downloading" ? "bg-accent-blue" : 
                      status === "transcribing" ? "bg-accent-orange" : "bg-green-600"
                    }`} />
                  )}
                  <span className={`technical-text ${
                    status === "downloading" ? "text-accent-blue" :
                    status === "transcribing" ? "text-accent-orange" :
                    status === "exporting" ? "text-green-600" : "text-accent-red"
                  }`}>
                    {status === "downloading" ? "Downloading" :
                     status === "transcribing" ? "Transcribing" :
                     status === "exporting" ? "Exporting" : "Failed"}
                  </span>
                </div>
                <span className="text-xs font-mono text-text-muted">{Math.round(progress)}%</span>
              </div>
              
              <div className="w-full bg-bg-main h-1.5 overflow-hidden border border-border-main">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  className={`h-full ${
                    status === "downloading" ? "bg-accent-blue" :
                    status === "transcribing" ? "bg-accent-orange" :
                    status === "exporting" ? "bg-green-600" :
                    "bg-accent-red"
                  }`}
                />
              </div>
              
              {status === "transcribing" && (
                <p className="mt-2 text-[10px] text-text-muted text-center font-mono">
                  _whisper_process::extracting_dialog
                </p>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}

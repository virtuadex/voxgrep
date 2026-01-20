import { useState } from "react";
import { VideoFile } from "../types";
import { motion, AnimatePresence } from "framer-motion";
import { Library as LibraryIcon, Search, CheckCircle, Clock, HardDrive, Filter } from "lucide-react";

interface LibraryProps {
  library: VideoFile[];
  onSelect: (video: VideoFile) => void;
  selectedVideoPath?: string;
}

export function Library({ library, onSelect, selectedVideoPath }: LibraryProps) {
  const [filter, setFilter] = useState("");

  const filteredLibrary = library.filter(v => 
    v.filename.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <section className="bg-bg-secondary p-6 technical-border h-[600px] flex flex-col shadow-technical">
      <div className="flex justify-between items-center mb-4 border-b border-border-main pb-2">
        <h2 className="text-sm font-bold flex items-center gap-3 text-text-main uppercase tracking-widest">
          <LibraryIcon size={16} />
          LIBRARY
        </h2>
        <span className="text-[10px] font-mono text-text-muted bg-white px-2 py-0.5 border border-border-main">
          {library.length} ITEMS
        </span>
      </div>

      <div className="relative mb-6">
        <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none text-text-muted">
          <Search size={14} />
        </div>
        <input 
          type="text" 
          placeholder="FILTER INDEX..." 
          className="w-full bg-white border border-border-strong rounded-none pl-9 pr-4 py-2 text-xs font-mono focus:outline-none focus:border-accent-blue focus:ring-1 focus:ring-accent-blue transition-all placeholder:text-text-muted uppercase"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        {filter && (
          <button 
            onClick={() => setFilter("")}
            className="absolute inset-y-0 right-3 flex items-center text-text-muted hover:text-accent-red transition-colors"
          >
            <span className="text-[10px] font-bold uppercase tracking-tighter">Clear</span>
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
        <AnimatePresence mode="popLayout">
          {filteredLibrary.length > 0 ? (
            filteredLibrary.map((video, idx) => (
              <motion.div
                layout
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15, delay: idx * 0.02 }}
                key={video.path}
                onClick={() => onSelect(video)}
                className={`p-3 border transition-all cursor-pointer group relative overflow-hidden ${
                  selectedVideoPath === video.path
                    ? "bg-white border-accent-blue shadow-sm" 
                    : "bg-bg-main border-border-main hover:border-accent-orange hover:bg-white"
                }`}
              >
                {selectedVideoPath === video.path && (
                  <motion.div 
                    layoutId="active-indicator"
                    className="absolute left-0 top-0 bottom-0 w-1 bg-accent-blue" 
                  />
                )}
                
                <div className={`font-bold text-sm truncate transition-colors pl-2 ${
                  selectedVideoPath === video.path ? "text-accent-blue" : "text-text-main group-hover:text-accent-orange"
                }`}>
                  {video.filename}
                </div>
                
                <div className="flex flex-col gap-1.5 mt-2 pl-2">
                  <div className="flex justify-between items-center text-[9px] font-mono text-text-muted uppercase tracking-tight">
                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1">
                        <Clock size={10} />
                        {new Date(video.created_at * 1000).toLocaleDateString()}
                      </span>
                      <span className="flex items-center gap-1">
                        <HardDrive size={10} />
                        {(video.size_bytes / (1024 * 1024)).toFixed(1)}MB
                      </span>
                    </div>
                  </div>
                  
                  <div className={`flex items-center gap-1.5 text-[9px] font-black uppercase tracking-widest ${
                    video.has_transcript ? "text-green-600" : "text-accent-orange"
                  }`}>
                    {video.has_transcript ? (
                      <>
                        <CheckCircle size={10} />
                        <span>Indexed</span>
                      </>
                    ) : (
                      <>
                        <div className="w-1.5 h-1.5 rounded-full bg-accent-orange animate-pulse" />
                        <span>Ready</span>
                      </>
                    )}
                  </div>
                </div>
              </motion.div>
            ))
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-text-muted p-8 text-center opacity-50">
              <Filter size={24} className="mb-2" />
              <p className="text-[10px] font-bold uppercase tracking-widest">No matches found</p>
            </div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}

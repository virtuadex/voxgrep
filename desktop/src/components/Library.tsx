import { useState, useMemo, useCallback } from "react";
import { VideoFile } from "../types";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Library as LibraryIcon, Search, Clock, 
  HardDrive, Film, ChevronRight, X, Play,
  RefreshCw
} from "lucide-react";
import { convertFileSrc } from "@tauri-apps/api/core";

interface LibraryProps {
  library: VideoFile[];
  onSelect: (video: VideoFile) => void;
  selectedVideoPath?: string;
  onRefresh?: () => void;
  isLoading?: boolean;
}

export function Library({ library, onSelect, selectedVideoPath, onRefresh, isLoading }: LibraryProps) {
  const [filter, setFilter] = useState("");
  const [previewVideo, setPreviewVideo] = useState<VideoFile | null>(null);

  const filteredLibrary = useMemo(() => 
    library.filter(v => v.filename.toLowerCase().includes(filter.toLowerCase())),
    [library, filter]
  );

  const stats = useMemo(() => ({
    total: library.length,
    indexed: library.filter(v => v.has_transcript).length,
    totalSize: library.reduce((acc, v) => acc + v.size_bytes, 0)
  }), [library]);

  const handleVideoPreview = useCallback((e: React.MouseEvent, video: VideoFile) => {
    e.stopPropagation();
    setPreviewVideo(previewVideo?.path === video.path ? null : video);
  }, [previewVideo]);

  return (
    <motion.section 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
      className="glass-card rounded-xl p-5 flex flex-col"
      style={{ height: 'calc(100vh - 400px)', minHeight: '400px', maxHeight: '600px' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="section-label">
          <LibraryIcon className="w-4 h-4 text-accent-secondary" />
          Media Library
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={onRefresh}
            disabled={isLoading}
            className="btn-icon w-7 h-7"
            title="Refresh library"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <span className="badge badge-info">{stats.total}</span>
        </div>
      </div>

      {/* Compact Stats */}
      <div className="flex gap-2 mb-3 text-xs">
        <div className="flex-1 px-3 py-2 rounded-lg bg-bg-secondary/50 border border-border-subtle text-center">
          <span className="font-bold text-text-primary">{stats.total}</span>
          <span className="text-text-muted ml-1.5">files</span>
        </div>
        <div className="flex-1 px-3 py-2 rounded-lg bg-bg-secondary/50 border border-border-subtle text-center">
          <span className="font-bold text-accent-success">{stats.indexed}</span>
          <span className="text-text-muted ml-1.5">indexed</span>
        </div>
        <div className="flex-1 px-3 py-2 rounded-lg bg-bg-secondary/50 border border-border-subtle text-center">
          <span className="font-bold text-text-primary">{(stats.totalSize / (1024 * 1024 * 1024)).toFixed(1)}</span>
          <span className="text-text-muted ml-1.5">GB</span>
        </div>
      </div>

      {/* Search Filter */}
      <div className="relative mb-3">
        <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
          <Search className="w-3.5 h-3.5 text-text-muted" />
        </div>
        <input 
          type="text" 
          placeholder="Filter..." 
          className="input-field pl-9 pr-8 py-2 text-xs"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        {filter && (
          <button 
            onClick={() => setFilter("")}
            className="absolute inset-y-0 right-2 flex items-center text-text-muted hover:text-accent-primary transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Video Preview Modal */}
      <AnimatePresence>
        {previewVideo && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-3 overflow-hidden"
          >
            <div className="rounded-lg overflow-hidden border border-accent-secondary/50 bg-bg-main">
              <video 
                src={convertFileSrc(previewVideo.path)}
                controls
                className="w-full aspect-video"
                autoPlay
              />
              <div className="p-2 flex items-center justify-between bg-bg-elevated">
                <span className="text-xs font-medium text-text-primary truncate flex-1 mr-2">
                  {previewVideo.filename}
                </span>
                <button 
                  onClick={() => setPreviewVideo(null)}
                  className="text-xs text-text-muted hover:text-accent-primary"
                >
                  Close
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* File List */}
      <div className="flex-1 overflow-y-auto space-y-1.5 custom-scrollbar">
        <AnimatePresence mode="popLayout">
          {filteredLibrary.length > 0 ? (
            filteredLibrary.map((video, idx) => {
              const isSelected = selectedVideoPath === video.path;
              return (
                <motion.div
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.15, delay: idx * 0.015 }}
                  key={video.path}
                  onClick={() => onSelect(video)}
                  className={`group p-3 rounded-lg cursor-pointer transition-all relative ${
                    isSelected
                      ? "bg-accent-secondary/15 border border-accent-secondary/50" 
                      : "bg-bg-secondary/30 border border-transparent hover:border-border-default hover:bg-bg-elevated/50"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {/* Preview Button */}
                    <button
                      onClick={(e) => handleVideoPreview(e, video)}
                      className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 transition-all ${
                        isSelected 
                          ? 'bg-accent-secondary/20 text-accent-secondary hover:bg-accent-secondary/30' 
                          : 'bg-bg-elevated text-text-muted hover:bg-accent-primary/20 hover:text-accent-primary'
                      }`}
                      title="Preview video"
                    >
                      {previewVideo?.path === video.path ? (
                        <X className="w-4 h-4" />
                      ) : (
                        <Play className="w-4 h-4 ml-0.5" fill="currentColor" />
                      )}
                    </button>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className={`font-medium text-sm truncate transition-colors ${
                        isSelected ? "text-accent-secondary" : "text-text-primary group-hover:text-accent-primary"
                      }`}>
                        {video.filename}
                      </div>
                      
                      <div className="flex items-center gap-2 mt-1">
                        <span className="flex items-center gap-1 text-[10px] text-text-muted">
                          <Clock className="w-2.5 h-2.5" />
                          {new Date(video.created_at * 1000).toLocaleDateString()}
                        </span>
                        <span className="w-0.5 h-0.5 rounded-full bg-text-muted" />
                        <span className="flex items-center gap-1 text-[10px] text-text-muted">
                          <HardDrive className="w-2.5 h-2.5" />
                          {(video.size_bytes / (1024 * 1024)).toFixed(0)}MB
                        </span>
                      </div>
                    </div>

                    {/* Status */}
                    <div className="flex items-center gap-1.5 shrink-0">
                      {video.has_transcript ? (
                        <div className="w-2 h-2 rounded-full bg-accent-success" title="Indexed" />
                      ) : (
                        <div className="w-2 h-2 rounded-full bg-accent-primary animate-pulse" title="Ready to index" />
                      )}
                      <ChevronRight className={`w-4 h-4 transition-all ${
                        isSelected ? 'text-accent-secondary' : 'text-text-muted opacity-0 group-hover:opacity-100'
                      }`} />
                    </div>
                  </div>
                </motion.div>
              );
            })
          ) : (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="h-full flex flex-col items-center justify-center text-center p-6"
            >
              <div className="w-12 h-12 rounded-full bg-bg-elevated flex items-center justify-center mb-3">
                {filter ? <Search className="w-5 h-5 text-text-muted" /> : <Film className="w-5 h-5 text-text-muted" />}
              </div>
              <p className="text-sm font-medium text-text-secondary mb-1">
                {filter ? "No matches" : "No videos"}
              </p>
              <p className="text-xs text-text-muted">
                {filter ? "Try a different search" : "Add videos to get started"}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.section>
  );
}

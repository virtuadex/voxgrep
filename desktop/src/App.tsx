import { useState, useCallback, useEffect } from "react";
import "./index.css";

import { Header } from "./components/Header";
import { InputSource } from "./components/InputSource";
import { Library } from "./components/Library";
import { SearchDashboard } from "./components/SearchDashboard";
import { VideoFile, AppStatus, SearchMatch, SearchType } from "./types";
import { downloadVideo, addLocalFile, openFolder } from "./api";
import { useLibrary } from "./hooks/useLibrary";
import { useSearch } from "./hooks/useSearch";
import { motion } from "framer-motion";
import { Focus, Layers, X } from "lucide-react";

function App() {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<AppStatus>("idle");
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [selectedVideo, setSelectedVideo] = useState<VideoFile | null>(null);
  const [useGPU, setUseGPU] = useState(true); // Default to GPU on
  const [ngramN, setNgramN] = useState(1);

  const { library, scan, isLoading: isLibraryLoading, isScanning } = useLibrary();
  const { 
    matches, 
    isSearching, 
    search, 
    ngrams, 
    isNgramsLoading, 
    exportMatches,
    searchError,
    reset: resetSearch
  } = useSearch(selectedVideo, ngramN);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K to focus search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('input[placeholder*="Search"]') as HTMLInputElement;
        searchInput?.focus();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Refresh library on mount
  useEffect(() => {
    scan("downloads");
  }, []);

  const handleDownload = async () => {
    if (!url) return;
    
    const isLocalFile = url.startsWith('/') || url.match(/^[A-Za-z]:\\/);
    const device = useGPU ? "mlx" : "auto";
    
    setStatus(isLocalFile ? "transcribing" : "downloading");
    setProgress(10);
    
    // Simulate progress for better UX
    const progressInterval = setInterval(() => {
      setProgress(p => Math.min(p + 5, 90));
    }, 2000);
    
    try {
      if (isLocalFile) {
        await addLocalFile(url, device);
        setMessage("File added! Transcription running in background.");
      } else {
        await downloadVideo(url, device);
        setMessage("Download started! Transcription will begin automatically.");
      }
      
      clearInterval(progressInterval);
      setProgress(100);
      
      setTimeout(() => {
        setMessage(null);
        setStatus("idle");
        setProgress(0);
        setUrl("");
      }, 3000);
      
      // Refresh library periodically to pick up new files
      setTimeout(() => scan("downloads"), 3000);
      setTimeout(() => scan("downloads"), 8000);
      setTimeout(() => scan("downloads"), 15000);
    } catch (e: any) {
      clearInterval(progressInterval);
      console.error("Processing failed:", e);
      setStatus("error");
      setMessage(e?.response?.data?.detail || e?.message || "Failed to process. Check if backend is running.");
      setProgress(0);
      setTimeout(() => { setMessage(null); setStatus("idle"); }, 6000);
    }
  };

  const handleSelectVideo = (video: VideoFile) => {
    const newSelection = selectedVideo?.path === video.path ? null : video;
    setSelectedVideo(newSelection);
    // Reset search when changing selection
    if (newSelection?.path !== selectedVideo?.path) {
      resetSearch();
    }
  };

  const handleClearSelection = () => {
    setSelectedVideo(null);
    resetSearch();
  };

  const handleSearch = useCallback((query: string, type: SearchType, threshold: number, exactMatch?: boolean) => {
    if (query.length > 0) {
      search({ query, type, threshold, exactMatch });
    }
  }, [search]);

  const handleExport = useCallback(async (matches: SearchMatch[]) => {
    if (matches.length === 0) return;
    setStatus("exporting");
    setProgress(0);
    
    const progressInterval = setInterval(() => {
      setProgress(p => Math.min(p + 3, 95));
    }, 500);
    
    const timestamp = Math.floor(Date.now() / 1000);
    const output = `downloads/supercut_${timestamp}.mp4`;
    
    try {
      await exportMatches({ matches, output });
      clearInterval(progressInterval);
      setProgress(100);
      setMessage(`Supercut exported! Check downloads folder.`);
      setTimeout(() => { setMessage(null); setStatus("idle"); setProgress(0); }, 5000);
      // Refresh library to show new supercut
      setTimeout(() => scan("downloads"), 1000);
    } catch (e: any) {
      clearInterval(progressInterval);
      console.error("Export failed:", e);
      setStatus("error");
      setMessage(e?.response?.data?.detail || "Export failed. Please try again.");
      setTimeout(() => { setMessage(null); setStatus("idle"); setProgress(0); }, 5000);
    }
  }, [exportMatches, scan]);

  const handleOpenFolder = useCallback(async (path: string) => {
    try {
      await openFolder(path);
    } catch (e) {
      console.error("Failed to open folder:", e);
    }
  }, []);

  const handleRefreshLibrary = useCallback(() => {
    scan("downloads");
  }, [scan]);

  return (
    <div className="min-h-screen p-4 lg:p-6 xl:p-8 max-w-[1920px] mx-auto">
      <Header message={message} />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 lg:gap-6 mt-6">
        {/* Left Sidebar */}
        <div className="lg:col-span-3 xl:col-span-3 space-y-4">
          <InputSource 
            url={url} 
            setUrl={setUrl} 
            useGPU={useGPU} 
            setUseGPU={setUseGPU} 
            status={status} 
            progress={progress} 
            onDownload={handleDownload} 
          />

          <Library 
            library={library} 
            onSelect={handleSelectVideo}
            selectedVideoPath={selectedVideo?.path}
            onRefresh={handleRefreshLibrary}
            isLoading={isLibraryLoading || isScanning}
          />
        </div>

        {/* Main Content */}
        <div className="lg:col-span-9 xl:col-span-9">
          {/* Scope Indicator */}
          <motion.div 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-4 flex items-center justify-between"
          >
            <div className="flex items-center gap-2">
              {selectedVideo ? (
                <div className="flex items-center gap-2 px-3 py-1.5 glass-card rounded-lg">
                  <Focus className="w-4 h-4 text-accent-secondary" />
                  <span className="text-sm text-text-secondary">Scope:</span>
                  <span className="text-sm font-medium text-text-primary truncate max-w-[250px]">
                    {selectedVideo.filename}
                  </span>
                  <button 
                    onClick={handleClearSelection}
                    className="ml-1 p-1 rounded hover:bg-bg-elevated text-text-muted hover:text-accent-danger transition-colors"
                    title="Clear selection"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2 px-3 py-1.5 glass-card rounded-lg">
                  <Layers className="w-4 h-4 text-accent-primary" />
                  <span className="text-sm text-text-secondary">Scope:</span>
                  <span className="text-sm font-medium text-accent-primary">
                    Full Library ({library.length} files)
                  </span>
                </div>
              )}
            </div>

            {/* Keyboard Hints */}
            <div className="hidden lg:flex items-center gap-3 text-xs text-text-muted">
              <div className="flex items-center gap-1.5">
                <kbd className="px-1.5 py-0.5 rounded bg-bg-elevated border border-border-default font-mono text-[10px]">⌘K</kbd>
                <span>Search</span>
              </div>
            </div>
          </motion.div>
          
          <SearchDashboard 
            onSearch={handleSearch} 
            onExport={handleExport}
            onOpenFolder={handleOpenFolder}
            onGetNGrams={setNgramN}
            matches={matches} 
            ngrams={ngrams}
            isSearching={isSearching}
            isNgramsLoading={isNgramsLoading}
            status={status}
            progress={progress}
            searchError={searchError}
          />
        </div>
      </div>
    </div>
  );
}

export default App;

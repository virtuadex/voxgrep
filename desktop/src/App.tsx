import { useState, useCallback } from "react";
import "./index.css";

import { Header } from "./components/Header";
import { InputSource } from "./components/InputSource";
import { Library } from "./components/Library";
import { SearchDashboard } from "./components/SearchDashboard";
import { VideoFile, AppStatus, SearchMatch, SearchType } from "./types";
import { downloadVideo, addLocalFile, openFolder } from "./api";
import { useLibrary } from "./hooks/useLibrary";
import { useSearch } from "./hooks/useSearch";

function App() {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<AppStatus>("idle");
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [selectedVideo, setSelectedVideo] = useState<VideoFile | null>(null);
  const [useGPU, setUseGPU] = useState(false);
  const [ngramN, setNgramN] = useState(1);

  const { library, scan } = useLibrary();
  const { 
    matches, 
    isSearching, 
    search, 
    ngrams, 
    isNgramsLoading, 
    exportMatches 
  } = useSearch(selectedVideo, ngramN);

  const handleDownload = async () => {
    if (!url) return;
    
    // Detect if it's a local file path or URL
    const isLocalFile = url.startsWith('/') || url.match(/^[A-Za-z]:\\/);
    const device = useGPU ? "mlx" : "auto";
    
    setStatus(isLocalFile ? "transcribing" : "downloading");
    setProgress(10);
    
    try {
      if (isLocalFile) {
        await addLocalFile(url, device);
        setMessage("Local file added and transcription started");
      } else {
        await downloadVideo(url, device);
        setMessage("Download and transcription started");
      }
      
      setTimeout(() => setMessage(null), 3000);
      setStatus("idle");
      setProgress(0);
      
      // Refresh library after a delay to allow background task to complete
      setTimeout(() => scan("downloads"), 2000);
    } catch (e) {
      console.error("Processing failed:", e);
      setStatus("error");
      setMessage("Failed to process file");
      setTimeout(() => setMessage(null), 5000);
    }
  };

  const handleSelectVideo = (video: VideoFile) => {
    setSelectedVideo(prev => prev?.path === video.path ? null : video);
  };

  const handleSearch = useCallback((query: string, type: SearchType, threshold: number) => {
    if (query.length > 0) {
      search({ query, type, threshold });
    }
  }, [search]);

  const handleExport = useCallback(async (matches: SearchMatch[]) => {
    if (matches.length === 0) return;
    setStatus("exporting");
    setProgress(0);
    
    const timestamp = Math.floor(Date.now() / 1000);
    const output = `downloads/supercut_${timestamp}.mp4`;
    
    try {
      await exportMatches({ matches, output });
      setMessage(`Supercut exported to ${output}`);
      setTimeout(() => setMessage(null), 5000);
      setStatus("idle");
      setProgress(0);
    } catch (e) {
      console.error("Export failed:", e);
      setStatus("error");
    }
  }, [exportMatches]);

  const handleOpenFolder = useCallback(async (path: string) => {
    try {
      await openFolder(path);
    } catch (e) {
      console.error("Failed to open folder:", e);
    }
  }, []);

  return (
    <div className="min-h-screen p-6 lg:p-12 max-w-[1920px] mx-auto relative z-10">
      <Header message={message} />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mt-8 lg:mt-12">
        <div className="lg:col-span-4 space-y-8">
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
          />
        </div>

        <div className="lg:col-span-8">
          <div className="mb-6 flex items-center gap-3">
            <div className="w-2 h-2 bg-accent-orange rounded-full animate-pulse" />
            <span className="technical-text text-text-muted">Active Scope //</span>
            <span className={`technical-text px-2 py-0.5 border ${selectedVideo ? "bg-accent-blue text-white border-accent-blue" : "bg-bg-secondary border-border-main text-text-main"}`}>
              {selectedVideo ? selectedVideo.filename : "FULL_LIBRARY_INDEX"}
            </span>
          </div>
          
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
          />
        </div>
      </div>
    </div>
  );
}

export default App;

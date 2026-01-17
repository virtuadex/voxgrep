import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import "./index.css";

interface SearchMatch {
  file: string;
  start: number;
  end: number;
  content: string;
}

interface VideoFile {
  path: string;
  name: string;
  size: string;
  date: number;
}

function App() {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<"idle" | "downloading" | "transcribing" | "complete" | "error">("idle");
  const [progress, setProgress] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [library, setLibrary] = useState<VideoFile[]>([]);
  const [matches, setMatches] = useState<SearchMatch[]>([]);
  const [useGPU, setUseGPU] = useState(false);

  useEffect(() => {
    // Listen for python events
    const unlisten = listen("python-event", (event: any) => {
      const { event: pyEvent, data } = event.payload;
      
      if (pyEvent === "status") {
        if (data.includes("Downloading")) setStatus("downloading");
        if (data.includes("Transcribing")) setStatus("transcribing");
      } else if (pyEvent === "search_results") {
        setMatches(data);
      } else if (pyEvent === "library") {
        setLibrary(data);
      } else if (pyEvent === "complete") {
        setStatus("complete");
        refreshLibrary();
      } else if (pyEvent === "error") {
        setStatus("error");
        console.error("Python Error:", data);
      }
    });

    refreshLibrary();
    return () => { unlisten.then(f => f()); };
  }, []);

  const refreshLibrary = () => {
    invoke("run_python_command", { args: ["list", "--path", "downloads"] });
  };

  const handleDownload = async () => {
    if (!url) return;
    setStatus("downloading");
    setProgress(10);
    invoke("run_python_command", { args: ["download", url, "--output", "downloads", "--device", useGPU ? "mlx" : "cpu"] });
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    if (query.length > 2) {
      invoke("run_python_command", { args: ["search", query, "--path", "downloads"] });
    } else {
      setMatches([]);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8 font-['Inter']">
      <header className="mb-12 flex justify-between items-end">
        <div>
          <h1 className="text-5xl font-black bg-linear-to-br from-blue-400 via-purple-500 to-pink-500 bg-clip-text text-transparent tracking-tight">
            VIDEOGREP
          </h1>
          <p className="text-slate-400 mt-2 font-medium tracking-wide flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            SYSTEM ONLINE • CLIP COMPILER READY
          </p>
        </div>
        <div className="text-right text-xs font-mono text-slate-500">
          v0.1.0-prototype
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Left Column: Side Controls */}
        <div className="lg:col-span-1 space-y-8">
          <section className="glass p-6 rounded-3xl border border-slate-800 shadow-2xl">
            <h2 className="text-lg font-bold mb-6 flex items-center gap-3">
              <span className="p-2 bg-blue-500/20 rounded-xl text-blue-400">📥</span>
              INPUT SOURCE
            </h2>
            <div className="space-y-4">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Paste YouTube URL..."
                  className="w-full bg-slate-900/50 border border-slate-700/50 rounded-2xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all placeholder:text-slate-600"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                />
              </div>

              <div className="flex items-center gap-2 px-1">
                 <input 
                   type="checkbox" 
                   id="gpuToggle"
                   checked={useGPU}
                   onChange={(e) => setUseGPU(e.target.checked)}
                   className="w-4 h-4 accent-blue-500 rounded cursor-pointer"
                 />
                 <label htmlFor="gpuToggle" className="text-sm text-slate-400 cursor-pointer select-none">
                   Enable GPU Acceleration (Apple Silicon)
                 </label>
              </div>
              <button
                onClick={handleDownload}
                disabled={status !== "idle" || !url}
                className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-600 transition-all py-3 rounded-2xl font-bold shadow-lg shadow-blue-900/20 active:scale-95"
              >
                {status === "idle" ? "PROCESS VIDEO" : "WORKING..."}
              </button>

              {status !== "idle" && (
                <div className="mt-4 p-4 bg-slate-900/80 rounded-2xl border border-slate-800/50">
                  <div className="flex justify-between text-[10px] font-black text-blue-400 uppercase tracking-widest mb-2">
                    <span>{status}</span>
                    <span>{progress}%</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div 
                      className="bg-linear-to-r from-blue-600 to-blue-400 h-full transition-all duration-500"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </section>

          <section className="glass p-6 rounded-3xl border border-slate-800 h-[500px] flex flex-col">
            <h2 className="text-lg font-bold mb-6 flex items-center gap-3">
              <span className="p-2 bg-purple-500/20 rounded-xl text-purple-400">📚</span>
              LIBRARY
            </h2>
            <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
              {library.map(video => (
                <div key={video.path} className="p-4 bg-slate-900/40 hover:bg-slate-900/80 rounded-2xl border border-slate-800/50 transition-all cursor-pointer group">
                  <div className="font-bold text-sm truncate group-hover:text-blue-400 transition-colors">{video.name}</div>
                  <div className="flex justify-between mt-2 text-[10px] font-mono text-slate-500 uppercase">
                    <span>{new Date(video.date * 1000).toLocaleDateString()}</span>
                    <span>{video.size}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* Right Column: Search Dashboard */}
        <div className="lg:col-span-3 space-y-8">
          <section className="glass p-8 rounded-4xl border border-slate-800 min-h-[700px] flex flex-col shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 blur-[120px] rounded-full pointer-events-none" />
            
            <div className="flex justify-between items-center mb-10 relative z-10">
              <h2 className="text-2xl font-black tracking-tight">SEARCH DASHBOARD</h2>
              <div className="flex p-1 bg-slate-900/80 rounded-2xl border border-slate-800/50">
                <button className="px-6 py-2 rounded-xl text-xs font-bold uppercase tracking-widest bg-slate-800 text-white shadow-lg">Fragment</button>
                <button className="px-6 py-2 rounded-xl text-xs font-bold uppercase tracking-widest text-slate-500 hover:text-slate-300 transition-colors">Sentence</button>
                <button className="ml-2 px-6 py-2 rounded-xl text-xs font-bold uppercase tracking-widest bg-linear-to-r from-purple-600 to-pink-600 text-white shadow-lg hover:scale-105 transition-all">Mashup</button>
              </div>
            </div>

            <div className="flex-1 space-y-4 overflow-y-auto pr-4 custom-scrollbar relative z-10">
              {matches.length > 0 ? (
                matches.map((match, idx) => (
                  <div key={idx} className="p-6 bg-slate-900/40 hover:bg-slate-900/80 rounded-3xl border border-slate-800/50 transition-all group cursor-pointer hover:border-blue-500/30">
                    <div className="flex gap-6">
                      <div className="w-32 aspect-video bg-slate-800 rounded-lg shrink-0 flex items-center justify-center font-mono text-[10px] text-slate-600">
                        {match.file.split('/').pop()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between items-start mb-2">
                          <span className="text-xs font-black text-blue-400 uppercase tracking-widest">{match.file.split('/').pop()}</span>
                          <span className="font-mono text-xs text-slate-500 bg-slate-800/50 px-2 py-1 rounded-md">{match.start.toFixed(2)}s</span>
                        </div>
                        <p className="text-slate-300 italic text-sm leading-relaxed">
                          {match.content}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-slate-600 opacity-50">
                   <div className="text-6xl mb-6">🔍</div>
                   <p className="text-xl font-bold uppercase tracking-widest">Awaiting Search Query</p>
                   <p className="text-sm">Scan your library for phrases or keywords</p>
                </div>
              )}
            </div>

            <div className="mt-10 relative z-10">
              <div className="absolute inset-y-0 left-6 flex items-center pointer-events-none text-slate-500 text-xl">
                󰍉
              </div>
              <input
                type="text"
                placeholder="Query database... (e.g. 'Expanding Universe')"
                className="w-full bg-slate-900 border border-slate-700/50 rounded-3xl pl-16 pr-8 py-5 text-xl font-medium focus:outline-none focus:ring-2 focus:ring-purple-500/30 transition-all placeholder:text-slate-700 shadow-xl"
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
              />
            </div>
          </section>

          {/* Timeline Heatmap */}
          <section className="glass p-8 rounded-4xl border border-slate-800 shadow-xl">
            <h2 className="text-sm font-black text-slate-500 mb-6 uppercase tracking-[0.2em] flex items-center gap-3">
              <span className="w-2 h-2 rounded-full bg-red-500"></span>
              Search Density • Temporal Distribution
            </h2>
            <div className="h-16 w-full bg-slate-900/80 rounded-2xl flex overflow-hidden border border-slate-800/50 p-2 gap-1">
               {/* This will be dynamic */}
               <div className="h-full bg-blue-500/10 flex-4 rounded-sm transition-all hover:bg-blue-500/20" />
               <div className="h-full bg-blue-500/20 flex-2 rounded-sm transition-all hover:bg-blue-500/30" />
               <div className="h-full bg-red-600 w-16 rounded-sm shadow-[0_0_15px_rgba(220,38,38,0.3)] transition-all hover:scale-x-110" title="High Density" />
               <div className="h-full bg-red-400 w-6 rounded-sm shadow-[0_0_10px_rgba(248,113,113,0.3)]" />
               <div className="h-full bg-blue-500/10 flex-6 rounded-sm" />
               <div className="h-full bg-red-500 w-10 rounded-sm" />
               <div className="h-full bg-blue-500/10 flex-3 rounded-sm" />
            </div>
            <div className="flex justify-between mt-3 text-[10px] font-mono text-slate-600 uppercase tracking-widest">
              <span>Start</span>
              <span>Library Duration Map</span>
              <span>End</span>
            </div>
          </section>
        </div>
      </div>
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.1);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.2);
        }
      `}</style>
    </div>
  );
}

export default App;

import { useState, useEffect, KeyboardEvent, useMemo, useRef, useCallback } from "react";
import { SearchMatch, NGramMatch, AppStatus } from "../types";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Scissors, FolderOpen, Play, BarChart3, Info, Sparkles, X, Hash, Clock, Percent, Activity, Loader2 } from "lucide-react";
import { convertFileSrc } from "@tauri-apps/api/core";

interface SearchDashboardProps {
  onSearch: (query: string, type: string, threshold: number) => void;
  onExport: (matches: SearchMatch[]) => void;
  onOpenFolder: (path: string) => void;
  onGetNGrams: (n: number) => void;
  matches: SearchMatch[];
  ngrams: NGramMatch[];
  isSearching: boolean;
  isNgramsLoading: boolean;
  status: AppStatus;
  progress: number;
}

export function SearchDashboard({ 
  onSearch, 
  onExport, 
  onOpenFolder,
  onGetNGrams, 
  matches, 
  ngrams, 
  isSearching, 
  isNgramsLoading,
  status, 
  progress 
}: SearchDashboardProps) {
  const [query, setQuery] = useState("");
  const [searchType, setSearchType] = useState("sentence");
  const [threshold, setThreshold] = useState(0.45);
  const [hasSearched, setHasSearched] = useState(false);
  const [searchTime, setSearchTime] = useState<number | null>(null);
  const [startTime, setStartTime] = useState<number>(0);
  const [ngramN, setNgramN] = useState(1);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const triggerSearch = useCallback(() => {
    if (query.trim().length > 0) {
      setHasSearched(true);
      setStartTime(performance.now());
      onSearch(query.trim(), searchType, threshold);
    }
  }, [query, searchType, threshold, onSearch]);

  useEffect(() => {
    if (!isSearching && hasSearched && startTime > 0) {
      setSearchTime((performance.now() - startTime) / 1000);
    }
  }, [isSearching, hasSearched, startTime]);

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      triggerSearch();
    }
  };

  useEffect(() => {
    if (query.trim().length > 0 && hasSearched) {
      const handler = setTimeout(() => {
        triggerSearch();
      }, 400);
      return () => clearTimeout(handler);
    }
  }, [threshold, searchType, triggerSearch, query, hasSearched]);

  useEffect(() => {
    onGetNGrams(ngramN);
  }, [ngramN, onGetNGrams]);

  const heatmapData = useMemo(() => {
    if (matches.length === 0) return Array(60).fill(0);
    const buckets = Array(60).fill(0);
    const maxTime = matches.reduce((max, m) => Math.max(max, m.end), 60);
    matches.forEach(m => {
      const bucketIdx = Math.floor((m.start / maxTime) * 59);
      if (bucketIdx >= 0 && bucketIdx < 60) buckets[bucketIdx]++;
    });
    const maxVal = Math.max(...buckets, 1);
    return buckets.map(v => v / maxVal);
  }, [matches]);

  const clearSearch = () => {
    setQuery("");
    setHasSearched(false);
    setSearchTime(null);
    searchInputRef.current?.focus();
  };

  return (
    <div className="space-y-6">
      <section className="bg-bg-secondary p-8 technical-border flex flex-col shadow-technical relative overflow-hidden min-h-[700px]">
        {/* Search Input Bar */}
        <div className="mb-8 relative z-10">
          <div className="relative group">
            <div className="absolute inset-y-0 left-6 flex items-center pointer-events-none text-text-muted text-xl group-focus-within:text-accent-orange transition-colors">
              <Search size={24} />
            </div>
            <input
              ref={searchInputRef}
              type="text"
              placeholder={searchType === "mash" ? "ENTER WORD FOR MASHUP..." : `SEARCH ${searchType.toUpperCase()} IN INDEX...`}
              className="w-full bg-white border border-border-strong rounded-none pl-16 pr-32 py-6 text-xl font-mono text-text-main focus:outline-none focus:border-accent-orange focus:ring-1 focus:ring-accent-orange transition-all placeholder:text-text-muted/50 uppercase"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <div className="absolute right-4 inset-y-4 flex gap-2">
              {query && (
                <button 
                  onClick={clearSearch}
                  className="px-4 text-text-muted hover:text-accent-red transition-colors"
                >
                  <X size={20} />
                </button>
              )}
            <button 
                onClick={triggerSearch} 
                disabled={isSearching}
                className={`px-8 h-full font-bold text-xs uppercase tracking-widest transition-all active:translate-y-px shadow-sm flex items-center gap-2 border border-transparent ${
                  isSearching ? "bg-bg-main text-text-muted cursor-not-allowed border-border-main" :
                  "bg-accent-orange hover:bg-orange-600 text-white shadow-md active:shadow-none"
                }`}
              >
                {isSearching ? <Loader2 size={14} className="animate-spin" /> : null}
                {isSearching ? "SCANNING" : "SEARCH"}
              </button>
            </div>
          </div>
        </div>

        {/* Controls Bar */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-10 relative z-10 p-2 bg-white border border-border-main">
          <div className="space-y-1 pl-4">
            <h2 className="text-xl font-black tracking-tight flex items-center gap-2 text-text-main">
              <Activity className="text-accent-blue" size={20} />
              RESULTS
            </h2>
            <AnimatePresence>
              {searchTime && !isSearching && matches.length > 0 && (
                <motion.div 
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-2 text-[10px] font-bold text-text-muted uppercase tracking-widest"
                >
                  <Sparkles size={10} className="text-accent-orange" />
                  Found {matches.length} results in {searchTime.toFixed(2)}s
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          
          <div className="flex flex-wrap items-center gap-4 pr-2">
            <div className="flex p-1 bg-bg-main border border-border-main">
              {["fragment", "sentence", "semantic"].map(t => (
                <button 
                  key={t}
                  onClick={() => setSearchType(t)} 
                  className={`px-4 py-2 text-[10px] font-black uppercase tracking-widest transition-all rounded-none ${searchType === t ? "bg-white text-accent-blue shadow-sm border border-border-main" : "text-text-muted hover:text-text-main"}`}
                >
                  {t}
                </button>
              ))}
              <div className="w-px bg-border-main mx-1 my-1"></div>
              <button 
                onClick={() => setSearchType("mash")} 
                className={`px-4 py-2 text-[10px] font-black uppercase tracking-widest transition-all rounded-none ${searchType === "mash" ? "bg-accent-blue text-white shadow-sm" : "text-text-muted hover:text-text-main"}`}
              >
                Mashup
              </button>
            </div>
          </div>
        </div>

        {/* Threshold Slider */}
        <AnimatePresence>
          {searchType === "semantic" && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-8 px-5 py-4 bg-white border border-border-main relative z-10 flex items-center gap-6"
            >
              <div className="flex-1">
                <div className="flex justify-between items-center mb-2">
                  <div className="flex items-center gap-2">
                    <Percent size={12} className="text-accent-blue" />
                    <span className="text-[10px] font-black text-text-muted uppercase tracking-widest">Similarity Threshold</span>
                  </div>
                  <span className="text-xs font-mono font-bold text-accent-blue bg-bg-secondary px-2 py-0.5 border border-border-main">{Math.round(threshold * 100)}%</span>
                </div>
                <input type="range" min="0.1" max="0.9" step="0.05" value={threshold} onChange={(e) => setThreshold(parseFloat(e.target.value))} className="w-full h-1 bg-border-main rounded-none appearance-none cursor-pointer accent-accent-blue" />
              </div>
              <div className="w-1/3 text-[9px] text-text-muted flex items-start gap-2 border-l border-border-main pl-6 font-mono">
                <Info size={14} className="shrink-0 text-text-main" />
                Higher values return more precise matches but fewer results.
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Status Messages */}
        <AnimatePresence>
          {status === "transcribing" && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-6 p-6 bg-white border border-accent-orange/50 relative z-10 border-l-4 border-l-accent-orange"
            >
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-accent-orange animate-pulse" />
                  <span className="text-xs font-black text-accent-orange uppercase tracking-[0.2em]">Whisper AI Transcription in Progress</span>
                </div>
                <span className="text-xs font-mono text-text-main font-bold">{Math.round(progress)}%</span>
              </div>
              <div className="w-full bg-bg-main h-2 overflow-hidden border border-border-main">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  className="h-full bg-accent-orange"
                />
              </div>
              <p className="mt-2 text-[10px] text-text-muted font-mono">_process::extracting_dialog_patterns</p>
            </motion.div>
          )}

          {status === "exporting" && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-6 p-6 bg-white border border-green-600/50 relative z-10 border-l-4 border-l-green-600"
            >
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-green-600 animate-pulse" />
                  <span className="text-xs font-black text-green-600 uppercase tracking-[0.2em]">Exporting Supercut Compilation</span>
                </div>
                <span className="text-xs font-mono text-green-600 font-bold">{Math.round(progress)}%</span>
              </div>
              <div className="w-full bg-bg-main h-2 overflow-hidden border border-border-main">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  className="h-full bg-green-600"
                />
              </div>
              <p className="mt-2 text-[10px] text-text-muted font-mono">_render::concatenating_clips</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Main Content */}
        <div className="flex-1 flex flex-col md:flex-row gap-8 min-h-0 relative z-10">
          <div className="flex-1 space-y-4 overflow-y-auto pr-4 custom-scrollbar">
            <AnimatePresence mode="wait">
              {isSearching ? (
                <motion.div 
                  key="searching"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="h-full flex flex-col items-center justify-center p-12"
                >
                  <div className="relative mb-8">
                    <div className="w-16 h-16 border-4 border-border-main border-t-accent-blue rounded-full animate-spin"></div>
                  </div>
                  <p className="text-xl font-black uppercase tracking-[0.2em] text-accent-blue mb-2">
                    {searchType === "semantic" ? "Neural Mapping..." : "Scanning Database..."}
                  </p>
                  <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-none border border-border-main shadow-sm">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-600 animate-pulse" />
                    <span className="text-[10px] font-mono text-text-muted uppercase tracking-widest">Engine Active</span>
                  </div>
                </motion.div>
              ) : matches.length > 0 ? (
                <motion.div 
                  key="results"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="grid grid-cols-1 gap-4 pb-8"
                >
                  {matches.map((match, idx) => (
                    <motion.div 
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.05 }}
                      key={idx} 
                      className="p-4 bg-white hover:bg-white rounded-none border border-border-main hover:border-accent-blue transition-all group shadow-sm flex gap-6 relative"
                    >
                      <div className="w-48 aspect-video bg-black rounded-sm shrink-0 overflow-hidden relative group/vid border border-border-main">
                        <video 
                          className="w-full h-full object-cover opacity-80 group-hover/vid:opacity-100 transition-opacity"
                          onLoadedMetadata={(e) => {
                            e.currentTarget.currentTime = match.start;
                          }}
                          onMouseOver={(e) => e.currentTarget.play()}
                          onMouseOut={(e) => { e.currentTarget.pause(); e.currentTarget.currentTime = match.start; }}
                          muted
                          preload="metadata"
                        >
                          <source src={convertFileSrc(match.file)} type="video/mp4" />
                        </video>
                        <div className="absolute inset-0 flex items-center justify-center pointer-events-none group-hover/vid:opacity-0 transition-opacity bg-black/10">
                           <Play size={20} className="text-white fill-white" />
                        </div>
                        <div className="absolute bottom-2 right-2 px-1.5 py-0.5 bg-black/80 rounded-none text-[9px] font-mono text-white border border-white/20">
                          {Math.floor(match.start / 60)}:{(match.start % 60).toFixed(0).padStart(2, '0')}
                        </div>
                      </div>
                      
                      <div className="flex-1 min-w-0 flex flex-col py-1">
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-[9px] font-black text-accent-blue bg-bg-secondary px-2 py-0.5 border border-border-main uppercase tracking-widest truncate max-w-[200px]">
                              {match.file.split("/").pop()}
                            </span>
                            {match.score && (
                              <div className="flex items-center gap-1.5 text-[9px] font-mono font-bold text-accent-orange bg-white px-2 py-0.5 border border-accent-orange/30">
                                <Sparkles size={8} />
                                {Math.round(match.score * 100)}%
                              </div>
                            )}
                          </div>
                        </div>
                        
                        <div className="flex-1">
                          <p className="text-text-main text-sm leading-relaxed font-medium line-clamp-3 relative font-serif italic">
                            "{match.content}"
                          </p>
                        </div>
                        
                        <div className="mt-3 flex items-center gap-3">
                          <button 
                            onClick={(e) => {
                              const card = e.currentTarget.closest('.group');
                              const video = card?.querySelector('video');
                              if (video) {
                                video.currentTime = match.start;
                                video.play();
                              }
                            }}
                            className="px-3 py-1.5 bg-white hover:bg-accent-blue hover:text-white text-accent-blue text-[9px] font-black uppercase tracking-widest border border-accent-blue transition-all flex items-center gap-2"
                          >
                            <Play size={10} fill="currentColor" />
                            Preview
                          </button>
                          <button 
                            onClick={() => onOpenFolder(match.file)}
                            className="px-3 py-1.5 bg-bg-secondary hover:bg-border-main text-text-muted text-[9px] font-black uppercase tracking-widest border border-border-main transition-all flex items-center gap-2"
                          >
                            <FolderOpen size={10} />
                            Source
                          </button>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </motion.div>
              ) : hasSearched ? (
                <motion.div 
                  key="no-results"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="h-full flex flex-col items-center justify-center text-text-muted p-12"
                >
                  <X size={48} className="opacity-20 mb-4" />
                  <p className="text-lg font-black uppercase tracking-[0.2em] mb-2 text-text-main">Zero Matches</p>
                  <p className="text-xs font-mono">Try a different keyword or lower the threshold</p>
                </motion.div>
              ) : (
                <motion.div 
                  key="idle"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="h-full flex flex-col items-center justify-center text-text-main p-12"
                >
                  <div className="grid grid-cols-2 gap-4 max-w-md">
                    <div className="p-6 bg-white border border-border-main text-center space-y-3 hover:border-accent-blue transition-colors group">
                      <Hash className="mx-auto text-text-muted group-hover:text-accent-blue" size={24} />
                      <p className="text-[10px] font-black uppercase tracking-widest">Fragment</p>
                      <p className="text-[9px] text-text-muted leading-tight">Word-level precision.</p>
                    </div>
                    <div className="p-6 bg-white border border-border-main text-center space-y-3 hover:border-accent-blue transition-colors group">
                      <Activity className="mx-auto text-text-muted group-hover:text-accent-blue" size={24} />
                      <p className="text-[10px] font-black uppercase tracking-widest">Sentence</p>
                      <p className="text-[9px] text-text-muted leading-tight">Full sentence matches.</p>
                    </div>
                    <div className="p-6 bg-white border border-border-main text-center space-y-3 hover:border-accent-orange transition-colors group">
                      <Sparkles className="mx-auto text-text-muted group-hover:text-accent-orange" size={24} />
                      <p className="text-[10px] font-black uppercase tracking-widest">Semantic</p>
                      <p className="text-[9px] text-text-muted leading-tight">Conceptual search.</p>
                    </div>
                    <div className="p-6 bg-white border border-border-main text-center space-y-3 hover:border-accent-red transition-colors group">
                      <Scissors className="mx-auto text-text-muted group-hover:text-accent-red" size={24} />
                      <p className="text-[10px] font-black uppercase tracking-widest">Mashup</p>
                      <p className="text-[9px] text-text-muted leading-tight">Randomized clips.</p>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* NGrams Panel */}
          <div className="w-80 bg-white border border-border-main flex flex-col overflow-hidden shadow-sm">
            <div className="p-4 border-b border-border-main flex justify-between items-center bg-bg-secondary">
              <div className="flex items-center gap-2">
                <BarChart3 size={14} className="text-accent-blue" />
                <span className="text-[10px] font-black text-text-muted uppercase tracking-widest">LINGUISTIC N-GRAMS</span>
              </div>
              <div className="flex p-0.5 bg-white border border-border-main">
                {[1, 2, 3].map(n => (
                  <button 
                    key={n}
                    onClick={() => setNgramN(n)}
                    className={`px-2 py-0.5 text-[9px] font-black transition-all ${ngramN === n ? "bg-accent-blue text-white" : "text-text-muted hover:text-text-main"}`}
                  >
                    {n}G
                  </button>
                ))}
              </div>
            </div>
            
            <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
              <AnimatePresence mode="wait">
                {isNgramsLoading ? (
                  <div className="h-full flex flex-col items-center justify-center p-8 space-y-4 opacity-50">
                    <Loader2 size={24} className="animate-spin text-text-muted" />
                    <span className="text-[9px] font-black uppercase tracking-widest text-text-muted">Analyzing...</span>
                  </div>
                ) : ngrams.length > 0 ? (
                  <div className="space-y-1">
                    {ngrams.slice(0, 50).map((g, i) => (
                      <button
                        key={i}
                        onClick={() => {
                          setQuery(g.ngram);
                          setHasSearched(true);
                          setStartTime(performance.now());
                          onSearch(g.ngram, searchType, threshold);
                          searchInputRef.current?.focus();
                        }}
                        className="w-full group text-left p-2 rounded-sm hover:bg-bg-secondary border border-transparent hover:border-border-main transition-all flex items-center justify-between"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="w-5 h-5 bg-white border border-border-main flex items-center justify-center shrink-0">
                            <span className="text-[9px] font-mono text-text-muted">{i + 1}</span>
                          </div>
                          <span className="text-xs text-text-main font-medium truncate pr-2">{g.ngram}</span>
                        </div>
                        <span className="text-[9px] font-mono font-bold text-accent-blue">{g.count}</span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center p-8 text-center opacity-40">
                    <BarChart3 size={24} className="mb-2 text-text-muted" />
                    <p className="text-[10px] font-black uppercase tracking-widest text-text-muted">
                      No Data
                    </p>
                  </div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>

        <AnimatePresence>
          {matches.length > 0 && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-8 flex justify-center sticky bottom-8 z-50 pointer-events-none"
            >
              <button 
                onClick={() => onExport(matches)}
                className="pointer-events-auto px-12 py-4 bg-accent-blue hover:bg-blue-700 text-white text-xs font-black uppercase tracking-[0.2em] shadow-xl active:translate-y-px flex items-center gap-3 group border border-transparent"
              >
                <Scissors size={18} className="group-hover:rotate-12 transition-transform" />
                Export Compilation ({matches.length})
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      {/* Timeline Heatmap */}
      <section className="bg-bg-secondary p-8 technical-border shadow-technical relative overflow-hidden">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-sm font-black text-text-muted uppercase tracking-[0.2em] flex items-center gap-3">
            <div className="w-2.5 h-2.5 rounded-none bg-accent-red animate-pulse"></div>
            Search Density
          </h2>
          <div className="flex items-center gap-4 text-[10px] font-mono text-text-muted uppercase tracking-widest">
            <span className="flex items-center gap-1.5"><Clock size={10} /> Normalized Scope</span>
            <span className="w-px h-3 bg-border-main"></span>
            <span>{matches.length} Keys</span>
          </div>
        </div>

        <div className="h-16 w-full bg-white border border-border-main flex items-end overflow-hidden p-2 gap-0.5">
          {heatmapData.map((val, i) => (
            <motion.div 
              key={i} 
              initial={{ height: "5%" }}
              animate={{ height: `${Math.max(val * 100, 5)}%` }}
              transition={{ delay: i * 0.01, duration: 0.5 }}
              className={`flex-1 transition-all duration-300 ${
                val > 0 
                  ? "bg-accent-orange" 
                  : "bg-bg-secondary"
              }`}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

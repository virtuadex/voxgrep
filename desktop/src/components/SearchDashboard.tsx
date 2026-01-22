import { useState, useEffect, KeyboardEvent, useMemo, useRef, useCallback } from "react";
import { SearchMatch, NGramMatch, AppStatus, SearchType } from "../types";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Search, Scissors, FolderOpen, Play, BarChart3, Sparkles, X, Hash, 
  Clock, Activity, Loader2, Zap, Waves, Target, 
  MessageSquare, TrendingUp, Volume2, AlertCircle
} from "lucide-react";
import { convertFileSrc } from "@tauri-apps/api/core";

interface SearchDashboardProps {
  onSearch: (query: string, type: SearchType, threshold: number, exactMatch?: boolean) => void;
  onExport: (matches: SearchMatch[]) => void;
  onOpenFolder: (path: string) => void;
  onGetNGrams: (n: number) => void;
  matches: SearchMatch[];
  ngrams: NGramMatch[];
  isSearching: boolean;
  isNgramsLoading: boolean;
  status: AppStatus;
  progress: number;
  searchError?: Error | null;
}

const searchModes: { id: SearchType; label: string; icon: typeof Hash; desc: string }[] = [
  { id: "fragment", label: "Fragment", icon: Hash, desc: "Words" },
  { id: "sentence", label: "Sentence", icon: MessageSquare, desc: "Full lines" },
  { id: "semantic", label: "Semantic", icon: Sparkles, desc: "AI meaning" },
  { id: "mash", label: "Mashup", icon: Scissors, desc: "Random remix" },
];

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
  progress,
  searchError
}: SearchDashboardProps) {
  const [query, setQuery] = useState("");
  const [searchType, setSearchType] = useState<SearchType>("sentence");
  const [threshold, setThreshold] = useState(0.45);
  const [hasSearched, setHasSearched] = useState(false);
  const [searchTime, setSearchTime] = useState<number | null>(null);
  const [startTime, setStartTime] = useState<number>(0);
  const [ngramN, setNgramN] = useState(1);
  const [exactMatch, setExactMatch] = useState(false);
  const [hoveringVideo, setHoveringVideo] = useState<number | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const triggerSearch = useCallback(() => {
    if (query.trim().length > 0) {
      setHasSearched(true);
      setStartTime(performance.now());
      onSearch(query.trim(), searchType, threshold, exactMatch);
    }
  }, [query, searchType, threshold, exactMatch, onSearch]);

  useEffect(() => {
    if (!isSearching && hasSearched && startTime > 0) {
      setSearchTime((performance.now() - startTime) / 1000);
    }
  }, [isSearching, hasSearched, startTime]);

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") triggerSearch();
    if (e.key === "Escape") {
      setQuery("");
      setHasSearched(false);
      searchInputRef.current?.blur();
    }
  };

  // Debounced search on option changes
  useEffect(() => {
    if (query.trim().length > 0 && hasSearched) {
      const handler = setTimeout(triggerSearch, 300);
      return () => clearTimeout(handler);
    }
  }, [threshold, searchType, exactMatch]);

  useEffect(() => {
    onGetNGrams(ngramN);
  }, [ngramN, onGetNGrams]);

  const heatmapData = useMemo(() => {
    if (matches.length === 0) return Array(40).fill(0);
    const buckets = Array(40).fill(0);
    const maxTime = matches.reduce((max, m) => Math.max(max, m.end), 60);
    matches.forEach(m => {
      const bucketIdx = Math.floor((m.start / maxTime) * 39);
      if (bucketIdx >= 0 && bucketIdx < 40) buckets[bucketIdx]++;
    });
    const maxVal = Math.max(...buckets, 1);
    return buckets.map(v => v / maxVal);
  }, [matches]);

  const totalDuration = useMemo(() => 
    matches.reduce((acc, m) => acc + (m.end - m.start), 0),
    [matches]
  );

  const clearSearch = () => {
    setQuery("");
    setHasSearched(false);
    setSearchTime(null);
    searchInputRef.current?.focus();
  };

  const currentMode = searchModes.find(m => m.id === searchType)!;

  return (
    <div className="space-y-4">
      {/* Search Bar + Mode Selector */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="glass-card rounded-xl p-4"
      >
        {/* Search Input Row */}
        <div className="flex gap-3 mb-4">
          <div className="flex-1 relative">
            <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
              <Search className={`w-5 h-5 transition-colors ${isSearching ? 'text-accent-primary animate-pulse' : query ? 'text-accent-primary' : 'text-text-muted'}`} />
            </div>
            <input
              ref={searchInputRef}
              type="text"
              placeholder={`Search ${currentMode.label.toLowerCase()}...`}
              className="w-full bg-bg-secondary/80 border border-border-default rounded-lg pl-12 pr-12 py-3.5 text-base text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-primary focus:ring-2 focus:ring-accent-primary-glow transition-all"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            {query && (
              <button 
                onClick={clearSearch}
                className="absolute right-4 inset-y-0 flex items-center text-text-muted hover:text-accent-danger transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
          <button 
            onClick={triggerSearch} 
            disabled={isSearching || !query.trim()}
            className="btn-primary px-6 shrink-0"
          >
            {isSearching ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Zap className="w-4 h-4" />
            )}
            <span className="hidden sm:inline">{isSearching ? "Searching" : "Search"}</span>
          </button>
        </div>

        {/* Mode Selector - Always Visible */}
        <div className="flex flex-wrap items-center gap-2">
          {searchModes.map((mode) => (
            <button
              key={mode.id}
              onClick={() => setSearchType(mode.id)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                searchType === mode.id 
                  ? 'bg-accent-primary text-white shadow-lg shadow-accent-primary/25' 
                  : 'bg-bg-elevated text-text-secondary hover:text-text-primary hover:bg-bg-secondary border border-border-subtle'
              }`}
            >
              <mode.icon className="w-4 h-4" />
              <span>{mode.label}</span>
              <span className={`text-xs ${searchType === mode.id ? 'text-white/70' : 'text-text-muted'}`}>
                {mode.desc}
              </span>
            </button>
          ))}

          {/* Divider */}
          <div className="w-px h-6 bg-border-default mx-1" />

          {/* Exact Match Toggle (Fragment only) */}
          {searchType === "fragment" && (
            <button
              onClick={() => setExactMatch(!exactMatch)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                exactMatch 
                  ? 'bg-accent-secondary text-white' 
                  : 'bg-bg-elevated text-text-secondary hover:text-text-primary border border-border-subtle'
              }`}
            >
              <Target className="w-4 h-4" />
              Exact
            </button>
          )}

          {/* Semantic Threshold */}
          {searchType === "semantic" && (
            <div className="flex items-center gap-3 px-3 py-2 bg-bg-elevated rounded-lg border border-border-subtle">
              <Waves className="w-4 h-4 text-accent-secondary" />
              <input 
                type="range" 
                min="0.1" 
                max="0.9" 
                step="0.05" 
                value={threshold} 
                onChange={(e) => setThreshold(parseFloat(e.target.value))} 
                className="w-24 h-1 bg-border-default rounded-full appearance-none cursor-pointer accent-accent-secondary"
              />
              <span className="text-xs font-mono font-bold text-accent-secondary w-10">{Math.round(threshold * 100)}%</span>
            </div>
          )}
        </div>
      </motion.div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
        {/* Results Panel */}
        <motion.section 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="xl:col-span-3 glass-card rounded-xl p-5 flex flex-col"
          style={{ minHeight: '500px', maxHeight: 'calc(100vh - 380px)' }}
        >
          {/* Results Header */}
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-border-subtle">
            <div className="flex items-center gap-3">
              <Activity className="w-4 h-4 text-accent-secondary" />
              <span className="font-semibold text-text-primary">Results</span>
              {hasSearched && !isSearching && (
                <span className="text-sm text-text-muted">
                  {matches.length} match{matches.length !== 1 ? 'es' : ''}
                  {searchTime && ` in ${searchTime.toFixed(2)}s`}
                </span>
              )}
            </div>
            {matches.length > 0 && (
              <div className="flex items-center gap-4 text-xs text-text-muted">
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {totalDuration.toFixed(1)}s total
                </span>
              </div>
            )}
          </div>

          {/* Results Content */}
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            <AnimatePresence mode="wait">
              {/* Loading State */}
              {isSearching && (
                <motion.div 
                  key="loading"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="h-full flex flex-col items-center justify-center py-12"
                >
                  <div className="relative mb-6">
                    <div className="w-16 h-16 border-3 border-border-default border-t-accent-primary rounded-full animate-spin" />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <currentMode.icon className="w-6 h-6 text-accent-primary" />
                    </div>
                  </div>
                  <p className="text-sm font-medium text-text-primary mb-1">
                    {searchType === "semantic" ? "Neural search..." : "Scanning transcripts..."}
                  </p>
                  <p className="text-xs text-text-muted">Searching for "{query}"</p>
                </motion.div>
              )}

              {/* Error State */}
              {!isSearching && searchError && (
                <motion.div 
                  key="error"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="h-full flex flex-col items-center justify-center py-12"
                >
                  <div className="w-14 h-14 rounded-full bg-accent-danger/10 flex items-center justify-center mb-4">
                    <AlertCircle className="w-7 h-7 text-accent-danger" />
                  </div>
                  <p className="text-sm font-medium text-text-primary mb-1">Search failed</p>
                  <p className="text-xs text-text-muted max-w-sm text-center">
                    {searchError.message || "An error occurred while searching"}
                  </p>
                </motion.div>
              )}

              {/* Results List */}
              {!isSearching && !searchError && matches.length > 0 && (
                <motion.div 
                  key="results"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="space-y-3 pb-4"
                >
                  {matches.map((match, idx) => (
                    <motion.div 
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: Math.min(idx * 0.03, 0.3) }}
                      key={idx} 
                      className="group p-3 bg-bg-secondary/40 hover:bg-bg-elevated border border-border-subtle hover:border-accent-secondary/40 rounded-lg transition-all flex gap-4"
                      onMouseEnter={() => setHoveringVideo(idx)}
                      onMouseLeave={() => setHoveringVideo(null)}
                    >
                      {/* Video Thumbnail */}
                      <div className="w-36 aspect-video rounded-md overflow-hidden relative bg-bg-main shrink-0 border border-border-default">
                        <video 
                          className="w-full h-full object-cover"
                          onLoadedMetadata={(e) => { e.currentTarget.currentTime = match.start; }}
                          onMouseOver={(e) => e.currentTarget.play()}
                          onMouseOut={(e) => { e.currentTarget.pause(); e.currentTarget.currentTime = match.start; }}
                          muted
                          preload="metadata"
                        >
                          <source src={convertFileSrc(match.file)} type="video/mp4" />
                        </video>
                        
                        {/* Play Overlay */}
                        <div className={`absolute inset-0 flex items-center justify-center bg-black/30 transition-opacity ${hoveringVideo === idx ? 'opacity-0' : 'opacity-100'}`}>
                          <div className="w-8 h-8 rounded-full bg-white/90 flex items-center justify-center">
                            <Play className="w-3.5 h-3.5 text-bg-main ml-0.5" fill="currentColor" />
                          </div>
                        </div>

                        {/* Time Badge */}
                        <div className="absolute bottom-1 right-1 px-1.5 py-0.5 bg-black/80 rounded text-[10px] font-mono text-white">
                          {Math.floor(match.start / 60)}:{(match.start % 60).toFixed(0).padStart(2, '0')}
                        </div>

                        {/* Score Badge */}
                        {match.score && (
                          <div className="absolute top-1 left-1 px-1.5 py-0.5 bg-accent-primary/90 rounded text-[10px] font-bold text-white flex items-center gap-0.5">
                            <TrendingUp className="w-2.5 h-2.5" />
                            {Math.round(match.score * 100)}%
                          </div>
                        )}
                      </div>
                      
                      {/* Content */}
                      <div className="flex-1 min-w-0 flex flex-col py-0.5">
                        <div className="flex items-center gap-2 mb-1.5">
                          <span className="text-xs text-text-muted truncate max-w-[200px]">
                            {match.file.split("/").pop()}
                          </span>
                          <span className="text-[10px] text-text-muted">
                            {(match.end - match.start).toFixed(1)}s
                          </span>
                        </div>
                        
                        <p className="text-sm text-text-primary leading-relaxed flex-1 line-clamp-2">
                          "{match.content}"
                        </p>
                        
                        <div className="flex items-center gap-2 mt-2">
                          <button 
                            onClick={(e) => {
                              const card = e.currentTarget.closest('.group');
                              const video = card?.querySelector('video');
                              if (video) { video.currentTime = match.start; video.play(); }
                            }}
                            className="btn-secondary py-1 px-2.5 text-[10px]"
                          >
                            <Play className="w-3 h-3" fill="currentColor" />
                            Play
                          </button>
                          <button 
                            onClick={() => onOpenFolder(match.file)}
                            className="btn-secondary py-1 px-2.5 text-[10px]"
                          >
                            <FolderOpen className="w-3 h-3" />
                            Open
                          </button>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </motion.div>
              )}

              {/* No Results */}
              {!isSearching && !searchError && hasSearched && matches.length === 0 && (
                <motion.div 
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="h-full flex flex-col items-center justify-center py-12"
                >
                  <div className="w-14 h-14 rounded-full bg-bg-elevated flex items-center justify-center mb-4">
                    <X className="w-7 h-7 text-text-muted" />
                  </div>
                  <p className="text-sm font-medium text-text-primary mb-1">No matches found</p>
                  <p className="text-xs text-text-muted">Try different keywords or adjust the threshold</p>
                </motion.div>
              )}

              {/* Idle State */}
              {!isSearching && !hasSearched && (
                <motion.div 
                  key="idle"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="h-full flex flex-col items-center justify-center py-12"
                >
                  <div className="w-16 h-16 rounded-full bg-bg-elevated flex items-center justify-center mb-4">
                    <Search className="w-8 h-8 text-text-muted" />
                  </div>
                  <p className="text-sm font-medium text-text-primary mb-1">Ready to search</p>
                  <p className="text-xs text-text-muted">Enter a query and press Enter or click Search</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Export Button */}
          <AnimatePresence>
            {matches.length > 0 && (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                className="mt-4 pt-4 border-t border-border-subtle"
              >
                <button 
                  onClick={() => onExport(matches)}
                  disabled={status === "exporting"}
                  className="w-full btn-primary py-3"
                >
                  {status === "exporting" ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Exporting... {Math.round(progress)}%
                    </>
                  ) : (
                    <>
                      <Scissors className="w-4 h-4" />
                      Export Supercut ({matches.length} clips, {totalDuration.toFixed(1)}s)
                    </>
                  )}
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.section>

        {/* Side Panel: N-Grams + Heatmap */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.3 }}
          className="space-y-4"
        >
          {/* N-Grams Panel */}
          <div className="glass-card rounded-xl p-4 flex flex-col" style={{ height: '350px' }}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-accent-secondary" />
                <span className="text-sm font-semibold text-text-primary">Top Phrases</span>
              </div>
              <div className="flex bg-bg-elevated rounded-md p-0.5">
                {[1, 2, 3].map(n => (
                  <button 
                    key={n}
                    onClick={() => setNgramN(n)}
                    className={`px-2 py-1 text-[10px] font-bold rounded transition-all ${
                      ngramN === n ? 'bg-accent-secondary text-white' : 'text-text-muted hover:text-text-primary'
                    }`}
                  >
                    {n}G
                  </button>
                ))}
              </div>
            </div>
            
            <div className="flex-1 overflow-y-auto custom-scrollbar space-y-1">
              {isNgramsLoading ? (
                <div className="h-full flex flex-col items-center justify-center">
                  <Loader2 className="w-5 h-5 text-text-muted animate-spin mb-2" />
                  <span className="text-xs text-text-muted">Loading...</span>
                </div>
              ) : ngrams.length > 0 ? (
                ngrams.slice(0, 25).map((g, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setQuery(g.ngram);
                      setHasSearched(true);
                      setStartTime(performance.now());
                      onSearch(g.ngram, searchType, threshold, exactMatch);
                    }}
                    className="w-full flex items-center justify-between p-2 rounded-md hover:bg-bg-elevated transition-all group text-left"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="w-5 h-5 rounded bg-bg-elevated flex items-center justify-center text-[10px] font-mono text-text-muted shrink-0 group-hover:bg-accent-secondary group-hover:text-white transition-colors">
                        {i + 1}
                      </span>
                      <span className="text-sm text-text-primary truncate group-hover:text-accent-primary transition-colors">
                        {g.ngram}
                      </span>
                    </div>
                    <span className="text-xs font-mono font-bold text-accent-secondary ml-2">{g.count}</span>
                  </button>
                ))
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-center p-4">
                  <Volume2 className="w-6 h-6 text-text-muted mb-2 opacity-50" />
                  <p className="text-xs text-text-muted">Select a video to see phrases</p>
                </div>
              )}
            </div>
          </div>

          {/* Heatmap */}
          <div className="glass-card rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-accent-danger" />
                <span className="text-sm font-semibold text-text-primary">Timeline</span>
              </div>
              <span className="text-xs text-text-muted">{matches.length} hits</span>
            </div>

            <div className="h-8 bg-bg-secondary/50 rounded-md border border-border-subtle flex items-end overflow-hidden p-1 gap-px">
              {heatmapData.map((val, i) => (
                <motion.div 
                  key={i} 
                  initial={{ height: "15%" }}
                  animate={{ height: `${Math.max(val * 100, 15)}%` }}
                  transition={{ delay: i * 0.01, duration: 0.3 }}
                  className={`flex-1 rounded-sm ${
                    val > 0.6 ? "bg-accent-primary" : 
                    val > 0.2 ? "bg-accent-secondary" :
                    val > 0 ? "bg-text-muted/50" : "bg-border-subtle"
                  }`}
                />
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

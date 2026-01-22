import { useMutation, useQuery } from "@tanstack/react-query";
import { searchMedia, exportSupercut, getNGrams } from "../api";
import { SearchMatch, VideoFile, SearchType } from "../types";

export function useSearch(selectedVideo: VideoFile | null, ngramN: number) {
  // Scope search to selected video if one is chosen
  const videoIds = selectedVideo?.id ? [selectedVideo.id] : undefined;
  
  const searchMutation = useMutation({
    mutationFn: ({ query, type, threshold, exactMatch }: { query: string; type: SearchType; threshold: number; exactMatch?: boolean }) => 
      searchMedia(query, type, threshold, exactMatch, videoIds),
  });

  // Fetch ngrams for selected video or full library
  const ngramPath = selectedVideo?.path || "downloads";
  const ngramsQuery = useQuery({
    queryKey: ["ngrams", ngramPath, ngramN],
    queryFn: () => getNGrams(ngramPath, ngramN),
    enabled: true, // Always fetch
    staleTime: 30000, // Cache for 30 seconds
  });

  const exportMutation = useMutation({
    mutationFn: ({ matches, output }: { matches: SearchMatch[]; output: string }) => 
      exportSupercut(matches, { output }),
  });

  return {
    matches: searchMutation.data || [],
    isSearching: searchMutation.isPending,
    search: searchMutation.mutate,
    searchError: searchMutation.error,
    ngrams: ngramsQuery.data || [],
    isNgramsLoading: ngramsQuery.isLoading,
    ngramsError: ngramsQuery.error,
    exportMatches: exportMutation.mutateAsync,
    isExporting: exportMutation.isPending,
    reset: searchMutation.reset,
  };
}

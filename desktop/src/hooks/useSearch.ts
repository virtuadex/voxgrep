import { useMutation, useQuery } from "@tanstack/react-query";
import { searchMedia, exportSupercut, getNGrams } from "../api";
import { SearchMatch, VideoFile } from "../types";

export function useSearch(selectedVideo: VideoFile | null, ngramN: number) {
  const searchMutation = useMutation({
    mutationFn: ({ query, type, threshold }: { query: string; type: string; threshold: number }) => 
      searchMedia(query, type as any, threshold),
  });

  const ngramsQuery = useQuery({
    queryKey: ["ngrams", selectedVideo?.path || "downloads", ngramN],
    queryFn: () => getNGrams(selectedVideo?.path || "downloads", ngramN),
  });

  const exportMutation = useMutation({
    mutationFn: ({ matches, output }: { matches: SearchMatch[]; output: string }) => 
      exportSupercut(matches, { output }),
  });

  return {
    matches: searchMutation.data || [],
    isSearching: searchMutation.isPending,
    search: searchMutation.mutate,
    ngrams: ngramsQuery.data || [],
    isNgramsLoading: ngramsQuery.isLoading,
    exportMatches: exportMutation.mutateAsync,
    isExporting: exportMutation.isPending,
  };
}

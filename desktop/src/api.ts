/**
 * VoxGrep API Client
 * 
 * Provides typed API access for all VoxGrep server endpoints.
 */
import axios from "axios";
import {
  VideoFile,
  SearchMatch,
  NGramMatch,
  VectorStats,
  Speaker,
  ModelsResponse,
  SubtitlePresets,
  ExportOptions,
  HealthResponse,
  SearchType,
} from "./types";

const API_BASE_URL = "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 second timeout for most requests
});

// ============================================================================
// Phase 1: Core API
// ============================================================================

/**
 * Check server health and get feature availability.
 */
export const getHealth = async (): Promise<HealthResponse> => {
  const { data } = await api.get("/health");
  return data;
};

/**
 * Get all videos in the library.
 */
export const getLibrary = async (): Promise<VideoFile[]> => {
  const { data } = await api.get("/library");
  return data;
};

/**
 * Get a specific video by ID.
 */
export const getVideo = async (videoId: number): Promise<VideoFile> => {
  const { data } = await api.get(`/library/${videoId}`);
  return data;
};

/**
 * Scan a directory for new videos.
 */
export const scanLibrary = async (path?: string): Promise<{ added: number; path: string }> => {
  const { data } = await api.post("/library/scan", null, {
    params: path ? { path } : undefined,
  });
  return data;
};

/**
 * Delete a video from the library (doesn't delete file).
 */
export const deleteVideo = async (videoId: number): Promise<{ status: string }> => {
  const { data } = await api.delete(`/library/${videoId}`);
  return data;
};

/**
 * Download a video from URL and transcribe it.
 */
export const downloadVideo = async (
  url: string,
  device: string = "auto"
): Promise<{ status: string; url: string }> => {
  const { data } = await api.post("/download", null, {
    params: { url, device },
  });
  return data;
};

/**
 * Add a local video file to the library and transcribe it.
 */
export const addLocalFile = async (
  filepath: string,
  device: string = "auto"
): Promise<{ status: string; filepath: string }> => {
  const { data } = await api.post("/add-local", null, {
    params: { filepath, device },
  });
  return data;
};

/**
 * Search across the library.
 */
export const searchMedia = async (
  query: string,
  type: SearchType = "sentence",
  threshold: number = 0.45,
  videoIds?: number[]
): Promise<SearchMatch[]> => {
  const { data } = await api.get("/search", {
    params: {
      query,
      type,
      threshold,
      video_ids: videoIds?.join(","),
    },
  });
  return data;
};

/**
 * Get n-grams for a path.
 */
export const getNGrams = async (
  path: string,
  n: number = 1
): Promise<NGramMatch[]> => {
  const { data } = await api.get("/ngrams", {
    params: { path, n },
  });
  return data;
};

/**
 * Export a supercut from search results.
 */
export const exportSupercut = async (
  matches: SearchMatch[],
  options: ExportOptions
): Promise<{ status: string; path: string }> => {
  const { data } = await api.post("/export", matches, {
    params: {
      output: options.output,
      transition: options.transition || "cut",
      transition_duration: options.transition_duration || 0.5,
      burn_subtitles: options.burn_subtitles || false,
      subtitle_preset: options.subtitle_preset || "default",
    },
  });
  return data;
};

/**
 * Open a folder in the system file manager.
 */
export const openFolder = async (path: string): Promise<{ status: string }> => {
  const { data } = await api.post("/open_folder", null, {
    params: { path },
  });
  return data;
};

// ============================================================================
// Phase 2: Vector Search & Indexing
// ============================================================================

/**
 * Index a video for semantic search.
 */
export const indexVideo = async (
  videoId: number,
  force: boolean = false
): Promise<{ status: string; video_id: number; segments: number }> => {
  const { data } = await api.post(`/index/${videoId}`, null, {
    params: { force },
  });
  return data;
};

/**
 * Index all videos in the library.
 */
export const indexAllVideos = async (
  force: boolean = false
): Promise<{ status: string; total_videos: number }> => {
  const { data } = await api.post("/index/all", null, {
    params: { force },
  });
  return data;
};

/**
 * Get vector index statistics.
 */
export const getIndexStats = async (): Promise<VectorStats> => {
  const { data } = await api.get("/index/stats");
  return data;
};

// ============================================================================
// Phase 2: Speaker Diarization
// ============================================================================

/**
 * Run speaker diarization on a video.
 */
export const diarizeVideo = async (
  videoId: number,
  numSpeakers?: number,
  force: boolean = false
): Promise<{ status: string; video_id: number }> => {
  const { data } = await api.post(`/diarize/${videoId}`, null, {
    params: {
      num_speakers: numSpeakers,
      force,
    },
  });
  return data;
};

/**
 * Get speakers detected in a video.
 */
export const getVideoSpeakers = async (videoId: number): Promise<Speaker[]> => {
  const { data } = await api.get(`/speakers/${videoId}`);
  return data;
};

// ============================================================================
// Phase 3: Multi-Model Support
// ============================================================================

/**
 * Get available transcription models and backends.
 */
export const getAvailableModels = async (): Promise<ModelsResponse> => {
  const { data } = await api.get("/models");
  return data;
};

/**
 * Transcribe a video with specific model/backend.
 */
export const transcribeVideo = async (
  videoId: number,
  options?: {
    model?: string;
    backend?: string;
    language?: string;
    force?: boolean;
  }
): Promise<{ status: string; video_id: number }> => {
  const { data } = await api.post(`/transcribe/${videoId}`, null, {
    params: options,
  });
  return data;
};

// ============================================================================
// Phase 3: Subtitle Styles
// ============================================================================

/**
 * Get available subtitle style presets.
 */
export const getSubtitlePresets = async (): Promise<SubtitlePresets> => {
  const { data } = await api.get("/subtitle-presets");
  return data;
};

// ============================================================================
// Media Serving
// ============================================================================

/**
 * Get the URL for streaming a video.
 */
export const getMediaUrl = (videoId: number): string => {
  return `${API_BASE_URL}/media/${videoId}`;
};

// ============================================================================
// Error Handling
// ============================================================================

/**
 * Check if an error is a network/connection error.
 */
export const isConnectionError = (error: unknown): boolean => {
  if (axios.isAxiosError(error)) {
    return error.code === "ECONNREFUSED" || error.code === "ERR_NETWORK";
  }
  return false;
};

/**
 * Get error message from API error.
 */
export const getErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    if (error.response?.data?.detail) {
      return error.response.data.detail;
    }
    if (error.message) {
      return error.message;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "An unknown error occurred";
};

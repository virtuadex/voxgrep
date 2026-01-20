/**
 * VoxGrep Type Definitions
 * 
 * Shared types for the desktop application.
 */

// ============================================================================
// Core Types
// ============================================================================

export interface SearchMatch {
  file: string;
  start: number;
  end: number;
  content: string;
  score?: number;
  speaker?: string;  // Phase 2: Speaker label
  video_id?: number;
}

export interface VideoFile {
  id?: number;
  path: string;
  filename: string;
  size_bytes: number;
  duration: number;
  created_at: number;
  has_transcript: boolean;
  transcript_path?: string;
  // Phase 2
  has_diarization?: boolean;
  diarization_path?: string;
  is_indexed?: boolean;
  indexed_at?: number;
}

export interface NGramMatch {
  ngram: string;
  count: number;
}

// ============================================================================
// Phase 2: Vector Search & Speakers
// ============================================================================

export interface VectorStats {
  total_embeddings: number;
  indexed_videos: number;
  embedding_dim: number;
  model_name: string | null;
}

export interface Speaker {
  id: number;
  video_id: number;
  speaker_label: string;
  display_name?: string;
  total_duration: number;
  segment_count: number;
}

// ============================================================================
// Phase 3: Transcription Models
// ============================================================================

export interface TranscriptionModel {
  name: string;
  backend: string;
  description: string;
  is_available: boolean;
  requires_gpu: boolean;
  estimated_speed: string;
}

export interface TranscriptionBackend {
  backend: string;
  available: boolean;
  is_default: boolean;
}

export interface ModelsResponse {
  models: TranscriptionModel[];
  backends: TranscriptionBackend[];
}

// ============================================================================
// Phase 3: Subtitle Styles
// ============================================================================

export interface SubtitleStyle {
  font: string;
  fontsize: number;
  color: string;
  stroke_color?: string;
  stroke_width: number;
  bg_color?: string;
  position: "bottom" | "top" | "center";
  margin_bottom: number;
  margin_top: number;
  max_width_ratio: number;
}

export interface SubtitlePresets {
  [key: string]: SubtitleStyle;
}

// ============================================================================
// Export Types
// ============================================================================

export type TransitionType = "cut" | "crossfade" | "fade_to_black" | "dissolve";

export interface ExportOptions {
  output: string;
  transition?: TransitionType;
  transition_duration?: number;
  burn_subtitles?: boolean;
  subtitle_preset?: string;
}

export interface ExportProgress {
  job_id: number;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  processed_clips: number;
  total_clips: number;
  error_message?: string;
}

// ============================================================================
// App State
// ============================================================================

export type AppStatus = 
  | "idle" 
  | "downloading" 
  | "transcribing" 
  | "indexing"
  | "diarizing"
  | "exporting" 
  | "error";

export interface AppFeatures {
  semantic_search: boolean;
  mlx_transcription: boolean;
  speaker_diarization: boolean;
}

export interface HealthResponse {
  status: string;
  version: string;
  features: AppFeatures;
}

// ============================================================================
// Search Types
// ============================================================================

export type SearchType = "sentence" | "fragment" | "mash" | "semantic";

export interface SearchParams {
  query: string;
  type: SearchType;
  threshold?: number;
  video_ids?: number[];
}
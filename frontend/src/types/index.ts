/**
 * TypeScript interfaces mirroring the chirply-ai backend Pydantic response schemas.
 * Source: backend/app/schemas/detection_schema.py
 */

// ─── Detection ───────────────────────────────────────────────────────────────

export interface Detection {
  id: string;
  timestamp: string; // ISO 8601 datetime string
  species_common: string;
  species_scientific: string;
  confidence: number; // 0.0 – 1.0
  audio_url: string;
  spectrogram_url: string;
}

export interface DetectionHistory {
  total: number;
  limit: number;
  offset: number;
  results: Detection[];
}

export interface SpeciesCount {
  common_name: string;
  count: number;
}

// ─── Health / System Status ───────────────────────────────────────────────────

export interface HardwareStatus {
  cpu_usage_percent: number;
  cpu_temperature_celsius: number;
  ram_used_mb: number;
  ram_total_mb: number;
  disk_free_percent: number;
}

export interface TelemetryStatus {
  uptime_seconds: number;
  total_processed_chunks: number;
  total_detections: number;
  last_run_timestamp: string | null;
  system_mode: string;
  database_path: string;
  recordings_dir: string;
  spectrograms_dir: string;
}

export interface SystemStatus {
  status: 'healthy' | 'degraded' | string;
  pipeline_active: boolean;
  hardware: HardwareStatus;
  microphone_level_db: number;
  telemetry: TelemetryStatus;
}

// ─── Stats ────────────────────────────────────────────────────────────────────

export interface StorageUtilization {
  recordings_count: number;
  recordings_size_bytes: number;
  spectrograms_count: number;
  spectrograms_size_bytes: number;
  database_size_bytes: number;
  disk_total_bytes: number;
  disk_used_bytes: number;
  disk_free_bytes: number;
  disk_free_percent: number;
}

export interface StatsResponse {
  total_detections: number;
  unique_species_count: number;
  most_frequent_species: SpeciesCount[];
  average_confidence: number;
  storage_utilization: StorageUtilization;
}

// ─── API Utility ─────────────────────────────────────────────────────────────

export interface ApiError {
  detail: string;
}

export interface DetectionFilters {
  limit?: number;
  offset?: number;
  min_confidence?: number;
  species?: string;
}

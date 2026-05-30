/**
 * Centralized API service layer for chirply-ai frontend.
 * All HTTP requests are made through this module — no direct fetch calls in components.
 *
 * Base URL is configured via Vite proxy: /api -> http://localhost:8000/api
 */

import type {
  SystemStatus,
  StatsResponse,
  DetectionHistory,
  Detection,
  SpeciesCount,
  DetectionFilters,
} from '../types';

const API_BASE = '/api/v1';

// ─── Generic fetch helper ─────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const err = await response.json();
      detail = err.detail ?? detail;
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

// ─── Health ───────────────────────────────────────────────────────────────────

/**
 * GET /api/v1/health
 * Returns system health including pipeline status, hardware metrics, and telemetry.
 */
export async function fetchHealth(): Promise<SystemStatus> {
  return apiFetch<SystemStatus>('/health');
}

// ─── Stats ────────────────────────────────────────────────────────────────────

/**
 * GET /api/v1/stats
 * Returns global detection statistics and storage utilization.
 */
export async function fetchStats(): Promise<StatsResponse> {
  return apiFetch<StatsResponse>('/stats');
}

// ─── Detections ───────────────────────────────────────────────────────────────

/**
 * GET /api/v1/detections
 * Returns paginated detections with optional filtering.
 */
export async function fetchDetections(filters: DetectionFilters = {}): Promise<DetectionHistory> {
  const params = new URLSearchParams();
  if (filters.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters.offset !== undefined) params.set('offset', String(filters.offset));
  if (filters.min_confidence !== undefined) params.set('min_confidence', String(filters.min_confidence));
  if (filters.species) params.set('species', filters.species);

  const query = params.toString() ? `?${params.toString()}` : '';
  return apiFetch<DetectionHistory>(`/detections${query}`);
}

/**
 * GET /api/v1/detections/:id
 * Returns a single detection by its unique identifier.
 */
export async function fetchDetectionById(id: string): Promise<Detection> {
  return apiFetch<Detection>(`/detections/${encodeURIComponent(id)}`);
}

/**
 * GET /api/v1/detections/summary/species
 * Returns aggregated species observation counts.
 */
export async function fetchSpeciesSummary(): Promise<SpeciesCount[]> {
  return apiFetch<SpeciesCount[]>('/detections/summary/species');
}

// ─── Media asset URL helpers ──────────────────────────────────────────────────

/**
 * Resolves a spectrogram URL returned by the backend API.
 * The backend already returns full /api/v1/spectrograms/<filename> paths.
 */
export function resolveSpectrogramUrl(url: string): string {
  if (!url) return '';
  // If already absolute, return as-is; otherwise prefix with origin
  if (url.startsWith('http')) return url;
  return url;
}

/**
 * Resolves an audio recording URL returned by the backend API.
 */
export function resolveAudioUrl(url: string): string {
  if (!url) return '';
  if (url.startsWith('http')) return url;
  return url;
}

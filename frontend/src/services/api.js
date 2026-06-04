/**
 * Chirply AI — API Service Layer
 */

const DEFAULT_PORT = 8000;

/**
 * Build the full base URL from a raw IP address input.
 * Handles cases like "192.168.1.10", "192.168.1.10:8000", "http://..."
 * @param {string} ip - Raw input from the user
 * @returns {string} Normalised base URL e.g. "http://192.168.1.10:8000"
 */
export function buildBaseUrl(ip) {
  let cleaned = ip.trim();
  // Strip any existing protocol
  cleaned = cleaned.replace(/^https?:\/\//, '');
  // Strip trailing slashes
  cleaned = cleaned.replace(/\/+$/, '');
  // If no port, append default
  if (!cleaned.includes(':')) {
    cleaned = `${cleaned}:${DEFAULT_PORT}`;
  }
  return `http://${cleaned}`;
}

/**
 * Ping the backend health endpoint to verify a device is reachable.
 * @param {string} ip - Raw IP address input from user
 * @returns {Promise<{ ok: boolean, data?: object, error?: string }>}
 */
export async function checkHealth(ip) {
  const baseUrl = buildBaseUrl(ip);
  try {
    const res = await fetch(`${baseUrl}/api/v1/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000), // 5s timeout
    });
    if (!res.ok) {
      return { ok: false, error: `Server responded with status ${res.status}` };
    }
    const data = await res.json();
    return { ok: true, data, baseUrl };
  } catch (err) {
    if (err.name === 'TimeoutError' || err.name === 'AbortError') {
      return { ok: false, error: 'Connection timed out. Check the IP and try again.' };
    }
    return { ok: false, error: 'Could not reach device. Check the IP and try again.' };
  }
}

/**
 * Persist a successfully connected device to localStorage.
 * @param {{ name: string, ip: string, baseUrl: string }} device
 */
export function saveRecentDevice(ip, baseUrl) {
  const existing = getRecentDevices();
  const updated = [
    { ip, baseUrl, lastSeen: Date.now() },
    ...existing.filter((d) => d.ip !== ip),
  ].slice(0, 5); // Keep at most 5 recent devices
  localStorage.setItem('chirply_recent_devices', JSON.stringify(updated));
}

/**
 * Read recent devices from localStorage.
 * @returns {Array<{ ip: string, baseUrl: string, lastSeen: number }>}
 */
export function getRecentDevices() {
  try {
    return JSON.parse(localStorage.getItem('chirply_recent_devices') || '[]');
  } catch {
    return [];
  }
}

/**
 * Format a "last seen" timestamp into a human-readable relative string.
 * @param {number} ts - Unix timestamp in ms
 * @returns {string}
 */
export function formatLastSeen(ts) {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}

// ─────────────────────────────────────────────────────────────
// Screen 2 — Dashboard API calls (all require a baseUrl)
// ─────────────────────────────────────────────────────────────

/**
 * Fetch paginated detection events.
 * @param {string} baseUrl
 * @param {{ limit?: number, offset?: number, min_confidence?: number, species?: string }} params
 */
export async function getDetections(baseUrl, params = {}) {
  const q = new URLSearchParams();
  if (params.limit)          q.set('limit', params.limit);
  if (params.offset)         q.set('offset', params.offset);
  if (params.min_confidence) q.set('min_confidence', params.min_confidence);
  if (params.species)        q.set('species', params.species);
  try {
    const res = await fetch(`${baseUrl}/api/v1/detections?${q}`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return { ok: false, data: null };
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, data: null };
  }
}

/**
 * Fetch hardware health diagnostics.
 * @param {string} baseUrl
 */
export async function getHealth(baseUrl) {
  try {
    const res = await fetch(`${baseUrl}/api/v1/health`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return { ok: false, data: null };
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, data: null };
  }
}

/**
 * Fetch aggregate analytics and storage stats.
 * @param {string} baseUrl
 */
export async function getStats(baseUrl) {
  try {
    const res = await fetch(`${baseUrl}/api/v1/stats`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return { ok: false, data: null };
    const data = await res.json();
    return { ok: true, data };
  } catch {
    return { ok: false, data: null };
  }
}

/**
 * Build a full URL to a spectrogram PNG.
 * @param {string} baseUrl
 * @param {string} spectrogramUrl - relative path e.g. "/api/v1/spectrograms/spec_xxx.png"
 */
export function spectrogramSrc(baseUrl, spectrogramUrl) {
  if (!spectrogramUrl) return null;
  return `${baseUrl}${spectrogramUrl}`;
}

/**
 * Build a full URL to a WAV recording.
 * @param {string} baseUrl
 * @param {string} audioUrl - relative path e.g. "/api/v1/recordings/rec_xxx.wav"
 */
export function audioSrc(baseUrl, audioUrl) {
  if (!audioUrl) return null;
  return `${baseUrl}${audioUrl}`;
}

/**
 * Format seconds into "1h 02m" or "45m" readable uptime string.
 * @param {number} seconds
 */
export function formatUptime(seconds) {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60) % 60;
  const h = Math.floor(seconds / 3600);
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m`;
  return `${m}m`;
}

/**
 * Format an ISO timestamp to a short UTC time string e.g. "16:45:02"
 * @param {string} isoString
 */
export function formatTime(isoString) {
  if (!isoString) return '—';
  try {
    return new Date(isoString).toISOString().slice(11, 19);
  } catch {
    return '—';
  }
}


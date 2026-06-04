import './DashboardPage.css';
import { useState, useEffect, useRef, useCallback } from 'react';
import { Settings, Square, SkipForward, Circle } from 'lucide-react';
import {
  getDetections, getHealth, getStats,
  spectrogramSrc, formatUptime, formatTime,
} from '../services/api.js';
import chirplyLogo from '../assets/chirply_logo.png';

const DETECTION_POLL_MS  = 3000;
const HEALTH_POLL_MS     = 8000;

// ── Shared Navbar ─────────────────────────────────────────────
function Navbar({ baseUrl, pipelineActive, onDisconnect }) {
  const ip = baseUrl.replace('http://', '');
  return (
    <nav className="navbar">
      <div className="nav-logo">
        <div className="nav-logo-mark">
          <img src={chirplyLogo} alt="Chirply" draggable="false"
            style={{ width: 14, height: 14, objectFit: 'contain', filter: 'invert(1)' }} />
        </div>
        <span className="nav-wordmark">Chirply</span>
      </div>
      <div className="nav-right">
        <div className={`status-pill ${pipelineActive ? 'status-pill--live' : ''}`}>
          <span className={`status-dot ${pipelineActive ? 'dot-live' : 'dot-warn'}`} />
          {ip} — {pipelineActive ? 'Live' : 'Degraded'}
        </div>
        <button className="nav-icon-btn" onClick={onDisconnect} title="Disconnect">
          <Settings size={14} />
        </button>
      </div>
    </nav>
  );
}

// ── Detection Card ────────────────────────────────────────────
function DetectionCard({ detection, baseUrl, isNew, onClick }) {
  const specSrc = spectrogramSrc(baseUrl, detection.spectrogram_url);
  const pct = Math.round(detection.confidence * 100);

  return (
    <button className={`detection-card ${isNew ? 'detection-card--new' : ''}`} onClick={onClick}>
      {isNew && <span className="new-badge">NEW</span>}

      {/* Mini spectrogram thumbnail */}
      <div className="card-spec-thumb">
        {specSrc
          ? <img src={specSrc} alt="spectrogram" className="card-spec-img" />
          : <div className="card-spec-placeholder" />}
      </div>

      {/* Species info */}
      <div className="card-info">
        <div className="card-common">{detection.species_common}</div>
        <div className="card-scientific">{detection.species_scientific}</div>
      </div>

      {/* Right: confidence + time */}
      <div className="card-right">
        <span className="card-confidence">{pct}%</span>
        <span className="card-time">{formatTime(detection.timestamp)} UTC</span>
      </div>
    </button>
  );
}

// ── Spectrogram Panel ─────────────────────────────────────────
function SpectrogramPanel({ latestDetection, baseUrl, pipelineActive, chunkCount }) {
  const specSrc = latestDetection ? spectrogramSrc(baseUrl, latestDetection.spectrogram_url) : null;

  return (
    <div className="bento-card spec-panel">
      {/* Header */}
      <div className="spec-panel-header">
        <div className="spec-panel-left">
          {pipelineActive && <span className="pulse-dot" />}
          <span className="spec-label">
            {pipelineActive ? 'Listening' : 'Idle'}
          </span>
          <span className="spec-sublabel">· 16 kHz mono · 128 mel bands</span>
        </div>
        <div className="spec-panel-right">
          {pipelineActive && (
            <div className="status-pill status-pill--live">
              <span className="status-dot dot-live" />
              BirdNET running
            </div>
          )}
        </div>
      </div>

      {/* Spectrogram image area */}
      <div className="spec-canvas-area">
        {specSrc ? (
          <img
            src={specSrc}
            alt={`Mel spectrogram — ${latestDetection.species_common}`}
            className="spec-image"
            key={specSrc} // re-render on new detection
          />
        ) : (
          <div className="spec-empty">
            <Circle size={18} strokeWidth={1} className="spec-empty-icon" />
            <span>Waiting for first detection…</span>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="spec-panel-footer">
        <span className="spec-foot-label">0.0 s</span>
        <span className="spec-foot-center">
          {chunkCount > 0 ? `chunk ${chunkCount.toLocaleString()} · ` : ''}
          auto-refreshes every 3 s
        </span>
        <span className="spec-foot-label">3.0 s</span>
      </div>
    </div>
  );
}

// ── Sidebar: Session Stats ────────────────────────────────────
function SessionStats({ stats, health }) {
  const uptime = health?.telemetry?.uptime_seconds ?? 0;
  return (
    <div className="bento-card sidebar-card">
      <div className="bento-card-header">Session</div>
      <div className="stats-grid">
        <div className="stat-cell">
          <div className="stat-num">{stats?.total_detections ?? '—'}</div>
          <div className="stat-lbl">Detections</div>
        </div>
        <div className="stat-cell">
          <div className="stat-num">{stats?.unique_species_count ?? '—'}</div>
          <div className="stat-lbl">Species</div>
        </div>
        <div className="stat-cell">
          <div className="stat-num">
            {stats?.average_confidence
              ? `${Math.round(stats.average_confidence * 100)}%`
              : '—'}
          </div>
          <div className="stat-lbl">Avg conf.</div>
        </div>
        <div className="stat-cell">
          <div className="stat-num">{uptime > 0 ? formatUptime(uptime) : '—'}</div>
          <div className="stat-lbl">Uptime</div>
        </div>
      </div>
    </div>
  );
}

// ── Sidebar: Pi Health ────────────────────────────────────────
function HealthBar({ label, value, max, unit, warn }) {
  const pct = max ? Math.min((value / max) * 100, 100) : value;
  const isWarn = warn && pct > warn;
  return (
    <div className="health-item">
      <div className="health-row">
        <span className="health-label">{label}</span>
        <span className={`health-val ${isWarn ? 'health-val--warn' : ''}`}>
          {value != null ? `${value}${unit ?? ''}` : '—'}
        </span>
      </div>
      <div className="health-track">
        <div
          className={`health-fill ${isWarn ? 'health-fill--warn' : ''}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function PiHealth({ health }) {
  const hw = health?.hardware;
  return (
    <div className="bento-card sidebar-card">
      <div className="bento-card-header">Pi Health</div>
      <div className="health-body">
        <HealthBar label="CPU"  value={hw?.cpu_usage_percent?.toFixed(0)}    unit="%" warn={80} />
        <HealthBar label="RAM"  value={hw?.ram_used_mb}   max={hw?.ram_total_mb} unit=" MB" warn={85} />
        <HealthBar label="Temp" value={hw?.cpu_temperature_celsius?.toFixed(1)} unit="°C" warn={70} />
        <HealthBar label="Disk" value={hw?.disk_free_percent?.toFixed(0)}    unit="% free" />
      </div>
    </div>
  );
}

// ── Sidebar: Top Species ──────────────────────────────────────
function TopSpecies({ stats }) {
  const species = stats?.most_frequent_species?.slice(0, 5) ?? [];
  return (
    <div className="bento-card sidebar-card">
      <div className="bento-card-header">Top Species</div>
      <div className="top-species-body">
        {species.length === 0 ? (
          <div className="top-species-empty">No detections yet</div>
        ) : (
          species.map((s, i) => (
            <div key={s.common_name} className="species-row">
              <span className="species-rank">{i + 1}</span>
              <span className="species-name">{s.common_name}</span>
              <span className="species-count">{s.count}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ── Pipeline Controls ─────────────────────────────────────────
function PipelineControls({ pipelineActive, chunkCount, mode }) {
  return (
    <div className="pipeline-controls">
      <button className={`ctrl-btn ${pipelineActive ? 'ctrl-btn--stop' : 'ctrl-btn--start'}`}>
        {pipelineActive ? <><Square size={11} /> Stop monitoring</> : <><Circle size={11} /> Start monitoring</>}
      </button>
      <button className="ctrl-btn ctrl-btn--ghost">
        <SkipForward size={11} /> Next chunk
      </button>
      <span className="pipeline-meta">
        {chunkCount > 0 ? `Chunk ${chunkCount.toLocaleString()} · ` : ''}
        3 s interval · BirdNET v2.4 · {mode === 'live' ? 'Live mic' : 'Mock mode'}
      </span>
    </div>
  );
}

// ── Dashboard Page ────────────────────────────────────────────
export default function DashboardPage({ baseUrl, initialHealth, onDisconnect, onSelectDetection }) {
  const [detections,  setDetections]  = useState([]);
  const [health,      setHealth]      = useState(initialHealth ?? null);
  const [stats,       setStats]       = useState(null);
  const [seenIds,     setSeenIds]     = useState(new Set());

  const detectionTimerRef = useRef(null);
  const healthTimerRef    = useRef(null);

  // ── Fetch detections ────────────────────────────────────────
  const fetchDetections = useCallback(async () => {
    const res = await getDetections(baseUrl, { limit: 15 });
    if (!res.ok || !res.data) return;
    setDetections(res.data.results ?? []);
  }, [baseUrl]);

  // ── Fetch health + stats ────────────────────────────────────
  const fetchHealthAndStats = useCallback(async () => {
    const [hRes, sRes] = await Promise.all([
      getHealth(baseUrl),
      getStats(baseUrl),
    ]);
    if (hRes.ok) setHealth(hRes.data);
    if (sRes.ok) setStats(sRes.data);
  }, [baseUrl]);

  // ── Polling setup ───────────────────────────────────────────
  useEffect(() => {
    fetchDetections();
    fetchHealthAndStats();

    detectionTimerRef.current = setInterval(fetchDetections, DETECTION_POLL_MS);
    healthTimerRef.current    = setInterval(fetchHealthAndStats, HEALTH_POLL_MS);

    return () => {
      clearInterval(detectionTimerRef.current);
      clearInterval(healthTimerRef.current);
    };
  }, [fetchDetections, fetchHealthAndStats]);

  // ── Track "new" detections (ids not in initial set) ─────────
  useEffect(() => {
    if (seenIds.size === 0 && detections.length > 0) {
      setSeenIds(new Set(detections.map((d) => d.id)));
    }
  }, [detections, seenIds.size]);

  const pipelineActive = health?.pipeline_active ?? false;
  const chunkCount     = health?.telemetry?.total_processed_chunks ?? 0;
  const mode           = health?.telemetry?.system_mode ?? 'mock';
  const latestDetection = detections[0] ?? null;

  const isNewDetection = (id) => seenIds.size > 0 && !seenIds.has(id);

  return (
    <div className="dashboard-page">
      <Navbar baseUrl={baseUrl} pipelineActive={pipelineActive} onDisconnect={onDisconnect} />

      <div className="dashboard-body">
        {/* ── MAIN COLUMN ──────────────────────────── */}
        <div className="dashboard-main">
          <PipelineControls
            pipelineActive={pipelineActive}
            chunkCount={chunkCount}
            mode={mode}
          />

          <SpectrogramPanel
            latestDetection={latestDetection}
            baseUrl={baseUrl}
            pipelineActive={pipelineActive}
            chunkCount={chunkCount}
          />

          {/* Detection Feed */}
          <div className="feed-section">
            <div className="feed-heading">
              Detection feed
              <span className="feed-sub">· polling every 3 s</span>
            </div>

            <div className="detection-feed">
              {detections.length === 0 ? (
                <div className="feed-empty">
                  <span>No detections yet — listening…</span>
                </div>
              ) : (
                detections.map((d) => (
                  <DetectionCard
                    key={d.id}
                    detection={d}
                    baseUrl={baseUrl}
                    isNew={isNewDetection(d.id)}
                    onClick={() => onSelectDetection(d)}
                  />
                ))
              )}
            </div>
          </div>
        </div>

        {/* ── SIDEBAR ──────────────────────────────── */}
        <aside className="dashboard-sidebar">
          <SessionStats stats={stats} health={health} />
          <PiHealth health={health} />
          <TopSpecies stats={stats} />
        </aside>
      </div>
    </div>
  );
}

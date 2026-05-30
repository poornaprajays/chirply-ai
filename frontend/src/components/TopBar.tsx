import React from 'react';
import { RefreshCw } from 'lucide-react';
import type { SystemStatus } from '../types';

interface TopBarProps {
  title: string;
  health: SystemStatus | null;
  loading: boolean;
  lastRefreshed: Date | null;
  onRefresh: () => void;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export const TopBar: React.FC<TopBarProps> = ({
  title,
  health,
  loading,
  lastRefreshed,
  onRefresh,
}) => {
  const status = health?.status ?? 'unknown';
  const pillClass = status === 'healthy' ? 'healthy' : status === 'degraded' ? 'degraded' : 'error';
  const pillLabel = status.toUpperCase();

  return (
    <header className="topbar">
      <span className="topbar-title">{title}</span>

      <div className="topbar-indicators">
        {health !== null && (
          <div className={`status-pill ${pillClass}`}>
            <div className="status-dot" />
            {pillLabel}
          </div>
        )}

        {lastRefreshed && (
          <span className="topbar-meta">
            Updated {formatTime(lastRefreshed)}
          </span>
        )}

        <button
          id="btn-refresh"
          className={`refresh-btn${loading ? ' spinning' : ''}`}
          onClick={onRefresh}
          disabled={loading}
        >
          <RefreshCw size={13} />
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>
    </header>
  );
};

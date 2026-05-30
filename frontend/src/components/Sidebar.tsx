import React from 'react';
import {
  LayoutDashboard,
  Bird,
  BarChart3,
  Activity,
  Cpu,
  ChevronRight,
} from 'lucide-react';

export type PageId = 'dashboard' | 'detections' | 'stats';

interface SidebarProps {
  activePage: PageId;
  onNavigate: (page: PageId) => void;
  pipelineActive: boolean;
}

const NAV_ITEMS: { id: PageId; label: string; icon: React.FC<{ size?: number }> }[] = [
  { id: 'dashboard',  label: 'Dashboard',  icon: LayoutDashboard },
  { id: 'detections', label: 'Detections', icon: Bird },
  { id: 'stats',      label: 'Analytics',  icon: BarChart3 },
];

export const Sidebar: React.FC<SidebarProps> = ({ activePage, onNavigate, pipelineActive }) => {
  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <Bird size={18} />
        </div>
        <div className="sidebar-logo-text">
          <span className="brand-name">Chirply</span>
          <span className="brand-tag">Ecoacoustic AI</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <div className="nav-section-label">Navigation</div>
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            id={`nav-${id}`}
            className={`nav-item${activePage === id ? ' active' : ''}`}
            onClick={() => onNavigate(id)}
          >
            <Icon size={16} />
            <span>{label}</span>
            {activePage === id && <ChevronRight size={12} style={{ marginLeft: 'auto', opacity: 0.5 }} />}
          </button>
        ))}

        <div className="nav-section-label" style={{ marginTop: '16px' }}>System</div>
        <div className="nav-item" style={{ cursor: 'default', opacity: 0.7 }}>
          <Activity size={16} />
          <span>Pipeline</span>
          <span style={{
            marginLeft: 'auto',
            fontSize: '0.65rem',
            fontWeight: 700,
            color: pipelineActive ? 'var(--status-healthy)' : 'var(--status-degraded)',
          }}>
            {pipelineActive ? 'LIVE' : 'IDLE'}
          </span>
        </div>
        <div className="nav-item" style={{ cursor: 'default', opacity: 0.7 }}>
          <Cpu size={16} />
          <span>Hardware</span>
          <span style={{
            marginLeft: 'auto',
            fontSize: '0.65rem',
            color: 'var(--text-muted)',
          }}>
            RPi
          </span>
        </div>
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="version-badge">chirply-ai v0.1.0</div>
      </div>
    </aside>
  );
};

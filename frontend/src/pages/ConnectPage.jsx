import './ConnectPage.css';
import { useState, useEffect } from 'react';
import { Settings, Cpu, Wifi, WifiOff, ArrowRight, Clock } from 'lucide-react';
import { checkHealth, saveRecentDevice, getRecentDevices, formatLastSeen } from '../services/api.js';
import birdHero from '../assets/bird_hero.png';
import chirplyLogo from '../assets/chirply_logo.png';

/* ── Bento Logo Mark ────────────────────────────────────────── */
function LogoMark() {
  return (
    <div className="nav-logo-mark">
      {/* Swallow logo — inverted to white on black nav background */}
      <img
        src={chirplyLogo}
        alt="Chirply swallow logo"
        style={{ width: '16px', height: '16px', objectFit: 'contain', filter: 'invert(1)' }}
        draggable="false"
      />
    </div>
  );
}

/* ── Navbar ─────────────────────────────────────────────────── */
function Navbar({ connected }) {
  return (
    <nav className="navbar">
      <div className="nav-logo">
        <LogoMark />
        <span className="nav-wordmark">Chirply</span>
      </div>
      <div className="nav-right">
        <div className="status-pill">
          <span className={`status-dot ${connected ? 'dot-live' : 'dot-idle'}`} />
          {connected ? 'Connected' : 'Not connected'}
        </div>
        <button className="nav-icon-btn" aria-label="Settings">
          <Settings size={14} />
        </button>
      </div>
    </nav>
  );
}

/* ── Device Row ─────────────────────────────────────────────── */
function DeviceRow({ device, onSelect }) {
  const isRecent = Date.now() - device.lastSeen < 600000; // < 10 min = "recent"
  const label = formatLastSeen(device.lastSeen);

  return (
    <button
      className="device-row"
      onClick={() => onSelect(device.ip)}
      aria-label={`Connect to ${device.ip}`}
    >
      <div className="device-icon-wrap">
        <Cpu size={14} />
      </div>
      <div className="device-info">
        <div className="device-ip">{device.ip}</div>
        <div className="device-sub">port 8000</div>
      </div>
      <div className={`device-badge ${isRecent ? 'badge-active' : 'badge-stale'}`}>
        <Clock size={10} />
        {label}
      </div>
      <ArrowRight size={12} className="device-arrow" />
    </button>
  );
}

/* ── Connect Page ───────────────────────────────────────────── */
export default function ConnectPage({ onConnected }) {
  const [ip, setIp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [recentDevices, setRecentDevices] = useState([]);

  useEffect(() => {
    setRecentDevices(getRecentDevices());
  }, []);

  async function handleConnect(targetIp) {
    const value = (targetIp ?? ip).trim();
    if (!value) {
      setError('Please enter an IP address.');
      return;
    }
    setError('');
    setLoading(true);
    const result = await checkHealth(value);
    setLoading(false);

    if (result.ok) {
      saveRecentDevice(value, result.baseUrl);
      onConnected(result.baseUrl, result.data);
    } else {
      setError(result.error);
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') handleConnect();
  }

  return (
    <div className="connect-page">
      {/* ── LEFT PANEL ────────────────────────────── */}
      <div className="connect-left">
        <Navbar connected={false} />

        <div className="connect-content">

          {/* ── Connection Bento Card ─────────────── */}
          <div className="bento-card connect-card animate-fade-up">
            <div className="bento-card-header">Raspberry Pi Connection</div>

            <div className="connect-card-body">
              {/* Icon + title */}
              <div className="connect-hero">
                <div className="connect-icon-wrap">
                  <Cpu size={22} strokeWidth={1.5} />
                </div>
                <div>
                  <h1 className="connect-title">Connect your device</h1>
                  <p className="connect-subtitle">
                    Enter the local IP address of your Raspberry Pi running
                    the Chirply backend on port 8000.
                  </p>
                </div>
              </div>

              {/* Input + button row */}
              <div className="connect-form">
                <label className="form-label" htmlFor="ip-input">
                  Raspberry Pi IP Address
                </label>
                <div className="input-row">
                  <input
                    id="ip-input"
                    className={`form-input${error ? ' error' : ''}`}
                    type="text"
                    placeholder="192.168.1.XX"
                    value={ip}
                    onChange={(e) => { setIp(e.target.value); setError(''); }}
                    onKeyDown={handleKeyDown}
                    disabled={loading}
                    autoComplete="off"
                    spellCheck="false"
                  />
                  <button
                    id="connect-btn"
                    className="btn btn-primary connect-btn"
                    onClick={() => handleConnect()}
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <span className="spinner" />
                        Connecting
                      </>
                    ) : (
                      <>
                        <Wifi size={13} />
                        Connect
                      </>
                    )}
                  </button>
                </div>

                {/* Error message */}
                {error && (
                  <div className="connect-error" role="alert">
                    <WifiOff size={11} />
                    {error}
                  </div>
                )}

                <p className="annotation" style={{ marginTop: '8px' }}>
                  Polls GET /api/v1/health to verify connection before proceeding
                </p>
              </div>
            </div>
          </div>

          {/* ── Recent Devices Bento Card ─────────── */}
          {recentDevices.length > 0 && (
            <div
              className="bento-card recent-card animate-fade-up"
              style={{ animationDelay: '60ms' }}
            >
              <div className="bento-card-header">Recent Devices</div>
              <div className="recent-devices-list">
                {recentDevices.map((device) => (
                  <DeviceRow
                    key={device.ip}
                    device={device}
                    onSelect={(selectedIp) => {
                      setIp(selectedIp);
                      handleConnect(selectedIp);
                    }}
                  />
                ))}
              </div>
            </div>
          )}

          {/* ── Bottom annotation ─────────────────── */}
          <p className="annotation bottom-annotation animate-fade-up"
            style={{ animationDelay: '120ms' }}>
            Make sure your device and this browser are on the same local network.
          </p>

        </div>
      </div>

      {/* ── RIGHT PANEL — Bird photo ───────────────── */}
      <div className="connect-right">
        <img
          src={birdHero}
          alt="A vibrant blue bird perched on a branch — Chirply AI detects birds like this in real time"
          className="bird-hero-img"
          draggable="false"
        />
        <div className="bird-overlay">
          <div className="bird-caption">
            <span className="bird-caption-label">Real-time acoustic detection</span>
            <span className="bird-caption-sub">powered by BirdNET on Raspberry Pi</span>
          </div>
        </div>
      </div>
    </div>
  );
}

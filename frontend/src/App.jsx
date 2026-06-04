import { useState } from 'react';
import ConnectPage from './pages/ConnectPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';

/**
 * App root — manages which screen is currently shown.
 * Screen routing:
 *   'connect'   → Screen 1: Device Connection
 *   'dashboard' → Screen 2: Live Monitoring
 *   'detail'    → Screen 3: Detection Detail (coming later)
 */
export default function App() {
  const [screen, setScreen] = useState('connect');
  const [connection, setConnection] = useState(null); // { baseUrl, healthData }

  function handleConnected(baseUrl, healthData) {
    setConnection({ baseUrl, healthData });
    setScreen('dashboard');
  }

  if (screen === 'connect') {
    return <ConnectPage onConnected={handleConnected} />;
  }

  if (screen === 'dashboard') {
    return (
      <DashboardPage
        baseUrl={connection?.baseUrl}
        initialHealth={connection?.healthData}
        onDisconnect={() => {
          setScreen('connect');
          setConnection(null);
        }}
        onSelectDetection={(det) => {
          console.log('Selected detection:', det);
          // Future Screen 3 details transition can go here
        }}
      />
    );
  }

  return null;
}

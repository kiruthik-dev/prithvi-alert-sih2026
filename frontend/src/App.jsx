import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import Header from './components/Header';
import RiskSidebar from './components/RiskSidebar';
import RiskMap from './components/RiskMap';
import ZoneDetails from './components/ZoneDetails';
import RiskSummary from './components/RiskSummary';
import AlertBanner from './components/AlertBanner';
import Chatbot from './components/Chatbot';
import WarningWidget from './components/WarningWidget';
import CitizenWarningBanner from './components/CitizenWarningBanner';
import { fetchRiskZones, triggerDemoScenario, WS_URL, API_BASE_URL } from './services/api';

export default function App() {
  const [zones, setZones] = useState([]);
  const [selectedZone, setSelectedZone] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [demoMode, setDemoMode] = useState('NORMAL');
  const [simulationMode, setSimulationMode] = useState(false);
  const [userLocation, setUserLocation] = useState(null);
  const [proximityAlert, setProximityAlert] = useState(null);
  const [publicWarning, setPublicWarning] = useState(null);
  const [userId, setUserId] = useState("fallback-user-uuid");
  const wsRef = useRef(null);

  // Dummy auto-registration to simulate logged-in user on mount
  useEffect(() => {
    fetch(`${API_BASE_URL}/api/v1/citizens/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: "Demo User", phone: "+91-9999999999", language: "en" })
    })
      .then(r => r.json())
      .then(d => setUserId(d.id))
      .catch(e => console.error(e));
  }, []);

  const loadZones = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRiskZones();
      setZones(data);
      if (data && data.length > 0) {
        const sorted = [...data].sort((a, b) => b.risk_score - a.risk_score);
        setSelectedZone(prev => prev || sorted[0]);
      }
    } catch (err) {
      console.error('Failed to fetch risk zones:', err);
      setError(err.message || 'Backend connection unavailable');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadZones();
  }, [loadZones]);

  const handleDemoTrigger = async (mode) => {
    setDemoMode(mode);
    try {
      await triggerDemoScenario(mode);
      await loadZones();
    } catch (err) {
      console.error('Demo trigger failed:', err);
    }
  };

  useEffect(() => {
    if (userLocation) {
      if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
        wsRef.current = new WebSocket(WS_URL);
        wsRef.current.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.type === 'WARNING') {
            setPublicWarning(data);
          } else if (data.status === 'DANGER') {
            setProximityAlert(data);
          } else {
            setProximityAlert(null);
          }
        };
      }
      
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ ...userLocation, user_id: userId }));
      } else {
        wsRef.current.onopen = () => {
          wsRef.current.send(JSON.stringify({ ...userLocation, user_id: userId }));
        };
      }
    } else {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setProximityAlert(null);
    }
  }, [userLocation]);

  useEffect(() => {
    let interval;
    if (simulationMode && userLocation) {
      // Move slightly north-east towards Gangtok every 2 seconds
      interval = setInterval(() => {
        setUserLocation(prev => ({
          lat: prev.lat + 0.05,
          lon: prev.lon + 0.05
        }));
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [simulationMode, userLocation]);

  // Sort zones by risk score descending
  const sortedZones = useMemo(() => {
    return [...zones].sort((a, b) => b.risk_score - a.risk_score);
  }, [zones]);

  const handleSelectZone = useCallback((zone) => {
    setSelectedZone(zone);
  }, []);

  const handleAcknowledgeWarning = async (notificationId) => {
    try {
      await fetch(`${API_BASE_URL}/api/v1/alerts/acknowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notification_id: notificationId })
      });
      setPublicWarning(null);
    } catch (e) {
      console.error(e);
      setPublicWarning(null);
    }
  };

  return (
    <>
      <CitizenWarningBanner warning={publicWarning} onAcknowledge={handleAcknowledgeWarning} />
      <AlertBanner alert={proximityAlert} onDismiss={() => setProximityAlert(null)} />
      {/* Header */}
      <Header 
        demoMode={demoMode} 
        onDemoTrigger={handleDemoTrigger} 
        simulationMode={simulationMode}
        setSimulationMode={setSimulationMode}
      />

      {/* Main content area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar — hidden on small screens */}
        <div className="hidden lg:flex">
          <RiskSidebar
            zones={sortedZones}
            selectedZone={selectedZone}
            onSelectZone={handleSelectZone}
            loading={loading}
            error={error}
          />
        </div>

        {/* Center map */}
        {error && !loading ? (
          <div className="flex-1 flex items-center justify-center bg-pa-dark">
            <div className="text-center p-8">
              <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" className="w-7 h-7 text-red-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-gray-200 mb-1">Backend Connection Unavailable</h2>
              <p className="text-sm text-gray-500 mb-4 max-w-md">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-lg text-sm font-medium hover:bg-blue-500/30 transition-colors"
              >
                Retry Connection
              </button>
            </div>
          </div>
        ) : loading ? (
          <div className="flex-1 flex items-center justify-center bg-pa-dark">
            <div className="flex flex-col items-center gap-3">
              <div className="w-10 h-10 border-3 border-blue-400/30 border-t-blue-400 rounded-full animate-spin"></div>
              <p className="text-sm text-gray-500">Loading risk zone data…</p>
            </div>
          </div>
        ) : (
          <RiskMap
            zones={sortedZones}
            selectedZone={selectedZone}
            onSelectZone={handleSelectZone}
            userLocation={userLocation}
            setUserLocation={setUserLocation}
            simulationMode={simulationMode}
          />
        )}

        {/* Right detail panel — hidden on small screens */}
        <div className="hidden xl:flex flex-col gap-4 p-4 min-w-[320px] max-w-[320px] overflow-y-auto">
          <WarningWidget />
          <ZoneDetails zone={selectedZone} />
        </div>
      </div>

      {/* Mobile zone detail overlay — only show when selected on small screens */}
      {selectedZone && (
        <div className="xl:hidden fixed bottom-16 left-0 right-0 z-[1001] px-2">
          <div className="bg-pa-card border border-pa-border rounded-t-xl p-4 shadow-2xl max-h-[40vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-bold text-white">{selectedZone.name}</h3>
              <button
                onClick={() => setSelectedZone(null)}
                className="text-gray-500 hover:text-gray-300 text-lg"
              >
                ✕
              </button>
            </div>
            <p className="text-[11px] text-gray-400">{selectedZone.district}, {selectedZone.state}</p>
            <div className="mt-2 flex items-center gap-2">
              <span className="text-xl font-bold font-mono" style={{ color: getRiskColorFromLevel(selectedZone.risk_level) }}>
                {selectedZone.risk_score}
              </span>
              <span className={`risk-badge ${getBadge(selectedZone.risk_level)}`}>{selectedZone.risk_level}</span>
            </div>
          </div>
        </div>
      )}

      {/* Bottom KPI bar */}
      <RiskSummary zones={sortedZones} />

      {/* Floating Chatbot */}
      <Chatbot userLocation={userLocation} />
    </>
  );
}

// Tiny helpers used only in the mobile overlay
function getRiskColorFromLevel(level) {
  const m = { LOW: '#22c55e', MODERATE: '#eab308', HIGH: '#f97316', 'VERY HIGH': '#ef4444', CRITICAL: '#dc2626' };
  return m[level] || '#6b7280';
}
function getBadge(level) {
  const m = { LOW: 'risk-badge-low', MODERATE: 'risk-badge-moderate', HIGH: 'risk-badge-high', 'VERY HIGH': 'risk-badge-very-high', CRITICAL: 'risk-badge-critical' };
  return m[level] || 'risk-badge-low';
}

import React, { useEffect, useState } from 'react';

export default function WarningWidget() {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/v1/alerts/history');
        if (res.ok) {
          const data = await res.json();
          setHistory(data);
        }
      } catch (err) {
        console.error("Failed to fetch alert history");
      }
    };
    
    // Fetch initially and then every 10s
    fetchHistory();
    const interval = setInterval(fetchHistory, 10000);
    return () => clearInterval(interval);
  }, []);

  const activeCount = history.filter(h => h.status === 'MOCK_SMS' && !h.acknowledged).length;

  return (
    <div className="bg-pa-card border border-pa-border rounded-xl p-4 flex flex-col h-full shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-bold text-white flex items-center gap-2 uppercase tracking-wider">
          <span className="text-orange-500">📢</span> Public Warning Status
        </h2>
        <span className="text-[10px] text-gray-400 bg-gray-800 px-2 py-0.5 rounded">LIVE</span>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-4">
        <div className="bg-[#0a0f1a] p-3 rounded-lg border border-gray-800 text-center">
          <p className="text-[10px] text-gray-500 uppercase">Active / Pending</p>
          <p className={`text-xl font-bold ${activeCount > 0 ? 'text-orange-500' : 'text-gray-300'}`}>
            {activeCount}
          </p>
        </div>
        <div className="bg-[#0a0f1a] p-3 rounded-lg border border-gray-800 text-center">
          <p className="text-[10px] text-gray-500 uppercase">Total Sent</p>
          <p className="text-xl font-bold text-gray-300">{history.length}</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto pr-1">
        <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-2 sticky top-0 bg-pa-card pb-1">Recent Alerts</p>
        {history.length === 0 ? (
          <p className="text-xs text-gray-500 italic text-center py-4">No recent public warnings.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {history.map((alert, i) => (
              <div key={i} className="bg-gray-800/50 p-2 rounded border border-gray-700/50 flex flex-col gap-1">
                <div className="flex justify-between items-start">
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded
                    ${alert.risk_level === 'CRITICAL' ? 'bg-red-500/20 text-red-400' : 
                      alert.risk_level === 'VERY HIGH' ? 'bg-orange-500/20 text-orange-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                    {alert.risk_level}
                  </span>
                  <span className="text-[9px] text-gray-500">{new Date(alert.created_at).toLocaleTimeString()}</span>
                </div>
                <p className="text-xs text-gray-300 line-clamp-2 mt-1">{alert.message}</p>
                <div className="flex justify-between items-center mt-1">
                  <span className="text-[9px] text-gray-400">Zone: {alert.zone_name}</span>
                  <span className={`text-[9px] ${alert.acknowledged ? 'text-green-400' : 'text-orange-400'}`}>
                    {alert.acknowledged ? 'ACKNOWLEDGED' : 'PENDING'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

import React from 'react';
import { getRiskBadgeClass, getRiskColor } from '../services/api';

export default function RiskSidebar({ zones, selectedZone, onSelectZone, loading, error }) {
  return (
    <aside className="w-72 xl:w-80 bg-pa-card border-r border-pa-border flex flex-col flex-shrink-0 overflow-hidden">
      {/* Sidebar header */}
      <div className="px-4 py-3 border-b border-pa-border flex-shrink-0">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-200 tracking-wide uppercase">Risk Zones</h2>
          <span className="text-[10px] bg-pa-accent/15 text-blue-400 px-2 py-0.5 rounded-full font-medium">
            {zones.length} zones
          </span>
        </div>
        <p className="text-[10px] text-gray-500 mt-0.5">Sorted by risk score (highest first)</p>
      </div>

      {/* Zone list */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
        {loading && (
          <div className="flex items-center justify-center h-32">
            <div className="flex flex-col items-center gap-2">
              <div className="w-6 h-6 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin"></div>
              <p className="text-xs text-gray-500">Loading zones…</p>
            </div>
          </div>
        )}

        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-center">
            <p className="text-xs text-red-400 font-medium">⚠ Backend connection unavailable</p>
            <p className="text-[10px] text-red-400/60 mt-1">{error}</p>
          </div>
        )}

        {!loading && !error && zones.length === 0 && (
          <div className="p-3 text-center">
            <p className="text-xs text-gray-500">No risk zones available</p>
          </div>
        )}

        {zones.map((zone) => {
          const isSelected = selectedZone?.id === zone.id;
          const riskColor = getRiskColor(zone.risk_level);
          return (
            <button
              key={zone.id}
              id={`zone-card-${zone.id}`}
              onClick={() => onSelectZone(zone)}
              className={`w-full text-left p-3 rounded-lg border transition-all duration-200 group
                ${isSelected
                  ? 'bg-blue-500/10 border-blue-500/30 shadow-sm shadow-blue-500/5'
                  : 'bg-pa-dark/50 border-pa-border hover:bg-pa-dark hover:border-gray-600'
                }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-gray-200 truncate group-hover:text-white transition-colors">
                    {zone.name}
                  </h3>
                  <p className="text-[11px] text-gray-500 mt-0.5">
                    {zone.district}, {zone.state}
                  </p>
                </div>
                <div
                  className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0"
                  style={{ backgroundColor: riskColor, boxShadow: `0 0 6px ${riskColor}40` }}
                />
              </div>
              <div className="flex items-center justify-between mt-2">
                <span className="text-lg font-bold text-gray-100 font-mono">{zone.risk_score}</span>
                <span className={`risk-badge ${getRiskBadgeClass(zone.risk_level)}`}>
                  {zone.risk_level}
                </span>
              </div>
            </button>
          );
        })}
      </div>

      {/* Threshold legend */}
      <div className="px-4 py-2.5 border-t border-pa-border flex-shrink-0">
        <p className="text-[9px] text-gray-600 text-center italic">
          ⓘ Prototype decision thresholds — not scientifically validated
        </p>
      </div>
    </aside>
  );
}

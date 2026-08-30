import React from 'react';
import { getRiskBadgeClass, getRiskColor, getRecommendation } from '../services/api';

export default function ZoneDetails({ zone }) {
  if (!zone) {
    return (
      <aside className="w-72 xl:w-80 bg-pa-card border-l border-pa-border flex flex-col flex-shrink-0 overflow-hidden">
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center">
            <div className="w-12 h-12 rounded-full bg-pa-dark border border-pa-border flex items-center justify-center mx-auto mb-3">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-gray-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 16v-4" />
                <path d="M12 8h.01" />
              </svg>
            </div>
            <p className="text-xs text-gray-500">Select a risk zone to view details</p>
          </div>
        </div>
      </aside>
    );
  }

  const riskColor = getRiskColor(zone.risk_level);

  return (
    <aside className="w-72 xl:w-80 bg-pa-card border-l border-pa-border flex flex-col flex-shrink-0 overflow-y-auto">
      {/* Zone header */}
      <div className="p-4 border-b border-pa-border">
        <div className="flex items-start gap-2">
          <div
            className="w-3 h-3 rounded-full mt-1 flex-shrink-0"
            style={{ backgroundColor: riskColor, boxShadow: `0 0 8px ${riskColor}50` }}
          />
          <div>
            <h2 className="text-sm font-bold text-white leading-snug">{zone.name}</h2>
            <p className="text-[11px] text-gray-400 mt-0.5">{zone.district}, {zone.state}</p>
          </div>
        </div>
      </div>

      {/* Risk score */}
      <div className="p-4 border-b border-pa-border">
        <p className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold mb-2">Risk Assessment</p>
        <div className="flex items-end gap-3">
          <span className="text-3xl font-bold font-mono" style={{ color: riskColor }}>
            {zone.risk_score}
          </span>
          <span className={`risk-badge ${getRiskBadgeClass(zone.risk_level)} mb-1`}>
            {zone.risk_level}
          </span>
        </div>
        {/* Risk bar */}
        <div className="mt-3 h-1.5 bg-pa-dark rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${Math.min(zone.risk_score, 100)}%`,
              backgroundColor: riskColor,
              boxShadow: `0 0 8px ${riskColor}60`,
            }}
          />
        </div>
      </div>

      {/* Environmental data */}
      <div className="p-4 border-b border-pa-border">
        <p className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold mb-3">Environment</p>
        <div className="space-y-2.5">
          <DetailRow label="Rainfall 24h" value={`${zone.rainfall_24h} mm`} />
          <DetailRow label="Soil Moisture" value={`${zone.soil_moisture}%`} />
          <DetailRow label="Slope Angle" value={`${zone.slope_angle}°`} />
          <DetailRow label="Historical Factor" value={zone.historical_factor} />
        </div>
      </div>

      {/* Location */}
      <div className="p-4 border-b border-pa-border">
        <p className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold mb-3">Location</p>
        <div className="space-y-2.5">
          <DetailRow label="Latitude" value={zone.latitude?.toFixed(6) ?? 'N/A'} />
          <DetailRow label="Longitude" value={zone.longitude?.toFixed(6) ?? 'N/A'} />
        </div>
      </div>

      {/* Recommendation */}
      <div className="p-4">
        <p className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold mb-2">
          Decision-Support Recommendation
        </p>
        <div className="p-3 rounded-lg border" style={{ borderColor: `${riskColor}30`, backgroundColor: `${riskColor}08` }}>
          <p className="text-sm font-semibold" style={{ color: riskColor }}>
            {getRecommendation(zone.risk_level)}
          </p>
        </div>
        <p className="text-[9px] text-gray-600 mt-2 italic text-center">
          ⓘ Prototype decision thresholds — not scientifically validated
        </p>
      </div>
    </aside>
  );
}

function DetailRow({ label, value }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[11px] text-gray-500">{label}</span>
      <span className="text-[11px] text-gray-200 font-mono font-medium">{value}</span>
    </div>
  );
}

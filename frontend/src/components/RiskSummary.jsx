import React, { useMemo } from 'react';
import { getRiskBadgeClass } from '../services/api';

const LEVELS = ['CRITICAL', 'VERY HIGH', 'HIGH', 'MODERATE', 'LOW'];

export default function RiskSummary({ zones }) {
  const counts = useMemo(() => {
    const c = { CRITICAL: 0, 'VERY HIGH': 0, HIGH: 0, MODERATE: 0, LOW: 0 };
    zones.forEach((z) => {
      if (c[z.risk_level] !== undefined) c[z.risk_level]++;
    });
    return c;
  }, [zones]);

  const kpis = useMemo(() => {
    if (zones.length === 0) return { total: 0, critical: 0, highest: null, avg: 0 };
    const critical = counts['CRITICAL'];
    const sorted = [...zones].sort((a, b) => b.risk_score - a.risk_score);
    const avg = zones.reduce((s, z) => s + z.risk_score, 0) / zones.length;
    return {
      total: zones.length,
      critical,
      highest: sorted[0],
      avg: avg.toFixed(1),
    };
  }, [zones, counts]);

  return (
    <div className="bg-pa-card border-t border-pa-border px-4 py-3 flex-shrink-0">
      <div className="flex flex-wrap items-center gap-3 lg:gap-6">
        {/* Risk level counts */}
        <div className="flex items-center gap-2 flex-wrap">
          {LEVELS.map((lvl) => (
            <div key={lvl} className="flex items-center gap-1.5">
              <span className={`risk-badge ${getRiskBadgeClass(lvl)} text-[10px] px-2 py-0`}>
                {lvl}
              </span>
              <span className="text-sm font-bold text-gray-200 font-mono">{counts[lvl]}</span>
            </div>
          ))}
        </div>

        {/* Divider */}
        <div className="hidden lg:block w-px h-6 bg-pa-border" />

        {/* KPI cards */}
        <div className="flex items-center gap-3 flex-wrap ml-auto">
          <KpiChip label="Active Zones" value={kpis.total} />
          <KpiChip label="Critical" value={kpis.critical} highlight={kpis.critical > 0} />
          <KpiChip
            label="Highest Risk"
            value={kpis.highest ? `${kpis.highest.risk_score} — ${kpis.highest.name}` : 'N/A'}
          />
          <KpiChip label="Avg Score" value={kpis.avg} />
        </div>
      </div>
    </div>
  );
}

function KpiChip({ label, value, highlight = false }) {
  return (
    <div className="flex items-center gap-2 bg-pa-dark/60 border border-pa-border rounded-lg px-3 py-1.5">
      <span className="text-[10px] text-gray-500 uppercase tracking-wide font-medium whitespace-nowrap">{label}</span>
      <span className={`text-xs font-bold font-mono whitespace-nowrap ${highlight ? 'text-red-400' : 'text-gray-200'}`}>
        {value}
      </span>
    </div>
  );
}

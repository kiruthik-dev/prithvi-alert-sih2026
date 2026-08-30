import React from 'react';

export default function Header({ demoMode, onDemoTrigger, simulationMode, setSimulationMode }) {
  const modes = [
    { key: 'NORMAL', label: 'Normal', color: 'bg-green-500/20 text-green-400 border-green-500/40' },
    { key: 'HEAVY_RAIN', label: 'Heavy Rain', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40' },
    { key: 'CRITICAL', label: 'Critical', color: 'bg-red-500/20 text-red-400 border-red-500/40' },
  ];

  return (
    <header className="bg-pa-card border-b border-pa-border px-4 py-2.5 flex items-center justify-between flex-shrink-0 z-50">
      {/* Left: Branding */}
      <div className="flex items-center gap-3">
        {/* Logo icon */}
        <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
        </div>
        <div>
          <h1 className="text-base font-bold tracking-wider text-white leading-tight">
            PRITHVI<span className="text-blue-400">ALERT</span>
          </h1>
          <p className="text-[10px] text-gray-500 font-medium tracking-wide leading-tight hidden sm:block">
            AI-Powered Landslide Early Warning &amp; Response Platform
          </p>
        </div>
      </div>

      {/* Center: Live indicator */}
      <div className="hidden md:flex items-center gap-2">
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500"></span>
        </span>
        <span className="text-xs font-semibold text-green-400 tracking-wider uppercase">Live</span>
      </div>

      {/* Right: Demo controls */}
      <div className="flex items-center gap-1.5">
        <div className="h-4 w-px bg-pa-border mx-2"></div>
        <button
          onClick={() => setSimulationMode(!simulationMode)}
          className={`flex items-center gap-1.5 px-3 py-1 text-[11px] font-semibold rounded border transition-all duration-200
            ${simulationMode
              ? 'bg-blue-500/20 text-blue-400 border-blue-500/40 shadow-sm'
              : 'bg-transparent text-gray-500 border-pa-border hover:text-gray-300 hover:border-gray-600'
            }`}
          title="Simulate user movement"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="3 11 22 2 13 21 11 13 3 11"/>
          </svg>
          Simulate Movement
        </button>
        <span className="text-[10px] text-gray-500 mr-1 hidden lg:inline ml-2">Demo:</span>
        {modes.map((m) => (
          <button
            key={m.key}
            id={`demo-btn-${m.key.toLowerCase()}`}
            onClick={() => onDemoTrigger(m.key)}
            className={`px-3 py-1 text-[11px] font-semibold rounded border transition-all duration-200
              ${demoMode === m.key
                ? `${m.color} shadow-sm`
                : 'bg-transparent text-gray-500 border-pa-border hover:text-gray-300 hover:border-gray-600'
              }`}
            title={`Demo: ${m.label} — Phase 3 will connect POST /api/v1/demo/trigger`}
          >
            {m.label}
          </button>
        ))}
      </div>
    </header>
  );
}

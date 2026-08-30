import React from 'react';

export default function CitizenWarningBanner({ warning, onAcknowledge }) {
  if (!warning) return null;

  const isCritical = warning.risk_level === 'CRITICAL' || warning.risk_level === 'VERY HIGH';

  return (
    <div className="fixed inset-0 z-[3000] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className={`max-w-md w-full rounded-xl shadow-2xl border-2 overflow-hidden animate-in zoom-in-95 duration-300
        ${isCritical ? 'border-red-600 bg-red-950/90' : 'border-orange-500 bg-orange-950/90'}
      `}>
        <div className={`p-4 flex items-center gap-3 ${isCritical ? 'bg-red-600' : 'bg-orange-600'}`}>
          <span className="text-3xl">⚠️</span>
          <div>
            <h2 className="text-lg font-bold text-white tracking-wider">
              {isCritical ? 'CRITICAL PUBLIC WARNING' : 'PUBLIC WARNING'}
            </h2>
            <p className="text-xs text-white/80 font-mono">Issued: {new Date(warning.timestamp).toLocaleTimeString()}</p>
          </div>
        </div>
        
        <div className="p-6">
          <p className="text-white text-sm leading-relaxed whitespace-pre-wrap">
            {warning.message}
          </p>
          
          <div className="mt-4 pt-4 border-t border-white/10">
            <p className="text-[10px] text-gray-400 italic mb-4">
              This is a localized prototype warning based on your current location relative to a high-risk zone.
            </p>
            <button
              onClick={() => onAcknowledge(warning.notification_id)}
              className={`w-full py-3 rounded font-bold text-white tracking-widest transition-transform hover:scale-[1.02] active:scale-95
                ${isCritical ? 'bg-red-600 hover:bg-red-500' : 'bg-orange-600 hover:bg-orange-500'}
              `}
            >
              ACKNOWLEDGE
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

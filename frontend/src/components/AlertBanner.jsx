import React from 'react';

export default function AlertBanner({ alert, onDismiss }) {
  if (!alert) return null;

  return (
    <div className="fixed top-16 left-1/2 transform -translate-x-1/2 z-[2000] w-full max-w-2xl px-4 animate-in slide-in-from-top-4">
      <div className="bg-red-600 text-white shadow-2xl rounded-xl border-2 border-red-400 p-4 flex items-center justify-between overflow-hidden relative">
        {/* Flashing background effect */}
        <div className="absolute inset-0 bg-red-500 opacity-20 animate-pulse"></div>
        
        <div className="flex items-center gap-4 relative z-10">
          <div className="flex-shrink-0 w-12 h-12 bg-white/20 rounded-full flex items-center justify-center animate-bounce">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <h3 className="text-xl font-bold uppercase tracking-wider">Proximity Alert</h3>
            <p className="text-red-100 font-medium">
              You are {alert.distance_m}m from {alert.zone} (CRITICAL RISK ZONE). Evacuate immediately!
            </p>
          </div>
        </div>
        
        <button
          onClick={onDismiss}
          className="relative z-10 p-2 hover:bg-white/20 rounded-lg transition-colors flex-shrink-0"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}

import React, { useEffect, useRef, useState, useMemo } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, LayersControl, useMap, useMapEvents, Marker } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.heat';
import { getRiskColor, getRiskBadgeClass, getRecommendation } from '../services/api';

/* ── FlyTo helper: pans map when selectedZone changes ──────────── */
function FlyToZone({ zone }) {
  const map = useMap();
  useEffect(() => {
    if (zone?.latitude && zone?.longitude) {
      map.flyTo([zone.latitude, zone.longitude], 11, { duration: 1.2 });
    }
  }, [zone, map]);
  return null;
}

/* ── Heatmap layer (imperative, since react-leaflet has no wrapper) */
function HeatmapLayer({ zones, visible }) {
  const map = useMap();
  const heatRef = useRef(null);

  useEffect(() => {
    if (!visible) {
      if (heatRef.current) {
        map.removeLayer(heatRef.current);
        heatRef.current = null;
      }
      return;
    }

    const points = zones
      .filter((z) => z.latitude && z.longitude)
      .map((z) => [z.latitude, z.longitude, z.risk_score / 100]);

    if (heatRef.current) {
      map.removeLayer(heatRef.current);
    }

    heatRef.current = L.heatLayer(points, {
      radius: 35,
      blur: 25,
      maxZoom: 13,
      max: 1.0,
      gradient: {
        0.2: '#22c55e',
        0.4: '#eab308',
        0.6: '#f97316',
        0.8: '#ef4444',
        1.0: '#dc2626',
      },
    }).addTo(map);

    return () => {
      if (heatRef.current) {
        map.removeLayer(heatRef.current);
        heatRef.current = null;
      }
    };
  }, [zones, visible, map]);

  return null;
}

/* ── Map Click Handler ────────────────────────────────────────── */
function MapClickHandler({ setUserLocation }) {
  useMapEvents({
    click(e) {
      setUserLocation({ lat: e.latlng.lat, lon: e.latlng.lng });
    },
  });
  return null;
}

/* ── Main map component ────────────────────────────────────────── */
export default function RiskMap({ zones, selectedZone, onSelectZone, userLocation, setUserLocation, simulationMode }) {
  const [showHeatmap, setShowHeatmap] = useState(false);

  // NER center: roughly centered on the North-East Region
  const nerCenter = [25.5, 91.5];
  const defaultZoom = 7;

  // Marker radius scales with risk_score
  const getRadius = (score) => Math.max(6, Math.min(20, 6 + (score / 100) * 14));

  return (
    <div className="flex-1 relative">
      {/* Heatmap toggle floating control */}
      <div className="absolute top-3 right-3 z-[1000]">
        <button
          id="heatmap-toggle"
          onClick={() => setShowHeatmap(!showHeatmap)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all duration-200 shadow-lg backdrop-blur-sm
            ${showHeatmap
              ? 'bg-orange-500/20 text-orange-400 border-orange-500/40 shadow-orange-500/10'
              : 'bg-pa-card/90 text-gray-400 border-pa-border hover:text-gray-200 hover:border-gray-500'
            }`}
        >
          <span className="text-sm">{showHeatmap ? '🔥' : '🗺️'}</span>
          {showHeatmap ? 'Hide Heatmap' : 'Show Heatmap'}
        </button>
      </div>

      <MapContainer
        center={nerCenter}
        zoom={defaultZoom}
        className="w-full h-full"
        zoomControl={true}
        style={{ background: '#0a0f1a' }}
      >
        <LayersControl position="topright">
          <LayersControl.BaseLayer checked name="Street Map">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Satellite">
            <TileLayer
              attribution='&copy; <a href="https://www.esri.com">Esri</a>'
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            />
          </LayersControl.BaseLayer>
        </LayersControl>

        {/* Risk zone markers */}
        {zones.map((zone) => {
          if (!zone.latitude || !zone.longitude) return null;
          const color = getRiskColor(zone.risk_level);
          const isSelected = selectedZone?.id === zone.id;
          return (
            <CircleMarker
              key={zone.id}
              center={[zone.latitude, zone.longitude]}
              radius={getRadius(zone.risk_score)}
              pathOptions={{
                color: isSelected ? '#3b82f6' : color,
                fillColor: color,
                fillOpacity: 0.35,
                weight: isSelected ? 3 : 1.5,
                opacity: 0.9,
              }}
              eventHandlers={{
                click: () => onSelectZone(zone),
              }}
            >
              <Popup maxWidth={300} minWidth={240}>
                <div className="p-1">
                  <h3 className="text-sm font-bold text-white mb-1">{zone.name}</h3>
                  <p className="text-[11px] text-gray-400">{zone.district}, {zone.state}</p>

                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-xl font-bold font-mono" style={{ color }}>{zone.risk_score}</span>
                    <span className={`risk-badge ${getRiskBadgeClass(zone.risk_level)}`}>
                      {zone.risk_level}
                    </span>
                  </div>

                  <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
                    <span className="text-gray-500">Rainfall 24h</span>
                    <span className="text-gray-300 font-mono">{zone.rainfall_24h} mm</span>
                    <span className="text-gray-500">Soil Moisture</span>
                    <span className="text-gray-300 font-mono">{zone.soil_moisture}%</span>
                    <span className="text-gray-500">Slope Angle</span>
                    <span className="text-gray-300 font-mono">{zone.slope_angle}°</span>
                    <span className="text-gray-500">Historical</span>
                    <span className="text-gray-300 font-mono">{zone.historical_factor}</span>
                  </div>

                  <div className="mt-2 pt-2 border-t border-gray-700">
                    <p className="text-[10px] text-gray-500 italic">Decision-support recommendation</p>
                    <p className="text-[11px] font-semibold" style={{ color }}>
                      {getRecommendation(zone.risk_level)}
                    </p>
                  </div>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}

        <HeatmapLayer zones={zones} visible={showHeatmap} />
        <FlyToZone zone={selectedZone} />
        <MapClickHandler setUserLocation={setUserLocation} />
        
        {userLocation && (
          <CircleMarker
            center={[userLocation.lat, userLocation.lon]}
            radius={8}
            pathOptions={{ color: '#fff', fillColor: '#3b82f6', fillOpacity: 1, weight: 2 }}
          >
            <Popup>
              <div className="p-1">
                <h3 className="text-xs font-bold mb-1">Simulated GPS Location</h3>
                <p className="text-[10px]">Lat: {userLocation.lat.toFixed(4)}</p>
                <p className="text-[10px]">Lon: {userLocation.lon.toFixed(4)}</p>
              </div>
            </Popup>
          </CircleMarker>
        )}
      </MapContainer>
    </div>
  );
}

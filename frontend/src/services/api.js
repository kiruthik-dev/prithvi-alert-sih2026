const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Fetch all risk zones from the backend.
 * @returns {Promise<Array>} Array of risk zone objects
 */
export async function fetchRiskZones() {
  const response = await fetch(`${API_BASE_URL}/api/v1/risk-zones`);
  if (!response.ok) {
    throw new Error(`Backend error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

/**
 * Check backend health.
 * @returns {Promise<Object>}
 */
export async function fetchHealth() {
  const response = await fetch(`${API_BASE_URL}/api/v1/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  return response.json();
}

/**
 * Trigger demo scenario
 */
export async function triggerDemoScenario(scenario) {
  const response = await fetch(`${API_BASE_URL}/api/v1/demo/trigger`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario })
  });
  if (!response.ok) throw new Error('Demo trigger failed');
  return response.json();
}

/**
 * Check if location is inside a risk zone
 */
export async function checkLocation(lat, lon) {
  const response = await fetch(`${API_BASE_URL}/api/v1/spatial/check-location?lat=${lat}&lon=${lon}`);
  if (!response.ok) throw new Error('Check location failed');
  return response.json();
}

/**
 * Check proximity to risk zones
 */
export async function checkProximity(lat, lon, radius = 5000) {
  const response = await fetch(`${API_BASE_URL}/api/v1/spatial/check-proximity?lat=${lat}&lon=${lon}&radius_m=${radius}`);
  if (!response.ok) throw new Error('Check proximity failed');
  return response.json();
}

export const WS_URL = API_BASE_URL.replace(/^http/, 'ws') + '/ws/location';

/**
 * Derive the risk level label from a numeric score using prototype thresholds.
 * These are NOT scientifically validated — they are prototype decision thresholds.
 */
export function getRiskLevel(score) {
  if (score >= 81) return 'CRITICAL';
  if (score >= 61) return 'VERY HIGH';
  if (score >= 41) return 'HIGH';
  if (score >= 21) return 'MODERATE';
  return 'LOW';
}

/**
 * Map a risk level string to a Tailwind badge class suffix.
 */
export function getRiskBadgeClass(level) {
  const map = {
    LOW: 'risk-badge-low',
    MODERATE: 'risk-badge-moderate',
    HIGH: 'risk-badge-high',
    'VERY HIGH': 'risk-badge-very-high',
    CRITICAL: 'risk-badge-critical',
  };
  return map[level] || 'risk-badge-low';
}

/**
 * Map risk level to a hex color for map markers.
 */
export function getRiskColor(level) {
  const map = {
    LOW: '#22c55e',
    MODERATE: '#eab308',
    HIGH: '#f97316',
    'VERY HIGH': '#ef4444',
    CRITICAL: '#dc2626',
  };
  return map[level] || '#6b7280';
}

/**
 * Get a decision-support recommendation based on prototype risk level.
 * Clearly a prototype — not an operational directive.
 */
export function getRecommendation(level) {
  const map = {
    LOW: 'Routine monitoring',
    MODERATE: 'Increased surveillance',
    HIGH: 'Alert local authorities',
    'VERY HIGH': 'Prepare evacuation response',
    CRITICAL: 'Immediate evacuation advisory',
  };
  return map[level] || 'Monitor';
}

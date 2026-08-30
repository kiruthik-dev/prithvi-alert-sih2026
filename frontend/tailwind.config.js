/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        'pa-dark': '#0a0f1a',
        'pa-card': '#111827',
        'pa-border': '#1e293b',
        'pa-accent': '#3b82f6',
        'pa-accent-dim': '#1e3a5f',
        'risk-low': '#22c55e',
        'risk-moderate': '#eab308',
        'risk-high': '#f97316',
        'risk-very-high': '#ef4444',
        'risk-critical': '#dc2626',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
};

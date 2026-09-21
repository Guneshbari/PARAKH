/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,jsx,ts,tsx}',
    './components/**/*.{js,jsx,ts,tsx}',
  ],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        background: '#060D1F',
        surface: '#0A162E',
        surfaceElevated: '#0E1F3D',
        surfaceHighlight: '#14274E',
        textPrimary: '#F8FAFC',
        textSecondary: '#A8B7CC',
        lime: '#C8F451',
        electric: '#2563EB',
        cyan: '#22D3EE',
        mint: '#2DD4BF',
        violet: '#8B5CF6',
        lavender: '#C4B5FD',
        // Assessment Risk States
        riskLower: '#34D399',
        riskModerate: '#FBBF24',
        riskHigher: '#F87171',
        riskNeutral: '#64748B',
      },
      borderRadius: {
        '2xl': '16px',
        '3xl': '20px',
        pill: '9999px',
      },
    },
  },
  plugins: [],
};

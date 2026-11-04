/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './tabs/*.html',
    './*.js',
  ],
  theme: {
    extend: {
      colors: {
        azure: { 50: '#f0f9ff', 500: '#0078d4', 600: '#005a9e', 900: '#0c2340' },
        sre: { bg: '#0a0e17', card: '#111827', border: '#1f293d', accent: '#38bdf8', success: '#10b981', warning: '#f59e0b', danger: '#ef4444' },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Menlo', 'Monaco', 'Courier New', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

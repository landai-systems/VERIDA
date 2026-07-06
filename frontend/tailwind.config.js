/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        surface: 'rgba(255,255,255,0.04)',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}

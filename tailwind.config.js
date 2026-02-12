/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./src/renderer/**/*.{js,ts,jsx,tsx}",
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        yandere: {
          50: '#fff0f5',
          100: '#ffe4ed',
          200: '#ffc4d8',
          300: '#ff9fbf',
          400: '#ff6b9d',
          500: '#ff3d7f',
          600: '#e91e63',
          700: '#c2185b',
          800: '#880e4f',
          900: '#560027',
        }
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-slow': 'bounce 2s infinite',
      }
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ima: {
          blue: '#2563EB',
          dark: '#0F172A',
          lime: '#A3E635',
          slate: '#1E293B'
        }
      }
    },
  },
  plugins: [],
}


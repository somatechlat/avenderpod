/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./tenants/templates/**/*.html",
    "./templates/**/*.html"
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        display: ['Space Grotesk', 'sans-serif'],
      },
      colors: {
        brand: {
          bg: '#090d14',
          panel: '#111827',
          pink: '#f43f5e',
          blue: '#38bdf8',
          cyan: '#22d3ee',
        }
      },
      backgroundImage: {
        'gradient-brand': 'linear-gradient(to right, #f43f5e, #38bdf8)',
      }
    }
  },
  plugins: [],
}

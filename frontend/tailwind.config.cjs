/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  // Enable dark mode with 'class' strategy
  // This allows both manual toggle and prefers-color-scheme detection
  darkMode: 'class',
  theme: {
    extend: {
      // Dark mode color palette
      colors: {
        dark: {
          bg: '#0f1419',
          surface: '#1a1f26',
          'surface-elevated': '#242a32',
          border: '#2f3941',
          text: '#e7e9ea',
          'text-secondary': '#8b9298',
        },
      },
    },
  },
  plugins: [],
}
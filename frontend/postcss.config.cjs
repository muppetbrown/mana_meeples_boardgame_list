module.exports = {
  plugins: {
    // Tailwind CSS v4 uses @import "tailwindcss" in CSS instead of PostCSS plugin
    // Only autoprefixer is needed here for vendor prefixes
    autoprefixer: {},
  },
}
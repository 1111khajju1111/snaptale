/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        snapyellow: '#FFDF00',
        snappink: '#FF2E93',
        snapcyan: '#00F0FF',
        snapplus: {
          bg: '#0D0A14',
          card: '#181224',
          crimson: '#E11D48',
          purple: '#9333EA',
          neon: '#C084FC'
        }
      }
    },
  },
  plugins: [],
}

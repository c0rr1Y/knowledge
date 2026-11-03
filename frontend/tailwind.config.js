/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Bright natural scenery palette
        nature: {
          50:  '#fafaf5',   // warm white background
          100: '#f5f2e8',   // light sand
          200: '#e8e2d2',   // warm beige
          300: '#d4c9a8',   // golden sand
          400: '#a3b18a',   // sage green
          500: '#588157',   // forest green
          600: '#3a5a40',   // deep forest
          700: '#344e41',   // dark pine
          800: '#283618',   // deep woods
          900: '#1a2312',   // darkest green
        },
        leaf: {
          400: '#22c55e',   // bright leaf
          500: '#16a34a',   // green leaf
          600: '#15803d',   // deep leaf
        },
        sky: {
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',   // sky blue accent
          600: '#0284c7',
        },
        sunset: {
          400: '#fb923c',
          500: '#f97316',   // warm orange accent
        },
        wood: {
          200: '#e7e5e4',
          300: '#d6d3d1',
          400: '#a8a29e',
          500: '#78716c',
        },
      },
      fontFamily: {
        sans: ['"Inter"', '"Noto Sans SC"', 'system-ui', '-apple-system', 'sans-serif'],
      },
      backgroundImage: {
        'nature-gradient': 'linear-gradient(135deg, #ecfdf5 0%, #dbeafe 50%, #fef3c7 100%)',
        'login-gradient': 'linear-gradient(135deg, #065f46 0%, #1e40af 50%, #064e3b 100%)',
        'card-gradient': 'linear-gradient(135deg, #f0fdf4 0%, #ffffff 50%, #eff6ff 100%)',
      },
    },
  },
  plugins: [],
}

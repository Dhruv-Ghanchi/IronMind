/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f4ff',
          100: '#e1e9ff',
          200: '#c7d6ff',
          300: '#a3b8ff',
          400: '#7a8fff',
          500: '#5361ff', // Primary Brand Color
          600: '#3d44ff',
          700: '#3133e6',
          800: '#2a2bb8',
          900: '#272991',
        },
        dark: {
          900: '#0a0b10',
          800: '#12141c',
          700: '#1c1f2b',
        }
      },
      fontFamily: {
        inter: ['Inter', 'sans-serif'],
      },
      backgroundImage: {
        'glass-gradient': 'linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0))',
      }
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // TODO: Replace with exact ScaleupBoard brand colors once provided
        brand: {
          50: '#eef9ff',
          100: '#d7efff',
          200: '#b0e0ff',
          300: '#7ccaff',
          400: '#42aff7',
          500: '#1593e6',
          600: '#0f78c2',
          700: '#0d609c',
          800: '#0e4f80',
          900: '#0d3f66'
        },
        primary: {
          DEFAULT: '#1593e6',
          50: '#eef9ff',
          100: '#d7efff',
          200: '#b0e0ff',
          300: '#7ccaff',
          400: '#42aff7',
          500: '#1593e6',
          600: '#0f78c2',
          700: '#0d609c',
          800: '#0e4f80',
          900: '#0d3f66'
        },
        secondary: {
          DEFAULT: '#0ea5a3',
          50: '#e6fffb',
          100: '#c7fffb',
          200: '#8ef2ee',
          300: '#5cd8d4',
          400: '#2fc1bd',
          500: '#0ea5a3',
          600: '#0a8786',
          700: '#0a6c6c',
          800: '#0b5858',
          900: '#0c4949',
        },
        accent: {
          DEFAULT: '#f59e0b',
          50: '#fff7ed',
          100: '#ffedd5',
          200: '#fed7aa',
          300: '#fdba74',
          400: '#fb923c',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        }
      }
    },
  },
  plugins: [],
}

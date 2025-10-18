import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: false,
    proxy: {
      // Proxy Django endpoints during dev so SPA can call without CORS
      '/accounts': 'http://localhost:8000',
      '/coaching': 'http://localhost:8000',
      '/dashboard': 'http://localhost:8000',
      '/ingest': 'http://localhost:8000',
      '/survey': 'http://localhost:8000',
      '/suropen': 'http://localhost:8000',
      '/exports': 'http://localhost:8000',
      '/chatbot': 'http://localhost:8000',
      '/api': 'http://localhost:8000',
    }
  },
  preview: {
    port: 5173
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})

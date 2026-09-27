import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Forward API and image requests to the FastAPI backend (port 8000 unless BACKEND_PORT is set).
const backend = `http://localhost:${process.env.BACKEND_PORT ?? 8000}`

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': backend,
      '/media': backend,
    },
  },
})

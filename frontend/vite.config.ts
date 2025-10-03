import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    allowedHosts: ['stav-agent.onrender.com', 'localhost', '127.0.0.1'],
  },
  preview: {
    port: process.env.PORT ? parseInt(process.env.PORT) : 4173,
    host: true,
    allowedHosts: ['stav-agent.onrender.com', 'localhost', '127.0.0.1'],
  },
  define: {
    'process.env': {}
  },
})

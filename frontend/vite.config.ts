import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    allowedHosts: ['stav-agent.onrender.com', 'localhost', '127.0.0.1'],
  },
  preview: {
    port: 4173,
    allowedHosts: ['stav-agent.onrender.com', 'localhost', '127.0.0.1'],
  },
  define: {
    'process.env': {}
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          antd: ['antd', '@ant-design/icons'],
          charts: ['recharts'],
          i18n: ['react-i18next', 'i18next'],
        },
      },
    },
  },
})

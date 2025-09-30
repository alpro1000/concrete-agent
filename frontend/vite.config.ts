import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: process.env.PORT ? parseInt(process.env.PORT) : 5173, // Используем динамический порт
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000', // Убедитесь, что API сервер доступен
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
    allowedHosts: ['stav-agent.onrender.com', 'localhost'], // Добавляем оба хоста
  },
  build: {
    outDir: 'dist',
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

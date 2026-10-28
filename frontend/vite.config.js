import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// En desarrollo el frontend llama a `/v1/...` y Vite lo reenvía al backend.
// En producción se puede apuntar directamente con VITE_API_URL.
const apiProxy = {
  '/v1': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: { proxy: apiProxy },
  preview: { proxy: apiProxy },
})

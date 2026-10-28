// URL base del backend. En desarrollo se deja vacía para usar el proxy de Vite
// (`/v1` → http://127.0.0.1:8000). En producción, define `VITE_API_URL`.
export const API_BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')

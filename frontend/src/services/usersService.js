import { apiFetch } from './http.js'

// Perfiles registrados en el backend, usados por la selección de perfil.
const usersService = {
  list() {
    return apiFetch('/v1/models/users/')
  },
}

export default usersService

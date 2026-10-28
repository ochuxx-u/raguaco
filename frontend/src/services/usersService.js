import { apiFetch } from './http.js'

// Perfiles registrados en el backend, usados por la selección de perfil.
const usersService = {
  list() {
    return apiFetch('/v1/models/users/')
  },

  create(user) {
    return apiFetch('/v1/models/users/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(user),
    })
  },
}

export default usersService

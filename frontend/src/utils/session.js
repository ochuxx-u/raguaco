const STORAGE_KEY = 'raguaco.session'

function isValidUser(value) {
  return (
    value !== null &&
    typeof value === 'object' &&
    typeof value.id === 'string' &&
    typeof value.nombre === 'string' &&
    typeof value.email === 'string'
  )
}

export function readStoredUser() {
  if (typeof window === 'undefined') {
    return null
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)

    if (!raw) {
      return null
    }

    const parsed = JSON.parse(raw)

    if (!isValidUser(parsed)) {
      window.localStorage.removeItem(STORAGE_KEY)
      return null
    }

    return parsed
  } catch {
    window.localStorage.removeItem(STORAGE_KEY)
    return null
  }
}

export function saveStoredUser(user) {
  if (!isValidUser(user)) {
    return
  }

  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(user))
  } catch {
    // Si el navegador bloquea el almacenamiento, la sesión sigue en memoria.
  }
}

export function clearStoredUser() {
  try {
    window.localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Sin almacenamiento disponible no hay nada que limpiar.
  }
}

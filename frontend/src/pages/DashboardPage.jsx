import { useEffect, useRef, useState } from 'react'
import RecentActivity from '../components/dashboard/RecentActivity.jsx'
import StatCard from '../components/dashboard/StatCard.jsx'
import dashboardService from '../services/dashboardService.js'
import './DashboardPage.css'

function DashboardPage({ currentUser = null, onNavigate = () => {} }) {
  const [summary, setSummary] = useState(null)
  const [isLoading, setIsLoading] = useState(Boolean(currentUser?.id))
  const [error, setError] = useState('')
  const requestRef = useRef(0)

  const loadSummary = async () => {
    const usuarioId = currentUser?.id

    // Sin perfil no se consulta el backend: la base se muestra vacía.
    if (!usuarioId) {
      requestRef.current += 1
      setSummary(null)
      setError('')
      setIsLoading(false)
      return
    }

    const requestId = ++requestRef.current
    setIsLoading(true)
    setError('')

    try {
      const data = await dashboardService.getSummary(usuarioId)

      if (requestId !== requestRef.current) {
        return
      }

      setSummary(data)
    } catch {
      if (requestId === requestRef.current) {
        setSummary(null)
        setError('No se pudo cargar la actividad reciente.')
      }
    } finally {
      if (requestId === requestRef.current) {
        setIsLoading(false)
      }
    }
  }

  useEffect(() => {
    void loadSummary()

    return () => {
      // Invalida la petición en curso al desmontar o al cambiar de usuario:
      // una respuesta vieja no debe pisar el estado actual.
      requestRef.current += 1
    }
  }, [currentUser?.id])

  const hasError = !isLoading && Boolean(error)
  const placeholder = isLoading ? '…' : hasError ? '—' : null
  const statValue = (key) => placeholder ?? summary?.stats[key] ?? '0'

  const firstName = currentUser?.nombre?.trim().split(/\s+/)[0] ?? ''

  const stats = [
    {
      id: 'documents',
      label: 'Documentos cargados',
      value: statValue('documents'),
    },
    {
      id: 'conversations',
      label: 'Conversaciones',
      value: statValue('conversations'),
    },
    {
      id: 'chunks',
      label: 'Chunks generados',
      value: statValue('chunks'),
      tone: 'accent',
    },
    {
      id: 'system-status',
      label: 'Estado del sistema',
      value: 'Operativo',
      tone: 'interactive',
    },
  ]

  return (
    <section className="dashboard" aria-labelledby="dashboard-title">
      <header className="dashboard__header">
        <div className="dashboard__heading">
          <h1 className="dashboard__title" id="dashboard-title">
            Bienvenido de nuevo{firstName ? ` ${firstName}` : ''}
          </h1>
          <p className="dashboard__subtitle">
            Tu base de conocimiento está lista para responder.
          </p>
        </div>

        <button
          className="dashboard__action"
          type="button"
          onClick={() => onNavigate('documents')}
        >
          + Subir nuevo documento
        </button>
      </header>

      <section className="dashboard__stats" aria-label="Estadísticas de la base de conocimiento">
        {stats.map((stat) => (
          <StatCard
            key={stat.id}
            label={stat.label}
            tone={stat.tone}
            value={stat.value}
          />
        ))}
      </section>

      <RecentActivity
        error={error}
        isLoading={isLoading}
        items={summary?.recentActivity ?? []}
        onRetry={loadSummary}
      />
    </section>
  )
}

export default DashboardPage

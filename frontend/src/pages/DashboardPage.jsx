import RecentActivity from '../components/dashboard/RecentActivity.jsx'
import StatCard from '../components/dashboard/StatCard.jsx'
import './DashboardPage.css'

const stats = [
  {
    id: 'documents',
    label: 'Documentos cargados',
    value: '24',
  },
  {
    id: 'conversations',
    label: 'Conversaciones',
    value: '58',
  },
  {
    id: 'chunks',
    label: 'Chunks generados',
    value: '3.412',
    tone: 'accent',
  },
  {
    id: 'system-status',
    label: 'Estado del sistema',
    value: 'Operativo',
    tone: 'interactive',
  },
]

const recentActivity = [
  {
    id: 'manual-politicas',
    message: 'manual_politicas.pdf — vectorización completada',
  },
  {
    id: 'vacaciones-permisos',
    message: 'Conversación “Vacaciones y permisos” — 6 mensajes',
  },
  {
    id: 'contrato-proveedor',
    message: 'contrato_proveedor.docx — procesando 62%',
  },
]

function DashboardPage({ onNavigate = () => {} }) {
  return (
    <section className="dashboard" aria-labelledby="dashboard-title">
      <header className="dashboard__header">
        <div className="dashboard__heading">
          <h1 className="dashboard__title" id="dashboard-title">
            Bienvenido de nuevo
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

      <RecentActivity items={recentActivity} />
    </section>
  )
}

export default DashboardPage

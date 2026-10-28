import './RecentActivity.css'

function RecentActivity({
  items = [],
  isLoading = false,
  error = '',
  onRetry = () => {},
}) {
  return (
    <section className="recent-activity" aria-labelledby="recent-activity-title">
      <h2 className="recent-activity__title" id="recent-activity-title">
        Actividad reciente
      </h2>

      <div className="recent-activity__content">
        {isLoading && (
          <div className="recent-activity__state" role="status">
            <span className="recent-activity__spinner" aria-hidden="true" />
            <p>Cargando actividad reciente…</p>
          </div>
        )}

        {!isLoading && error && (
          <div
            className="recent-activity__state recent-activity__state--error"
            role="alert"
          >
            <p>{error}</p>
            <button
              className="recent-activity__retry"
              type="button"
              onClick={onRetry}
            >
              Reintentar
            </button>
          </div>
        )}

        {!isLoading && !error && items.length === 0 && (
          <p className="recent-activity__empty">Aún no hay actividad reciente.</p>
        )}

        {!isLoading && !error && items.length > 0 && (
          <ul className="recent-activity__list">
            {items.map((item) => (
              <li className="recent-activity__item" key={item.id}>
                {item.message}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}

export default RecentActivity

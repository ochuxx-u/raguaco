import './StatCard.css'

function StatCard({ label, value, tone = 'default' }) {
  return (
    <article className={`stat-card stat-card--${tone}`}>
      <p className="stat-card__label">{label}</p>
      <p className="stat-card__value">{value}</p>
    </article>
  )
}

export default StatCard

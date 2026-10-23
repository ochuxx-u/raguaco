import './RecentActivity.css'

function RecentActivity({ items }) {
  return (
    <section className="recent-activity" aria-labelledby="recent-activity-title">
      <h2 className="recent-activity__title" id="recent-activity-title">
        Actividad reciente
      </h2>

      <ul className="recent-activity__list">
        {items.map((item) => (
          <li className="recent-activity__item" key={item.id}>
            {item.message}
          </li>
        ))}
      </ul>
    </section>
  )
}

export default RecentActivity

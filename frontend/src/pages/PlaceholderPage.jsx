import './PlaceholderPage.css'

function PlaceholderPage({ title, description }) {
  return (
    <section className="placeholder-page" aria-labelledby="placeholder-page-title">
      <header className="placeholder-page__header">
        <p className="placeholder-page__eyebrow">RAGUACO AI</p>
        <h1 className="placeholder-page__title" id="placeholder-page-title">
          {title}
        </h1>
        <p className="placeholder-page__description">{description}</p>
      </header>

      <div className="placeholder-page__panel">
        <div>
          <p className="placeholder-page__panel-title">Contenido en preparación</p>
          <p className="placeholder-page__panel-text">
            Esta pantalla se implementará en una etapa posterior.
          </p>
        </div>
      </div>
    </section>
  )
}

export default PlaceholderPage

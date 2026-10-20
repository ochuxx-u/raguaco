import './LandingPage.css'

const navItems = ['Dashboard', 'Documentos', 'Chat', 'Historial', 'Voz']
const pipelineSteps = ['Upload', 'Process', 'Vectorize', 'Retrieve', 'Respond']

function LandingPage() {
  const handlePlaceholderLink = (event) => {
    event.preventDefault()
  }

  return (
    <div className="landing">
      <svg
        className="landing__graph"
        viewBox="0 0 1280 720"
        preserveAspectRatio="xMaxYMid slice"
        fill="none"
        aria-hidden="true"
        focusable="false"
      >
        <path
          className="landing__graph-line"
          d="M700 120L900 220L1100 140L1000 360L820 420L700 120M900 220L1000 360M1100 140L1200 300L1000 360"
        />
        <circle className="landing__graph-node landing__graph-node--accent" cx="700" cy="120" r="6" />
        <circle className="landing__graph-node landing__graph-node--interactive" cx="900" cy="220" r="8" />
        <circle className="landing__graph-node landing__graph-node--accent" cx="1100" cy="140" r="6" />
        <circle className="landing__graph-node landing__graph-node--interactive" cx="1000" cy="360" r="9" />
        <circle className="landing__graph-node landing__graph-node--accent" cx="820" cy="420" r="6" />
        <circle className="landing__graph-node landing__graph-node--accent" cx="1200" cy="300" r="5" />
      </svg>

      <header className="landing__header">
        <a
          className="landing__brand"
          href="#"
          aria-label="RAGUACO AI — Inicio"
          onClick={handlePlaceholderLink}
        >
          <span className="landing__logo-mark" aria-hidden="true" />
          <span>
            RAGUACO <span className="landing__brand-accent">AI</span>
          </span>
        </a>

        <nav className="landing__nav" aria-label="Navegación principal">
          {navItems.map((item) => (
            <a
              className="landing__nav-link"
              href="#"
              key={item}
              onClick={handlePlaceholderLink}
            >
              {item}
            </a>
          ))}
        </nav>

        <p className="landing__status">
          <span className="landing__status-dot" aria-hidden="true" />
          Sistema activo
        </p>
      </header>

      <main className="landing__main">
        <section className="landing__hero" aria-labelledby="landing-title">
          <p className="landing__eyebrow">PLATAFORMA DE CONOCIMIENTO CON IA</p>
          <h1 className="landing__title" id="landing-title">
            RAGUACO <span className="landing__title-accent">AI</span>
          </h1>
          <h2 className="landing__subtitle">
            Conversa con tus documentos mediante inteligencia artificial
          </h2>
          <p className="landing__description">
            Carga tus archivos, vectorízalos automáticamente y haz preguntas en
            lenguaje natural, por texto o voz, con respuestas fundamentadas en
            fuentes.
          </p>

          <div className="landing__actions">
            <button className="landing__button landing__button--primary" type="button">
              Comenzar ahora
            </button>
            <button className="landing__button landing__button--secondary" type="button">
              Ver demo
            </button>
          </div>
        </section>

        <section className="landing__cards" aria-label="Ejemplos de la plataforma">
          <article className="landing__card landing__card--document">
            <p className="landing__card-title">Documento cargado</p>
            <p className="landing__card-text">manual_politicas.pdf · 48 págs.</p>
          </article>

          <article className="landing__card landing__card--answer">
            <p className="landing__card-title">Respuesta con fuentes</p>
            <p className="landing__card-text">“Según la página 12…” · relevancia 94%</p>
          </article>

          <article className="landing__card landing__card--voice">
            <p className="landing__card-title">Modo voz</p>
            <p className="landing__card-text">Habla con tu base de conocimiento</p>
          </article>
        </section>

        <ol className="landing__pipeline" aria-label="Flujo de procesamiento de documentos">
          {pipelineSteps.map((step, index) => (
            <li className="landing__pipeline-item" key={step}>
              <span
                className={`landing__pipeline-step${
                  step === 'Retrieve' ? ' landing__pipeline-step--active' : ''
                }`}
              >
                {step}
              </span>
              {index < pipelineSteps.length - 1 && (
                <span className="landing__pipeline-arrow" aria-hidden="true">
                  →
                </span>
              )}
            </li>
          ))}
        </ol>
      </main>
    </div>
  )
}

export default LandingPage

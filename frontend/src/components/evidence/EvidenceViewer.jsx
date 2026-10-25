import './EvidenceViewer.css'

function EvidenceViewer({ source }) {
  const fragment = source.fragmento ?? ''
  const highlightedFragment = source.fragmentoDestacado ?? ''
  const highlightIndex = highlightedFragment
    ? fragment.indexOf(highlightedFragment)
    : -1
  const before = highlightIndex >= 0 ? fragment.slice(0, highlightIndex) : fragment
  const after =
    highlightIndex >= 0
      ? fragment.slice(highlightIndex + highlightedFragment.length)
      : ''
  const metadata = [
    source.categoria,
    source.seccion,
    source.pagina != null ? `Página ${source.pagina}` : null,
    source.chunk != null ? `Chunk #${source.chunk}` : null,
  ].filter(Boolean)

  return (
    <article className="evidence-viewer">
      <header className="evidence-viewer__header">
        <div className="evidence-viewer__type" aria-label={`Tipo de archivo ${source.tipo}`}>
          {source.tipo ?? 'DOC'}
        </div>

        <div className="evidence-viewer__identity">
          <h2 className="evidence-viewer__name">{source.documento}</h2>
          {metadata.length > 0 && (
            <p className="evidence-viewer__metadata">{metadata.join(' · ')}</p>
          )}
        </div>
      </header>

      <div className="evidence-viewer__fragment-section">
        <p className="evidence-viewer__fragment-label">Fragmento relevante</p>
        <div
          className="evidence-viewer__fragment"
          tabIndex={0}
          role="region"
          aria-label="Fragmento relevante de la evidencia"
        >
          <p>
            {before}
            {highlightIndex >= 0 && <mark>{highlightedFragment}</mark>}
            {after}
          </p>
        </div>
      </div>
    </article>
  )
}

export default EvidenceViewer

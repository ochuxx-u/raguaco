import './SourceChip.css'

function SourceChip({ source, index, isActive, onClick }) {
  const pageLabel = source.pagina != null ? `página ${source.pagina}` : 'sin paginación'
  const evidenceLabel = `Ver evidencia de ${source.documento}, ${pageLabel}`

  return (
    <button
      className={`source-chip${isActive ? ' source-chip--active' : ''}`}
      type="button"
      aria-label={evidenceLabel}
      title={evidenceLabel}
      onClick={onClick}
    >
      Fuente {index + 1}
      {source.pagina != null ? ` · pág. ${source.pagina}` : ''}
    </button>
  )
}

export default SourceChip

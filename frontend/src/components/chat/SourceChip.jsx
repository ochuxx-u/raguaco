import './SourceChip.css'

function SourceChip({ source, index, isActive, onClick }) {
  const evidenceLabel = `Ver evidencia de ${source.documento}, página ${source.pagina}`

  return (
    <button
      className={`source-chip${isActive ? ' source-chip--active' : ''}`}
      type="button"
      aria-label={evidenceLabel}
      title={evidenceLabel}
      onClick={onClick}
    >
      Fuente {index + 1} · pág. {source.pagina}
    </button>
  )
}

export default SourceChip

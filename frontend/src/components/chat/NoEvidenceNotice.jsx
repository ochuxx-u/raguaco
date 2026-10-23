import './NoEvidenceNotice.css'

function NoEvidenceNotice() {
  return (
    <div className="no-evidence" role="note">
      <svg
        viewBox="0 0 24 24"
        width="18"
        height="18"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="9" />
        <path d="M12 8v5M12 16h.01" />
      </svg>
      <p>
        No encontré información suficiente en tus documentos para responder esta
        pregunta.
      </p>
    </div>
  )
}

export default NoEvidenceNotice

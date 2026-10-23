import { useRef, useState } from 'react'
import './DocumentUploader.css'

const ALLOWED_EXTENSIONS = ['pdf', 'docx', 'txt']

function getExtension(fileName) {
  return fileName.split('.').pop()?.toLowerCase() ?? ''
}

function isAllowedFile(file) {
  return ALLOWED_EXTENSIONS.includes(getExtension(file.name))
}

function DocumentUploader({ isUploading = false, onUpload }) {
  const [category, setCategory] = useState('')
  const [error, setError] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef(null)

  const handleFiles = async (fileList) => {
    if (isUploading) return

    const files = Array.from(fileList ?? [])

    if (!files.length) return

    if (files.some((file) => !isAllowedFile(file))) {
      setError('Solo se permiten archivos PDF, DOCX o TXT.')
      return
    }

    setError('')

    try {
      await onUpload(files, { categoria: category.trim() })
      setCategory('')
    } catch {
      setError('No se pudieron subir los archivos. Inténtalo de nuevo.')
    }
  }

  const handleFileInputChange = (event) => {
    const files = Array.from(event.target.files ?? [])
    event.target.value = ''
    void handleFiles(files)
  }

  const handleDragOver = (event) => {
    event.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (event) => {
    if (event.currentTarget.contains(event.relatedTarget)) return
    setIsDragging(false)
  }

  const handleDrop = (event) => {
    event.preventDefault()
    setIsDragging(false)
    void handleFiles(event.dataTransfer.files)
  }

  return (
    <div className="document-uploader" aria-busy={isUploading}>
      <div
        className={`document-uploader__dropzone${
          isDragging ? ' document-uploader__dropzone--dragging' : ''
        }`}
        role="group"
        aria-label="Zona de carga de documentos"
        onDragEnter={handleDragOver}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="document-uploader__copy">
          <p className="document-uploader__title">Arrastra tus archivos aquí</p>
          <p className="document-uploader__hint">
            PDF, DOCX, TXT · asigna una categoría al subir
          </p>
        </div>

        <label className="document-uploader__category">
          <span className="document-uploader__category-label">Categoría (opcional)</span>
          <input
            type="text"
            value={category}
            placeholder="Ej. Políticas"
            disabled={isUploading}
            onChange={(event) => setCategory(event.target.value)}
          />
        </label>

        <button
          className="document-uploader__button"
          type="button"
          disabled={isUploading}
          onClick={() => fileInputRef.current?.click()}
        >
          {isUploading ? 'Subiendo…' : 'Subir documento'}
        </button>

        <input
          className="document-uploader__input"
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          multiple
          onChange={handleFileInputChange}
        />
      </div>

      {error && (
        <p className="document-uploader__error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}

export default DocumentUploader

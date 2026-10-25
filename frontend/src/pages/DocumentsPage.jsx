import { useEffect, useMemo, useRef, useState } from 'react'
import DocumentDetailPanel from '../components/documents/DocumentDetailPanel.jsx'
import DocumentList from '../components/documents/DocumentList.jsx'
import DocumentUploader from '../components/documents/DocumentUploader.jsx'
import documentsService from '../services/documentsService.js'
import queriesService from '../services/queriesService.js'
import { DOCUMENT_STATES } from '../utils/documents.js'
import './DocumentsPage.css'

const PIPELINE_STEPS = ['Upload', 'Process', 'Vectorize', 'Retrieve', 'Respond']

function DocumentsPage({ onNavigate = () => {}, selectedDocumentId = null }) {
  const [documents, setDocuments] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [isUploading, setIsUploading] = useState(false)
  const [simulatedIds, setSimulatedIds] = useState(() => new Set())
  const [selectedDocument, setSelectedDocument] = useState(null)
  const [detailError, setDetailError] = useState('')
  const [documentToDelete, setDocumentToDelete] = useState(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const detailRequestRef = useRef(0)
  const autoOpenedDocumentRef = useRef(null)

  const loadDocuments = async () => {
    setIsLoading(true)
    setLoadError('')

    try {
      const data = await documentsService.list()
      setDocuments(data)
      return data
    } catch {
      setLoadError('No se pudieron cargar los documentos.')
      return []
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void loadDocuments()
  }, [])

  const categoryOptions = useMemo(() => {
    const categories = []

    for (const document of documents) {
      if (!categories.includes(document.categoria)) {
        categories.push(document.categoria)
      }
    }

    return categories
  }, [documents])

  useEffect(() => {
    if (categoryFilter !== 'all' && !categoryOptions.includes(categoryFilter)) {
      setCategoryFilter('all')
    }
  }, [categoryFilter, categoryOptions])

  const filteredDocuments = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase()

    return documents.filter((document) => {
      const matchesSearch =
        !normalizedSearch || document.nombre.toLowerCase().includes(normalizedSearch)
      const matchesStatus = statusFilter === 'all' || document.estado === statusFilter
      const matchesCategory =
        categoryFilter === 'all' || document.categoria === categoryFilter

      return matchesSearch && matchesStatus && matchesCategory
    })
  }, [documents, searchTerm, statusFilter, categoryFilter])

  const hasSimulatedProcessing = useMemo(
    () =>
      documents.some(
        (document) =>
          simulatedIds.has(document.id) &&
          (document.estado === 'pendiente' || document.estado === 'procesando'),
      ),
    [documents, simulatedIds],
  )

  useEffect(() => {
    if (!hasSimulatedProcessing) {
      return undefined
    }

    let cancelled = false

    const pollDocuments = async () => {
      try {
        const latestDocuments = await documentsService.list()

        if (!cancelled) {
          setDocuments(latestDocuments)
        }
      } catch {
        // La lista conserva el último estado conocido si falla una actualización.
      }
    }

    const intervalId = setInterval(pollDocuments, 1200)

    return () => {
      cancelled = true
      clearInterval(intervalId)
    }
  }, [hasSimulatedProcessing])

  const handleUpload = async (files, metadata) => {
    setIsUploading(true)

    try {
      const results = await Promise.allSettled(
        files.map((file) => documentsService.upload(file, metadata)),
      )
      const createdDocuments = results
        .filter((result) => result.status === 'fulfilled')
        .map((result) => result.value)

      if (createdDocuments.length > 0) {
        setDocuments((currentDocuments) => [...createdDocuments, ...currentDocuments])
        setSimulatedIds((currentIds) => {
          const nextIds = new Set(currentIds)
          createdDocuments.forEach((document) => nextIds.add(document.id))
          return nextIds
        })
      }

      if (results.some((result) => result.status === 'rejected')) {
        throw new Error('No se pudieron subir todos los archivos.')
      }
    } finally {
      setIsUploading(false)
    }
  }

  const handleViewDetail = async (document) => {
    const requestId = ++detailRequestRef.current
    setSelectedDocument(document)
    setDetailError('')

    try {
      const detail = await documentsService.getById(document.id)

      if (detailRequestRef.current === requestId) {
        setSelectedDocument(detail)
      }
    } catch {
      if (detailRequestRef.current === requestId) {
        setDetailError('No se pudo cargar el detalle del documento.')
      }
    }
  }

  const closeDetail = () => {
    detailRequestRef.current += 1
    setSelectedDocument(null)
    setDetailError('')
  }

  useEffect(() => {
    if (!selectedDocumentId) {
      autoOpenedDocumentRef.current = null
      return
    }

    if (documents.length === 0) return
    if (autoOpenedDocumentRef.current === selectedDocumentId) return

    const matchedDocument = documents.find(
      (document) => document.id === selectedDocumentId,
    )

    if (!matchedDocument) return

    autoOpenedDocumentRef.current = selectedDocumentId
    void handleViewDetail(matchedDocument)
  }, [documents, selectedDocumentId])

  const startConversationForDocument = async (document) => {
    const conversation = await queriesService.createConversation(document.id)
    onNavigate('chat', conversation.id, document.id)
  }

  const handleAsk = (document) => {
    void startConversationForDocument(document)
  }

  const handleRequestDelete = (document) => {
    setDeleteError('')
    setDocumentToDelete(document)
  }

  const closeDeleteDialog = () => {
    if (isDeleting) return
    setDocumentToDelete(null)
    setDeleteError('')
  }

  const handleDelete = async () => {
    if (!documentToDelete || isDeleting) return

    const deletedId = documentToDelete.id
    setIsDeleting(true)
    setDeleteError('')

    try {
      await documentsService.remove(deletedId)
      setDocuments((currentDocuments) =>
        currentDocuments.filter((document) => document.id !== deletedId),
      )
      setSimulatedIds((currentIds) => {
        const nextIds = new Set(currentIds)
        nextIds.delete(deletedId)
        return nextIds
      })

      if (selectedDocument?.id === deletedId) {
        closeDetail()
      }

      setDocumentToDelete(null)
    } catch {
      setDeleteError('No se pudo eliminar el documento. Inténtalo de nuevo.')
    } finally {
      setIsDeleting(false)
    }
  }

  useEffect(() => {
    if (!documentToDelete) {
      return undefined
    }

    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && !isDeleting) {
        setDocumentToDelete(null)
        setDeleteError('')
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [documentToDelete, isDeleting])

  const selectedDocumentForPanel = selectedDocument
    ? documents.find((document) => document.id === selectedDocument.id) ?? selectedDocument
    : null

  const emptyMessage =
    documents.length === 0
      ? 'Aún no has cargado documentos.'
      : 'No se encontraron documentos con esos filtros.'

  return (
    <section className="documents-page" aria-labelledby="documents-title">
      <header className="documents-page__header">
        <div className="documents-page__heading">
          <h1 className="documents-page__title" id="documents-title">
            Gestor de documentos
          </h1>
          <p className="documents-page__intro">
            Administra tus documentos, revisa su estado de procesamiento y consulta el
            detalle de cada archivo.
          </p>
        </div>

        <ol className="documents-page__pipeline" aria-label="Flujo de procesamiento de documentos">
          {PIPELINE_STEPS.map((step, index) => (
            <li className="documents-page__pipeline-item" key={step}>
              <span
                className={`documents-page__pipeline-step${
                  step === 'Retrieve' ? ' documents-page__pipeline-step--active' : ''
                }`}
              >
                {step}
              </span>
              {index < PIPELINE_STEPS.length - 1 && (
                <span className="documents-page__pipeline-arrow" aria-hidden="true">
                  →
                </span>
              )}
            </li>
          ))}
        </ol>
      </header>

      <DocumentUploader isUploading={isUploading} onUpload={handleUpload} />

      <div className="documents-page__toolbar">
        <div className="documents-page__search">
          <svg
            className="documents-page__search-icon"
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="m16.5 16.5 4 4" />
          </svg>
          <input
            type="search"
            value={searchTerm}
            placeholder="Buscar por nombre…"
            aria-label="Buscar por nombre de documento"
            onChange={(event) => setSearchTerm(event.target.value)}
          />
        </div>

        <select
          className="documents-page__filter"
          value={statusFilter}
          aria-label="Filtrar por estado"
          onChange={(event) => setStatusFilter(event.target.value)}
        >
          <option value="all">Todos los estados</option>
          {DOCUMENT_STATES.map((state) => (
            <option key={state.value} value={state.value}>
              {state.label}
            </option>
          ))}
        </select>

        <select
          className="documents-page__filter"
          value={categoryFilter}
          aria-label="Filtrar por categoría"
          onChange={(event) => setCategoryFilter(event.target.value)}
        >
          <option value="all">Todas las categorías</option>
          {categoryOptions.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>
      </div>

      <DocumentList
        documents={filteredDocuments}
        emptyMessage={emptyMessage}
        error={loadError}
        highlightedDocumentId={selectedDocumentId}
        isLoading={isLoading}
        onAsk={handleAsk}
        onDelete={handleRequestDelete}
        onRetry={loadDocuments}
        onViewDetail={handleViewDetail}
      />

      {selectedDocumentForPanel && (
        <DocumentDetailPanel
          document={selectedDocumentForPanel}
          error={detailError}
          onAsk={(document) => {
            closeDetail()
            void startConversationForDocument(document)
          }}
          onClose={closeDetail}
        />
      )}

      {documentToDelete && (
        <div
          className="documents-page__modal"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeDeleteDialog()
            }
          }}
        >
          <section
            className="documents-page__dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-document-title"
          >
            <h2 className="documents-page__dialog-title" id="delete-document-title">
              Eliminar documento
            </h2>
            <p className="documents-page__dialog-text">
              ¿Seguro que quieres eliminar “{documentToDelete.nombre}”? Esta acción
              solo afecta a la lista actual.
            </p>

            {deleteError && (
              <p className="documents-page__dialog-error" role="alert">
                {deleteError}
              </p>
            )}

            <div className="documents-page__dialog-actions">
              <button
                className="documents-page__dialog-cancel"
                type="button"
                autoFocus
                disabled={isDeleting}
                onClick={closeDeleteDialog}
              >
                Cancelar
              </button>
              <button
                className="documents-page__dialog-delete"
                type="button"
                disabled={isDeleting}
                onClick={handleDelete}
              >
                {isDeleting ? 'Eliminando…' : 'Eliminar'}
              </button>
            </div>
          </section>
        </div>
      )}
    </section>
  )
}

export default DocumentsPage

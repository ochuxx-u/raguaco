import { useEffect, useRef, useState } from 'react'
import documentsService from '../services/documentsService.js'

// Carga los documentos del usuario y mantiene la selección compartida entre
// Chat y Voz. La selección vive en `App.jsx`; este hook la sincroniza para que
// cambiar de pestaña no reinicie los documentos marcados.
export default function useDocumentSelection({
  currentUser,
  initialSelectedDocumentIds = [],
  onSelectedDocumentsChange = () => {},
}) {
  const [documents, setDocuments] = useState([])
  const [isDocumentsLoading, setIsDocumentsLoading] = useState(true)
  const [documentsError, setDocumentsError] = useState('')
  const [selectedDocumentIds, setSelectedDocumentIds] = useState(() =>
    initialSelectedDocumentIds.filter(Boolean),
  )

  const documentsRequestRef = useRef(0)
  // Distingue la selección inicial (primer documento por defecto) de una
  // selección vacía elegida por el usuario: si ya ha tocado el panel, no se
  // vuelve a marcar nada automáticamente.
  const hasUserChosenSelection = useRef(false)

  const loadDocuments = async () => {
    const requestId = ++documentsRequestRef.current
    setIsDocumentsLoading(true)
    setDocumentsError('')

    if (!currentUser?.id) {
      setDocuments([])
      setIsDocumentsLoading(false)
      return
    }

    try {
      const nextDocuments = await documentsService.list(currentUser.id)

      if (requestId !== documentsRequestRef.current) return

      setDocuments(nextDocuments)
    } catch {
      if (requestId === documentsRequestRef.current) {
        setDocumentsError('No se pudieron cargar los documentos.')
      }
    } finally {
      if (requestId === documentsRequestRef.current) {
        setIsDocumentsLoading(false)
      }
    }
  }

  useEffect(() => {
    void loadDocuments()
  }, [currentUser?.id])

  useEffect(() => {
    if (isDocumentsLoading) return

    setSelectedDocumentIds((current) => {
      const validIds = current.filter((id) =>
        documents.some((document) => document.id === id),
      )

      if (validIds.length > 0) return validIds
      if (documents.length === 0 || hasUserChosenSelection.current) return []

      return [documents[0].id]
    })
  }, [documents, isDocumentsLoading])

  useEffect(() => {
    // Al cambiar de usuario la selección vuelve a su valor por defecto.
    hasUserChosenSelection.current = false
  }, [currentUser?.id])

  useEffect(() => {
    onSelectedDocumentsChange(selectedDocumentIds)
  }, [selectedDocumentIds, onSelectedDocumentsChange])

  const toggleDocument = (document) => {
    if (!document?.id) return

    hasUserChosenSelection.current = true

    setSelectedDocumentIds((current) => {
      const isSelected = current.includes(document.id)

      // Se permite quedarse sin documentos: el chat bloquea la pregunta hasta
      // que se seleccione al menos uno y, sin filtro, el backend busca en todos
      // los documentos del usuario.
      return isSelected
        ? current.filter((id) => id !== document.id)
        : [...current, document.id]
    })
  }

  return {
    documents,
    documentsError,
    isDocumentsLoading,
    loadDocuments,
    selectedDocumentIds,
    toggleDocument,
  }
}

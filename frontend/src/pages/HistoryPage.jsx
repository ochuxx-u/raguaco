import { useEffect, useMemo, useRef, useState } from 'react'
import ConversationList from '../components/history/ConversationList.jsx'
import conversationsService from '../services/conversationsService.js'
import './HistoryPage.css'

function normalizeText(value) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
}

function HistoryPage({ currentUser = null, onOpenConversation = () => {} }) {
  const [conversations, setConversations] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const requestRef = useRef(0)

  const loadConversations = async () => {
    const requestId = ++requestRef.current
    setIsLoading(true)
    setError('')

    if (!currentUser?.id) {
      setConversations([])
      setIsLoading(false)
      return
    }

    try {
      const nextConversations = await conversationsService.list(currentUser.id)

      if (requestId !== requestRef.current) return

      setConversations(nextConversations)
    } catch {
      if (requestId === requestRef.current) {
        setError('No se pudieron cargar las conversaciones.')
      }
    } finally {
      if (requestId === requestRef.current) {
        setIsLoading(false)
      }
    }
  }

  useEffect(() => {
    void loadConversations()
  }, [currentUser?.id])

  const filteredConversations = useMemo(() => {
    const normalizedSearch = normalizeText(searchTerm.trim())

    if (!normalizedSearch) return conversations

    return conversations.filter((conversation) =>
      normalizeText(`${conversation.titulo} ${conversation.ultimaPregunta}`).includes(
        normalizedSearch,
      ),
    )
  }, [conversations, searchTerm])

  const handleSelectConversation = (conversation) => {
    onOpenConversation(
      conversation.id,
      conversation.documentId ?? null,
      conversation.titulo,
    )
  }

  const emptyMessage =
    conversations.length === 0
      ? 'No hay conversaciones todavía.'
      : 'No se encontraron conversaciones con esa búsqueda.'

  return (
    <section className="history-page" aria-labelledby="history-title">
      <header className="history-page__header">
        <h1 className="history-page__title" id="history-title">
          Historial de conversaciones
        </h1>

        <div className="history-page__search">
          <svg
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
            placeholder="Buscar en conversaciones…"
            aria-label="Buscar en conversaciones"
            onChange={(event) => setSearchTerm(event.target.value)}
          />
        </div>
      </header>

      <ConversationList
        conversations={filteredConversations}
        emptyMessage={emptyMessage}
        error={error}
        isLoading={isLoading}
        onRetry={loadConversations}
        onSelect={handleSelectConversation}
      />
    </section>
  )
}

export default HistoryPage

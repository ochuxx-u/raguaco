import PlaceholderPage from './PlaceholderPage.jsx'

function ChatPage({ conversationId }) {
  return (
    <PlaceholderPage
      title="Chat RAG"
      description={
        conversationId
          ? 'Aquí se abrirá la conversación seleccionada.'
          : 'Aquí conversarás con tus documentos y consultarás las fuentes.'
      }
    />
  )
}

export default ChatPage

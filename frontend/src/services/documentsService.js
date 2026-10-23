import {
  getDocumentById,
  listDocuments,
  removeDocument,
  uploadDocument,
} from '../mocks/mockBackend.js'

// Punto único de acceso a Documentos. La implementación interna se sustituirá
// por los endpoints de FastAPI sin cambiar la firma consumida por las páginas.
const documentsService = {
  list() {
    return listDocuments()
  },

  getById(id) {
    return getDocumentById(id)
  },

  upload(file, metadata) {
    return uploadDocument(file, metadata)
  },

  remove(id) {
    return removeDocument(id)
  },
}

export default documentsService

import { getDefaultEvidence, getEvidenceById } from '../mocks/mockBackend.js'

const evidenceService = {
  getById(id) {
    return getEvidenceById(id)
  },

  getDefault() {
    return getDefaultEvidence()
  },
}

export default evidenceService

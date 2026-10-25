import { processVoiceQuery } from '../mocks/mockBackend.js'

const voiceService = {
  process() {
    return processVoiceQuery()
  },
}

export default voiceService

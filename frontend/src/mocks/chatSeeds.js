const vacationSources = [
  {
    id: 'source-manual-politicas-p12',
    documentId: 'doc-manual-politicas',
    documento: 'manual_politicas.pdf',
    pagina: 12,
    fragmento:
      '“…el personal tendrá derecho a 15 días hábiles de vacaciones por cada año cumplido…”',
  },
  {
    id: 'source-manual-politicas-p13',
    documentId: 'doc-manual-politicas',
    documento: 'manual_politicas.pdf',
    pagina: 13,
    fragmento:
      '“…los días de vacaciones se contabilizan como hábiles y deben solicitarse con la anticipación establecida en el calendario interno…”',
  },
]

export const chatSeedMessages = [
  {
    id: 'seed-user-vacaciones',
    role: 'user',
    content: '¿Cuántos días de vacaciones corresponden tras un año de servicio?',
    sources: [],
  },
  {
    id: 'seed-assistant-vacaciones',
    role: 'assistant',
    content: 'Corresponden 15 días hábiles después de completar un año de servicio.',
    sources: vacationSources,
    hasEvidence: true,
  },
]

export { vacationSources }

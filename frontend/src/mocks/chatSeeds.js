const vacationSources = [
  {
    id: 'source-manual-politicas-p12',
    documentId: 'doc-manual-politicas',
    documento: 'manual_politicas.pdf',
    tipo: 'PDF',
    categoria: 'Políticas',
    seccion: 'Sección 4.2',
    pagina: 12,
    chunk: 87,
    fragmento:
      '…de acuerdo con el reglamento interno, el personal tendrá derecho a 15 días hábiles de vacaciones por cada año cumplido de servicio, los cuales podrán fraccionarse previo acuerdo con su jefe directo. Para solicitar este beneficio deberá presentarse la solicitud con al menos quince días de anticipación, indicando las fechas de inicio y término, y contar con la aprobación del área correspondiente…',
    fragmentoDestacado:
      'el personal tendrá derecho a 15 días hábiles de vacaciones por cada año cumplido',
  },
  {
    id: 'source-manual-politicas-p13',
    documentId: 'doc-manual-politicas',
    documento: 'manual_politicas.pdf',
    tipo: 'PDF',
    categoria: 'Políticas',
    seccion: 'Sección 5.1',
    pagina: 13,
    chunk: 102,
    fragmento:
      '…los días de vacaciones se contabilizan como hábiles y deben solicitarse con la anticipación establecida en el calendario interno, considerando las necesidades del área y los plazos de aprobación. Las solicitudes fuera de plazo quedan sujetas a disponibilidad y a la autorización de la jefatura correspondiente…',
    fragmentoDestacado:
      'los días de vacaciones se contabilizan como hábiles y deben solicitarse con la anticipación establecida',
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

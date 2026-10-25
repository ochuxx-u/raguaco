import { vacationSources } from './chatSeeds.js'

export const conversationSeeds = [
  {
    id: 'conversation-vacaciones-permisos',
    titulo: 'Vacaciones y permisos',
    fecha: '01 oct 2026',
    documentId: 'doc-manual-politicas',
    messages: [
      {
        id: 'vacaciones-m1',
        role: 'user',
        content: '¿Cuándo puedo empezar a solicitar vacaciones?',
      },
      {
        id: 'vacaciones-m2',
        role: 'assistant',
        content:
          'Las vacaciones se generan al completar un año de servicio. Antes de ese período puedes consultar las opciones de permiso disponibles.',
        sources: [],
        hasEvidence: true,
      },
      {
        id: 'vacaciones-m3',
        role: 'user',
        content: '¿Los días se cuentan como hábiles o naturales?',
      },
      {
        id: 'vacaciones-m4',
        role: 'assistant',
        content:
          'Se contabilizan como días hábiles y deben solicitarse con la anticipación establecida.',
        sources: [vacationSources[1]],
        hasEvidence: true,
      },
      {
        id: 'vacaciones-m5',
        role: 'user',
        content: '¿Cuántos días de vacaciones corresponden tras un año?',
      },
      {
        id: 'vacaciones-m6',
        role: 'assistant',
        content:
          'Corresponden 15 días hábiles después de completar un año de servicio.',
        sources: [vacationSources[0]],
        hasEvidence: true,
      },
    ],
  },
  {
    id: 'conversation-clausulas-contrato',
    titulo: 'Cláusulas del contrato',
    fecha: '29 sep 2026',
    documentId: 'doc-contrato-proveedor',
    messages: [
      {
        id: 'contrato-m1',
        role: 'user',
        content: '¿Cuál es el plazo de vigencia del contrato?',
      },
      {
        id: 'contrato-m2',
        role: 'assistant',
        content:
          'El contrato tiene una vigencia inicial de doce meses desde su firma.',
        sources: [],
        hasEvidence: true,
      },
      {
        id: 'contrato-m3',
        role: 'user',
        content: '¿Existe renovación automática?',
      },
      {
        id: 'contrato-m4',
        role: 'assistant',
        content:
          'Sí, se renueva por períodos iguales salvo aviso contrario con treinta días de anticipación.',
        sources: [],
        hasEvidence: true,
      },
      {
        id: 'contrato-m5',
        role: 'user',
        content: '¿Qué condiciones de pago se aplican?',
      },
      {
        id: 'contrato-m6',
        role: 'assistant',
        content:
          'El pago se realiza dentro de los treinta días posteriores a la factura.',
        sources: [],
        hasEvidence: true,
      },
      {
        id: 'contrato-m7',
        role: 'user',
        content: '¿Qué ocurre si se incumple una cláusula?',
      },
      {
        id: 'contrato-m8',
        role: 'assistant',
        content:
          'El incumplimiento puede generar una penalización proporcional al daño causado.',
        sources: [],
        hasEvidence: true,
      },
      {
        id: 'contrato-m9',
        role: 'user',
        content: '¿Qué penalizaciones hay por incumplimiento?',
      },
    ],
  },
  {
    id: 'conversation-preguntas-frecuentes',
    titulo: 'Preguntas frecuentes',
    fecha: '27 sep 2026',
    documentId: 'doc-faq-clientes',
    messages: [
      {
        id: 'faq-m1',
        role: 'user',
        content: '¿Cuánto tarda un reembolso?',
      },
      {
        id: 'faq-m2',
        role: 'assistant',
        content: 'El plazo habitual es de cinco a diez días hábiles.',
        sources: [],
        hasEvidence: true,
      },
      {
        id: 'faq-m3',
        role: 'user',
        content: '¿Cómo se gestiona un reembolso?',
      },
      {
        id: 'faq-m4',
        role: 'assistant',
        content:
          'Puedes solicitarlo desde Soporte indicando el número de pedido.',
        sources: [],
        hasEvidence: true,
      },
    ],
  },
]

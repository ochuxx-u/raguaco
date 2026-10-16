# FRONTEND_SPEC — Especificación del frontend de RAGUACO

> **Versión:** 1.0 — 15 de octubre de 2026
> **Este documento es la fuente de verdad del frontend de RAGUACO.**
> Todo desarrollo de interfaz debe seguir este spec. Ante cualquier duda no cubierta aquí, aplican el mockup y sus modificaciones; no se inventa diseño nuevo.

---

## 1. Objetivo y alcance

Definir las reglas de diseño, estructura, navegación, datos y componentes del frontend web de RAGUACO (sistema RAG conversacional con carga de documentos, chat en lenguaje natural, interacción por voz y presentación de fuentes).

**Alcance de este documento:**
- Stack, restricciones técnicas y convenciones de código.
- Sistema de diseño (tokens extraídos del mockup).
- Layout general, navegación y comportamiento responsive.
- Reglas por pantalla: Landing, Dashboard, Documentos, Chat RAG, Historial, Voz y Evidencia.
- Estrategia de datos con mocks y capa de servicios para la futura API FastAPI.

**Fuera de alcance (por ahora):** backend, base de datos, autenticación real, captura de voz real, y cualquier tecnología no listada en la sección 3.

---

## 2. Fuentes y precedencia

| # | Fuente | Rol |
| :- | :--- | :--- |
| 1 | `Docs/Frontend/FRONTEND_SPEC.md` (este documento) | Fuente de verdad consolidada |
| 2 | `Docs/Frontend/reference/Modificaciones_frontend.md` | Cambios explícitos sobre el mockup |
| 3 | `Docs/Frontend/reference/RAGUACO_AI.html` | Mockup visual de referencia (7 pantallas, 1280×720) |
| 4 | `Docs/Requerimientos/RF - RNF.md` | Alcance funcional (RF11, RF12, RF9, RF6, RNF1, RNF5, etc.) |
| 5 | `Docs/DIAGRAMS.md` | Estructura objetivo del código (`rag_app/frontend/`) |

**Reglas de conflicto:**
1. Las **modificaciones** prevalecen sobre el mockup.
2. Este **spec** prevalece sobre interpretaciones libres del mockup.
3. Los **RF/RNF** definen comportamiento funcional; el mockup define lo visual.
4. Regla de oro: **todo elemento visual debe rastrearse al mockup o a las modificaciones.** Lo derivado (responsive, accesibilidad, normalización de tokens) está marcado como tal en este documento.

---

## 3. Stack, ubicación y restricciones

| Aspecto | Decisión |
| :--- | :--- |
| Framework | React |
| Build tool | Vite |
| Lenguaje | JavaScript (sin TypeScript) |
| Estilos | CSS plano (sin Tailwind ni CSS-in-JS) |
| Ubicación | `/frontend` en la raíz del repositorio |
| Datos iniciales | Mocks locales (backend aún no existe) |
| Navegación | Estado interno de React (sin React Router por ahora) |

**Prohibido por ahora:** TypeScript, Tailwind, Redux, Next.js, React Router y librerías de componentes/iconos. **No agregar dependencias adicionales sin aprobación previa.** Los iconos se implementan como SVG en línea.

---

## 4. Convenciones

- **Idioma de la interfaz: únicamente español.** Todo texto visible (títulos, botones, placeholders, mensajes de error/vacío, `aria-label`, tooltips) va en español.
- **Identificadores de código en inglés:** nombres de componentes, archivos, carpetas, funciones, variables, props y clases CSS.
- **Formato de fechas** (según mockup): `12 sep 2026`, `01 oct 2026` (día de dos dígitos, mes abreviado en español, año de cuatro dígitos).
- **CSS plano:** tokens globales en `src/styles/`; estilos de componentes co-locados junto a su `.jsx`; clases con prefijo por componente (estilo BEM corto, p. ej. `.document-row__status`). Sin CSS Modules obligatorio; si se usa, es una decisión de implementación, no de diseño.
- **Estructura objetivo de referencia** (no se crea completa de una vez; ver sección 10):

```text
frontend/
├── index.html
├── package.json
├── vite.config.js
├── public/
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── config.js                 (USE_MOCKS, VITE_API_URL)
    ├── styles/                   (tokens.css, base.css)
    ├── layout/                   (AppLayout, Sidebar, FloatingUserButton)
    ├── pages/                    (LandingPage, DashboardPage, DocumentsPage,
    │                              ChatPage, HistoryPage, VoicePage, EvidencePage)
    ├── components/               (common/, documents/, chat/, evidence/,
    │                              history/, voice/, dashboard/)
    ├── services/                 (http.js + servicios por dominio)
    ├── mocks/                    (semillas + mockBackend.js)
    ├── hooks/
    └── utils/
```

---

## 5. Sistema de diseño

> Tokens extraídos directamente del mockup (`RAGUACO_AI.html`). Los nombres de variables son propuesta de implementación; los **valores son obligatorios**.

### 5.1 Colores

| Token | Valor | Uso en el mockup |
| :--- | :--- | :--- |
| `--color-bg` | `#0F172A` | Fondo general y barra superior |
| `--color-bg-glow` | gradiente radial `#1E3A8A → #0F172A` (centro 75% 30%) | Fondo de Landing |
| `--color-surface` | `#1E293B` | Tarjetas, paneles, inputs |
| `--color-surface-deep` | `#1E3A8A` | Avatar, cuadros de tipo de archivo |
| `--color-border` | `#334155` | Bordes de tarjetas y separadores |
| `--color-text` | `#F8FAFC` | Texto principal |
| `--color-text-muted` | `#CBD5E1` | Texto secundario |
| `--color-primary` | `#2563EB` | Botón primario, logo |
| `--color-interactive` | `#3B82F6` | Acentos, bordes activos, gráficos SVG |
| `--color-accent` | `#22D3EE` | Acento cian: marca "AI", estados Listo, enlaces activos |
| `--color-danger` | `#FF8A80` / fondo `#2A1215` / borde `#5C2B2E` | Acciones destructivas/errores (observado en el mockup) |
| `--color-status-error` | `#FB923C` | Badge "Error" |

Glows y sombras del mockup:
- Botón primario: `box-shadow: 0 0 28px rgba(59,130,246,.6)`.
- Logo (cuadrado): `box-shadow: 0 0 18px rgba(34,211,238,.5)`.
- Tarjetas flotantes: `box-shadow: 0 20px 40px rgba(0,0,0,.4)`.

### 5.2 Tipografía

- **Familia:** Manrope (pesos 400, 600, 800), fallback `system-ui, sans-serif`.
- **Tamaños observados en el mockup (usar esta escala):** 12 (badges, etiquetas), 13 (texto secundario), 14 (cuerpo/nav), 15 (título de fila), 16–18 (subtítulos y botones), 24–34 (títulos de sección), 72 (título hero de Landing).
- Títulos con peso 800; subtítulos y énfasis con 600; cuerpo con 400.

### 5.3 Radios

| Token | Valor | Uso |
| :--- | :--- | :--- |
| `--radius-button` | `12px` | Botones |
| `--radius-card` | `16px` | Tarjetas y paneles |
| `--radius-file-icon` | `11px` | Cuadro de tipo de archivo (44×44) |
| `--radius-logo` | `9px` | Cuadrado del logo (30×30) |
| `--radius-pill` | `99px` | Badges y chips |

### 5.4 Badges de estado de documento

Píldora (`border-radius: 99px`, borde 1px, fondo transparente, `font-size: 12px`, peso 700). Mapean al enum `EstadoDocumento` del diagrama de clases:

| Estado (UI) | Color | Texto secundario asociado |
| :--- | :--- | :--- |
| Pendiente | `#CBD5E1` | "En cola" |
| Procesando | `#3B82F6` | "Indexando N%" |
| Listo | `#22D3EE` | "N chunks" |
| Error | `#FB923C` | "Sin chunks" |

### 5.5 Reglas generales de UI

- Iconos: SVG en línea con `stroke` (`currentColor`), trazo redondeado; tamaño de referencia 16–20px. Sin librerías externas.
- Todo botón de icono lleva `aria-label` en español y tooltip/título.
- Estados obligatorios en cada lista/panel: **cargando** (spinner), **vacío** (mensaje informativo) y **error** (mensaje + reintentar). Textos de vacío por pantalla se definen en la sección 8.
- Contraste: texto principal sobre fondos oscuros siempre `--color-text` o `--color-text-muted`; nunca grises arbitrarios.

---

## 6. Layout general

### 6.1 App shell (pantallas de la aplicación)

- **Sidebar izquierdo colapsable** (modificación explícita; reemplaza la barra superior del mockup en las pantallas de la aplicación).
  - Opciones, en este orden: **Dashboard, Documentos, Chat, Historial, Voz, Evidencia**.
  - Ítem activo: fondo `--color-surface`, texto `--color-text` y acento `--color-accent`.
  - Cabecera: logo "RAGUACO AI" (cuadrado azul + texto, "AI" en cian).
  - Pie: indicador "Sistema activo" con punto cian (elemento del mockup reubicado aquí al desaparecer la barra superior).
  - **Colapsable:** expandido ~240px (icono + etiqueta), colapsado ~72px (solo iconos, con tooltip). Botón de alternar visible en el propio sidebar. El estado vive en `App.jsx` (sin persistencia por ahora).
- **Usuario como botón flotante** (modificación explícita): botón circular fijo, esquina inferior derecha, visible en todas las pantallas (incluida Landing). Estilo según el círculo de usuario del mockup: fondo `--color-surface-deep`, borde `--color-interactive`. Al hacer clic abre un menú pequeño (nombre/email de mock, acciones placeholder). **El círculo de usuario de la barra superior del mockup no se duplica.**
- **Sin scroll horizontal** en ninguna pantalla; el scroll vertical ocurre dentro del contenedor de contenido de cada pantalla.

### 6.2 Landing aparte

- La Landing **no muestra el sidebar**: conserva su diseño propio del mockup (barra superior con logo, enlaces a Dashboard/Documentos/Chat/Historial/Voz, indicador "Sistema activo", hero, tarjetas flotantes y franja de pipeline).
- Sus enlaces navegan a las vistas de la aplicación (navegación por estado).

### 6.3 Textos largos: crecimiento limitado y scroll interno

Regla transversal (aplica a todas las pantallas):

1. **Listas y paneles** (documentos, historial, conversaciones, evidencias, mensajes): altura máxima del contenedor con `overflow-y: auto`; el crecimiento del contenido no estira la página.
2. **Textos de una línea** (nombres de archivo, títulos de conversación): truncado con elipsis; el texto completo, si aplica, en el panel de detalle o tooltip.
3. **Extractos** (última pregunta en Historial, citas en evidencia): máximo 2 líneas visibles (line-clamp).
4. **Mensajes del chat y respuestas**: sin límite de líneas, pero sin romper el layout: `overflow-wrap: anywhere` para palabras largas; el scroll es del contenedor de mensajes.
5. **Campo de escritura del chat**: crece hasta ~5 líneas y luego hace scroll interno.
6. **Visor de evidencia**: fragmento con altura máxima (~40vh) y scroll interno.

### 6.4 Responsive

Diseño responsive obligatorio (modificaciones). Comportamiento derivado de esa regla:

| Ancho | Sidebar | Contenido |
| :--- | :--- | :--- |
| ≥ 1024px | Visible, expandible/colapsable por el usuario | Multi-columna (Chat: 3 columnas) |
| 768–1023px | Colapsado por defecto; al expandir, se superpone sobre el contenido | Paneles laterales (documentos/evidencia en Chat) se abren como panel superpuesto |
| < 768px | Oculto por defecto; se abre como panel deslizante desde la izquierda con botón de menú | Una sola columna; tarjetas apiladas; panel de evidencia accesible por botón (overlay) |

---

## 7. Navegación

- **Sin React Router.** El estado de vista vive en `App.jsx` con `useState`.
- Vistas: `landing` (inicial), `dashboard`, `documents`, `chat`, `history`, `voice`, `evidence`.
- `App.jsx` además mantiene: `conversationId` seleccionado (para abrir el Chat desde Historial/Dashboard) y el estado colapsado del sidebar. No hace fetching ni conoce `services/`.
- `main.jsx` es solo el punto de entrada: importa CSS global, monta `<App />` en `#root` con `StrictMode`. Sin lógica.
- Clic en el logo (sidebar o Landing) → vuelve a `landing`.
- Las pantallas de la aplicación se renderizan dentro del App shell; `landing` se renderiza sola.

---

## 8. Pantallas

> Los textos entre comillas son copy del mockup y deben respetarse tal cual.

### 8.1 Landing (`LandingPage`)

- **Barra superior** (como el mockup): logo "RAGUACO AI", enlaces Dashboard · Documentos · Chat · Historial · Voz, indicador "Sistema activo".
- **Hero:** etiqueta "PLATAFORMA DE CONOCIMIENTO CON IA"; título "RAGUACO AI" (con "AI" en cian); subtítulo "Conversa con tus documentos mediante inteligencia artificial"; párrafo "Carga tus archivos, vectorízalos automáticamente y haz preguntas en lenguaje natural, por texto o voz, con respuestas fundamentadas en fuentes."
- **Botones:** "Comenzar ahora" (primario, con glow) y "Ver demo" (secundario con borde).
- **Tarjetas flotantes:** "Documento cargado" ("manual_politicas.pdf · 48 págs."), "Respuesta con fuentes" ("“Según la página 12…” · relevancia 94%"), "Modo voz" ("Habla con tu base de conocimiento").
  - Nota: el texto de la tarjeta "Respuesta con fuentes" se conserva como copy decorativo; ver regla de score en 8.4/8.7.
- **Franja de pipeline** (se conserva; la modificación de eliminación aplica **solo al Dashboard**): `Upload → Process → Vectorize → Retrieve → Respond` como píldoras.
- Fondo con gradiente `--color-bg-glow` y grafo decorativo SVG (líneas azules y nodos cian).

### 8.2 Dashboard (`DashboardPage`)

- **Sin bloque "Pipeline RAG"** (eliminado por modificación explícita).
- Cabecera: "Bienvenido de nuevo" + "Tu base de conocimiento está lista para responder." + botón "+ Subir nuevo documento".
- **Tarjetas de estadísticas** (valores de mocks): "Documentos cargados" 24 · "Conversaciones" 58 · "Chunks generados" 3.412 · "Estado del sistema" "Operativo".
- **"Actividad reciente"**: lista de eventos con ejemplos del mockup: "manual_politicas.pdf — vectorización completada", "Conversación “Vacaciones y permisos” — 6 mensajes", "contrato_proveedor.docx — procesando 62%".
- Acción "+ Subir nuevo documento" → vista Documentos (flujo de carga).

### 8.3 Documentos (`DocumentsPage`)

- Título "Gestor de documentos". La franja de pipeline del mockup se conserva en la cabecera.
- **Zona de carga:** drag & drop "Arrastra tus archivos aquí" + "PDF, DOCX, TXT · asigna una categoría al subir" + botón "Subir documento".
- **Listado** (filas de datos): cuadro de tipo (PDF/DOC/TXT, 44×44, radio 11px), nombre, categoría · fecha, columna de progreso ("214 chunks", "Indexando 62%", "En cola", "Sin chunks"), badge de estado, y acciones por fila: "Preguntar", "Ver detalle", "Eliminar".
- **Documentos de referencia del mockup** (semillas de mocks): `manual_politicas.pdf` (Políticas · 12 sep 2026 · Listo), `contrato_proveedor.docx` (Legal · 30 sep 2026 · Procesando 62%), `faq_clientes.txt` (Soporte · 01 oct 2026 · Pendiente), `reporte_q2.pdf` (Finanzas · 28 sep 2026 · Error).
- "Eliminar" es acción destructiva: usa tonos `--color-danger` y pide confirmación.
- "Preguntar" navega al Chat. "Ver detalle" abre el panel de detalle del documento (metadatos + acciones).
- Estado vacío: "Aún no has cargado documentos."

### 8.4 Chat RAG (`ChatPage`)

- **Tres columnas en escritorio:**
  1. **Documentos** (izquierda): lista de documentos y filtros por categoría (mockup: "Políticas · Legal · Soporte").
  2. **Conversación** (centro): hilo de mensajes; respuesta con chips de fuentes ("Fuente 1 · pág. 12", "Fuente 2 · pág. 13").
  3. **Fuentes y evidencia** (derecha): **panel separado** (modificación explícita) con tarjetas de evidencia: documento · página, cita textual y "Ver más".
- **Controles orientados a iconos** (modificación explícita): adjuntar (＋), **voz** (micrófono) y **enviar** (flecha/avión de papel) como botones de icono con `aria-label` en español. Los controles de voz y envío tienen la **transición visual** indicada en las modificaciones: en su estado compacto priorizan el icono. El campo de texto usa el placeholder "Pregunta algo sobre tus documentos…".
- **Fuentes bajo la respuesta:** cada fuente es cliqueable y enfoca/abre la evidencia correspondiente en el panel.
- **Sin evidencia (RF9):** cuando la respuesta no tenga respaldo documental, mostrar un aviso explícito en lugar de una respuesta inventada. Copy base: "No encontré información suficiente en tus documentos para responder esta pregunta."
- **Score de similitud: NO mostrar** porcentajes ni valores de similitud/relevancia (ver 9.6). El mockup muestra "Relevancia 94%": esa presentación queda pendiente hasta que el backend lo defina.
- El panel de evidencia pasa a overlay/drawer en pantallas medianas y pequeñas (6.4).

### 8.5 Historial (`HistoryPage`)

- Título "Historial de conversaciones" + buscador ("Buscar en conversaciones…").
- **Filas completas clickeables** (modificación explícita): **sin botón "Abrir"**. Toda la fila abre la conversación en el Chat.
- **Hover completo** (modificación explícita): la fila cambia visualmente al pasar el cursor (cambio de fondo a `--color-surface` y borde a `--color-interactive`, cursor pointer, transición breve). Debe existir también estado `focus-visible` equivalente para teclado.
- Contenido de fila (mockup): título ("Vacaciones y permisos"), extracto de última pregunta, "01 oct 2026 · 6 mensajes".
- Conversaciones de referencia del mockup (semillas): "Vacaciones y permisos" (6 mensajes), "Cláusulas del contrato" (9), "Preguntas frecuentes" (4).
- Estado vacío: "No hay conversaciones todavía."

### 8.6 Voz (`VoicePage`)

- **Flujo simulado con mocks en esta fase** (decisión): sin captura real de micrófono y **sin Web Speech API**.
- Elementos (mockup): texto "Estoy escuchando…", waveform de barras cian (puede ser estática o con animación CSS simple), controles **Micrófono** (iniciar) y **Detener**, orientados a icono con `aria-label` (modificación de controles por iconos). Aplican la **transición visual** de los controles de voz y envío: en su estado compacto priorizan el icono.
- Paneles inferiores: "Transcripción" ("¿Cuántos días de vacaciones tengo?") y "Respuesta" ("Corresponden 15 días hábiles, según la página 12.").
- **Transcripción:** el texto de la transcripción se muestra en **gris oscuro** (modificación visual que prevalece sobre el mockup), garantizando contraste adecuado con su fondo.
- **Fuentes/evidencia:** la Voz también muestra el panel de evidencia (decisión: panel dentro de Chat y Voz), reutilizando los componentes de la familia `Evidence*`.
- Estados del flujo simulado: inactivo → "escuchando" → "procesando" → resultado (transcripción + respuesta + evidencia), con latencias simuladas desde mocks.

### 8.7 Evidencia (`EvidencePage`)

- **Pantalla independiente** (nombre final `EvidencePage`; no `SourcesPage`).
- **Tarjeta de documento:** cuadro PDF, "manual_politicas.pdf", migas de contexto "Políticas · Sección 4.2 · Página 12 · Chunk #87". **Sin bloque de similitud** (el mockup muestra "0.94 / Similitud": no se implementa, ver 9.6).
- **Fragmento:** cita textual con el fragmento relevante resaltado (cian/`--color-accent`).
- **Acciones:** "Abrir documento" (navega a Documentos con el detalle abierto) y "Volver al chat" (navega a Chat).
- El fragmento respeta la regla de scroll interno de 6.3.

---

## 9. Datos: mocks y servicios

### 9.1 Regla de acceso a datos

- **Los componentes y páginas nunca acceden a datos directamente**: consumen `src/services/`.
- La capa de servicios es el **único** punto de contacto con el backend (futuro FastAPI) y la única que conoce `src/mocks/`.
- Ningún secreto/clave en el frontend (RNF5): todo pasa por el backend.

### 9.2 Servicios (`src/services/`)

| Archivo | Responsabilidad | Endpoints futuros (referencia) |
| :--- | :--- | :--- |
| `http.js` | Wrapper de `fetch`: base URL (`VITE_API_URL`), JSON, errores normalizados | — |
| `documentsService.js` | Listar, consultar, subir, eliminar documentos; estado de procesamiento | `GET /documents`, `GET /documents/{id}`, `POST /documents`, `DELETE /documents/{id}` |
| `queriesService.js` | Preguntas del chat (RAG) | `POST /query` con `{ pregunta, conversacionId? }` → `{ respuesta, fuentes }` |
| `conversationsService.js` | Conversaciones e historial de mensajes | `GET/POST /conversations`, `GET /conversations/{id}/messages` |
| `voiceService.js` | Voz (simulada en esta fase) | `POST /voice` (procesarVoz del diagrama) |
| `dashboardService.js` | Resumen del Dashboard | Compone con documentos + conversaciones; endpoint agregado solo si el backend lo ofrece |

- `src/config.js` expone `USE_MOCKS` (hoy `true`) y la URL base. Cambiar a API real = cambiar implementación interna de cada servicio, **sin tocar componentes**.

### 9.3 Mocks (`src/mocks/`)

- Aislados aquí: semillas de datos + `mockBackend.js`.
- `mockBackend.js` simula: latencia artificial (300–800ms), mutaciones (subir → Pendiente → Procesando con progreso → Listo; eliminar), respuestas del chat con y sin evidencia, y datos del Dashboard. Trabaja sobre **copias** de las semillas.
- Semillas de referencia (extraídas del mockup): 4 documentos (ver 8.3), 3 conversaciones (ver 8.5), estadísticas 24/58/3.412/Operativo, conversación de ejemplo del Chat ("¿Cuántos días de vacaciones corresponden tras un año de servicio?" con fuentes en pág. 12 y 13), evidencia `manual_politicas.pdf · Sección 4.2 · Página 12 · Chunk #87`.
- Al existir el backend, `src/mocks/` se elimina sin tocar componentes.

### 9.4 Estados de documento (contrato UI ↔ backend)

Los labels y colores de UI (5.4) mapean al enum del diagrama de clases: `pendiente → "Pendiente"`, `procesando → "Procesando"`, `listo → "Listo"`, `error → "Error"`. El progreso (`Indexando N%`, `En cola`, `N chunks`, `Sin chunks`) es texto secundario del estado.

### 9.5 Datos pendientes de contrato (backend)

Formas exactas de request/response (campos, paginación, filtros) quedan pendientes del backend. Los servicios definen la **firma** esperada y aíslan el cambio.

### 9.6 Score de similitud — regla explícita

**No asumir que se mostrará score de similitud.** La UI **no** muestra porcentajes ni valores (`Relevancia 94%`, `0.94`, etc.) en ninguna vista (Chat, Voz, Evidencia). El mockup los incluye, pero su presentación queda **pendiente hasta que el backend defina** si existirá y con qué forma. Los componentes de evidencia deben poder renderizar sin ese dato.

---

## 10. Componentes

**Estrategia: incremental.** No se crea el inventario completo desde el inicio; cada paso implementa **solo los componentes que esa pantalla necesita**, reutilizando los ya existentes. Este inventario es un objetivo de referencia, no una orden de creación:

| Grupo | Componentes objetivo |
| :--- | :--- |
| `common/` | Button, IconButton, Card, Badge, Spinner, EmptyState, ErrorState, Modal, ConfirmDialog, SearchInput |
| `documents/` | DocumentUploader, DocumentList, DocumentRow, DocumentStatusBadge, DocumentDetailPanel |
| `chat/` | ChatWindow, MessageList, MessageBubble, ChatInput, SourceChip, NoEvidenceNotice |
| `evidence/` | EvidencePanel (dentro de Chat/Voz), EvidenceCard, EvidenceViewer |
| `history/` | ConversationList, ConversationItem |
| `voice/` | VoiceRecorder (simulado), RecordingIndicator, TranscriptView, AudioPlayer (placeholder) |
| `dashboard/` | StatCard, RecentActivity |
| `layout/` | AppLayout, Sidebar, FloatingUserButton |

Reglas: nombres en inglés; un componente = una carpeta/par de archivos (`Component.jsx` + `Component.css` co-locado cuando aplique); sin lógica de negocio dentro de componentes de presentación.

---

## 11. Accesibilidad y UX básicas

- Todos los botones de icono con `aria-label` en español; tooltips donde el icono no sea autoexplicativo.
- Navegación por teclado: sidebar, filas del historial y controles del chat alcanzables con Tab; `focus-visible` visible.
- Estados de carga/vacío/error en todas las listas y paneles.
- Textos largos: cumplir siempre 6.3.
- Animaciones discretas (hover, transiciones ≤150ms); la waveform de Voz puede usar animación CSS simple.

---

## 12. Pendientes y fuera de alcance por ahora

| Tema | Estado |
| :--- | :--- |
| Score de similitud/relevancia | **Pendiente del backend**; la UI no lo muestra (9.6) |
| Formas exactas de request/response | Pendientes del backend (9.5) |
| Autenticación real | Fuera de alcance (RNF8 la prevé como extensión futura) |
| Captura de voz real / Web Speech API / streaming | Fuera de alcance en esta fase (Voz simulada) |
| React Router | No por ahora; migrable cuando hagan falta URLs compartibles |
| Librerías de iconos, componentes o estado global | No por ahora (iconos SVG locales) |
| Parámetros de recuperación (Top-K, umbral, filtros) | No aparecen en el mockup; fuera de la primera versión |

---

*Documento derivado de `Docs/Frontend/reference/RAGUACO_AI.html` (mockup), `Docs/Frontend/reference/Modificaciones_frontend.md`, `Docs/Requerimientos/RF - RNF.md` y `Docs/DIAGRAMS.md`. Cualquier cambio de diseño debe reflejarse primero en este spec.*

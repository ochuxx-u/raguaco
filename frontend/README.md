# RAGUACO AI — Frontend

Interfaz web de **RAGUACO**, un sistema RAG conversacional para cargar documentos, formular preguntas en lenguaje natural y obtener respuestas fundamentadas en fuentes.

Construida con **React**, **Vite**, **JavaScript** y **CSS**.

## Requisitos

- Node.js `^20.19.0` o `>=22.12.0` (requisito de Vite 8)
- npm

## Instalación

```bash
npm install
```

## Scripts disponibles

| Comando | Descripción |
| :--- | :--- |
| `npm run dev` | Inicia el servidor de desarrollo con recarga en caliente (HMR). |
| `npm run build` | Genera el build de producción en el directorio `dist/`. |
| `npm run preview` | Sirve localmente el build de producción para previsualizarlo. |

## Estructura del proyecto

| Archivo | Descripción |
| :--- | :--- |
| `index.html` | Documento HTML de entrada de la aplicación. |
| `src/main.jsx` | Punto de entrada de React; monta el componente raíz. |
| `src/App.jsx` | Componente raíz de la aplicación. |
| `src/index.css` | Estilos globales base. |
| `vite.config.js` | Configuración de Vite con el plugin oficial de React. |

## Estado actual

Proyecto en fase de andamiaje: incluye únicamente la aplicación React mínima. Todavía no hay pantallas, mocks ni servicios implementados.

## Documentación

La especificación del frontend, que es la fuente de verdad del proyecto, está en [`../Docs/Frontend/FRONTEND_SPEC.md`](../Docs/Frontend/FRONTEND_SPEC.md).

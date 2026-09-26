# Requerimientos Principales - Sistema RAG Conversacional

## Requerimientos Funcionales del Sistema

| ID | Requerimiento | Descripción Ampliada | Prioridad |
| :--- | :--- | :--- | :--- |
| **RF1** | Gestión de documentos | El sistema deberá permitir al usuario cargar, consultar y eliminar documentos compatibles. Los documentos podrán pertenecer a cualquier temática. | Alta |
| **RF2** | Procesamiento automático de documentos | Cada documento nuevo deberá ser procesado automáticamente mediante un pipeline de ingesta.<br>El proceso debe incluir:<br>Documento → extracción de texto → limpieza → fragmentación → generación de embeddings → almacenamiento vectorial. | Alta |
| **RF3** | Almacenamiento persistente de la información | El sistema deberá almacenar:<br>Documento original, información de los documentos, chunks, embeddings, metadatos, estado de procesamiento | Alta |
| **RF4** | Gestión del estado del procesamiento | El sistema deberá controlar el estado de cada documento durante su procesamiento | Alta |
| **RF5** | Consulta en lenguaje natural | El usuario podrá generar preguntas utilizando lenguaje natural. Cada consulta se debe transformar en un embedding compatible con los documentos almacenados. | Alta |
| **RF6** | Recuperación semántica de la información | El sistema deberá comparar el embedding de la consulta con los embeddings almacenados y recuperar los fragmentos más relevantes.<br>Top-K[^1], Umbral de similitud, documento, metadatos o categorías opcionales. | Alta |
| **RF7** | Generación de respuestas mediante RAG | El sistema deberá construir un contexto a partir de los fragmentos recuperados y enviarlo junto con la pregunta a un modelo de lenguaje.<br>Debe generar una respuesta basada principalmente en la información recuperada.<br>Pregunta → embedding → retrieval → contexto → LLM → respuesta. | Alta |
| **RF8** | Presentación de fuentes | El sistema deberá indicar qué documentos respaldan la respuesta generada. | Alta |
| **RF9** | Control de respuesta sin evidencias | Cuando el sistema no encuentre información suficientemente relacionada con la pregunta, deberá indicarlo explícitamente en lugar de generar una respuesta sin fundamento documental. | Alta |
| **RF10** | Gestión de conversaciones | El sistema deberá permitir mantener conversaciones compuestas por múltiples mensajes. | Media |
| **RF11** | Interfaz y API | El sistema deberá proporcionar una interfaz mediante la cual el usuario pueda:<br>- Cargar documentos<br>- Consultar documentos<br>- Realizar preguntas<br>- Visualizar respuestas<br>- Consultar fuentes<br>Las funcionalidades principales deberán estar disponibles a través de una API desarrollada con FastAPI o tecnología equivalente. | Alta |
| **RF12** | Interacción mediante voz | En la fase avanzada del proyecto, el sistema deberá permitir al usuario realizar preguntas mediante voz.<br>El flujo será:<br>Voz → Speech-to-Text → RAG → respuesta textual → Text-to-Speech → voz.<br>Posteriormente podrá evolucionarse hacia conversación de voz en tiempo real mediante streaming o WebRTC. | Alta, versión final |

[^1]: **Comentario [KG1]:** Es un parámetro de configuración en los modelos de inteligencia artificial y modelos de lenguaje (LLM) que limita el número de palabras o tokens candidatos más probables entre los que la IA puede elegir en cada paso para generar texto.

---

## Requerimientos No Funcionales

| ID | Requerimiento | Descripción Ampliada |
| :--- | :--- | :--- |
| **RNF1** | Modularidad | El sistema deberá desarrollarse utilizando una arquitectura modular que separe responsabilidades como:<br>- Carga y extracción<br>- Chunking<br>- Embeddings<br>- Almacenamiento<br>- Retrieval<br>- Generación<br>- API<br>- Interfaz<br>- Voz |
| **RNF2** | Mantenibilidad | Esto permitirá modificar o sustituir componentes de forma independiente.<br>El código deberá ser legible, documentado y organizado siguiendo buenas prácticas de desarrollo en Python.<br>Se deberá evitar concentrar toda la lógica de la aplicación en un único archivo o componente. |
| **RNF3** | Escalabilidad | El sistema deberá permitir incrementar progresivamente:<br>- Número de documentos<br>- Número de chunks<br>- Embeddings<br>- Consultas<br>- Conversaciones<br>- Usuarios en futuras versiones<br>El almacenamiento vectorial deberá soportar mecanismos de indexación adecuados cuando aumente la cantidad de información. |
| **RNF4** | Rendimiento | La recuperación semántica deberá ejecutarse con una latencia que permita una experiencia conversacional adecuada. |
| **RNF5** | Seguridad | Las credenciales, claves de API y secretos deberán almacenarse mediante variables de entorno y nunca escribirse directamente en el código fuente.<br>El sistema deberá impedir que secretos del backend sean expuestos al cliente. |
| **RNF6** | Confiabilidad y manejo de errores | Un fallo durante el procesamiento de un documento o una consulta no deberá provocar la caída completa de la aplicación. |
| **RNF7** | Trazabilidad | El sistema deberá permitir identificar cómo se produjo una respuesta. |
| **RNF8** | Extensibilidad | La arquitectura deberá permitir incorporar posteriormente:<br>- Nuevos formatos de documentos<br>- Nuevos modelos de embeddings<br>- Diferentes LLM<br>- Búsqueda híbrida<br>- Reranking<br>- Autenticación<br>- Nuevos proveedores de voz<br>sin reconstruir completamente la aplicación. |
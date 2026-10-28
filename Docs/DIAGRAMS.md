# Diagramas

En esta sección se recopilan los diagramas UML y de arquitectura del sistema **raguaco**.

## Casos de uso

![Casos de uso](UML/imagenes/Casos_de_Uso.png)

## Arquitectura

![Arquitectura High Level](UML/imagenes/DIA-ArquitecturaHighLevel.png)

## Componentes

![Diagrama de componentes](UML/imagenes/DIA-Componentes.png)

## Diagrama de clases

![Diagrama de clases](UML/imagenes/Diagrama_Clases.png)

## Entidad-Relación

![Diagrama entidad relacion](UML/imagenes/diagrama%20entidad%20relacion.png)

## Diagramas de secuencia

### Consulta con lenguaje natural (Ask with PNL)

![Secuencia Ask with PNL](UML/imagenes/DIA-SECUENCIA_Ask-With-PNL.png)

### ETL de documentos

![Secuencia ETL Documents](UML/imagenes/DIA-SECUENCIA_ETL-DOCUMENTS.png)

### Interacción por voz

![Secuencia Voice Interact](UML/imagenes/DIA-SECUENCIA_Voice-Interact.png)

---

## Estructura de rutas

A continuación se presenta el orden de carpetas y archivos que tendrá la aplicación:

> La API expone los modelos de dominio (`domain/models`) directamente: no hay una
> capa de DTO (`schemas`) intermedia. Los servicios de `domain/services` son los que
> traducen entre la entidad y el exterior cuando haga falta.

> `app/ai-models/` es el apartado donde se guardarán los modelos locales que son
> parte del proyecto (pesos, checkpoints y archivos de configuración asociados),
> de forma que puedan versionarse junto al código y servirse en tiempo de ejecución
> sin depender de una descarga externa. Se ubica al lado de `api/` porque es un
> recurso de la aplicación que el backend carga para inferencia.

```text
rag_app/
├── App/
│   ├── main.py
│   ├── api/
│   │   ├── deps.py
│   │   └── routes/
│   │       ├── documents.py
│   │       ├── queries.py
│   │       ├── conversations.py
│   │       ├── users.py
│   │       └── voice.py
│   ├── ai-models/
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── exceptions.py
│   ├── domain/
│   │   ├── models/
│   │   └── services/
│   │       ├── document_ingestion_service.py
│   │       ├── rag_service.py
│   │       ├── conversation_service.py
│   │       └── voice_service.py
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── repositories/
│   │   ├── vector/
│   │   │   └── pgvector_repository.py
│   │   ├── storage/
│   │   │   └── local_storage.py
│   │   ├── llm/
│   │   │   └── llm_service.py
│   │   ├── embeddings/
│   │   │   └── embedding_service.py
│   │   ├── tts/
│   │   │   ├── kokoro_tts.py
│   │   │   └── tts_text.py
│   │   ├── stt/
│   │   │   ├── whisper_stt.py
│   │   │   └── vad.py
│   │   └── loaders/
│   │       ├── document_loader.py
│   │       ├── text_cleaner.py
│   │       └── chunking_service.py
│   └── tests/
│── frontend/
├── migrations/
├── scripts/
├── requirements.txt
├── .env.example
└── README.md
```

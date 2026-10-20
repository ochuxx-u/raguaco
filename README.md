# Raguaco 🤖 🇨🇴

¡Bienvenido a **Raguaco**! 👋

**Raguaco** es un sistema RAG (*Retrieval-Augmented Generation*) conversacional que permite cargar documentos, procesarlos automáticamente y responder preguntas en lenguaje natural apoyándose en la información recuperada, con fuentes verificables e **interacción por voz**.

## Documentación

### Inciar aplicación (backend)
Para iniciar el servidor de Raguaco es necesario:
1. Instalar dependencias en el archivo `requirements.txt`.
2. Ejecutar servidor:
```
cd App && uvicorn main:app
```

### Iniciar aplicación (frontend)
Para iniciar el apartado visual (lado del cliente) ver [aquí](frontend/README.md).

### Descargar voz para el TTS (Kokoro)

Descargar modelo de voz Kokoro-82M desde HuggingFace
```
# Haber descargado previamente los requirements.txt
hf download onnx-community/Kokoro-82M-v1.0-ONNX --local-dir App/ai-models
```

Debe crearse la ruta `./App/ai-models/`

> [!WARNING]
> Instalar las extensiones necesarios en su SO para la fonética en español
```
# Linux
sudo apt install espeak-ng ffmpeg

# Windows
winget install Gyan.FFmpeg
winget install eSpeak-NG.eSpeak-NG

# macOS
brew install espeak-ng ffmpeg
```

> [!NOTE]
> En Windows también puedes instalar `espeak-ng` con [Scoop](https://scoop.sh/):
```
scoop install main/espeak-ng
```

### Docs iniciales
- [Requerimientos funcionales y no funcionales](Docs/Requerimientos/RF%20-%20RNF.md)
- [Diagramas UML](Docs/DIAGRAMS.md)

## Licencia

Distribuido bajo la licencia [MIT](LICENSE).

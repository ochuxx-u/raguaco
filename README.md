![Logo de Raguaco AI](Docs/logo_ini.png)

# Raguaco 🤖 🇨🇴

¡Bienvenido a **Raguaco**! 👋

**Raguaco** es un sistema RAG (*Retrieval-Augmented Generation*) conversacional que permite cargar documentos, procesarlos automáticamente y responder preguntas en lenguaje natural apoyándose en la información recuperada, con fuentes verificables e **interacción por voz**.

Conoce más acerca de Raguaco:
**[Misión, visión y origen](Docs/MISION_Y_VISION.md)**.

## Documentación

### Inciar aplicación (backend)
Para iniciar el servidor de Raguaco es necesario:
1. Instalar dependencias en el archivo `requirements.txt`.
2. Tener PostgreSQL disponible y configurar `DATABASE_URL` en un archivo `.env` (copiar `.env.example`). Para levantar una base local con el esquema y datos de prueba, ver [Docs/Tests/TESTING_PGVECTOR.md](Docs/Tests/TESTING_PGVECTOR.md).
3. Ejecutar servidor:
```
cd App && uvicorn main:app --reload
```

### Iniciar aplicación (frontend)
Para iniciar el apartado visual (lado del cliente) ver [aquí](frontend/README.md).

### Descarga/instalación de modelos de Inteligencia Artificial

#### Descargar voz para el TTS (Kokoro)

Descargar modelo de voz Kokoro-82M desde HuggingFace
```
# Haber descargado previamente los requirements.txt
hf download onnx-community/Kokoro-82M-v1.0-ONNX --local-dir App/ai-models/kokoro-82m
```

Debe crearse la ruta `./App/ai-models/kokoro-82m/`

> [!WARNING]
> Instalar las extensiones necesarias a continuación en su SO para la fonética en español del modelo TTS
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

##### Configurar el TTS y probar el streaming

En `.env` (copiar `.env.example`). Las rutas son relativas a `App/`:
```
TTS_MODEL=ai-models/kokoro-82m
# int8: menor latencia | onnx/model.onnx: máxima calidad (fp32)
TTS_MODEL_FILE=onnx/model_quantized.onnx
TTS_VOICE=ef_dora
TTS_LANGUAGE=es
TTS_OUTPUT_DIR=storage/tts
```

El servicio no espera a sintetizar toda la respuesta: parte el texto en frases,
escribe un `.wav` por frase en `App/storage/tts/{job_id}/` y entrega cada uno en
cuanto está listo. El primer fragmento es corto para que el audio empiece antes
y los siguientes se mantienen acotados (`TTS_CHUNK_CHARS`) para que cada WAV
esté listo antes de que termine de sonar el anterior: reproducción sin cortes.

Prueba local con el texto editable de la variable `TEXTO` (reproduce por el
altavoz mientras sintetiza, o solo genera los WAV con `--sin-audio`):
```
cd App
python tests_models/probar_tts_streaming.py
python tests_models/probar_tts_streaming.py --sin-audio
python tests_models/probar_tts_streaming.py --texto "Una prueba corta de voz."
```

API (`POST /v1/voice/tts`): responde `application/x-ndjson`, un evento por
línea (`inicio`, `fragmento`, `fin`). Cada `fragmento` trae la URL del WAV para
reproducirlo de inmediato:
```
curl -N -X POST http://localhost:8000/v1/voice/tts \
  -H 'Content-Type: application/json' \
  -d '{"texto":"Hola, esto es una prueba de la respuesta hablada."}'

# El evento fragmento devuelve, por ejemplo:
# {"tipo":"fragmento","indice":0,"nombre":"000.wav","url":"http://.../v1/voice/tts/<job>/000.wav",...}
```
El WAV se descarga con `GET /v1/voice/tts/{job_id}/{nombre}`. Los jobs se
borran solos pasados `TTS_RETENTION_MINUTES` (30 por defecto).

#### Descargar modelo de STT (faster-whisper)

Modelo de transcripción de voz a texto (STT) que Raguaco usa para convertir la pregunta hablada del usuario en texto antes de consultar el RAG. Se ejecuta **en local**, sin API externa.

**1. Instalar las dependencias** (ya incluidas en `requirements.txt`: `faster-whisper`, `soundcard`, `soundfile`):
```
pip install -r requirements.txt
```

**2. Descargar el modelo** desde HuggingFace (variante `small`, ~460 MB):
```
hf download Systran/faster-whisper-small --local-dir App/ai-models/faster-whisper-small
```

Debe crearse la ruta `./App/ai-models/faster-whisper-small/` con los archivos `model.bin`, `config.json`, `tokenizer.json` y `vocabulary.txt`.

Otros tamaños disponibles (más precisos, más pesados y más lentos en CPU): `tiny`, `base`, `medium`, `large-v3`, `large-v3-turbo`, `distil-large-v3`. Para usarlos basta repetir el comando con el repositorio correspondiente, por ejemplo `Systran/faster-whisper-base --local-dir App/ai-models/faster-whisper-base`.

**3. Configurar la ruta del modelo** en `.env` (copiar `.env.example`). Las rutas son relativas a `App/`:
```
STT_MODEL=ai-models/faster-whisper-small
STT_LANGUAGE=es
STT_DEVICE=cpu
STT_COMPUTE_TYPE=int8
```

##### Probar la secuencia completa de voz (STT → RAG → TTS)

El flujo cierra la pregunta **automáticamente** cuando detecta
`VOICE_SILENCE_SECONDS` segundos de silencio después de haber oído voz. El
detector (`DetectorVoz`) acumula bloques del micrófono y entrega el audio
completo; después la API transcribe con faster-whisper, consulta el RAG y
devuelve la respuesta con fuentes y audio por fragmentos.

1. Arranca la API (precarga STT y TTS en segundo plano):
```
cd App
uvicorn main:app --reload
```

2. En otra terminal, habla cuando el script lo indique:
```
cd App
python tests_models/probar_voz_completa.py
```
Opciones útiles: `--sin-audio` (no reproduce), `--archivo pregunta.wav`
(prueba un archivo), `--silencio 1.2` (ajusta el cierre), `--umbral` y
`--calibracion` (ajustan el detector al ruido del micrófono),
`--conversacion-id` (continúa una conversación) y `--usuario-id` (por defecto
usa el usuario de prueba con documentos reales). El script pide unos segundos
de silencio al empezar para medir el ruido de fondo.

La ruta equivalente es `POST /v1/voice/consultar` (multipart):
```
curl -N -X POST http://localhost:8000/v1/voice/consultar \
  -F "audio=@pregunta.wav;type=audio/wav" \
  -F "usuario_id=d18f3e28-0c98-4b29-96d6-89a04c7d716b"
```
Responde NDJSON con `procesando`, `transcripcion`, `respuesta` (texto y
`referencias`) y los eventos de audio (`inicio`, `fragmento`, `fin`). Acepta
WAV, OGG/Opus y WebM (lo que graba `MediaRecorder` en el navegador); si el
contenedor no lo lee `soundfile`, se decodifica con `ffmpeg`. Este endpoint es
**solo para voz**; para preguntas escritas se usa `POST /v1/queries/`.

> [!NOTE]
> El detector de silencio del script es la referencia para el frontend: con
> `MediaRecorder` + Web Audio se detecta la pausa y se sube el audio al mismo
> endpoint. El streaming continuo por WebSocket/WebRTC queda como evolución
> posterior de RF12.

#### Descargar modelo de embeddings (multilingual-e5-small)

Modelo de embeddings multilingüe que Raguaco usa para vectorizar los fragmentos de los documentos (`passage`) y las preguntas del usuario (`query`); recupera resultados a través del método de similitud del coseno.

```
# Haber descargado previamente los requirements.txt
hf download intfloat/multilingual-e5-small --local-dir App/ai-models/multilingual-e5-small
```

Para ahorrar ~1.2 GB se pueden omitir las variantes que no se usan: la de OpenVINO, la copia de los pesos en formato PyTorch (`model.safetensors` ya es equivalente) y las variantes ONNX optimizadas/cuantizadas.

```
hf download intfloat/multilingual-e5-small --local-dir App/ai-models/multilingual-e5-small \
  --exclude "openvino/*" \
  --exclude "pytorch_model.bin" \
  --exclude ".eval_results/*" \
  --exclude "onnx/model_qint8_avx512_vnni.onnx" \
  --exclude "onnx/model_O4.onnx"
```

> [!NOTE]
> El comando anterior está escrito en varias líneas (bash). En Windows pega el equivalente en una sola línea, repitiendo `--exclude` por cada patrón.
>
> La variante `onnx/model_qint8_avx512_vnni.onnx` solo corre en CPU con AVX512-VNNI. Compruébalo con `grep -o avx512_vnni /proc/cpuinfo` antes de descargarla.

Comprobar que los pesos cargan y que la dimensión es 384:

```
cd App && python -c "import onnxruntime; s = onnxruntime.InferenceSession('ai-models/multilingual-e5-small/onnx/model.onnx'); print(s.get_outputs()[0].shape)"
# -> ['batch_size', 'sequence_length', 384]
```

`multilingual-e5-small` exige prefijos en el texto: `query: ` para las preguntas del usuario y `passage: ` para los fragmentos de los documentos. **Sin ellos la recuperación se degrada** aunque el modelo funcione.

Para vectorizar **no** hacen falta `sentence-transformers` ni PyTorch: la inferencia corre sobre `onnxruntime` (el mismo motor que ya usa el TTS) y la tokenización sobre `tokenizers` (~12 MB). Ambos están en `requirements.txt`.

La ruta se configura en `.env` y, como la aplicación se ejecuta con `App/` como raíz, es relativa:

```
EMBEDDING_MODEL=ai-models/multilingual-e5-small
EMBEDDING_DIMENSION=384
```
La dimensión 384 coincide con la columna `vector(384)` del schema de la base de datos.

#### Conectar modelo LLM

> [!NOTE]
> Actualmente el servicio LLM permite únicamente conexión a través de la API Key de OpenCode Go.

Para establecer la conexión con el modelo LLM basta con definir el endpoint del servicio, definir el tipo de modelo (DeepSeek, Qwen, Gemini, Claude, etc) y conectar el API Key.

El archivo `.env.example` indica cómo debe verse el archivo `.env` donde, en un apartado, se integran los datos mencionados:

```
LLM_BASE_URL=https://opencode.ai/zen/go/v1
LLM_MODEL=qwen3.8-flash
LLM_API_KEY=oc_sk_1...
``` 
 
### Docs iniciales
- [Requerimientos funcionales y no funcionales](Docs/Requerimientos/RF%20-%20RNF.md)
- [Diagramas UML](Docs/DIAGRAMS.md)

## Licencia

Distribuido bajo la licencia [MIT](LICENSE).

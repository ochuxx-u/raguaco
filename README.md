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
cd App && uvicorn main:app
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

#### Descargar modelo de STT (faster-whisper)

Modelo de transcripción de voz a texto (STT) que Raguaco usa para convertir la pregunta hablada del usuario en texto antes de consultar el RAG. Se ejecuta **en local**, sin API externa.

**1. Instalar las dependencias** (ya incluidas en `requirements.txt`: `faster-whisper`, `sounddevice`, `soundfile`):
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

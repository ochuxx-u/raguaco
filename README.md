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

### Descargar voz para el TTS (Kokoro)

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

### Descargar modelo de embeddings (multilingual-e5-small)

Modelo de embeddings multilingüe que Raguaco usa para vectorizar los fragmentos de los documentos (`passage`) y las preguntas del usuario (`query`).

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

### Docs iniciales
- [Requerimientos funcionales y no funcionales](Docs/Requerimientos/RF%20-%20RNF.md)
- [Diagramas UML](Docs/DIAGRAMS.md)

## Licencia

Distribuido bajo la licencia [MIT](LICENSE).

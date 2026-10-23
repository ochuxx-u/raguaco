"""
Prueba de TTS en español con Kokoro (ONNX).

No se usa misaki: misaki no tiene soporte de español (el extra `es` no existe).
La fonemización se hace con espeak-ng, que es lo que usa kokoro-onnx por debajo
(vía `kokoro_onnx.tokenizer.Tokenizer` con lang="es").
"""

from pathlib import Path

import numpy as np
import onnxruntime as rt
import soundfile as sf
from kokoro_onnx.tokenizer import Tokenizer

MODEL_DIR = Path(__file__).resolve().parents[1] / "ai-models" / "kokoro-82m"
MODEL_PATH = MODEL_DIR / "onnx" / "model.onnx"
VOICE_PATH = MODEL_DIR / "voices" / "ef_dora.bin"  # voz femenina española
LANG = "es"
OUTPUT = Path(__file__).with_name("salida.wav")

texto = "Bienvenidos a Raguaco, esta es la voz de nuestro proyecto."

# 1) Texto -> fonemas IPA (espeak-ng) y fonemas -> ids del modelo
tokenizer = Tokenizer()
fonemas = tokenizer.phonemize(texto, LANG)
tokens = tokenizer.tokenize(fonemas)

# 2) Vectores de estilo (uno por longitud de token) y selección por longitud
voices = np.fromfile(VOICE_PATH, dtype=np.float32).reshape(-1, 1, 256)
assert len(tokens) < len(voices), "texto demasiado largo para el vector de estilo"
ref_s = voices[len(tokens)]

# 3) Inferencia ONNX
sess = rt.InferenceSession(str(MODEL_PATH), providers=["CPUExecutionProvider"])
audio = sess.run(
    None,
    {
        "input_ids": [[0, *tokens, 0]],
        "style": ref_s,
        "speed": np.ones(1, dtype=np.float32),
    },
)[0]

samples = np.asarray(audio).reshape(-1)
sf.write(OUTPUT, samples, 24000)
print(f"OK -> {OUTPUT} ({len(samples) / 24000:.2f}s, 24000 Hz)")
print(f"fonemas: {fonemas}")

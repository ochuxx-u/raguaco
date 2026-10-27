"""
Prueba de TTS en español con Kokoro (ONNX).

No se usa misaki: misaki no tiene soporte de español (el extra `es` no existe).
La fonemización se hace con espeak-ng, que es lo que usa kokoro-onnx por debajo
(vía `kokoro_onnx.tokenizer.Tokenizer` con lang="es").

El modelo tiene un contexto de 512 tokens (510 fonemas + 2 de padding), así que
los textos largos se parten por frases en lotes de <=510 fonemas y el audio de
cada lote se concatena en un único WAV.
"""

import re
from pathlib import Path

import numpy as np
import onnxruntime as rt
import soundfile as sf
from kokoro_onnx.config import MAX_PHONEME_LENGTH
from kokoro_onnx.tokenizer import Tokenizer

MODEL_DIR = Path(__file__).resolve().parents[1] / "ai-models" / "kokoro-82m"
MODEL_PATH = MODEL_DIR / "onnx" / "model.onnx"
VOICE_PATH = MODEL_DIR / "voices" / "if_sara.bin"  # voz femenina española
LANG = "es"
OUTPUT = Path(__file__).with_name("salida.wav")

SAMPLE_RATE = 24000
PAUSA_SEGUNDOS = 0.25  # silencio entre lotes

texto = "Sí, el contexto lo considera una droga. En [1] se describe el alcohol como una molécula que \"entra de inmediato al sistema\" y luego se refiere a ella como \"la droga\". En [2] se clasifica explícitamente como \"droga legal\", junto con el tabaco. En [4] se menciona que el alcohol genera cambios en las funciones cerebrales y se incluye dentro del grupo de \"todas las drogas\" que afectan la motivación. En [5] aparece como palabra clave asociada a dependencia y adicciones."

# Las citas tipo "[1]" no deben leerse en voz alta: se eliminan antes de fonemizar.
texto = re.sub(r"\[\s*\d+\s*\]", "", texto)
texto = re.sub(r"\s{2,}", " ", texto)            # espacios dobles que deja el recorte
texto = re.sub(r"\s+([.,;:!?])", r"\1", texto)   # espacio suelto antes de puntuación
texto = texto.strip()


def trocear_frase(frase, tokenizer):
    """Fonemiza una frase y la parte por palabras si supera el límite."""
    fonemas = tokenizer.phonemize(frase, LANG)
    if not fonemas:
        return []
    if len(fonemas) <= MAX_PHONEME_LENGTH:
        return [fonemas]

    trozos, actual = [], ""
    for palabra in fonemas.split(" "):
        candidato = f"{actual} {palabra}".strip()
        if len(candidato) <= MAX_PHONEME_LENGTH:
            actual = candidato
        else:
            if actual:
                trozos.append(actual)
            actual = palabra[:MAX_PHONEME_LENGTH]
    if actual:
        trozos.append(actual)
    return trozos


def construir_lotes(texto, tokenizer):
    """Agrupa frases (ya troceadas) en lotes de <=MAX_PHONEME_LENGTH fonemas."""
    frases = [f for f in re.split(r"(?<=[.!?])\s+", texto) if f.strip()]
    trozos = []
    for frase in frases:
        trozos.extend(trocear_frase(frase, tokenizer))

    lotes, actual = [], ""
    for trozo in trozos:
        candidato = f"{actual} {trozo}".strip()
        if len(candidato) <= MAX_PHONEME_LENGTH:
            actual = candidato
        elif actual:
            lotes.append(actual)
            actual = trozo
        else:
            actual = trozo
    if actual:
        lotes.append(actual)
    return lotes


def sintetizar(fonemas, tokenizer, voices, sess):
    """Fonemas -> audio de un único lote."""
    tokens = tokenizer.tokenize(fonemas)
    ref_s = voices[min(len(tokens), len(voices) - 1)]
    audio = sess.run(
        None,
        {
            "input_ids": [[0, *tokens, 0]],
            "style": ref_s,
            "speed": np.ones(1, dtype=np.float32),
        },
    )[0]
    return np.asarray(audio).reshape(-1)


# 1) Texto -> fonemas IPA (espeak-ng), partido en lotes que el modelo acepta
tokenizer = Tokenizer()
lotes = construir_lotes(texto, tokenizer)

# 2) Vectores de estilo e inferencia ONNX, lote a lote
voices = np.fromfile(VOICE_PATH, dtype=np.float32).reshape(-1, 1, 256)
sess = rt.InferenceSession(str(MODEL_PATH), providers=["CPUExecutionProvider"])

pausa = np.zeros(int(SAMPLE_RATE * PAUSA_SEGUNDOS), dtype=np.float32)
partes = []
for i, lote in enumerate(lotes, start=1):
    audio = sintetizar(lote, tokenizer, voices, sess)
    if partes:
        partes.append(pausa)
    partes.append(audio)
    print(f"lote {i}/{len(lotes)}: {len(lote)} fonemas -> {len(audio) / SAMPLE_RATE:.2f}s")

# 3) Concatenar y guardar un único WAV
samples = np.concatenate(partes)
sf.write(OUTPUT, samples, SAMPLE_RATE)
print(f"OK -> {OUTPUT} ({len(samples) / SAMPLE_RATE:.2f}s, {SAMPLE_RATE} Hz)")
print(f"lotes: {len(lotes)} | fonemas totales: {sum(len(l) for l in lotes)}")

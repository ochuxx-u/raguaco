"""Prueba local del TTS en streaming: texto → WAV por frases → reproducción.

Uso (desde `App/`, con el venv activo):

    python tests_models/probar_tts_streaming.py
    python tests_models/probar_tts_streaming.py --sin-audio
    python tests_models/probar_tts_streaming.py --texto "Una prueba corta."

El texto de prueba está en la variable `TEXTO`: edítala para narrar lo que
quieras. El script mide la optimización real:

- **TTFA** (time to first audio): cuánto tarda el primer WAV en estar listo.
- **Síntesis total**: cuánto tarda el último fragmento.
- **Audio total** y **huecos**: si la síntesis se mantiene por delante de la
  reproducción, no hay silencios entre frases.

El producto del script son los `.wav` de
`App/storage/tts/{job_id}/`, servidos por la API en
`GET /v1/voice/tts/{job_id}/{indice}.wav`.
"""

import argparse
import asyncio
import queue
import sys
import threading
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

from domain.services.voice_service import VoiceService  # noqa: E402
from infrastructure.tts.kokoro_tts import KokoroTTS  # noqa: E402

# Texto crudo de prueba: tiene Markdown, citas [n], una URL y un emoji a
# propósito, para comprobar que se normalizan antes de narrar. Edítalo.
TEXTO = """
# Raguaco y la voz

**Raguaco** es un sistema RAG conversacional: permite subir documentos,
recuperar los fragmentos relevantes y responder en lenguaje natural con
fuentes verificables [1]. Cuando no encuentra evidencia suficiente, se niega
a inventar y lo dice explícitamente [2].

La interacción por voz añade dos caminos: dictar la pregunta y escuchar la
respuesta. Para que la respuesta empiece a sonar cuanto antes, el texto se
divide en frases y cada frase se sintetiza en un archivo WAV independiente.
Así, la primera frase se reproduce mientras el resto todavía se está
generando. Más información en https://raguaco.example.com/docs 👍

La optimización no cambia el contenido: cambia cuándo está disponible.
"""


def _reproducir(altavoz, ruta: Path) -> None:
    """Reproduce un WAV completo.

    SoundCard espera una matriz `frames x canales`; el WAV es mono, así que se
    replica en todos los canales del altavoz.
    """
    audio, sample_rate = sf.read(str(ruta), dtype='float32')
    canales = int(getattr(altavoz, 'channels', 1) or 1)
    datos = np.repeat(audio.reshape(-1, 1), canales, axis=1)
    altavoz.play(datos, samplerate=sample_rate)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--texto',
        default=None,
        help='Sustituye la variable TEXTO por este texto.',
    )
    parser.add_argument(
        '--sin-audio',
        action='store_true',
        help='Genera los WAV y mide tiempos, sin abrir el altavoz.',
    )
    args = parser.parse_args()
    texto = args.texto if args.texto is not None else TEXTO

    motor = KokoroTTS()
    if not motor.configured:
        print(
            'Falta el modelo TTS o la voz. Descárgalo según el README:\n'
            '  hf download onnx-community/Kokoro-82M-v1.0-ONNX '
            '--local-dir App/ai-models/kokoro-82m'
        )
        return 1

    print(f'Cargando Kokoro ({motor.voice}, {motor.sample_rate} Hz)...')
    t0 = time.perf_counter()
    if not motor.precargar():
        return 1
    print(f'Modelo cargado en {time.perf_counter() - t0:.2f} s\n')

    servicio = VoiceService(tts=motor)
    try:
        plan = servicio.preparar(texto)
    except Exception as exc:  # TTSError: texto vacío tras la limpieza
        print(f'No se pudo preparar el texto: {exc}')
        return 1

    print(f'Job: {plan.job_id}')
    print(f'Fragmentos: {len(plan.fragmentos)}')
    for indice, fragmento in enumerate(plan.fragmentos, start=1):
        print(f'  {indice:02d}. ({len(fragmento):3d} car.) {fragmento}')
    print()

    altavoz = None
    if not args.sin_audio:
        try:
            import soundcard as sc

            altavoz = sc.default_speaker()
            print(f'Altavoz: {altavoz.name}')
        except Exception as exc:  # sin servidor de audio / sin dispositivo
            print(f'No se pudo abrir el altavoz ({exc}); sigo sin reproducir.')
    if altavoz is None:
        print('Modo sin audio: solo se generan los WAV.\n')

    # El productor sintetiza y escribe WAV; el consumidor reproduce. El buffer
    # de 2 fragmentos permite que la síntesis del siguiente avance mientras
    # suena el actual, sin acumular toda la respuesta en memoria.
    cola: queue.Queue = queue.Queue(maxsize=2)
    inicio = time.perf_counter()

    def producir() -> None:
        async def generar() -> None:
            async for fragmento in servicio.sintetizar(plan):
                cola.put(fragmento)

        try:
            asyncio.run(generar())
        except Exception as exc:  # se reenvía al hilo principal
            cola.put(exc)
        finally:
            cola.put(None)

    hilo = threading.Thread(target=producir, name='tts-productor', daemon=True)
    hilo.start()

    primera_ms: int | None = None
    ultima_ms = 0
    duracion_total = 0.0
    reproduciendo_hasta = 0.0
    huecos: list[float] = []

    while True:
        elemento = cola.get()
        if elemento is None:
            break
        if isinstance(elemento, Exception):
            print(f'Error al sintetizar: {elemento}')
            return 1

        fragmento = elemento
        listo_sintesis = fragmento.ms_desde_inicio / 1000
        if primera_ms is None:
            primera_ms = fragmento.ms_desde_inicio
        ultima_ms = fragmento.ms_desde_inicio
        duracion_total += fragmento.duracion

        print(
            f'[{fragmento.indice + 1}/{len(plan.fragmentos)}] listo a '
            f'{listo_sintesis:.2f} s | '
            f'{fragmento.duracion:.2f} s de audio | '
            f'síntesis {fragmento.ms_sintesis} ms'
        )

        if altavoz is not None:
            # `listo_sintesis` y `reproduciendo_hasta` comparten el mismo
            # origen temporal (el inicio de `sintetizar`), así que la
            # comparación mide si el WAV llegó tarde respecto de la cola.
            if reproduciendo_hasta > 0 and listo_sintesis > reproduciendo_hasta:
                huecos.append(listo_sintesis - reproduciendo_hasta)
            ruta = servicio.ruta_fragmento(plan.job_id, fragmento.nombre)
            try:
                _reproducir(altavoz, ruta)
            except Exception as exc:  # dispositivo ocupado, sin servidor, etc.
                print(f'No se pudo reproducir el fragmento ({exc}); sigo sin audio.')
                altavoz = None
            reproduciendo_hasta = time.perf_counter() - inicio

    total_ms = int(round((time.perf_counter() - inicio) * 1000))
    print('\n--- Resumen ---')
    print(f'TTFA (primer WAV listo): {primera_ms / 1000:.2f} s')
    print(f'Último WAV listo:        {ultima_ms / 1000:.2f} s')
    print(f'Audio total:             {duracion_total:.2f} s')
    factor = (duracion_total / (ultima_ms / 1000)) if ultima_ms else 0.0
    if factor >= 1:
        print(f'La síntesis va {factor:.2f}x más rápido que la reproducción.')
    else:
        print(f'La síntesis va {1 / factor:.2f}x más lenta que la reproducción.')
    if primera_ms is not None and len(plan.fragmentos) > 1:
        print(
            f'El primer WAV llega {ultima_ms / primera_ms:.1f}x antes que el '
            'último: esa es la ventaja de empezar a hablar ya.'
        )
        print(
            f'La reproducción puede empezar {ultima_ms / 1000 - primera_ms / 1000:.2f} s '
            'antes de que termine la síntesis.'
        )
    elif len(plan.fragmentos) == 1:
        print('El texto cabe en un solo fragmento: no hay solapamiento que medir.')
    if altavoz is not None:
        if huecos:
            print(f'Cortes entre fragmentos: {len(huecos)} (máx. {max(huecos):.2f} s)')
        else:
            print('Reproducción continua: sin cortes entre fragmentos.')
    print(f'Tiempo total del script: {total_ms / 1000:.2f} s')
    print(f'WAV: {servicio.directorio / plan.job_id}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

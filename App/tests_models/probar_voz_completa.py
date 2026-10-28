"""Prueba de la secuencia completa de voz: hablar → STT → RAG → respuesta hablada.

Uso (con la API levantada en otra terminal):

    cd App && uvicorn main:app --reload

    # En otra terminal, con el venv activo:
    cd App
    python tests_models/probar_voz_completa.py

El script escucha el micrófono con `soundcard`, acumula audio y **cierra la
pregunta automáticamente** cuando detecta `VOICE_SILENCE_SECONDS` segundos de
silencio después de haber oído voz. Luego envía el WAV a
`POST /v1/voice/consultar`, imprime la transcripción y la respuesta con sus
fuentes, y reproduce los fragmentos TTS en cuanto llegan.

Opciones útiles:

    --sin-audio          no abre el altavoz (solo prueba STT → RAG)
    --archivo audio.wav  procesa un archivo en vez del micrófono
    --silencio 1.2       segundos de silencio que cierran la pregunta
    --conversacion-id    continúa una conversación existente
    --usuario-id         usuario de la consulta (por defecto, el usuario de
                         prueba con documentos reales)
"""

import argparse
import io
import json
import sys
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import httpx  # noqa: E402
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

from core.config import settings  # noqa: E402
from infrastructure.stt.vad import DetectorVoz  # noqa: E402

# Usuario de prueba con documentos reales en la base local (`alcohol.pdf`).
USUARIO_POR_DEFECTO = 'd18f3e28-0c98-4b29-96d6-89a04c7d716b'
API_POR_DEFECTO = 'http://127.0.0.1:8000'
SAMPLE_RATE = 16_000


def _wav_bytes(audio: np.ndarray) -> bytes:
    """Empaqueta el audio como WAV PCM 16 para enviarlo por multipart."""
    buffer = io.BytesIO()
    sf.write(buffer, audio, SAMPLE_RATE, format='WAV', subtype='PCM_16')
    return buffer.getvalue()


def _abrir_microfono():
    try:
        import soundcard as sc

        return sc.default_microphone()
    except Exception as exc:
        print(
            f'No pude abrir el micrófono ({exc}).\n'
            'Comprueba el dispositivo con: python -m soundcard',
            file=sys.stderr,
        )
        return None


def _abrir_altavoz():
    try:
        import soundcard as sc

        return sc.default_speaker()
    except Exception as exc:
        print(f'No pude abrir el altavoz ({exc}); sigo sin reproducir.')
        return None


def _reproducir(altavoz, audio: np.ndarray, sample_rate: int) -> None:
    """Reproduce un bloque mono, replicado en los canales del altavoz."""
    canales = int(getattr(altavoz, 'channels', 1) or 1)
    datos = np.repeat(np.asarray(audio, dtype=np.float32).reshape(-1, 1), canales, axis=1)
    altavoz.play(datos, samplerate=sample_rate)


def grabar_pregunta(
    microfono,
    silencio_segundos: float,
    espera_maxima: float,
    umbral: float,
    calibracion: float,
) -> np.ndarray:
    """Graba hasta detectar el silencio final; devuelve el audio de la pregunta.

    Antes de pedir la pregunta mide el ruido ambiental (si `calibracion` > 0) y
    eleva el umbral a `max(configurado, ruido_mediano * 1.5)`: así un ventilador
    o un micrófono con ganancia alta no impiden detectar el silencio.
    """
    from infrastructure.stt.vad import pico

    bloques = max(1, int(settings.voice_chunk_seconds * SAMPLE_RATE))
    paso = bloques / SAMPLE_RATE

    try:
        with microfono.recorder(samplerate=SAMPLE_RATE, channels=1) as grabador:
            umbral_efectivo = umbral
            if calibracion > 0:
                print(
                    f'   Calibrando ruido ambiental ({calibracion:.1f} s); '
                    'mantente en silencio…',
                    flush=True,
                )
                picos = []
                for _ in range(max(1, int(calibracion / paso))):
                    bloque = np.squeeze(grabador.record(numframes=bloques)).astype(np.float32)
                    picos.append(pico(bloque))
                # Percentil bajo: un golpe o una voz durante la calibración no
                # debe inflar el umbral de toda la pregunta.
                ruido = float(np.percentile(picos, 25)) if len(picos) > 1 else picos[0]
                umbral_efectivo = max(umbral, ruido * 1.5)
                print(
                    f'   Ruido de fondo (pico): {ruido:.4f} · '
                    f'umbral de voz: {umbral_efectivo:.4f}\n'
                )
                if ruido > 0.2:
                    print(
                        '   ⚠️  El ruido de fondo es alto; usa audífonos o '
                        'acerca el micrófono.\n'
                    )

            detector = DetectorVoz(
                silence_seconds=silencio_segundos,
                silence_peak=umbral_efectivo,
            )
            print('🎤 Habla ahora. La pregunta se enviará sola al dejar de hablar.')
            print(
                f'   Silencio de cierre: {silencio_segundos:.1f} s · '
                f'umbral de pico: {umbral_efectivo:.4f}\n'
            )

            inicio = time.perf_counter()
            hablado_avisado = False
            while True:
                datos = grabador.record(numframes=bloques)
                bloque = np.squeeze(datos).astype(np.float32)
                audio = detector.agregar(bloque)

                if detector.hablado and not hablado_avisado:
                    print('   · voz detectada…', flush=True)
                    hablado_avisado = True
                if audio is not None:
                    duracion = len(audio) / SAMPLE_RATE
                    print(f'   · fin de voz ({duracion:.1f} s de audio)\n')
                    return audio
                if time.perf_counter() - inicio > espera_maxima:
                    raise SystemExit(
                        f'No se cerró la pregunta en {espera_maxima:.0f} s. '
                        'Si hay ruido ambiente, sube --umbral '
                        f'({umbral_efectivo:.4f}) o revisa el micrófono.'
                    )
    except KeyboardInterrupt:
        raise SystemExit('\nCancelado.') from None


def _leer_archivo(path: str) -> np.ndarray:
    audio, samplerate = sf.read(path, dtype='float32', always_2d=True)
    audio = audio.mean(axis=1)
    if samplerate != SAMPLE_RATE:
        duracion = len(audio) / samplerate
        objetivo = int(duracion * SAMPLE_RATE)
        audio = np.interp(
            np.linspace(0.0, duracion, objetivo, endpoint=False),
            np.linspace(0.0, duracion, len(audio), endpoint=False),
            audio,
        ).astype(np.float32)
    return audio


def _guardar_wav(audio: np.ndarray, path: Path) -> None:
    """Guarda una copia de la pregunta (útil para depurar el STT)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio, SAMPLE_RATE, subtype='PCM_16')


def _procesar_stream(
    respuesta: httpx.Response,
    altavoz,
    *,
    sin_audio: bool,
    usuario_id: str,
    conversacion_id: str | None,
) -> int:
    """Lee el NDJSON de la API, imprime el resultado y reproduce los WAV."""
    procesando_desde = time.perf_counter()
    job_id: str | None = None
    total_fragmentos = 0
    conversacion_final = conversacion_id
    reproducidos = 0
    errores = 0

    for linea in respuesta.iter_lines():
        if not linea.strip():
            continue
        evento = json.loads(linea)
        tipo = evento.get('tipo')

        if tipo == 'procesando':
            print('⏳ Procesando audio (STT + RAG)…', flush=True)
        elif tipo == 'transcripcion':
            print(f'\n🗣️  Tú: {evento["texto"]}')
            if evento.get('ms_stt') is not None:
                print(f'   (STT: {evento["ms_stt"] / 1000:.2f} s)')
        elif tipo == 'respuesta':
            conversacion_final = evento.get('conversacion_id') or conversacion_final
            print(f'\n🤖 Raguaco: {evento["texto"]}\n')
            print(f'   Fuentes citadas: {len(evento.get("referencias", []))}')
            if evento.get('ms_rag') is not None:
                print(f'   (RAG: {evento["ms_rag"] / 1000:.2f} s)')
            if not sin_audio:
                print('   Reproduciendo respuesta…\n')
        elif tipo == 'inicio':
            job_id = evento.get('job_id')
            total_fragmentos = evento.get('total_fragmentos', 0)
        elif tipo == 'fragmento':
            reproducidos += 1
            duracion = float(evento.get('duracion', 0))
            print(
                f'   🔊 fragmento {evento["indice"] + 1}/{total_fragmentos} '
                f'({duracion:.2f} s, listo a {evento.get("ms_desde_inicio", 0) / 1000:.2f} s)'
            )
            if not sin_audio and altavoz is not None:
                url = evento['url']
                try:
                    wav = httpx.get(url, timeout=60.0)
                    wav.raise_for_status()
                    audio, sample_rate = sf.read(
                        io.BytesIO(wav.content), dtype='float32'
                    )
                    _reproducir(altavoz, audio, sample_rate)
                except Exception as exc:
                    print(f'   No se pudo reproducir el fragmento ({exc}).')
                    altavoz = None
        elif tipo == 'fin':
            conversacion_final = evento.get('conversacion_id') or conversacion_final
            print('\n--- Resumen ---')
            print(f'   Fragmentos de audio: {reproducidos}/{total_fragmentos}')
            print(f'   Audio generado: {evento.get("duracion_total", 0):.2f} s')
            for clave, etiqueta in (
                ('ms_stt', 'STT'),
                ('ms_rag', 'RAG'),
                ('ms_primera', 'primer audio'),
                ('ms_total', 'total voz'),
            ):
                valor = evento.get(clave)
                if valor is not None:
                    print(f'   {etiqueta}: {valor / 1000:.2f} s')
            print(f'   job_id: {job_id}')
        elif tipo == 'error':
            errores += 1
            print(f'\n❌ Error ({evento.get("codigo", "voz")}): {evento.get("detalle")}')
            break

    if conversacion_final:
        print(f'\nConversación: {conversacion_final}')
    print(f'Latencia total del script: {time.perf_counter() - procesando_desde:.2f} s')
    print(f'Usuario: {usuario_id}')
    return 1 if errores else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api', default=API_POR_DEFECTO, help='URL base de la API.')
    parser.add_argument(
        '--usuario-id',
        default=USUARIO_POR_DEFECTO,
        help='Usuario que hace la consulta (por defecto, el de los documentos de prueba).',
    )
    parser.add_argument(
        '--conversacion-id',
        default=None,
        help='Continúa una conversación existente en vez de crear una nueva.',
    )
    parser.add_argument(
        '--archivo',
        default=None,
        help='Procesa este archivo de audio en vez de escuchar el micrófono.',
    )
    parser.add_argument(
        '--sin-audio',
        action='store_true',
        help='No abre el altavoz; solo transcribe y consulta el RAG.',
    )
    parser.add_argument(
        '--silencio',
        type=float,
        default=settings.voice_silence_seconds,
        help='Segundos de silencio que cierran la pregunta.',
    )
    parser.add_argument(
        '--umbral',
        type=float,
        default=settings.voice_silence_peak,
        help='Umbral de pico mínimo de silencio; el script lo eleva con el ruido ambiente.',
    )
    parser.add_argument(
        '--calibracion',
        type=float,
        default=1.0,
        help='Segundos de ruido ambiental medidos antes de hablar (0 desactiva).',
    )
    parser.add_argument(
        '--espera-maxima',
        type=float,
        default=30.0,
        help='Segundos máximos esperando voz antes de rendirse.',
    )
    args = parser.parse_args()

    if args.archivo:
        try:
            audio = _leer_archivo(args.archivo)
        except Exception as exc:
            print(f'No pude leer {args.archivo}: {exc}', file=sys.stderr)
            return 1
        print(f'Archivo: {args.archivo} ({len(audio) / SAMPLE_RATE:.2f} s)\n')
    else:
        microfono = _abrir_microfono()
        if microfono is None:
            return 1
        try:
            audio = grabar_pregunta(
                microfono,
                args.silencio,
                args.espera_maxima,
                args.umbral,
                args.calibracion,
            )
        except SystemExit as exc:
            print(exc)
            return 1

    ruta_debug = APP_DIR / 'storage' / 'voz' / f'pregunta_{int(time.time())}.wav'
    _guardar_wav(audio, ruta_debug)
    print(f'Pregunta guardada en {ruta_debug}')

    altavoz = None if args.sin_audio else _abrir_altavoz()
    datos = {'usuario_id': args.usuario_id}
    if args.conversacion_id:
        datos['conversacion_id'] = args.conversacion_id

    try:
        with httpx.stream(
            'POST',
            f'{args.api.rstrip("/")}/v1/voice/consultar',
            data=datos,
            files={'audio': ('pregunta.wav', _wav_bytes(audio), 'audio/wav')},
            timeout=180.0,
        ) as respuesta:
            if respuesta.status_code != 200:
                print(
                    f'La API respondió {respuesta.status_code}: {respuesta.read().decode("utf-8", "replace")}',
                    file=sys.stderr,
                )
                return 1
            return _procesar_stream(
                respuesta,
                altavoz,
                sin_audio=args.sin_audio,
                usuario_id=args.usuario_id,
                conversacion_id=args.conversacion_id,
            )
    except httpx.ConnectError:
        print(
            f'No pude conectar con la API en {args.api}.\n'
            'Arranca el backend en otra terminal:\n'
            '  cd App && uvicorn main:app --reload',
            file=sys.stderr,
        )
        return 1
    except httpx.HTTPError as exc:
        print(f'Error de red con la API: {exc}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\nCancelado.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

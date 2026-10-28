"""Preparación del texto para el TTS: limpieza y segmentación por frases.

El objetivo es que la primera frase se pueda sintetizar (y reproducir) cuanto
antes, sin esperar a que se genere el audio de toda la respuesta. Por eso el
texto se limpia de marcas que no deben pronunciarse y se parte en fragmentos:

1. El **primer** fragmento se limita a `TTS_FIRST_CHUNK_CHARS` caracteres
   (una frase corta o una cláusula si la frase es muy larga). Es el que marca
   la latencia percibida por el usuario.
2. Los **siguientes** se agrupan hasta `TTS_CHUNK_CHARS` caracteres. El tope
   es deliberadamente moderado: cada WAV debe quedar listo antes de que el
   anterior termine de reproducirse; fragmentos demasiado grandes producen
   silencios entre frases.

`limpiar_para_voz` reutiliza `limpiar_markdown` (el chat muestra texto plano) y
después elimina lo que no aporta al oído: citas de fuentes `[n]`, emojis y
viñetas; las URLs se sustituyen por «el enlace» para no deletrearlas.
`segmentar_para_voz` trabaja sobre texto ya limpio.
"""

import re

from infrastructure.llm.plain_text import limpiar_markdown

# Citas de fuentes de la respuesta RAG: `[1]`, `[2]`, `[1, 3]`, `[4-6]`.
_RE_CITAS = re.compile(r'\[\s*\d+(?:\s*[,–-]\s*\d+)*\s*\]')

# URLs: se sustituyen por una expresión pronunciable (deletrear la URL no
# aporta nada al oyente).
_RE_URL = re.compile(r'(?:https?://|www\.)\S+', re.IGNORECASE)

# Separación de párrafos: el limpiador de Markdown conserva los saltos de
# línea. Un párrafo nuevo suele ser una idea nueva; si no trae puntuación, se
# le añade un punto para que la fonemización haga la pausa.
_RE_PARRAFO = re.compile(r'\n\s*\n+')

# Puntuación duplicada que puede dejar el reemplazo anterior (`fin..`).
_RE_PUNTUACION_DOBLE = re.compile(r'([.,;:!?…])\s*\.')

# Emojis y pictogramas: no tienen una lectura útil en español.
_RE_EMOJI = re.compile('[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]')

# Viñetas al inicio de línea (el limpiador de Markdown deja `-` y `•`).
_RE_VINETA = re.compile(r'(?m)^[ \t]*[-•·][ \t]+')

# Restos de énfasis que sobreviven al limpiador (p. ej. `** **`). Los
# asteriscos sueltos se conservan: en `2 * 3` son una multiplicación legible.
_RE_SIMBOLOS = re.compile(r'(?:\*{2,}|`{2,}|~{2,})')

# Espacios repetidos y espacio suelto antes de puntuación.
_RE_ESPACIOS = re.compile(r'\s+')
_RE_ESPACIO_PUNTUACION = re.compile(r'\s+([,.;:!?…])')

# Fin de frase: puntuación seguida de espacio y del inicio de otra frase.
# El lookahead evita cortar abreviaturas comunes (`p. ej.`, `Dr.`) cuando la
# siguiente palabra empieza en minúscula.
_RE_FIN_FRASE = re.compile(r'(?<=[.!?…])\s+(?=[¿¡"«“(\dA-ZÁÉÍÓÚÜÑ])')

# Fin de cláusula: se usa para partir una frase demasiado larga sin romper
# palabras y conservando una entonación razonable.
_RE_FIN_CLAUSULA = re.compile(r'(?<=[,;:])\s+')

# Un fragmento final más corto que esto se fusiona con el anterior si cabe.
MIN_FRAGMENTO = 30


def limpiar_para_voz(texto: str) -> str:
    """Devuelve el texto listo para pronunciar, sin marcas ni ruido visual.

    No cambia el contenido semántico: quita la notación Markdown, las citas,
    los emojis y las viñetas, sustituye las URLs por «el enlace» y normaliza
    los espacios.
    """
    limpio = limpiar_markdown(texto or '')
    limpio = _RE_PARRAFO.sub('. ', limpio)
    limpio = _RE_PUNTUACION_DOBLE.sub(r'\1', limpio)
    limpio = _RE_VINETA.sub('', limpio)
    limpio = _RE_CITAS.sub('', limpio)
    limpio = _RE_URL.sub('el enlace', limpio)
    limpio = _RE_EMOJI.sub('', limpio)
    limpio = _RE_SIMBOLOS.sub('', limpio)
    limpio = _RE_ESPACIO_PUNTUACION.sub(r'\1', limpio)
    limpio = _RE_ESPACIOS.sub(' ', limpio)
    limpio = limpio.strip()
    # Si solo quedaron signos (p. ej. `*`), no hay nada que pronunciar.
    if not any(caracter.isalnum() for caracter in limpio):
        return ''
    return limpio


def _dividir_en_frases(texto: str) -> list[str]:
    """Parte por fin de frase conservando la puntuación de cierre."""
    return [frase.strip() for frase in _RE_FIN_FRASE.split(texto) if frase.strip()]


def _partir_por_palabras(texto: str, limite: int) -> list[str]:
    """Parte `texto` en trozos de hasta `limite` caracteres sin cortar palabras.

    Una palabra aislada más larga que el límite se corta a la fuerza: es la
    única forma de respetar el tope (caso patológico, p. ej. una URL pegada).
    """
    limite = max(1, limite)
    piezas: list[str] = []
    actual = ''
    for palabra in texto.split():
        candidato = f'{actual} {palabra}'.strip()
        if len(candidato) <= limite:
            actual = candidato
            continue
        if actual:
            piezas.append(actual)
        while len(palabra) > limite:
            piezas.append(palabra[:limite])
            palabra = palabra[limite:]
        actual = palabra
    if actual:
        piezas.append(actual)
    return piezas


def _partir_por_limite(texto: str, limite: int) -> list[str]:
    """Parte una frase en piezas de hasta `limite` caracteres.

    Primero intenta cortar por cláusulas (coma, punto y coma, dos puntos) para
    conservar pausas naturales; si una cláusula sigue siendo larga, cae a
    palabras.
    """
    texto = texto.strip()
    if not texto:
        return []
    if len(texto) <= limite:
        return [texto]

    clausulas = [parte.strip() for parte in _RE_FIN_CLAUSULA.split(texto) if parte.strip()]
    if len(clausulas) == 1:
        return _partir_por_palabras(texto, limite)

    piezas: list[str] = []
    actual = ''
    for clausula in clausulas:
        candidato = f'{actual} {clausula}'.strip()
        if len(candidato) <= limite:
            actual = candidato
            continue

        # Una cláusula corta ("Además,") no debe quedar sola: se une al
        # principio de la siguiente y se reparte por palabras.
        if actual and len(actual) < MIN_FRAGMENTO:
            piezas.extend(_partir_por_palabras(candidato, limite))
            actual = ''
            continue

        if actual:
            piezas.append(actual)
        if len(clausula) <= limite:
            actual = clausula
        else:
            piezas.extend(_partir_por_palabras(clausula, limite))
            actual = ''
    if actual:
        piezas.append(actual)

    if (
        len(piezas) > 1
        and len(piezas[-1]) < MIN_FRAGMENTO
        and len(piezas[-2]) + 1 + len(piezas[-1]) <= limite
    ):
        piezas[-2] = f'{piezas[-2]} {piezas[-1]}'
        piezas.pop()
    return piezas


def segmentar_para_voz(
    texto: str,
    *,
    primer_max: int = 100,
    resto_max: int = 120,
) -> list[str]:
    """Parte `texto` (ya limpio) en fragmentos listos para sintetizar.

    El primer fragmento busca la menor latencia posible; los demás agrupan
    frases hasta `resto_max` para reducir el número de inferencias. Todas las
    piezas quedan por debajo de su límite salvo una palabra aislada
    patológicamente larga, que se corta a la fuerza.
    """
    limite_resto = max(1, resto_max)
    limite_primero = min(max(1, primer_max), limite_resto)

    # Unidades atómicas: frases ya partidas para que quepan en el límite mayor.
    unidades: list[str] = []
    for frase in _dividir_en_frases(texto):
        unidades.extend(_partir_por_limite(frase, limite_resto))
    if not unidades:
        return []

    fragmentos: list[str] = []

    # Primer fragmento: lo más corto posible para empezar a hablar ya.
    primera = unidades.pop(0)
    if len(primera) > limite_primero:
        partes = _partir_por_limite(primera, limite_primero)
        fragmentos.append(partes.pop(0))
        unidades[:0] = partes
    else:
        actual = primera
        while unidades and len(f'{actual} {unidades[0]}') <= limite_primero:
            actual = f'{actual} {unidades.pop(0)}'
        fragmentos.append(actual)

    # Resto: agrupar hasta el límite mayor.
    actual = ''
    for unidad in unidades:
        candidato = f'{actual} {unidad}'.strip()
        if len(candidato) <= limite_resto:
            actual = candidato
        else:
            if actual:
                fragmentos.append(actual)
            actual = unidad
    if actual:
        fragmentos.append(actual)

    # Evita un último fragmento de una o dos palabras que suene entrecortado.
    if (
        len(fragmentos) > 1
        and len(fragmentos[-1]) < MIN_FRAGMENTO
        and len(fragmentos[-2]) + 1 + len(fragmentos[-1]) <= limite_resto
    ):
        fragmentos[-2] = f'{fragmentos[-2]} {fragmentos[-1]}'
        fragmentos.pop()

    return fragmentos

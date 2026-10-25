"""Limpieza del texto extraído antes de fragmentarlo.

El objetivo es normalizar el ruido de la extracción (codificación, retornos de
carro, caracteres de control, espacios repetidos) **sin tocar la estructura**:
se conservan deliberadamente los saltos de línea `'\\n'` y el marcador de
página form-feed `'\\f'` que deja `DocumentLoader` entre páginas de un PDF.
`ChunkingService` los necesita para repartir párrafos y poblar
`Fragmento.pagina`; por eso el recorte de bordes ignora `'\\f'` (que para
Python es un espacio en blanco y un `.strip()` a secas lo eliminaría).
"""

import re
import unicodedata

# Caracteres de control a eliminar. Ojo: `'\f'` (form feed) ES `\x0c` y debe
# sobrevivir, por eso `\x0c` no está en la clase; `'\n'` (`\x0a`) tampoco.
_CONTROL = re.compile(r'[\x00-\x08\x0b\x0e-\x1f\x7f]')

# Espacios y tabulaciones horizontales repetidos (no cruzan el final de línea).
_HORIZONTALES = re.compile(r'[ \t]+')

# Tres o más saltos de línea seguidos equivalen a una sola línea en blanco.
_SALTOS_LARGOS = re.compile(r'\n{3,}')


def _recortar(texto: str) -> str:
    """Quita espacios al inicio y al final, pero nunca el marcador `'\\f'`."""
    inicio, fin = 0, len(texto)
    while inicio < fin and texto[inicio].isspace() and texto[inicio] != '\f':
        inicio += 1
    while fin > inicio and texto[fin - 1].isspace() and texto[fin - 1] != '\f':
        fin -= 1
    return texto[inicio:fin]


class TextCleaner:
    """Normaliza el texto extraído sin perder saltos de línea ni páginas."""

    def limpiar(self, texto: str) -> str:
        """Devuelve `texto` normalizado y sin ruido de extracción.

        Pasos: normalización Unicode NFC; `'\r\n'`/`'\r'` → `'\n'`; eliminación
        de caracteres de control salvo `'\\n'` y `'\\f'`; colapso de espacios y
        tabulaciones repetidos en un espacio por línea; recorte de bordes de
        cada línea; colapso de tres o más saltos de línea en dos; recorte final.
        Los recortes conservan el marcador de página `'\\f'` a propósito.
        """
        texto = unicodedata.normalize('NFC', texto)
        texto = texto.replace('\r\n', '\n').replace('\r', '\n')
        texto = _CONTROL.sub('', texto)
        texto = _HORIZONTALES.sub(' ', texto)
        texto = '\n'.join(_recortar(linea) for linea in texto.split('\n'))
        texto = _SALTOS_LARGOS.sub('\n\n', texto)
        return _recortar(texto)

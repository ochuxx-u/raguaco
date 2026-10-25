"""Fragmentación del texto limpio en `Fragmento`, listos para indexar.

Estrategia de empaquetado:

1. **Paginación**: si el texto contiene el marcador form-feed `'\f'` que deja
   `DocumentLoader` entre páginas de un PDF, se parte por él y cada fragmento
   hereda el número de página (1-based). Sin marcador, `pagina` queda `None`
   (formatos sin paginación: txt, md, docx).
2. Dentro de cada página se separan los **párrafos** por líneas en blanco
   (`\\n\\s*\\n`).
3. Los párrafos consecutivos se **empaquetan** en un fragmento mientras quepan
   en `max_chars` (unidos por `'\n\n'`). Un párrafo más grande se parte primero
   en oraciones (por `'. '`, conservando el punto) y, si una oración sigue
   siendo más larga que `max_chars`, se corta en duro en `max_chars`.
4. Se descartan los fragmentos vacíos o solo espacios.
5. `indice` es el orden global 0-based de los fragmentos resultantes y continúa
   entre páginas.
"""

import re
from typing import Any

from pydantic import Field

from domain.models.base import ModeloBase

# Párrafos separados por una o más líneas en blanco.
_PARrafOS = re.compile(r'\n\s*\n')

# Frontera de oración: justo después de un punto seguido de espacio.
_ORACIONES = re.compile(r'(?<=\. )')


class Fragmento(ModeloBase):
    """Trozo de texto de un documento, con su posición en el original."""

    contenido: str = Field(min_length=1, description='Texto limpio del fragmento')
    indice: int = Field(ge=0, description='Posición del fragmento dentro del documento')
    pagina: int | None = Field(
        default=None,
        ge=1,
        description='Página del documento original; `None` en formatos sin paginación',
    )
    metadatos: dict[str, Any] = Field(
        default_factory=dict,
        description='Metadatos libres del fragmento',
    )


class ChunkingService:
    """Parte el texto limpio en fragmentos de a lo sumo `max_chars` caracteres."""

    def __init__(self, max_chars: int = 1000) -> None:
        if max_chars < 1:
            raise ValueError('max_chars debe ser al menos 1')
        self._max_chars = max_chars

    def fragmentar(self, texto: str) -> list[Fragmento]:
        """Divide `texto` en fragmentos ordenados y numerados.

        Reparto de `pagina`: si `texto` trae el marcador `'\f'` entre páginas de
        un PDF, cada fragmento hereda el número de su página (1-based, contado
        sobre el resultado de partir por `'\f'`); en textos sin marcador,
        `pagina` es `None`. `indice` es global y 0-based, y sigue contando entre
        páginas. Si no queda ningún fragmento se lanza `ValueError`.
        """
        if '\f' in texto:
            paginas: list[tuple[int | None, str]] = list(
                enumerate(texto.split('\f'), start=1)
            )
        else:
            paginas = [(None, texto)]

        fragmentos: list[Fragmento] = []
        for numero, pagina in paginas:
            for contenido in self._empaquetar_pagina(pagina):
                fragmentos.append(
                    Fragmento(contenido=contenido, indice=len(fragmentos), pagina=numero)
                )

        if not fragmentos:
            raise ValueError('El documento no contiene texto procesable')
        return fragmentos

    def _empaquetar_pagina(self, pagina: str) -> list[str]:
        """Une párrafos consecutivos mientras quepan en `max_chars`."""
        paquetes: list[str] = []
        actual = ''
        for pieza, separador in self._unidades_de_pagina(pagina):
            if not actual:
                actual = pieza
            elif len(actual) + len(separador) + len(pieza) <= self._max_chars:
                actual += separador + pieza
            else:
                paquetes.append(actual)
                actual = pieza
        if actual:
            paquetes.append(actual)
        return [paquete for paquete in paquetes if paquete.strip()]

    def _unidades_de_pagina(self, pagina: str) -> list[tuple[str, str]]:
        """Trozos de la página de a lo sumo `max_chars`, con su separador previo.

        Cada elemento es `(pieza, separador)`, donde `separador` es lo que hay
        que anteponer a `pieza` para reconstruir el texto: `'\\n\\n'` entre
        párrafos, un espacio entre las oraciones de un párrafo partido y nada
        al inicio de la página.
        """
        unidades: list[tuple[str, str]] = []
        parrafos = [parrafo.strip() for parrafo in _PARrafOS.split(pagina)]
        for parrafo in parrafos:
            if not parrafo:
                continue
            piezas = self._partir_parrafo(parrafo)
            for posicion, pieza in enumerate(piezas):
                separador = '' if not unidades else ('\n\n' if posicion == 0 else ' ')
                unidades.append((pieza, separador))
        return unidades

    def _partir_parrafo(self, parrafo: str) -> list[str]:
        """Parte un párrafo demasiado largo: primero en oraciones, luego en duro."""
        if len(parrafo) <= self._max_chars:
            return [parrafo]
        oraciones = [oracion.strip() for oracion in _ORACIONES.split(parrafo)]
        piezas: list[str] = []
        actual = ''
        for oracion in oraciones:
            if not oracion:
                continue
            for trozo in self._cortar_largo(oracion):
                if not actual:
                    actual = trozo
                elif len(actual) + 1 + len(trozo) <= self._max_chars:
                    actual = f'{actual} {trozo}'
                else:
                    piezas.append(actual)
                    actual = trozo
        if actual:
            piezas.append(actual)
        return piezas

    def _cortar_largo(self, texto: str) -> list[str]:
        """Corte duro en `max_chars` para oraciones aún demasiado largas."""
        if len(texto) <= self._max_chars:
            return [texto]
        return [
            texto[inicio:inicio + self._max_chars]
            for inicio in range(0, len(texto), self._max_chars)
        ]

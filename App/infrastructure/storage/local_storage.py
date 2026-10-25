"""Almacenamiento local de los archivos originales subidos.

`StorageService` guarda una **copia** del documento subido dentro del
directorio `STORAGE_DIR` (relativo a `App/` o absoluto, igual que las rutas de
`EmbeddingService`) bajo una ruta única `{uuid4().hex}/{nombre_saneado}`: el
subdirectorio por identificador evita colisiones y conserva intacto el nombre
original (que `Documento` deriva de la ruta); el saneado (`[A-Za-z0-9._-]`, el
resto a `_`) desactiva nombres hostiles con barras o espacios. El original del usuario
nunca se mueve ni se borra: `guardar_original` copia con `shutil.copy2` (o
escribe por trozos si recibe un binario) y `eliminar_original` borra solo la
copia del almacén, la que señala `Documento.ruta_original`.
"""

import re
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from core.config import settings

# Tamaño de lectura al copiar un binario por trozos (1 MiB).
_TROZO = 1024 * 1024

# Todo lo que no sea `[A-Za-z0-9._-]` pasa a `_` en el nombre de destino.
_NO_SANO = re.compile(r'[^A-Za-z0-9._-]')
_GUIONES_BAJOS = re.compile(r'_+')


class StorageService:
    """Guarda y borra copias de los documentos originales en disco."""

    def __init__(self, directorio: str | Path | None = None) -> None:
        # `App/` es la raíz de ejecución; anclar contra el paquete resuelve las
        # rutas relativas igual que `EmbeddingService`, sin depender del cwd.
        self._app_dir = Path(__file__).resolve().parents[2]
        crudo = str(directorio if directorio is not None else settings.storage_dir).strip()
        self._dir = self._resolver(crudo)

    def _resolver(self, ruta: str | Path | None) -> Path:
        crudo = str(ruta or '').strip()
        if not crudo:
            return self._app_dir
        camino = Path(crudo).expanduser()
        return camino if camino.is_absolute() else self._app_dir / camino

    def guardar_original(
        self, archivo: str | Path | BinaryIO, nombre: str | None = None
    ) -> str:
        """Guarda una copia de `archivo` en el almacén y devuelve su ruta absoluta.

        `archivo` puede ser una ruta (se copia con `shutil.copy2`; el original
        del usuario se queda donde está) o un objeto binario con `.read()` (se
        escribe por trozos; el nombre base sale de `nombre` o de su atributo
        `name`). El destino es `{uuid4().hex}/{nombre_saneado}` dentro del
        directorio de almacenamiento, que se crea si no existe.
        """
        directorio = self._dir

        if isinstance(archivo, (str, Path)):
            origen = Path(archivo)
            if not origen.is_file():
                raise FileNotFoundError(f'No encuentro el archivo: {origen}')
            base = nombre if nombre else origen.name
            destino = self._ruta_destino(directorio, base)
            shutil.copy2(origen, destino)
            return str(destino.resolve())

        if hasattr(archivo, 'read'):
            base = nombre if nombre else getattr(archivo, 'name', None)
            if not base:
                raise ValueError(
                    'No puedo deducir el nombre del archivo: pasa `nombre` '
                    'o usa un objeto con atributo `name`.'
                )
            destino = self._ruta_destino(directorio, base)
            with open(destino, 'wb') as salida:
                while True:
                    trozo = archivo.read(_TROZO)
                    if not trozo:
                        break
                    if isinstance(trozo, str):
                        raise ValueError(
                            'El archivo llegó como texto; se espera un flujo binario.'
                        )
                    salida.write(trozo)
            return str(destino.resolve())

        raise TypeError(
            'archivo debe ser una ruta (str | Path) o un flujo binario con .read().'
        )

    def eliminar_original(self, ruta: str | Path) -> bool:
        """Borra una copia del almacén. `True` si la borró, `False` si no existía.

        Una ruta relativa se resuelve dentro del directorio de almacenamiento;
        la ruta absoluta que devolvió `guardar_original` se usa tal cual.
        """
        camino = Path(ruta).expanduser()
        if not camino.is_absolute():
            camino = self._dir / camino
        if not camino.is_file():
            return False
        camino.unlink()
        # El subdirectorio `{uuid4().hex}` queda vacío: se retira con la copia.
        padre = camino.parent
        if padre != self._dir:
            try:
                padre.rmdir()
            except OSError:  # quedan más copias: se borrará con la última
                pass
        return True

    @staticmethod
    def _ruta_destino(directorio: Path, base: str | Path) -> Path:
        """Ruta destino `{uuid4().hex}/{nombre_saneado}`, única y sin hostilidad.

        El nombre original se conserva (solo saneado) dentro de un
        subdirectorio con el identificador: así `Documento.nombre`, que se
        deriva de la ruta, sigue siendo el nombre del archivo del usuario.
        """
        solo_nombre = Path(str(base)).name
        sano = _NO_SANO.sub('_', solo_nombre)
        sano = _GUIONES_BAJOS.sub('_', sano)
        destino = directorio / uuid.uuid4().hex / sano
        destino.parent.mkdir(parents=True, exist_ok=True)
        return destino

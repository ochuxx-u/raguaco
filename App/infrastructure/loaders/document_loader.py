"""Carga de documentos: extrae el texto de pdf, docx, txt y md.

Formatos soportados (por extensión, en minúsculas):

- `.txt`, `.md`: texto plano; se lee como UTF-8 y, si la decodificación falla,
  se reintenta con latin-1 para no perder el documento por un carácter suelto.
- `.pdf`: texto extraído página por página y unido con el carácter form-feed
  `'\f'`. Ese marcador de paginación lo consume `ChunkingService` para poblar
  `Fragmento.pagina`; es la única fuente de número de página del pipeline.
- `.docx`: párrafos de Word unidos con `'\n'`. Word no expone paginación, así
  que el texto no lleva `'\f'` y los fragmentos quedan con `pagina=None`.

Los imports de `pypdf` y `python-docx` son perezosos (dentro del método, el
mismo patrón que `infrastructure/embeddings/embedding_service.py`): la
aplicación arranca aunque falte alguna de las dependencias (RNF6) y el error
solo aparece al procesar el formato correspondiente.
"""

from pathlib import Path

# Extensiones admitidas, en minúsculas y con el punto.
FORMATOS_SOPORTADOS = ('.pdf', '.docx', '.txt', '.md')


class DocumentLoader:
    """Extrae texto plano de un documento subido, según su extensión."""

    def extraer_texto(self, archivo: str | Path) -> str:
        """Devuelve el texto del archivo `archivo` (ruta a un documento).

        Según la extensión: `.txt`/`.md` se leen como texto, `.pdf` se extrae
        página por página uniendo las páginas con `'\f'` y `.docx` une los
        párrafos con `'\\n'`. Cualquier otra extensión, un archivo inexistente o
        un documento sin texto extraíble terminan en un error con mensaje claro.
        """
        ruta = Path(archivo)
        if not ruta.is_file():
            raise FileNotFoundError(f'No encuentro el archivo: {ruta}')

        extension = ruta.suffix.lower()
        if extension in ('.txt', '.md'):
            texto = self._leer_texto(ruta)
        elif extension == '.pdf':
            texto = self._leer_pdf(ruta)
        elif extension == '.docx':
            texto = self._leer_docx(ruta)
        else:
            raise ValueError(
                f'Formato no soportado: {extension or "(sin extensión)"} '
                '(se admite pdf, docx, txt, md)'
            )

        if not texto.strip():
            raise ValueError('El documento no contiene texto extraíble')
        return texto

    @staticmethod
    def _leer_texto(ruta: Path) -> str:
        """Lee texto plano: UTF-8 y, si falla, latin-1 (nunca pierde bytes)."""
        try:
            return ruta.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            return ruta.read_text(encoding='latin-1')

    @staticmethod
    def _leer_pdf(ruta: Path) -> str:
        """Extrae el texto de cada página del PDF, unidas con `'\f'`."""
        # Import perezoso: la app arranca aunque no esté instalado pypdf (RNF6).
        from pypdf import PdfReader

        lector = PdfReader(str(ruta))
        paginas = [(pagina.extract_text() or '') for pagina in lector.pages]
        return '\f'.join(paginas)

    @staticmethod
    def _leer_docx(ruta: Path) -> str:
        """Extrae los párrafos de Word, unidos con `'\\n'` (sin paginación)."""
        # Import perezoso: la app arranca aunque no esté instalado python-docx.
        import docx

        documento = docx.Document(str(ruta))
        return '\n'.join(parrafo.text for parrafo in documento.paragraphs)

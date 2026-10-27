"""Conversión de las respuestas Markdown del LLM a texto plano.

El chat del frontend pinta `Mensaje.contenido` como texto plano
(`white-space: pre-wrap` en `MessageBubble.css`, sin renderizador de Markdown),
así que la notación que devuelve el modelo (`**negrita**`, `# título`,
`` `código` ``, `[texto](url)`, viñetas con `*`…) se vería literal en la
respuesta. Este módulo conserva el texto dictado y elimina **solo** el marcado.

Lo que se transforma:

- vallas de bloque de código (` ``` `) y comillas invertidas de código en línea;
- encabezados (`#`, `##`…) y citas (`>`);
- énfasis (`**`, `*`, `__`, `_`) y tachado (`~~`);
- enlaces e imágenes (`[texto](url)`, `![alt](url)`) → se quedan con el texto;
- reglas horizontales (`---`, `***`, `___`) y separadores de tabla;
- viñetas `*` / `+` → `-` (misma marca, sin notación) y listas numeradas sin
  cambios, porque ya son texto legible;
- escapes (`\\*`, `\\_`…) → el carácter literal.

Las citas `[n]` de las fuentes (RF8) **no se tocan**: son las que relacionan el
texto de la respuesta con `RespuestaRAG.referencias`. Por eso el reemplazo de
enlaces exige paréntesis justo después del corchete y `[1]` nunca los lleva.
"""

import re

# Caracteres que Markdown permite escapar con barra invertida (CommonMark).
_ESCAPES = re.compile(r'\\([\\`*_{}\[\]()#+\-.!>~|])')

# Imágenes `![alt](url)`: para texto plano no aportan y el cliente no las pinta.
_IMAGENES = re.compile(r'!\[([^\]]*)\]\([^)]*\)')

# Enlaces `[texto](url)` (y `[texto][ref]`): se conserva el texto, se quita la URL.
_ENLACES = re.compile(r'\[([^\]\n]+)\]\((?:[^)\s]*)\)|\[([^\]\n]+)\]\[[^\]\n]*\]')

# Encabezados `#`…`######` al inicio de línea y sus cierres opcionales al final.
_ENCABEZADOS = re.compile(r'^[ \t]{0,3}#{1,6}[ \t]*(.*?)[ \t]*#*[ \t]*$', re.MULTILINE)

# Marcas de cita `>` al inicio de línea (anidadas: se aplican todas).
_CITAS = re.compile(r'^[ \t]*(?:>[ \t]?)+', re.MULTILINE)

# Regla horizontal: tres o más `-`, `*` o `_` (iguales) solos en la línea.
_REGLA_HORIZONTAL = re.compile(r'^[ \t]*([-*_])[ \t]*(?:\1[ \t]*){2,}$', re.MULTILINE)

# Fila separadora de tabla (`|---|---|:--:|`), que no aporta nada como texto.
_SEPARADOR_TABLA = re.compile(
    r'^[ \t]*\|?[ \t]*:?-{3,}:?[ \t]*(?:\|[ \t]*:?-{3,}:?[ \t]*)+\|?[ \t]*$',
    re.MULTILINE,
)

# Vallas de bloque de código: se eliminan las líneas que solo las abren o cierran.
_VALLAS = re.compile(r'^[ \t]*(?:```|~~~)[^\n]*$', re.MULTILINE)

# Código en línea: `` `x` `` o ```` ``x`` ```` → `x`.
_CODIGO_EN_LINEA = re.compile(r'(`+)(?!`)(.+?)(?<!`)\1(?!`)', re.DOTALL)

# Viñetas `-`, `*`, `+` → `-`: la marca se conserva, la notación no.
_VINETAS = re.compile(r'^([ \t]*)[*+][ \t]+', re.MULTILINE)

# Énfasis y tachado. Los `*` exigen texto pegado a la marca para no comerse
# productos tipo `2 * 3 * 4`; los `_` exigen además no estar dentro de una
# palabra, así que identificadores como `usuario_id` sobreviven.
_NEGRITA_ASTERISCO = re.compile(r'\*\*(?!\s)(.+?)(?<!\s)\*\*', re.DOTALL)
_CURSIVA_ASTERISCO = re.compile(r'\*(?![\s*])(.+?)(?<![\s*])\*')
_NEGRITA_GUIONES = re.compile(r'__(?!\s)(.+?)(?<!\s)__', re.DOTALL)
_CURSIVA_GUIONES = re.compile(r'(?<![\w_])_(?![\s_])(.+?)(?<![\s_])_(?![\w_])')
_TACHADO = re.compile(r'~~(?!\s)(.+?)(?<!\s)~~')

# Líneas vacías repetidas: dos saltos bastan para separar párrafos.
_SALTOS_LARGOS = re.compile(r'\n{3,}')


def _reemplazar_enlace(coincidencia: re.Match[str]) -> str:
    """Devuelve el texto visible del enlace, sin corchetes ni URL."""
    return coincidencia.group(1) or coincidencia.group(2) or ''


def limpiar_markdown(texto: str) -> str:
    """Devuelve `texto` como texto plano legible, sin notación Markdown.

    Conserva el contenido y los saltos de línea (el frontend los respeta con
    `pre-wrap`) y las citas `[n]` (RF8). Es idempotente: aplicar la limpieza a
    una respuesta ya limpia no cambia nada.
    """
    texto = texto.replace('\r\n', '\n').replace('\r', '\n')
    texto = _ESCAPES.sub(r'\1', texto)
    texto = _VALLAS.sub('', texto)
    texto = _SEPARADOR_TABLA.sub('', texto)
    texto = _REGLA_HORIZONTAL.sub('', texto)
    texto = _IMAGENES.sub(r'\1', texto)
    texto = _ENLACES.sub(_reemplazar_enlace, texto)
    texto = _ENCABEZADOS.sub(r'\1', texto)
    texto = _CITAS.sub('', texto)
    texto = _VINETAS.sub(r'\1- ', texto)
    texto = _CODIGO_EN_LINEA.sub(r'\2', texto)
    texto = _NEGRITA_ASTERISCO.sub(r'\1', texto)
    texto = _CURSIVA_ASTERISCO.sub(r'\1', texto)
    texto = _NEGRITA_GUIONES.sub(r'\1', texto)
    texto = _CURSIVA_GUIONES.sub(r'\1', texto)
    texto = _TACHADO.sub(r'\1', texto)
    # Los recortes de bordes por línea evitan espacios huérfanos al quitar marcas.
    texto = '\n'.join(linea.rstrip() for linea in texto.split('\n'))
    texto = _SALTOS_LARGOS.sub('\n\n', texto)
    return texto.strip()

"""Rutas de documentos.

Conectan la API con la entidad de dominio `Documento`
(`domain/models/documento.py`) y con la tabla `documento` de PostgreSQL a
través de `DocumentoRepository`. El cliente puede indicar la ruta de un
archivo ya presente en el servidor (`POST /`) o subir el archivo desde el
navegador (`POST /upload`); el servidor reconoce el nombre y el formato, y
asigna los datos que le corresponden (`id`, `fecha_carga`, `estado`). El
registro dispara el pipeline de ingesta (`DocumentIngestionService`, RF2), de
modo que `POST` devuelve el documento ya procesado (fragmentos y embeddings
guardados). La `categoria` es opcional y solo se toma del cliente.
"""

import os
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    File,
    Form,
    HTTPException,
    Path,
    Query,
    Response,
    UploadFile,
    status,
)
from psycopg.errors import ForeignKeyViolation

from api.deps import DocumentIngestionServiceDep, DocumentoRepositoryDep, StorageServiceDep
from domain.models.documento import Documento

router = APIRouter(prefix='/v1/models/documents', tags=['documents'])

# Formatos que acepta la subida desde el navegador (la carga por ruta admite
# también Markdown, pero la UI de Documentos solo ofrece PDF, DOCX y TXT).
ALLOWED_UPLOAD_EXTENSIONS = {'.pdf', '.docx', '.txt'}


@router.get(
    '/',
    response_model=list[Documento],
    summary='Listar documentos',
    description='Devuelve los documentos registrados, de la más reciente a la más antigua.',
)
async def list_documents(
    repo: DocumentoRepositoryDep,
    usuario_id: Annotated[
        UUID | None,
        Query(description='Si se indica, devuelve solo los documentos de ese usuario'),
    ] = None,
) -> list[Documento]:
    return await repo.list(usuario_id)


@router.post(
    '/',
    response_model=Documento,
    status_code=status.HTTP_201_CREATED,
    summary='Registrar y procesar un documento',
    description=(
        'Procesa el archivo de la ruta indicada con el pipeline de ingesta automático '
        '(RF2) y lo registra: guarda una copia del original, extrae el texto, lo limpia, '
        'lo fragmenta, genera el embedding de cada fragmento y guarda los fragmentos con '
        'sus vectores. El servidor reconoce el `nombre` y el `formato` a partir de la '
        'ruta, y asigna el `id`, la `fecha_carga` (UTC) y el `estado`: los que vengan en '
        'el cuerpo se ignoran. La `categoria` es la indicada por el cliente y queda '
        'vacía si no se envía; `num_paginas` se detecta del archivo y `progreso` '
        'refleja el avance de la ingesta (100 al terminar). La respuesta devuelve el documento ya '
        'procesado, con '
        '`estado` `listo`, o con `estado` `error` y el motivo del fallo en '
        '`metadatos["error"]` (RNF6: un documento fallido no interrumpe la aplicación).'
    ),
    responses={
        404: {'description': 'No existe el archivo o el usuario indicado'},
        422: {'description': 'La ruta no incluye la extensión del archivo'},
    },
)
async def create_document(
    ingestion: DocumentIngestionServiceDep,
    payload: Annotated[
        Documento,
        Body(
            openapi_examples={
                'valida': {
                    'summary': 'Registro válido',
                    'value': {
                        'usuario_id': '00000000-0000-4000-8000-000000000001',
                        'ruta_original': '/docs/manual_politicas.pdf',
                    },
                }
            }
        ),
    ],
) -> Documento:
    ruta = payload.ruta_original
    if not os.path.isfile(ruta):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No existe ningún archivo en la ruta {ruta}',
        )

    categoria = (payload.categoria or '').strip() or None

    try:
        return await ingestion.procesar_documento(
            ruta,
            usuario_id=payload.usuario_id,
            categoria=categoria,
            metadatos=payload.metadatos,
        )
    except ForeignKeyViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No existe un usuario con el id {payload.usuario_id}',
        ) from exc


@router.post(
    '/upload',
    response_model=Documento,
    status_code=status.HTTP_201_CREATED,
    summary='Subir y procesar un documento',
    description=(
        'Recibe un archivo PDF, DOCX o TXT desde el navegador, guarda una copia en el '
        'almacén y ejecuta el pipeline de ingesta (RF2). La `categoria` es opcional y '
        'se guarda tal como la indica el cliente; si no se envía, queda vacía. El '
        'servidor reconoce el `nombre` y el `formato` a partir del archivo y asigna '
        '`id`, `fecha_carga` (UTC), `estado`, `num_paginas` y `progreso`. La respuesta '
        'devuelve el documento procesado (o en `estado` `error` con el motivo en '
        '`metadatos["error"]` si el contenido no se pudo procesar).'
    ),
    responses={
        404: {'description': 'No existe el usuario indicado'},
        422: {'description': 'Formato no permitido o datos inválidos'},
    },
)
async def upload_document(
    ingestion: DocumentIngestionServiceDep,
    archivo: Annotated[UploadFile, File(description='Archivo PDF, DOCX o TXT')],
    usuario_id: Annotated[UUID, Form(description='Usuario propietario del documento')],
    categoria: Annotated[
        str | None,
        Form(max_length=100, description='Categoría temática opcional'),
    ] = None,
) -> Documento:
    nombre = archivo.filename or ''
    extension = os.path.splitext(nombre)[1].lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Formato no permitido: usa PDF, DOCX o TXT.',
        )

    categoria_limpia = (categoria or '').strip() or None

    try:
        return await ingestion.procesar_documento(
            archivo.file,
            usuario_id=usuario_id,
            categoria=categoria_limpia,
            nombre_archivo=nombre,
        )
    except ForeignKeyViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No existe un usuario con el id {usuario_id}',
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    finally:
        await archivo.close()


@router.get(
    '/{documento_id}',
    response_model=Documento,
    summary='Obtener un documento',
    description='Devuelve el documento con el identificador indicado.',
    responses={
        404: {'description': 'No existe un documento con ese identificador'},
        422: {'description': 'El identificador no es un UUID válido'},
    },
)
async def get_document(
    repo: DocumentoRepositoryDep,
    documento_id: Annotated[
        UUID,
        Path(description='Identificador del documento'),
    ],
) -> Documento:
    documento = await repo.get(documento_id)
    if documento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No existe un documento con el id {documento_id}',
        )
    return documento


@router.delete(
    '/{documento_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Eliminar un documento',
    description=(
        'Elimina el documento con el identificador indicado junto con todo lo que '
        'depende de él: sus fragmentos (chunks) con sus embeddings y las referencias '
        'a fuentes que los citen (la base de datos los borra en cascada), y también '
        'la copia del archivo guardada en el almacén.'
    ),
    responses={
        404: {'description': 'No existe un documento con ese identificador'},
        422: {'description': 'El identificador no es un UUID válido'},
    },
)
async def delete_document(
    repo: DocumentoRepositoryDep,
    storage: StorageServiceDep,
    documento_id: Annotated[
        UUID,
        Path(description='Identificador del documento'),
    ],
) -> Response:
    documento = await repo.get(documento_id)
    if documento is None or not await repo.delete(documento_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No existe un documento con el id {documento_id}',
        )
    storage.eliminar_original(documento.ruta_original)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

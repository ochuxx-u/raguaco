"""Rutas de documentos.

Conectan la API con la entidad de dominio `Documento`
(`domain/models/documento.py`) y con la tabla `documento` de PostgreSQL a
través de `DocumentoRepository`. El cliente solo indica la ruta del archivo
cargado; el servidor reconoce el resto de los datos (nombre y formato) y
asigna los que le corresponden (`id`, `fecha_carga`, `estado`). El registro
dispara el pipeline de ingesta (`DocumentIngestionService`, RF2), de modo que
`POST` devuelve el documento ya procesado (fragmentos y embeddings guardados).
"""

import os
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Path, Query, Response, status
from psycopg.errors import ForeignKeyViolation

from api.deps import DocumentIngestionServiceDep, DocumentoRepositoryDep
from domain.models.documento import Documento

router = APIRouter(prefix='/v1/models/documents', tags=['documents'])


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
        'el cuerpo se ignoran. La `categoria` se rellena con el mismo valor que el '
        '`formato`, `num_paginas` se detecta del archivo y `progreso` refleja el avance '
        'de la ingesta (100 al terminar). La respuesta devuelve el documento ya '
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

    try:
        return await ingestion.procesar_documento(
            ruta,
            usuario_id=payload.usuario_id,
            metadatos=payload.metadatos,
        )
    except ForeignKeyViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No existe un usuario con el id {payload.usuario_id}',
        ) from exc


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
    description='Elimina el documento con el identificador indicado.',
    responses={
        404: {'description': 'No existe un documento con ese identificador'},
        422: {'description': 'El identificador no es un UUID válido'},
    },
)
async def delete_document(
    repo: DocumentoRepositoryDep,
    documento_id: Annotated[
        UUID,
        Path(description='Identificador del documento'),
    ],
) -> Response:
    if not await repo.delete(documento_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No existe un documento con el id {documento_id}',
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

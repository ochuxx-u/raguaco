"""Rutas de documentos.

Conectan la API con la entidad de dominio `Documento`
(`domain/models/documento.py`) y con la tabla `documento` de PostgreSQL a
través de `DocumentoRepository`. El cliente solo indica la ruta del archivo
cargado; el servidor reconoce el resto de los datos (nombre y formato) y
asigna los que le corresponden (`id`, `fecha_carga`, `estado`).
"""

import os
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Path, Query, Response, status
from psycopg.errors import ForeignKeyViolation

from api.deps import DocumentoRepositoryDep
from domain.models.documento import Documento, EstadoDocumento

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
    summary='Registrar un documento',
    description=(
        'Registra un documento a partir de la ruta del archivo. El servidor reconoce '
        'el `nombre` y el `formato` a partir de la ruta, y asigna el `id`, la '
        '`fecha_carga` (UTC) y el `estado` inicial (`pendiente`): los que vengan en el '
        'cuerpo se ignoran.'
    ),
    responses={
        404: {'description': 'No existe el archivo o el usuario indicado'},
        422: {'description': 'La ruta no incluye la extensión del archivo'},
    },
)
async def create_document(
    repo: DocumentoRepositoryDep,
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

    documento = Documento(
        usuario_id=payload.usuario_id,
        nombre=payload.nombre,
        formato=payload.formato,
        ruta_original=ruta,
        categoria=payload.categoria,
        estado=EstadoDocumento.PENDIENTE,
        fecha_carga=datetime.now(timezone.utc),
        metadatos={**payload.metadatos, 'tamano_bytes': os.path.getsize(ruta)},
    )
    try:
        return await repo.create(documento)
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

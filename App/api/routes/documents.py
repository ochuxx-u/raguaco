"""Rutas de documentos.

Conectan la API con la entidad de dominio `Documento`
(`domain/models/documento.py`). El cliente solo indica la ruta del archivo
cargado; el servidor reconoce el resto de los datos (nombre y formato) y
asigna los que le corresponden (`id`, `fecha_carga`, `estado`).
"""

import os
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Path, Query, Response, status

from domain.models.documento import Documento, EstadoDocumento

router = APIRouter(prefix='/api/v1/documents', tags=['documents'])

# Almacenamiento temporal en memoria para poder probar los endpoints desde /docs.
# TODO: reemplazar por DocumentoRepository (infrastructure/db/repositories)
# inyectado con Depends(get_db).
_DOCUMENTOS: dict[UUID, Documento] = {}


@router.get(
    '/',
    response_model=list[Documento],
    summary='Listar documentos',
    description='Devuelve los documentos registrados, de la más reciente a la más antigua.',
)
async def list_documents(
    usuario_id: Annotated[
        UUID | None,
        Query(description='Si se indica, devuelve solo los documentos de ese usuario'),
    ] = None,
) -> list[Documento]:
    documentos = _DOCUMENTOS.values()
    if usuario_id is not None:
        documentos = [doc for doc in documentos if doc.usuario_id == usuario_id]
    return sorted(documentos, key=lambda doc: doc.fecha_carga, reverse=True)


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
        404: {'description': 'No existe ningún archivo en la ruta indicada'},
        422: {'description': 'La ruta no incluye la extensión del archivo'},
    },
)
async def create_document(
    payload: Annotated[
        Documento,
        Body(
            openapi_examples={
                'valida': {
                    'summary': 'Registro válido',
                    'value': {
                        'usuario_id': '8b1c0f4e-2a7d-4d6f-9c3b-5e8a1d2f7a10',
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
    _DOCUMENTOS[documento.id] = documento
    return documento


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
    documento_id: Annotated[
        UUID,
        Path(description='Identificador del documento'),
    ],
) -> Documento:
    documento = _DOCUMENTOS.get(documento_id)
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
    documento_id: Annotated[
        UUID,
        Path(description='Identificador del documento'),
    ],
) -> Response:
    if documento_id not in _DOCUMENTOS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No existe un documento con el id {documento_id}',
        )
    del _DOCUMENTOS[documento_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)

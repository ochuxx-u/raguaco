from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Body, HTTPException, Query, status
from psycopg.errors import UniqueViolation
from pydantic import EmailStr

from api.deps import UsuarioRepositoryDep
from domain.models.usuario import Usuario

router = APIRouter(prefix='/v1/models/users', tags=['users'])


@router.get(
    '/',
    response_model=Usuario,
    summary='Buscar usuario por email',
    description='Devuelve el usuario cuyo email coincide con el indicado.',
    responses={
        404: {'description': 'No existe un usuario con ese email'},
        422: {'description': 'El email no tiene un formato válido'},
    },
)
async def get_user(
    repo: UsuarioRepositoryDep,
    email: Annotated[
        EmailStr,
        Query(description='Email del usuario a buscar'),
    ],
) -> Usuario:
    usuario = await repo.get_by_email(email)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'No existe un usuario con el email {email}',
        )
    return usuario


@router.post(
    '/',
    response_model=Usuario,
    status_code=status.HTTP_201_CREATED,
    summary='Registrar un usuario',
    description=(
        'Da de alta un usuario. El `email` debe ser único. '
        'El `id` lo asigna el servidor: el que venga en el cuerpo se ignora.'
    ),
    responses={
        409: {'description': 'El email ya está registrado'}
    },
)
async def create_user(
    repo: UsuarioRepositoryDep,
    payload: Annotated[
        Usuario,
        Body(
            openapi_examples={
                'valido': {
                    'summary': 'Alta válida',
                    'value': {'nombre': 'Ana García', 'email': 'ana@ejemplo.com'},
                }
            }
        ),
    ],
) -> Usuario:
    email = payload.email.lower()
    if await repo.get_by_email(email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'El email {payload.email} ya está registrado',
        )

    usuario = Usuario(id=uuid4(), nombre=payload.nombre, email=email)
    try:
        return await repo.create(usuario)
    except UniqueViolation as exc:
        # Otra petición pudo registrar el mismo email entre la consulta y el
        # insert; la restricción unique de la base sigue siendo la fuente de verdad.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'El email {payload.email} ya está registrado',
        ) from exc

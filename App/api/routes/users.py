from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import EmailStr

from domain.models.usuario import Usuario

router = APIRouter(prefix='/v1/models/users', tags=['users'])

# Almacenamiento temporal en memoria para poder probar los endpoints desde /docs.
# TODO: reemplazar por UsuarioRepository (infrastructure/db/repositories) inyectado con Depends(get_db).
_USERS: dict[UUID, Usuario] = {}


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
    email: Annotated[
        EmailStr,
        Query(description='Email del usuario a buscar'),
    ],
) -> Usuario:
    target = email.lower()
    for usuario in _USERS.values():
        if usuario.email.lower() == target:
            return usuario
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f'No existe un usuario con el email {email}',
    )


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
    if any(usuario.email.lower() == email for usuario in _USERS.values()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'El email {payload.email} ya está registrado',
        )

    usuario = Usuario(id=uuid4(), nombre=payload.nombre, email=email)
    _USERS[usuario.id] = usuario
    return usuario

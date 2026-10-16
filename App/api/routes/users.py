from typing import Annotated
from fastapi import APIRouter, Body, HTTPException, status
from domain.schemas.users import UserCreate, UserRead

router = APIRouter(prefix='/api/v1/users', tags=['users'])

# Almacenamiento temporal en memoria para poder probar los endpoints desde /docs.
# TODO: reemplazar por UsuarioRepository (infrastructure/db/repositories) inyectado con Depends(get_db).
_USERS: dict[int, UserRead] = {}
_next_id = 1


@router.get(
    '/',
    response_model=list[UserRead],
    summary='Listar usuarios',
    description='Devuelve todos los usuarios registrados.',
)
async def users() -> list[UserRead]:
    return list(_USERS.values())


@router.post(
    '/',
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary='Registrar un usuario',
    description='Da de alta un usuario. El `email` debe ser único.',
    responses={
        409: {'description': 'El email ya está registrado'}
    },
)
async def create_user(
    payload: Annotated[
        UserCreate,
        Body(
            openapi_examples={
                'valido': {
                    'summary': 'Alta válida',
                    'value': {'nombre': 'Ana García', 'email': 'ana@ejemplo.com'},
                }
            }
        ),
    ],
) -> UserRead:
    global _next_id
    
    email = payload.email.lower()
    if any(user.email.lower() == email for user in _USERS.values()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'El email {payload.email} ya está registrado',
        )
    
    user = UserRead(id=_next_id, nombre=payload.nombre, email=email)
    _USERS[_next_id] = user
    _next_id += 1
    return user

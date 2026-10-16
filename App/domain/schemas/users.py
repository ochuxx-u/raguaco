from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Datos que envía el cliente para registrar un usuario."""

    nombre: str = Field(min_length=2, max_length=50, description='Nombre del usuario')
    email: EmailStr = Field(description='Correo del usuario; debe ser único')


class UserRead(BaseModel):
    """Representación pública del usuario devuelta por la API."""

    id: int = Field(description='Identificador del usuario')
    nombre: str
    email: EmailStr

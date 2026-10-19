"""Configuración común de los modelos de dominio.

Las entidades de `domain/models` son la representación *del dominio* (el diagrama de
clases y el diagrama entidad-relación). La API las expone directamente: no hay una
capa de DTO aparte. Esta clase base solo define comportamiento transversal para no
repetir configuración en cada entidad.
"""

from pydantic import BaseModel, ConfigDict


class ModeloBase(BaseModel):
    """Clase base de todas las entidades del dominio.

    Configuración:

    - `from_attributes`: permite construir el modelo desde una fila de base de datos
      o desde un objeto del ORM (`modelo.model_validate(fila)`).
    - `validate_assignment`: valida también las asignaciones posteriores
      (`documento.estado = ...`), de modo que el dominio no quede con estados inválidos.
    - `populate_by_name`: acepta tanto el nombre del campo como su alias.
    """

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        populate_by_name=True,
    )

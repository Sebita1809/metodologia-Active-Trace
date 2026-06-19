"""Domain model exports for the academic structure module."""

from app.models.domain.asignacion import Asignacion
from app.models.domain.carrera import Carrera
from app.models.domain.cohorte import Cohorte
from app.models.domain.materia import Materia
from app.models.domain.umbral_materia import UmbralMateria
from app.models.domain.usuario import Usuario

__all__ = [
    "Asignacion",
    "Carrera",
    "Cohorte",
    "Materia",
    "UmbralMateria",
    "Usuario",
]

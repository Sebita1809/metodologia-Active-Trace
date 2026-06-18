"""Domain model exports for the academic structure module."""

from app.models.domain.carrera import Carrera
from app.models.domain.cohorte import Cohorte
from app.models.domain.materia import Materia

__all__ = [
    "Carrera",
    "Cohorte",
    "Materia",
]

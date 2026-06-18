"""Shared enumerations reused across domain models."""

import enum


class EstadoGenerico(str, enum.Enum):
    ACTIVA = "Activa"
    INACTIVA = "Inactiva"

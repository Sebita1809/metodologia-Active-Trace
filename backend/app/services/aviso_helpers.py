"""
app/services/aviso_helpers.py — Pure helper functions for aviso business logic.

These functions contain NO side effects and NO DB access.
They are extracted as pure functions to enable easy unit testing without a DB.

Implemented: C-15 (avisos-y-acknowledgment)
"""
from __future__ import annotations

import uuid
from datetime import datetime


def aviso_es_vigente(inicio_en: datetime, fin_en: datetime, ahora: datetime) -> bool:
    """Return True if *ahora* falls within [inicio_en, fin_en] inclusive.

    Parameters
    ----------
    inicio_en:
        The datetime when the aviso becomes visible (inclusive).
    fin_en:
        The datetime when the aviso expires (inclusive).
    ahora:
        The current datetime to evaluate against the window.

    Returns
    -------
    True when inicio_en <= ahora <= fin_en.
    """
    return inicio_en <= ahora <= fin_en


def usuario_en_audiencia(
    alcance: str,
    rol_destino: str | None,
    cohorte_id: uuid.UUID | None,
    materia_id: uuid.UUID | None,
    usuario_rol: str,
    usuario_cohorte_ids: list[uuid.UUID],
    usuario_materia_ids: list[uuid.UUID],
) -> bool:
    """Return True if the user falls within the aviso's target audience.

    Parameters
    ----------
    alcance:
        Audience segmentation: 'Global' | 'PorMateria' | 'PorCohorte' | 'PorRol'
    rol_destino:
        Required when alcance='PorRol'. Target role name (e.g. 'ALUMNO').
    cohorte_id:
        Required when alcance='PorCohorte'. Target cohorte UUID.
    materia_id:
        Required when alcance='PorMateria'. Target materia UUID.
    usuario_rol:
        The authenticated user's primary role.
    usuario_cohorte_ids:
        UUIDs of the cohortes the user belongs to.
    usuario_materia_ids:
        UUIDs of the materias the user is enrolled in / assigned to.

    Returns
    -------
    True if the user is in the target audience; False otherwise.
    Unknown alcance values return False (safe default).
    """
    if alcance == "Global":
        return True
    if alcance == "PorRol":
        return rol_destino == usuario_rol
    if alcance == "PorCohorte":
        return cohorte_id in usuario_cohorte_ids
    if alcance == "PorMateria":
        return materia_id in usuario_materia_ids
    return False

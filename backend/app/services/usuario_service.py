"""
app/services/usuario_service.py — UsuarioService.

Business logic for Usuario profiles with encrypted PII.

Rules enforced:
  - Encrypt PII on create/update; decrypt on get/list responses.
  - email_hash computed from normalized email for uniqueness check.
  - Uniqueness violations on (tenant_id, email_hash) surfaced as ValueError.
  - Tenant identity always from constructor (JWT-sourced), never from request.
  - Soft delete for audit trail.
  - NEVER log PII or include PII in error messages.

Implemented: C-07 (usuarios-y-asignaciones)
Updated:     fix-admin-usuario-patch — roles from Asignacion
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import CryptoService
from app.models.usuario import Usuario
from app.repositories.usuario_repository import UsuarioRepository


@dataclass
class UsuarioDecifrado:
    """Transient DTO carrying decrypted PII — never persisted."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    nombre: str
    apellidos: str
    email: str
    dni: str | None
    cuil: str | None
    cbu: str | None
    alias_cbu: str | None
    banco: str | None
    regional: str | None
    legajo: str | None
    legajo_profesional: str | None
    sexo: str | None
    modalidad_cobro: str | None
    facturador: bool
    estado: str
    created_at: object
    updated_at: object
    roles: list[dict] = field(default_factory=list)


class UsuarioService:
    """CRUD operations for Usuario profiles.

    Encrypts PII on write; decrypts on read.
    All operations scoped to *tenant_id* from JWT — never from request body.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        crypto: CryptoService,
    ) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._crypto = crypto
        self._repo = UsuarioRepository(session=session, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _encrypt_optional(self, value: str | None) -> str | None:
        """Encrypt *value* if not None."""
        return self._crypto.encrypt(value) if value is not None else None

    def _decrypt_optional(self, ciphertext: str | None) -> str | None:
        """Decrypt *ciphertext* if not None."""
        return self._crypto.decrypt(ciphertext) if ciphertext is not None else None

    @staticmethod
    def _compute_vigencia(hasta: date | None) -> str | None:
        if hasta is None:
            return "Vigente"
        return "Vencida" if hasta < date.today() else "Vigente"

    def _to_decifrado(self, usuario: Usuario) -> UsuarioDecifrado:
        """Build a UsuarioDecifrado by decrypting all PII fields."""
        roles = [
            {
                "rol": a.rol,
                "materia": str(a.materia_id) if a.materia_id is not None else None,
                "vigencia": self._compute_vigencia(a.hasta),
            }
            for a in usuario.asignaciones
        ]
        return UsuarioDecifrado(
            id=usuario.id,
            tenant_id=usuario.tenant_id,
            nombre=usuario.nombre,
            apellidos=usuario.apellidos,
            email=self._crypto.decrypt(usuario.email),
            dni=self._decrypt_optional(usuario.dni),
            cuil=self._decrypt_optional(usuario.cuil),
            cbu=self._decrypt_optional(usuario.cbu),
            alias_cbu=self._decrypt_optional(usuario.alias_cbu),
            banco=usuario.banco,
            regional=usuario.regional,
            legajo=usuario.legajo,
            legajo_profesional=usuario.legajo_profesional,
            sexo=usuario.sexo,
            modalidad_cobro=usuario.modalidad_cobro,
            facturador=usuario.facturador,
            estado=usuario.estado,
            roles=roles,
            created_at=usuario.created_at,
            updated_at=usuario.updated_at,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        nombre: str,
        apellidos: str,
        email: str,
        dni: str | None = None,
        cuil: str | None = None,
        cbu: str | None = None,
        alias_cbu: str | None = None,
        banco: str | None = None,
        regional: str | None = None,
        legajo: str | None = None,
        legajo_profesional: str | None = None,
        sexo: str | None = None,
        modalidad_cobro: str | None = None,
        facturador: bool = False,
        estado: str = "Activo",
    ) -> UsuarioDecifrado:
        """Create a new Usuario with encrypted PII.

        Raises ValueError if a Usuario with the same email already exists
        in this tenant (translated to HTTP 409 by the router).
        """
        email_hash = self._crypto.hash_deterministic(email)

        existing = await self._repo.get_by_email_hash(email_hash)
        if existing is not None:
            # Do NOT include the email in the error message (no PII in logs)
            raise ValueError("Ya existe un usuario con ese email en este tenant")

        usuario = Usuario(
            tenant_id=self._tenant_id,
            nombre=nombre,
            apellidos=apellidos,
            email=self._crypto.encrypt(email),
            email_hash=email_hash,
            dni=self._encrypt_optional(dni),
            cuil=self._encrypt_optional(cuil),
            cbu=self._encrypt_optional(cbu),
            alias_cbu=self._encrypt_optional(alias_cbu),
            banco=banco,
            regional=regional,
            legajo=legajo,
            legajo_profesional=legajo_profesional,
            sexo=sexo,
            modalidad_cobro=modalidad_cobro,
            facturador=facturador,
            estado=estado,
        )
        persisted = await self._repo.create(usuario)
        return self._to_decifrado(persisted)

    async def get(self, usuario_id: uuid.UUID) -> UsuarioDecifrado | None:
        """Return Usuario by ID (decrypted PII), or None if not found."""
        usuario = await self._repo.get(usuario_id)
        if usuario is None:
            return None
        return self._to_decifrado(usuario)

    async def list(self) -> list[UsuarioDecifrado]:
        """Return all non-deleted Usuarios in this tenant (PII decrypted)."""
        usuarios = await self._repo.list()
        return [self._to_decifrado(u) for u in usuarios]

    async def update(
        self,
        usuario_id: uuid.UUID,
        *,
        nombre: str | None = None,
        apellidos: str | None = None,
        email: str | None = None,
        dni: str | None = None,
        cuil: str | None = None,
        cbu: str | None = None,
        alias_cbu: str | None = None,
        banco: str | None = None,
        regional: str | None = None,
        legajo: str | None = None,
        legajo_profesional: str | None = None,
        sexo: str | None = None,
        modalidad_cobro: str | None = None,
        facturador: bool | None = None,
        estado: str | None = None,
    ) -> UsuarioDecifrado | None:
        """Update a Usuario. Returns None if not found.

        Only re-encrypts PII fields that are explicitly provided (not None).
        Raises ValueError if the new email conflicts with another user.
        """
        data: dict = {}

        # Normalize empty strings to None for encrypted optional fields
        if cbu is not None and cbu.strip() == "":
            cbu = None
        if alias_cbu is not None and alias_cbu.strip() == "":
            alias_cbu = None
        if modalidad_cobro is not None and modalidad_cobro.strip() == "":
            modalidad_cobro = None

        if nombre is not None:
            data["nombre"] = nombre
        if apellidos is not None:
            data["apellidos"] = apellidos
        if email is not None:
            email_hash = self._crypto.hash_deterministic(email)
            existing = await self._repo.get_by_email_hash(email_hash)
            if existing is not None and existing.id != usuario_id:
                raise ValueError("Ya existe un usuario con ese email en este tenant")
            data["email"] = self._crypto.encrypt(email)
            data["email_hash"] = email_hash
        if dni is not None:
            data["dni"] = self._crypto.encrypt(dni)
        if cuil is not None:
            data["cuil"] = self._crypto.encrypt(cuil)
        if cbu is not None:
            data["cbu"] = self._crypto.encrypt(cbu)
        if alias_cbu is not None:
            data["alias_cbu"] = self._crypto.encrypt(alias_cbu)
        if banco is not None:
            data["banco"] = banco
        if regional is not None:
            data["regional"] = regional
        if legajo is not None:
            data["legajo"] = legajo
        if legajo_profesional is not None:
            data["legajo_profesional"] = legajo_profesional
        if sexo is not None:
            data["sexo"] = sexo
        if modalidad_cobro is not None:
            data["modalidad_cobro"] = modalidad_cobro
        if facturador is not None:
            data["facturador"] = facturador
        if estado is not None:
            data["estado"] = estado

        updated = await self._repo.update(usuario_id, **data)
        if updated is None:
            return None
        return self._to_decifrado(updated)

    async def delete(self, usuario_id: uuid.UUID) -> bool:
        """Soft-delete a Usuario. Returns False if not found."""
        return await self._repo.soft_delete(usuario_id)

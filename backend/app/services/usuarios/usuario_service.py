"""Business logic for Usuario CRUD with PII encryption."""
import hashlib
import hmac
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import EstadoGenerico
from app.core.security import AESCipher
from app.repositories.usuarios.usuario_repository import UsuarioRepository


class UsuarioService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = UsuarioRepository(db, tenant_id)

    async def create(self, data: dict) -> dict:
        """Create a user with PII encrypted."""
        email = data.get("email", "").lower().strip()

        # Check uniqueness
        if await self.repo.exists_by_email(email):
            raise HTTPException(status_code=409, detail="Email already exists")

        # Encrypt PII fields
        encrypted = {
            "email": AESCipher.encrypt(email),
            "email_hash": self._compute_email_hash(email),
        }
        for field in ("dni", "cuil", "cbu", "alias_cbu"):
            val = data.get(field)
            encrypted[field] = AESCipher.encrypt(val) if val else None

        # Build create payload
        create_data = {
            "nombre": data["nombre"],
            "apellidos": data["apellidos"],
            "email": encrypted["email"],
            "email_hash": encrypted["email_hash"],
            "dni": encrypted["dni"],
            "cuil": encrypted["cuil"],
            "cbu": encrypted["cbu"],
            "alias_cbu": encrypted["alias_cbu"],
            "banco": data.get("banco"),
            "regional": data.get("regional"),
            "legajo": data.get("legajo"),
            "legajo_profesional": data.get("legajo_profesional"),
            "facturador": data.get("facturador", False),
            "estado": EstadoGenerico.ACTIVA.value,
        }

        entity = await self.repo.create(create_data)
        return self._to_response(entity)

    async def get(self, id: uuid.UUID) -> dict:
        entity = await self.repo.get(id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Usuario not found")
        return self._to_response(entity)

    async def list(self, email: str | None = None) -> list[dict]:
        if email:
            entity = await self.repo.get_by_email(email)
            return [self._to_response(entity)] if entity else []
        entities = await self.repo.list()
        return [self._to_response(e) for e in entities]

    async def update(self, id: uuid.UUID, data: dict) -> dict:
        entity = await self.repo.get(id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Usuario not found")

        update_data = {}
        for field in ("nombre", "apellidos", "banco", "regional",
                      "legajo", "legajo_profesional", "facturador"):
            if field in data:
                update_data[field] = data[field]

        # Handle PII updates
        if "email" in data:
            email = data["email"].lower().strip()
            # Check uniqueness (excluding current user)
            existing = await self.repo.get_by_email(email)
            if existing and existing.id != id:
                raise HTTPException(status_code=409, detail="Email already exists")
            update_data["email"] = AESCipher.encrypt(email)
            update_data["email_hash"] = self._compute_email_hash(email)

        for field in ("dni", "cuil", "cbu", "alias_cbu"):
            if field in data:
                val = data[field]
                update_data[field] = AESCipher.encrypt(val) if val else None

        updated = await self.repo.update(id, update_data)
        if updated is None:
            raise HTTPException(status_code=404, detail="Usuario not found")
        return self._to_response(updated)

    async def deactivate(self, id: uuid.UUID) -> None:
        entity = await self.repo.get(id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Usuario not found")
        if entity.estado == EstadoGenerico.INACTIVA.value:
            raise HTTPException(
                status_code=409, detail="Usuario is already inactive"
            )
        await self.repo.update(id, {"estado": EstadoGenerico.INACTIVA.value})

    async def get_by_email(self, email: str) -> dict | None:
        entity = await self.repo.get_by_email(email)
        if entity is None:
            return None
        return self._to_response(entity)

    @staticmethod
    def _safe_decrypt(ciphertext: str | None) -> str | None:
        if not ciphertext:
            return None
        try:
            return AESCipher.decrypt(ciphertext)
        except Exception:
            return "[encrypted]"

    def _to_response(self, entity) -> dict:
        return {
            "id": entity.id,
            "tenant_id": entity.tenant_id,
            "nombre": entity.nombre,
            "apellidos": entity.apellidos,
            "email": self._safe_decrypt(entity.email) or "",
            "dni": self._safe_decrypt(entity.dni),
            "cuil": self._safe_decrypt(entity.cuil),
            "cbu": self._safe_decrypt(entity.cbu),
            "alias_cbu": self._safe_decrypt(entity.alias_cbu),
            "banco": entity.banco,
            "regional": entity.regional,
            "legajo": entity.legajo,
            "legajo_profesional": entity.legajo_profesional,
            "facturador": entity.facturador,
            "estado": entity.estado,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
        }

    @staticmethod
    def _compute_email_hash(email: str) -> str:
        key = get_settings().ENCRYPTION_KEY.encode("utf-8")
        normalized = email.lower().strip().encode("utf-8")
        return hmac.new(key, normalized, hashlib.sha256).hexdigest()

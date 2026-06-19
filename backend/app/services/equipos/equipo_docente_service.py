"""Domain service for teaching team operations."""
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import EstadoGenerico
from app.repositories.usuarios.asignacion_repository import AsignacionRepository
from app.repositories.usuarios.umbral_materia_repository import UmbralMateriaRepository
from app.repositories.usuarios.usuario_repository import UsuarioRepository

VALID_ROLES = {"ALUMNO", "TUTOR", "PROFESOR", "COORDINADOR", "NEXO", "ADMIN", "FINANZAS"}
MAX_MASIVA = 200


class EquipoDocenteService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = AsignacionRepository(db, tenant_id)
        self.usuario_repo = UsuarioRepository(db, tenant_id)
        self.umbral_repo = UmbralMateriaRepository(db, tenant_id)

    async def get_mis_equipos(self, usuario_id: uuid.UUID) -> list[dict]:
        entities = await self.repo.list_vigentes_por_usuario(usuario_id)
        return [self._to_response(e) for e in entities]

    async def get_equipo_por_materia(self, materia_id: uuid.UUID, cohorte_id: uuid.UUID | None = None) -> list[dict]:
        entities = await self.repo.list_vigentes_por_materia_y_cohorte(materia_id, cohorte_id)
        return [self._to_response(e) for e in entities]

    async def asignacion_masiva(self, data: dict) -> list[dict]:
        materia_id = data.get("materia_id")
        carrera_id = data.get("carrera_id")
        cohorte_id = data.get("cohorte_id")
        rol = data["rol"]
        desde = data["desde"]
        hasta = data.get("hasta")
        usuario_ids = data["usuario_ids"]
        comisiones = data.get("comisiones") or []
        responsable_id = data.get("responsable_id")

        if rol not in VALID_ROLES:
            raise HTTPException(status_code=422, detail=f"Invalid role: {rol}")

        if hasta and desde > hasta:
            raise HTTPException(status_code=422, detail="desde must be before or equal to hasta")

        if len(usuario_ids) > MAX_MASIVA:
            raise HTTPException(status_code=422, detail=f"Maximum {MAX_MASIVA} users per request")

        for uid in usuario_ids:
            user = await self.usuario_repo.get(uuid.UUID(uid) if isinstance(uid, str) else uid)
            if user is None:
                raise HTTPException(status_code=422, detail=f"User {uid} not found in tenant")
            if user.estado != EstadoGenerico.ACTIVA.value:
                raise HTTPException(status_code=422, detail=f"User {uid} is inactive")

        if responsable_id:
            resp_user = await self.usuario_repo.get(responsable_id)
            if resp_user is None:
                raise HTTPException(status_code=422, detail="Responsable not found in tenant")

        created = []
        for uid in usuario_ids:
            create_data = {
                "usuario_id": uuid.UUID(uid) if isinstance(uid, str) else uid,
                "rol": rol,
                "materia_id": materia_id,
                "carrera_id": carrera_id,
                "cohorte_id": cohorte_id,
                "comisiones": comisiones,
                "responsable_id": responsable_id,
                "desde": desde,
                "hasta": hasta,
            }
            entity = await self.repo.create(create_data)
            if rol in ("PROFESOR", "TUTOR") and materia_id:
                await self.umbral_repo.create_default(entity.id, materia_id)
            created.append(self._to_response(entity))

        return created

    async def clonar_equipo(self, data: dict) -> dict:
        materia_id = data["materia_id"]
        cohorte_origen_id = data["cohorte_origen_id"]
        cohorte_destino_id = data["cohorte_destino_id"]
        desde = data["desde"]
        hasta = data.get("hasta")

        if cohorte_origen_id == cohorte_destino_id:
            raise HTTPException(status_code=422, detail="Origin and destination cohorts must be different")

        origen = await self.repo.list_vigentes_por_materia_y_cohorte(materia_id, cohorte_origen_id)
        if not origen:
            return {"creadas": [], "conteo": 0}

        creadas = []
        for asig in origen:
            create_data = {
                "usuario_id": asig.usuario_id,
                "rol": asig.rol,
                "materia_id": materia_id,
                "carrera_id": asig.carrera_id,
                "cohorte_id": cohorte_destino_id,
                "comisiones": asig.comisiones,
                "responsable_id": asig.responsable_id,
                "desde": desde,
                "hasta": hasta,
            }
            entity = await self.repo.create(create_data)
            if asig.rol in ("PROFESOR", "TUTOR") and materia_id:
                await self.umbral_repo.create_default(entity.id, materia_id)
            creadas.append(self._to_response(entity))

        return {"creadas": creadas, "conteo": len(creadas)}

    async def modificar_vigencia(self, data: dict) -> dict:
        materia_id = data["materia_id"]
        desde = data["desde"]
        hasta = data.get("hasta")
        cohorte_id = data.get("cohorte_id")

        if hasta and desde > hasta:
            raise HTTPException(status_code=422, detail="desde must be before or equal to hasta")

        entities = await self.repo.list_vigentes_por_materia_y_cohorte(materia_id, cohorte_id)
        conteo = 0
        for entity in entities:
            await self.repo.update(entity.id, {"desde": desde, "hasta": hasta})
            conteo += 1

        return {"conteo": conteo}

    def _to_response(self, entity) -> dict:
        return {
            "id": entity.id,
            "tenant_id": entity.tenant_id,
            "usuario_id": entity.usuario_id,
            "rol": entity.rol,
            "materia_id": entity.materia_id,
            "carrera_id": entity.carrera_id,
            "cohorte_id": entity.cohorte_id,
            "comisiones": entity.comisiones,
            "responsable_id": entity.responsable_id,
            "desde": entity.desde,
            "hasta": entity.hasta,
            "estado_vigencia": entity.estado_vigencia,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
        }

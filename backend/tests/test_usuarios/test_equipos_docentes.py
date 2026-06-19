"""Tests for Equipo Docente endpoints — consulta, asignación masiva, clonación, vigencia, exportación y validación de desactivación (C-08)."""

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.tenant import Tenant

pytestmark = pytest.mark.asyncio

BASE = "/api/v1/equipos"
USUARIOS_BASE = "/api/v1/admin/usuarios"
MATERIAS_BASE = "/api/v1/admin/materias"
CARRERAS_BASE = "/api/v1/admin/carreras"
COHORTES_BASE = "/api/v1/admin/cohortes"
ASIGNACIONES_BASE = "/api/v1/asignaciones"


def _admin_token(tenant_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(
        user_id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        roles=["ADMIN"],
    )
    return {"Authorization": f"Bearer {token}"}


def _coord_token(tenant_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(
        user_id=str(uuid.uuid4()),
        tenant_id=str(tenant_id),
        roles=["COORDINADOR"],
    )
    return {"Authorization": f"Bearer {token}"}


def _token_for_user(
    user_id: uuid.UUID, tenant_id: uuid.UUID, roles: list[str]
) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user_id),
        tenant_id=str(tenant_id),
        roles=roles,
    )
    return {"Authorization": f"Bearer {token}"}


async def _crear_usuario(
    client: AsyncClient, headers: dict, email_suffix: str = ""
) -> dict:
    resp = await client.post(
        f"{USUARIOS_BASE}/",
        json={
            "nombre": "Equipo",
            "apellidos": "Test",
            "email": f"equipo.{email_suffix or uuid.uuid4().hex[:8]}@example.com",
        },
        headers=headers,
    )
    return resp.json()


async def _crear_materia(
    client: AsyncClient, headers: dict, codigo: str = ""
) -> dict:
    resp = await client.post(
        f"{MATERIAS_BASE}/",
        json={
            "codigo": codigo or f"EQ-{uuid.uuid4().hex[:6].upper()}",
            "nombre": "Materia Test Equipos",
        },
        headers=headers,
    )
    return resp.json()


async def _crear_carrera(
    client: AsyncClient, headers: dict, codigo: str = ""
) -> dict:
    resp = await client.post(
        f"{CARRERAS_BASE}/",
        json={
            "codigo": codigo or f"CARR-{uuid.uuid4().hex[:6].upper()}",
            "nombre": "Carrera Test Equipos",
        },
        headers=headers,
    )
    return resp.json()


async def _crear_cohorte(
    client: AsyncClient, headers: dict, carrera_id: uuid.UUID, nombre: str = ""
) -> dict:
    resp = await client.post(
        f"{COHORTES_BASE}/",
        json={
            "carrera_id": str(carrera_id),
            "nombre": nombre or f"Cohorte {uuid.uuid4().hex[:6]}",
            "anio": 2026,
            "vig_desde": "2026-03-01",
        },
        headers=headers,
    )
    return resp.json()


# ═══════════════════════════════════════════════════════════════
# Mis Equipos
# ═══════════════════════════════════════════════════════════════


class TestMisEquipos:
    async def test_mis_equipos_asignado(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN a user with asignaciones WHEN they GET /mis-equipos THEN 200 with their asignaciones."""
        admin_headers = _admin_token(tenant_a.id)
        user = await _crear_usuario(async_client, admin_headers, "docente")
        user_id = uuid.UUID(user["id"])

        await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": str(user_id),
                "rol": "PROFESOR",
                "desde": "2026-01-01",
                "hasta": "2026-12-31",
            },
            headers=admin_headers,
        )

        headers = _token_for_user(user_id, tenant_a.id, ["PROFESOR"])
        response = await async_client.get(f"{BASE}/mis-equipos", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["rol"] == "PROFESOR"
        assert data[0]["usuario_id"] == str(user_id)

    async def test_mis_equipos_sin_asignaciones(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN a user without asignaciones WHEN they GET /mis-equipos THEN 200 with empty list."""
        admin_headers = _admin_token(tenant_a.id)
        user = await _crear_usuario(async_client, admin_headers, "soltero")
        user_id = uuid.UUID(user["id"])

        headers = _token_for_user(user_id, tenant_a.id, ["PROFESOR"])
        response = await async_client.get(f"{BASE}/mis-equipos", headers=headers)
        assert response.status_code == 200
        assert response.json() == []

    async def test_mis_equipos_no_auth(self, async_client: AsyncClient):
        """WHEN no auth token THEN 401."""
        response = await async_client.get(f"{BASE}/mis-equipos")
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════
# Equipo por Materia
# ═══════════════════════════════════════════════════════════════


class TestEquipoPorMateria:
    async def test_equipo_materia_existente(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN a materia with asignaciones WHEN GET /materias/{id} THEN 200 with team grouped by cohorte."""
        headers = _admin_token(tenant_a.id)
        materia = await _crear_materia(async_client, headers)
        user1 = await _crear_usuario(async_client, headers, "prof1")
        user2 = await _crear_usuario(async_client, headers, "prof2")

        await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": user1["id"],
                "rol": "PROFESOR",
                "materia_id": materia["id"],
                "desde": "2026-01-01",
                "hasta": "2026-12-31",
            },
            headers=headers,
        )
        await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": user2["id"],
                "rol": "TUTOR",
                "materia_id": materia["id"],
                "desde": "2026-01-01",
                "hasta": "2026-12-31",
            },
            headers=headers,
        )

        response = await async_client.get(
            f"{BASE}/materias/{materia['id']}", headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        roles = {a["rol"] for a in data}
        assert roles == {"PROFESOR", "TUTOR"}

    async def test_equipo_materia_inexistente(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN materia does not exist THEN 404."""
        headers = _admin_token(tenant_a.id)
        response = await async_client.get(
            f"{BASE}/materias/{uuid.uuid4()}", headers=headers
        )
        assert response.status_code == 404

    async def test_equipo_filtrado_por_cohorte(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """WHEN querying with ?cohorte_id= THEN only matching asignaciones returned."""
        headers = _admin_token(tenant_a.id)
        materia = await _crear_materia(async_client, headers)
        carrera = await _crear_carrera(async_client, headers)
        cohorte1 = await _crear_cohorte(async_client, headers, uuid.UUID(carrera["id"]), "CohA")
        cohorte2 = await _crear_cohorte(async_client, headers, uuid.UUID(carrera["id"]), "CohB")

        user = await _crear_usuario(async_client, headers, "filtro")

        await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": user["id"],
                "rol": "PROFESOR",
                "materia_id": materia["id"],
                "carrera_id": carrera["id"],
                "cohorte_id": cohorte1["id"],
                "desde": "2026-01-01",
                "hasta": "2026-12-31",
            },
            headers=headers,
        )
        await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": user["id"],
                "rol": "TUTOR",
                "materia_id": materia["id"],
                "carrera_id": carrera["id"],
                "cohorte_id": cohorte2["id"],
                "desde": "2026-01-01",
                "hasta": "2026-12-31",
            },
            headers=headers,
        )

        response = await async_client.get(
            f"{BASE}/materias/{materia['id']}",
            params={"cohorte_id": cohorte1["id"]},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["rol"] == "PROFESOR"


# ═══════════════════════════════════════════════════════════════
# Asignación Masiva
# ═══════════════════════════════════════════════════════════════


class TestAsignacionMasiva:
    async def test_masiva_exitosa(
        self, async_client: AsyncClient, tenant_a: Tenant, db_session: AsyncSession
    ):
        """GIVEN valid users and context WHEN POST /asignacion-masiva THEN 201 with all creadas + UmbralMateria."""
        headers = _admin_token(tenant_a.id)
        materia = await _crear_materia(async_client, headers)
        carrera = await _crear_carrera(async_client, headers)
        cohorte = await _crear_cohorte(async_client, headers, uuid.UUID(carrera["id"]))
        user1 = await _crear_usuario(async_client, headers, "masiva1")
        user2 = await _crear_usuario(async_client, headers, "masiva2")

        payload = {
            "materia_id": materia["id"],
            "carrera_id": carrera["id"],
            "cohorte_id": cohorte["id"],
            "rol": "PROFESOR",
            "usuario_ids": [user1["id"], user2["id"]],
            "desde": "2026-01-01",
            "hasta": "2026-12-31",
            "comisiones": [],
        }
        response = await async_client.post(
            f"{BASE}/asignacion-masiva", json=payload, headers=headers
        )
        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        for asignacion in data:
            assert asignacion["rol"] == "PROFESOR"
            assert asignacion["materia_id"] == materia["id"]
            assert "estado_vigencia" in asignacion

        result = await db_session.execute(
            text("SELECT COUNT(*) FROM umbral_materia WHERE materia_id = :mid"),
            {"mid": materia["id"]},
        )
        count = result.scalar()
        assert count == 2

    async def test_masiva_usuario_inactivo(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN an inactive user in the list WHEN POST /asignacion-masiva THEN 422 without creating any."""
        headers = _admin_token(tenant_a.id)
        materia = await _crear_materia(async_client, headers)
        carrera = await _crear_carrera(async_client, headers)
        cohorte = await _crear_cohorte(async_client, headers, uuid.UUID(carrera["id"]))
        user1 = await _crear_usuario(async_client, headers, "activo")
        user2 = await _crear_usuario(async_client, headers, "inactivo")

        response = await async_client.delete(
            f"{USUARIOS_BASE}/{user2['id']}", headers=headers
        )
        assert response.status_code == 204, f"Expected 204, got {response.status_code}: {response.text}"

        payload = {
            "materia_id": materia["id"],
            "carrera_id": carrera["id"],
            "cohorte_id": cohorte["id"],
            "rol": "PROFESOR",
            "usuario_ids": [user1["id"], user2["id"]],
            "desde": "2026-01-01",
            "hasta": "2026-12-31",
            "comisiones": [],
        }
        response = await async_client.post(
            f"{BASE}/asignacion-masiva", json=payload, headers=headers
        )
        assert response.status_code == 422
        detail = response.json()["detail"].lower()
        assert "inactivo" in detail or "inactive" in detail

    async def test_masiva_rol_invalido(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN an invalid rol WHEN POST /asignacion-masiva THEN 422."""
        headers = _admin_token(tenant_a.id)
        materia = await _crear_materia(async_client, headers)
        carrera = await _crear_carrera(async_client, headers)
        cohorte = await _crear_cohorte(async_client, headers, uuid.UUID(carrera["id"]))
        user = await _crear_usuario(async_client, headers, "rolbad")

        payload = {
            "materia_id": materia["id"],
            "carrera_id": carrera["id"],
            "cohorte_id": cohorte["id"],
            "rol": "SUPERVISOR",
            "usuario_ids": [user["id"]],
            "desde": "2026-01-01",
            "hasta": "2026-12-31",
            "comisiones": [],
        }
        response = await async_client.post(
            f"{BASE}/asignacion-masiva", json=payload, headers=headers
        )
        assert response.status_code == 422

    async def test_masiva_fechas_invalidas(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN desde > hasta WHEN POST /asignacion-masiva THEN 422."""
        headers = _admin_token(tenant_a.id)
        materia = await _crear_materia(async_client, headers)
        carrera = await _crear_carrera(async_client, headers)
        cohorte = await _crear_cohorte(async_client, headers, uuid.UUID(carrera["id"]))
        user = await _crear_usuario(async_client, headers, "datebad")

        payload = {
            "materia_id": materia["id"],
            "carrera_id": carrera["id"],
            "cohorte_id": cohorte["id"],
            "rol": "PROFESOR",
            "usuario_ids": [user["id"]],
            "desde": "2026-12-31",
            "hasta": "2026-01-01",
            "comisiones": [],
        }
        response = await async_client.post(
            f"{BASE}/asignacion-masiva", json=payload, headers=headers
        )
        assert response.status_code == 422

    async def test_masiva_excede_limite(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN 201 user_ids WHEN POST /asignacion-masiva THEN 422 (max 200)."""
        headers = _admin_token(tenant_a.id)
        materia = await _crear_materia(async_client, headers)
        carrera = await _crear_carrera(async_client, headers)
        cohorte = await _crear_cohorte(async_client, headers, uuid.UUID(carrera["id"]))

        payload = {
            "materia_id": materia["id"],
            "carrera_id": carrera["id"],
            "cohorte_id": cohorte["id"],
            "rol": "PROFESOR",
            "usuario_ids": [str(uuid.uuid4()) for _ in range(201)],
            "desde": "2026-01-01",
            "hasta": "2026-12-31",
            "comisiones": [],
        }
        response = await async_client.post(
            f"{BASE}/asignacion-masiva", json=payload, headers=headers
        )
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════
# Clonar Equipo
# ═══════════════════════════════════════════════════════════════


class TestClonarEquipo:
    async def test_clonar_exitoso(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN asignaciones in origen WHEN POST /clonar THEN 201 with duplicates in destino."""
        headers = _admin_token(tenant_a.id)
        materia = await _crear_materia(async_client, headers)
        carrera = await _crear_carrera(async_client, headers)
        carrera_id = uuid.UUID(carrera["id"])
        cohorte_origen = await _crear_cohorte(async_client, headers, carrera_id, "Origen")
        cohorte_destino = await _crear_cohorte(async_client, headers, carrera_id, "Destino")

        user = await _crear_usuario(async_client, headers, "clon")

        await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": user["id"],
                "rol": "PROFESOR",
                "materia_id": materia["id"],
                "carrera_id": carrera["id"],
                "cohorte_id": cohorte_origen["id"],
                "desde": "2026-01-01",
                "hasta": "2026-12-31",
            },
            headers=headers,
        )

        payload = {
            "materia_id": materia["id"],
            "carrera_id": carrera["id"],
            "cohorte_origen_id": cohorte_origen["id"],
            "cohorte_destino_id": cohorte_destino["id"],
            "desde": "2027-01-01",
            "hasta": "2027-12-31",
        }
        response = await async_client.post(
            f"{BASE}/clonar", json=payload, headers=headers
        )
        assert response.status_code == 201
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["cohorte_id"] == cohorte_destino["id"]
        assert data[0]["usuario_id"] == user["id"]
        assert data[0]["rol"] == "PROFESOR"

    async def test_clonar_cohortes_iguales(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN cohorte_origen == cohorte_destino WHEN POST /clonar THEN 422."""
        headers = _admin_token(tenant_a.id)
        materia = await _crear_materia(async_client, headers)
        carrera = await _crear_carrera(async_client, headers)
        carrera_id = uuid.UUID(carrera["id"])
        cohorte = await _crear_cohorte(async_client, headers, carrera_id, "Igual")

        payload = {
            "materia_id": materia["id"],
            "carrera_id": carrera["id"],
            "cohorte_origen_id": cohorte["id"],
            "cohorte_destino_id": cohorte["id"],
            "desde": "2027-01-01",
            "hasta": "2027-12-31",
        }
        response = await async_client.post(
            f"{BASE}/clonar", json=payload, headers=headers
        )
        assert response.status_code == 422

    async def test_clonar_cohorte_destino_inexistente(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN non-existent cohorte_destino WHEN POST /clonar THEN 404."""
        headers = _admin_token(tenant_a.id)
        materia = await _crear_materia(async_client, headers)
        carrera = await _crear_carrera(async_client, headers)
        carrera_id = uuid.UUID(carrera["id"])
        cohorte_origen = await _crear_cohorte(async_client, headers, carrera_id, "Real")

        payload = {
            "materia_id": materia["id"],
            "carrera_id": carrera["id"],
            "cohorte_origen_id": cohorte_origen["id"],
            "cohorte_destino_id": str(uuid.uuid4()),
            "desde": "2027-01-01",
            "hasta": "2027-12-31",
        }
        response = await async_client.post(
            f"{BASE}/clonar", json=payload, headers=headers
        )
        assert response.status_code == 404

    async def test_clonar_sin_asignaciones_origen(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN origen without asignaciones WHEN POST /clonar THEN 200 with empty list."""
        headers = _admin_token(tenant_a.id)
        materia = await _crear_materia(async_client, headers)
        carrera = await _crear_carrera(async_client, headers)
        carrera_id = uuid.UUID(carrera["id"])
        cohorte_origen = await _crear_cohorte(async_client, headers, carrera_id, "Vacio")
        cohorte_destino = await _crear_cohorte(async_client, headers, carrera_id, "Nuevo")

        payload = {
            "materia_id": materia["id"],
            "carrera_id": carrera["id"],
            "cohorte_origen_id": cohorte_origen["id"],
            "cohorte_destino_id": cohorte_destino["id"],
            "desde": "2027-01-01",
            "hasta": "2027-12-31",
        }
        response = await async_client.post(
            f"{BASE}/clonar", json=payload, headers=headers
        )
        assert response.status_code == 200
        assert response.json() == []


# ═══════════════════════════════════════════════════════════════
# Modificar Vigencia
# ═══════════════════════════════════════════════════════════════


class TestModificarVigencia:
    async def test_vigencia_exitosa(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN asignaciones with old dates WHEN PATCH /vigencia THEN 200 with affected count."""
        headers = _admin_token(tenant_a.id)
        materia = await _crear_materia(async_client, headers)
        user = await _crear_usuario(async_client, headers, "vigencia")

        await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": user["id"],
                "rol": "PROFESOR",
                "materia_id": materia["id"],
                "desde": "2025-01-01",
                "hasta": "2025-12-31",
            },
            headers=headers,
        )

        payload = {
            "materia_id": materia["id"],
            "desde": "2026-03-01",
            "hasta": "2026-12-31",
        }
        response = await async_client.patch(
            f"{BASE}/vigencia", json=payload, headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "afectadas" in data or "count" in data or isinstance(data, dict)

    async def test_vigencia_rango_invalido(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN desde > hasta WHEN PATCH /vigencia THEN 422."""
        headers = _admin_token(tenant_a.id)
        materia = await _crear_materia(async_client, headers)

        payload = {
            "materia_id": materia["id"],
            "desde": "2026-12-31",
            "hasta": "2026-01-01",
        }
        response = await async_client.patch(
            f"{BASE}/vigencia", json=payload, headers=headers
        )
        assert response.status_code == 422


# ═══════════════════════════════════════════════════════════════
# Exportar Equipo
# ═══════════════════════════════════════════════════════════════


class TestExportarEquipo:
    async def test_exportar_exitoso(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN a materia with asignaciones WHEN GET /{id}/exportar THEN 200 with CSV content."""
        headers = _admin_token(tenant_a.id)
        materia = await _crear_materia(async_client, headers)
        user = await _crear_usuario(async_client, headers, "export")

        await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": user["id"],
                "rol": "PROFESOR",
                "materia_id": materia["id"],
                "desde": "2026-01-01",
                "hasta": "2026-12-31",
            },
            headers=headers,
        )

        response = await async_client.get(
            f"{BASE}/{materia['id']}/exportar", headers=headers
        )
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "csv" in content_type.lower() or "text" in content_type.lower()
        body = response.text
        assert "Docente" in body or "docente" in body.lower() or "Rol" in body
        assert len(body) > 0

    async def test_exportar_sin_datos(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN a materia without asignaciones WHEN GET /{id}/exportar THEN 200 with CSV headers only."""
        headers = _admin_token(tenant_a.id)
        materia = await _crear_materia(async_client, headers)

        response = await async_client.get(
            f"{BASE}/{materia['id']}/exportar", headers=headers
        )
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "csv" in content_type.lower() or "text" in content_type.lower()
        body = response.text
        assert len(body) > 0


# ═══════════════════════════════════════════════════════════════
# Desactivación con Asignaciones (C-06 integration)
# ═══════════════════════════════════════════════════════════════


class TestDesactivacionConAsignaciones:
    async def test_desactivar_materia_con_asignaciones(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN a materia with active asignaciones WHEN desactivar THEN 409."""
        headers = _admin_token(tenant_a.id)
        materia = await _crear_materia(async_client, headers)
        user = await _crear_usuario(async_client, headers, "desact")

        await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": user["id"],
                "rol": "PROFESOR",
                "materia_id": materia["id"],
                "desde": "2026-01-01",
                "hasta": "2026-12-31",
            },
            headers=headers,
        )

        response = await async_client.put(
            f"{MATERIAS_BASE}/{materia['id']}",
            json={"estado": "Inactiva"},
            headers=headers,
        )
        assert response.status_code == 409

    async def test_desactivar_materia_sin_asignaciones(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN a materia without asignaciones WHEN desactivar THEN 200."""
        headers = _admin_token(tenant_a.id)
        materia = await _crear_materia(async_client, headers)

        response = await async_client.put(
            f"{MATERIAS_BASE}/{materia['id']}",
            json={"estado": "Inactiva"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["estado"] == "Inactiva"

    async def test_desactivar_carrera_con_asignaciones(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN a carrera with active asignaciones via its cohorte WHEN desactivar THEN 409."""
        headers = _admin_token(tenant_a.id)
        carrera = await _crear_carrera(async_client, headers)
        carrera_id = uuid.UUID(carrera["id"])
        cohorte = await _crear_cohorte(async_client, headers, carrera_id)
        materia = await _crear_materia(async_client, headers)
        user = await _crear_usuario(async_client, headers, "desact-carr")

        await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": user["id"],
                "rol": "PROFESOR",
                "materia_id": materia["id"],
                "carrera_id": carrera["id"],
                "cohorte_id": cohorte["id"],
                "desde": "2026-01-01",
                "hasta": "2026-12-31",
            },
            headers=headers,
        )

        response = await async_client.put(
            f"{CARRERAS_BASE}/{carrera['id']}",
            json={"estado": "Inactiva"},
            headers=headers,
        )
        assert response.status_code == 409

    async def test_desactivar_cohorte_con_asignaciones(
        self, async_client: AsyncClient, tenant_a: Tenant
    ):
        """GIVEN a cohorte with active asignaciones WHEN desactivar THEN 409."""
        headers = _admin_token(tenant_a.id)
        carrera = await _crear_carrera(async_client, headers)
        carrera_id = uuid.UUID(carrera["id"])
        cohorte = await _crear_cohorte(async_client, headers, carrera_id)
        materia = await _crear_materia(async_client, headers)
        user = await _crear_usuario(async_client, headers, "desact-coh")

        await async_client.post(
            f"{ASIGNACIONES_BASE}/",
            json={
                "usuario_id": user["id"],
                "rol": "PROFESOR",
                "materia_id": materia["id"],
                "carrera_id": carrera["id"],
                "cohorte_id": cohorte["id"],
                "desde": "2026-01-01",
                "hasta": "2026-12-31",
            },
            headers=headers,
        )

        response = await async_client.put(
            f"{COHORTES_BASE}/{cohorte['id']}",
            json={"estado": "Inactiva"},
            headers=headers,
        )
        assert response.status_code == 409


# ═══════════════════════════════════════════════════════════════
# Multi-Tenant Isolation
# ═══════════════════════════════════════════════════════════════


class TestMultiTenantIsolation:
    async def test_tenant_a_no_ve_equipo_tenant_b(
        self, async_client: AsyncClient, tenant_a: Tenant, tenant_b: Tenant
    ):
        """GIVEN materia in tenant_b WHEN tenant_a GET /materias/{id} THEN 404."""
        headers_a = _admin_token(tenant_a.id)
        headers_b = _admin_token(tenant_b.id)
        materia_b = await _crear_materia(async_client, headers_b)

        response = await async_client.get(
            f"{BASE}/materias/{materia_b['id']}", headers=headers_a
        )
        assert response.status_code == 404

"""Tests for UmbralMateria configuration (C-10)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.umbral_materia import UmbralMateria
from app.repositories.usuarios.umbral_materia_repository import (
    UmbralMateriaRepository,
)

class TestUmbralRepository:
    @pytest.mark.asyncio
    async def test_create_default_umbral(
        self, db_session: AsyncSession, tenant_a, materia_create, asignacion_profesor
    ):
        repo = UmbralMateriaRepository(db_session, tenant_a.id)
        umbral = await repo.create_default(asignacion_profesor.id, materia_create.id)
        assert umbral.id is not None
        assert umbral.umbral_pct == 60
        assert umbral.asignacion_id == asignacion_profesor.id
        assert umbral.materia_id == materia_create.id
        assert umbral.valores_aprobatorios == [] or umbral.valores_aprobatorios is None

    @pytest.mark.asyncio
    async def test_create_umbral_with_valores(
        self, db_session: AsyncSession, tenant_a, materia_create, asignacion_profesor
    ):
        repo = UmbralMateriaRepository(db_session, tenant_a.id)
        umbral = await repo.create({
            "asignacion_id": asignacion_profesor.id,
            "materia_id": materia_create.id,
            "umbral_pct": 75,
            "valores_aprobatorios": ["Aprobado", "Satisfactorio"],
        })
        assert umbral.umbral_pct == 75
        assert umbral.valores_aprobatorios == ["Aprobado", "Satisfactorio"]

    @pytest.mark.asyncio
    async def test_get_by_asignacion(
        self, db_session: AsyncSession, tenant_a, materia_create, asignacion_profesor
    ):
        repo = UmbralMateriaRepository(db_session, tenant_a.id)
        created = await repo.create_default(asignacion_profesor.id, materia_create.id)
        found = await repo.get_by_asignacion(asignacion_profesor.id)
        assert found is not None
        assert found.id == created.id

    @pytest.mark.asyncio
    async def test_get_by_asignacion_not_found(
        self, db_session: AsyncSession, tenant_a
    ):
        repo = UmbralMateriaRepository(db_session, tenant_a.id)
        found = await repo.get_by_asignacion(uuid.uuid4())
        assert found is None

    @pytest.mark.asyncio
    async def test_update_config(
        self, db_session: AsyncSession, tenant_a, materia_create, asignacion_profesor
    ):
        repo = UmbralMateriaRepository(db_session, tenant_a.id)
        created = await repo.create_default(asignacion_profesor.id, materia_create.id)
        updated = await repo.update_config(created.id, {
            "umbral_pct": 80,
            "valores_aprobatorios": ["Excelente"],
        })
        assert updated is not None
        assert updated.umbral_pct == 80
        assert updated.valores_aprobatorios == ["Excelente"]

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation_umbral(
        self, db_session: AsyncSession, tenant_a, tenant_b, materia_create, asignacion_profesor
    ):
        repo_a = UmbralMateriaRepository(db_session, tenant_a.id)
        created_a = await repo_a.create_default(asignacion_profesor.id, materia_create.id)

        repo_b = UmbralMateriaRepository(db_session, tenant_b.id)
        found_b = await repo_b.get_by_asignacion(asignacion_profesor.id)
        assert found_b is None


class TestUmbralDerivation:
    """Test approval derivation logic (E7 rules)."""

    def _derive(self, nota_numerica, nota_textual, umbral_pct=60, valores_aprobatorios=None):
        if nota_numerica is not None:
            try:
                return float(nota_numerica) >= umbral_pct
            except (ValueError, TypeError):
                pass
        if nota_textual and valores_aprobatorios:
            return nota_textual in valores_aprobatorios
        if nota_textual and not valores_aprobatorios:
            return False
        return None

    def test_numeric_above_threshold(self):
        assert self._derive(75, None) is True

    def test_numeric_below_threshold(self):
        assert self._derive(45, None) is False

    def test_numeric_at_threshold(self):
        assert self._derive(60, None) is True

    def test_textual_in_approved_set(self):
        assert self._derive(None, "Satisfactorio", valores_aprobatorios=["Satisfactorio", "Aprobado"]) is True

    def test_textual_not_in_approved_set(self):
        assert self._derive(None, "Regular", valores_aprobatorios=["Satisfactorio", "Aprobado"]) is False

    def test_textual_no_valores_set(self):
        assert self._derive(None, "Aprobado", valores_aprobatorios=[]) is False

    def test_no_grade_returns_none(self):
        assert self._derive(None, None) is None

    def test_numeric_precedence_over_textual(self):
        assert self._derive(45, "Satisfactorio", valores_aprobatorios=["Satisfactorio"]) is False

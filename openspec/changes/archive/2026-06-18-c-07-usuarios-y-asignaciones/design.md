## Context

C-07 es el sexto change del camino crítico. Depende de C-06 (estructura-academica) que ya implementó `Carrera`, `Cohorte` y `Materia`. El sistema actual tiene:

- Multi-tenancy row-level con `BaseRepository` que filtra por `tenant_id` automáticamente
- RBAC fino con `require_permission("modulo:accion")` y 7 roles seed
- Cifrado AES-256-GCM vía `AESCipher` en `app/core/security.py`
- `BaseModel` con UUID PK, timestamps y soft delete

C-07 introduce dos entidades fundamentales: `Usuario` (identidad académica con PII cifrada) y `Asignacion` (vinculación usuario ↔ rol ↔ contexto académico con vigencia). Todo módulo posterior (equipos, padrón, encuentros, comunicaciones, liquidaciones) depende de estas entidades.

## Goals / Non-Goals

**Goals:**
- Modelar `Usuario` con identidad por UUID interno, PII cifrada en reposo, y legajo como atributo de negocio
- Modelar `Asignacion` como el mecanismo que otorga un rol a un usuario sobre un contexto académico (materia, carrera, cohorte, comisiones), con vigencia temporal y jerarquía responsable
- Proveer ABM de usuarios (`/api/admin/usuarios`) con guard `usuarios:gestionar` (solo ADMIN)
- Proveer ABM de asignaciones (`/api/asignaciones`) con guard `equipos:asignar` (COORDINADOR, ADMIN)
- Agregar permisos `usuarios:gestionar` y `equipos:asignar` a la matriz RBAC
- Asegurar que PII cifrada nunca se exponga en logs, respuestas API ni trazas

**Non-Goals:**
- Gestión de equipos docentes (asignación masiva, clonado, export) — será C-08
- Sincronización con Moodle de usuarios — será C-09
- Import masivo de usuarios desde archivo — será C-09
- Perfil de usuario (edición propia, cambio de datos) — será C-20
- Frontend de administración de usuarios — será C-24

## Decisions

### D1: Búsqueda por email mediante hash HMAC-SHA256

**Decisión**: Agregar columna `email_hash` (no nullable, unique junto a tenant_id) calculada como `HMAC-SHA256(email, key_derivada)` para permitir búsqueda determinística por email sin comprometer el cifrado AES-256-GCM.

**Alternativas consideradas**:
1. **Cifrado determinístico (AES-SIV)**: Permite `WHERE` directo sobre columna cifrada pero reduce seguridad (mismo texto → mismo cifrado, revela patrones).
2. **Descifrar en memoria y filtrar**: No escala para listados grandes.
3. **Solo hash (sin cifrado)**: El email sería buscable pero no reversible — no cumple requerimiento de PII cifrada en reposo.

**Razón**: HMAC-SHA256 con key derivada del `ENCRYPTION_KEY` principal ofrece búsqueda O(1) sin revelar el email plano ni permitir rainbow tables. La key del HMAC es una derivación determinística (HKDF) de la key principal, no la key misma, por si ambas columnas quedan expuestas.

### D2: Estado vigencia derivado, no almacenado

**Decisión**: `estado_vigencia` se calcula en tiempo de consulta comparando `desde`/`hasta` contra la fecha actual. No se persiste en DB. En responses API se incluye como campo calculado.

**Razón**: La vigencia es una función determinística de `(desde, hasta, hoy)`. Almacenarla requeriría un job diario o trigger para mantenerla sincronizada y agregaría complejidad sin beneficio. La fórmula `desde <= CURRENT_DATE AND (hasta IS NULL OR hasta >= CURRENT_DATE)` es eficiente con índices compuestos en `(tenant_id, desde, hasta)`.

### D3: `comisiones` como JSONB

**Decisión**: El campo `comisiones` en `Asignacion` se modela como `JSONB` en PostgreSQL (lista de strings).

**Razón**: JSONB es el estándar del proyecto (ya usado en `Tenant.config`), soporta indexing, y una lista de strings variable por asignación no justifica una tabla normalizada separada. El tipo `ARRAY[TEXT]` de PG es menos flexible para evolución futura.

### D4: Reutilización de AESCipher existente

**Decisión**: Se reutiliza la clase `AESCipher` de `app/core/security.py` para cifrar los campos PII de `Usuario`. No se crea un nuevo módulo de cifrado.

**Razón**: La implementación actual AES-256-GCM es correcta, está testeada y es la misma que se usará para cifrar `destinatario` en comunicaciones (C-12). Centralizar el cifrado evita duplicación y asegura consistencia.

### D5: Desactivación de usuario no cierra asignaciones automáticamente

**Decisión**: Al desactivar un usuario (`estado = Inactivo`), las asignaciones vigentes quedan intactas en la DB. El guard de permisos verifica `Usuario.estado = Activo` antes de considerar cualquier asignación como válida. Esto evita side effects automáticos y mantiene el histórico de asignaciones sin mutación.

**Alternativa considerada**: Cerrar asignaciones automáticamente (poner `hasta = today`). Descartado porque pierde la traza de la asignación original y complica el clonado entre períodos (C-08).

### D6: Permisos nuevos via migración Alembic separada

**Decisión**: Los permisos `usuarios:gestionar` y `equipos:asignar` se agregan en la migración 006 (no se modifica la migración 003 existente).

**Razón**: Las migraciones Alembic son inmutables una vez aplicadas. Modificar la 003 rompería la cadena de revisiones en entornos donde ya se ejecutó. La migración 006 hará `INSERT INTO permiso ...` y `INSERT INTO rol_permiso ...` con los nuevos permisos asignados a los roles correspondientes (ADMIN para ambos; COORDINADOR solo para `equipos:asignar`).

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|-----------|
| **Falso positivo en búsqueda por email_hash**: colisión de HMAC-SHA256 (teórica) | HMAC-SHA256 tiene probabilidad de colisión despreciable. Si ocurriera, el cifrado AES-GCM descifraría correctamente solo el email que coincide — el falso positivo se descarta post-descifrado. |
| **Rendimiento en listados con descifrado**: si un listado de 1000 usuarios requiere descifrar todos los emails para mostrarlos | El overhead de AES-256-GCM es ~1μs por descifrado. 1000 usuarios = ~1ms. No es cuello de botella. Si escala a decenas de miles, se puede cachear en Redis. |
| **Exposición accidental de PII en logs**: un `logger.debug(usuario)` imprimiría los campos cifrados como bytes | Los modelos SQLAlchemy deben tener un `__repr__` que excluya campos PII. Los schemas Pydantic no deben incluir campos cifrados en responses que los expongan en texto plano. |
| **Asignaciones huérfanas**: si se elimina (soft-delete) una materia/carrera/cohorte referenciada por asignaciones activas | Las FKs tienen `ON DELETE` restrictivo. Para soft-delete, el service de estructura (C-06) debe verificar que no haya asignaciones activas antes de desactivar, o manejar la desactivación en cascada. Esto se aborda en C-08 (equipos-docentes) que gestiona el ciclo de vida de asignaciones. |

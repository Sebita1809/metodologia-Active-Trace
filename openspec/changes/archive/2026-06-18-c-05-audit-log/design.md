## Context

C-04 (RBAC) está archivado: los roles, permisos y el guard `require_permission` están implementados. Los permisos `auditoria:ver` e `impersonacion:usar` ya existen en el seed. Pero no hay ningún registro de acciones — cualquier operación significativa (importar calificaciones, enviar comunicaciones, modificar equipos) ocurre sin trazabilidad.

El archivo `app/core/exceptions.py` está reservado como placeholder. No existe ningún helper de auditoría ni catálogo de códigos de acción.

C-05 es el cimiento de trazabilidad del sistema. Todos los changes de dominio (C-06 a C-18) generarán registros de auditoría usando lo que construye C-05. Por eso se diseña como un servicio simple y desacoplado, no un middleware mágico.

## Goals / Non-Goals

**Goals:**
- Modelo `AuditLog` append-only con inmutabilidad a nivel app (repository sin update/delete) y DB (trigger que rechaza UPDATE/DELETE)
- Helper `audit_record()` que cualquier service pueda llamar con: acción, actor_id, impersonado_id (opcional), materia_id (opcional), detalle (dict opcional), filas_afectadas (opcional), más IP y user_agent extraídos automáticamente del request
- Catálogo de códigos de acción como enum `AuditAction` con los 7 códigos iniciales
- Sistema de impersonación: endpoints para iniciar/finalizar, sesión JWT distinguible, registro obligatorio en AuditLog
- Integración con `get_current_user` para que los endpoints de impersonación obtengan el contexto actual
- Resolución de `impersonado_id` como metadata en el UserContext cuando hay impersonación activa
- Tests: append-only (rechazo de update/delete con pytest), atribución bajo impersonación, registro con código + filas afectadas

**Non-Goals:**
- CRUD de audit-log (nadie edita ni borra — es append-only)
- Panel de visualización de auditoría (será C-19 panel-auditoria-metricas)
- Catálogo administrable de códigos de acción vía API (se define como enum; si se necesita administrable será en un change futuro)
- Particionamiento automático de la tabla (se implementa como tabla única; si escala se particiona post-MVP)
- Cache de auditoría (cada registro se escribe síncrono; si hay problemas de performance se evalúa cola asíncrona después)

## Decisions

### D1 — Helper explícito desde services, no decorador ni middleware
El helper `audit_record()` es una función async que los services llaman explícitamente después de cada operación significativa.

**Alternativas consideradas:**
- *Decorador en routers*: Requiere metadata de la acción en el decorador, difícil de pasar datos dinámicos como filas_afectadas.
- *Middleware automático*: Capturaría requests HTTP pero no actions internas (workers, tareas batch), y no sabe qué acción de negocio ocurrió.

**Decisión**: Helper explícito desde services. Más verboso pero más predecible y funciona en cualquier contexto (HTTP, worker, CLI).

### D2 — `audit_record()` en `app/services/audit/audit_service.py`
El helper vive en services (no en core) porque depende del modelo AuditLog y del repositorio. Es una función independiente (no una clase) que recibe parámetros con nombres explícitos:

```python
async def audit_record(
    db: AsyncSession,
    actor_id: uuid.UUID,
    accion: AuditAction,
    *,
    tenant_id: uuid.UUID,
    impersonado_id: uuid.UUID | None = None,
    materia_id: uuid.UUID | None = None,
    detalle: dict | None = None,
    filas_afectadas: int | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
```

Esto permite que cualquier service la llame con `await audit_record(db=..., ...)`.

### D3 — IP y user_agent extraídos del request vía dependency
Se crea una dependencia `get_request_metadata(request: Request)` que extrae IP y User-Agent. El router los pasa al service, y el service los pasa al helper. Así el helper no depende de Starlette/FastAPI.

### D4 — Append-only enforcement en dos capas
- **App**: Repository de AuditLog solo expone `add()` y `list()` — sin `update()` ni `delete()`. El modelo no tiene `deleted_at` (no aplica soft-delete al audit-log).
- **DB**: Trigger `before update` / `before delete` en `audit_log` que rechaza la operación. Como defensa adicional, el usuario de la app no tiene permisos UPDATE/DELETE sobre la tabla.

### D5 — Impersonación como tipo de sesión en JWT
El JWT existente tiene un campo `type` que hoy puede ser `"access"` o `"temp_session"`. Se agrega el tipo `"impersonation"` con dos claims extra:
- `actor_id`: UUID del usuario real que impersona
- `impersonado_id`: UUID del usuario siendo impersonado

El `UserContext` se extiende para incluir estos campos cuando `type == "impersonation"`:

```python
class UserContext(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    roles: list[str]
    is_impersonating: bool = False
    actor_id: uuid.UUID | None = None
    impersonated_user_id: uuid.UUID | None = None
```

### D6 — materia_id como UUID simple sin FK
El modelo AuditLog tiene `materia_id` como columna UUID nullable, pero **sin ForeignKey** a `materia`. La entidad Materia se crea en C-06 y la FK generaría una dependencia cíclica (C-06 depende de C-05 para auditar, C-05 depende de C-06 para la FK). En su lugar, `materia_id` es un identificador lógico que se resuelve en C-19 (panel de auditoría) con un JOIN explícito.

### D7 — El catálogo de códigos es un enum, no una tabla
Los 7 códigos iniciales se definen como `enum.StrEnum` (`AuditAction`). Esto permite type-checking y autocompletado. Si en el futuro se necesita un catálogo administrable vía API, se migra a tabla con un change dedicado.

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|------------|
| **Escritura síncrona en cada acción significativa agrega latencia** | El insert es sobre una tabla sin FKs complejas (solo `actor_id` lógico) y con un índice mínimo. Si la tabla crece, se agrega particionado por mes. |
| **Trigger de append-only en DB puede ser esquivado por conexiones con permisos elevados** | El trigger es una defensa secundaria. La defensa primaria es que la app nunca ejecuta UPDATE/DELETE. El trigger cubre el caso de acceso directo a DB. |
| **Impersonación mal implementada permite escalada de privilegios** | Solo usuarios con `impersonacion:usar` pueden iniciarla. La sesión es explícita y distinguible. Toda acción queda atribuida al actor real. Auditoría obligatoria de cada inicio/fin. |
| **materia_id sin FK puede derivar en datos huérfanos** | Es intencional — Materia se crea en C-06. En C-19 se valida la integridad referencial al consultar. Si se elimina una materia (soft-delete), los registros de auditoría referentes a ella se conservan. |
| **Crecimiento infinito de la tabla audit_log** | Sin límite de retención por diseño (RN-23). Se agrega índice compuesto por `(tenant_id, fecha_hora)` para queries eficientes. Si el tamaño es problema post-MVP, se particiona por fecha. |

## Migration Plan

1. Crear modelo `AuditLog` y migración 004
2. Aplicar migración: `alembic upgrade head`
3. Ejecutar script SQL para crear el trigger de append-only
4. Verificar que el trigger rechaza UPDATE/DELETE
5. Crear helper `audit_record()` y enum `AuditAction`
6. Crear endpoints de impersonación
7. Extender `create_session()` para soportar tipo `impersonation`
8. Tests

Rollback: `alembic downgrade -1` + eliminar trigger manualmente.

## Open Questions

- **¿El trigger append-only se implementa como función PL/pgSQL o como regla de Fila (ROW LEVEL SECURITY)?** — La trigger function es más compatible y no depende del rol de conexión. Se implementa como `CREATE OR REPLACE FUNCTION reject_modify()` con `BEFORE UPDATE OR DELETE` y `RAISE EXCEPTION`.
- **¿Los índices adicionales además de `(tenant_id, fecha_hora)`?** — Se agrega índice en `actor_id` para queries de "acciones de un usuario" y en `accion` para filtrado por tipo.

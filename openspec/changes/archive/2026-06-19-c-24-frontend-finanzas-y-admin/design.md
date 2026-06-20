## Context

C-24 cierra el frontend de la plataforma. El backend está 100% operativo desde C-06, C-07, C-17, C-18 y C-19. El shell (C-21), la feature de gestión académica del docente (C-22) y la feature de coordinación (C-23) ya existen. C-24 agrega las features FINANZAS, ADMIN y AUDITORÍA — las tres son mayormente read-heavy con algunas operaciones de escritura críticas (cierre de liquidación, ABM de usuarios, ABM de estructura).

## Goals / Non-Goals

**Goals:**
- UI completa para FINANZAS: liquidaciones segmentadas, cierre, historial, grilla salarial, facturas
- UI completa para ADMIN: estructura académica (carreras/cohortes/materias), usuarios del tenant, programas, fechas de evaluaciones
- Panel de auditoría para COORDINADOR/ADMIN + log completo para ADMIN
- Completar todas las entradas de nav faltantes

**Non-Goals:**
- Ningún cambio de backend — todos los endpoints ya existen
- Módulo de corrección asistida por IA (F12.1, externo al scope)
- Gestión de tenants a nivel plataforma (operación de infraestructura, no UI de tenant)

## Decisions

### 1 — Feature FINANZAS separada de ADMIN

`features/finanzas/` y `features/admin/` son features independientes con guards distintos. FINANZAS ve liquidaciones y facturas; ADMIN ve estructura y usuarios. Aunque ADMIN puede ver liquidaciones como read-only, la escritura (cerrar, configurar salarios) es exclusiva de FINANZAS.

**Razón**: mantener el principio de mínimo privilegio en la UI — no mezclar permisos de escritura financiera con permisos de estructura académica en un solo guard.

### 2 — Cierre de liquidación: acción destructiva con doble confirmación

`POST /api/v1/liquidaciones/{periodo}/cerrar` es **irreversible** (RN-22). La UI DEBE mostrar un diálogo de confirmación con el texto explícito del período y el total a cerrar antes de ejecutar la acción.

**Razón**: RN-22 es explícito — liquidación cerrada no puede modificarse. Un cierre accidental no tiene rollback.

### 3 — Datos bancarios (CBU/alias): el frontend no los manipula

Los campos `cbu` y `alias` de usuarios vienen cifrados del backend. El frontend los muestra como texto plano en la UI (el backend descifra antes de responder) pero **nunca los envía en query strings ni params de URL** — solo en el body de POST/PUT sobre HTTPS.

**Razón**: Regla dura #12 — PII y datos bancarios con AES-256 en reposo. El transporte siempre es HTTPS; la exposición en URLs violaría logs de acceso.

### 4 — Auditoría: gráfico de acciones por día con librería ligera

El panel F9.1 requiere un gráfico de serie temporal (acciones por día). Usar el componente SVG nativo de React o una librería ya presente en el proyecto (`recharts` si está instalada). **No agregar nuevas dependencias pesadas** sin verificar `package.json` primero.

**Razón**: el proyecto ya tiene dependencias definidas; agregar Chart.js o D3 sin aprobación viola el principio de no introducir dependencias no acordadas.

### 5 — Programas de materia: upload de archivo PDF/DOCX

F5.3 sube un "documento de programa oficial". El frontend envía el archivo via `multipart/form-data` igual que en C-22 (importación de calificaciones). El campo `archivo` es binario; `titulo`, `carrera_id`, `cohorte_id` van como JSON en el mismo form o como campos adicionales del multipart — verificar el router `programas.py` antes de implementar.

### 6 — Endpoints a consumir por módulo

| Feature | Endpoints clave |
|---------|----------------|
| Liquidaciones | `GET /api/v1/liquidaciones?cohorte_id=&mes=&docente_id=`, `POST /api/v1/liquidaciones/{id}/cerrar`, `GET /api/v1/liquidaciones/historial` |
| Grilla salarial | `GET/POST/PUT/DELETE /api/v1/liquidaciones/salarios-base`, `GET/POST/PUT/DELETE /api/v1/liquidaciones/plus` |
| Facturas | `GET/POST/PUT/DELETE /api/v1/facturas` |
| Carreras | `GET/POST/PUT /api/v1/carreras` |
| Cohortes | `GET/POST/PUT /api/v1/cohortes` |
| Usuarios | `GET/POST/PUT /api/v1/usuarios` |
| Programas | `GET/POST /api/v1/programas` |
| Fechas académicas | `GET/POST/PUT /api/v1/fechas-academicas` |
| Auditoría | `GET /api/v1/auditoria/panel`, `GET /api/v1/auditoria/log` |

> **IMPORTANTE**: verificar los paths exactos leyendo cada router antes de implementar los services. Los paths listados son los esperados según el diseño de C-18/C-19 pero pueden diferir.

## Risks / Trade-offs

- [Cierre irreversible de liquidación] La acción de cierre no tiene rollback → mitigation: doble confirmación con datos del período en el diálogo.
- [Gráfico de auditoría] Si no hay librería de charts disponible, usar barras CSS (Tailwind) como fallback — no bloquear la feature por falta de dependencia.
- [Upload de programas] El multipart puede diferir del patrón de C-22 — el agente debe leer `programas.py` antes de implementar.
- [Usuarios con PII] El ABM de usuarios incluye CBU/alias — el agente debe nunca enviar estos campos en query strings.

## Open Questions

- **Gráfico de auditoría**: ¿hay alguna librería de charts ya instalada en `frontend/package.json`? El agente debe verificarlo antes de decidir el componente.
- **Path de salarios base y plus**: ¿son sub-rutas de `/liquidaciones/` o tienen prefijo propio? Verificar `liquidaciones.py` y `facturas.py`.
- **Exportar liquidación**: ¿el endpoint devuelve un CSV blob o genera una URL de descarga? Verificar el router.

## ADDED Requirements

### Requirement: Panel de interacciones del sistema

La feature SHALL presentar el panel de métricas de auditoría con filtros por rango de fechas, materia, usuario y estado de actividad, consumiendo `GET /api/v1/auditoria/panel` (verificar path exacto). Accesible a COORDINADOR y ADMIN con permiso `auditoria:ver`. Implementa F9.1 y FL-11.

#### Scenario: Ver panel con métricas
- **WHEN** el COORDINADOR accede al panel de auditoría sin filtros
- **THEN** la UI muestra: (1) gráfico de acciones por día, (2) tabla de estado de comunicaciones por docente, (3) tabla de interacciones por docente y materia, (4) log de últimas 200 acciones

#### Scenario: Filtrar por rango de fechas
- **WHEN** el usuario filtra por rango "julio 2025 – agosto 2025"
- **THEN** todas las sub-vistas del panel se actualizan con los datos del período seleccionado

#### Scenario: Sin datos para el período
- **WHEN** no hay actividad registrada para los filtros aplicados
- **THEN** cada sub-vista muestra su estado vacío individual

### Requirement: Gráfico de acciones por día

La feature SHALL mostrar un gráfico de barras (o SVG nativo si no hay librería de charts disponible en `package.json`) con el volumen de acciones por día para el período filtrado. Implementa F9.1 sub-vista 1.

#### Scenario: Gráfico con datos
- **WHEN** hay actividad para el período seleccionado
- **THEN** el gráfico muestra una barra por día con la cantidad de acciones del día

#### Scenario: Gráfico vacío
- **WHEN** no hay actividad para el período
- **THEN** el gráfico muestra el estado vacío "sin actividad en el período"

### Requirement: Log de últimas acciones

La feature SHALL mostrar las últimas N acciones del sistema (por defecto 200) con columnas fecha/hora, usuario, materia, tipo de acción, registros afectados, IP y agente de usuario. Implementa F9.1 sub-vista 4.

#### Scenario: Ver log de últimas acciones
- **WHEN** el usuario accede al log
- **THEN** la UI muestra las acciones más recientes paginadas, con todas las columnas definidas en F9.2

### Requirement: Log completo de auditoría (solo ADMIN)

La feature SHALL presentar el log completo de auditoría sin límite de registros, consumiendo `GET /api/v1/auditoria/log`, visible únicamente para ADMIN. Implementa F9.2 y RN-23, RN-24.

#### Scenario: ADMIN ve el log completo
- **WHEN** el ADMIN accede al log completo con filtro por usuario
- **THEN** la UI muestra todos los registros del usuario sin corte de N registros

#### Scenario: COORDINADOR no ve el log completo
- **WHEN** un COORDINADOR accede a la ruta del log completo
- **THEN** la UI muestra 403 o redirige — el log completo es exclusivo de ADMIN

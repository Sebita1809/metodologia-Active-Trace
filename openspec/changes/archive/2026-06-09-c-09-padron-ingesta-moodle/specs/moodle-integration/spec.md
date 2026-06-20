## ADDED Requirements

### Requirement: Cliente aislado de Moodle Web Services

El sistema SHALL proveer un cliente dedicado de Moodle Web Services en `app/integrations/moodle_ws.py`, aislado de la lógica de negocio. El cliente SHALL recibir la configuración de conexión (URL base y token) por inyección y NUNCA SHALL acceder directamente a la base de datos. Sus fallas NUNCA SHALL romper el flujo principal de la API.

#### Scenario: Cliente desacoplado del dominio

- **WHEN** la capa de servicio necesita datos del LMS
- **THEN** invoca al cliente `moodle_ws`, que encapsula las llamadas HTTP al LMS y devuelve datos normalizados, sin que el cliente consulte la base de datos

### Requirement: Sincronización de usuarios y actividades

El sistema SHALL sincronizar usuarios y actividades desde Moodle Web Services. La sincronización SHALL poder ejecutarse de dos formas: **nocturna automática** (programada) y **on-demand** disparada por un usuario autorizado. Una sync exitosa de padrón SHALL producir una nueva `VersionPadron` activa con origen `moodle`.

#### Scenario: Sync on-demand

- **WHEN** un usuario con permiso `padron:cargar` dispara una sincronización on-demand para `(materia, cohorte)`
- **THEN** el sistema obtiene los datos del LMS vía el cliente Moodle y crea una nueva versión activa de padrón con origen `moodle`, registrando `PADRON_CARGAR`

#### Scenario: Sync nocturna

- **WHEN** se ejecuta el job nocturno de sincronización
- **THEN** el sistema actualiza el padrón de las materias configuradas creando nuevas versiones activas, sin intervención manual

### Requirement: Mapeo de errores de integración a HTTP 502 con reintento

El sistema SHALL mapear los errores de comunicación con Moodle Web Services (timeout, error de red, respuesta de error del LMS) a una respuesta HTTP **502 Bad Gateway**. El cliente SHALL aplicar un mecanismo de reintento ante fallos transitorios antes de propagar el error.

#### Scenario: Error transitorio reintentado

- **WHEN** una llamada al LMS falla con un error transitorio
- **THEN** el cliente reintenta según la política configurada antes de propagar el fallo

#### Scenario: Falla persistente mapeada a 502

- **WHEN** la sincronización on-demand falla tras agotar los reintentos
- **THEN** el endpoint responde HTTP 502 y no deja el padrón en un estado parcial (no se activa una versión incompleta)

### Requirement: Fallback de importación manual

El sistema SHALL permitir, para tenants cuyo Moodle no exponga Web Services, cargar el padrón mediante importación manual de archivo `.xlsx` / `.csv`. El fallback manual SHALL producir el mismo resultado de dominio que la sync de Moodle: una nueva `VersionPadron` activa, con origen `archivo`.

#### Scenario: Tenant sin Web Services usa importación de archivo

- **WHEN** un tenant no tiene Moodle Web Services disponible y un usuario importa un archivo de padrón
- **THEN** el sistema crea la versión activa con origen `archivo`, equivalente en estructura a la que generaría la sync de Moodle

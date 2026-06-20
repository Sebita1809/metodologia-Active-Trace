## ADDED Requirements

### Requirement: Cliente HTTP centralizado
El sistema SHALL exponer una única instancia de Axios en `shared/services/api.ts` configurada con la base URL de la API. Todas las peticiones al backend SHALL realizarse a través de esta instancia. La instancia SHALL adjuntar el header `Authorization: Bearer <access_token>` cuando existe una sesión activa.

#### Scenario: Inyección del access token
- **WHEN** se emite una petición a través del cliente HTTP y existe un access token en la sesión
- **THEN** la petición incluye el header `Authorization: Bearer <access_token>`

#### Scenario: Petición sin sesión
- **WHEN** se emite una petición a través del cliente HTTP y no existe sesión activa
- **THEN** la petición se envía sin header `Authorization`

### Requirement: Refresh transparente de tokens ante 401
El sistema SHALL interceptar las respuestas `401 Unauthorized` y, si existe un refresh token, SHALL invocar `POST /api/auth/refresh` para obtener un nuevo par de tokens (con rotación), persistir el par nuevo y reintentar automáticamente la petición original una sola vez. El usuario NO SHALL percibir el refresh.

#### Scenario: Refresh exitoso y reintento
- **WHEN** una petición protegida recibe `401` por access token expirado y existe un refresh token válido
- **THEN** el cliente llama a `/api/auth/refresh`, guarda el nuevo par de tokens y reintenta la petición original, que ahora responde correctamente

#### Scenario: Una sola cola de refresh para peticiones concurrentes
- **WHEN** varias peticiones reciben `401` simultáneamente
- **THEN** el cliente ejecuta un único refresh y, al completarse, reintenta todas las peticiones encoladas con el nuevo access token

#### Scenario: Refresh fallido cierra la sesión
- **WHEN** la llamada a `/api/auth/refresh` falla (refresh token inválido, rotado o expirado)
- **THEN** el cliente limpia la sesión y redirige al login, sin reintentar la petición original en bucle

#### Scenario: No reintentar el propio refresh
- **WHEN** la petición que recibe `401` es la llamada a `/api/auth/refresh`
- **THEN** el cliente NO intenta refrescar de nuevo y trata el caso como sesión inválida

### Requirement: Manejo diferenciado de 403
El sistema SHALL tratar las respuestas `403 Forbidden` como falta de permiso (no como sesión expirada). El cliente NO SHALL intentar refresh ante un `403` y SHALL propagar el error para que la UI muestre el estado de acceso denegado.

#### Scenario: 403 no dispara refresh
- **WHEN** una petición recibe `403 Forbidden`
- **THEN** el cliente NO llama a `/api/auth/refresh` y propaga el error de autorización a la capa de UI

### Requirement: Errores de red y de servidor propagados
El sistema SHALL propagar de forma tipada los errores de red y los códigos `>= 500` para que las features puedan mostrar mensajes de error sin romper la aplicación.

#### Scenario: Error de servidor
- **WHEN** una petición recibe un código `500`
- **THEN** el cliente propaga un error tipado que el hook de servicio puede manejar para mostrar un mensaje al usuario

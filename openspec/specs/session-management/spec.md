## ADDED Requirements

### Requirement: Identidad derivada exclusivamente del JWT
El sistema SHALL derivar la identidad mostrada (user id, tenant, roles) exclusivamente de los claims del access token JWT verificado por el backend (`sub`, `tenant_id`, `roles`, `exp`). El frontend NUNCA SHALL construir identidad ni permisos a partir de parámetros de URL, formularios o estado arbitrario del cliente.

#### Scenario: Lectura de claims de la sesión
- **WHEN** existe una sesión activa
- **THEN** el frontend obtiene `sub`, `tenant_id` y `roles` decodificando el access token, y los usa para adaptar la UI

#### Scenario: La identidad no se altera desde la petición
- **WHEN** la URL u otro input del cliente contiene un identificador de usuario distinto
- **THEN** el frontend lo trata como dato de negocio y NO lo usa para cambiar la identidad de la sesión

### Requirement: Persistencia y limpieza de tokens
El sistema SHALL persistir el access token y el refresh token de forma que sobrevivan recargas de la página dentro de la misma sesión del navegador, y SHALL limpiarlos completamente al cerrar sesión o ante un refresh fallido.

#### Scenario: Sesión sobrevive a recarga
- **WHEN** el usuario recarga la página teniendo una sesión válida
- **THEN** el frontend recupera los tokens persistidos y mantiene la sesión sin pedir login nuevamente

#### Scenario: Limpieza total al cerrar sesión
- **WHEN** se cierra la sesión (logout o refresh fallido)
- **THEN** el access token y el refresh token quedan eliminados del almacenamiento del cliente

### Requirement: Estado de sesión global
El sistema SHALL exponer el estado de sesión (autenticado / no autenticado, claims actuales) de forma global a la aplicación, de modo que guards, layout y features reaccionen a cambios de sesión sin recargar la página.

#### Scenario: La UI reacciona al cambio de sesión
- **WHEN** la sesión pasa de no autenticada a autenticada tras un login exitoso
- **THEN** los componentes suscritos al estado de sesión se actualizan y muestran la app autenticada sin recarga completa

### Requirement: Detección de access token expirado
El sistema SHALL considerar inválida la sesión cuando el `exp` del access token ya pasó y no es posible refrescar, tratando al usuario como no autenticado.

#### Scenario: Sesión expirada sin refresh posible
- **WHEN** el access token está expirado y el refresh token también es inválido
- **THEN** el frontend considera la sesión no autenticada y redirige al login

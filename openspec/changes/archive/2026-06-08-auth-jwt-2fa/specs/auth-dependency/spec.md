## ADDED Requirements

### Requirement: Dependency `get_current_user` que resuelve identidad desde JWT
El sistema SHALL proveer una FastAPI Dependency `get_current_user` que extrae el Bearer token del header `Authorization`, lo verifica criptográficamente, y retorna un objeto inmutable `CurrentUser` con `user_id` (UUID), `tenant_id` (UUID) y `roles` (list[str]). La identidad y el tenant del usuario NUNCA se aceptan desde parámetros de query, body ni headers alternativos.

#### Scenario: Request autenticado con token válido
- **WHEN** un handler inyecta `Depends(get_current_user)` y el request incluye `Authorization: Bearer <valid_token>`
- **THEN** la dependency retorna un `CurrentUser` con los valores de `sub`, `tenant_id` y `roles` extraídos del token sin consultar la BD

#### Scenario: Request sin token
- **WHEN** un handler inyecta `Depends(get_current_user)` y el request no incluye el header `Authorization`
- **THEN** la dependency lanza `HTTPException(401)` antes de que el handler se ejecute

#### Scenario: Request con token malformado o firma inválida
- **WHEN** un handler inyecta `Depends(get_current_user)` y el token no puede verificarse (firma inválida, formato incorrecto)
- **THEN** la dependency lanza `HTTPException(401)` antes de que el handler se ejecute

#### Scenario: Request con token de scope incorrecto
- **WHEN** un handler protegido (no el gate de 2FA) recibe un token con scope `"2fa_pending"`
- **THEN** la dependency lanza `HTTPException(401)` — el scope `"2fa_pending"` no autoriza acceso a recursos normales

### Requirement: Identidad inmutable por parámetro de petición
El sistema SHALL ignorar completamente cualquier intento de especificar `user_id` o `tenant_id` en la URL, query string o body de una request como mecanismo de identidad. La única fuente válida son los claims del JWT verificado.

#### Scenario: Parámetro `user_id` en query string ignorado
- **WHEN** un handler protegido recibe `?user_id=<otro-uuid>` en la query string
- **THEN** el sistema utiliza el `user_id` del JWT verificado, no el del parámetro; el parámetro se trata como dato de entrada de negocio a validar contra los permisos del usuario actual

#### Scenario: `tenant_id` en body ignorado como identidad
- **WHEN** un handler protegido recibe `tenant_id` en el body del request
- **THEN** el sistema utiliza el `tenant_id` del JWT verificado para todas las operaciones de aislamiento; cualquier `tenant_id` del body se trata como input de negocio, no como selector de tenant del actor

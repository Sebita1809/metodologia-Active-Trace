## MODIFIED Requirements

### Requirement: Dependency `get_current_user` que resuelve identidad desde JWT
El sistema SHALL proveer una FastAPI Dependency `get_current_user` que extrae el Bearer token del header `Authorization`, lo verifica criptográficamente, y retorna un objeto inmutable `CurrentUser` con `user_id` (UUID), `tenant_id` (UUID) y `roles` (list[str]). La identidad y el tenant del usuario NUNCA se aceptan desde parámetros de query, body ni headers alternativos. Los `roles` presentes en el `CurrentUser` son informativos para diagnóstico y no constituyen la fuente de autorización: los permisos efectivos se resuelven server-side contra la base de datos en cada request (ver capability `rbac-authorization`), nunca a partir de los `roles` del token.

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

#### Scenario: Los roles del token no autorizan por sí solos
- **WHEN** un endpoint protegido por `require_permission(...)` recibe un token cuyos `roles` incluyen un rol con el permiso requerido, pero el usuario no tiene ese rol asignado y vigente en la BD
- **THEN** la autorización falla con `403`, porque los permisos efectivos se resuelven contra la BD, no contra los `roles` del token

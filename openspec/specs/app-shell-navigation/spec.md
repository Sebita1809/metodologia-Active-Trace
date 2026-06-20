## ADDED Requirements

### Requirement: Layout principal de la aplicación autenticada
El sistema SHALL proveer un layout/shell común para las pantallas autenticadas, con una zona de navegación (menú) y un área de contenido donde se renderizan las rutas de las features. El shell SHALL mostrar la identidad básica del usuario de la sesión y la acción de cerrar sesión.

#### Scenario: Render del shell autenticado
- **WHEN** un usuario autenticado navega dentro de la aplicación
- **THEN** se renderiza el layout con el menú, el área de contenido de la ruta activa y la acción de logout disponible

#### Scenario: El login no usa el shell autenticado
- **WHEN** un usuario no autenticado está en las pantallas de auth (login, 2FA, recuperación)
- **THEN** esas pantallas se muestran sin el shell/menú de la aplicación autenticada

### Requirement: Menú adaptado a los permisos de la sesión
El sistema SHALL construir el menú de navegación mostrando únicamente las secciones para las que la sesión tiene rol/permiso. Las secciones no permitidas NO SHALL aparecer en el menú.

#### Scenario: Menú filtrado por rol
- **WHEN** se renderiza el menú para un usuario con un conjunto dado de roles
- **THEN** solo aparecen las entradas de menú asociadas a secciones para las que la sesión está autorizada

#### Scenario: Cambio de sesión actualiza el menú
- **WHEN** la sesión cambia (login, logout o cambio de roles efectivos)
- **THEN** el menú se recalcula para reflejar las secciones permitidas por la nueva sesión

### Requirement: Página inicial tras autenticarse
El sistema SHALL definir una ruta de inicio por defecto a la que se dirige al usuario tras un login exitoso, dentro del shell autenticado.

#### Scenario: Redirección a inicio tras login
- **WHEN** un usuario completa el login (con o sin 2FA)
- **THEN** el frontend lo lleva a la ruta de inicio por defecto renderizada dentro del shell autenticado

## ADDED Requirements

### Requirement: Proyecto SPA con el stack frontend del producto
El sistema SHALL inicializar el frontend como una Single Page Application en el directorio `frontend/`, construida con React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, React Hook Form + Zod y Axios. El proyecto SHALL arrancar en modo desarrollo con HMR y SHALL producir un build de producción.

#### Scenario: El proyecto arranca en desarrollo
- **WHEN** se ejecuta el comando de desarrollo de Vite en `frontend/`
- **THEN** el servidor de desarrollo levanta la SPA con Hot Module Replacement activo y sirve la pantalla inicial

#### Scenario: El proyecto compila para producción
- **WHEN** se ejecuta el comando de build de Vite
- **THEN** se genera el bundle de producción sin errores de TypeScript

#### Scenario: TypeScript estricto sin `any`
- **WHEN** se compila el proyecto con la configuración de TypeScript del producto
- **THEN** el modo estricto está activo y el uso de `any` explícito es rechazado por el linter/compilador

### Requirement: Organización feature-based de carpetas
El sistema SHALL organizar el código por módulos de negocio (features). Cada feature SHALL agrupar sus propios `components`, `hooks`, `services`, `types` y `pages`. El código transversal reutilizable SHALL vivir bajo `shared/`.

#### Scenario: Estructura de una feature
- **WHEN** se inspecciona el directorio `frontend/src/features/auth/`
- **THEN** existe la estructura `components/`, `hooks/`, `services/`, `types/` y `pages/` propia de la feature

#### Scenario: Código transversal en shared
- **WHEN** se inspecciona `frontend/src/shared/`
- **THEN** contiene `services/` (cliente HTTP), `components/` (UI reutilizable) y `hooks/` compartidos

### Requirement: Convenciones de código del frontend
El sistema SHALL nombrar los componentes y sus archivos en PascalCase (`LoginPage.tsx`), SHALL prohibir class components y SHALL usar únicamente Tailwind CSS para estilos (sin CSS modules ni estilos inline, salvo valores dinámicos).

#### Scenario: Componente en PascalCase y funcional
- **WHEN** se crea un nuevo componente React en el proyecto
- **THEN** el nombre del componente y del archivo está en PascalCase y el componente es funcional (no una clase)

#### Scenario: Estilos solo con Tailwind
- **WHEN** se aplica estilo a un componente
- **THEN** se usan clases utilitarias de Tailwind y no se introducen archivos CSS modules ni estilos inline estáticos

### Requirement: Toda comunicación con el backend pasa por hooks de servicio
El sistema SHALL canalizar todo acceso al backend a través de hooks de TanStack Query ubicados en `services/`/`hooks/` de cada feature, que usan el cliente HTTP centralizado. Ningún componente SHALL llamar a Axios directamente.

#### Scenario: Fetch desde un componente
- **WHEN** un componente necesita datos del backend
- **THEN** los obtiene mediante un hook de servicio (TanStack Query) y no instancia ni invoca Axios directamente

## ADDED Requirements

### Requirement: Tenant es la raíz de aislamiento del sistema
Toda institución que usa la plataforma es un `Tenant`. El sistema SHALL garantizar que ningún dato de un tenant sea accesible desde el contexto de otro tenant. La entidad `Tenant` existe en la base de datos como raíz del aislamiento row-level.

#### Scenario: Tenant se crea con atributos mínimos
- **WHEN** se crea un `Tenant` con `slug`, `nombre` y `activo=True`
- **THEN** el registro queda persistido con un UUID generado, `created_at` y `updated_at` automáticos

#### Scenario: Slug de Tenant es único en el sistema
- **WHEN** se intenta crear un segundo `Tenant` con el mismo `slug`
- **THEN** la base de datos rechaza la operación con error de unicidad

### Requirement: Tenant puede ser desactivado
El sistema SHALL permitir marcar un Tenant como inactivo (`activo=False`). Un Tenant inactivo no admite nuevas sesiones de sus usuarios (validación que realizará C-03).

#### Scenario: Tenant inactivo registrado en base de datos
- **WHEN** se persiste un `Tenant` con `activo=False`
- **THEN** el campo `activo` queda en `False` y el registro existe sin error

# Spec Delta — materia (C-18, MODIFIED)

## ADDED Requirements

### Requirement: Materia mapea a una clave de categoría de Plus
El sistema SHALL permitir asociar a una Materia una `clave_plus` (string libre, nullable) que la mapea a una clave de categoría de Plus salarial. Las claves son configurables por tenant (PA-22). Una Materia con `clave_plus` nulo no aporta Plus al cálculo de liquidación (RN-33, RN-34).

#### Scenario: Asignar clave_plus a una materia
- **WHEN** un ADMIN con `estructura:gestionar` hace PATCH a una Materia seteando `clave_plus = "PROG"`
- **THEN** el sistema persiste la `clave_plus` y retorna HTTP 200

#### Scenario: Materia sin clave_plus no genera plus
- **WHEN** una Materia tiene `clave_plus = null` y un docente tiene comisiones de esa materia en un período
- **THEN** esas comisiones no aportan Plus al cálculo de la liquidación

#### Scenario: clave_plus es libre y no validada contra catálogo global
- **WHEN** un ADMIN asigna una `clave_plus` que no existe en otros tenants
- **THEN** el sistema acepta el valor sin validarlo contra un catálogo global

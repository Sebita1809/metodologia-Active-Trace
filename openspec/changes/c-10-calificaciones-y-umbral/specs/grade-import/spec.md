## ADDED Requirements

### Requirement: Import grades from LMS file
The system SHALL allow PROFESOR and COORDINADOR to import student grades from an LMS-exported spreadsheet file (xlsx/csv) for a specific subject and cohort.

#### Scenario: Successful grade import
- **WHEN** a PROFESOR uploads a valid xlsx file with grades for their subject
- **THEN** the system SHALL return a preview with detected activities (columns) and students (rows)

#### Scenario: Import without active padron
- **WHEN** a PROFESOR tries to import grades for a subject/cohort without an active `VersionPadron`
- **THEN** the system SHALL reject with 400 error: "No hay padrón activo para esta materia y cohorte"

#### Scenario: Activity detection - numeric columns
- **WHEN** the system processes a file with numeric grade columns (e.g., 0-10 scale)
- **THEN** these columns SHALL be detected as numeric activities (RN-01) and offered for selection

#### Scenario: Activity detection - textual columns
- **WHEN** the system processes a file with textual grade columns (e.g., "Aprobado", "No entregado")
- **THEN** these columns SHALL be detected as textual activities (RN-02) and offered for selection

### Requirement: Preview and confirm grade import
The system SHALL provide a two-step import flow: preview with activity selection, then confirm.

#### Scenario: Preview with activity selection
- **WHEN** the system shows the import preview
- **THEN** the user SHALL select which detected activities to include in the import
- **AND** the system SHALL show expected row count and column count

#### Scenario: Confirm import
- **WHEN** the user confirms the import with selected activities
- **THEN** the system SHALL create `Calificacion` records for each student-activity combination
- **AND** log an audit entry with code `CALIFICACIONES_IMPORTAR`

#### Scenario: Preview rejects invalid file
- **WHEN** a user uploads an unsupported format (not xlsx/csv)
- **THEN** the system SHALL reject with 400 error: "Formato de archivo no soportado"

### Requirement: Grade approval derivation
The system SHALL derive the `aprobado` field based on grade type and configuration.

#### Scenario: Numeric grade above threshold
- **WHEN** a student has `nota_numerica = 75` and the subject threshold is 60
- **THEN** `aprobado` SHALL be `true`

#### Scenario: Numeric grade below threshold
- **WHEN** a student has `nota_numerica = 45` and the subject threshold is 60
- **THEN** `aprobado` SHALL be `false`

#### Scenario: Textual grade in approved set
- **WHEN** a student has `nota_textual = "Satisfactorio"` and the subject approved values include "Satisfactorio"
- **THEN** `aprobado` SHALL be `true`

#### Scenario: Textual grade not in approved set
- **WHEN** a student has `nota_textual = "Regular"` and the subject approved values do not include "Regular"
- **THEN** `aprobado` SHALL be `false`

### Requirement: List grades by subject and cohort
The system SHALL return all grades for a given subject and cohort.

#### Scenario: List grades
- **WHEN** a PROFESOR requests grades for their subject and cohort
- **THEN** the system SHALL return all calificaciones with student info, actividad, nota_numerica, nota_textual, and derived aprobado

#### Scenario: List grades without data
- **WHEN** a PROFESOR requests grades for a subject/cohort with no imported grades
- **THEN** the system SHALL return an empty list

### Requirement: Clear grades for a subject
The system SHALL allow clearing all imported grades for a subject and cohort (F1.5, RN-04).

#### Scenario: Clear grades successfully
- **WHEN** a PROFESOR clears grades for their subject and cohort
- **THEN** the system SHALL hard-delete all `Calificacion` records for that materia/cohorte
- **AND** log an audit entry with code `CALIFICACIONES_IMPORTAR`

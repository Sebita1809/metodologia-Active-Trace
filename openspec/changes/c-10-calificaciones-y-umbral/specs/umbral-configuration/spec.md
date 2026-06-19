## ADDED Requirements

### Requirement: Configure passing threshold per assignment
The system SHALL allow PROFESOR to configure the passing grade threshold for their subject assignment.

#### Scenario: Set threshold successfully
- **WHEN** a PROFESOR sets the threshold to 70 for their subject
- **THEN** the system SHALL update the `umbral_pct` for that assignment
- **AND** all subsequent grade approval calculations SHALL use the new threshold

#### Scenario: Set threshold without existing umbral
- **WHEN** a PROFESOR sets a threshold but no `UmbralMateria` exists for their assignment
- **THEN** the system SHALL create a new `UmbralMateria` with the specified values

#### Scenario: Threshold at default value
- **WHEN** a new assignment is created for PROFESOR/TUTOR role
- **THEN** the system SHALL auto-create an `UmbralMateria` with default `umbral_pct = 60` and empty `valores_aprobatorios`
- **AND** this SHALL NOT affect other teachers' thresholds for the same subject

### Requirement: Configure approved textual values
The system SHALL allow PROFESOR to set which textual values count as approved.

#### Scenario: Set approved textual values
- **WHEN** a PROFESOR sets approved textual values to ["Satisfactorio", "Supera lo esperado", "Aprobado"]
- **THEN** the system SHALL store these values in `valores_aprobatorios`
- **AND** grade approval SHALL consider these values as passing

#### Scenario: Clear approved textual values
- **WHEN** a PROFESOR clears all approved textual values
- **THEN** the system SHALL set `valores_aprobatorios` to an empty list
- **AND** only numeric grades SHALL be considered for approval

### Requirement: Threshold isolation per teacher
The system SHALL ensure each teacher's threshold only affects their own assignments.

#### Scenario: Threshold isolation
- **WHEN** two PROFESORes are assigned to the same subject and one changes their threshold
- **THEN** the other PROFESOR's threshold SHALL remain unchanged
- **AND** grade approval calculations SHALL use each teacher's own configured threshold

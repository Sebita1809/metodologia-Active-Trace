## ADDED Requirements

### Requirement: Worker procesa la cola de comunicaciones pendientes

El sistema SHALL proveer un worker asíncrono independiente (módulo en `workers/`) que consuma las comunicaciones en estado `Pendiente` despachables, las transicione a `Enviando`, las despache a través de una interfaz de canal de envío inyectable, y resuelva su estado a `Enviado` (despacho OK) o `Error` (despacho fallido), registrando `enviado_at` al pasar a `Enviado`. El worker SHALL respetar el ciclo de vida de estados (RN-15). El canal de envío externo (SMTP/API) SHALL ser inyectable para permitir mockearlo en tests sin tocar la base de datos.

#### Scenario: despacho exitoso transiciona a Enviado

- **WHEN** el worker procesa una comunicación despachable y el canal retorna éxito
- **THEN** la comunicación pasa de `Enviando` a `Enviado` y se registra `enviado_at`

#### Scenario: despacho fallido transiciona a Error

- **WHEN** el worker procesa una comunicación despachable y el canal retorna fallo
- **THEN** la comunicación pasa de `Enviando` a `Error`

#### Scenario: worker toma el mensaje en Enviando antes de despachar

- **WHEN** el worker selecciona una comunicación despachable
- **THEN** la transiciona a `Enviando` antes de invocar el canal de envío

### Requirement: Worker respeta la aprobación humana configurable por tenant

Cuando el tenant exige aprobación de comunicaciones (RN-17), el worker SHALL procesar únicamente las comunicaciones `Pendiente` que tengan `aprobado_at` no nulo. Las comunicaciones `Pendiente` sin aprobar NO SHALL ser despachadas. Si el tenant no exige aprobación, el worker SHALL procesar cualquier comunicación `Pendiente`. Ante configuración ausente o ambigua, el worker SHALL comportarse como si la aprobación fuera requerida (fail-safe).

#### Scenario: con aprobación requerida solo despacha aprobados

- **WHEN** el tenant exige aprobación y existen comunicaciones `Pendiente` aprobadas y no aprobadas
- **THEN** el worker despacha solo las que tienen `aprobado_at` y deja las no aprobadas en `Pendiente`

#### Scenario: sin aprobación requerida despacha todos los pendientes

- **WHEN** el tenant no exige aprobación
- **THEN** el worker despacha todas las comunicaciones `Pendiente` sin requerir `aprobado_at`

#### Scenario: configuración ausente exige aprobación

- **WHEN** la configuración de aprobación del tenant no está definida
- **THEN** el worker se comporta como si la aprobación fuera requerida y no despacha mensajes sin aprobar

### Requirement: Los fallos del worker no rompen el flujo principal

El worker SHALL aislar sus fallos: una excepción lanzada por el canal de envío al despachar una comunicación SHALL ser capturada, transicionar esa comunicación a `Error`, y NO SHALL propagarse ni interrumpir el procesamiento del resto de la cola ni el flujo HTTP principal (§5.2).

#### Scenario: excepción del canal se captura como Error

- **WHEN** el canal de envío lanza una excepción al despachar una comunicación
- **THEN** el worker captura la excepción, transiciona esa comunicación a `Error` y no propaga la excepción

#### Scenario: un fallo no detiene el resto del lote

- **WHEN** el canal falla en una comunicación pero tiene éxito en las demás del lote
- **THEN** la fallida queda en `Error` y las demás quedan en `Enviado`

### Requirement: Cancelación gana la carrera contra el worker

Una comunicación que fue cancelada (`Pendiente → Cancelado`) antes de que el worker la tome NO SHALL ser despachada. La transición a `Enviando` SHALL aplicarse condicionada a que el estado siga siendo `Pendiente`, de modo que una cancelación concurrente excluya el despacho.

#### Scenario: mensaje cancelado no se despacha

- **WHEN** una comunicación pasa a `Cancelado` antes de que el worker la procese
- **THEN** el worker no la transiciona a `Enviando` ni invoca el canal de envío para ella

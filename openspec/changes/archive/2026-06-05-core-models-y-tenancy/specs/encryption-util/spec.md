## ADDED Requirements

### Requirement: CryptoService cifra strings PII con AES-256-GCM
El sistema SHALL proveer `CryptoService` con métodos `encrypt(plaintext: str) -> str` y `decrypt(ciphertext: str) -> str`. El cifrado SHALL usar AES-256-GCM con IV aleatorio de 12 bytes generado por operación. El resultado de `encrypt` SHALL ser una string base64url que incluye IV, ciphertext y tag de autenticación.

#### Scenario: encrypt produce resultado diferente para el mismo input
- **WHEN** se llama `encrypt("mismo_valor")` dos veces con la misma clave
- **THEN** los dos resultados son distintos (IV diferente por operación)

#### Scenario: decrypt recupera el plaintext original
- **WHEN** se llama `decrypt(encrypt(plaintext))` con la misma instancia de CryptoService
- **THEN** el resultado es idéntico al `plaintext` original

### Requirement: CryptoService detecta tampering del ciphertext
El sistema SHALL rechazar con excepción cualquier ciphertext modificado o corrupto. AES-256-GCM provee autenticación; cualquier alteración del ciphertext, IV o tag debe ser detectable.

#### Scenario: decrypt falla con ciphertext alterado
- **WHEN** se llama `decrypt` con un ciphertext modificado (un byte cambiado)
- **THEN** la operación lanza una excepción de autenticación (no devuelve datos corruptos en silencio)

### Requirement: CryptoService requiere clave de 256 bits (32 bytes)
El sistema SHALL rechazar el arranque si `ENCRYPTION_KEY` no tiene exactamente 32 bytes (64 caracteres hex). Esta validación ocurre al construir `Settings`, no en tiempo de cifrado.

#### Scenario: clave inválida falla en Settings
- **WHEN** `ENCRYPTION_KEY` es una cadena hex de longitud incorrecta (p.ej. 30 bytes)
- **THEN** la instanciación de `Settings` lanza `ValidationError` con mensaje claro

#### Scenario: plaintext nunca aparece en logs
- **WHEN** se ejecuta `encrypt` o `decrypt`
- **THEN** ninguna línea de log contiene el valor de `plaintext` ni la clave de cifrado

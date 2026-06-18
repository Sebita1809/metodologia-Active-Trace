## ADDED Requirements

### Requirement: AES-256-GCM encryption utility
The system SHALL provide an `AESCipher` utility class that encrypts and decrypts sensitive data at rest using AES-256 in GCM mode.

- Input/output format: plaintext string → base64-encoded ciphertext (nonce + ciphertext + tag)
- Key source: `ENCRYPTION_KEY` environment variable, exactly 32 bytes
- Decryption MUST verify integrity before returning plaintext

#### Scenario: Encrypt plaintext
- **WHEN** encrypting a plaintext string
- **THEN** the result is a non-empty base64 string containing nonce, ciphertext, and authentication tag

#### Scenario: Decrypt returns original plaintext (round-trip)
- **WHEN** decrypting a previously encrypted value
- **THEN** the result matches the original plaintext exactly

#### Scenario: Decrypt with tampered ciphertext raises error
- **WHEN** attempting to decrypt a ciphertext whose content was modified
- **THEN** the system raises an authentication error (integrity check fails)

#### Scenario: Encrypt empty string
- **WHEN** encrypting an empty string
- **THEN** the result is a valid base64 ciphertext that decrypts back to an empty string

#### Scenario: Encrypt None raises error
- **WHEN** attempting to encrypt a `None` value
- **THEN** the system raises a `ValueError`

#### Scenario: Decrypt invalid base64 raises error
- **WHEN** attempting to decrypt a string that is not valid base64
- **THEN** the system raises a `ValueError`

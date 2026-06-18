# api-rate-limiting

## ADDED Requirements

### Requirement: Rate limit on login
The system MUST limit login attempts to a maximum of 5 per 60-second sliding window, keyed by the combination of source IP address and email (IP+email). Once the limit is reached, further attempts MUST be blocked until the window resets.

#### Scenario: Login under limit is allowed
- **WHEN** a client sends fewer than 5 login requests within a 60-second window for the same IP+email combination
- **THEN** each request MUST be processed normally without rate-limit intervention

#### Scenario: Login exceeds limit within window
- **WHEN** a client sends a 6th login request within a 60-second window for the same IP+email combination
- **THEN** the system MUST reject the request and NOT process the login

#### Scenario: Window resets after 60 seconds
- **WHEN** a client has been rate-limited and waits 60 seconds from the first request in the current window
- **THEN** the client MUST be allowed to attempt login again (the counter resets for that IP+email combination)

### Requirement: Rate limit response
When a request is rate-limited, the system MUST return HTTP 429 (Too Many Requests) with a `Retry-After` header indicating the number of seconds remaining until the window resets.

#### Scenario: Rate-limited request returns 429 with Retry-After
- **WHEN** a login request is blocked due to rate limiting
- **THEN** the system MUST respond with HTTP status 429 and a `Retry-After` header whose value SHALL be the integer number of seconds until the current 60-second window expires

#### Scenario: Retry-After header is accurate
- **WHEN** a client receives a 429 response with a `Retry-After` value of N seconds and waits exactly N seconds before retrying
- **THEN** the retry request MUST NOT be rate-limited (provided no other requests were made in the interim)

### Requirement: Rate limit separate per tenant
Rate-limit counters MUST be scoped independently by the IP+email combination. Each tenant's traffic MUST NOT affect another tenant's counters, and a global (tenant-agnostic) counter MUST NOT be used.

#### Scenario: Different tenants have independent counters
- **WHEN** 5 failed login attempts occur for user `a@example.com` via IP `10.0.0.1` on tenant A, and a separate request arrives for user `b@example2.com` via the same IP `10.0.0.1` on tenant B
- **THEN** the request on tenant B MUST be processed normally because the IP+email combination differs from the blocked combination on tenant A

#### Scenario: Same email on different tenants is not shared
- **WHEN** 5 login attempts are exhausted for `user@example.com` on tenant A, and a login attempt arrives for `user@example.com` on tenant B from a different IP
- **THEN** the request on tenant B MUST be processed normally because the IP+email combination is distinct

### Requirement: Rate limit abstraction
The rate-limiter MUST be defined behind an abstract interface (e.g., a Python protocol or abstract base class) so that the backing store (in-memory, Redis, database, etc.) can be swapped without changing the consuming code.

#### Scenario: Rate limiter implements a defined interface
- **WHEN** any rate-limiter implementation is provided to the login service
- **THEN** it MUST conform to a defined interface that exposes at least `check_rate_limit(ip: str, email: str) -> RateLimitResult` where `RateLimitResult` includes whether the request is allowed and the remaining seconds until reset

#### Scenario: Backing store can be swapped
- **WHEN** the system is configured to use `RedisRateLimiter` instead of `InMemoryRateLimiter`
- **THEN** the login service MUST behave identically — same rate-limiting logic, same 429 responses — without any code changes to the service itself, only to the dependency-injection wiring

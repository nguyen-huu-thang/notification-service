# Architecture

**English** | [Tiếng Việt](../vn/architecture.md)

---

## Layered Overview

Notification Service follows **Hexagonal Architecture** (Ports and Adapters) with DDD tactical patterns, built on Python + Xime Framework.

```
External Clients (gRPC + mTLS)
        ↓
   Adapter Layer (api/)           ← receives gRPC requests, maps to use case inputs
        ↓
 Application Layer (application/) ← use cases, port interfaces, DTOs
        ↓
   Domain Layer (domain/)         ← pure Python classes + value objects, no framework dependency
        ↑
Infrastructure Layer (infrastructure/) ← SMTP, Jinja2, mTLS
```

The domain layer has no knowledge of aiosmtplib, Jinja2, or gRPC. The infrastructure layer has no knowledge of use case logic. Dependencies always point inward toward the domain.

---

## Directory Structure

```
app/
│
├── api/                                      ← adapter layer
│   └── grpc/
│       ├── external/
│       │   └── NotificationGrpcHandler.py    ← receives gRPC from other services
│       ├── interceptor/
│       │   └── AppExceptionInterceptor.py    ← catches AppException, redacts per channel, aborts with xime-error metadata
│       ├── mapper/
│       │   └── NotificationGrpcMapper.py     ← gRPC message ↔ Command/Result
│       └── generated/                        ← protobuf generated code
│
├── application/
│   ├── usecase/                              ← orchestrate: validate → domain → infra → return
│   │   └── email/
│   │       └── SendEmailUseCase.py           ← hybrid outbox
│   ├── service/                              ← reusable business logic
│   │   ├── retry/RetryPolicy.py              ← backoff + retry/dead-letter decision
│   │   └── email/
│   │       ├── EmailDeliveryService.py       ← send + apply outcome (shared usecase/worker)
│   │       ├── RetrySendService.py           ← worker that re-sends due notifications
│   │       └── NotificationCleanupService.py ← retention cleanup
│   ├── port/
│   │   └── outbound/                         ← Protocol interfaces (excluded from DI scan)
│   │       └── email/
│   │           ├── EmailSenderPort.py
│   │           ├── TemplatePort.py
│   │           ├── SaveNotificationPort.py
│   │           ├── LoadNotificationPort.py
│   │           └── DeleteNotificationPort.py
│   └── dto/                                  ← Pydantic/dataclass models (excluded from DI scan)
│       └── email/
│           ├── SendEmailCommand.py           ← carries idempotency_key
│           └── SendEmailResult.py            ← notification_id: Id
│
├── domain/                                   ← pure Python (excluded from DI scan)
│   ├── sharedkernel/                         ← Id (value object), IdFactory, IdService (KSUID)
│   ├── email/
│   │   ├── model/EmailNotification.py        ← plain class: invariants + behavior + retry state
│   │   └── valueobject/EmailAddress.py       ← normalize + validate
│   └── error/                                ← framework-neutral error objects
│       ├── Visibility.py                     ← PRIVATE / SYSTEM / PUBLIC
│       ├── Channel.py                        ← GRPC_INTERNAL / REST_EXTERNAL
│       ├── GrpcCode.py                        ← neutral gRPC status
│       ├── ErrorDef.py                        ← descriptor of one error code
│       ├── error_code.py                      ← error catalog (range 080000-089999)
│       └── redaction.py                       ← channel-based redaction
│
├── infrastructure/
│   ├── smtp/
│   │   └── SmtpEmailAdapter.py               ← implements EmailSenderPort
│   ├── template/
│   │   ├── JinjaTemplateAdapter.py           ← implements TemplatePort
│   │   └── templates/                        ← Jinja2 HTML templates (otp-email, login-alert, ...)
│   └── persistence/                          ← entity + mapper + repository
│       ├── entity/EmailNotificationEntity.py
│       ├── mapper/EmailNotificationMapper.py
│       └── repository/email/SqlAlchemyNotificationRepository.py
│
├── scheduler/                                ← background jobs (DI-scanned)
│   ├── EmailRetryJob.py                      ← every 1 min: re-send due notifications
│   └── NotificationCleanupJob.py            ← every 24h: remove old rows
│
├── config/
│   ├── dependency.py                         ← DI binding: Protocol → Implementation
│   └── scheduler.py                          ← registers IntervalJobs
│
├── common/
│   ├── constants/
│   │   ├── NotificationChannel.py            ← EMAIL, PHONE
│   │   └── NotificationStatus.py            ← PENDING, SENT, FAILED, DEAD_LETTER
│   ├── exception/
│   │   └── AppException.py                   ← AppException + PrivateError / SystemError / PublicError
│   └── util/
│       ├── Normalizer.py                     ← phone normalization (SMS later)
│       └── Pii.py                            ← mask_email for PII-safe logging
│
└── main.py
```

---

## DDD Tactical Patterns

### Domain Objects are Immutable

Domain objects in `domain/` are **plain Python classes** — they enforce invariants in
the constructor, expose private fields through read-only `@property`, and have no ORM
annotations or framework dependencies. IDs are an `Id` value object, not raw `bytes`.

```python
class EmailNotification:
    def __init__(self, notification_id: Id, recipient: EmailAddress, subject: str,
                 body: str, channel: NotificationChannel, status: NotificationStatus,
                 created_at: datetime, attempts: int = 0, ...) -> None:
        if not subject:
            raise ValueError("subject is required")
        self._notification_id = notification_id
        # ... assign remaining fields

    @property
    def status(self) -> NotificationStatus:
        return self._status

    def mark_sent(self, now: datetime) -> 'EmailNotification':
        return self._copy(status=NotificationStatus.SENT, attempts=self._attempts + 1, sent_at=now)

    def schedule_retry(self, now, next_retry_at, error_code) -> 'EmailNotification': ...
    def dead_letter(self, now, error_code) -> 'EmailNotification': ...
```

State changes return a new instance via a `_copy(...)` helper. No mutation.

### Port Interfaces Use Protocol

Port interfaces in `application/port/outbound/` use Python `Protocol` — not `ABC`, not abstract classes.

```python
# application/port/outbound/email/EmailSenderPort.py
from typing import Protocol

class EmailSenderPort(Protocol):
    async def send(self, to: str, subject: str, body: str) -> None: ...
```

Port interfaces are excluded from DI scan — they are binding targets, not implementations.

### Constructor Injection Only

Xime Framework uses **constructor injection exclusively**. No `@inject` decorators, no service locators.

```python
class SendEmailUseCase:
    def __init__(self,
                 email_sender: EmailSenderPort,
                 template:     TemplatePort) -> None:
        self._email_sender = email_sender
        self._template     = template
```

### Explicit DI Binding

All Protocol → Implementation bindings are declared explicitly in `config/dependency.py`. Missing binding causes startup failure (fail-fast).

```python
dependency.bind({
    EmailSenderPort: SmtpEmailAdapter,
    TemplatePort:    JinjaTemplateAdapter,
})
```

---

## Naming Conventions

| Type | Pattern | Example |
|---|---|---|
| Domain object | `*` (PascalCase) | `EmailNotification` |
| Port interface | `*Port` | `EmailSenderPort`, `TemplatePort` |
| Infrastructure adapter | `*Adapter` | `SmtpEmailAdapter`, `JinjaTemplateAdapter` |
| Use case | `*UseCase` | `SendEmailUseCase` |
| gRPC handler | `*GrpcHandler` | `NotificationGrpcHandler` |
| gRPC mapper | `*GrpcMapper` | `NotificationGrpcMapper` |
| DTO command | `*Command` | `SendEmailCommand` |
| DTO result | `*Result` | `SendEmailResult` |

---

## Packages Excluded from DI Scan

Xime Framework's DI scanner skips these packages — they contain interfaces and pure models, not implementations:

```
domain/
application/dto/
application/port/
common/constants/
common/exception/
api/grpc/mapper/        ← registered manually
```

---

## Use Case Flow

```
gRPC Request (SendEmail)
      ↓
NotificationGrpcHandler
      → maps proto message to SendEmailCommand (via NotificationGrpcMapper)
      ↓
SendEmailUseCase.execute(command, caller_service_id)   ← hybrid outbox
      → validate recipient (EmailAddress) + render body (TemplatePort)
      → if idempotency_key already exists → return existing id (no resend)
      → persist EmailNotification(PENDING) (transaction)
      → EmailDeliveryService.deliver(): send via SMTP
           • success            → mark_sent(SENT)
           • transient failure  → schedule_retry(FAILED, next_retry_at)  ← worker resends
           • recipient refused  → dead_letter(DEAD_LETTER)
      → persist outcome → return SendEmailResult(notification_id)
      ↓
NotificationGrpcHandler
      → maps SendEmailResult to proto response (notification_id as Base62 string)
      ↓
gRPC Response
```

A background worker (`EmailRetryJob`, every 1 min) scans due PENDING/FAILED notifications
and resends them; `NotificationCleanupJob` (every 24h) removes old rows by retention.
Notification Service **has a database** (PostgreSQL + Alembic): `email_notifications`
(outbox) and `trust_*` (mTLS cert/key) tables.

---

## Error Codes & Exceptions

The service follows the platform-wide error/exception standard (reference implementations: data-service and trust-service). Notification Service owns the **`080000 - 089999`** range, split into three zones by the thousands digit of the offset:

| Zone | Range | Visibility | Who can read |
| ---- | ----- | ---------- | ------------ |
| Private | `080000 - 083999` | `PRIVATE` | service-internal only, redacted on every outbound channel |
| System | `084000 - 086999` | `SYSTEM` | other services over gRPC mTLS, redacted toward browsers |
| Public | `087000 - 089999` | `PUBLIC` | safe for clients/browsers on any channel |

The catalog (`app/domain/error/error_code.py`) contains the shared Common block (`E000000 - E007008`) plus the Notification block:

| errorKey | Zone | gRPC status | Meaning |
| -------- | ---- | ----------- | ------- |
| `E080000` | Private | INTERNAL | Internal Notification Service error |
| `E080001` | Private | INTERNAL | Email template render error |
| `E084000` | System | UNAVAILABLE | Transient email delivery failure, retryable |
| `E087000` | Public | INVALID_ARGUMENT | Invalid recipient |
| `E087001` | Public | INVALID_ARGUMENT | Missing content (template_name or body) |

**Usage:** business code throws one of the three base classes `PrivateError` / `SystemError` / `PublicError` (in `common/exception/AppException.py`) carrying an `error_key` from the catalog:

```python
# Malformed recipient — client error
raise PublicError("E087000")

# Flaky SMTP — other services may retry
raise SystemError("E084000")
```

**Redaction flow:** handlers do **not** catch errors. Every exception bubbles up to `AppExceptionInterceptor` (`api/grpc/interceptor/`), which redacts per the `GRPC_INTERNAL` channel (via `redaction.py`) then `abort`s with the matching status and `xime-error` / `xime-error-code` trailing metadata. Since gRPC here is service-to-service over mTLS, `SYSTEM` and `PUBLIC` pass through and only `PRIVATE` collapses to `E000000`. This service is gRPC-only, with no REST handler.

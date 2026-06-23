# Notification Service

**English** | [Tiếng Việt](README-vn.md)

> Lightweight notification delivery infrastructure for the Xime Base Platform — sending transactional emails and SMS (future) on behalf of other services.

---

Notification Service is the **outbound communication layer** of the Xime Base Platform. It is an infrastructure service with no business domain knowledge — it does not know whether a message is an order confirmation, a password reset code, or a security alert. Other services call it when they need to deliver a notification to an end user.

```
Application Services (social, ecommerce, SaaS, AI)
              ↓ gRPC + mTLS
         Identity Service ──→ SendEmail (OTP code in template data)
         User Service     ──→ SendEmail (OTP code in template data)
         Payment Service  ──→ SendEmail (transaction receipts)
              ↓ gRPC + mTLS
       Notification Service
              ↓
     ┌────────┴────────┐
   Email           Phone/SMS
  (SMTP)        (future — SMS gateway)
     ↓                ↓
   User             User
```

---

## What Notification Service Does

**Email Delivery**
- Send transactional emails via named templates or pre-rendered body
- Render HTML email templates via Jinja2
- Normalize recipient address before delivery

**Durable Delivery (outbox)**
- Persist every email (`email_notifications` table) for retry, audit, and idempotency
- Automatic retry with exponential backoff on transient failures; dead-letter when exhausted
- Optional caller-supplied `idempotency_key` to avoid duplicate sends
- Background workers: retry due notifications and clean up old rows by retention

## What Notification Service Does NOT Do

- Does not generate OTP codes — OTP lifecycle belongs to the calling service
- Does not store or verify OTP codes
- Does not know the business meaning of a notification
- Does not manage user notification preferences
- Does not authenticate end users
- Does not originate communication — it only delivers on request

---

## Key Design Decisions

### Infrastructure Service with No Domain Knowledge

Notification Service is a delivery pipeline, not a business service. The caller encodes all business context in the template name and data it sends. Notification Service knows nothing about "order confirmation", "password reset", or "OTP verification" — it only knows "send this template to this recipient."

### Caller Owns OTP Lifecycle

OTP generation, storage, and verification are the **caller's responsibility**. When Identity Service needs to send a login MFA code, it:
1. Generates the OTP code itself
2. Stores the hash in its own database
3. Calls Notification Service's `SendEmail` with the OTP code in the template data
4. Verifies the submitted code against its own records

Notification Service simply renders the template and delivers the email.

### Caller Trust via mTLS

All callers must present a valid mTLS certificate issued by Trust Service. Notification Service does not verify end-user identity — it trusts the calling service completely.

### Immutable Domain Model

Domain objects (`EmailNotification`) are plain Python classes that enforce their
invariants in the constructor and expose state through read-only properties. They
are immutable: state changes (`mark_sent`, `schedule_retry`, `dead_letter`) return
new instances instead of mutating in place. IDs are an `Id` value object (KSUID, 24
bytes), not raw `bytes`.

---

## Quick Start

```bash
# Install Xime Framework from local path
pip install -e "D:\code\xime\xime framework"

# Install service dependencies
pip install -e .

# Run the service
python -m app.main
```

gRPC: `9092`

---

## Architecture

Notification Service follows **Hexagonal Architecture** (Ports and Adapters) with DDD tactical patterns, built on Python + Xime Framework:

```
app/
├── api/          ← Input adapters (gRPC handlers, mappers, interceptors)
├── application/  ← Use cases, services (retry/delivery/cleanup), ports, DTOs
├── domain/       ← Pure Python classes + value objects (Id, EmailAddress)
├── infrastructure/ ← SMTP adapter, Jinja2 engine, persistence (entity/mapper/repository)
├── scheduler/    ← Background jobs (email retry, retention cleanup)
├── integration/  ← Trust Service mTLS bootstrap + cert/key sync
├── config/       ← DI binding, gRPC, scheduler configuration
└── common/       ← Constants, exceptions, utilities
```

Domain layer has no dependency on infrastructure, framework, or database. All dependencies point inward. Persistence uses PostgreSQL + Alembic (tables: `trust_*`, `email_notifications`).

---

## Documentation

| Document | Description |
|---|---|
| [Overview](docs/en/overview.md) | Role, capabilities, position in Base Platform |
| [Architecture](docs/en/architecture.md) | Layer structure, directory layout, DDD patterns |
| [OTP Delivery Pattern](docs/en/otp-system.md) | How callers deliver OTP emails using Notification Service |
| [API Reference](docs/en/api.md) | gRPC proto definitions, usage rules |
| [Integration](docs/en/integration.md) | How Identity Service, User Service, and others call this service |

---

## Base Platform Services

| Service | Role |
|---|---|
| `trust-service` | Trust infrastructure — CA, mTLS, JWT signing keys |
| `identity-service` | Authentication infrastructure — JWT, refresh tokens |
| `user-service` | Human Identity Domain Service |
| `data-service` | Data infrastructure — object storage, permission |
| `notification-service` | **Notification delivery — email, SMS** |
| `payment-service` | Payment processing |

---

## Project Status

Notification Service is in **active development**. Email delivery (templates + SMTP),
the durable outbox (persistence, retry with backoff, dead-letter, idempotency, retention
cleanup), gRPC API, Trust mTLS integration, and observability (structured JSON logging +
Prometheus metrics) are implemented and covered by tests. SMS is planned next.

---

## License

MIT

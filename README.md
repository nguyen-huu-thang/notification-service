# Notification Service

**English** | [Tiếng Việt](README-vn.md)

> Lightweight notification delivery infrastructure for the Xime Base Platform — sending transactional emails, OTP codes, and SMS (future) on behalf of other services.

---

Notification Service is the **outbound communication layer** of the Xime Base Platform. It is an infrastructure service with no business domain knowledge — it does not know whether a message is an order confirmation, a password reset, or a security alert. Other services call it when they need to deliver a notification to an end user.

```
Application Services (social, ecommerce, SaaS, AI)
              ↓ gRPC + mTLS
         Identity Service ──→ SendOtpEmail (MFA, email verification)
         User Service     ──→ SendOtpEmail (phone/email change confirmation)
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
- Send transactional emails (OTP codes, system notifications, custom messages)
- Render HTML email templates via Jinja2
- Normalize recipient address before delivery

**OTP System**
- Generate secure 6-digit OTP codes
- Hash and store OTP records in the database (never stores plaintext)
- Verify submitted OTP codes — single-use, time-limited
- Support multiple OTP types: email verification, login MFA, password reset, and more

## What Notification Service Does NOT Do

- Does not know the business meaning of a notification
- Does not manage user notification preferences
- Does not authenticate end users
- Does not originate communication — it only delivers on request
- Does not retry failed sends (caller decides retry strategy)

---

## Key Design Decisions

### Infrastructure Service with No Domain Knowledge

Notification Service is a delivery pipeline, not a business service. The caller encodes all business context in the template name and data it sends. Notification Service knows nothing about "order confirmation" or "password reset" — it only knows "send this template to this recipient."

### OTP Ownership

Notification Service owns the full OTP lifecycle — generation, storage, and verification. The caller receives an `otp_id` and later presents the `otp_id + code` to verify. This separation means the caller never touches the raw OTP code or its hash.

### Caller Trust via mTLS

All callers must present a valid mTLS certificate issued by Trust Service. Notification Service does not verify end-user identity — it trusts the calling service completely.

### Immutable Domain Model

Domain objects (`OtpRecord`, `EmailNotification`) are frozen Python dataclasses. State changes (e.g., marking an OTP as used) return new instances instead of mutating in place.

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
├── api/          ← Input adapters (gRPC handlers, mappers)
├── application/  ← Use cases, port interfaces, DTOs
├── domain/       ← Pure Python dataclasses (frozen=True)
├── infrastructure/ ← SMTP adapter, Jinja2 template, SQLAlchemy persistence
├── config/       ← DI binding configuration
└── common/       ← Constants, exceptions, utilities
```

Domain layer has no dependency on infrastructure, framework, or database. All dependencies point inward.

---

## Documentation

| Document | Description |
|---|---|
| [Overview](docs/en/overview.md) | Role, capabilities, position in Base Platform |
| [Architecture](docs/en/architecture.md) | Layer structure, directory layout, DDD patterns |
| [OTP System](docs/en/otp-system.md) | OTP lifecycle, security design, OTP types |
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
| `notification-service` | **Notification delivery — email, OTP, SMS** |
| `payment-service` | Payment processing |

---

## Project Status

Notification Service is in **active development**. Domain model and common layer are complete. Use case, infrastructure, and gRPC API implementation are in progress.

---

## License

MIT

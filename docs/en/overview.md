# Overview

**English** | [Tiếng Việt](../vn/overview.md)

---

## What is Notification Service?

Notification Service is the **outbound communication infrastructure** of the Xime Base Platform.

Its role is to be the single point responsible for delivering messages to the outside world — via email today, via SMS in the future. When any service in the platform needs to reach an end user, it delegates the delivery to Notification Service.

```
Base Platform Services
  identity-service → SendEmail (OTP code in template data)
  user-service     → SendEmail (OTP code in template data)
  payment-service  → SendEmail (transaction receipts)

Application Layer Services
  order-service      → SendEmail (order confirmation)
  workspace-service  → SendEmail (workspace invitations)
         ↓  (all outbound communication flows through here)
   Notification Service
         ↓
   SMTP server → Email
   SMS gateway → Phone (future)
```

---

## Position in Base Platform

The Xime Base Platform is divided into two layers:

### Base Platform (core services)

Generic, reusable infrastructure services built once and shared across all applications:

| Service | Role |
|---|---|
| `trust-service` | Trust infrastructure — CA, mTLS, JWT signing keys |
| `identity-service` | Authentication — JWT issuance, refresh tokens |
| `user-service` | Human Identity Domain — credentials, account state |
| `data-service` | Data infrastructure — object storage, permission |
| `notification-service` | **Notification delivery — email, SMS** |
| `payment-service` | Payment processing |

### Application Layer (business services)

Application-specific logic that relies on Base Platform:

- **Social Network**: post-service, comment-service, media-service
- **Ecommerce**: product-service, order-service
- **SaaS / AI**: workspace-service, dataset-service, ai-agent-service

Notification Service serves all of these — both core platform services and application-layer services — whenever they need to deliver a message to an end user.

---

## Capability: Email Delivery

Notification Service has one core capability: deliver emails on behalf of callers.

```
Caller
   → SendEmail(to, subject, template_name, template_data)
        ↓
Notification Service
   → normalize recipient address
   → render Jinja2 template with provided data
   → send via SMTP adapter
   → return notification_id
```

For callers with a pre-rendered body:

```
Caller
   → SendEmail(to, subject, body)
        ↓
Notification Service
   → normalize recipient address
   → send via SMTP adapter
   → return notification_id
```

Notification Service does not know what the email means. The caller provides the template name, the data, and the recipient — Notification Service only handles rendering and delivery.

---

## Who Calls Notification Service?

All callers communicate via **gRPC + mTLS**. Notification Service has no REST API — it only accepts gRPC connections.

### Base Platform Services (internal callers)

| Service | Use Cases |
|---|---|
| **Identity Service** | Send login MFA email, email verification email on registration, password reset email |
| **User Service** | Send new email confirmation email, phone confirmation email, password change notification |

For OTP flows, these services generate and manage the OTP code themselves, then pass the code as template data when calling `SendEmail`.

### Application Layer (business callers)

Application services send custom transactional emails relevant to their business domain:

| Example Use Case | Notification Type |
|---|---|
| Order confirmation | `SendEmail` (template: `order-confirmation`) |
| Appointment reminder | `SendEmail` |
| Transaction alert | `SendEmail` (template: `transaction-alert`) |
| Workspace invitation | `SendEmail` (template: `workspace-invite`) |

Application services do not know about SMTP or Jinja2 internals — they call gRPC and pass: recipient, subject, template name, and data. The delivery details are entirely Notification Service's concern.

---

## Design Philosophy

| Question | Answer |
|---|---|
| What is Notification Service? | Outbound delivery infrastructure — the platform's single notification gateway |
| What does it manage? | Email delivery and template rendering |
| Does it manage OTP codes? | No — OTP lifecycle is the caller's responsibility |
| Does it know what a notification means? | No — that is the caller's concern |
| Does it authenticate end users? | No — it trusts the calling service via mTLS |
| What if SMTP goes down? | The email is persisted (PENDING/FAILED); a worker retries it with backoff, dead-lettering when exhausted |
| Is it stateful? | Yes — PostgreSQL stores the email outbox + mTLS cert/key |

---

## What Notification Service Is NOT

- Not a business service — it has no knowledge of order flows, auth flows, or user journeys
- Not an OTP manager — it does not generate, store, or verify OTP codes
- Not a message broker — it takes no async events (callers invoke it directly over gRPC); it does have an internal outbox + retry, but is not a full queueing system
- Not a notification preferences manager — it does not decide who wants what
- Not a user-facing service — end users never interact with it directly

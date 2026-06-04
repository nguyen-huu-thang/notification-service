# Overview

**English** | [Tiếng Việt](../vn/overview.md)

---

## What is Notification Service?

Notification Service is the **outbound communication infrastructure** of the Xime Base Platform.

Its role is to be the single point responsible for delivering messages to the outside world — via email today, via SMS in the future. No other service sends emails or manages OTP codes directly. When any service in the platform needs to reach an end user, it delegates to Notification Service.

```
Base Platform Services
  identity-service → SendOtpEmail (MFA codes, email verification)
  user-service     → SendOtpEmail (credential change confirmation)
  payment-service  → SendEmail    (transaction receipts)

Application Layer Services
  order-service    → SendEmail    (order confirmation)
  workspace-service → SendEmail   (workspace invitations)
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
| `notification-service` | **Notification delivery — email, OTP, SMS** |
| `payment-service` | Payment processing |

### Application Layer (business services)

Application-specific logic that relies on Base Platform:

- **Social Network**: post-service, comment-service, media-service
- **Ecommerce**: product-service, order-service
- **SaaS / AI**: workspace-service, dataset-service, ai-agent-service

Notification Service serves all of these — both core platform services and application-layer services — whenever they need to deliver a message to an end user.

---

## Two Capabilities

Notification Service provides two independent capabilities that share infrastructure but have separate concerns:

### A. Email Delivery

Used for sending any outbound email — including OTP emails, system notifications, and application-defined custom messages:

```
Caller
   → SendEmail(to, subject, body, channel)
        ↓
Notification Service
   → normalize recipient address
   → validate recipient format
   → send via SMTP adapter
   → return notification_id
```

For template-based emails, the caller passes a template name and context data instead of a pre-rendered body:

```
Caller
   → SendEmail(to, template_name, template_context, channel)
        ↓
Notification Service
   → render template (Jinja2)
   → send via SMTP adapter
```

### B. OTP System

Used for verification flows where the platform needs to prove the user controls an email address or phone number:

```
Caller
   → SendOtpEmail(channel, target, otp_type, context_id)
        ↓
Notification Service
   → generate 6-digit OTP code
   → hash OTP code (HMAC-SHA256)
   → save OtpRecord to database (expires in 5 minutes)
   → render OTP email template
   → send email
   → return otp_id + expires_at
        ↓
Caller holds otp_id, waits for user to submit the code
        ↓
Caller
   → VerifyOtp(otp_id, code)
        ↓
Notification Service
   → load OtpRecord by otp_id
   → check: not expired, not already used
   → verify: hash(code) == stored otp_hash
   → mark OtpRecord as used (one-time enforcement)
   → return success/failure
```

The caller never sees the raw OTP code or its hash. Notification Service owns the entire OTP lifecycle.

---

## Who Calls Notification Service?

All callers communicate via **gRPC + mTLS**. Notification Service has no REST API — it only accepts gRPC connections.

### Base Platform Services (internal callers)

| Service | Use Cases |
|---|---|
| **Identity Service** | Login MFA OTP, email verification OTP on registration, password reset OTP |
| **User Service** | New email confirmation OTP, phone number confirmation OTP, password change notification |

### Application Layer (business callers)

Application services send custom transactional emails relevant to their business domain:

| Example Use Case | Notification Type |
|---|---|
| Order confirmation | `SendEmail` (template: `order-confirmation`) |
| Appointment reminder | `SendEmail` or `SendSms` |
| Transaction alert | `SendEmail` (template: `transaction-alert`) |
| Workspace invitation | `SendEmail` (template: `workspace-invite`) |

Application services do not know about SMTP, Jinja2 templates, or OTP storage — they call gRPC and pass: channel, recipient, template name, and data. The delivery details are entirely Notification Service's concern.

---

## Design Philosophy

| Question | Answer |
|---|---|
| What is Notification Service? | Outbound delivery infrastructure — the platform's single notification gateway |
| What does it manage? | Email delivery + OTP lifecycle (generate, store, verify) |
| Does it know what a notification means? | No — that is the caller's concern |
| Does it authenticate end users? | No — it trusts the calling service via mTLS |
| Who owns OTP codes? | Notification Service — callers only receive an `otp_id` |
| What if SMTP goes down? | Notification Service returns an error; the caller decides whether to retry |
| Is it stateful? | Yes — OTP records are persisted in PostgreSQL |

---

## What Notification Service Is NOT

- Not a business service — it has no knowledge of order flows, auth flows, or user journeys
- Not a message broker — it does not queue or retry sends internally
- Not a notification preferences manager — it does not decide who wants what
- Not a user-facing service — end users never interact with it directly

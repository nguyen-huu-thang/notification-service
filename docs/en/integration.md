# Integration

**English** | [Tiếng Việt](../vn/integration.md)

---

## Overview

Notification Service is a **downstream service** — it is called by others, never calling them back. It integrates with the platform in two ways:

| Integration | Direction | When |
|---|---|---|
| mTLS trust setup | Trust Service → Notification Service | Startup only |
| Notification delivery | Any service → Notification Service | Per user action |

Notification Service does not call Identity Service, User Service, or any other service at runtime. It trusts the caller's certificate and executes the delivery request.

---

## Trust Service Integration

### mTLS Bootstrap (Startup)

Notification Service must establish its mTLS identity before it can accept gRPC connections. This happens once at startup:

```
Notification Service startup
      ↓
1. Call Trust Service: GetRootCertificate
      → receive Root CA certificate (PEM)
      → pin Root CA in gRPC server TLS trust store

2. Call Trust Service: BootstrapCert (via admin, once on first deployment)
      → receive X.509 leaf certificate + initial refresh token
      → certificate SAN contains service_id = "notification-service"

3. Load certificate + private key into gRPC server TLS context
      → Notification Service is now reachable over mTLS
      → all incoming connections verified against pinned Root CA
```

### Certificate Rotation

Notification Service rotates its certificate before expiry (~100 days after issuance):

```
Detect cert approaching rotation window
      ↓
Generate new key pair (in memory)
      ↓
Call Trust Service: RotateCertificate
  → token_id + refresh_token (one-time)
  → new public key (PEM)
  → over existing mTLS connection
      ↓
Trust Service issues new cert
      ↓
Load new cert + key pair into TLS configuration
      ↓
Store new refresh token for next rotation
```

### Resilience

If Trust Service is unavailable:
- mTLS continues to work using the existing certificate
- Notification Service accepts and processes requests normally
- Only cert rotation is blocked — handled when Trust Service recovers

---

## Identity Service Integration

Identity Service is the **primary caller** of Notification Service for authentication events. It owns the OTP lifecycle and calls Notification Service only to deliver the email.

### Login MFA

```
User attempts login with MFA enabled
      ↓
Identity Service
  → generate OTP code
  → save HMAC(otp_code) in its own database
  → gRPC + mTLS → Notification Service
  SendEmailRequest {
    to:      "user@example.com",
    subject: "Your login verification code",
    tmpl: {
      template_name: "otp-email",
      context: { "otp_code": "847291", "expires_min": "5" }
    }
  }
      ↓
Notification Service → renders template → sends email → returns notification_id
      ↓
Identity Service → store otp_id in session → return challenge response to client
      ↓
User submits OTP code
      ↓
Identity Service
  → verify HMAC(submitted_code) == stored hash
  → mark OTP as used in its own database
  → issue JWT + refresh token
```

### Email Verification on Registration

```
User registers with email address
      ↓
Identity Service
  → generate OTP → store hash → SendEmail { template: "otp-email", otp_code, ... }
      ↓
Notification Service → sends email
      ↓
Identity Service stores otp_id + waits
      ↓
User submits OTP → Identity Service verifies locally → marks email as verified
```

### Password Reset

```
User requests password reset
      ↓
Identity Service
  → generate OTP → store hash → SendEmail { template: "otp-email", otp_code, ... }
      ↓
Notification Service → sends email
      ↓
User submits OTP → Identity Service verifies locally → authorizes password change
```

### Login Alert (no OTP)

```
Suspicious login detected
      ↓
Identity Service
  → SendEmail {
      to:      "user@example.com",
      subject: "New login detected",
      tmpl:    { template_name: "login-alert", context: { "device": "...", "location": "..." } }
    }
      ↓
Notification Service → sends alert email
```

---

## User Service Integration

User Service calls Notification Service for credential change confirmation flows. It also owns the OTP lifecycle for these flows.

### Email Change Confirmation

```
User requests email address change
      ↓
User Service
  → generate OTP → store hash
  → SendEmail {
      to:   new_email,
      tmpl: { template_name: "otp-email", context: { "otp_code": "...", "action": "confirm your new email" } }
    }
      ↓
Notification Service → sends OTP to new email
      ↓
User submits code → User Service verifies locally → updates email address
```

### Phone Confirmation

```
User adds/changes phone number
      ↓
User Service
  → generate OTP → store hash
  → (future) SendSms { to: phone_number, template: "otp-sms", context: { "otp_code": "..." } }
      ↓
Notification Service → sends SMS (when implemented)
      ↓
User submits code → User Service verifies locally → stores verified phone number
```

---

## Application Layer Integration

Application services in the business layer (ecommerce, social, SaaS, AI) call Notification Service for domain-specific notifications using `SendEmail` with named templates.

### Order Confirmation (example)

```
Order Service (application layer)
  → gRPC + mTLS → Notification Service
  SendEmailRequest {
    to:      "buyer@example.com",
    subject: "Your order has been confirmed",
    tmpl: {
      template_name: "order-confirmation",
      context: {
        "order_id":    "ORD-20240601-001",
        "total":       "199,000 VND",
        "items":       "...",
        "delivery_at": "2024-06-05"
      }
    }
  }
      ↓
Notification Service → render Jinja2 template → send email → return notification_id
```

---

## Integration Summary

```
Trust Service
      ↓ provides mTLS certificate (startup only)

Notification Service
      │
      ├── Identity Service
      │     └── SendEmail (otp-email, login-alert, password-changed, ...)
      │
      ├── User Service
      │     └── SendEmail (otp-email, password-changed, ...)
      │
      └── Application Services (any)
            └── SendEmail (custom templates per use case)
```

---

## What Notification Service Does NOT Do at Runtime

- Does not call back to Identity Service or User Service
- Does not fetch user preferences or contact details — all targeting is provided by the caller
- Does not verify end-user identity — caller verification is done via mTLS at the service level
- Does not participate in any authentication or authorization decision — it only delivers
- Does not store OTP records — the caller manages OTP state

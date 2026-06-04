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

Identity Service is the **primary caller** of Notification Service within Base Platform. It triggers OTP flows for authentication events.

### Login MFA

```
User attempts login with MFA enabled
      ↓
Identity Service
  → gRPC + mTLS → Notification Service
  SendOtpEmailRequest {
    channel:    "EMAIL",
    target:     "user@example.com",
    otp_type:   "LOGIN_MFA",
    context_id: <identity_id>
  }
      ↓
Notification Service
  → generate OTP
  → save OtpRecord (expires 5 min)
  → send email
  → return otp_id + expires_at
      ↓
Identity Service
  → store otp_id in session
  → return challenge response to client
      ↓
User submits OTP code
      ↓
Identity Service
  → gRPC + mTLS → Notification Service
  VerifyOtpRequest { otp_id, code }
      ↓
Notification Service
  → verify → mark used → return success
      ↓
Identity Service
  → issue JWT + refresh token
```

### Email Verification on Registration

```
User registers with email address
      ↓
Identity Service
  → SendOtpEmail { otp_type: "VERIFY_EMAIL", target: email, context_id: identity_id }
      ↓
Notification Service → sends OTP email
      ↓
Identity Service stores otp_id
      ↓
User submits OTP → Identity Service → VerifyOtp
      ↓
Notification Service confirms → Identity Service marks email as verified
```

### Password Reset

```
User requests password reset
      ↓
Identity Service
  → SendOtpEmail { otp_type: "RESET_PASSWORD", target: email, context_id: identity_id }
      ↓
Notification Service → sends reset OTP email
      ↓
User submits OTP → Identity Service → VerifyOtp
      ↓
Notification Service confirms → Identity Service authorizes password change
```

---

## User Service Integration

User Service calls Notification Service for credential change confirmation flows.

### Email Change Confirmation

```
User requests email address change
      ↓
User Service
  → SendOtpEmail {
      otp_type:   "CONFIRM_EMAIL_CHANGE",
      target:     new_email,
      context_id: user_id
    }
      ↓
Notification Service → sends OTP to new email
      ↓
User submits code → User Service → VerifyOtp
      ↓
Notification Service confirms → User Service updates email address
```

### Phone Confirmation

```
User adds/changes phone number
      ↓
User Service
  → SendOtpEmail (or future SendOtpSms) {
      otp_type:   "CONFIRM_PHONE",
      target:     phone_number,
      context_id: user_id
    }
      ↓
Notification Service → sends OTP
      ↓
User submits code → User Service → VerifyOtp
      ↓
Notification Service confirms → User Service stores verified phone number
```

---

## Application Layer Integration

Application services in the business layer (ecommerce, social, SaaS, AI) call Notification Service for domain-specific notifications. They use `SendEmail` with named templates.

### Order Confirmation (example)

```
Order Service (application layer)
  → gRPC + mTLS → Notification Service
  SendEmailRequest {
    to:            "buyer@example.com",
    subject:       "Your order has been confirmed",
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
Notification Service
  → render Jinja2 template
  → send email
  → return notification_id
```

Application services do not know the SMTP host, template engine, or OTP subsystem. They only specify what to send and to whom.

---

## Integration Summary

```
Trust Service
      ↓ provides mTLS certificate (startup only)

Notification Service
      │
      ├── Identity Service
      │     ├── SendOtpEmail (LOGIN_MFA, VERIFY_EMAIL, RESET_PASSWORD)
      │     └── VerifyOtp
      │
      ├── User Service
      │     ├── SendOtpEmail (CONFIRM_EMAIL_CHANGE, CONFIRM_PHONE)
      │     └── VerifyOtp
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

# OTP Delivery Pattern

**English** | [Tiếng Việt](../vn/otp-system.md)

---

## Overview

Notification Service does **not** generate, store, or verify OTP codes. OTP lifecycle — generation, storage, and verification — belongs entirely to the **calling service** (Identity Service, User Service, etc.).

Notification Service's role in an OTP flow is simple: receive a `SendEmail` call with the OTP code already included in the template data, render the template, and deliver the email.

```
Identity Service
      ↓ generates OTP code
      ↓ stores HMAC-SHA256(otp_code) in its database
      ↓ SendEmail(to, template="otp-email", data={otp_code, expires_min})
Notification Service
      ↓ renders template with otp_code
      ↓ sends email via SMTP
      ↓ returns notification_id
Identity Service
      ↓ waits for user to submit code
User submits code → Identity Service
      ↓ verifies HMAC(submitted_code) == stored hash
      ↓ marks OTP as used in its own database
      ↓ proceeds (issue JWT, confirm change, etc.)
```

---

## Why the Caller Owns OTP

OTP is an authentication and security concept — it belongs to the auth domain, not to the delivery infrastructure. Moving OTP lifecycle into Notification Service would:

- Force Notification Service to store auth-domain data (`otp_type`, `context_id`, `identity_id`)
- Create a dependency where Identity Service must call back to Notification Service just to verify a 6-digit code
- Violate the "no domain knowledge" boundary that makes Notification Service reusable across all applications

By keeping OTP in the calling service, each service manages its own security policy: expiry duration, retry limits, brute-force protection, and audit logging are all the caller's concern.

---

## Caller Implementation Guide

### 1. Generate and Store the OTP

```python
import secrets
import hmac
import hashlib

# Generate
otp_code = f"{secrets.randbelow(1_000_000):06d}"  # "847291"

# Hash — never store raw code
secret_key = b"..."  # from config
otp_hash = hmac.new(secret_key, otp_code.encode(), hashlib.sha256).hexdigest()

# Store in caller's own DB
await otp_repository.save(OtpRecord(
    otp_id     = generate_id(),
    target     = normalize_email(user_email),
    otp_hash   = otp_hash,
    otp_type   = OtpType.LOGIN_MFA,
    context_id = identity_id,
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5),
    is_used    = False,
))
```

### 2. Call Notification Service to Deliver

```python
await notification_stub.SendEmail(SendEmailRequest(
    to      = user_email,
    subject = "Your verification code",
    tmpl    = TemplateContent(
        template_name = "otp-email",
        context       = {
            "otp_code":    otp_code,       # raw code — goes to user's inbox only
            "expires_min": "5",
        },
    ),
))
```

### 3. Verify When User Submits

```python
record = await otp_repository.find_by_id(otp_id)

if record is None:
    raise OtpNotFoundError()
if datetime.now(timezone.utc) >= record.expires_at:
    raise OtpExpiredError()
if record.is_used:
    raise OtpAlreadyUsedError()

submitted_hash = hmac.new(secret_key, submitted_code.encode(), hashlib.sha256).hexdigest()
if not hmac.compare_digest(submitted_hash, record.otp_hash):
    raise OtpInvalidError()

# Mark as used
await otp_repository.save(record.mark_used())
```

---

## Notification Service Template Contract

Notification Service provides an `otp-email` template that expects these context variables:

| Variable | Required | Description |
|---|---|---|
| `otp_code` | Yes | The 6-digit OTP code to display |
| `expires_min` | No | Expiry time in minutes (default: shown as "a few minutes") |
| `action` | No | Human-readable description of the action (e.g., "log in", "reset your password") |

For other notification types (login alert, password changed, etc.), see the templates in `infrastructure/template/templates/`.

---

## Security Responsibilities

| Concern | Owner |
|---|---|
| OTP code generation (secure random) | Calling service |
| OTP hash storage (no plaintext) | Calling service |
| OTP expiry enforcement | Calling service |
| One-time use enforcement | Calling service |
| Rate limiting (OTPs per recipient) | Calling service |
| Brute-force protection (failed attempts) | Calling service |
| Template rendering and email delivery | **Notification Service** |

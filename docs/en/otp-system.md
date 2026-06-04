# OTP System

**English** | [Tiếng Việt](../vn/otp-system.md)

---

## Overview

The OTP (One-Time Password) system in Notification Service manages the full lifecycle of verification codes used across the platform. It is the only component responsible for generating, storing, and verifying OTP codes — no other service touches OTP data directly.

```
Identity Service / User Service
      ↓ SendOtpEmail(channel, target, otp_type, context_id)
Notification Service
      ↓ generates code → hashes → stores → sends email
      ↓ returns otp_id + expires_at
Caller holds otp_id
      ↓ user submits code to caller
Caller
      ↓ VerifyOtp(otp_id, code)
Notification Service
      ↓ looks up record → checks expiry → verifies hash → marks used
      ↓ returns success/failure
Caller proceeds (issue JWT, confirm change, etc.)
```

---

## OTP Types

Each OTP is created with a specific `otp_type` that identifies its purpose:

| OTP Type | Used by | Purpose |
|---|---|---|
| `VERIFY_EMAIL` | Identity Service, User Service | Confirm ownership of an email address |
| `RESET_PASSWORD` | Identity Service | Authorize a password reset flow |
| `LOGIN_MFA` | Identity Service | Second-factor challenge during login |
| `CONFIRM_EMAIL_CHANGE` | User Service | Verify new email address when changing account email |
| `CONFIRM_PHONE` | User Service | Verify phone number ownership |

The `otp_type` is stored in the `OtpRecord` and returned in responses for observability. Notification Service does not act differently based on type — type is informational for the caller.

---

## OTP Record Domain Model

```python
@dataclass(frozen=True)
class OtpRecord:
    otp_id:     bytes     # 24-byte KSUID — unique identifier returned to caller
    channel:    OtpChannel  # EMAIL | PHONE
    target:     str       # normalized recipient (email address or phone number)
    otp_hash:   str       # HMAC-SHA256 hash of the raw OTP code
    otp_type:   OtpType   # purpose of this OTP
    context_id: bytes     # caller-provided ID linking this OTP to a business entity
    expires_at: datetime  # when this OTP becomes invalid
    is_used:    bool      # True after successful verification (one-time enforcement)
    created_at: datetime
```

`context_id` is an opaque identifier provided by the caller — for example, the `identity_id` or `user_id` of the entity undergoing verification. Notification Service stores it but does not interpret it.

---

## Send OTP Flow

```
SendOtpEmailUseCase.execute(command)
      ↓
1. Generate OTP code
      → secrets.randbelow(1_000_000)
      → format as 6-digit string (zero-padded)

2. Hash OTP code
      → HMAC-SHA256(key=SECRET_KEY, msg=otp_code)
      → store hash only — raw code never persisted

3. Create OtpRecord
      → otp_id     = generate_id()         (24-byte KSUID)
      → otp_hash   = computed above
      → expires_at = now + 5 minutes
      → is_used    = False

4. Save OtpRecord to database
      → SaveOtpPort.save(otp_record)

5. Render email template
      → TemplatePort.render("otp-email", {"otp_code": raw_code})
      → raw_code is passed to template but never stored

6. Send email
      → EmailSenderPort.send(target, subject, rendered_body)

7. Return SendOtpResult
      → otp_id, expires_at
      (caller stores otp_id; raw code goes only to the user's inbox)
```

---

## Verify OTP Flow

```
VerifyOtpUseCase.execute(command)
      command = { otp_id, code }
      ↓
1. Load OtpRecord
      → LoadOtpPort.find_by_id(otp_id)
      → raises OtpNotFoundError if not found

2. Check expiry
      → now > otp_record.expires_at → raises OtpExpiredError

3. Check already used
      → otp_record.is_used == True → raises OtpAlreadyUsedError

4. Verify code
      → HMAC-SHA256(SECRET_KEY, submitted_code) == otp_record.otp_hash
      → mismatch → raises OtpVerificationFailedError

5. Mark as used
      → updated = otp_record.mark_used()      (returns new frozen instance)
      → SaveOtpPort.save(updated)             (upsert / update in DB)

6. Return VerifyOtpResult
      → { success: True }
```

---

## Security Design

### No Plaintext Storage

Raw OTP codes are **never stored** — not in the database, not in logs. Only the HMAC-SHA256 hash is persisted.

```
raw_code  → HMAC-SHA256(SECRET_KEY, raw_code) → stored in otp_hash column
```

The raw code exists only in memory during the `SendOtpEmailUseCase` execution and in the email body delivered to the user.

### One-Time Enforcement

Once verified successfully, `is_used` is set to `True` and persisted. Any subsequent verification attempt on the same `otp_id` returns `OtpAlreadyUsedError` — even if the correct code is submitted.

### Time-Limited Validity

OTP codes expire after a short TTL (default: 5 minutes). An expired OTP cannot be verified even if the code is correct. The `expires_at` timestamp is stored at creation time using UTC.

### Timing-Safe Comparison

Hash comparison uses constant-time equality (`hmac.compare_digest`) to prevent timing attacks:

```python
import hmac
valid = hmac.compare_digest(expected_hash, submitted_hash)
```

### Identifier Design

`otp_id` is a 24-byte KSUID — sortable, globally unique, and opaque. It does not encode any information about the OTP type, recipient, or caller. The caller receives only `otp_id` — they cannot derive the OTP code from it.

---

## Database Schema

```sql
CREATE TABLE otp_records (
    otp_id      BYTEA        PRIMARY KEY,         -- KSUID 24 bytes
    channel     VARCHAR(10)  NOT NULL,             -- EMAIL | PHONE
    target      VARCHAR(255) NOT NULL,             -- normalized recipient
    otp_hash    VARCHAR(255) NOT NULL,             -- HMAC-SHA256 hash (never raw)
    otp_type    VARCHAR(50)  NOT NULL,             -- VERIFY_EMAIL | LOGIN_MFA | ...
    context_id  BYTEA,                            -- opaque caller-provided ID
    expires_at  TIMESTAMP    NOT NULL,
    is_used     BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMP    NOT NULL
);

CREATE INDEX idx_otp_target_type ON otp_records (target, otp_type, is_used);
CREATE INDEX idx_otp_expires     ON otp_records (expires_at);
```

The index on `(target, otp_type, is_used)` supports future rate-limiting queries (e.g., "how many unused OTPs of type RESET_PASSWORD has this email received in the last hour?").

---

## OTP Cleanup

Expired OTP records accumulate over time. A scheduled background job (not yet implemented — see roadmap) will periodically delete records where `expires_at < now - retention_window`. Expired records are safe to delete after a short retention window (e.g., 24 hours) since they can no longer be used.

---

## What Notification Service Does NOT Enforce

- **Rate limiting per recipient**: Notification Service does not limit how many OTPs a caller sends to the same address. The calling service (Identity Service, User Service) is responsible for rate limiting at its own layer.
- **OTP type validation**: Notification Service accepts any `otp_type` string. It is the caller's responsibility to send a valid type.
- **Caller authorization by OTP type**: Any authenticated caller (valid mTLS cert) can request any OTP type. Fine-grained authorization by type is a future concern.

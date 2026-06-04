# API Reference

**English** | [Tiếng Việt](../vn/api.md)

---

## Overview

Notification Service exposes a single gRPC API group. There is no REST API — all communication happens over gRPC with mandatory mTLS.

| Group | Purpose |
|---|---|
| **NotificationService** | Send emails, manage OTP lifecycle |

Proto files are located in `app/api/grpc/generated/`.

All callers must present a valid mTLS certificate issued by Trust Service. Unauthenticated connections are rejected at the TLS layer.

---

## NotificationService

```protobuf
service NotificationService {
  // Send a plain email (no OTP)
  rpc SendEmail(SendEmailRequest) returns (SendEmailResponse);

  // Generate an OTP, save it, and send it to the recipient via email
  rpc SendOtpEmail(SendOtpEmailRequest) returns (SendOtpEmailResponse);

  // Verify a submitted OTP code
  rpc VerifyOtp(VerifyOtpRequest) returns (VerifyOtpResponse);
}
```

---

## SendEmail

Send a transactional email directly — either with a pre-rendered body or using a named template.

```protobuf
message SendEmailRequest {
  string to       = 1;  // recipient email address
  string subject  = 2;  // email subject line

  oneof content {
    string body          = 3;  // pre-rendered HTML or plain text
    TemplateContent tmpl = 4;  // render from a named template
  }
}

message TemplateContent {
  string template_name = 1;                  // e.g. "order-confirmation"
  map<string, string> context = 2;           // template variables
}

message SendEmailResponse {
  bytes notification_id = 1;  // 24-byte KSUID of the EmailNotification record
}
```

**Usage notes:**
- `to` is normalized (lowercased, Unicode-normalized) before sending
- `template_name` must match a file in `infrastructure/template/templates/`
- `notification_id` is returned for logging and traceability — it is not used for any further operation

---

## SendOtpEmail

Generate a 6-digit OTP code, store its hash in the database, and send it to the recipient via email.

```protobuf
message SendOtpEmailRequest {
  string channel    = 1;  // always "EMAIL" for this RPC
  string target     = 2;  // recipient email address
  string otp_type   = 3;  // VERIFY_EMAIL | RESET_PASSWORD | LOGIN_MFA | ...
  bytes  context_id = 4;  // opaque ID linking OTP to a business entity (e.g. identity_id)
}

message SendOtpEmailResponse {
  bytes  otp_id     = 1;  // 24-byte KSUID — store this to verify later
  int64  expires_at = 2;  // Unix timestamp (ms) — when the OTP becomes invalid
}
```

**Usage notes:**
- `target` is normalized before use (lowercased, trimmed)
- `otp_id` must be stored by the caller — it is required to verify the OTP later
- `context_id` is stored as-is and returned in responses for traceability; Notification Service does not interpret it
- The raw OTP code goes only to the user's inbox — the caller never sees it

**OTP type values:**

| Value | Meaning |
|---|---|
| `VERIFY_EMAIL` | Confirm ownership of an email address |
| `RESET_PASSWORD` | Authorize a password reset |
| `LOGIN_MFA` | Second-factor challenge during login |
| `CONFIRM_EMAIL_CHANGE` | Verify new email address |
| `CONFIRM_PHONE` | Verify phone number |

---

## VerifyOtp

Verify a submitted OTP code against the stored record.

```protobuf
message VerifyOtpRequest {
  bytes  otp_id = 1;  // returned by SendOtpEmail
  string code   = 2;  // 6-digit code submitted by the user
}

message VerifyOtpResponse {
  bool   success        = 1;
  string failure_reason = 2;  // populated when success = false
}
```

**Failure reasons:**

| Reason | Meaning |
|---|---|
| `NOT_FOUND` | No OTP record exists for the given `otp_id` |
| `EXPIRED` | OTP has passed its `expires_at` timestamp |
| `ALREADY_USED` | OTP was already verified successfully |
| `INVALID_CODE` | The submitted code does not match |

**Usage notes:**
- On success, the OTP record is marked as used — subsequent calls with the same `otp_id` will return `ALREADY_USED`
- On failure, the record is **not** marked as used — the caller may allow the user to retry (subject to the caller's own rate limiting)

---

## gRPC Status Codes

| Situation | gRPC Status |
|---|---|
| Request succeeds | `OK` |
| Invalid recipient format | `INVALID_ARGUMENT` |
| Template not found | `NOT_FOUND` |
| SMTP delivery failed | `UNAVAILABLE` |
| OTP not found | `NOT_FOUND` |
| Any unexpected error | `INTERNAL` |

---

## API Usage Rules

### mTLS Required

All connections must use mTLS. The caller presents its service certificate (issued by Trust Service). Notification Service verifies:

```
1. TLS layer:   cert chain validates against pinned Root CA
2. App layer:   service_id extracted from cert SAN
3. App layer:   cert.service_id == request metadata service_id
```

### Do Not Call on Every User Request

Notification Service is a fire-and-forget delivery service. Callers should:
- Call `SendOtpEmail` once per user action requiring OTP (login, registration, etc.)
- Store the returned `otp_id` in their own session or database — do not call `SendOtpEmail` again to "look up" an existing OTP
- Call `VerifyOtp` once when the user submits their code

### Retry Strategy Belongs to the Caller

If `SendEmail` or `SendOtpEmail` returns `UNAVAILABLE` (SMTP failure), Notification Service has not stored any retry intent. The caller decides whether to retry. For OTP flows, the caller may re-call `SendOtpEmail` to generate a new OTP — the old `otp_id` remains in the database and will expire naturally.

### Summary Table

| Situation | Should call? |
|---|---|
| User requests login OTP | Yes — `SendOtpEmail` |
| User submits OTP code | Yes — `VerifyOtp` |
| Sending order confirmation | Yes — `SendEmail` with template |
| Checking if a previous OTP is still valid | No — use `expires_at` returned at creation |
| Sending the same email multiple times | No — call once; retry only on transport failure |

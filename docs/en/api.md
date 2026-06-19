# API Reference

**English** | [Tiếng Việt](../vn/api.md)

---

## Overview

Notification Service exposes a single gRPC API. There is no REST API — all communication happens over gRPC with mandatory mTLS.

| Group | Purpose |
|---|---|
| **NotificationService** | Send emails on behalf of other services |

Proto files are located in `app/api/grpc/generated/`.

All callers must present a valid mTLS certificate issued by Trust Service. Unauthenticated connections are rejected at the TLS layer.

---

## NotificationService

```protobuf
service NotificationService {
  // Send a transactional email — either from a named template or pre-rendered body
  rpc SendEmail(SendEmailRequest) returns (SendEmailResponse);
}
```

---

## SendEmail

Send a transactional email to a single recipient. Supports two content modes: named template (Jinja2 rendered server-side) or pre-rendered body.

```protobuf
message SendEmailRequest {
  string to      = 1;  // recipient email address
  string subject = 2;  // email subject line

  oneof content {
    string body          = 3;  // pre-rendered HTML or plain text
    TemplateContent tmpl = 4;  // render from a named template
  }

  string idempotency_key = 5;  // optional — same key + same caller returns the existing id
}

message TemplateContent {
  string template_name            = 1;  // e.g. "otp-email", "order-confirmation"
  map<string, string> context     = 2;  // template variables
}

message SendEmailResponse {
  string notification_id = 1;  // 24-byte KSUID as Base62 — for logging and traceability
}
```

**Usage notes:**

- `to` is normalized (lowercased, Unicode-normalized) before sending
- `template_name` must match a file in `infrastructure/template/templates/`
- `notification_id` is returned as a Base62 string for logging and traceability — it is not used for any further operation
- `idempotency_key` (optional): pass it to avoid duplicate sends when the caller retries; the same key from the same caller returns the existing `notification_id` instead of resending
- For OTP emails: the caller generates the OTP code, stores its hash, and passes the raw code as a template variable (e.g., `context["otp_code"] = "123456"`)

**Example — OTP email:**

```
SendEmailRequest {
  to:      "user@example.com",
  subject: "Your verification code",
  tmpl: {
    template_name: "otp-email",
    context: {
      "otp_code":   "847291",
      "expires_min": "5"
    }
  }
}
```

**Example — order confirmation:**

```
SendEmailRequest {
  to:      "buyer@example.com",
  subject: "Your order has been confirmed",
  tmpl: {
    template_name: "order-confirmation",
    context: {
      "order_id":    "ORD-20240601-001",
      "total":       "199,000 VND",
      "delivery_at": "2024-06-05"
    }
  }
}
```

---

## gRPC Status Codes

| Situation | gRPC Status |
|---|---|
| Request succeeds (including accepted-and-pending-retry) | `OK` |
| Invalid recipient format (`E087000`) | `INVALID_ARGUMENT` |
| Missing content: neither body nor template (`E087001`) | `INVALID_ARGUMENT` |
| Template not found (`E087002`) | `INVALID_ARGUMENT` |
| Internal error (DB, unexpected) | `INTERNAL` |

> **Transient** SMTP failures are no longer returned to the caller: the email is accepted
> into the outbox and a worker retries it. The caller only receives errors for the
> validation cases above.

---

## API Usage Rules

### mTLS Required

All connections must use mTLS. The caller presents its service certificate (issued by Trust Service). Notification Service verifies:

```
1. TLS layer:   cert chain validates against pinned Root CA
2. App layer:   service_id extracted from cert SAN
3. App layer:   cert.service_id == request metadata service_id
```

### Durable Delivery (outbox)

Notification Service persists every email, then sends it (hybrid outbox model). On a
transient failure (SMTP down) the email is **not lost**: it stays `FAILED`/`PENDING` and a
worker retries it with exponential backoff, dead-lettering when exhausted. So the caller
**does not need to retry** on transient errors. Client errors (bad recipient/template) are
still returned immediately so the caller can fix them. To stay safe when a caller must
retry, pass an `idempotency_key`.

### Summary Table

| Situation | Should call? |
|---|---|
| Send login OTP to user | Yes — `SendEmail` with `otp-email` template |
| Send order confirmation | Yes — `SendEmail` with `order-confirmation` template |
| Avoid duplicates on retry | Yes — pass `idempotency_key`; same key + same caller returns the existing id |
| Retry yourself on transient SMTP error | Not needed — the outbox worker resends automatically |

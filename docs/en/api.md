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
}

message TemplateContent {
  string template_name            = 1;  // e.g. "otp-email", "order-confirmation"
  map<string, string> context     = 2;  // template variables
}

message SendEmailResponse {
  bytes notification_id = 1;  // 24-byte KSUID — for logging and traceability
}
```

**Usage notes:**

- `to` is normalized (lowercased, Unicode-normalized) before sending
- `template_name` must match a file in `infrastructure/template/templates/`
- `notification_id` is returned for logging and traceability — it is not used for any further operation
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
| Request succeeds | `OK` |
| Invalid recipient format | `INVALID_ARGUMENT` |
| Template not found | `NOT_FOUND` |
| SMTP delivery failed | `UNAVAILABLE` |
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

### Fire and Forget

Notification Service is a fire-and-forget delivery service. Call `SendEmail` once per user action. If `SendEmail` returns `UNAVAILABLE` (SMTP failure), Notification Service has not stored any retry intent — the caller decides whether to retry.

### Summary Table

| Situation | Should call? |
|---|---|
| Send login OTP to user | Yes — `SendEmail` with `otp-email` template |
| Send order confirmation | Yes — `SendEmail` with `order-confirmation` template |
| Checking if a previous email was delivered | No — Notification Service does not expose delivery status |
| Sending the same email multiple times | No — call once; retry only on transport failure |

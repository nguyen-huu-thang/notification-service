# API Reference

[English](../en/api.md) | **Tiếng Việt**

---

## Tổng quan

Notification Service chỉ có một gRPC API duy nhất. Không có REST API — mọi giao tiếp đều qua gRPC với mTLS bắt buộc.

| Nhóm | Mục đích |
|---|---|
| **NotificationService** | Gửi email thay mặt cho các service khác |

Proto file nằm trong `app/api/grpc/generated/`.

Tất cả caller phải trình certificate mTLS hợp lệ do Trust Service cấp. Kết nối không được xác thực bị từ chối ở tầng TLS.

---

## NotificationService

```protobuf
service NotificationService {
  // Gửi email giao dịch — dùng template hoặc body đã render sẵn
  rpc SendEmail(SendEmailRequest) returns (SendEmailResponse);
}
```

---

## SendEmail

Gửi email giao dịch đến một người nhận. Hỗ trợ hai chế độ nội dung: template có tên (Jinja2 render phía server) hoặc body đã render sẵn.

```protobuf
message SendEmailRequest {
  string to      = 1;  // địa chỉ email người nhận
  string subject = 2;  // tiêu đề email

  oneof content {
    string body          = 3;  // HTML hoặc plain text đã render sẵn
    TemplateContent tmpl = 4;  // render từ template có tên
  }

  string idempotency_key = 5;  // tùy chọn — cùng key + cùng caller trả id cũ, không gửi lại
}

message TemplateContent {
  string template_name            = 1;  // ví dụ: "otp-email", "order-confirmation"
  map<string, string> context     = 2;  // biến template
}

message SendEmailResponse {
  string notification_id = 1;  // KSUID 24 byte mã hóa Base62 — dùng cho logging và traceability
}
```

**Lưu ý khi sử dụng:**

- `to` được chuẩn hóa (lowercase, Unicode normalize) trước khi gửi
- `template_name` phải khớp với file trong `infrastructure/template/templates/`
- `notification_id` trả về dạng Base62 string để logging và truy vết — không dùng cho thao tác nào khác
- `idempotency_key` (tùy chọn): truyền để tránh gửi trùng khi caller retry; cùng key + cùng caller sẽ trả lại `notification_id` cũ thay vì gửi lại
- Với email OTP: caller tự tạo mã OTP, lưu hash, và truyền mã thô vào template variable (ví dụ: `context["otp_code"] = "123456"`)

**Ví dụ — email OTP:**

```
SendEmailRequest {
  to:      "user@example.com",
  subject: "Mã xác nhận của bạn",
  tmpl: {
    template_name: "otp-email",
    context: {
      "otp_code":   "847291",
      "expires_min": "5"
    }
  }
}
```

**Ví dụ — xác nhận đơn hàng:**

```
SendEmailRequest {
  to:      "buyer@example.com",
  subject: "Đơn hàng của bạn đã được xác nhận",
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

| Tình huống | gRPC Status |
|---|---|
| Request thành công (kể cả khi đã nhận và đang chờ retry) | `OK` |
| Định dạng email không hợp lệ (`E087000`) | `INVALID_ARGUMENT` |
| Thiếu nội dung: không có body lẫn template (`E087001`) | `INVALID_ARGUMENT` |
| Template không tìm thấy (`E087002`) | `INVALID_ARGUMENT` |
| Lỗi nội bộ (DB, không mong đợi) | `INTERNAL` |

> Lỗi SMTP **tạm thời** không còn trả về caller: email đã được nhận vào outbox và worker
> tự gửi lại. Caller chỉ nhận lỗi cho các trường hợp validate phía trên.

---

## Quy tắc sử dụng API

### mTLS bắt buộc

Tất cả kết nối phải dùng mTLS. Caller trình certificate service (do Trust Service cấp). Notification Service xác minh:

```
1. TLS layer:   cert chain hợp lệ với Root CA đã pin
2. App layer:   service_id được trích xuất từ cert SAN
3. App layer:   cert.service_id == service_id trong request metadata
```

### Gửi bền vững (outbox)

Notification Service lưu mọi email vào DB rồi gửi (mô hình hybrid outbox). Khi gặp lỗi
tạm thời (SMTP down), email **không bị mất**: được giữ ở trạng thái `FAILED`/`PENDING` và
worker tự gửi lại với exponential backoff, hết số lần thì chuyển `DEAD_LETTER`. Vì vậy
caller **không cần tự retry** khi lỗi tạm thời. Lỗi client (recipient/template sai) vẫn
trả về ngay để caller sửa. Để an toàn khi caller buộc phải retry, truyền `idempotency_key`.

### Tóm tắt

| Tình huống | Nên gọi? |
|---|---|
| Gửi OTP đăng nhập cho user | Có — `SendEmail` với template `otp-email` |
| Gửi xác nhận đơn hàng | Có — `SendEmail` với template `order-confirmation` |
| Tránh gửi trùng khi retry | Có — truyền `idempotency_key`; cùng key + cùng caller trả id cũ |
| Tự retry khi SMTP lỗi tạm thời | Không cần — outbox + worker tự gửi lại |

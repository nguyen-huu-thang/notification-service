# API Reference

[English](../en/api.md) | **Tiếng Việt**

---

## Tổng quan

Notification Service chỉ có một nhóm gRPC API duy nhất. Không có REST API — mọi giao tiếp đều qua gRPC với mTLS bắt buộc.

| Nhóm | Mục đích |
|---|---|
| **NotificationService** | Gửi email, quản lý vòng đời OTP |

Proto file nằm trong `app/api/grpc/generated/`.

Tất cả caller phải trình certificate mTLS hợp lệ do Trust Service cấp. Kết nối không được xác thực bị từ chối ở tầng TLS.

---

## NotificationService

```protobuf
service NotificationService {
  // Gửi email thông thường (không có OTP)
  rpc SendEmail(SendEmailRequest) returns (SendEmailResponse);

  // Tạo OTP, lưu vào DB, và gửi cho người nhận qua email
  rpc SendOtpEmail(SendOtpEmailRequest) returns (SendOtpEmailResponse);

  // Xác minh mã OTP người dùng gửi
  rpc VerifyOtp(VerifyOtpRequest) returns (VerifyOtpResponse);
}
```

---

## SendEmail

Gửi email giao dịch trực tiếp — dùng body đã render sẵn hoặc template có tên.

```protobuf
message SendEmailRequest {
  string to       = 1;  // địa chỉ email người nhận
  string subject  = 2;  // tiêu đề email

  oneof content {
    string body          = 3;  // HTML hoặc plain text đã render
    TemplateContent tmpl = 4;  // render từ template có tên
  }
}

message TemplateContent {
  string template_name = 1;                  // ví dụ: "order-confirmation"
  map<string, string> context = 2;           // biến template
}

message SendEmailResponse {
  bytes notification_id = 1;  // KSUID 24 bytes của bản ghi EmailNotification
}
```

**Lưu ý sử dụng:**
- `to` được chuẩn hóa (chữ thường, Unicode-normalized) trước khi gửi
- `template_name` phải khớp với file trong `infrastructure/template/templates/`
- `notification_id` trả về để ghi log và truy vết — không dùng cho thao tác nào khác

---

## SendOtpEmail

Tạo mã OTP 6 chữ số, lưu hash vào database, và gửi cho người nhận qua email.

```protobuf
message SendOtpEmailRequest {
  string channel    = 1;  // luôn là "EMAIL" với RPC này
  string target     = 2;  // địa chỉ email người nhận
  string otp_type   = 3;  // VERIFY_EMAIL | RESET_PASSWORD | LOGIN_MFA | ...
  bytes  context_id = 4;  // ID liên kết OTP với entity nghiệp vụ (ví dụ: identity_id)
}

message SendOtpEmailResponse {
  bytes  otp_id     = 1;  // KSUID 24 bytes — lưu lại để verify sau
  int64  expires_at = 2;  // Unix timestamp (ms) — khi nào OTP hết hạn
}
```

**Lưu ý sử dụng:**
- `target` được chuẩn hóa trước khi dùng (chữ thường, trim)
- `otp_id` phải được caller lưu lại — cần thiết để verify OTP sau này
- `context_id` được lưu nguyên vẹn và trả về trong response để truy vết; Notification Service không diễn giải ý nghĩa
- Mã OTP thô chỉ đến hộp thư của người dùng — caller không bao giờ thấy

**Giá trị otp_type:**

| Giá trị | Ý nghĩa |
|---|---|
| `VERIFY_EMAIL` | Xác nhận quyền sở hữu địa chỉ email |
| `RESET_PASSWORD` | Uỷ quyền reset mật khẩu |
| `LOGIN_MFA` | Xác thực yếu tố thứ hai khi đăng nhập |
| `CONFIRM_EMAIL_CHANGE` | Xác minh địa chỉ email mới |
| `CONFIRM_PHONE` | Xác minh số điện thoại |

---

## VerifyOtp

Xác minh mã OTP người dùng gửi so với bản ghi đã lưu.

```protobuf
message VerifyOtpRequest {
  bytes  otp_id = 1;  // trả về từ SendOtpEmail
  string code   = 2;  // mã 6 chữ số người dùng gửi
}

message VerifyOtpResponse {
  bool   success        = 1;
  string failure_reason = 2;  // có giá trị khi success = false
}
```

**Lý do thất bại:**

| Lý do | Ý nghĩa |
|---|---|
| `NOT_FOUND` | Không có bản ghi OTP nào với `otp_id` này |
| `EXPIRED` | OTP đã qua `expires_at` |
| `ALREADY_USED` | OTP đã được xác minh thành công trước đó |
| `INVALID_CODE` | Mã gửi lên không khớp |

**Lưu ý sử dụng:**
- Khi thành công, OTP record được đánh dấu là đã dùng — các lần gọi tiếp theo với cùng `otp_id` sẽ trả về `ALREADY_USED`
- Khi thất bại, record **không** bị đánh dấu đã dùng — caller có thể cho phép người dùng thử lại (tuỳ vào rate limiting của caller)

---

## gRPC Status Code

| Tình huống | gRPC Status |
|---|---|
| Request thành công | `OK` |
| Định dạng email không hợp lệ | `INVALID_ARGUMENT` |
| Template không tìm thấy | `NOT_FOUND` |
| SMTP gửi thất bại | `UNAVAILABLE` |
| OTP không tìm thấy | `NOT_FOUND` |
| Lỗi không xác định | `INTERNAL` |

---

## Quy tắc sử dụng API

### mTLS bắt buộc

Tất cả kết nối phải dùng mTLS. Caller trình certificate service (do Trust Service cấp). Notification Service xác minh:

```
1. Tầng TLS:  chuỗi cert xác nhận hợp lệ với Root CA đã pin
2. Tầng app:  service_id được lấy từ cert SAN
3. Tầng app:  cert.service_id == service_id trong request metadata
```

### Không gọi với mỗi request của user

Notification Service là delivery service fire-and-forget. Caller nên:
- Gọi `SendOtpEmail` một lần cho mỗi hành động của user cần OTP (đăng nhập, đăng ký, v.v.)
- Lưu `otp_id` trả về vào session hoặc database của mình — không gọi `SendOtpEmail` lại để "tra cứu" OTP đã có
- Gọi `VerifyOtp` một lần khi user gửi mã

### Chiến lược Retry thuộc về Caller

Nếu `SendEmail` hoặc `SendOtpEmail` trả về `UNAVAILABLE` (SMTP thất bại), Notification Service không lưu intent retry nào. Caller quyết định có retry không. Với luồng OTP, caller có thể gọi lại `SendOtpEmail` để tạo OTP mới — `otp_id` cũ vẫn còn trong database và sẽ tự hết hạn.

### Bảng tóm tắt

| Tình huống | Nên gọi? |
|---|---|
| User yêu cầu OTP đăng nhập | Có — `SendOtpEmail` |
| User gửi mã OTP | Có — `VerifyOtp` |
| Gửi email xác nhận đơn hàng | Có — `SendEmail` với template |
| Kiểm tra OTP trước đó còn hạn không | Không — dùng `expires_at` trả về lúc tạo |
| Gửi cùng một email nhiều lần | Không — gọi một lần; retry chỉ khi lỗi transport |

# Tích Hợp

[English](../en/integration.md) | **Tiếng Việt**

---

## Tổng quan

Notification Service là **downstream service** — nó được gọi bởi các service khác, không bao giờ gọi lại. Nó tích hợp với platform theo hai cách:

| Tích hợp | Chiều | Khi nào |
|---|---|---|
| Thiết lập trust mTLS | Trust Service → Notification Service | Chỉ lúc khởi động |
| Gửi thông báo | Bất kỳ service → Notification Service | Theo hành động của user |

Notification Service không gọi Identity Service, User Service hay bất kỳ service nào khác tại runtime. Nó tin tưởng certificate của caller và thực thi yêu cầu gửi.

---

## Tích hợp với Trust Service

### Bootstrap mTLS (Khởi động)

Notification Service phải thiết lập danh tính mTLS trước khi có thể nhận kết nối gRPC. Điều này xảy ra một lần khi khởi động:

```
Notification Service khởi động
      ↓
1. Gọi Trust Service: GetRootCertificate
      → nhận Root CA certificate (PEM)
      → pin Root CA vào TLS trust store của gRPC server

2. Gọi Trust Service: BootstrapCert (qua admin, một lần khi deploy lần đầu)
      → nhận chứng chỉ X.509 leaf + initial refresh token
      → certificate SAN chứa service_id = "notification-service"

3. Load certificate + private key vào TLS context của gRPC server
      → Notification Service giờ có thể nhận kết nối qua mTLS
      → tất cả kết nối vào đều được xác minh với Root CA đã pin
```

### Rotation Certificate

Notification Service rotate certificate trước khi hết hạn (~100 ngày sau khi cấp):

```
Phát hiện cert đang đến ngưỡng rotation
      ↓
Tạo key pair mới (trong bộ nhớ)
      ↓
Gọi Trust Service: RotateCertificate
  → token_id + refresh_token (dùng một lần)
  → new public key (PEM)
  → qua kết nối mTLS hiện có
      ↓
Trust Service cấp cert mới
      ↓
Load cert + key pair mới vào TLS configuration
      ↓
Lưu refresh token mới cho lần rotation tiếp theo
```

### Resilience

Nếu Trust Service không khả dụng:
- mTLS vẫn hoạt động bằng certificate đã có
- Notification Service nhận và xử lý request bình thường
- Chỉ rotation cert bị chặn — sẽ xử lý khi Trust Service phục hồi

---

## Tích hợp với Identity Service

Identity Service là **caller chính** của Notification Service trong Base Platform. Nó kích hoạt các luồng OTP cho sự kiện xác thực.

### Đăng nhập MFA

```
User đăng nhập với MFA được bật
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
  → tạo OTP
  → lưu OtpRecord (hết hạn sau 5 phút)
  → gửi email
  → trả về otp_id + expires_at
      ↓
Identity Service
  → lưu otp_id vào session
  → trả về challenge response cho client
      ↓
User gửi mã OTP
      ↓
Identity Service
  → gRPC + mTLS → Notification Service
  VerifyOtpRequest { otp_id, code }
      ↓
Notification Service
  → xác minh → đánh dấu đã dùng → trả về thành công
      ↓
Identity Service
  → phát JWT + refresh token
```

### Xác minh Email khi Đăng ký

```
User đăng ký với địa chỉ email
      ↓
Identity Service
  → SendOtpEmail { otp_type: "VERIFY_EMAIL", target: email, context_id: identity_id }
      ↓
Notification Service → gửi email OTP
      ↓
Identity Service lưu otp_id
      ↓
User gửi OTP → Identity Service → VerifyOtp
      ↓
Notification Service xác nhận → Identity Service đánh dấu email đã xác minh
```

### Reset Mật khẩu

```
User yêu cầu reset mật khẩu
      ↓
Identity Service
  → SendOtpEmail { otp_type: "RESET_PASSWORD", target: email, context_id: identity_id }
      ↓
Notification Service → gửi email OTP reset
      ↓
User gửi OTP → Identity Service → VerifyOtp
      ↓
Notification Service xác nhận → Identity Service uỷ quyền đổi mật khẩu
```

---

## Tích hợp với User Service

User Service gọi Notification Service cho các luồng xác nhận thay đổi thông tin đăng nhập.

### Xác nhận Đổi Email

```
User yêu cầu đổi địa chỉ email
      ↓
User Service
  → SendOtpEmail {
      otp_type:   "CONFIRM_EMAIL_CHANGE",
      target:     new_email,
      context_id: user_id
    }
      ↓
Notification Service → gửi OTP đến email mới
      ↓
User gửi mã → User Service → VerifyOtp
      ↓
Notification Service xác nhận → User Service cập nhật địa chỉ email
```

### Xác nhận Số Điện thoại

```
User thêm/đổi số điện thoại
      ↓
User Service
  → SendOtpEmail (hoặc SendOtpSms trong tương lai) {
      otp_type:   "CONFIRM_PHONE",
      target:     phone_number,
      context_id: user_id
    }
      ↓
Notification Service → gửi OTP
      ↓
User gửi mã → User Service → VerifyOtp
      ↓
Notification Service xác nhận → User Service lưu số điện thoại đã xác minh
```

---

## Tích hợp với Application Layer

Các service nghiệp vụ trong application layer (thương mại điện tử, mạng xã hội, SaaS, AI) gọi Notification Service để gửi email giao dịch liên quan đến domain của họ. Họ dùng `SendEmail` với template có tên.

### Xác nhận Đơn hàng (ví dụ)

```
Order Service (application layer)
  → gRPC + mTLS → Notification Service
  SendEmailRequest {
    to:            "buyer@example.com",
    subject:       "Đơn hàng của bạn đã được xác nhận",
    tmpl: {
      template_name: "order-confirmation",
      context: {
        "order_id":    "ORD-20240601-001",
        "total":       "199.000 VND",
        "items":       "...",
        "delivery_at": "05/06/2024"
      }
    }
  }
      ↓
Notification Service
  → render Jinja2 template
  → gửi email
  → trả về notification_id
```

Application service không cần biết SMTP host, template engine hay OTP subsystem. Họ chỉ chỉ định gửi cái gì và gửi cho ai.

---

## Tóm tắt tích hợp

```
Trust Service
      ↓ cung cấp certificate mTLS (chỉ lúc khởi động)

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
      └── Application Service (bất kỳ)
            └── SendEmail (template tuỳ chỉnh theo use case)
```

---

## Những gì Notification Service KHÔNG làm tại Runtime

- Không gọi lại Identity Service hay User Service
- Không lấy preferences hay thông tin liên lạc của user — tất cả đều do caller cung cấp
- Không xác minh danh tính user cuối — xác minh caller được thực hiện qua mTLS ở tầng service
- Không tham gia vào bất kỳ quyết định authentication hay authorization nào — chỉ gửi thông báo

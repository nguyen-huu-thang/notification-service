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

Notification Service phải thiết lập danh tính mTLS trước khi nhận kết nối gRPC. Việc này chỉ xảy ra một lần khi khởi động:

```
Notification Service khởi động
      ↓
1. Gọi Trust Service: GetRootCertificate
      → nhận Root CA certificate (PEM)
      → pin Root CA vào TLS trust store của gRPC server

2. Gọi Trust Service: BootstrapCert (qua admin, một lần khi deploy lần đầu)
      → nhận X.509 leaf certificate + initial refresh token
      → certificate SAN chứa service_id = "notification-service"

3. Nạp certificate + private key vào TLS context của gRPC server
      → Notification Service sẵn sàng nhận kết nối mTLS
      → mọi kết nối đến đều được xác minh với Root CA đã pin
```

### Rotate Certificate

Notification Service rotate certificate trước khi hết hạn (~100 ngày sau khi cấp):

```
Phát hiện cert sắp đến hạn rotate
      ↓
Tạo key pair mới (trong memory)
      ↓
Gọi Trust Service: RotateCertificate
  → token_id + refresh_token (dùng một lần)
  → public key mới (PEM)
  → qua kết nối mTLS hiện có
      ↓
Trust Service cấp cert mới
      ↓
Nạp cert + key pair mới vào TLS config
      ↓
Lưu refresh token mới cho lần rotate tiếp theo
```

### Resilience

Nếu Trust Service không khả dụng:
- mTLS vẫn hoạt động bình thường bằng cert hiện có
- Notification Service vẫn nhận và xử lý request
- Chỉ bị ảnh hưởng: không rotate cert được — xử lý khi Trust Service phục hồi

---

## Tích hợp với Identity Service

Identity Service là **caller chính** của Notification Service cho các sự kiện authentication. Identity Service sở hữu vòng đời OTP và chỉ gọi Notification Service để gửi email.

### Login MFA

```
User đăng nhập với MFA được bật
      ↓
Identity Service
  → tạo mã OTP
  → lưu HMAC(otp_code) vào database của mình
  → gRPC + mTLS → Notification Service
  SendEmailRequest {
    to:      "user@example.com",
    subject: "Mã xác nhận đăng nhập",
    tmpl: {
      template_name: "otp-email",
      context: { "otp_code": "847291", "expires_min": "5" }
    }
  }
      ↓
Notification Service → render template → gửi email → trả về notification_id
      ↓
Identity Service → lưu otp_id vào session → trả về challenge response cho client
      ↓
User gửi mã OTP lên
      ↓
Identity Service
  → xác minh HMAC(mã_gửi_lên) == hash đã lưu
  → đánh dấu OTP đã dùng trong database của mình
  → phát JWT + refresh token
```

### Xác minh Email khi Đăng ký

```
User đăng ký với địa chỉ email
      ↓
Identity Service
  → tạo OTP → lưu hash → SendEmail { template: "otp-email", otp_code, ... }
      ↓
Notification Service → gửi email
      ↓
Identity Service lưu otp_id + chờ
      ↓
User gửi OTP → Identity Service tự xác minh → đánh dấu email đã xác minh
```

### Reset Mật khẩu

```
User yêu cầu reset mật khẩu
      ↓
Identity Service
  → tạo OTP → lưu hash → SendEmail { template: "otp-email", otp_code, ... }
      ↓
Notification Service → gửi email
      ↓
User gửi OTP → Identity Service tự xác minh → cho phép đổi mật khẩu
```

### Cảnh báo đăng nhập mới (không OTP)

```
Phát hiện đăng nhập đáng ngờ
      ↓
Identity Service
  → SendEmail {
      to:      "user@example.com",
      subject: "Phát hiện đăng nhập mới",
      tmpl:    { template_name: "login-alert", context: { "device": "...", "location": "..." } }
    }
      ↓
Notification Service → gửi email cảnh báo
```

---

## Tích hợp với User Service

User Service gọi Notification Service cho các flow xác nhận thay đổi thông tin. User Service cũng sở hữu vòng đời OTP cho các flow này.

### Xác nhận Đổi Email

```
User yêu cầu đổi địa chỉ email
      ↓
User Service
  → tạo OTP → lưu hash
  → SendEmail {
      to:   new_email,
      tmpl: { template_name: "otp-email", context: { "otp_code": "...", "action": "xác nhận email mới" } }
    }
      ↓
Notification Service → gửi OTP đến email mới
      ↓
User gửi mã → User Service tự xác minh → cập nhật địa chỉ email
```

### Xác nhận Số Điện thoại

```
User thêm/đổi số điện thoại
      ↓
User Service
  → tạo OTP → lưu hash
  → (tương lai) SendSms { to: phone_number, template: "otp-sms", context: { "otp_code": "..." } }
      ↓
Notification Service → gửi SMS (khi implement)
      ↓
User gửi mã → User Service tự xác minh → lưu số điện thoại đã xác minh
```

---

## Tích hợp từ Application Layer

Các service nghiệp vụ (thương mại điện tử, mạng xã hội, SaaS, AI) gọi Notification Service để gửi email theo domain của họ.

### Xác nhận đơn hàng (ví dụ)

```
Order Service (application layer)
  → gRPC + mTLS → Notification Service
  SendEmailRequest {
    to:      "buyer@example.com",
    subject: "Đơn hàng của bạn đã được xác nhận",
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
Notification Service → render Jinja2 template → gửi email → trả về notification_id
```

---

## Tóm tắt tích hợp

```
Trust Service
      ↓ cung cấp mTLS certificate (chỉ lúc khởi động)

Notification Service
      │
      ├── Identity Service
      │     └── SendEmail (otp-email, login-alert, password-changed, ...)
      │
      ├── User Service
      │     └── SendEmail (otp-email, password-changed, ...)
      │
      └── Application Services (bất kỳ)
            └── SendEmail (template tùy theo use case)
```

---

## Notification Service KHÔNG làm gì tại Runtime

- Không gọi lại Identity Service hay User Service
- Không lấy thông tin tuỳ chọn hay địa chỉ liên lạc của user — caller cung cấp tất cả
- Không xác minh danh tính user cuối — xác minh caller được thực hiện qua mTLS ở tầng service
- Không tham gia vào bất kỳ quyết định authentication hay authorization nào — chỉ gửi
- Không lưu trữ OTP — caller tự quản lý trạng thái OTP

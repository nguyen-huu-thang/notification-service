# Notification Service

[English](README.md) | **Tiếng Việt**

> Hạ tầng gửi thông báo nhẹ cho Xime Base Platform — gửi email giao dịch, mã OTP, và SMS (tương lai) thay mặt cho các service khác.

---

Notification Service là **tầng giao tiếp ra bên ngoài** của Xime Base Platform. Đây là infrastructure service không chứa logic nghiệp vụ — nó không biết thông báo là xác nhận đơn hàng, reset mật khẩu hay cảnh báo bảo mật. Các service khác gọi đến khi cần gửi thông báo cho người dùng cuối.

```
Application Services (mạng xã hội, thương mại điện tử, SaaS, AI)
              ↓ gRPC + mTLS
         Identity Service ──→ SendOtpEmail (MFA, xác minh email)
         User Service     ──→ SendOtpEmail (xác nhận đổi email/SĐT)
              ↓ gRPC + mTLS
       Notification Service
              ↓
     ┌────────┴────────┐
   Email           Phone/SMS
  (SMTP)        (tương lai — SMS gateway)
     ↓                ↓
  Người dùng     Người dùng
```

---

## Notification Service làm gì

**Gửi Email**
- Gửi email giao dịch (mã OTP, thông báo hệ thống, tin nhắn tuỳ chỉnh)
- Render template email HTML bằng Jinja2
- Chuẩn hóa địa chỉ email trước khi gửi

**Hệ thống OTP**
- Tạo mã OTP 6 chữ số ngẫu nhiên bảo mật
- Hash và lưu OTP vào database (không lưu plaintext)
- Xác minh mã OTP — dùng một lần, có thời hạn
- Hỗ trợ nhiều loại OTP: xác minh email, đăng nhập MFA, reset mật khẩu, và nhiều hơn

## Notification Service KHÔNG làm gì

- Không biết ý nghĩa nghiệp vụ của thông báo
- Không quản lý tuỳ chọn thông báo của user
- Không authenticate user cuối
- Không tự khởi tạo giao tiếp — chỉ gửi khi được yêu cầu
- Không retry khi gửi thất bại (caller quyết định chiến lược retry)

---

## Quyết định thiết kế quan trọng

### Infrastructure Service không có Domain Knowledge

Notification Service là pipeline gửi thông báo, không phải business service. Caller mã hóa toàn bộ context nghiệp vụ trong tên template và dữ liệu truyền vào. Notification Service không biết "xác nhận đơn hàng" hay "reset mật khẩu" — nó chỉ biết "gửi template này đến địa chỉ này".

### OTP Ownership

Notification Service sở hữu toàn bộ vòng đời OTP — tạo mã, lưu trữ, và xác minh. Caller nhận về `otp_id` và sau đó trình `otp_id + code` để xác minh. Thiết kế này đảm bảo caller không bao giờ tiếp xúc với OTP code thô hay hash của nó.

### Tin tưởng Caller qua mTLS

Tất cả caller phải trình certificate mTLS hợp lệ do Trust Service cấp. Notification Service không xác minh danh tính user cuối — nó tin tưởng hoàn toàn vào service gọi đến.

### Immutable Domain Model

Các đối tượng domain (`OtpRecord`, `EmailNotification`) là Python dataclass với `frozen=True`. Thay đổi trạng thái (ví dụ: đánh dấu OTP đã dùng) trả về instance mới thay vì mutate tại chỗ.

---

## Chạy nhanh

```bash
# Cài Xime Framework từ local path
pip install -e "D:\code\xime\xime framework"

# Cài dependencies của service
pip install -e .

# Chạy service
python -m app.main
```

gRPC: `9092`

---

## Kiến trúc

Notification Service theo **Hexagonal Architecture** (Ports and Adapters) với DDD tactical patterns, xây dựng trên Python + Xime Framework:

```
app/
├── api/          ← Input adapter (gRPC handler, mapper)
├── application/  ← Use case, port interface, DTO
├── domain/       ← Pure Python dataclass (frozen=True)
├── infrastructure/ ← SMTP adapter, Jinja2 template, SQLAlchemy persistence
├── config/       ← Cấu hình DI binding
└── common/       ← Constant, exception, utility
```

Domain layer không phụ thuộc vào infrastructure, framework hay database. Mọi dependency đều hướng vào trong.

---

## Tài liệu

| Tài liệu | Mô tả |
|---|---|
| [Tổng quan](docs/vn/overview.md) | Vai trò, khả năng, vị trí trong Base Platform |
| [Kiến trúc](docs/vn/architecture.md) | Cấu trúc tầng, cây thư mục, DDD pattern |
| [Hệ thống OTP](docs/vn/otp-system.md) | Vòng đời OTP, thiết kế bảo mật, các loại OTP |
| [API Reference](docs/vn/api.md) | gRPC proto definition, quy tắc sử dụng |
| [Tích hợp](docs/vn/integration.md) | Identity Service, User Service và các service khác gọi Notification Service như thế nào |

---

## Các Service trong Base Platform

| Service | Vai trò |
|---|---|
| `trust-service` | Trust infrastructure — CA, mTLS, JWT signing key |
| `identity-service` | Authentication infrastructure — JWT, refresh token |
| `user-service` | Human Identity Domain Service |
| `data-service` | Data infrastructure — object storage, permission |
| `notification-service` | **Gửi thông báo — email, OTP, SMS** |
| `payment-service` | Thanh toán |

---

## Trạng thái dự án

Notification Service đang trong **giai đoạn phát triển tích cực**. Domain model và common layer đã hoàn chỉnh. Use case, infrastructure và gRPC API đang trong quá trình triển khai.

---

## Giấy phép

MIT

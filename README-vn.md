# Notification Service

[English](README.md) | **Tiếng Việt**

> Hạ tầng gửi thông báo nhẹ cho Xime Base Platform — gửi email giao dịch và SMS (tương lai) thay mặt cho các service khác.

---

Notification Service là **tầng giao tiếp ra bên ngoài** của Xime Base Platform. Đây là infrastructure service không chứa logic nghiệp vụ — nó không biết thông báo là xác nhận đơn hàng, mã reset mật khẩu hay cảnh báo bảo mật. Các service khác gọi đến khi cần gửi thông báo cho người dùng cuối.

```
Application Services (mạng xã hội, thương mại điện tử, SaaS, AI)
              ↓ gRPC + mTLS
         Identity Service ──→ SendEmail (mã OTP trong template data)
         User Service     ──→ SendEmail (mã OTP trong template data)
         Payment Service  ──→ SendEmail (biên lai giao dịch)
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
- Gửi email giao dịch qua template có tên hoặc body đã render sẵn
- Render template email HTML bằng Jinja2
- Chuẩn hóa địa chỉ email trước khi gửi

## Notification Service KHÔNG làm gì

- Không tạo mã OTP — vòng đời OTP là trách nhiệm của service gọi đến
- Không lưu trữ hay xác minh mã OTP
- Không biết ý nghĩa nghiệp vụ của thông báo
- Không quản lý tuỳ chọn thông báo của user
- Không authenticate user cuối
- Không tự khởi tạo giao tiếp — chỉ gửi khi được yêu cầu
- Không retry khi gửi thất bại (caller quyết định chiến lược retry)

---

## Quyết định thiết kế quan trọng

### Infrastructure Service không có Domain Knowledge

Notification Service là pipeline gửi thông báo, không phải business service. Caller mã hóa toàn bộ context nghiệp vụ trong tên template và dữ liệu truyền vào. Notification Service không biết "xác nhận đơn hàng", "reset mật khẩu" hay "xác minh OTP" — nó chỉ biết "gửi template này đến địa chỉ này".

### Caller sở hữu vòng đời OTP

Tạo mã OTP, lưu trữ và xác minh là **trách nhiệm của service gọi đến**. Khi Identity Service cần gửi mã MFA:
1. Identity Service tự tạo mã OTP
2. Lưu hash vào database của mình
3. Gọi `SendEmail` của Notification Service với mã OTP trong template data
4. Tự xác minh mã khi người dùng gửi lên

Notification Service chỉ render template và gửi email.

### Tin tưởng Caller qua mTLS

Tất cả caller phải trình certificate mTLS hợp lệ do Trust Service cấp. Notification Service không xác minh danh tính user cuối — nó tin tưởng hoàn toàn vào service gọi đến.

### Immutable Domain Model

Các đối tượng domain (`EmailNotification`) là Python dataclass với `frozen=True`. Thay đổi trạng thái trả về instance mới thay vì mutate tại chỗ.

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
├── infrastructure/ ← SMTP adapter, Jinja2 template engine
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
| [OTP Delivery Pattern](docs/vn/otp-system.md) | Cách caller gửi email OTP qua Notification Service |
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
| `notification-service` | **Gửi thông báo — email, SMS** |
| `payment-service` | Thanh toán |

---

## Trạng thái dự án

Notification Service đang trong **giai đoạn phát triển tích cực**. Domain model và common layer đã hoàn chỉnh. Use case, infrastructure và gRPC API đang trong quá trình triển khai.

---

## Giấy phép

MIT

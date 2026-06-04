# Tổng Quan

[English](../en/overview.md) | **Tiếng Việt**

---

## Notification Service là gì?

Notification Service là **hạ tầng giao tiếp ra ngoài** của Xime Base Platform.

Vai trò của nó là điểm duy nhất chịu trách nhiệm gửi thông báo ra thế giới bên ngoài — qua email hiện tại, qua SMS trong tương lai. Khi bất kỳ service nào trong platform cần liên lạc với người dùng cuối, họ ủy thác việc gửi cho Notification Service.

```
Các service trong Base Platform
  identity-service → SendEmail (mã OTP trong template data)
  user-service     → SendEmail (mã OTP trong template data)
  payment-service  → SendEmail (biên lai giao dịch)

Các service trong Application Layer
  order-service      → SendEmail (xác nhận đơn hàng)
  workspace-service  → SendEmail (lời mời workspace)
         ↓  (mọi giao tiếp ra ngoài đều đi qua đây)
   Notification Service
         ↓
   SMTP server → Email
   SMS gateway → Điện thoại (tương lai)
```

---

## Vị trí trong Base Platform

Xime Base Platform được chia thành hai tầng:

### Base Platform (service lõi)

Các service hạ tầng dùng chung — xây dựng một lần, dùng cho mọi ứng dụng:

| Service | Vai trò |
|---|---|
| `trust-service` | Trust infrastructure — CA, mTLS, JWT signing key |
| `identity-service` | Authentication — phát hành JWT, refresh token |
| `user-service` | Human Identity Domain — credential, trạng thái tài khoản |
| `data-service` | Data infrastructure — object storage, permission |
| `notification-service` | **Gửi thông báo — email, SMS** |
| `payment-service` | Thanh toán |

### Application Layer (service nghiệp vụ)

Logic nghiệp vụ cụ thể của từng ứng dụng, dựa trên Base Platform:

- **Mạng xã hội**: post-service, comment-service, media-service
- **Thương mại điện tử**: product-service, order-service
- **SaaS / AI**: workspace-service, dataset-service, ai-agent-service

Notification Service phục vụ tất cả — cả service lõi lẫn service nghiệp vụ — khi họ cần gửi thông báo đến người dùng cuối.

---

## Khả năng: Gửi Email

Notification Service có một khả năng cốt lõi: gửi email thay mặt cho caller.

```
Caller
   → SendEmail(to, subject, template_name, template_data)
        ↓
Notification Service
   → chuẩn hóa địa chỉ email
   → render Jinja2 template với dữ liệu được cung cấp
   → gửi qua SMTP adapter
   → trả về notification_id
```

Với caller đã có body sẵn:

```
Caller
   → SendEmail(to, subject, body)
        ↓
Notification Service
   → chuẩn hóa địa chỉ email
   → gửi qua SMTP adapter
   → trả về notification_id
```

Notification Service không biết email này có ý nghĩa gì. Caller cung cấp tên template, dữ liệu và địa chỉ nhận — Notification Service chỉ lo render và gửi.

---

## Ai gọi Notification Service?

Tất cả caller giao tiếp qua **gRPC + mTLS**. Notification Service không có REST API — chỉ nhận kết nối gRPC.

### Các service trong Base Platform (caller nội bộ)

| Service | Use case |
|---|---|
| **Identity Service** | Gửi email MFA đăng nhập, email xác minh email khi đăng ký, email reset mật khẩu |
| **User Service** | Gửi email xác nhận email mới, email xác nhận SĐT, thông báo đổi mật khẩu |

Với các flow OTP, các service này tự tạo và quản lý mã OTP, sau đó truyền mã vào template data khi gọi `SendEmail`.

### Application Layer (caller nghiệp vụ)

Các service nghiệp vụ gửi email giao dịch liên quan đến domain của họ:

| Use case ví dụ | Loại notification |
|---|---|
| Xác nhận đơn hàng | `SendEmail` (template: `order-confirmation`) |
| Nhắc lịch hẹn | `SendEmail` |
| Thông báo giao dịch | `SendEmail` (template: `transaction-alert`) |
| Lời mời workspace | `SendEmail` (template: `workspace-invite`) |

Các service nghiệp vụ không cần biết về SMTP hay Jinja2 — họ chỉ gọi gRPC và truyền: địa chỉ nhận, tiêu đề, tên template và dữ liệu.

---

## Triết lý thiết kế

| Câu hỏi | Câu trả lời |
|---|---|
| Notification Service là gì? | Hạ tầng gửi thông báo — cổng thông báo duy nhất của platform |
| Nó quản lý gì? | Gửi email và render template |
| Nó có quản lý mã OTP không? | Không — vòng đời OTP là trách nhiệm của caller |
| Nó có biết ý nghĩa của thông báo không? | Không — đó là trách nhiệm của caller |
| Nó có authenticate user cuối không? | Không — tin tưởng caller qua mTLS |
| Nếu SMTP bị down? | Trả lỗi về caller; caller quyết định retry |
| Có trạng thái không? | Không — không cần database |

---

## Notification Service KHÔNG phải là

- Không phải business service — không biết về flow đặt hàng, flow auth, hay hành trình người dùng
- Không phải OTP manager — không tạo, lưu hay xác minh mã OTP
- Không phải message broker — không queue hay retry gửi nội bộ
- Không phải notification preference manager — không quyết định ai muốn nhận gì
- Không phải user-facing service — người dùng cuối không tương tác trực tiếp với nó

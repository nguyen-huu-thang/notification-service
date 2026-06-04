# Tổng Quan

[English](../en/overview.md) | **Tiếng Việt**

---

## Notification Service là gì?

Notification Service là **hạ tầng giao tiếp ra ngoài** của Xime Base Platform.

Vai trò của nó là điểm duy nhất chịu trách nhiệm gửi thông báo ra thế giới bên ngoài — qua email hiện tại, qua SMS trong tương lai. Không có service nào khác tự gửi email hay quản lý mã OTP. Khi bất kỳ service nào trong platform cần liên lạc với người dùng cuối, họ ủy thác cho Notification Service.

```
Các service trong Base Platform
  identity-service → SendOtpEmail (MFA, xác minh email)
  user-service     → SendOtpEmail (xác nhận đổi thông tin)
  payment-service  → SendEmail    (biên lai giao dịch)

Các service trong Application Layer
  order-service      → SendEmail   (xác nhận đơn hàng)
  workspace-service  → SendEmail   (lời mời workspace)
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
| `notification-service` | **Gửi thông báo — email, OTP, SMS** |
| `payment-service` | Thanh toán |

### Application Layer (service nghiệp vụ)

Logic nghiệp vụ cụ thể của từng ứng dụng, dựa trên Base Platform:

- **Mạng xã hội**: post-service, comment-service, media-service
- **Thương mại điện tử**: product-service, order-service
- **SaaS / AI**: workspace-service, dataset-service, ai-agent-service

Notification Service phục vụ tất cả — cả service nền tảng lẫn application layer — bất cứ khi nào họ cần gửi thông báo đến người dùng cuối.

---

## Hai khả năng chính

Notification Service cung cấp hai khả năng độc lập, dùng chung hạ tầng nhưng có trách nhiệm riêng biệt:

### A. Gửi Email

Dùng để gửi bất kỳ email nào ra ngoài — bao gồm email OTP, thông báo hệ thống, và email tuỳ chỉnh từ application layer:

```
Caller
   → SendEmail(to, subject, body, channel)
        ↓
Notification Service
   → normalize địa chỉ nhận
   → validate định dạng email
   → gửi qua SMTP adapter
   → trả về notification_id
```

Với email dùng template, caller truyền tên template và dữ liệu thay vì body đã render:

```
Caller
   → SendEmail(to, template_name, template_context, channel)
        ↓
Notification Service
   → render template (Jinja2)
   → gửi qua SMTP adapter
```

### B. Hệ thống OTP

Dùng trong các luồng xác minh cần chứng minh người dùng kiểm soát một địa chỉ email hay số điện thoại:

```
Caller
   → SendOtpEmail(channel, target, otp_type, context_id)
        ↓
Notification Service
   → tạo mã OTP 6 chữ số
   → hash mã OTP (HMAC-SHA256)
   → lưu OtpRecord vào database (hết hạn sau 5 phút)
   → render template email OTP
   → gửi email
   → trả về otp_id + expires_at
        ↓
Caller lưu otp_id, chờ user gửi mã
        ↓
Caller
   → VerifyOtp(otp_id, code)
        ↓
Notification Service
   → load OtpRecord → kiểm tra hết hạn → verify hash → đánh dấu đã dùng
   → trả về thành công/thất bại
```

Caller không bao giờ thấy mã OTP thô hay hash của nó. Notification Service sở hữu toàn bộ vòng đời OTP.

---

## Ai gọi Notification Service?

Tất cả caller giao tiếp qua **gRPC + mTLS**. Notification Service không có REST API — chỉ nhận kết nối gRPC.

### Service trong Base Platform (caller nội bộ)

| Service | Use case |
|---|---|
| **Identity Service** | OTP đăng nhập MFA, OTP xác minh email khi đăng ký, OTP reset mật khẩu |
| **User Service** | OTP xác nhận đổi email, OTP xác nhận số điện thoại, thông báo đổi mật khẩu |

### Application Layer (caller nghiệp vụ)

Service trong application layer gửi email giao dịch liên quan đến nghiệp vụ riêng của họ:

| Ví dụ use case | Loại notification |
|---|---|
| Xác nhận đơn hàng | `SendEmail` (template: `order-confirmation`) |
| Nhắc lịch hẹn | `SendEmail` hoặc `SendSms` |
| Cảnh báo giao dịch | `SendEmail` (template: `transaction-alert`) |
| Lời mời workspace | `SendEmail` (template: `workspace-invite`) |

Application service không cần biết về SMTP, Jinja2 template hay OTP storage — họ chỉ gọi gRPC và truyền: kênh gửi, địa chỉ nhận, tên template, và dữ liệu. Mọi chi tiết gửi đi là trách nhiệm của Notification Service.

---

## Triết lý thiết kế

| Câu hỏi | Câu trả lời |
|---|---|
| Notification Service là gì? | Hạ tầng gửi thông báo — cổng thông báo duy nhất của platform |
| Nó quản lý gì? | Gửi email + vòng đời OTP (tạo, lưu, xác minh) |
| Nó có biết thông báo có ý nghĩa gì không? | Không — đó là trách nhiệm của caller |
| Nó có authenticate user cuối không? | Không — nó tin tưởng service gọi đến qua mTLS |
| Ai sở hữu mã OTP? | Notification Service — caller chỉ nhận `otp_id` |
| Nếu SMTP bị down thì sao? | Notification Service trả lỗi; caller quyết định có retry không |
| Nó có trạng thái không? | Có — OTP record được lưu trong PostgreSQL |

---

## Notification Service KHÔNG phải là

- Không phải business service — không có kiến thức về luồng đơn hàng, luồng xác thực hay hành trình người dùng
- Không phải message broker — không queue hay retry gửi nội bộ
- Không phải quản lý notification preferences — không quyết định ai muốn nhận gì
- Không phải service đối mặt người dùng — người dùng cuối không tương tác trực tiếp với nó

# OTP Delivery Pattern

[English](../en/otp-system.md) | **Tiếng Việt**

---

## Tổng quan

Notification Service **không** tạo, lưu hay xác minh mã OTP. Toàn bộ vòng đời OTP — tạo mã, lưu trữ và xác minh — hoàn toàn thuộc trách nhiệm của **service gọi đến** (Identity Service, User Service, ...).

Vai trò của Notification Service trong một flow OTP rất đơn giản: nhận lệnh `SendEmail` với mã OTP đã có sẵn trong template data, render template, và gửi email.

```
Identity Service
      ↓ tạo mã OTP
      ↓ lưu HMAC-SHA256(otp_code) vào database của mình
      ↓ SendEmail(to, template="otp-email", data={otp_code, expires_min})
Notification Service
      ↓ render template với otp_code
      ↓ gửi email qua SMTP
      ↓ trả về notification_id
Identity Service
      ↓ chờ user gửi mã lên
User gửi mã → Identity Service
      ↓ xác minh HMAC(mã_gửi_lên) == hash đã lưu
      ↓ đánh dấu OTP đã dùng trong database của mình
      ↓ tiếp tục xử lý (phát JWT, xác nhận thay đổi, ...)
```

---

## Tại sao Caller sở hữu OTP

OTP là khái niệm thuộc về authentication và bảo mật — nó thuộc về auth domain, không phải delivery infrastructure. Đưa vòng đời OTP vào Notification Service sẽ:

- Buộc Notification Service phải lưu dữ liệu auth domain (`otp_type`, `context_id`, `identity_id`)
- Tạo dependency ngược: Identity Service phải gọi lại Notification Service chỉ để kiểm tra 6 chữ số
- Vi phạm ranh giới "không có domain knowledge" — ranh giới này giúp Notification Service có thể tái sử dụng cho mọi ứng dụng

Khi giữ OTP ở service gọi đến, mỗi service tự quản lý chính sách bảo mật của mình: thời hạn hết hạn, giới hạn retry, bảo vệ brute-force, và audit log đều là trách nhiệm của caller.

---

## Hướng dẫn triển khai cho Caller

### 1. Tạo và lưu OTP

```python
import secrets
import hmac
import hashlib

# Tạo mã
otp_code = f"{secrets.randbelow(1_000_000):06d}"  # "847291"

# Hash — không lưu mã thô
secret_key = b"..."  # từ config
otp_hash = hmac.new(secret_key, otp_code.encode(), hashlib.sha256).hexdigest()

# Lưu vào DB của caller
await otp_repository.save(OtpRecord(
    otp_id     = generate_id(),
    target     = normalize_email(user_email),
    otp_hash   = otp_hash,
    otp_type   = OtpType.LOGIN_MFA,
    context_id = identity_id,
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5),
    is_used    = False,
))
```

### 2. Gọi Notification Service để gửi

```python
await notification_stub.SendEmail(SendEmailRequest(
    to      = user_email,
    subject = "Mã xác nhận của bạn",
    tmpl    = TemplateContent(
        template_name = "otp-email",
        context       = {
            "otp_code":    otp_code,       # mã thô — chỉ đến hộp thư của user
            "expires_min": "5",
        },
    ),
))
```

### 3. Xác minh khi user gửi mã lên

```python
record = await otp_repository.find_by_id(otp_id)

if record is None:
    raise OtpNotFoundError()
if datetime.now(timezone.utc) >= record.expires_at:
    raise OtpExpiredError()
if record.is_used:
    raise OtpAlreadyUsedError()

submitted_hash = hmac.new(secret_key, submitted_code.encode(), hashlib.sha256).hexdigest()
if not hmac.compare_digest(submitted_hash, record.otp_hash):
    raise OtpInvalidError()

# Đánh dấu đã dùng
await otp_repository.save(record.mark_used())
```

---

## Template Contract của Notification Service

Notification Service cung cấp template `otp-email` với các biến sau:

| Biến | Bắt buộc | Mô tả |
|---|---|---|
| `otp_code` | Có | Mã OTP 6 chữ số để hiển thị |
| `expires_min` | Không | Thời gian hết hạn tính bằng phút |
| `action` | Không | Mô tả hành động (ví dụ: "đăng nhập", "đặt lại mật khẩu") |

Xem các template khác (thông báo đăng nhập, đổi mật khẩu, ...) trong `infrastructure/template/templates/`.

---

## Phân chia trách nhiệm bảo mật

| Vấn đề | Chủ sở hữu |
|---|---|
| Tạo mã OTP ngẫu nhiên bảo mật | Service gọi đến |
| Lưu hash OTP (không lưu plaintext) | Service gọi đến |
| Kiểm tra hạn sử dụng | Service gọi đến |
| Giới hạn dùng một lần | Service gọi đến |
| Rate limiting (số OTP gửi mỗi địa chỉ) | Service gọi đến |
| Bảo vệ brute-force (số lần nhập sai) | Service gọi đến |
| Render template và gửi email | **Notification Service** |

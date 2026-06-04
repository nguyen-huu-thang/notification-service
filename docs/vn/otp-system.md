# Hệ Thống OTP

[English](../en/otp-system.md) | **Tiếng Việt**

---

## Tổng quan

Hệ thống OTP (One-Time Password) trong Notification Service quản lý toàn bộ vòng đời của mã xác minh được dùng trên toàn platform. Đây là thành phần duy nhất chịu trách nhiệm tạo, lưu trữ và xác minh mã OTP — không có service nào khác tiếp xúc trực tiếp với dữ liệu OTP.

```
Identity Service / User Service
      ↓ SendOtpEmail(channel, target, otp_type, context_id)
Notification Service
      ↓ tạo mã → hash → lưu → gửi email
      ↓ trả về otp_id + expires_at
Caller lưu otp_id
      ↓ user gửi mã về cho caller
Caller
      ↓ VerifyOtp(otp_id, code)
Notification Service
      ↓ tìm record → kiểm tra hết hạn → verify hash → đánh dấu đã dùng
      ↓ trả về thành công/thất bại
Caller tiếp tục (phát JWT, xác nhận thay đổi, v.v.)
```

---

## Các loại OTP

Mỗi OTP được tạo với một `otp_type` cụ thể xác định mục đích sử dụng:

| OTP Type | Dùng bởi | Mục đích |
|---|---|---|
| `VERIFY_EMAIL` | Identity Service, User Service | Xác nhận quyền sở hữu địa chỉ email |
| `RESET_PASSWORD` | Identity Service | Uỷ quyền luồng reset mật khẩu |
| `LOGIN_MFA` | Identity Service | Xác thực yếu tố thứ hai khi đăng nhập |
| `CONFIRM_EMAIL_CHANGE` | User Service | Xác minh địa chỉ email mới khi đổi email |
| `CONFIRM_PHONE` | User Service | Xác minh quyền sở hữu số điện thoại |

`otp_type` được lưu trong `OtpRecord` và trả về trong response để phục vụ observability. Notification Service không xử lý khác nhau theo type — type chỉ mang tính thông tin cho caller.

---

## Domain Model OtpRecord

```python
@dataclass(frozen=True)
class OtpRecord:
    otp_id:     bytes     # KSUID 24 bytes — định danh trả về cho caller
    channel:    OtpChannel  # EMAIL | PHONE
    target:     str       # người nhận đã chuẩn hóa (email hoặc số điện thoại)
    otp_hash:   str       # HMAC-SHA256 hash của mã OTP thô
    otp_type:   OtpType   # mục đích của OTP này
    context_id: bytes     # ID do caller cung cấp, liên kết OTP với entity nghiệp vụ
    expires_at: datetime  # khi nào OTP không còn hợp lệ
    is_used:    bool      # True sau khi xác minh thành công (đảm bảo dùng một lần)
    created_at: datetime
```

`context_id` là định danh mờ do caller cung cấp — ví dụ `identity_id` hoặc `user_id` của entity đang được xác minh. Notification Service lưu nó nhưng không diễn giải ý nghĩa.

---

## Luồng Gửi OTP

```
SendOtpEmailUseCase.execute(command)
      ↓
1. Tạo OTP code
      → secrets.randbelow(1_000_000)
      → format thành chuỗi 6 chữ số (thêm số 0 ở đầu nếu cần)

2. Hash OTP code
      → HMAC-SHA256(key=SECRET_KEY, msg=otp_code)
      → chỉ lưu hash — mã thô không bao giờ được lưu

3. Tạo OtpRecord
      → otp_id     = generate_id()         (KSUID 24 bytes)
      → otp_hash   = tính toán ở trên
      → expires_at = now + 5 phút
      → is_used    = False

4. Lưu OtpRecord vào database
      → SaveOtpPort.save(otp_record)

5. Render template email
      → TemplatePort.render("otp-email", {"otp_code": raw_code})
      → raw_code truyền vào template nhưng không được lưu

6. Gửi email
      → EmailSenderPort.send(target, subject, rendered_body)

7. Trả về SendOtpResult
      → otp_id, expires_at
      (caller lưu otp_id; mã thô chỉ đến hộp thư của người dùng)
```

---

## Luồng Xác Minh OTP

```
VerifyOtpUseCase.execute(command)
      command = { otp_id, code }
      ↓
1. Load OtpRecord
      → LoadOtpPort.find_by_id(otp_id)
      → ném OtpNotFoundError nếu không tìm thấy

2. Kiểm tra hết hạn
      → now > otp_record.expires_at → ném OtpExpiredError

3. Kiểm tra đã dùng
      → otp_record.is_used == True → ném OtpAlreadyUsedError

4. Xác minh mã
      → HMAC-SHA256(SECRET_KEY, submitted_code) == otp_record.otp_hash
      → không khớp → ném OtpVerificationFailedError

5. Đánh dấu đã dùng
      → updated = otp_record.mark_used()      (trả về frozen instance mới)
      → SaveOtpPort.save(updated)             (upsert / update trong DB)

6. Trả về VerifyOtpResult
      → { success: True }
```

---

## Thiết kế Bảo mật

### Không lưu Plaintext

Mã OTP thô **không bao giờ được lưu** — không trong database, không trong log. Chỉ có HMAC-SHA256 hash được lưu.

```
raw_code  → HMAC-SHA256(SECRET_KEY, raw_code) → lưu vào cột otp_hash
```

Mã thô chỉ tồn tại trong bộ nhớ trong suốt quá trình thực thi `SendOtpEmailUseCase` và trong nội dung email gửi đến người dùng.

### Đảm bảo Dùng Một Lần

Sau khi xác minh thành công, `is_used` được đặt thành `True` và lưu xuống DB. Bất kỳ lần xác minh nào tiếp theo với cùng `otp_id` đều trả về `OtpAlreadyUsedError` — kể cả khi gửi đúng mã.

### Giới Hạn Thời Gian

Mã OTP hết hạn sau TTL ngắn (mặc định: 5 phút). OTP đã hết hạn không thể xác minh dù gửi đúng mã. Timestamp `expires_at` được lưu tại thời điểm tạo, dùng UTC.

### So sánh Hằng Thời Gian

So sánh hash dùng so sánh hằng thời gian (`hmac.compare_digest`) để ngăn timing attack:

```python
import hmac
valid = hmac.compare_digest(expected_hash, submitted_hash)
```

### Thiết kế Định Danh

`otp_id` là KSUID 24 bytes — có thể sắp xếp, duy nhất toàn cầu và mờ. Nó không mã hóa thông tin về loại OTP, người nhận hay caller. Caller chỉ nhận `otp_id` — không thể suy ra mã OTP từ nó.

---

## Schema Database

```sql
CREATE TABLE otp_records (
    otp_id      BYTEA        PRIMARY KEY,         -- KSUID 24 bytes
    channel     VARCHAR(10)  NOT NULL,             -- EMAIL | PHONE
    target      VARCHAR(255) NOT NULL,             -- người nhận đã chuẩn hóa
    otp_hash    VARCHAR(255) NOT NULL,             -- HMAC-SHA256 hash (không phải raw)
    otp_type    VARCHAR(50)  NOT NULL,             -- VERIFY_EMAIL | LOGIN_MFA | ...
    context_id  BYTEA,                            -- ID do caller cung cấp
    expires_at  TIMESTAMP    NOT NULL,
    is_used     BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMP    NOT NULL
);

CREATE INDEX idx_otp_target_type ON otp_records (target, otp_type, is_used);
CREATE INDEX idx_otp_expires     ON otp_records (expires_at);
```

Index trên `(target, otp_type, is_used)` hỗ trợ truy vấn rate-limiting trong tương lai (ví dụ: "email này đã nhận bao nhiêu OTP loại RESET_PASSWORD chưa dùng trong 1 giờ qua?").

---

## Dọn dẹp OTP

Bản ghi OTP đã hết hạn tích lũy theo thời gian. Một scheduled job nền (chưa triển khai — xem roadmap) sẽ định kỳ xoá các bản ghi có `expires_at < now - retention_window`. Bản ghi đã hết hạn an toàn để xoá sau một khoảng retention ngắn (ví dụ: 24 giờ) vì chúng không còn có thể sử dụng được.

---

## Những gì Notification Service KHÔNG đảm bảo

- **Rate limiting theo người nhận**: Notification Service không giới hạn số OTP caller gửi đến cùng một địa chỉ. Service gọi đến (Identity Service, User Service) chịu trách nhiệm rate limiting ở tầng của họ.
- **Validation otp_type**: Notification Service chấp nhận bất kỳ chuỗi `otp_type` nào. Caller có trách nhiệm gửi loại hợp lệ.
- **Phân quyền caller theo otp_type**: Bất kỳ caller đã xác thực (cert mTLS hợp lệ) đều có thể yêu cầu bất kỳ loại OTP nào. Phân quyền chi tiết theo loại là vấn đề trong tương lai.

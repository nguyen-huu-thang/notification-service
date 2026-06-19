# Kiến Trúc

[English](../en/architecture.md) | **Tiếng Việt**

---

## Tổng quan các tầng

Notification Service theo **Hexagonal Architecture** (Ports and Adapters) với DDD tactical patterns, xây dựng trên Python + Xime Framework.

```
External Clients (gRPC + mTLS)
        ↓
   Adapter Layer (api/)           ← nhận gRPC request, map sang use case input
        ↓
 Application Layer (application/) ← use case, port interface, DTO
        ↓
   Domain Layer (domain/)         ← pure Python class + value object, không phụ thuộc framework
        ↑
Infrastructure Layer (infrastructure/) ← SMTP, Jinja2, mTLS
```

Domain layer không biết về aiosmtplib, Jinja2 hay gRPC. Infrastructure layer không biết về use case logic. Mọi dependency đều hướng vào trong về phía domain.

---

## Cấu trúc thư mục

```
app/
│
├── api/                                      ← adapter layer
│   └── grpc/
│       ├── external/
│       │   └── NotificationGrpcHandler.py    ← nhận gRPC từ các service khác
│       ├── interceptor/
│       │   └── AppExceptionInterceptor.py    ← bắt AppException, che lỗi theo kênh, abort kèm metadata xime-error
│       ├── mapper/
│       │   └── NotificationGrpcMapper.py     ← gRPC message ↔ Command/Result
│       └── generated/                        ← code được generate từ protobuf
│
├── application/
│   ├── usecase/                              ← orchestrate: validate → domain → infra → return
│   │   └── email/
│   │       └── SendEmailUseCase.py           ← hybrid outbox
│   ├── service/                              ← logic nghiệp vụ tái sử dụng
│   │   ├── retry/RetryPolicy.py              ← backoff + quyết định retry/dead-letter
│   │   └── email/
│   │       ├── EmailDeliveryService.py       ← gửi + áp dụng kết quả (dùng chung usecase/worker)
│   │       ├── RetrySendService.py           ← worker gửi lại notification đến hạn
│   │       └── NotificationCleanupService.py ← dọn dữ liệu cũ theo retention
│   ├── port/
│   │   └── outbound/                         ← Protocol interface (excluded khỏi DI scan)
│   │       └── email/
│   │           ├── EmailSenderPort.py
│   │           ├── TemplatePort.py
│   │           ├── SaveNotificationPort.py
│   │           ├── LoadNotificationPort.py
│   │           └── DeleteNotificationPort.py
│   └── dto/                                  ← Pydantic/dataclass model (excluded khỏi DI scan)
│       └── email/
│           ├── SendEmailCommand.py           ← có idempotency_key
│           └── SendEmailResult.py            ← notification_id: Id
│
├── domain/                                   ← pure Python (excluded khỏi DI scan)
│   ├── sharedkernel/                         ← Id (value object), IdFactory, IdService (KSUID)
│   ├── email/
│   │   ├── model/EmailNotification.py        ← class thường: invariant + behavior + retry state
│   │   └── valueobject/EmailAddress.py       ← normalize + validate
│   └── error/                                ← object thuần error (framework-neutral)
│       ├── Visibility.py                     ← PRIVATE / SYSTEM / PUBLIC
│       ├── Channel.py                        ← GRPC_INTERNAL / REST_EXTERNAL
│       ├── GrpcCode.py                        ← status gRPC trung lập
│       ├── ErrorDef.py                        ← mô tả một mã lỗi
│       ├── error_code.py                      ← catalog mã lỗi (dải 080000-089999)
│       └── redaction.py                       ← che lỗi theo kênh
│
├── infrastructure/
│   ├── smtp/
│   │   └── SmtpEmailAdapter.py               ← implements EmailSenderPort
│   ├── template/
│   │   ├── JinjaTemplateAdapter.py           ← implements TemplatePort
│   │   └── templates/                        ← Jinja2 HTML template (otp-email, login-alert, ...)
│   └── persistence/                          ← entity + mapper + repository
│       ├── entity/EmailNotificationEntity.py
│       ├── mapper/EmailNotificationMapper.py
│       └── repository/email/SqlAlchemyNotificationRepository.py
│
├── scheduler/                                ← job nền (DI scan)
│   ├── EmailRetryJob.py                      ← mỗi 1 phút: gửi lại notification đến hạn
│   └── NotificationCleanupJob.py            ← mỗi 24h: dọn dữ liệu cũ
│
├── config/
│   ├── dependency.py                         ← DI binding: Protocol → Implementation
│   └── scheduler.py                          ← đăng ký IntervalJob
│
├── common/
│   ├── constants/
│   │   ├── NotificationChannel.py            ← EMAIL, PHONE
│   │   └── NotificationStatus.py            ← PENDING, SENT, FAILED, DEAD_LETTER
│   ├── exception/
│   │   └── AppException.py                   ← AppException + PrivateError / SystemError / PublicError
│   └── util/
│       ├── Normalizer.py                     ← chuẩn hóa số điện thoại (SMS sau)
│       └── Pii.py                            ← mask_email cho log an toàn PII
│
└── main.py
```

---

## DDD Tactical Patterns

### Domain Object là Immutable

Domain object trong `domain/` là **class Python thường** — kiểm tra invariant trong
constructor, field private expose qua `@property` chỉ-đọc, không có ORM annotation,
không phụ thuộc framework. ID dùng value object `Id`, không dùng `bytes` thuần.

```python
class EmailNotification:
    def __init__(self, notification_id: Id, recipient: EmailAddress, subject: str,
                 body: str, channel: NotificationChannel, status: NotificationStatus,
                 created_at: datetime, attempts: int = 0, ...) -> None:
        if not subject:
            raise ValueError("subject is required")
        self._notification_id = notification_id
        # ... gán field còn lại

    @property
    def status(self) -> NotificationStatus:
        return self._status

    def mark_sent(self, now: datetime) -> 'EmailNotification':
        return self._copy(status=NotificationStatus.SENT, attempts=self._attempts + 1, sent_at=now)

    def schedule_retry(self, now, next_retry_at, error_code) -> 'EmailNotification': ...
    def dead_letter(self, now, error_code) -> 'EmailNotification': ...
```

Thay đổi trạng thái trả về instance mới qua helper `_copy(...)`. Không mutate.

### Port Interface dùng Protocol

Port interface trong `application/port/outbound/` dùng Python `Protocol` — không phải `ABC`, không phải abstract class.

```python
# application/port/outbound/email/EmailSenderPort.py
from typing import Protocol

class EmailSenderPort(Protocol):
    async def send(self, to: str, subject: str, body: str) -> None: ...
```

Port interface excluded khỏi DI scan — chúng là binding target, không phải implementation.

### Constructor Injection Only

Xime Framework dùng **constructor injection hoàn toàn**. Không có decorator `@inject`, không có service locator.

```python
class SendEmailUseCase:
    def __init__(self,
                 email_sender: EmailSenderPort,
                 template:     TemplatePort) -> None:
        self._email_sender = email_sender
        self._template     = template
```

### Bind DI Tường Minh

Tất cả binding Protocol → Implementation được khai báo tường minh trong `config/dependency.py`. Thiếu binding → startup fail ngay (fail-fast).

```python
dependency.bind({
    EmailSenderPort: SmtpEmailAdapter,
    TemplatePort:    JinjaTemplateAdapter,
})
```

---

## Quy tắc đặt tên

| Loại | Pattern | Ví dụ |
|---|---|---|
| Domain object | `*` (PascalCase) | `EmailNotification` |
| Port interface | `*Port` | `EmailSenderPort`, `TemplatePort` |
| Infrastructure adapter | `*Adapter` | `SmtpEmailAdapter`, `JinjaTemplateAdapter` |
| Use case | `*UseCase` | `SendEmailUseCase` |
| gRPC handler | `*GrpcHandler` | `NotificationGrpcHandler` |
| gRPC mapper | `*GrpcMapper` | `NotificationGrpcMapper` |
| DTO command | `*Command` | `SendEmailCommand` |
| DTO result | `*Result` | `SendEmailResult` |

---

## Package Excluded khỏi DI Scan

DI scanner của Xime Framework bỏ qua các package sau — chúng chứa interface và pure model, không phải implementation:

```
domain/
application/dto/
application/port/
common/constants/
common/exception/
api/grpc/mapper/        ← đăng ký thủ công
```

---

## Luồng Use Case

```
gRPC Request (SendEmail)
      ↓
NotificationGrpcHandler
      → map proto message sang SendEmailCommand (qua NotificationGrpcMapper)
      ↓
SendEmailUseCase.execute(command, caller_service_id)   ← hybrid outbox
      → validate recipient (EmailAddress) + render body (TemplatePort)
      → nếu có idempotency_key đã tồn tại → trả id cũ (không gửi lại)
      → lưu EmailNotification(PENDING) vào DB (transaction)
      → EmailDeliveryService.deliver(): gửi qua SMTP
           • thành công        → mark_sent(SENT)
           • lỗi tạm thời       → schedule_retry(FAILED, next_retry_at)  ← worker gửi lại
           • recipient bị từ chối → dead_letter(DEAD_LETTER)
      → lưu kết quả vào DB → trả SendEmailResult(notification_id)
      ↓
NotificationGrpcHandler
      → map SendEmailResult sang proto response (notification_id dạng Base62 string)
      ↓
gRPC Response
```

Worker nền (`EmailRetryJob`, mỗi 1 phút) quét các notification PENDING/FAILED đến
hạn và gửi lại; `NotificationCleanupJob` (mỗi 24h) dọn dữ liệu cũ theo retention.
Notification Service **có database** (PostgreSQL + Alembic): bảng `email_notifications`
(outbox) và `trust_*` (cert/key mTLS).

---

## Mã lỗi & Exception

Service tuân theo chuẩn mã lỗi/exception chung của platform (tham chiếu hiện thực: data-service và trust-service). Dải mã riêng của Notification Service là **`080000 - 089999`**, chia 3 vùng theo chữ số hàng nghìn của offset:

| Vùng | Dải | Visibility | Ai đọc được |
| ---- | --- | ---------- | ----------- |
| Private | `080000 - 083999` | `PRIVATE` | chỉ nội bộ service, bị che ở mọi kênh ra ngoài |
| System | `084000 - 086999` | `SYSTEM` | service khác đọc qua gRPC mTLS, bị che khi ra browser |
| Public | `087000 - 089999` | `PUBLIC` | an toàn cho client/browser trên mọi kênh |

Catalog hiện có (`app/domain/error/error_code.py`) gồm khối Common dùng chung (`E000000 - E007008`) và khối Notification:

| errorKey | Vùng | gRPC status | Ý nghĩa |
| -------- | ---- | ----------- | ------- |
| `E080000` | Private | INTERNAL | Lỗi nội bộ Notification Service |
| `E080001` | Private | INTERNAL | Lỗi render template email |
| `E084000` | System | UNAVAILABLE | Gửi email thất bại tạm thời, có thể thử lại |
| `E087000` | Public | INVALID_ARGUMENT | Người nhận không hợp lệ |
| `E087001` | Public | INVALID_ARGUMENT | Thiếu nội dung gửi (template_name hoặc body) |

**Cách dùng:** nghiệp vụ ném một trong ba base class `PrivateError` / `SystemError` / `PublicError` (trong `common/exception/AppException.py`) kèm một `error_key` trong catalog. Ví dụ:

```python
# Người nhận sai định dạng — lỗi từ phía client
raise PublicError("E087000")

# SMTP chập chờn — service khác có thể retry
raise SystemError("E084000")
```

**Luồng che lỗi:** handler **không** bắt lỗi thủ công. Mọi exception lọt lên `AppExceptionInterceptor` (`api/grpc/interceptor/`), nó che lỗi theo kênh `GRPC_INTERNAL` (qua `redaction.py`) rồi `abort` với status tương ứng và trailing metadata `xime-error` / `xime-error-code`. Vì gRPC ở đây là liên service qua mTLS nên `SYSTEM` và `PUBLIC` lọt nguyên, chỉ `PRIVATE` bị quy về `E000000`. Service này gRPC-only, không có REST handler.

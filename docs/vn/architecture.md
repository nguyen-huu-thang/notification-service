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
   Domain Layer (domain/)         ← pure Python dataclass, không phụ thuộc framework
        ↑
Infrastructure Layer (infrastructure/) ← SMTP, Jinja2, SQLAlchemy, mTLS
```

Domain layer không biết gì về SQLAlchemy, aiosmtplib, Jinja2 hay gRPC. Infrastructure layer không biết gì về logic use case. Mọi dependency đều hướng vào trong về phía domain.

---

## Cấu trúc thư mục

```
app/
│
├── api/                                      ← adapter layer
│   └── grpc/
│       ├── external/
│       │   └── NotificationGrpcHandler.py    ← nhận gRPC từ service khác
│       ├── mapper/
│       │   └── NotificationGrpcMapper.py     ← gRPC message ↔ Command/Result
│       └── generated/                        ← code sinh ra từ protobuf
│
├── application/
│   ├── usecase/                              ← orchestrate: validate → domain → infra → return
│   │   ├── email/
│   │   │   └── SendEmailUseCase.py
│   │   └── otp/
│   │       ├── SendOtpEmailUseCase.py
│   │       └── VerifyOtpUseCase.py
│   ├── port/
│   │   └── outbound/                         ← Protocol interface (không nằm trong DI scan)
│   │       ├── email/
│   │       │   ├── EmailSenderPort.py
│   │       │   └── TemplatePort.py
│   │       └── otp/
│   │           ├── SaveOtpPort.py
│   │           └── LoadOtpPort.py
│   └── dto/                                  ← Pydantic model (không nằm trong DI scan)
│       ├── email/
│       │   ├── SendEmailCommand.py
│       │   └── SendEmailResult.py
│       └── otp/
│           ├── SendOtpCommand.py
│           ├── SendOtpResult.py
│           ├── VerifyOtpCommand.py
│           └── VerifyOtpResult.py
│
├── domain/                                   ← pure Python (không nằm trong DI scan)
│   ├── email/
│   │   └── EmailNotification.py              ← frozen dataclass
│   └── otp/
│       └── OtpRecord.py                      ← frozen dataclass
│
├── infrastructure/
│   ├── smtp/
│   │   └── SmtpEmailAdapter.py               ← implement EmailSenderPort
│   ├── template/
│   │   ├── JinjaTemplateAdapter.py           ← implement TemplatePort
│   │   └── templates/                        ← Jinja2 HTML template
│   │       ├── otp-email.html
│   │       └── ...
│   └── persistence/
│       ├── entity/
│       │   └── otp/
│       │       └── OtpRecordEntity.py        ← SQLAlchemy ORM entity
│       ├── mapper/
│       │   └── OtpRecordMapper.py            ← mapper Entity ↔ Domain
│       └── repository/
│           └── otp/
│               └── SqlAlchemyOtpRepository.py ← implement SaveOtpPort + LoadOtpPort
│
├── config/
│   └── dependency.py                         ← DI binding: Protocol → Implementation
│
├── common/
│   ├── constants/
│   │   ├── NotificationChannel.py            ← EMAIL, PHONE
│   │   ├── OtpType.py                        ← VERIFY_EMAIL, RESET_PASSWORD, LOGIN_MFA, ...
│   │   └── NotificationStatus.py             ← PENDING, SENT, FAILED
│   ├── exception/
│   │   ├── InvalidRecipientError.py
│   │   ├── OtpNotFoundError.py
│   │   ├── OtpExpiredError.py
│   │   ├── OtpAlreadyUsedError.py
│   │   └── OtpVerificationFailedError.py
│   └── util/
│       ├── IdGenerator.py                    ← KSUID 24 bytes
│       └── Normalizer.py                     ← chuẩn hóa email/phone
│
└── main.py
```

---

## DDD Tactical Patterns

### Domain Object là Immutable

Domain object trong `domain/` là **frozen Python dataclass** — không có ORM annotation, không phụ thuộc framework.

```python
@dataclass(frozen=True)
class OtpRecord:
    otp_id: bytes
    channel: OtpChannel
    target: str
    otp_hash: str
    otp_type: OtpType
    context_id: bytes
    expires_at: datetime
    is_used: bool
    created_at: datetime

    def mark_used(self) -> 'OtpRecord':
        return replace(self, is_used=True)  # trả về instance mới
```

Thay đổi trạng thái dùng `dataclasses.replace()` để trả về instance mới. Không mutate.

### Port Interface dùng Protocol

Port interface trong `application/port/outbound/` dùng Python `Protocol` — không phải `ABC`, không phải abstract class.

```python
# application/port/outbound/email/EmailSenderPort.py
from typing import Protocol

class EmailSenderPort(Protocol):
    async def send(self, to: str, subject: str, body: str) -> None: ...
```

Port interface không nằm trong DI scan — chúng là binding target, không phải implementation.

### Constructor Injection duy nhất

Xime Framework chỉ dùng **constructor injection**. Không có decorator `@inject`, không có service locator.

```python
class SendOtpEmailUseCase:
    def __init__(self,
                 email_sender: EmailSenderPort,
                 template: TemplatePort,
                 save_otp: SaveOtpPort) -> None:
        self._email_sender = email_sender
        self._template     = template
        self._save_otp     = save_otp
```

### DI Binding tường minh

Tất cả binding Protocol → Implementation được khai báo tường minh trong `config/dependency.py`. Thiếu binding → startup fail ngay (fail-fast).

```python
dependency.bind({
    EmailSenderPort: SmtpEmailAdapter,
    TemplatePort:    JinjaTemplateAdapter,
    SaveOtpPort:     SqlAlchemyOtpRepository,
    LoadOtpPort:     SqlAlchemyOtpRepository,
})
```

### Tách Port theo Use Case

Thay vì một `OtpRepository` với nhiều method, port được tách theo use case:

```
SaveOtpPort   ← chỉ dùng bởi SendOtpEmailUseCase
LoadOtpPort   ← chỉ dùng bởi VerifyOtpUseCase
```

Mỗi port phản ánh đúng dependency của một use case — ranh giới sạch hơn, dễ test hơn.

---

## Quy tắc đặt tên

| Loại | Pattern | Ví dụ |
|---|---|---|
| Domain object | `*` (PascalCase) | `OtpRecord`, `EmailNotification` |
| SQLAlchemy entity | `*Entity` | `OtpRecordEntity` |
| Repository implementation | `SqlAlchemy*Repository` | `SqlAlchemyOtpRepository` |
| Port interface | `*Port` | `EmailSenderPort`, `SaveOtpPort` |
| Infrastructure adapter | `*Adapter` | `SmtpEmailAdapter`, `JinjaTemplateAdapter` |
| Use case | `*UseCase` | `SendOtpEmailUseCase`, `VerifyOtpUseCase` |
| gRPC handler | `*GrpcHandler` | `NotificationGrpcHandler` |
| gRPC mapper | `*GrpcMapper` | `NotificationGrpcMapper` |
| DTO command | `*Command` | `SendOtpCommand`, `VerifyOtpCommand` |
| DTO result | `*Result` | `SendOtpResult`, `VerifyOtpResult` |

---

## Package bị loại khỏi DI Scan

DI scanner của Xime Framework bỏ qua các package sau — chúng chứa interface và pure model, không phải implementation:

```
domain/
application/dto/
application/port/
common/constants/
common/exception/
api/grpc/mapper/                        ← đăng ký thủ công
infrastructure/persistence/mapper/      ← khởi tạo trực tiếp
```

---

## Luồng Use Case

```
gRPC Request (ví dụ: SendOtpEmail)
      ↓
NotificationGrpcHandler
      → map proto message sang SendOtpCommand (qua NotificationGrpcMapper)
      ↓
SendOtpEmailUseCase.execute(command)
      → tạo OTP code
      → hash OTP code
      → tạo OtpRecord (frozen dataclass)
      → SaveOtpPort.save(otp_record)     ← lưu vào PostgreSQL
      → TemplatePort.render(...)         ← render Jinja2 template
      → EmailSenderPort.send(...)        ← gửi qua SMTP
      → trả về SendOtpResult
      ↓
NotificationGrpcHandler
      → map SendOtpResult sang proto response
      ↓
gRPC Response
```

---

## Xử lý Transaction

Use case có ghi database bọc thao tác trong transaction tường minh:

```python
async def execute(self, command: SendOtpCommand) -> SendOtpResult:
    async with self.transaction():
        otp_record = OtpRecord(...)
        await self._save_otp.save(otp_record)
        # gửi email xảy ra sau khi commit thành công
    await self._email_sender.send(...)
    return SendOtpResult(...)
```

Email được gửi sau khi transaction commit — nếu SMTP call thất bại, OTP record đã được lưu và caller quyết định có retry hay không.

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
│       ├── mapper/
│       │   └── NotificationGrpcMapper.py     ← gRPC message ↔ Command/Result
│       └── generated/                        ← code được generate từ protobuf
│
├── application/
│   ├── usecase/                              ← orchestrate: validate → domain → infra → return
│   │   └── email/
│   │       └── SendEmailUseCase.py
│   ├── port/
│   │   └── outbound/                         ← Protocol interface (excluded khỏi DI scan)
│   │       └── email/
│   │           ├── EmailSenderPort.py
│   │           └── TemplatePort.py
│   └── dto/                                  ← Pydantic model (excluded khỏi DI scan)
│       └── email/
│           ├── SendEmailCommand.py
│           └── SendEmailResult.py
│
├── domain/                                   ← pure Python (excluded khỏi DI scan)
│   └── email/
│       └── EmailNotification.py              ← frozen dataclass
│
├── infrastructure/
│   ├── smtp/
│   │   └── SmtpEmailAdapter.py               ← implements EmailSenderPort
│   └── template/
│       ├── JinjaTemplateAdapter.py           ← implements TemplatePort
│       └── templates/                        ← Jinja2 HTML template
│           ├── otp-email.html.j2
│           ├── login-alert.html.j2
│           ├── password-changed.html.j2
│           └── ...
│
├── config/
│   └── dependency.py                         ← DI binding: Protocol → Implementation
│
├── common/
│   ├── constants/
│   │   ├── NotificationChannel.py            ← EMAIL, PHONE
│   │   └── NotificationStatus.py            ← PENDING, SENT, FAILED
│   ├── exception/
│   │   └── InvalidRecipientError.py
│   └── util/
│       ├── IdGenerator.py                    ← KSUID 24 bytes
│       └── Normalizer.py                     ← chuẩn hóa email
│
└── main.py
```

---

## DDD Tactical Patterns

### Domain Object là Immutable

Domain object trong `domain/` là **frozen Python dataclass** — không có ORM annotation, không phụ thuộc framework.

```python
@dataclass(frozen=True)
class EmailNotification:
    notification_id: bytes
    recipient:       str
    subject:         str
    body:            str
    channel:         NotificationChannel
    status:          NotificationStatus
    created_at:      datetime
    sent_at:         datetime | None = None

    def mark_sent(self, now: datetime) -> 'EmailNotification':
        return replace(self, status=NotificationStatus.SENT, sent_at=now)
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
SendEmailUseCase.execute(command)
      → chuẩn hóa email người nhận
      → TemplatePort.render(template_name, context)   ← render Jinja2 template
      → EmailSenderPort.send(to, subject, body)       ← gửi qua SMTP
      → trả về SendEmailResult(notification_id)
      ↓
NotificationGrpcHandler
      → map SendEmailResult sang proto response
      ↓
gRPC Response
```

Không có thao tác database — Notification Service là stateless.

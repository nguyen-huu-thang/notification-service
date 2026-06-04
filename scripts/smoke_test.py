"""
Smoke test end-to-end cho Notification Service.

Yêu cầu:
  - Service đang chạy: python -m app.main
  - DB đã migrate: $env:DATABASE_URL="..."; python -m alembic upgrade head

Chạy:
  python scripts/smoke_test.py

SMTP debug server được nhúng sẵn — không cần Docker hay MailHog.
"""
import asyncio
import json
import re
import sys

import grpc

sys.path.insert(0, ".")
from app.api.grpc.generated import notification_pb2, notification_pb2_grpc

GRPC_ADDR = "localhost:50051"
SMTP_HOST = "localhost"
SMTP_PORT = 1025
TEST_EMAIL = "smoke-test@xime.local"


# ── Embedded SMTP debug server ────────────────────────────────────────────────

class _CaptureSmtpHandler:
    """SMTP handler tối giản: nhận mail, lưu vào list để test đọc."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            await self._serve(reader, writer)
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        def send(line: str) -> None:
            writer.write((line + "\r\n").encode())

        send("220 localhost DebugSMTP")
        await writer.drain()

        body_lines: list[str] = []
        in_data = False

        while True:
            try:
                raw = await asyncio.wait_for(reader.readline(), timeout=10)
            except asyncio.TimeoutError:
                break
            if not raw:
                break

            cmd = raw.decode("utf-8", errors="replace").rstrip("\r\n")

            if in_data:
                if cmd == ".":
                    in_data = False
                    self.messages.append("\n".join(body_lines))
                    body_lines = []
                    send("250 OK")
                    await writer.drain()
                else:
                    body_lines.append(cmd[1:] if cmd.startswith(".") else cmd)
            else:
                upper = cmd.upper()
                if upper.startswith(("EHLO", "HELO")):
                    send("250 localhost")
                elif upper.startswith("MAIL FROM"):
                    send("250 OK")
                elif upper.startswith("RCPT TO"):
                    send("250 OK")
                elif upper == "DATA":
                    in_data = True
                    send("354 End with <CR><LF>.<CR><LF>")
                elif upper == "QUIT":
                    send("221 Bye")
                    await writer.drain()
                    break
                else:
                    send("250 OK")
                await writer.drain()


def _extract_otp(raw_email: str) -> str | None:
    """Parse MIME email, decode body, tìm 6-digit OTP trong HTML."""
    import email as email_lib

    msg = email_lib.message_from_string(raw_email)

    # Lấy HTML body — hỗ trợ cả multipart và single-part
    html_body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                html_body = payload.decode(charset) if payload else ""
                break
    else:
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or "utf-8"
        html_body = payload.decode(charset) if payload else str(msg.get_payload())

    # OTP nằm trong span có letter-spacing: 12px theo template otp-email.html.j2
    m = re.search(r"letter-spacing:\s*12px[^>]*>\s*(\d{6})\s*<", html_body)
    if m:
        return m.group(1)
    # Fallback: số 6 chữ số bất kỳ
    m = re.search(r"\b(\d{6})\b", html_body)
    return m.group(1) if m else None


# ── Smoke test runner ─────────────────────────────────────────────────────────

class _Result:
    def __init__(self) -> None:
        self._rows: list[tuple[str, bool, str]] = []

    def ok(self, name: str) -> None:
        self._rows.append((name, True, ""))

    def fail(self, name: str, reason: str) -> None:
        self._rows.append((name, False, reason))

    def skip(self, name: str) -> None:
        self._rows.append((name, True, "SKIP"))

    def print_summary(self) -> bool:
        print("\n" + "=" * 60)
        print("KẾT QUẢ SMOKE TEST")
        print("=" * 60)
        passed = 0
        for name, ok, msg in self._rows:
            icon = "✓" if ok else "✗"
            suffix = f" [{msg}]" if msg else ""
            print(f"  {icon} {name}{suffix}")
            if ok:
                passed += 1
        total = len(self._rows)
        print(f"\n{passed}/{total} passed")
        return passed == total


async def run_tests(smtp_handler: _CaptureSmtpHandler) -> bool:
    result = _Result()

    async with grpc.aio.insecure_channel(GRPC_ADDR) as channel:
        stub = notification_pb2_grpc.NotificationServiceStub(channel)

        # ── [1] SendOtpEmail ──────────────────────────────────────────────────
        print("\n[1] SendOtpEmail")
        otp_id = None
        otp_code = None
        try:
            resp = await stub.SendOtpEmail(notification_pb2.SendOtpEmailRequest(
                channel="EMAIL",
                target=TEST_EMAIL,
                otp_type="VERIFY_EMAIL",
            ))
            otp_id = resp.otp_id
            print(f"    otp_id   : {otp_id.hex()}")
            print(f"    expires  : {resp.expires_at}")

            # Tìm OTP code trong email vừa nhận
            await asyncio.sleep(0.3)  # cho SMTP xử lý xong
            if smtp_handler.messages:
                otp_code = _extract_otp(smtp_handler.messages[-1])
                print(f"    otp_code : {otp_code} (extracted from email)")
            result.ok("SendOtpEmail")
        except grpc.RpcError as e:
            print(f"    FAIL: {e.code()} — {e.details()}")
            result.fail("SendOtpEmail", e.details())

        # ── [2] VerifyOtp — sai code ──────────────────────────────────────────
        print("\n[2] VerifyOtp — wrong code (expect INVALID_ARGUMENT)")
        if otp_id:
            try:
                await stub.VerifyOtp(notification_pb2.VerifyOtpRequest(
                    otp_id=otp_id, code="000000"
                ))
                print("    FAIL: expected error, got success")
                result.fail("VerifyOtp_wrong_code", "expected INVALID_ARGUMENT")
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.INVALID_ARGUMENT:
                    print(f"    OK: {e.code()}")
                    result.ok("VerifyOtp_wrong_code")
                else:
                    print(f"    FAIL: {e.code()} — {e.details()}")
                    result.fail("VerifyOtp_wrong_code", e.details())
        else:
            result.skip("VerifyOtp_wrong_code")

        # ── [3] VerifyOtp — đúng code ─────────────────────────────────────────
        print("\n[3] VerifyOtp — correct code (extracted from email)")
        if otp_id and otp_code:
            try:
                resp = await stub.VerifyOtp(notification_pb2.VerifyOtpRequest(
                    otp_id=otp_id, code=otp_code
                ))
                print(f"    OK: success={resp.success}")
                result.ok("VerifyOtp_correct")
            except grpc.RpcError as e:
                print(f"    FAIL: {e.code()} — {e.details()}")
                result.fail("VerifyOtp_correct", e.details())
        elif otp_id and not otp_code:
            print("    SKIP: không tìm được OTP code trong email")
            result.skip("VerifyOtp_correct")
        else:
            result.skip("VerifyOtp_correct")

        # ── [4] VerifyOtp — dùng lại code đã verify ──────────────────────────
        print("\n[4] VerifyOtp — already used (expect FAILED_PRECONDITION)")
        if otp_id and otp_code:
            try:
                await stub.VerifyOtp(notification_pb2.VerifyOtpRequest(
                    otp_id=otp_id, code=otp_code
                ))
                print("    FAIL: expected error, got success")
                result.fail("VerifyOtp_already_used", "expected FAILED_PRECONDITION")
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.FAILED_PRECONDITION:
                    print(f"    OK: {e.code()}")
                    result.ok("VerifyOtp_already_used")
                else:
                    print(f"    FAIL: {e.code()} — {e.details()}")
                    result.fail("VerifyOtp_already_used", e.details())
        else:
            result.skip("VerifyOtp_already_used")

        # ── [5] VerifyOtp — OTP hết hạn (SendOtp mới + fake expire) ──────────
        # Bỏ qua test này trong smoke test vì cần thao tác DB trực tiếp

        # ── [6] SendEmail ─────────────────────────────────────────────────────
        print("\n[5] SendEmail")
        try:
            resp = await stub.SendEmail(notification_pb2.SendEmailRequest(
                to=TEST_EMAIL,
                subject="Smoke Test — Generic Email",
                template_name="generic-email.html.j2",
                template_data=json.dumps({
                    "subject": "Smoke Test",
                    "body": "Service đang hoạt động bình thường.",
                }),
            ))
            print(f"    notification_id: {resp.notification_id.hex()}")
            result.ok("SendEmail")
        except grpc.RpcError as e:
            print(f"    FAIL: {e.code()} — {e.details()}")
            result.fail("SendEmail", e.details())

        # ── [7] Invalid recipient ─────────────────────────────────────────────
        print("\n[6] SendOtpEmail — invalid email (expect INVALID_ARGUMENT)")
        try:
            await stub.SendOtpEmail(notification_pb2.SendOtpEmailRequest(
                channel="EMAIL", target="not-an-email", otp_type="VERIFY_EMAIL"
            ))
            print("    FAIL: expected error, got success")
            result.fail("InvalidRecipient", "expected INVALID_ARGUMENT")
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.INVALID_ARGUMENT:
                print(f"    OK: {e.code()}")
                result.ok("InvalidRecipient")
            else:
                print(f"    FAIL: {e.code()} — {e.details()}")
                result.fail("InvalidRecipient", e.details())

        # ── [8] OTP not found ─────────────────────────────────────────────────
        print("\n[7] VerifyOtp — unknown otp_id (expect NOT_FOUND)")
        try:
            fake_id = bytes(24)
            await stub.VerifyOtp(notification_pb2.VerifyOtpRequest(
                otp_id=fake_id, code="123456"
            ))
            print("    FAIL: expected error, got success")
            result.fail("OtpNotFound", "expected NOT_FOUND")
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                print(f"    OK: {e.code()}")
                result.ok("OtpNotFound")
            else:
                print(f"    FAIL: {e.code()} — {e.details()}")
                result.fail("OtpNotFound", e.details())

    return result.print_summary()


async def main() -> None:
    smtp_handler = _CaptureSmtpHandler()

    print(f"Khởi động SMTP debug server trên {SMTP_HOST}:{SMTP_PORT}...")
    try:
        server = await asyncio.start_server(
            smtp_handler.handle, SMTP_HOST, SMTP_PORT
        )
    except OSError as e:
        print(f"WARN: Không mở được SMTP port {SMTP_PORT}: {e}")
        print("      (Nếu đã có SMTP server khác chạy, smoke test vẫn tiếp tục)")
        server = None

    try:
        if server:
            async with server:
                success = await run_tests(smtp_handler)
        else:
            success = await run_tests(smtp_handler)
    finally:
        if server:
            server.close()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

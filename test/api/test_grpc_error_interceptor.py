"""
Integration-style test — AppExceptionInterceptor trên một gRPC server in-process,
mắc nối đúng thứ tự framework dùng: ErrorMappingInterceptor built-in (outermost)
đứng trước, của ta (innermost) đứng sau.

Chứng minh hợp đồng end-to-end:
  - PublicError  -> status thật + metadata xime-error / xime-error-code
  - SystemError  -> lọt nguyên (liên service qua gRPC) + metadata
  - PrivateError -> che về INTERNAL / E000000 (không lộ key nội bộ)
  - Exception thô -> INTERNAL / E000000
"""
import grpc
import grpc.aio
import pytest

from xime.adapters.grpc.interceptors._error import ErrorMappingInterceptor

from app.api.grpc.interceptor.AppExceptionInterceptor import AppExceptionInterceptor
from app.common.exception.AppException import PrivateError, PublicError, SystemError

pytestmark = pytest.mark.asyncio

_METHOD = "/probe.Probe/Call"


def _generic_handler(raiser):
    async def handler(request, context):
        raiser()
        return b""

    handlers = {
        "Call": grpc.unary_unary_rpc_method_handler(
            handler,
            request_deserializer=lambda b: b,
            response_serializer=lambda b: b,
        )
    }
    return grpc.method_handlers_generic_handler("probe.Probe", handlers)


async def _call(raiser):
    # Mirror framework ordering: built-ins (outermost) then ours (innermost).
    server = grpc.aio.server(interceptors=[ErrorMappingInterceptor({}), AppExceptionInterceptor()])
    server.add_generic_rpc_handlers((_generic_handler(raiser),))
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as ch:
            call = ch.unary_unary(_METHOD, request_serializer=lambda b: b, response_deserializer=lambda b: b)
            with pytest.raises(grpc.aio.AioRpcError) as ei:
                await call(b"x")
            err = ei.value
            return err.code(), dict(err.trailing_metadata() or ())
    finally:
        await server.stop(None)


async def test_public_error_keeps_status_and_metadata():
    def raiser():
        raise PublicError("E087000")

    code, md = await _call(raiser)
    assert code is grpc.StatusCode.INVALID_ARGUMENT
    assert md.get("xime-error") == "E087000"
    assert md.get("xime-error-code") == "87000"


async def test_system_error_passes_on_grpc():
    def raiser():
        raise SystemError("E084000")

    code, md = await _call(raiser)
    assert code is grpc.StatusCode.UNAVAILABLE
    assert md.get("xime-error") == "E084000"
    assert md.get("xime-error-code") == "84000"


async def test_private_error_redacted():
    def raiser():
        raise PrivateError("E080000")

    code, md = await _call(raiser)
    assert code is grpc.StatusCode.INTERNAL
    assert md.get("xime-error") == "E000000"


async def test_plain_exception_redacted():
    def raiser():
        raise RuntimeError("boom")

    code, md = await _call(raiser)
    assert code is grpc.StatusCode.INTERNAL
    assert md.get("xime-error") == "E000000"

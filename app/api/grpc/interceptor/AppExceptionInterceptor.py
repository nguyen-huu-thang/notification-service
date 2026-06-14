# gRPC server interceptor applying the platform error standard.
# Interceptor gRPC áp chuẩn mã lỗi platform.
#
# Registered (innermost) via configure_grpc_interceptors in app/config/grpc.py.
# Catches AppException (and any stray Exception), redacts per the GRPC_INTERNAL
# channel, and aborts with `xime-error` / `xime-error-code` trailing metadata.
# All gRPC here is service-to-service over mTLS, so SYSTEM + PUBLIC pass through
# and only PRIVATE is collapsed to E000000.
#
# Đăng ký (innermost) qua configure_grpc_interceptors trong app/config/grpc.py.
# Bắt AppException (và mọi Exception lọt), che theo kênh GRPC_INTERNAL, rồi abort
# kèm trailing metadata `xime-error` / `xime-error-code`. Mọi gRPC ở đây là
# liên service qua mTLS nên SYSTEM + PUBLIC lọt, chỉ PRIVATE bị quy về E000000.
from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any

import grpc
import grpc.aio

from app.common.exception.AppException import AppException
from app.domain.error.Channel import Channel
from app.domain.error.ErrorDef import ErrorDef
from app.domain.error.Visibility import Visibility
from app.domain.error.error_code import UNKNOWN, get_error
from app.domain.error.redaction import redact_for_channel

_log = logging.getLogger(__name__)


def _grpc_status(ed: ErrorDef) -> grpc.StatusCode:
    # Map the domain-neutral GrpcCode to the grpc library status by matching name.
    # Map GrpcCode trung lập của domain sang status thư viện grpc theo tên.
    return grpc.StatusCode[ed.grpc_code.name]


def _resolve(exc: Exception) -> ErrorDef:
    if isinstance(exc, AppException):
        raw = get_error(exc.error_key)
        if raw.visibility is not Visibility.PUBLIC:
            _log.error("Non-public error on gRPC: %s", raw.error_key, exc_info=exc)
        return redact_for_channel(raw, Channel.GRPC_INTERNAL)
    _log.error("Unhandled error on gRPC", exc_info=exc)
    return UNKNOWN


def _metadata(ed: ErrorDef) -> tuple[tuple[str, str], ...]:
    return (("xime-error", ed.error_key), ("xime-error-code", str(ed.code)))


class AppExceptionInterceptor(grpc.aio.ServerInterceptor):
    async def intercept_service(
        self,
        continuation: Callable[..., Coroutine[Any, Any, grpc.RpcMethodHandler | None]],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler | None:
        handler = await continuation(handler_call_details)
        if handler is None:
            return None
        if handler.unary_unary is not None:
            return handler._replace(unary_unary=self._wrap_unary(handler.unary_unary))
        if handler.unary_stream is not None:
            return handler._replace(unary_stream=self._wrap_streaming(handler.unary_stream))
        if handler.stream_unary is not None:
            return handler._replace(stream_unary=self._wrap_unary(handler.stream_unary))
        if handler.stream_stream is not None:
            return handler._replace(stream_stream=self._wrap_streaming(handler.stream_stream))
        return handler

    @staticmethod
    def _wrap_unary(fn: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapped(request: Any, context: grpc.aio.ServicerContext) -> Any:
            try:
                return await fn(request, context)
            except grpc.RpcError:
                raise
            except Exception as exc:
                ed = _resolve(exc)
                await context.abort(_grpc_status(ed), ed.message, trailing_metadata=_metadata(ed))

        return wrapped

    @staticmethod
    def _wrap_streaming(fn: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapped(request: Any, context: grpc.aio.ServicerContext) -> AsyncIterator[Any]:
            try:
                async for item in fn(request, context):
                    yield item
            except grpc.RpcError:
                raise
            except Exception as exc:
                ed = _resolve(exc)
                await context.abort(_grpc_status(ed), ed.message, trailing_metadata=_metadata(ed))

        return wrapped

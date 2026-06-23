from __future__ import annotations

import logging

from xime.core.context import request_context
from xime.core.security.peer import current_caller


class LoggingContextFilter(logging.Filter):
    """Inject per-request context onto every LogRecord.

    Pulls request_id (set by the framework's RequestContextInterceptor) and the
    verified peer identity (caller_service_id) so the JSON formatter can emit
    them on every line. Runs for all records, including those from background
    jobs where there is no request - then the fields are simply None.
    Gắn request_id (do RequestContextInterceptor của framework đặt) và peer
    identity đã verify (caller_service_id) vào mọi LogRecord để formatter xuất ra.
    Với log từ job nền (không có request) thì hai trường này là None.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_context.get("request_id")
        record.caller_service_id = current_caller()
        return True

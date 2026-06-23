from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

# Standard LogRecord attributes — everything else passed via logging `extra=`
# is treated as a structured field and merged into the JSON output.
# Thuộc tính LogRecord chuẩn — mọi field khác truyền qua `extra=` được coi là
# field có cấu trúc và gộp vào JSON.
_RESERVED = frozenset(logging.makeLogRecord({}).__dict__.keys()) | {
    "message",
    "asctime",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """One JSON object per log line: machine-parseable, context-enriched.

    Fixed keys (timestamp/level/logger/message) always appear. request_id and
    caller_service_id come from LoggingContextFilter. Any `extra=` keys an app
    log passes (event, notification_id, status, error_code...) are merged in,
    making each line a structured event.
    Mỗi dòng log là một JSON: máy đọc được, kèm context. Các key cố định luôn có;
    request_id/caller_service_id từ LoggingContextFilter; mọi key `extra=` được
    gộp vào để mỗi dòng là một event có cấu trúc.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Context fields from LoggingContextFilter (may be None outside a request).
        # Trường context từ LoggingContextFilter (có thể None ngoài request).
        request_id = getattr(record, "request_id", None)
        if request_id is not None:
            payload["request_id"] = request_id
        caller = getattr(record, "caller_service_id", None)
        if caller is not None:
            payload["caller_service_id"] = caller

        # Structured extras passed via logging `extra={...}`. request_id and
        # caller_service_id are handled above (and omitted when None), so skip
        # them here to avoid re-adding them as null.
        # Field có cấu trúc truyền qua `extra={...}`. request_id và
        # caller_service_id đã xử lý ở trên (bỏ qua khi None) nên loại ở đây để
        # không bị thêm lại dưới dạng null.
        for key, value in record.__dict__.items():
            if (
                key not in _RESERVED
                and key not in payload
                and key not in ("request_id", "caller_service_id")
            ):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)

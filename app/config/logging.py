from __future__ import annotations

import logging.config
import os

# Structured JSON logging for the whole service. Called once from main.py BEFORE
# the Xime bootstrap runs: installing a root handler here makes the framework's
# own logging setup defer (it only configures root when no handler exists), so
# our JSON format wins without fighting the framework.
# Log JSON có cấu trúc cho toàn service. Gọi một lần trong main.py TRƯỚC khi
# Xime bootstrap chạy: cài root handler ở đây khiến phần logging của framework tự
# nhường (nó chỉ cấu hình root khi chưa có handler), nên định dạng JSON của ta
# thắng mà không phải tranh với framework.

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def configure_logging() -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "context": {
                    "()": "app.common.observability.LoggingContextFilter.LoggingContextFilter",
                },
            },
            "formatters": {
                "json": {
                    "()": "app.common.observability.JsonFormatter.JsonFormatter",
                },
            },
            "handlers": {
                "stdout": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "json",
                    "filters": ["context"],
                },
            },
            "root": {
                "level": _LOG_LEVEL,
                "handlers": ["stdout"],
            },
        }
    )

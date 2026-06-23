from __future__ import annotations

import logging

from prometheus_client import start_http_server
from xime.core.config.runtime import RuntimeConfig

_log = logging.getLogger(__name__)

_DEFAULT_PORT = 9100


class MetricsServer:
    """Exposes Prometheus metrics on a dedicated HTTP port at startup.

    The service is gRPC-only, so it has no HTTP server of its own. This starts a
    tiny stdlib HTTP endpoint (/metrics) in a background thread for Prometheus to
    scrape. Controlled by `metrics.enabled` / `metrics.port` in application.yml.
    Service chỉ có gRPC, không có HTTP server riêng. Component này mở một endpoint
    HTTP nhỏ (/metrics) bằng thread nền để Prometheus scrape. Bật/tắt + cổng cấu
    hình qua metrics.enabled / metrics.port trong application.yml.

    Fail-soft: a metrics-port bind error is logged but never blocks startup -
    observability must not take the service down.
    Fail-soft: lỗi bind cổng metrics chỉ log, không chặn startup - observability
    không được làm sập service.
    """

    def __init__(self, config: RuntimeConfig) -> None:
        self._enabled: bool = config.get("metrics.enabled", True)
        self._port: int = config.get("metrics.port", _DEFAULT_PORT)

    async def post_construct(self) -> None:
        if not self._enabled:
            _log.info("Metrics server disabled (metrics.enabled=false).")
            return
        try:
            start_http_server(self._port)
            _log.info("Metrics server listening on :%d/metrics", self._port)
        except OSError as exc:
            # Port in use / not bindable — degrade without crashing the service.
            # Cổng bị chiếm / không bind được — chạy tiếp, không làm sập service.
            _log.error("Failed to start metrics server on :%d: %s", self._port, exc)

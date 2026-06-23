from __future__ import annotations

from prometheus_client import Counter, Histogram

# Service-level email delivery metrics, exposed via MetricsServer on a dedicated
# HTTP port for Prometheus to scrape. Counters/histogram live at module scope so
# any component can import and increment them without DI wiring.
# Metrics gửi email cấp service, expose qua MetricsServer trên một cổng HTTP
# riêng để Prometheus scrape. Counter/histogram đặt ở scope module để mọi
# component import và tăng được mà không cần DI.

# Label cardinality is kept low on purpose: `reason` is a coarse bucket
# (transient / rejected), NOT the raw error key, to avoid metric explosion.
# Cố ý giữ cardinality thấp: `reason` là nhóm thô (transient/rejected), KHÔNG
# phải error key thô, để tránh nổ metric.

EMAILS_SENT = Counter(
    "notification_emails_sent_total",
    "Total emails delivered successfully.",
)

EMAILS_FAILED = Counter(
    "notification_emails_failed_total",
    "Total email delivery failures.",
    labelnames=("reason",),
)

EMAILS_DEAD_LETTER = Counter(
    "notification_emails_dead_letter_total",
    "Total emails moved to dead-letter (permanently undeliverable).",
)

RETRY_ATTEMPTS = Counter(
    "notification_retry_attempts_total",
    "Total retry deliveries processed by the background worker.",
)

SEND_DURATION = Histogram(
    "notification_send_duration_seconds",
    "Email send attempt duration in seconds.",
)

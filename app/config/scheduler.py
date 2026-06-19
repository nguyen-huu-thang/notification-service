from xime.starters.scheduler import SchedulerConfig, IntervalJob, configure_scheduler

from app.integration.trust.scheduler.CertRotationJob import CertRotationJob
from app.integration.trust.scheduler.KeyRefreshJob import KeyRefreshJob
from app.integration.trust.scheduler.KeyCleanupJob import KeyCleanupJob
from app.scheduler.EmailRetryJob import EmailRetryJob
from app.scheduler.NotificationCleanupJob import NotificationCleanupJob

# ── Scheduler configuration for Notification Service ─────────────────────────
#
# CertRotation        — every 1 hour  : checks if cert is due for rotation
# KeyRefresh          — every 6 hours : fetches fresh verification keys from Trust
# KeyCleanup          — every 24 hours: removes expired keys from DB and cache
# EmailRetry          — every 1 minute: re-sends due PENDING/FAILED notifications
# NotificationCleanup — every 24 hours: removes old SENT/DEAD_LETTER rows
#
# All times are in UTC. Jobs are no-op when nothing needs to be done.
# ─────────────────────────────────────────────────────────────────────────────

configure_scheduler(SchedulerConfig(
    jobs=[
        IntervalJob(job_class=CertRotationJob, hours=1),
        IntervalJob(job_class=KeyRefreshJob, hours=6),
        IntervalJob(job_class=KeyCleanupJob, hours=24),
        IntervalJob(job_class=EmailRetryJob, minutes=1),
        IntervalJob(job_class=NotificationCleanupJob, hours=24),
    ],
    timezone="UTC",
))

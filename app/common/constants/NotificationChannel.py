from enum import Enum


class NotificationChannel(str, Enum):
    EMAIL = "EMAIL"
    PHONE = "PHONE"

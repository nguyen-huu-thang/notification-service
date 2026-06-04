"""
Chạy Alembic migration.
Usage: python scripts/migrate.py
"""
import asyncio
import os
import sys

# Đọc DATABASE_URL từ env hoặc dùng default
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://thang:123456@localhost:5432/notification_service",
)

os.environ["DATABASE_URL"] = DATABASE_URL

# Chạy alembic upgrade head
from alembic.config import Config
from alembic import command

cfg = Config("alembic.ini")
print(f"Migrating: {DATABASE_URL.split('@')[-1]}")  # log chỉ host, không log password
command.upgrade(cfg, "head")
print("Migration done.")

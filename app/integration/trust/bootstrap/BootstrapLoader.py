import base64
import json
import logging
from pathlib import Path

from app.integration.trust.bootstrap.BootstrapPayload import BootstrapPayload

_log = logging.getLogger(__name__)


class BootstrapLoader:
    """Reads and parses the bootstrap file (base64-encoded JSON)."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def exists(self) -> bool:
        return self._path.is_file() and self._path.stat().st_size > 0

    def load(self) -> BootstrapPayload:
        try:
            encoded = self._path.read_text(encoding="utf-8").strip()
            decoded = base64.b64decode(encoded).decode("utf-8")
            data = json.loads(decoded)
            return BootstrapPayload.from_dict(data)
        except Exception as e:
            raise RuntimeError(
                f"Failed to load bootstrap file: {self._path}\nCause: {e}"
            ) from e

    def delete(self) -> None:
        try:
            if self._path.exists():
                self._path.unlink()
                _log.info("Bootstrap file deleted: %s", self._path)
        except Exception as e:
            _log.error("Failed to delete bootstrap file %s: %s", self._path, e)

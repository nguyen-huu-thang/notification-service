from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class _BootstrapCertificate:
    id: str
    service_id: str
    public_cert: str
    private_key: str
    status: str
    issued_at: str   # Unix milliseconds as string
    expires_at: str  # Unix milliseconds as string
    deleted: bool = False

    def issued_at_datetime(self) -> datetime:
        return datetime.fromtimestamp(int(self.issued_at) / 1000.0, tz=timezone.utc)

    def expires_at_datetime(self) -> datetime:
        return datetime.fromtimestamp(int(self.expires_at) / 1000.0, tz=timezone.utc)


@dataclass(frozen=True)
class BootstrapPayload:
    certificate: _BootstrapCertificate
    token_id: str
    refresh_token: str

    @staticmethod
    def from_dict(data: dict) -> BootstrapPayload:
        cert_data = data["certificate"]
        cert = _BootstrapCertificate(
            id=cert_data["id"],
            service_id=cert_data["service_id"],
            public_cert=cert_data["public_cert"],
            private_key=cert_data["private_key"],
            status=cert_data["status"],
            issued_at=str(cert_data["issued_at"]),
            expires_at=str(cert_data["expires_at"]),
            deleted=cert_data.get("deleted", False),
        )
        return BootstrapPayload(
            certificate=cert,
            token_id=data["token_id"],
            refresh_token=data["refresh_token"],
        )

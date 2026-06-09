from dataclasses import dataclass


@dataclass(frozen=True)
class RootCertificate:
    pem: str  # CA cert PEM — used to verify Trust Service certificate

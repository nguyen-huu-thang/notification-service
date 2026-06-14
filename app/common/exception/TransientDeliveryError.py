class TransientDeliveryError(Exception):
    """Raised when a delivery attempt fails due to a transient infrastructure issue.

    Callers receiving this error via gRPC (UNAVAILABLE) may safely retry.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)

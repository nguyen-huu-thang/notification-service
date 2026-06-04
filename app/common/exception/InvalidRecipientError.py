class InvalidRecipientError(Exception):
    def __init__(self, target: str) -> None:
        super().__init__(f"Invalid recipient: {target!r}")
        self.target = target

class OtpNotFoundError(Exception):
    def __init__(self, otp_id: bytes) -> None:
        super().__init__(f"OTP not found: {otp_id.hex()}")
        self.otp_id = otp_id

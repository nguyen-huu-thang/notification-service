class OtpExpiredError(Exception):
    def __init__(self, otp_id: bytes) -> None:
        super().__init__(f"OTP expired: {otp_id.hex()}")
        self.otp_id = otp_id

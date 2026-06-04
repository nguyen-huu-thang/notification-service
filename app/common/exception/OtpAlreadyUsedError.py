class OtpAlreadyUsedError(Exception):
    def __init__(self, otp_id: bytes) -> None:
        super().__init__(f"OTP already used: {otp_id.hex()}")
        self.otp_id = otp_id

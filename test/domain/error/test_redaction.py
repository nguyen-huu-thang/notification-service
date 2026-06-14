"""
Unit tests — che lỗi theo kênh (phần quan trọng nhất về bảo mật của chuẩn).

  - PRIVATE  -> quy về E000000 trên mọi kênh ra ngoài
  - SYSTEM   -> lọt trên gRPC (liên service), bị che trên REST
  - PUBLIC   -> lọt trên mọi kênh
"""
from app.domain.error.Channel import Channel
from app.domain.error.error_code import get_error
from app.domain.error.redaction import redact_for_channel
from app.domain.error.Visibility import Visibility

_PRIVATE = get_error("E080000")  # notification Private, INTERNAL
_SYSTEM = get_error("E084000")   # notification System, UNAVAILABLE
_PUBLIC = get_error("E087000")   # notification Public, INVALID_ARGUMENT


def test_private_redacted_on_rest():
    out = redact_for_channel(_PRIVATE, Channel.REST_EXTERNAL)
    assert out.error_key == "E000000"


def test_private_redacted_on_grpc():
    out = redact_for_channel(_PRIVATE, Channel.GRPC_INTERNAL)
    assert out.error_key == "E000000"


def test_system_passes_on_grpc():
    out = redact_for_channel(_SYSTEM, Channel.GRPC_INTERNAL)
    assert out.error_key == _SYSTEM.error_key
    assert out.visibility is Visibility.SYSTEM


def test_system_redacted_on_rest_to_common_public():
    out = redact_for_channel(_SYSTEM, Channel.REST_EXTERNAL)
    # UNAVAILABLE không có mã public cùng họ -> rơi về E007000, không lộ key SYSTEM.
    assert out.error_key == "E007000"
    assert out.visibility is Visibility.PUBLIC


def test_public_passes_on_rest():
    out = redact_for_channel(_PUBLIC, Channel.REST_EXTERNAL)
    assert out.error_key == _PUBLIC.error_key


def test_public_passes_on_grpc():
    out = redact_for_channel(_PUBLIC, Channel.GRPC_INTERNAL)
    assert out.error_key == _PUBLIC.error_key

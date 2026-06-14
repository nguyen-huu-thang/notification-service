# Immutable descriptor of a single catalog error code.
# Mô tả bất biến của một mã lỗi trong catalog.
#
# Domain pure: uses int http_status + a neutral GrpcCode (no grpc/framework dep).
# Domain thuần: dùng int http_status + GrpcCode trung lập (không phụ thuộc grpc/framework).
from dataclasses import dataclass

from app.domain.error.GrpcCode import GrpcCode
from app.domain.error.Visibility import Visibility


@dataclass(frozen=True)
class ErrorDef:
    # errorKey = "E" + code zero-padded to the tier width (6 digits for Base Platform).
    # errorKey = "E" + code zero-pad theo độ rộng tầng (6 chữ số cho Base Platform).
    error_key: str
    code: int
    message: str
    http_status: int
    grpc_code: GrpcCode
    visibility: Visibility

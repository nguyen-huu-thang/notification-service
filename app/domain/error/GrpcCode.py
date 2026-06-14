# Language-neutral gRPC status code, mirroring the names of grpc.StatusCode.
# Mã trạng thái gRPC trung lập, trùng tên với grpc.StatusCode.
#
# Kept in the domain layer so the domain does not depend on the grpc library.
# The gRPC adapter converts to grpc.StatusCode via grpc.StatusCode[code.name].
# Giữ ở tầng domain để domain không phụ thuộc thư viện grpc. Adapter gRPC chuyển
# sang grpc.StatusCode bằng grpc.StatusCode[code.name].
from enum import Enum


class GrpcCode(Enum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FAILED_PRECONDITION = "FAILED_PRECONDITION"
    UNAVAILABLE = "UNAVAILABLE"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    INTERNAL = "INTERNAL"

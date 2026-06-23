from app.config.logging import configure_logging

# Structured JSON logging must be installed before the Xime bootstrap emits any
# log, so the framework's default logging defers to ours.
# Cài log JSON trước khi Xime bootstrap log dòng nào, để logging mặc định của
# framework nhường cho ta.
configure_logging()

import app.config.grpc  # noqa: E402, F401 — registers gRPC services and error mappings

from xime import Application  # noqa: E402
from xime.adapters.grpc import GrpcAdapter  # noqa: E402

app = Application(config_module="app.config.dependency")

if __name__ == "__main__":
    app.use(GrpcAdapter()).run()

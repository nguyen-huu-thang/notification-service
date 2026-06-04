import app.config.grpc  # noqa: F401 — registers gRPC services and error mappings

from xime import Application
from xime.adapters.grpc import GrpcAdapter

app = Application(config_module="app.config.dependency")

if __name__ == "__main__":
    app.use(GrpcAdapter()).run()

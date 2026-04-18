from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class EmulatorConfig:
    bind_host: str = "127.0.0.1"
    http_port: int = 8080
    login_port: int = 4021
    capture_root: Path = Path("captures")

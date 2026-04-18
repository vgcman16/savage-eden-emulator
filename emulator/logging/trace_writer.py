from __future__ import annotations

from pathlib import Path
from time import strftime


class TraceWriter:
    def __init__(self, capture_root: Path) -> None:
        self.capture_root = capture_root
        self.run_dir: Path | None = None

    def start_run(self, label: str) -> Path:
        timestamp = strftime("%Y%m%d-%H%M%S")
        self.run_dir = self.capture_root / f"{timestamp}-{label}"
        (self.run_dir / "packets").mkdir(parents=True, exist_ok=True)
        return self.run_dir

    def _require_run_dir(self) -> Path:
        if self.run_dir is None:
            raise RuntimeError("start_run() must be called before writing traces")
        return self.run_dir

    def write_text(self, relative_path: str, content: str) -> Path:
        target = self._require_run_dir() / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def append_text(self, relative_path: str, content: str) -> Path:
        target = self._require_run_dir() / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(content)
        return target

    def write_bytes(self, relative_path: str, content: bytes) -> Path:
        target = self._require_run_dir() / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return target

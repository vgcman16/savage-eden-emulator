# Laghaim Milestone 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python compatibility shim that makes the stock launcher report a local server as online, captures the first login exchange, and drives the stock client through a scripted stub-login path.

**Architecture:** The implementation is a small Python package with four runtime parts: configuration, trace writing, launcher HTTP probe, and login gateway. The gateway stays protocol-agnostic at first by capturing raw bytes and then graduating to a fixture-driven reply engine so the team can iterate toward a working stub-login without rebuilding the entire game server.

**Tech Stack:** Python 3.12, standard library (`argparse`, `dataclasses`, `http.server`, `json`, `pathlib`, `socket`, `socketserver`, `threading`, `time`, `unittest`)

---

### Task 1: Create The Python Skeleton And Default Config

**Files:**
- Create: `pyproject.toml`
- Create: `emulator/__init__.py`
- Create: `emulator/config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from pathlib import Path
import unittest

from emulator.config import EmulatorConfig


class EmulatorConfigTests(unittest.TestCase):
    def test_defaults_match_milestone_one_expectations(self) -> None:
        config = EmulatorConfig()

        self.assertEqual(config.bind_host, "127.0.0.1")
        self.assertEqual(config.http_port, 8080)
        self.assertEqual(config.login_port, 4021)
        self.assertEqual(config.capture_root, Path("captures"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest -v tests.test_config
```

Expected:

```text
ERROR: test_config (unittest.loader._FailedTest.test_config)
ModuleNotFoundError: No module named 'emulator'
```

- [ ] **Step 3: Write minimal implementation**

```toml
# pyproject.toml
[project]
name = "savage-eden-emulator"
version = "0.1.0"
requires-python = ">=3.12"
description = "Local preservation and compatibility tooling for the Laghaim client"
```

```python
# emulator/__init__.py
"""Laghaim emulator package."""
```

```python
# emulator/config.py
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class EmulatorConfig:
    bind_host: str = "127.0.0.1"
    http_port: int = 8080
    login_port: int = 4021
    capture_root: Path = Path("captures")
```

```python
# tests/__init__.py
"""Unit tests for the Laghaim emulator."""
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest -v tests.test_config
```

Expected:

```text
test_defaults_match_milestone_one_expectations ... ok
```

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml emulator/__init__.py emulator/config.py tests/__init__.py tests/test_config.py
git commit -m "feat: add emulator config scaffold"
```

### Task 2: Add Trace Writing And Run Directories

**Files:**
- Create: `emulator/logging/__init__.py`
- Create: `emulator/logging/trace_writer.py`
- Create: `tests/test_trace_writer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_trace_writer.py
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from emulator.logging.trace_writer import TraceWriter


class TraceWriterTests(unittest.TestCase):
    def test_start_run_creates_packets_directory_and_summary_file(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            writer = TraceWriter(Path(tmp_dir))
            run_dir = writer.start_run("smoke")
            writer.write_text("summary.md", "ready\n")
            writer.write_bytes("packets/conn-0001-in-0001.bin", b"\x01\x02")

            self.assertTrue((run_dir / "summary.md").exists())
            self.assertTrue((run_dir / "packets").is_dir())
            self.assertEqual((run_dir / "packets/conn-0001-in-0001.bin").read_bytes(), b"\x01\x02")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest -v tests.test_trace_writer
```

Expected:

```text
ModuleNotFoundError: No module named 'emulator.logging'
```

- [ ] **Step 3: Write minimal implementation**

```python
# emulator/logging/__init__.py
"""Logging helpers for packet capture and run summaries."""
```

```python
# emulator/logging/trace_writer.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest -v tests.test_trace_writer
```

Expected:

```text
test_start_run_creates_packets_directory_and_summary_file ... ok
```

- [ ] **Step 5: Commit**

```powershell
git add emulator/logging/__init__.py emulator/logging/trace_writer.py tests/test_trace_writer.py
git commit -m "feat: add trace writer and run directories"
```

### Task 3: Implement The Launcher HTTP Probe

**Files:**
- Create: `emulator/services/__init__.py`
- Create: `emulator/services/http_probe.py`
- Create: `tests/test_http_probe.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_http_probe.py
from http.client import HTTPConnection
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from emulator.logging.trace_writer import TraceWriter
from emulator.services.http_probe import HttpProbeService


class HttpProbeTests(unittest.TestCase):
    def test_probe_returns_online_and_no_update_markers(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            writer = TraceWriter(Path(tmp_dir))
            writer.start_run("probe")
            probe = HttpProbeService("127.0.0.1", 0, writer)
            probe.start()
            try:
                conn = HTTPConnection("127.0.0.1", probe.port, timeout=2)
                conn.request("GET", "/status")
                response = conn.getresponse()
                body = response.read().decode("utf-8")
            finally:
                probe.stop()

            self.assertEqual(response.status, 200)
            self.assertIn("SERVER ONLINE!", body)
            self.assertIn("NO_UPDATE", body)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest -v tests.test_http_probe
```

Expected:

```text
ModuleNotFoundError: No module named 'emulator.services'
```

- [ ] **Step 3: Write minimal implementation**

```python
# emulator/services/__init__.py
"""Runtime services for the Laghaim emulator."""
```

```python
# emulator/services/http_probe.py
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from emulator.logging.trace_writer import TraceWriter


class _ProbeHandler(BaseHTTPRequestHandler):
    writer: TraceWriter

    def do_GET(self) -> None:  # noqa: N802
        body = "SERVER ONLINE!\nNO_UPDATE\n"
        self.writer.append_text(
            "launcher-http.log",
            f"{self.command} {self.path} from {self.client_address[0]}:{self.client_address[1]}\n",
        )
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        return


class HttpProbeService:
    def __init__(self, host: str, port: int, writer: TraceWriter) -> None:
        handler = type("ProbeHandler", (_ProbeHandler,), {"writer": writer})
        self._server = ThreadingHTTPServer((host, port), handler)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest -v tests.test_http_probe
```

Expected:

```text
test_probe_returns_online_and_no_update_markers ... ok
```

- [ ] **Step 5: Commit**

```powershell
git add emulator/services/__init__.py emulator/services/http_probe.py tests/test_http_probe.py
git commit -m "feat: add launcher http probe"
```

### Task 4: Implement The Raw Login Gateway Capture

**Files:**
- Create: `emulator/services/login_gateway.py`
- Create: `tests/test_login_gateway.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_login_gateway.py
from pathlib import Path
from tempfile import TemporaryDirectory
import socket
import time
import unittest

from emulator.logging.trace_writer import TraceWriter
from emulator.services.login_gateway import LoginGatewayService


class LoginGatewayTests(unittest.TestCase):
    def test_gateway_captures_first_inbound_packet(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            writer = TraceWriter(Path(tmp_dir))
            run_dir = writer.start_run("login")
            gateway = LoginGatewayService("127.0.0.1", 0, writer)
            gateway.start()
            try:
                with socket.create_connection(("127.0.0.1", gateway.port), timeout=2) as client:
                    client.sendall(b"\x01\x02login")
                    time.sleep(0.2)
            finally:
                gateway.stop()

            packet_files = sorted((run_dir / "packets").glob("*.bin"))
            self.assertEqual(len(packet_files), 1)
            self.assertEqual(packet_files[0].read_bytes(), b"\x01\x02login")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest -v tests.test_login_gateway
```

Expected:

```text
ImportError: cannot import name 'LoginGatewayService'
```

- [ ] **Step 3: Write minimal implementation**

```python
# emulator/services/login_gateway.py
from __future__ import annotations

import socketserver
from threading import Thread

from emulator.logging.trace_writer import TraceWriter


class _LoginGatewayHandler(socketserver.BaseRequestHandler):
    writer: TraceWriter
    counter: int = 0

    def handle(self) -> None:
        payload = self.request.recv(4096)
        if not payload:
            return
        type(self).counter += 1
        packet_name = f"packets/conn-0001-in-{type(self).counter:04d}.bin"
        self.writer.write_bytes(packet_name, payload)


class _ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


class LoginGatewayService:
    def __init__(self, host: str, port: int, writer: TraceWriter) -> None:
        handler = type("LoginHandler", (_LoginGatewayHandler,), {"writer": writer, "counter": 0})
        self._server = _ThreadingTCPServer((host, port), handler)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest -v tests.test_login_gateway
```

Expected:

```text
test_gateway_captures_first_inbound_packet ... ok
```

- [ ] **Step 5: Commit**

```powershell
git add emulator/services/login_gateway.py tests/test_login_gateway.py
git commit -m "feat: capture raw login packets"
```

### Task 5: Add The Runner CLI

**Files:**
- Create: `emulator/runner.py`
- Create: `tests/test_runner.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_runner.py
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from emulator import runner


class RunnerTests(unittest.TestCase):
    def test_main_once_starts_and_stops_services(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            exit_code = runner.main(
                [
                    "--capture-root",
                    tmp_dir,
                    "--http-port",
                    "0",
                    "--login-port",
                    "0",
                    "--once",
                ]
            )

            self.assertEqual(exit_code, 0)
            run_dirs = list(Path(tmp_dir).glob("*"))
            self.assertEqual(len(run_dirs), 1)
            self.assertTrue((run_dirs[0] / "summary.md").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest -v tests.test_runner
```

Expected:

```text
ImportError: cannot import name 'runner'
```

- [ ] **Step 3: Write minimal implementation**

```python
# emulator/runner.py
from __future__ import annotations

import argparse

from emulator.config import EmulatorConfig
from emulator.logging.trace_writer import TraceWriter
from emulator.services.http_probe import HttpProbeService
from emulator.services.login_gateway import LoginGatewayService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind-host", default="127.0.0.1")
    parser.add_argument("--http-port", type=int, default=8080)
    parser.add_argument("--login-port", type=int, default=4021)
    parser.add_argument("--capture-root", default="captures")
    parser.add_argument("--once", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = EmulatorConfig(
        bind_host=args.bind_host,
        http_port=args.http_port,
        login_port=args.login_port,
        capture_root=args.capture_root,
    )
    writer = TraceWriter(config.capture_root)
    run_dir = writer.start_run("runner")
    http_probe = HttpProbeService(config.bind_host, config.http_port, writer)
    login_gateway = LoginGatewayService(config.bind_host, config.login_port, writer)
    http_probe.start()
    login_gateway.start()
    writer.write_text(
        "summary.md",
        (
            f"bind_host={config.bind_host}\n"
            f"http_port={http_probe.port}\n"
            f"login_port={login_gateway.port}\n"
            f"run_dir={run_dir}\n"
        ),
    )
    if args.once:
        http_probe.stop()
        login_gateway.stop()
        return 0
    try:
        while True:
            pass
    except KeyboardInterrupt:
        http_probe.stop()
        login_gateway.stop()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest -v tests.test_runner
```

Expected:

```text
test_main_once_starts_and_stops_services ... ok
```

- [ ] **Step 5: Commit**

```powershell
git add emulator/runner.py tests/test_runner.py
git commit -m "feat: add emulator runner cli"
```

### Task 6: Normalize Captures And Record The First Real Run

**Files:**
- Create: `emulator/tools/__init__.py`
- Create: `emulator/tools/normalize_capture.py`
- Create: `tests/test_normalize_capture.py`
- Create: `notes/research/milestone-1-observations.md`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_normalize_capture.py
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from emulator.tools.normalize_capture import normalize_capture


class NormalizeCaptureTests(unittest.TestCase):
    def test_normalize_capture_copies_packet_files_and_writes_manifest(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source = tmp_path / "source"
            target = tmp_path / "target"
            (source / "packets").mkdir(parents=True)
            (source / "packets" / "conn-0001-in-0001.bin").write_bytes(b"\xAA\xBB")

            normalize_capture(source, target)

            self.assertEqual((target / "packets" / "conn-0001-in-0001.bin").read_bytes(), b"\xAA\xBB")
            self.assertTrue((target / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest -v tests.test_normalize_capture
```

Expected:

```text
ModuleNotFoundError: No module named 'emulator.tools'
```

- [ ] **Step 3: Write minimal implementation**

```python
# emulator/tools/__init__.py
"""Utility tools for offline capture processing."""
```

```python
# emulator/tools/normalize_capture.py
from __future__ import annotations

import json
import shutil
from pathlib import Path


def normalize_capture(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    packet_target = target / "packets"
    packet_target.mkdir(parents=True, exist_ok=True)
    packet_files = sorted((source / "packets").glob("*.bin"))
    for packet_file in packet_files:
        shutil.copy2(packet_file, packet_target / packet_file.name)
    manifest = {"source": str(source), "packets": [packet.name for packet in packet_files]}
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
```

```markdown
# notes/research/milestone-1-observations.md
# Milestone 1 Observations

- Launcher probe status: not run yet
- Login gateway status: not run yet
- First packet capture: not run yet
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest -v tests.test_normalize_capture
```

Expected:

```text
test_normalize_capture_copies_packet_files_and_writes_manifest ... ok
```

- [ ] **Step 5: Commit**

```powershell
git add emulator/tools/__init__.py emulator/tools/normalize_capture.py tests/test_normalize_capture.py notes/research/milestone-1-observations.md
git commit -m "feat: add capture normalization tooling"
```

### Task 7: Implement Framing Helpers For Packet Analysis

**Files:**
- Create: `emulator/protocol/__init__.py`
- Create: `emulator/protocol/framing.py`
- Create: `tests/test_framing.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_framing.py
import unittest

from emulator.protocol.framing import hexdump, read_u16_le, read_u32_le, xor_bytes


class FramingTests(unittest.TestCase):
    def test_helpers_cover_basic_binary_analysis(self) -> None:
        self.assertEqual(read_u16_le(b"\x34\x12"), 0x1234)
        self.assertEqual(read_u32_le(b"\x78\x56\x34\x12"), 0x12345678)
        self.assertEqual(xor_bytes(b"\x01\x02", 0xFF), b"\xFE\xFD")
        self.assertIn("01 02 03", hexdump(b"\x01\x02\x03"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest -v tests.test_framing
```

Expected:

```text
ModuleNotFoundError: No module named 'emulator.protocol'
```

- [ ] **Step 3: Write minimal implementation**

```python
# emulator/protocol/__init__.py
"""Binary protocol helpers for the Laghaim emulator."""
```

```python
# emulator/protocol/framing.py
from __future__ import annotations


def read_u16_le(data: bytes) -> int:
    return int.from_bytes(data[:2], "little")


def read_u32_le(data: bytes) -> int:
    return int.from_bytes(data[:4], "little")


def xor_bytes(data: bytes, key: int) -> bytes:
    return bytes(value ^ key for value in data)


def hexdump(data: bytes) -> str:
    hex_part = " ".join(f"{value:02X}" for value in data)
    return f"00000000  {hex_part}"
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m unittest -v tests.test_framing
```

Expected:

```text
test_helpers_cover_basic_binary_analysis ... ok
```

- [ ] **Step 5: Commit**

```powershell
git add emulator/protocol/__init__.py emulator/protocol/framing.py tests/test_framing.py
git commit -m "feat: add packet framing helpers"
```

### Task 8: Add A Fixture-Driven Reply Engine For The Login Gateway

**Files:**
- Create: `emulator/protocol/conversation.py`
- Modify: `emulator/services/login_gateway.py`
- Create: `tests/test_conversation.py`
- Create: `tests/test_login_gateway_replay.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_conversation.py
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from emulator.protocol.conversation import ConversationScript


class ConversationScriptTests(unittest.TestCase):
    def test_loads_match_and_response_hex(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            script_path = Path(tmp_dir) / "login-script.json"
            script_path.write_text(
                json.dumps(
                    {
                        "match_hex": "01026C6F67696E",
                        "response_hex": "90000000",
                    }
                ),
                encoding="utf-8",
            )
            script = ConversationScript.load(script_path)
            self.assertEqual(script.match_bytes, b"\x01\x02login")
            self.assertEqual(script.response_bytes, b"\x90\x00\x00\x00")


if __name__ == "__main__":
    unittest.main()
```

```python
# tests/test_login_gateway_replay.py
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import socket
import time
import unittest

from emulator.logging.trace_writer import TraceWriter
from emulator.services.login_gateway import LoginGatewayService


class LoginGatewayReplayTests(unittest.TestCase):
    def test_gateway_replays_scripted_response_on_match(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            script_path = tmp_path / "login-script.json"
            script_path.write_text(
                json.dumps(
                    {
                        "match_hex": "01026C6F67696E",
                        "response_hex": "90000000",
                    }
                ),
                encoding="utf-8",
            )
            writer = TraceWriter(tmp_path)
            writer.start_run("replay")
            gateway = LoginGatewayService("127.0.0.1", 0, writer, script_path=script_path)
            gateway.start()
            try:
                with socket.create_connection(("127.0.0.1", gateway.port), timeout=2) as client:
                    client.sendall(b"\x01\x02login")
                    time.sleep(0.2)
                    response = client.recv(16)
            finally:
                gateway.stop()

            self.assertEqual(response, b"\x90\x00\x00\x00")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m unittest -v tests.test_conversation tests.test_login_gateway_replay
```

Expected:

```text
ModuleNotFoundError: No module named 'emulator.protocol.conversation'
TypeError: LoginGatewayService.__init__() got an unexpected keyword argument 'script_path'
```

- [ ] **Step 3: Write minimal implementation**

```python
# emulator/protocol/conversation.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ConversationScript:
    match_bytes: bytes
    response_bytes: bytes

    @classmethod
    def load(cls, path: Path) -> "ConversationScript":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            match_bytes=bytes.fromhex(payload["match_hex"]),
            response_bytes=bytes.fromhex(payload["response_hex"]),
        )
```

```python
# emulator/services/login_gateway.py
from __future__ import annotations

import socketserver
from pathlib import Path
from threading import Thread

from emulator.logging.trace_writer import TraceWriter
from emulator.protocol.conversation import ConversationScript


class _LoginGatewayHandler(socketserver.BaseRequestHandler):
    writer: TraceWriter
    script: ConversationScript | None
    counter: int = 0

    def handle(self) -> None:
        payload = self.request.recv(4096)
        if not payload:
            return
        type(self).counter += 1
        packet_name = f"packets/conn-0001-in-{type(self).counter:04d}.bin"
        self.writer.write_bytes(packet_name, payload)
        if self.script is not None and payload == self.script.match_bytes:
            self.request.sendall(self.script.response_bytes)
            self.writer.write_bytes("packets/conn-0001-out-0001.bin", self.script.response_bytes)


class _ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


class LoginGatewayService:
    def __init__(self, host: str, port: int, writer: TraceWriter, script_path: Path | None = None) -> None:
        script = ConversationScript.load(script_path) if script_path is not None else None
        handler = type(
            "LoginHandler",
            (_LoginGatewayHandler,),
            {"writer": writer, "counter": 0, "script": script},
        )
        self._server = _ThreadingTCPServer((host, port), handler)
        self._thread = Thread(target=self._server.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
python -m unittest -v tests.test_conversation tests.test_login_gateway_replay
```

Expected:

```text
test_loads_match_and_response_hex ... ok
test_gateway_replays_scripted_response_on_match ... ok
```

- [ ] **Step 5: Commit**

```powershell
git add emulator/protocol/conversation.py emulator/services/login_gateway.py tests/test_conversation.py tests/test_login_gateway_replay.py
git commit -m "feat: add scripted login reply engine"
```

### Task 9: Run The Real Client Against Localhost And Update The Checkpoint List

**Files:**
- Modify: `notes/research/milestone-1-observations.md`
- Modify: `docs/superpowers/specs/2026-04-18-laghaim-milestone-1-design.md`
- Create: `notes/research/login-script.json`

- [ ] **Step 1: Start the emulator locally**

Run:

```powershell
python -m emulator.runner --capture-root captures --http-port 18080 --login-port 14021
```

Expected:

```text
summary.md written under captures/<timestamp>-runner
```

- [ ] **Step 2: Point the stock launcher at localhost and capture the first live run**

Run:

```powershell
Start-Process "C:\Users\skull\OneDrive\Documents\savage eden\client\LaghaimOnlineNew\LAUNCHER_PLAY.exe"
```

Manual verification target:

```text
ServerIP = 127.0.0.1
CSPort = 18080
GSPort = 14021
```

Expected:

```text
launcher-http.log appears under the newest captures/<timestamp>-runner directory
packets/conn-0001-in-0001.bin appears after entering login credentials
```

- [ ] **Step 3: Normalize the newest run and create the first reply script**

Run:

```powershell
$latest = Get-ChildItem captures -Directory | Sort-Object Name | Select-Object -Last 1
python -c "from pathlib import Path; from emulator.tools.normalize_capture import normalize_capture; normalize_capture(Path(r'$($latest.FullName)'), Path('captures/latest'))"
python - <<'PY'
from pathlib import Path
import json

request_bytes = (Path('captures/latest/packets') / 'conn-0001-in-0001.bin').read_bytes()
script_path = Path('notes/research/login-script.json')
script_path.parent.mkdir(parents=True, exist_ok=True)
script_path.write_text(
    json.dumps(
        {
            'match_hex': request_bytes.hex(),
            'response_hex': '90000000',
        },
        indent=2,
    ),
    encoding='utf-8',
)
PY
```

Expected:

```text
captures/latest/manifest.json exists
notes/research/login-script.json exists
```

- [ ] **Step 4: Re-run the emulator with the scripted response and record the outcome**

Run:

```powershell
python - <<'PY'
from pathlib import Path
import json

path = Path('notes/research/login-script.json')
payload = json.loads(path.read_text(encoding='utf-8'))
candidate_responses = [
    '90000000',
    '00000000',
    '01000000',
    payload['match_hex'][:4] + '0000',
    payload['match_hex'][:8] + '00000000',
]
path.write_text(
    json.dumps(
        {
            'match_hex': payload['match_hex'],
            'response_hex': candidate_responses[0],
        },
        indent=2,
    ),
    encoding='utf-8',
)
PY
python -m emulator.runner --capture-root captures --http-port 18080 --login-port 14021
```

Expected:

```text
The client either advances past the login dialog or fails at a clearly visible next step.
The newest run contains conn-0001-in-0001.bin and conn-0001-out-0001.bin.
```

- [ ] **Step 5: Update notes and checkboxes, then commit**

Update `notes/research/milestone-1-observations.md` with:

```markdown
- Launcher probe status: include the exact status path and body seen in `launcher-http.log`
- Login gateway status: include the first captured login packet file name
- First packet capture: include packet size, first 16 bytes, and whether the scripted response advanced the client
```

Update `docs/superpowers/specs/2026-04-18-laghaim-milestone-1-design.md` by checking off each milestone checkpoint completed during the real run.

Commit:

```powershell
git add notes/research/milestone-1-observations.md notes/research/login-script.json docs/superpowers/specs/2026-04-18-laghaim-milestone-1-design.md
git commit -m "docs: record milestone one probe and login findings"
```

## Self-Review

- Spec coverage:
  - project skeleton: covered by Tasks 1-2
  - launcher probe: covered by Task 3
  - runner and one-command startup: covered by Task 5
  - capture logging: covered by Tasks 2, 4, and 6
  - framing helpers: covered by Task 7
  - scripted stub-login path: covered by Tasks 8-9
  - checkpoint updates: covered by Task 9
- Placeholder scan:
  - removed all `TODO` and `TBD` markers
  - replaced vague “figure out later” language with concrete files, commands, and candidate responses
- Type consistency:
  - `EmulatorConfig`, `TraceWriter`, `HttpProbeService`, `LoginGatewayService`, and `ConversationScript` are used consistently across tasks


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

from __future__ import annotations

import select
import socket
import socketserver
from pathlib import Path
from threading import Lock, Thread

from emulator.logging.trace_writer import TraceWriter
from emulator.protocol.conversation import ConversationScript


class _LoginGatewayHandler(socketserver.BaseRequestHandler):
    writer: TraceWriter
    script: ConversationScript | None
    proxy_target: tuple[str, int] | None
    in_counter: int = 0
    out_counter: int = 0
    counter_lock: Lock

    @classmethod
    def _next_packet_name(cls, direction: str) -> str:
        with cls.counter_lock:
            if direction == "in":
                cls.in_counter += 1
                counter = cls.in_counter
            else:
                cls.out_counter += 1
                counter = cls.out_counter
        return f"packets/conn-0001-{direction}-{counter:04d}.bin"

    def _write_packet(self, direction: str, payload: bytes) -> None:
        packet_name = type(self)._next_packet_name(direction)
        self.writer.write_bytes(packet_name, payload)

    def _proxy_session(self) -> None:
        assert self.proxy_target is not None
        with socket.create_connection(self.proxy_target, timeout=5) as upstream:
            sockets: dict[socket.socket, tuple[str, socket.socket]] = {
                self.request: ("in", upstream),
                upstream: ("out", self.request),
            }
            while sockets:
                readable, _, _ = select.select(list(sockets), [], [], 0.25)
                if not readable:
                    continue
                for source in readable:
                    direction, sink = sockets[source]
                    try:
                        payload = source.recv(4096)
                    except OSError:
                        payload = b""
                    if not payload:
                        sockets.pop(source, None)
                        try:
                            sink.shutdown(socket.SHUT_WR)
                        except OSError:
                            pass
                        continue
                    self._write_packet(direction, payload)
                    sink.sendall(payload)

    def handle(self) -> None:
        if self.proxy_target is not None:
            self._proxy_session()
            return

        self.request.settimeout(1.0)
        while True:
            try:
                payload = self.request.recv(4096)
            except (ConnectionResetError, TimeoutError):
                break
            if not payload:
                break

            self._write_packet("in", payload)

            if self.script is not None and payload == self.script.match_bytes:
                self.request.sendall(self.script.response_bytes)
                self._write_packet("out", self.script.response_bytes)
                if self.script.close_after_response:
                    break


class _ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


class LoginGatewayService:
    def __init__(
        self,
        host: str,
        port: int,
        writer: TraceWriter,
        script_path: Path | None = None,
        proxy_host: str | None = None,
        proxy_port: int | None = None,
    ) -> None:
        script = ConversationScript.load(script_path) if script_path is not None else None
        proxy_target = None
        if proxy_host is not None:
            if proxy_port is None:
                raise ValueError("proxy_port is required when proxy_host is set")
            proxy_target = (proxy_host, proxy_port)
        handler = type(
            "LoginHandler",
            (_LoginGatewayHandler,),
            {
                "writer": writer,
                "in_counter": 0,
                "out_counter": 0,
                "counter_lock": Lock(),
                "script": script,
                "proxy_target": proxy_target,
            },
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

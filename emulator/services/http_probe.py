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

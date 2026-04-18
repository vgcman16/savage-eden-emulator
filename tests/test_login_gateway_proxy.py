from pathlib import Path
from tempfile import TemporaryDirectory
import socket
import socketserver
import threading
import unittest

from emulator.logging.trace_writer import TraceWriter
from emulator.services.login_gateway import LoginGatewayService


class _UpstreamHandler(socketserver.BaseRequestHandler):
    received_payloads: list[bytes]
    response_bytes: bytes

    def handle(self) -> None:
        payload = self.request.recv(4096)
        if payload:
            type(self).received_payloads.append(payload)
            self.request.sendall(type(self).response_bytes)


class _ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


class LoginGatewayProxyTests(unittest.TestCase):
    def test_gateway_proxies_login_exchange_and_captures_both_directions(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            writer = TraceWriter(tmp_path)
            run_dir = writer.start_run("proxy")

            upstream_handler = type(
                "UpstreamHandler",
                (_UpstreamHandler,),
                {
                    "received_payloads": [],
                    "response_bytes": b"\x10\x00proxy-response",
                },
            )
            upstream_server = _ThreadingTCPServer(("127.0.0.1", 0), upstream_handler)
            upstream_thread = threading.Thread(target=upstream_server.serve_forever, daemon=True)
            upstream_thread.start()

            gateway = LoginGatewayService(
                "127.0.0.1",
                0,
                writer,
                proxy_host="127.0.0.1",
                proxy_port=int(upstream_server.server_address[1]),
            )
            gateway.start()
            try:
                with socket.create_connection(("127.0.0.1", gateway.port), timeout=2) as client:
                    client.settimeout(1)
                    client.sendall(b"\x01\x02login")
                    response = client.recv(64)
            finally:
                gateway.stop()
                upstream_server.shutdown()
                upstream_server.server_close()
                upstream_thread.join(timeout=2)

            self.assertEqual(response, b"\x10\x00proxy-response")
            self.assertEqual(upstream_handler.received_payloads, [b"\x01\x02login"])

            packet_files = sorted((run_dir / "packets").glob("*.bin"))
            self.assertEqual(
                [packet.name for packet in packet_files],
                [
                    "conn-0001-in-0001.bin",
                    "conn-0001-out-0001.bin",
                ],
            )
            self.assertEqual(packet_files[0].read_bytes(), b"\x01\x02login")
            self.assertEqual(packet_files[1].read_bytes(), b"\x10\x00proxy-response")

    def test_gateway_can_write_proxy_packets_into_a_custom_directory(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            writer = TraceWriter(tmp_path)
            run_dir = writer.start_run("proxy-custom-dir")

            upstream_handler = type(
                "UpstreamHandler",
                (_UpstreamHandler,),
                {
                    "received_payloads": [],
                    "response_bytes": b"\x10\x00world-response",
                },
            )
            upstream_server = _ThreadingTCPServer(("127.0.0.1", 0), upstream_handler)
            upstream_thread = threading.Thread(target=upstream_server.serve_forever, daemon=True)
            upstream_thread.start()

            gateway = LoginGatewayService(
                "127.0.0.1",
                0,
                writer,
                proxy_host="127.0.0.1",
                proxy_port=int(upstream_server.server_address[1]),
                packet_dir="packets/world-4007",
            )
            gateway.start()
            try:
                with socket.create_connection(("127.0.0.1", gateway.port), timeout=2) as client:
                    client.settimeout(1)
                    client.sendall(b"\x03\x04world")
                    response = client.recv(64)
            finally:
                gateway.stop()
                upstream_server.shutdown()
                upstream_server.server_close()
                upstream_thread.join(timeout=2)

            self.assertEqual(response, b"\x10\x00world-response")
            packet_files = sorted((run_dir / "packets" / "world-4007").glob("*.bin"))
            self.assertEqual(
                [packet.name for packet in packet_files],
                [
                    "conn-0001-in-0001.bin",
                    "conn-0001-out-0001.bin",
                ],
            )
            self.assertEqual(packet_files[0].read_bytes(), b"\x03\x04world")
            self.assertEqual(packet_files[1].read_bytes(), b"\x10\x00world-response")


if __name__ == "__main__":
    unittest.main()

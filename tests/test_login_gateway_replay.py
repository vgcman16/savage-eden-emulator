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

    def test_gateway_keeps_connection_open_for_follow_up_packets(self) -> None:
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
            run_dir = writer.start_run("replay-loop")
            gateway = LoginGatewayService("127.0.0.1", 0, writer, script_path=script_path)
            gateway.start()
            try:
                with socket.create_connection(("127.0.0.1", gateway.port), timeout=2) as client:
                    client.sendall(b"\x01\x02login")
                    response = client.recv(16)
                    self.assertEqual(response, b"\x90\x00\x00\x00")
                    client.sendall(b"\x05\x06next")
                    time.sleep(0.2)
            finally:
                gateway.stop()

            packet_files = sorted((run_dir / "packets").glob("*.bin"))
            self.assertEqual(
                [packet.name for packet in packet_files],
                [
                    "conn-0001-in-0001.bin",
                    "conn-0001-in-0002.bin",
                    "conn-0001-out-0001.bin",
                ],
            )
            self.assertEqual(packet_files[1].read_bytes(), b"\x05\x06next")

    def test_gateway_can_close_immediately_after_scripted_response(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            script_path = tmp_path / "login-script.json"
            script_path.write_text(
                json.dumps(
                    {
                        "match_hex": "01026C6F67696E",
                        "response_hex": "1000F142961C941E8D58BC1AF5D3E2F7DEF5",
                        "close_after_response": True,
                    }
                ),
                encoding="utf-8",
            )
            writer = TraceWriter(tmp_path)
            writer.start_run("replay-close")
            gateway = LoginGatewayService("127.0.0.1", 0, writer, script_path=script_path)
            gateway.start()
            try:
                with socket.create_connection(("127.0.0.1", gateway.port), timeout=2) as client:
                    client.settimeout(0.3)
                    client.sendall(b"\x01\x02login")
                    response = client.recv(32)
                    self.assertEqual(
                        response,
                        bytes.fromhex("1000F142961C941E8D58BC1AF5D3E2F7DEF5"),
                    )
                    follow_up = client.recv(1)
            finally:
                gateway.stop()

            self.assertEqual(follow_up, b"")


if __name__ == "__main__":
    unittest.main()

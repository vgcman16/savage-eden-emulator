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

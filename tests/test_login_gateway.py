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

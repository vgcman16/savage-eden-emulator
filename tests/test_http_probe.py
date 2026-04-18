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

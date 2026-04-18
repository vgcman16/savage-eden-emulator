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

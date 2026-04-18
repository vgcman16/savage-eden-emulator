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

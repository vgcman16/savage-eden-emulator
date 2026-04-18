from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from emulator.tools.frame_index import write_frame_index


def _make_frame(payload: bytes) -> bytes:
    return len(payload).to_bytes(2, "little") + payload


class FrameIndexTests(unittest.TestCase):
    def test_write_frame_index_splits_chunks_into_families(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source = tmp_path / "source"
            target = tmp_path / "target"
            (source / "packets").mkdir(parents=True)
            (source / "packets" / "conn-0001-out-0001.bin").write_bytes(
                _make_frame(b"OBJECT alpha 100") + _make_frame(b"PING world-state")
            )
            (source / "packets" / "proxy-4007").mkdir(parents=True)
            (source / "packets" / "proxy-4007" / "conn-0001-out-0002.bin").write_bytes(
                _make_frame(b"OBJECT bravo 200")
            )
            (source / "packets" / "proxy-4007" / "conn-0001-in-0001.bin").write_bytes(
                _make_frame(b"HELLO login")
            )

            write_frame_index(source, target)

            frame_index = json.loads((target / "frame-index.json").read_text(encoding="utf-8"))
            self.assertEqual(frame_index["chunk_count"], 3)
            self.assertEqual(frame_index["frame_count"], 4)
            self.assertEqual(frame_index["family_count"], 3)

            frame_names = [
                (
                    frame["source_packet"],
                    frame["frame_index"],
                    frame["frame_offset"],
                )
                for frame in frame_index["frames"]
            ]
            self.assertIn(("conn-0001-out-0001.bin", 0, 0), frame_names)
            self.assertIn(("conn-0001-out-0001.bin", 1, 18), frame_names)
            self.assertIn(("proxy-4007/conn-0001-out-0002.bin", 0, 0), frame_names)

            out_family = next(
                family
                for family in frame_index["families"]
                if family["direction"] == "out" and family["size"] == 18
            )
            self.assertEqual(out_family["count"], 2)
            self.assertEqual(out_family["prefix_hex"], _make_frame(b"OBJECT alpha 100")[:8].hex())
            self.assertIn("OBJECT alpha 100", out_family["ascii_fragments"])
            self.assertIn("OBJECT bravo 200", out_family["ascii_fragments"])
            self.assertIn("conn-0001-out-0001.bin#0@0", out_family["example_frames"])

            summary = (target / "summary.md").read_text(encoding="utf-8")
            self.assertIn("chunk_count=3", summary)
            self.assertIn("frame_count=4", summary)
            self.assertIn("family_count=3", summary)
            self.assertIn(out_family["prefix_hex"], summary)


if __name__ == "__main__":
    unittest.main()

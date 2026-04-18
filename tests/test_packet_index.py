from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from emulator.tools.packet_index import extract_ascii_fragments, write_packet_index


class PacketIndexTests(unittest.TestCase):
    def test_extract_ascii_fragments_ignores_short_noise(self) -> None:
        payload = b"\x00abc\x00HELLO WORLD\x00xy\x00ROOM 12 44\x00"

        fragments = extract_ascii_fragments(payload)

        self.assertEqual(fragments, ["HELLO WORLD", "ROOM 12 44"])

    def test_write_packet_index_groups_packets_into_families(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source = tmp_path / "source"
            target = tmp_path / "target"
            (source / "packets").mkdir(parents=True)
            (source / "packets" / "conn-0001-out-0001.bin").write_bytes(
                b"\xAA\xBB\xCC\xDDHEADalpha 100\x00"
            )
            (source / "packets" / "conn-0001-out-0002.bin").write_bytes(
                b"\xAA\xBB\xCC\xDDHEADbetaa 200\x00"
            )
            (source / "packets" / "proxy-4007").mkdir(parents=True)
            (source / "packets" / "proxy-4007" / "conn-0001-in-0001.bin").write_bytes(
                b"\x01\x02\x03\x04PING world-state\x00"
            )

            write_packet_index(source, target)

            packet_index = json.loads((target / "packet-index.json").read_text(encoding="utf-8"))
            self.assertEqual(packet_index["packet_count"], 3)
            self.assertEqual(packet_index["family_count"], 2)

            packet_names = [packet["name"] for packet in packet_index["packets"]]
            self.assertEqual(
                packet_names,
                [
                    "conn-0001-out-0001.bin",
                    "conn-0001-out-0002.bin",
                    "proxy-4007/conn-0001-in-0001.bin",
                ],
            )

            out_family = next(
                family
                for family in packet_index["families"]
                if family["direction"] == "out" and family["size"] == 18
            )
            self.assertEqual(out_family["count"], 2)
            self.assertEqual(out_family["prefix_hex"], "aabbccdd48454144")
            self.assertIn("HEADalpha 100", out_family["ascii_fragments"])
            self.assertIn("HEADbetaa 200", out_family["ascii_fragments"])

            summary = (target / "summary.md").read_text(encoding="utf-8")
            self.assertIn("packet_count=3", summary)
            self.assertIn("family_count=2", summary)
            self.assertIn("aabbccdd48454144", summary)


if __name__ == "__main__":
    unittest.main()

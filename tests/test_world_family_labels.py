from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from emulator.tools.world_family_labels import label_family, write_world_family_labels


class WorldFamilyLabelTests(unittest.TestCase):
    def test_label_family_recognizes_indexed_coordinate_pairs(self) -> None:
        family = {
            "direction": "out",
            "size": 31,
            "prefix_hex": "1d00f67be12c7d6a",
            "count": 209,
            "ascii_fragments": [
                "9: 35263 35265",
                "9: 35261 35265",
                "9: 35259 35265",
            ],
            "example_frames": ["conn-0001-out-0001.bin#0@0"],
        }

        labeled = label_family(family)

        self.assertIn("likely_indexed_coordinate_pair_ascii", labeled["labels"])
        self.assertEqual(labeled["confidence"], "high")
        self.assertEqual(labeled["numeric_shapes"], [3])

    def test_label_family_recognizes_coordinate_quads(self) -> None:
        family = {
            "direction": "out",
            "size": 31,
            "prefix_hex": "1d004d23c18ad027",
            "count": 47,
            "ascii_fragments": [
                "930 5708 0 0",
                "927 5648 0 0",
                "927 5653 0 0",
            ],
            "example_frames": ["conn-0001-out-0001.bin#1@31"],
        }

        labeled = label_family(family)

        self.assertIn("likely_coordinate_quad_ascii", labeled["labels"])
        self.assertEqual(labeled["confidence"], "high")
        self.assertEqual(labeled["numeric_shapes"], [4])

    def test_label_family_recognizes_named_text_payloads(self) -> None:
        family = {
            "direction": "out",
            "size": 92,
            "prefix_hex": "5a0077ea8422d608",
            "count": 98,
            "ascii_fragments": [
                "3 demigod",
                "Y1C^",
            ],
            "example_frames": ["conn-0001-out-0008.bin#47@1659"],
        }

        labeled = label_family(family)

        self.assertIn("likely_named_text_payload", labeled["labels"])
        self.assertIn("likely_text_bearing_payload", labeled["labels"])

    def test_label_family_recognizes_small_binary_keepalives(self) -> None:
        family = {
            "direction": "in",
            "size": 11,
            "prefix_hex": "0900000000000000",
            "count": 51,
            "ascii_fragments": [],
            "example_frames": ["conn-0001-in-0003.bin#0@0"],
        }

        labeled = label_family(family)

        self.assertEqual(labeled["labels"], ["likely_keepalive_or_ack"])
        self.assertEqual(labeled["confidence"], "medium")

    def test_label_family_recognizes_tagged_numeric_tokens(self) -> None:
        family = {
            "direction": "out",
            "size": 40,
            "prefix_hex": "260095c289e0d06b",
            "count": 704,
            "ascii_fragments": [
                "02460",
                "Aw/#02460",
                "p02460",
            ],
            "example_frames": ["conn-0001-out-0027.bin#0@0"],
        }

        labeled = label_family(family)

        self.assertEqual(labeled["labels"], ["likely_tagged_numeric_token"])
        self.assertEqual(labeled["confidence"], "medium")

    def test_label_family_keeps_plain_digit_families_as_numeric_ids(self) -> None:
        family = {
            "direction": "out",
            "size": 23,
            "prefix_hex": "1500a298040427e0",
            "count": 125,
            "ascii_fragments": [
                "3188",
                "6005",
                "8506",
            ],
            "example_frames": ["conn-0001-out-0015.bin#0@0"],
        }

        labeled = label_family(family)

        self.assertEqual(labeled["labels"], ["likely_numeric_id_ascii"])
        self.assertEqual(labeled["confidence"], "medium")

    def test_write_world_family_labels_summarizes_ranked_families(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source = tmp_path / "source"
            frame_index_dir = source / "frame-index"
            target = tmp_path / "target"
            frame_index_dir.mkdir(parents=True)
            (frame_index_dir / "frame-index.json").write_text(
                json.dumps(
                    {
                        "source": str(source),
                        "chunk_count": 10,
                        "frame_count": 20,
                        "family_count": 3,
                        "frames": [],
                        "families": [
                            {
                                "direction": "out",
                                "size": 31,
                                "prefix_hex": "1d00f67be12c7d6a",
                                "count": 5,
                                "ascii_fragments": ["9: 35263 35265"],
                                "example_frames": ["conn-0001-out-0001.bin#0@0"],
                            },
                            {
                                "direction": "out",
                                "size": 31,
                                "prefix_hex": "1d004d23c18ad027",
                                "count": 4,
                                "ascii_fragments": ["930 5708 0 0"],
                                "example_frames": ["conn-0001-out-0002.bin#0@0"],
                            },
                            {
                                "direction": "in",
                                "size": 11,
                                "prefix_hex": "0900000000000000",
                                "count": 30,
                                "ascii_fragments": [],
                                "example_frames": ["conn-0001-in-0001.bin#0@0"],
                            },
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            write_world_family_labels(source, target)

            labels_payload = json.loads((target / "world-family-labels.json").read_text(encoding="utf-8"))
            self.assertEqual(labels_payload["family_count"], 3)
            self.assertEqual(labels_payload["labeled_family_count"], 3)
            self.assertEqual(labels_payload["families"][0]["labels"][0], "likely_indexed_coordinate_pair_ascii")

            summary = (target / "summary.md").read_text(encoding="utf-8")
            self.assertIn("likely_coordinate_quad_ascii", summary)
            self.assertIn("likely_keepalive_or_ack", summary)


if __name__ == "__main__":
    unittest.main()

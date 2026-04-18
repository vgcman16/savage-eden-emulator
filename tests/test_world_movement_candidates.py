from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from emulator.tools.world_movement_candidates import (
    classify_movement_profile,
    extract_coordinate_point,
    summarize_coordinate_family,
    write_world_movement_candidates,
)


class WorldMovementCandidateTests(unittest.TestCase):
    def test_extract_coordinate_point_handles_supported_labels(self) -> None:
        indexed = {
            "ascii_fragments": ["9: 35263 35265"],
        }
        pair = {
            "ascii_fragments": [" 67860 67860"],
        }
        quad = {
            "ascii_fragments": ["930 5708 0 0"],
        }

        self.assertEqual(
            extract_coordinate_point(indexed, ["likely_indexed_coordinate_pair_ascii"]),
            (35263, 35265),
        )
        self.assertEqual(
            extract_coordinate_point(pair, ["likely_coordinate_pair_ascii"]),
            (67860, 67860),
        )
        self.assertEqual(
            extract_coordinate_point(quad, ["likely_coordinate_quad_ascii"]),
            (930, 5708),
        )

    def test_classify_movement_profile_distinguishes_static_and_moving_families(self) -> None:
        self.assertEqual(
            classify_movement_profile(
                {
                    "unique_position_count": 1,
                    "max_step_manhattan": 0,
                    "avg_step_manhattan": 0.0,
                }
            ),
            "static_anchor_candidate",
        )
        self.assertEqual(
            classify_movement_profile(
                {
                    "unique_position_count": 5,
                    "max_step_manhattan": 4,
                    "avg_step_manhattan": 2.0,
                }
            ),
            "fine_movement_candidate",
        )
        self.assertEqual(
            classify_movement_profile(
                {
                    "unique_position_count": 20,
                    "max_step_manhattan": 140,
                    "avg_step_manhattan": 68.0,
                }
            ),
            "entity_position_candidate",
        )
        self.assertEqual(
            classify_movement_profile(
                {
                    "unique_position_count": 120,
                    "max_step_manhattan": 5000,
                    "avg_step_manhattan": 1600.0,
                }
            ),
            "large_range_coordinate_stream",
        )

    def test_summarize_coordinate_family_reports_range_steps_and_neighbors(self) -> None:
        frames = [
            {"prefix_hex": "keepalive", "ascii_fragments": []},
            {"prefix_hex": "coord-a", "ascii_fragments": ["9: 35265 35265"]},
            {"prefix_hex": "other", "ascii_fragments": ["state"]},
            {"prefix_hex": "coord-a", "ascii_fragments": ["9: 35263 35265"]},
            {"prefix_hex": "keepalive", "ascii_fragments": []},
            {"prefix_hex": "coord-a", "ascii_fragments": ["9: 35261 35265"]},
        ]
        labels_by_prefix = {
            "coord-a": ["likely_indexed_coordinate_pair_ascii"],
            "keepalive": ["likely_keepalive_or_ack"],
            "other": ["unclassified"],
        }

        summary = summarize_coordinate_family(
            prefix_hex="coord-a",
            family_labels=labels_by_prefix["coord-a"],
            frames=frames,
            labels_by_prefix=labels_by_prefix,
        )

        self.assertEqual(summary["point_count"], 3)
        self.assertEqual(summary["unique_position_count"], 3)
        self.assertEqual(summary["x_span"], 4)
        self.assertEqual(summary["y_span"], 0)
        self.assertEqual(summary["dominant_axis"], "x")
        self.assertEqual(summary["movement_profile"], "fine_movement_candidate")
        self.assertEqual(summary["avg_step_manhattan"], 2.0)
        self.assertEqual(summary["neighbor_prefixes"][0]["prefix_hex"], "keepalive")

    def test_write_world_movement_candidates_generates_ranked_report(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source = tmp_path / "source"
            frame_index_dir = source / "frame-index"
            labels_dir = source / "world-family-labels"
            target = tmp_path / "target"
            frame_index_dir.mkdir(parents=True)
            labels_dir.mkdir(parents=True)

            frames = [
                {"prefix_hex": "coord-a", "ascii_fragments": ["9: 35265 35265"]},
                {"prefix_hex": "coord-a", "ascii_fragments": ["9: 35263 35265"]},
                {"prefix_hex": "static-b", "ascii_fragments": [" 35140 35140"]},
                {"prefix_hex": "static-b", "ascii_fragments": [" 35140 35140"]},
                {"prefix_hex": "coord-c", "ascii_fragments": ["930 5708 0 0"]},
                {"prefix_hex": "coord-c", "ascii_fragments": ["927 5648 0 0"]},
            ]
            (frame_index_dir / "frame-index.json").write_text(
                json.dumps(
                    {
                        "source": str(source),
                        "frames": frames,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            (labels_dir / "world-family-labels.json").write_text(
                json.dumps(
                    {
                        "source": str(source),
                        "families": [
                            {
                                "prefix_hex": "coord-a",
                                "labels": ["likely_indexed_coordinate_pair_ascii"],
                                "count": 2,
                            },
                            {
                                "prefix_hex": "static-b",
                                "labels": ["likely_coordinate_pair_ascii"],
                                "count": 2,
                            },
                            {
                                "prefix_hex": "coord-c",
                                "labels": ["likely_coordinate_quad_ascii"],
                                "count": 2,
                            },
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            write_world_movement_candidates(source, target)

            payload = json.loads((target / "world-movement-candidates.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["candidate_count"], 3)
            profiles = {item["prefix_hex"]: item["movement_profile"] for item in payload["families"]}
            self.assertEqual(profiles["coord-a"], "fine_movement_candidate")
            self.assertEqual(profiles["static-b"], "static_anchor_candidate")
            self.assertEqual(profiles["coord-c"], "entity_position_candidate")

            summary = (target / "summary.md").read_text(encoding="utf-8")
            self.assertIn("fine_movement_candidate", summary)
            self.assertIn("static_anchor_candidate", summary)


if __name__ == "__main__":
    unittest.main()

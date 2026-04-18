from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from emulator.tools.world_movement_compare import (
    compare_candidate_families,
    write_world_movement_comparison,
)


class WorldMovementCompareTests(unittest.TestCase):
    def test_compare_candidate_families_ranks_movement_gain(self) -> None:
        baseline = [
            {
                "prefix_hex": "coord-a",
                "labels": ["likely_indexed_coordinate_pair_ascii"],
                "movement_profile": "static_anchor_candidate",
                "point_count": 10,
                "unique_position_count": 1,
                "x_span": 0,
                "y_span": 0,
                "avg_step_manhattan": 0.0,
            },
            {
                "prefix_hex": "coord-b",
                "labels": ["likely_coordinate_quad_ascii"],
                "movement_profile": "entity_position_candidate",
                "point_count": 10,
                "unique_position_count": 10,
                "x_span": 200,
                "y_span": 180,
                "avg_step_manhattan": 60.0,
            },
        ]
        candidate = [
            {
                "prefix_hex": "coord-a",
                "labels": ["likely_indexed_coordinate_pair_ascii"],
                "movement_profile": "fine_movement_candidate",
                "point_count": 20,
                "unique_position_count": 11,
                "x_span": 20,
                "y_span": 0,
                "avg_step_manhattan": 2.9,
            },
            {
                "prefix_hex": "coord-b",
                "labels": ["likely_coordinate_quad_ascii"],
                "movement_profile": "entity_position_candidate",
                "point_count": 12,
                "unique_position_count": 12,
                "x_span": 220,
                "y_span": 185,
                "avg_step_manhattan": 63.0,
            },
        ]

        comparisons = compare_candidate_families(
            baseline,
            candidate,
            baseline_label="idle",
            candidate_label="walk-east",
        )

        self.assertEqual(comparisons[0]["prefix_hex"], "coord-a")
        self.assertEqual(comparisons[0]["profile_transition"], "static_anchor_candidate -> fine_movement_candidate")
        self.assertGreater(comparisons[0]["movement_gain_score"], comparisons[1]["movement_gain_score"])
        self.assertEqual(comparisons[0]["delta_unique_positions"], 10)

    def test_write_world_movement_comparison_generates_summary(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            baseline_dir = tmp_path / "idle"
            candidate_dir = tmp_path / "walk-east"
            target = tmp_path / "comparison"
            (baseline_dir / "world-movement-candidates").mkdir(parents=True)
            (candidate_dir / "world-movement-candidates").mkdir(parents=True)

            (baseline_dir / "world-movement-candidates" / "world-movement-candidates.json").write_text(
                json.dumps(
                    {
                        "source": str(baseline_dir),
                        "candidate_count": 1,
                        "families": [
                            {
                                "prefix_hex": "coord-a",
                                "labels": ["likely_indexed_coordinate_pair_ascii"],
                                "movement_profile": "static_anchor_candidate",
                                "point_count": 10,
                                "unique_position_count": 1,
                                "x_span": 0,
                                "y_span": 0,
                                "avg_step_manhattan": 0.0,
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            (candidate_dir / "world-movement-candidates" / "world-movement-candidates.json").write_text(
                json.dumps(
                    {
                        "source": str(candidate_dir),
                        "candidate_count": 1,
                        "families": [
                            {
                                "prefix_hex": "coord-a",
                                "labels": ["likely_indexed_coordinate_pair_ascii"],
                                "movement_profile": "fine_movement_candidate",
                                "point_count": 20,
                                "unique_position_count": 11,
                                "x_span": 20,
                                "y_span": 0,
                                "avg_step_manhattan": 2.9,
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            write_world_movement_comparison(
                baseline_dir,
                candidate_dir,
                target,
                baseline_label="idle",
                candidate_label="walk-east",
            )

            payload = json.loads((target / "world-movement-comparison.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["comparison_count"], 1)
            self.assertEqual(payload["families"][0]["profile_transition"], "static_anchor_candidate -> fine_movement_candidate")
            self.assertEqual(payload["families"][0]["delta_x_span"], 20)

            summary = (target / "summary.md").read_text(encoding="utf-8")
            self.assertIn("walk-east", summary)
            self.assertIn("fine_movement_candidate", summary)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from emulator.tools.world_family_trace import (
    compare_family_traces,
    extract_family_trace,
    write_world_family_trace_report,
)


class WorldFamilyTraceTests(unittest.TestCase):
    def test_extract_family_trace_returns_ordered_points_and_deltas(self) -> None:
        run_dir = Path("run")
        frame_index = {
            "source": str(run_dir),
            "frames": [
                {"prefix_hex": "other", "ascii_fragments": []},
                {"prefix_hex": "target", "ascii_fragments": ["9: 35265 35265"]},
                {"prefix_hex": "target", "ascii_fragments": ["9: 35263 35265"]},
                {"prefix_hex": "target", "ascii_fragments": ["9: 35261 35265"]},
            ],
        }
        labels = {
            "target": ["likely_indexed_coordinate_pair_ascii"],
        }

        trace = extract_family_trace(
            frame_index_payload=frame_index,
            labels_by_prefix=labels,
            prefix_hex="target",
        )

        self.assertEqual(trace["point_count"], 3)
        self.assertEqual(trace["points"], [[35265, 35265], [35263, 35265], [35261, 35265]])
        self.assertEqual(trace["deltas"], [[-2, 0], [-2, 0]])
        self.assertEqual(trace["x_span"], 4)
        self.assertEqual(trace["y_span"], 0)

    def test_compare_family_traces_reports_run_to_run_changes(self) -> None:
        traces = {
            "idle": {
                "point_count": 1,
                "points": [[35265, 35265]],
                "deltas": [],
                "x_span": 0,
                "y_span": 0,
            },
            "walk-east": {
                "point_count": 3,
                "points": [[35265, 35265], [35263, 35265], [35261, 35265]],
                "deltas": [[-2, 0], [-2, 0]],
                "x_span": 4,
                "y_span": 0,
            },
            "walk-north": {
                "point_count": 3,
                "points": [[35265, 35265], [35263, 35265], [35261, 35265]],
                "deltas": [[-2, 0], [-2, 0]],
                "x_span": 4,
                "y_span": 0,
            },
        }

        comparison = compare_family_traces(traces)

        self.assertIn("idle -> walk-east", comparison["comparisons"])
        self.assertEqual(comparison["comparisons"]["idle -> walk-east"]["delta_point_count"], 2)
        self.assertEqual(comparison["comparisons"]["walk-east -> walk-north"]["delta_x_span"], 0)
        self.assertEqual(comparison["consistent_axis"], "x")

    def test_write_world_family_trace_report_generates_summary(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            idle_dir = tmp_path / "idle"
            east_dir = tmp_path / "east"
            target = tmp_path / "report"
            for run_dir, fragments in (
                (idle_dir, ["9: 35265 35265"]),
                (east_dir, ["9: 35265 35265", "9: 35263 35265", "9: 35261 35265"]),
            ):
                (run_dir / "frame-index").mkdir(parents=True)
                (run_dir / "world-family-labels").mkdir(parents=True)
                (run_dir / "frame-index" / "frame-index.json").write_text(
                    json.dumps(
                        {
                            "source": str(run_dir),
                            "frames": [
                                {"prefix_hex": "target", "ascii_fragments": [fragment]}
                                for fragment in fragments
                            ],
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                (run_dir / "world-family-labels" / "world-family-labels.json").write_text(
                    json.dumps(
                        {
                            "families": [
                                {
                                    "prefix_hex": "target",
                                    "labels": ["likely_indexed_coordinate_pair_ascii"],
                                }
                            ]
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )

            write_world_family_trace_report(
                {"idle": idle_dir, "walk-east": east_dir},
                prefix_hex="target",
                target=target,
            )

            payload = json.loads((target / "world-family-trace.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["prefix_hex"], "target")
            self.assertEqual(payload["runs"]["idle"]["point_count"], 1)
            self.assertEqual(payload["runs"]["walk-east"]["x_span"], 4)

            summary = (target / "summary.md").read_text(encoding="utf-8")
            self.assertIn("walk-east", summary)
            self.assertIn("35263", summary)


if __name__ == "__main__":
    unittest.main()

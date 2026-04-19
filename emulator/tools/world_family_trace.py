from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

from emulator.tools.world_movement_candidates import extract_coordinate_point


def _resolve_frame_index_path(source: Path) -> Path:
    direct = source / "frame-index.json"
    if direct.exists():
        return direct

    nested = source / "frame-index" / "frame-index.json"
    if nested.exists():
        return nested

    raise FileNotFoundError(f"could not find frame-index.json under {source}")


def _resolve_world_label_path(source: Path) -> Path:
    direct = source / "world-family-labels.json"
    if direct.exists():
        return direct

    nested = source / "world-family-labels" / "world-family-labels.json"
    if nested.exists():
        return nested

    raise FileNotFoundError(f"could not find world-family-labels.json under {source}")


def extract_family_trace(
    *,
    frame_index_payload: dict[str, object],
    labels_by_prefix: dict[str, list[str]],
    prefix_hex: str,
) -> dict[str, object]:
    frames = frame_index_payload.get("frames", [])
    assert isinstance(frames, list)

    family_labels = labels_by_prefix.get(prefix_hex, [])
    points: list[list[int]] = []
    frame_indexes: list[int] = []

    for index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            continue
        if str(frame.get("prefix_hex")) != prefix_hex:
            continue
        point = extract_coordinate_point(frame, family_labels)
        if point is None:
            continue
        points.append([point[0], point[1]])
        frame_indexes.append(index)

    deltas = [
        [points[i + 1][0] - points[i][0], points[i + 1][1] - points[i][1]]
        for i in range(len(points) - 1)
    ]

    x_values = [point[0] for point in points] or [0]
    y_values = [point[1] for point in points] or [0]

    return {
        "labels": family_labels,
        "point_count": len(points),
        "points": points,
        "deltas": deltas,
        "x_span": max(x_values) - min(x_values),
        "y_span": max(y_values) - min(y_values),
        "frame_indexes": frame_indexes,
    }


def compare_family_traces(traces: dict[str, dict[str, object]]) -> dict[str, object]:
    comparison_rows: dict[str, dict[str, object]] = {}
    dominant_axes: set[str] = set()

    for left, right in combinations(sorted(traces), 2):
        left_trace = traces[left]
        right_trace = traces[right]
        left_x_span = int(left_trace["x_span"])
        right_x_span = int(right_trace["x_span"])
        left_y_span = int(left_trace["y_span"])
        right_y_span = int(right_trace["y_span"])

        dominant_axis = "static"
        if right_x_span > 0 or right_y_span > 0:
            if right_x_span > right_y_span:
                dominant_axis = "x"
            elif right_y_span > right_x_span:
                dominant_axis = "y"
            else:
                dominant_axis = "mixed"
        dominant_axes.add(dominant_axis)

        comparison_rows[f"{left} -> {right}"] = {
            "delta_point_count": int(right_trace["point_count"]) - int(left_trace["point_count"]),
            "delta_x_span": right_x_span - left_x_span,
            "delta_y_span": right_y_span - left_y_span,
            "left_last_point": left_trace["points"][-1] if left_trace["points"] else None,
            "right_last_point": right_trace["points"][-1] if right_trace["points"] else None,
            "dominant_axis": dominant_axis,
        }

    if len(dominant_axes) == 1:
        consistent_axis = next(iter(dominant_axes))
    else:
        consistent_axis = "mixed"

    return {
        "comparisons": comparison_rows,
        "consistent_axis": consistent_axis,
    }


def write_world_family_trace_report(
    runs: dict[str, Path],
    *,
    prefix_hex: str,
    target: Path,
) -> None:
    traces: dict[str, dict[str, object]] = {}

    for label, run_path in runs.items():
        frame_index_payload = json.loads(_resolve_frame_index_path(run_path).read_text(encoding="utf-8"))
        world_label_payload = json.loads(_resolve_world_label_path(run_path).read_text(encoding="utf-8"))
        families = world_label_payload.get("families", [])
        assert isinstance(families, list)
        labels_by_prefix = {
            str(family["prefix_hex"]): [str(label) for label in family.get("labels", [])]
            for family in families
            if isinstance(family, dict) and "prefix_hex" in family
        }

        traces[label] = extract_family_trace(
            frame_index_payload=frame_index_payload,
            labels_by_prefix=labels_by_prefix,
            prefix_hex=prefix_hex,
        )

    comparison = compare_family_traces(traces)
    payload = {
        "prefix_hex": prefix_hex,
        "runs": traces,
        **comparison,
    }

    target.mkdir(parents=True, exist_ok=True)
    (target / "world-family-trace.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    summary_lines = [
        "# World Family Trace",
        "",
        f"prefix_hex={prefix_hex}",
        f"consistent_axis={comparison['consistent_axis']}",
        "",
        "## Runs",
        "",
    ]

    for label, trace in traces.items():
        point_preview = ", ".join(str(point) for point in trace["points"][:8]) or "(none)"
        delta_preview = ", ".join(str(delta) for delta in trace["deltas"][:8]) or "(none)"
        summary_lines.append(
            f"- `{label}` points `{trace['point_count']}` x-span `{trace['x_span']}` y-span `{trace['y_span']}` points: {point_preview} deltas: {delta_preview}"
        )

    summary_lines.extend(
        [
            "",
            "## Comparisons",
            "",
        ]
    )
    for label, row in comparison["comparisons"].items():
        summary_lines.append(
            f"- `{label}` dominant-axis `{row['dominant_axis']}` point-delta `{row['delta_point_count']}` x-span-delta `{row['delta_x_span']}` y-span-delta `{row['delta_y_span']}` last-points `{row['left_last_point']} -> {row['right_last_point']}`"
        )

    (target / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

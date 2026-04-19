from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


_NUMBER_RE = re.compile(r"-?\d+")
_COORDINATE_LABELS = {
    "likely_coordinate_pair_ascii",
    "likely_indexed_coordinate_pair_ascii",
    "likely_coordinate_quad_ascii",
}


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


def extract_coordinate_point(frame: dict[str, object], family_labels: list[str]) -> tuple[int, int] | None:
    fragments = frame.get("ascii_fragments", [])
    if not isinstance(fragments, list):
        return None

    numbers = [int(token) for token in _NUMBER_RE.findall(" | ".join(str(fragment) for fragment in fragments))]
    if "likely_indexed_coordinate_pair_ascii" in family_labels and len(numbers) >= 3:
        return numbers[1], numbers[2]
    if "likely_coordinate_pair_ascii" in family_labels and len(numbers) >= 2:
        return numbers[0], numbers[1]
    if "likely_coordinate_quad_ascii" in family_labels and len(numbers) >= 2:
        return numbers[0], numbers[1]
    return None


def classify_movement_profile(summary: dict[str, object]) -> str:
    unique_position_count = int(summary["unique_position_count"])
    max_step = int(summary["max_step_manhattan"])
    avg_step = float(summary["avg_step_manhattan"])

    if unique_position_count <= 1:
        return "static_anchor_candidate"
    if max_step <= 25 and avg_step <= 10.0:
        return "fine_movement_candidate"
    if avg_step <= 200.0 and unique_position_count >= 2:
        return "entity_position_candidate"
    return "large_range_coordinate_stream"


def summarize_coordinate_family(
    *,
    prefix_hex: str,
    family_labels: list[str],
    frames: list[dict[str, object]],
    labels_by_prefix: dict[str, list[str]],
) -> dict[str, object]:
    positions: list[tuple[int, int]] = []
    occurrence_indexes: list[int] = []
    neighbor_counts: Counter[str] = Counter()

    for index, frame in enumerate(frames):
        if frame.get("prefix_hex") != prefix_hex:
            continue

        point = extract_coordinate_point(frame, family_labels)
        if point is None:
            continue

        positions.append(point)
        occurrence_indexes.append(index)

        for neighbor_index in (index - 1, index + 1):
            if 0 <= neighbor_index < len(frames):
                neighbor_prefix = str(frames[neighbor_index].get("prefix_hex", ""))
                if neighbor_prefix:
                    neighbor_counts[neighbor_prefix] += 1

    if not positions:
        raise ValueError(f"no coordinate points found for family {prefix_hex}")

    x_values = [point[0] for point in positions]
    y_values = [point[1] for point in positions]
    steps = [
        abs(positions[index + 1][0] - positions[index][0]) + abs(positions[index + 1][1] - positions[index][1])
        for index in range(len(positions) - 1)
    ]

    x_span = max(x_values) - min(x_values)
    y_span = max(y_values) - min(y_values)

    dominant_axis = "static"
    if x_span > 0 or y_span > 0:
        if x_span > y_span * 2:
            dominant_axis = "x"
        elif y_span > x_span * 2:
            dominant_axis = "y"
        else:
            dominant_axis = "mixed"

    summary = {
        "prefix_hex": prefix_hex,
        "labels": family_labels,
        "point_count": len(positions),
        "unique_position_count": len(set(positions)),
        "x_min": min(x_values),
        "x_max": max(x_values),
        "y_min": min(y_values),
        "y_max": max(y_values),
        "x_span": x_span,
        "y_span": y_span,
        "avg_step_manhattan": round(sum(steps) / len(steps), 2) if steps else 0.0,
        "min_step_manhattan": min(steps) if steps else 0,
        "max_step_manhattan": max(steps) if steps else 0,
        "dominant_axis": dominant_axis,
        "sample_positions": [list(point) for point in positions[:10]],
        "occurrence_indexes": occurrence_indexes[:10],
        "neighbor_prefixes": [
            {
                "prefix_hex": neighbor_prefix,
                "count": count,
                "labels": labels_by_prefix.get(neighbor_prefix, []),
            }
            for neighbor_prefix, count in neighbor_counts.most_common(6)
        ],
    }
    summary["movement_profile"] = classify_movement_profile(summary)
    return summary


def write_world_movement_candidates(source: Path, target: Path) -> None:
    frame_index_path = _resolve_frame_index_path(source)
    world_label_path = _resolve_world_label_path(source)

    frame_index_payload = json.loads(frame_index_path.read_text(encoding="utf-8"))
    world_label_payload = json.loads(world_label_path.read_text(encoding="utf-8"))

    frames = frame_index_payload.get("frames", [])
    families = world_label_payload.get("families", [])
    assert isinstance(frames, list)
    assert isinstance(families, list)

    labels_by_prefix: dict[str, list[str]] = {
        str(family["prefix_hex"]): [str(label) for label in family.get("labels", [])]
        for family in families
        if isinstance(family, dict) and "prefix_hex" in family
    }
    counts_by_prefix: dict[str, int] = {
        str(family["prefix_hex"]): int(family.get("count", 0))
        for family in families
        if isinstance(family, dict) and "prefix_hex" in family
    }

    candidates: list[dict[str, object]] = []
    for prefix_hex, family_labels in labels_by_prefix.items():
        if not any(label in _COORDINATE_LABELS for label in family_labels):
            continue

        try:
            summary = summarize_coordinate_family(
                prefix_hex=prefix_hex,
                family_labels=family_labels,
                frames=frames,
                labels_by_prefix=labels_by_prefix,
            )
        except ValueError:
            continue

        summary["frame_count"] = counts_by_prefix.get(prefix_hex, summary["point_count"])
        candidates.append(summary)

    candidates.sort(
        key=lambda candidate: (
            {
                "fine_movement_candidate": 0,
                "entity_position_candidate": 1,
                "static_anchor_candidate": 2,
                "large_range_coordinate_stream": 3,
            }.get(str(candidate["movement_profile"]), 4),
            -int(candidate["point_count"]),
            str(candidate["prefix_hex"]),
        )
    )

    payload = {
        "source": frame_index_payload.get("source", str(source)),
        "candidate_count": len(candidates),
        "families": candidates,
    }

    target.mkdir(parents=True, exist_ok=True)
    (target / "world-movement-candidates.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    summary_lines = [
        "# World Movement Candidates",
        "",
        f"source={payload['source']}",
        f"candidate_count={payload['candidate_count']}",
        "",
        "## Families",
        "",
    ]
    for candidate in candidates:
        neighbor_preview = ", ".join(
            f"`{neighbor['prefix_hex']}` x{neighbor['count']}"
            for neighbor in candidate["neighbor_prefixes"][:3]
        ) or "(none)"
        summary_lines.append(
            f"- `{candidate['movement_profile']}` prefix `{candidate['prefix_hex']}` labels `{', '.join(candidate['labels'])}` points `{candidate['point_count']}` unique `{candidate['unique_position_count']}` axis `{candidate['dominant_axis']}` x-span `{candidate['x_span']}` y-span `{candidate['y_span']}` avg-step `{candidate['avg_step_manhattan']}` neighbors: {neighbor_preview}"
        )

    (target / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

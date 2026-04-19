from __future__ import annotations

import json
from pathlib import Path


_PROFILE_RANK = {
    "static_anchor_candidate": 0,
    "large_range_coordinate_stream": 1,
    "entity_position_candidate": 2,
    "fine_movement_candidate": 3,
}


def _resolve_candidate_path(source: Path) -> Path:
    if source.is_file():
        return source

    direct = source / "world-movement-candidates.json"
    if direct.exists():
        return direct

    nested = source / "world-movement-candidates" / "world-movement-candidates.json"
    if nested.exists():
        return nested

    raise FileNotFoundError(f"could not find world-movement-candidates.json under {source}")


def compare_candidate_families(
    baseline_families: list[dict[str, object]],
    candidate_families: list[dict[str, object]],
    *,
    baseline_label: str,
    candidate_label: str,
) -> list[dict[str, object]]:
    baseline_by_prefix = {
        str(family["prefix_hex"]): family
        for family in baseline_families
        if isinstance(family, dict) and "prefix_hex" in family
    }
    candidate_by_prefix = {
        str(family["prefix_hex"]): family
        for family in candidate_families
        if isinstance(family, dict) and "prefix_hex" in family
    }

    comparisons: list[dict[str, object]] = []
    for prefix_hex in sorted(set(baseline_by_prefix) | set(candidate_by_prefix)):
        baseline = baseline_by_prefix.get(prefix_hex, {})
        candidate = candidate_by_prefix.get(prefix_hex, {})

        baseline_profile = str(baseline.get("movement_profile", "missing"))
        candidate_profile = str(candidate.get("movement_profile", "missing"))
        baseline_unique = int(baseline.get("unique_position_count", 0))
        candidate_unique = int(candidate.get("unique_position_count", 0))
        baseline_x_span = int(baseline.get("x_span", 0))
        candidate_x_span = int(candidate.get("x_span", 0))
        baseline_y_span = int(baseline.get("y_span", 0))
        candidate_y_span = int(candidate.get("y_span", 0))
        baseline_avg_step = float(baseline.get("avg_step_manhattan", 0.0))
        candidate_avg_step = float(candidate.get("avg_step_manhattan", 0.0))

        delta_unique = candidate_unique - baseline_unique
        delta_x_span = candidate_x_span - baseline_x_span
        delta_y_span = candidate_y_span - baseline_y_span
        delta_avg_step = round(candidate_avg_step - baseline_avg_step, 2)
        profile_gain = _PROFILE_RANK.get(candidate_profile, -1) - _PROFILE_RANK.get(baseline_profile, -1)

        movement_gain_score = (
            profile_gain * 100000
            + delta_unique * 100
            + max(0, delta_x_span)
            + max(0, delta_y_span)
            + int(round(max(0.0, delta_avg_step) * 10))
        )

        comparisons.append(
            {
                "prefix_hex": prefix_hex,
                "labels": candidate.get("labels") or baseline.get("labels") or [],
                "baseline_label": baseline_label,
                "candidate_label": candidate_label,
                "baseline_profile": baseline_profile,
                "candidate_profile": candidate_profile,
                "profile_transition": f"{baseline_profile} -> {candidate_profile}",
                "baseline_point_count": int(baseline.get("point_count", 0)),
                "candidate_point_count": int(candidate.get("point_count", 0)),
                "baseline_unique_positions": baseline_unique,
                "candidate_unique_positions": candidate_unique,
                "delta_unique_positions": delta_unique,
                "baseline_x_span": baseline_x_span,
                "candidate_x_span": candidate_x_span,
                "delta_x_span": delta_x_span,
                "baseline_y_span": baseline_y_span,
                "candidate_y_span": candidate_y_span,
                "delta_y_span": delta_y_span,
                "baseline_avg_step_manhattan": baseline_avg_step,
                "candidate_avg_step_manhattan": candidate_avg_step,
                "delta_avg_step_manhattan": delta_avg_step,
                "movement_gain_score": movement_gain_score,
            }
        )

    comparisons.sort(
        key=lambda item: (
            -int(item["movement_gain_score"]),
            -int(item["delta_unique_positions"]),
            str(item["prefix_hex"]),
        )
    )
    return comparisons


def write_world_movement_comparison(
    baseline_source: Path,
    candidate_source: Path,
    target: Path,
    *,
    baseline_label: str,
    candidate_label: str,
) -> None:
    baseline_path = _resolve_candidate_path(baseline_source)
    candidate_path = _resolve_candidate_path(candidate_source)

    baseline_payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate_payload = json.loads(candidate_path.read_text(encoding="utf-8"))

    baseline_families = baseline_payload.get("families", [])
    candidate_families = candidate_payload.get("families", [])
    assert isinstance(baseline_families, list)
    assert isinstance(candidate_families, list)

    comparisons = compare_candidate_families(
        baseline_families,
        candidate_families,
        baseline_label=baseline_label,
        candidate_label=candidate_label,
    )

    payload = {
        "baseline_label": baseline_label,
        "candidate_label": candidate_label,
        "baseline_source": str(baseline_source),
        "candidate_source": str(candidate_source),
        "comparison_count": len(comparisons),
        "families": comparisons,
    }

    target.mkdir(parents=True, exist_ok=True)
    (target / "world-movement-comparison.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    summary_lines = [
        "# World Movement Comparison",
        "",
        f"baseline_label={baseline_label}",
        f"candidate_label={candidate_label}",
        f"comparison_count={len(comparisons)}",
        "",
        "## Families",
        "",
    ]

    for item in comparisons[:25]:
        summary_lines.append(
            f"- prefix `{item['prefix_hex']}` labels `{', '.join(item['labels'])}` transition `{item['profile_transition']}` unique `{item['baseline_unique_positions']}->{item['candidate_unique_positions']}` x-span `{item['baseline_x_span']}->{item['candidate_x_span']}` y-span `{item['baseline_y_span']}->{item['candidate_y_span']}` avg-step `{item['baseline_avg_step_manhattan']}->{item['candidate_avg_step_manhattan']}` score `{item['movement_gain_score']}`"
        )

    (target / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

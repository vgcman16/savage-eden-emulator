from __future__ import annotations

import json
import re
from pathlib import Path


_WORD_RE = re.compile(r"[A-Za-z]{4,}")
_NUMERIC_ONLY_RE = re.compile(r"[\d\s:\-]+")
_PREFIXED_NUMERIC_TUPLE_RE = re.compile(r"\S*\d+(?:\s+\d+)+")
_TAGGED_NUMERIC_TOKEN_RE = re.compile(r"[^\s\d]{0,4}\d{3,}")


def _resolve_frame_index_path(source: Path) -> Path:
    if source.is_file():
        return source

    direct = source / "frame-index.json"
    if direct.exists():
        return direct

    nested = source / "frame-index" / "frame-index.json"
    if nested.exists():
        return nested

    raise FileNotFoundError(f"could not find frame-index.json under {source}")


def _extract_numeric_sequences(fragments: list[str]) -> list[list[int]]:
    sequences: list[list[int]] = []
    for fragment in fragments:
        stripped = fragment.strip()
        if not stripped:
            continue
        if _NUMERIC_ONLY_RE.fullmatch(stripped) or _PREFIXED_NUMERIC_TUPLE_RE.fullmatch(stripped):
            sequence = [int(token) for token in re.findall(r"-?\d+", stripped)]
            if sequence:
                sequences.append(sequence)
    return sequences


def _looks_like_named_text(fragment: str) -> bool:
    if " " not in fragment and "\t" not in fragment:
        return False

    for token in _WORD_RE.findall(fragment):
        lowered = token.lower()
        if lowered != token:
            continue
        if not any(vowel in lowered for vowel in "aeiou"):
            continue
        return True
    return False


def label_family(family: dict[str, object]) -> dict[str, object]:
    fragments = [fragment for fragment in family.get("ascii_fragments", []) if isinstance(fragment, str)]
    numeric_sequences = _extract_numeric_sequences(fragments)
    numeric_shapes = sorted({len(sequence) for sequence in numeric_sequences})

    labels: list[str] = []
    evidence: list[str] = []

    count = int(family.get("count", 0))
    size = int(family.get("size", 0))
    direction = str(family.get("direction", "unknown"))

    if not fragments and size <= 16 and count >= 20:
        labels.append("likely_keepalive_or_ack")
        evidence.append(f"no ASCII fragments, small frame size {size}, repeated {count} times")

    if numeric_sequences:
        shape_counts: dict[int, int] = {}
        for sequence in numeric_sequences:
            shape_counts[len(sequence)] = shape_counts.get(len(sequence), 0) + 1
        dominant_shape = max(shape_counts, key=shape_counts.get)
        dominant_ratio = shape_counts[dominant_shape] / len(numeric_sequences)

        dominant_sequences = [sequence for sequence in numeric_sequences if len(sequence) == dominant_shape]

        if dominant_shape == 4 and dominant_ratio >= 0.5:
            trailing_zero_ratio = sum(sequence[2:] == [0, 0] for sequence in dominant_sequences) / len(dominant_sequences)
            if trailing_zero_ratio >= 0.5:
                labels.append("likely_coordinate_quad_ascii")
                evidence.append("numeric fragments are 4-tuples and usually end with `0 0`")
            else:
                labels.append("likely_flag_tuple_ascii")
                evidence.append("numeric fragments are 4-tuples with changing flag-like values")
        elif dominant_shape == 3 and dominant_ratio >= 0.5:
            indexed_pair_ratio = sum(
                sequence[0] < 100 and sequence[1] >= 1000 and sequence[2] >= 1000
                for sequence in dominant_sequences
            ) / len(dominant_sequences)
            if indexed_pair_ratio >= 0.5:
                labels.append("likely_indexed_coordinate_pair_ascii")
                evidence.append("numeric fragments look like `<index>: <x> <y>`")
            else:
                labels.append("likely_numeric_triplet_ascii")
                evidence.append("numeric fragments are repeated 3-value tuples")
        elif dominant_shape == 2 and dominant_ratio >= 0.5:
            coordinate_ratio = sum(sequence[0] >= 1000 and sequence[1] >= 1000 for sequence in dominant_sequences) / len(dominant_sequences)
            if coordinate_ratio >= 0.5:
                labels.append("likely_coordinate_pair_ascii")
                evidence.append("numeric fragments are repeated 2-value coordinate-like pairs")
            else:
                labels.append("likely_numeric_pair_ascii")
                evidence.append("numeric fragments are repeated 2-value tuples")
        elif dominant_shape == 1 and dominant_ratio >= 0.5:
            tagged_numeric_fragments = [
                fragment
                for fragment in fragments
                if _TAGGED_NUMERIC_TOKEN_RE.fullmatch(fragment.strip())
            ]
            tagged_ratio = len(tagged_numeric_fragments) / len(fragments) if fragments else 0.0
            has_prefixed_token = any(not fragment.strip().isdigit() for fragment in tagged_numeric_fragments)
            if tagged_ratio >= 0.5 and has_prefixed_token:
                labels.append("likely_tagged_numeric_token")
                evidence.append(f"contains tagged numeric tokens such as `{tagged_numeric_fragments[0]}`")
            else:
                labels.append("likely_numeric_id_ascii")
                evidence.append("numeric fragments are repeated single-value ids or counters")
        elif dominant_shape >= 5 and dominant_ratio >= 0.5:
            labels.append("likely_flag_tuple_ascii")
            evidence.append("numeric fragments are long tuples with flag-like structure")

    named_text_fragments = [fragment for fragment in fragments if _looks_like_named_text(fragment)]
    if named_text_fragments:
        labels.append("likely_text_bearing_payload")
        evidence.append(f"contains named text such as `{named_text_fragments[0]}`")
        labels.append("likely_named_text_payload")
        evidence.append("contains one or more human-readable words")

    if not labels and fragments:
        tagged_numeric_fragments = [
            fragment
            for fragment in fragments
            if _TAGGED_NUMERIC_TOKEN_RE.fullmatch(fragment.strip())
        ]
        tagged_ratio = len(tagged_numeric_fragments) / len(fragments)
        has_prefixed_token = any(not fragment.strip().isdigit() for fragment in tagged_numeric_fragments)
        if tagged_ratio >= 0.5 and has_prefixed_token:
            labels.append("likely_tagged_numeric_token")
            evidence.append(f"contains tagged numeric tokens such as `{tagged_numeric_fragments[0]}`")

    if not labels:
        labels.append("unclassified")
        evidence.append(f"direction={direction}, size={size}, no strong ASCII pattern detected")

    confidence = "low"
    if any(
        label in labels
        for label in (
            "likely_coordinate_quad_ascii",
            "likely_indexed_coordinate_pair_ascii",
            "likely_coordinate_pair_ascii",
            "likely_named_text_payload",
        )
    ):
        confidence = "high"
    elif labels != ["unclassified"]:
        confidence = "medium"

    labeled_family = dict(family)
    labeled_family["labels"] = labels
    labeled_family["confidence"] = confidence
    labeled_family["numeric_shapes"] = numeric_shapes
    labeled_family["evidence"] = evidence
    return labeled_family


def write_world_family_labels(source: Path, target: Path) -> None:
    frame_index_path = _resolve_frame_index_path(source)
    frame_index_payload = json.loads(frame_index_path.read_text(encoding="utf-8"))
    families = frame_index_payload.get("families", [])
    assert isinstance(families, list)

    labeled_families = [label_family(family) for family in families if isinstance(family, dict)]

    payload = {
        "source": frame_index_payload.get("source", str(source)),
        "family_count": len(labeled_families),
        "labeled_family_count": sum(
            1
            for family in labeled_families
            if family.get("labels") != ["unclassified"]
        ),
        "families": labeled_families,
    }

    target.mkdir(parents=True, exist_ok=True)
    (target / "world-family-labels.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    summary_lines = [
        "# World Family Labels",
        "",
        f"source={payload['source']}",
        f"family_count={payload['family_count']}",
        f"labeled_family_count={payload['labeled_family_count']}",
        "",
        "## Families",
        "",
    ]

    for family in labeled_families:
        labels = ", ".join(f"`{label}`" for label in family["labels"])
        evidence = "; ".join(f"`{item}`" for item in family["evidence"][:2])
        fragments = family.get("ascii_fragments", [])
        assert isinstance(fragments, list)
        fragment_preview = ", ".join(f"`{fragment}`" for fragment in fragments[:2]) or "(none)"
        summary_lines.append(
            f"- count `{family['count']}` `{family['direction']}` size `{family['size']}` prefix `{family['prefix_hex']}` labels: {labels} confidence `{family['confidence']}` fragments: {fragment_preview} evidence: {evidence}"
        )

    (target / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

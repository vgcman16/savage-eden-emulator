from __future__ import annotations

import json
from pathlib import Path

from emulator.protocol.framing import split_length_prefixed_frames
from emulator.tools.packet_index import extract_ascii_fragments


def _resolve_packet_dir(source: Path) -> Path:
    packet_dir = source / "packets"
    return packet_dir if packet_dir.exists() else source


def _packet_direction(packet_name: str) -> str:
    if "-in-" in packet_name:
        return "in"
    if "-out-" in packet_name:
        return "out"
    return "unknown"


def write_frame_index(source: Path, target: Path) -> None:
    packet_dir = _resolve_packet_dir(source)
    packet_files = sorted(packet_dir.rglob("*.bin"), key=lambda path: path.relative_to(packet_dir).as_posix())

    frames: list[dict[str, object]] = []
    family_map: dict[tuple[str, int, str], dict[str, object]] = {}

    for packet_file in packet_files:
        relative_name = packet_file.relative_to(packet_dir).as_posix()
        direction = _packet_direction(relative_name)
        chunk = packet_file.read_bytes()

        for frame_index, (frame_offset, frame) in enumerate(split_length_prefixed_frames(chunk)):
            size = len(frame)
            prefix_hex = frame[:8].hex()
            ascii_fragments = extract_ascii_fragments(frame)

            frames.append(
                {
                    "source_packet": relative_name,
                    "frame_index": frame_index,
                    "frame_offset": frame_offset,
                    "direction": direction,
                    "size": size,
                    "prefix_hex": prefix_hex,
                    "ascii_fragments": ascii_fragments,
                }
            )

            family_key = (direction, size, prefix_hex)
            family = family_map.setdefault(
                family_key,
                {
                    "direction": direction,
                    "size": size,
                    "prefix_hex": prefix_hex,
                    "count": 0,
                    "example_frames": [],
                    "ascii_fragments": [],
                },
            )
            family["count"] = int(family["count"]) + 1

            example_frames = family["example_frames"]
            assert isinstance(example_frames, list)
            if len(example_frames) < 5:
                example_frames.append(f"{relative_name}#{frame_index}@{frame_offset}")

            family_fragments = family["ascii_fragments"]
            assert isinstance(family_fragments, list)
            for fragment in ascii_fragments:
                if fragment not in family_fragments:
                    family_fragments.append(fragment)

    families = sorted(
        family_map.values(),
        key=lambda family: (
            -int(family["count"]),
            str(family["direction"]),
            int(family["size"]),
            str(family["prefix_hex"]),
        ),
    )

    index_payload = {
        "source": str(source),
        "chunk_count": len(packet_files),
        "frame_count": len(frames),
        "family_count": len(families),
        "frames": frames,
        "families": families,
    }

    target.mkdir(parents=True, exist_ok=True)
    (target / "frame-index.json").write_text(json.dumps(index_payload, indent=2), encoding="utf-8")

    summary_lines = [
        "# Frame Index",
        "",
        f"source={source}",
        f"chunk_count={len(packet_files)}",
        f"frame_count={len(frames)}",
        f"family_count={len(families)}",
        "",
        "## Families",
        "",
    ]
    for family in families:
        fragments = family["ascii_fragments"]
        assert isinstance(fragments, list)
        preview = ", ".join(f"`{fragment}`" for fragment in fragments[:3]) or "(none)"
        summary_lines.append(
            f"- `{family['direction']}` size `{family['size']}` prefix `{family['prefix_hex']}` count `{family['count']}` fragments: {preview}"
        )

    (target / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

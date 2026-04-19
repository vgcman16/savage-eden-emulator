from __future__ import annotations

import json
from pathlib import Path


def extract_ascii_fragments(data: bytes, min_length: int = 4) -> list[str]:
    fragments: list[str] = []
    current: list[str] = []

    for byte in data:
        if 32 <= byte < 127:
            current.append(chr(byte))
            continue

        if len(current) >= min_length:
            fragments.append("".join(current))
        current = []

    if len(current) >= min_length:
        fragments.append("".join(current))

    return fragments


def _resolve_packet_dir(source: Path) -> Path:
    packet_dir = source / "packets"
    return packet_dir if packet_dir.exists() else source


def _packet_direction(packet_name: str) -> str:
    if "-in-" in packet_name:
        return "in"
    if "-out-" in packet_name:
        return "out"
    return "unknown"


def write_packet_index(source: Path, target: Path) -> None:
    packet_dir = _resolve_packet_dir(source)
    packet_files = sorted(packet_dir.rglob("*.bin"), key=lambda path: path.relative_to(packet_dir).as_posix())

    packets: list[dict[str, object]] = []
    family_map: dict[tuple[str, int, str], dict[str, object]] = {}

    for packet_file in packet_files:
        relative_name = packet_file.relative_to(packet_dir).as_posix()
        payload = packet_file.read_bytes()
        direction = _packet_direction(relative_name)
        size = len(payload)
        prefix_hex = payload[:8].hex()
        ascii_fragments = extract_ascii_fragments(payload)

        packets.append(
            {
                "name": relative_name,
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
                "example_packets": [],
                "ascii_fragments": [],
            },
        )
        family["count"] = int(family["count"]) + 1

        example_packets = family["example_packets"]
        assert isinstance(example_packets, list)
        if len(example_packets) < 5:
            example_packets.append(relative_name)

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
        "packet_count": len(packets),
        "family_count": len(families),
        "packets": packets,
        "families": families,
    }

    target.mkdir(parents=True, exist_ok=True)
    (target / "packet-index.json").write_text(json.dumps(index_payload, indent=2), encoding="utf-8")

    summary_lines = [
        "# Packet Index",
        "",
        f"source={source}",
        f"packet_count={len(packets)}",
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

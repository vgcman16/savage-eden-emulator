from __future__ import annotations

import json
import shutil
from pathlib import Path


def normalize_capture(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    packet_target = target / "packets"
    packet_target.mkdir(parents=True, exist_ok=True)
    packet_files = sorted((source / "packets").glob("*.bin"))
    for packet_file in packet_files:
        shutil.copy2(packet_file, packet_target / packet_file.name)
    manifest = {"source": str(source), "packets": [packet.name for packet in packet_files]}
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ConversationScript:
    match_bytes: bytes
    response_bytes: bytes
    close_after_response: bool = False

    @classmethod
    def load(cls, path: Path) -> "ConversationScript":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            match_bytes=bytes.fromhex(payload["match_hex"]),
            response_bytes=bytes.fromhex(payload["response_hex"]),
            close_after_response=bool(payload.get("close_after_response", False)),
        )

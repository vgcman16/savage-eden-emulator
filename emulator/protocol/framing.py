from __future__ import annotations


def read_u16_le(data: bytes) -> int:
    return int.from_bytes(data[:2], "little")


def read_u32_le(data: bytes) -> int:
    return int.from_bytes(data[:4], "little")


def xor_bytes(data: bytes, key: int) -> bytes:
    return bytes(value ^ key for value in data)


def hexdump(data: bytes) -> str:
    hex_part = " ".join(f"{value:02X}" for value in data)
    return f"00000000  {hex_part}"


def split_length_prefixed_frames(data: bytes) -> list[tuple[int, bytes]]:
    frames: list[tuple[int, bytes]] = []
    cursor = 0

    while cursor < len(data):
        if cursor + 2 > len(data):
            raise ValueError(f"truncated frame header at offset {cursor}")

        declared_size = read_u16_le(data[cursor : cursor + 2])
        frame_size = declared_size + 2
        frame_end = cursor + frame_size

        if frame_size <= 2:
            raise ValueError(f"invalid frame size {declared_size} at offset {cursor}")
        if frame_end > len(data):
            raise ValueError(
                f"truncated frame at offset {cursor}: expected {frame_size} bytes, got {len(data) - cursor}"
            )

        frames.append((cursor, data[cursor:frame_end]))
        cursor = frame_end

    return frames

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

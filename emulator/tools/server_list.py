from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ServerListEntry:
    name: str
    host: str
    port: int
    extra: tuple[str, ...] = ()

    @classmethod
    def from_row(cls, row: str) -> "ServerListEntry":
        parts = row.split()
        if len(parts) < 3:
            raise ValueError(f"server-list row must contain at least 3 tokens: {row!r}")
        return cls(
            name=parts[0],
            host=parts[1],
            port=int(parts[2]),
            extra=tuple(parts[3:]),
        )

    def to_row(self) -> str:
        parts = [self.name, self.host, str(self.port), *self.extra]
        return " ".join(parts)


@dataclass(slots=True)
class ServerListFile:
    prefix: bytes
    base_offset: int
    seed: int
    entries: list[ServerListEntry]


def decode_server_list_bytes(data: bytes) -> ServerListFile:
    if len(data) < 15:
        raise ValueError("server-list payload is too short")

    prefix = data[:6]
    base_offset = int.from_bytes(data[6:10], "little")
    seed = data[10]
    encoded_count = int.from_bytes(data[11:15], "little")
    entry_count = encoded_count - base_offset

    if entry_count < 0:
        raise ValueError("encoded entry count is smaller than the base offset")

    index = 15
    previous_offset = encoded_count
    previous_byte = seed
    entries: list[ServerListEntry] = []

    for _ in range(entry_count):
        if index + 4 > len(data):
            raise ValueError("server-list payload ended before the next row offset")
        next_offset = int.from_bytes(data[index : index + 4], "little")
        index += 4
        row_length = next_offset - previous_offset
        if row_length < 0:
            raise ValueError("server-list row length was negative")
        if index + row_length > len(data):
            raise ValueError("server-list row extends past the end of the payload")

        decoded_row = bytearray()
        for raw_byte in data[index : index + row_length]:
            decoded_byte = (raw_byte - previous_byte) & 0xFF
            decoded_row.append(decoded_byte)
            previous_byte = raw_byte
        index += row_length
        entries.append(ServerListEntry.from_row(decoded_row.decode("ascii")))
        previous_offset = next_offset

    if index != len(data):
        raise ValueError("server-list payload contained unexpected trailing bytes")

    return ServerListFile(
        prefix=prefix,
        base_offset=base_offset,
        seed=seed,
        entries=entries,
    )


def encode_server_list_bytes(server_list: ServerListFile) -> bytes:
    encoded = bytearray()
    encoded.extend(server_list.prefix)
    encoded.extend(server_list.base_offset.to_bytes(4, "little"))
    encoded.append(server_list.seed & 0xFF)

    entry_count = len(server_list.entries)
    encoded_count = server_list.base_offset + entry_count
    encoded.extend(encoded_count.to_bytes(4, "little"))

    previous_offset = encoded_count
    previous_byte = server_list.seed & 0xFF

    for entry in server_list.entries:
        row_bytes = entry.to_row().encode("ascii")
        previous_offset += len(row_bytes)
        encoded.extend(previous_offset.to_bytes(4, "little"))
        for decoded_byte in row_bytes:
            raw_byte = (previous_byte + decoded_byte) & 0xFF
            encoded.append(raw_byte)
            previous_byte = raw_byte

    return bytes(encoded)


def decode_server_list(path: Path) -> ServerListFile:
    return decode_server_list_bytes(path.read_bytes())


def write_server_list(path: Path, server_list: ServerListFile) -> None:
    path.write_bytes(encode_server_list_bytes(server_list))


def rewrite_server_list_endpoint(server_list: ServerListFile, host: str, port: int) -> ServerListFile:
    return ServerListFile(
        prefix=server_list.prefix,
        base_offset=server_list.base_offset,
        seed=server_list.seed,
        entries=[
            ServerListEntry(entry.name, host, port, entry.extra)
            for entry in server_list.entries
        ],
    )

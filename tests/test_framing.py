import unittest

from emulator.protocol.framing import (
    hexdump,
    read_u16_le,
    read_u32_le,
    split_length_prefixed_frames,
    xor_bytes,
)


class FramingTests(unittest.TestCase):
    def test_helpers_cover_basic_binary_analysis(self) -> None:
        self.assertEqual(read_u16_le(b"\x34\x12"), 0x1234)
        self.assertEqual(read_u32_le(b"\x78\x56\x34\x12"), 0x12345678)
        self.assertEqual(xor_bytes(b"\x01\x02", 0xFF), b"\xFE\xFD")
        self.assertIn("01 02 03", hexdump(b"\x01\x02\x03"))

    def test_split_length_prefixed_frames_handles_coalesced_frames(self) -> None:
        payload = b"\x03\x00ABC\x04\x00WXYZ"

        frames = split_length_prefixed_frames(payload)

        self.assertEqual(
            frames,
            [
                (0, b"\x03\x00ABC"),
                (5, b"\x04\x00WXYZ"),
            ],
        )

    def test_split_length_prefixed_frames_rejects_truncated_frame(self) -> None:
        with self.assertRaisesRegex(ValueError, "truncated frame"):
            split_length_prefixed_frames(b"\x05\x00AB")


if __name__ == "__main__":
    unittest.main()

import unittest

from emulator.protocol.framing import hexdump, read_u16_le, read_u32_le, xor_bytes


class FramingTests(unittest.TestCase):
    def test_helpers_cover_basic_binary_analysis(self) -> None:
        self.assertEqual(read_u16_le(b"\x34\x12"), 0x1234)
        self.assertEqual(read_u32_le(b"\x78\x56\x34\x12"), 0x12345678)
        self.assertEqual(xor_bytes(b"\x01\x02", 0xFF), b"\xFE\xFD")
        self.assertIn("01 02 03", hexdump(b"\x01\x02\x03"))


if __name__ == "__main__":
    unittest.main()

import unittest

from emulator.tools.server_list import (
    ServerListEntry,
    decode_server_list_bytes,
    encode_server_list_bytes,
    rewrite_server_list_endpoint,
)


SAMPLE_SVRLIST = bytes.fromhex(
    "38e71fdcea9de010000032e1100000fa10000079c5145697e3033a73a1d2053c6a9bcbfc2a5d90b0e4144479"
)
SAMPLE_SVRLISTM = bytes.fromhex(
    "0000000000003b7800004b3c7800005a78000098f96ddf48c01d3d6ea2d604366698c6f7295f8dbeef27477babde103061"
)


class ServerListToolsTests(unittest.TestCase):
    def test_decodes_classic_login_server_list(self) -> None:
        server_list = decode_server_list_bytes(SAMPLE_SVRLIST)

        self.assertEqual(len(server_list.entries), 1)
        self.assertEqual(
            server_list.entries[0],
            ServerListEntry("GLOBAL", "79.137.101.33", 4005),
        )

    def test_round_trips_existing_server_list_bytes(self) -> None:
        server_list = decode_server_list_bytes(SAMPLE_SVRLISTM)

        self.assertEqual(encode_server_list_bytes(server_list), SAMPLE_SVRLISTM)

    def test_rewrites_endpoint_without_changing_entry_shape(self) -> None:
        server_list = decode_server_list_bytes(SAMPLE_SVRLISTM)

        rewritten = rewrite_server_list_endpoint(server_list, "127.0.0.1", 14021)

        self.assertEqual(
            rewritten.entries[0],
            ServerListEntry("Matrix]", "127.0.0.1", 14021, ("1",)),
        )
        decoded = decode_server_list_bytes(encode_server_list_bytes(rewritten))
        self.assertEqual(decoded.entries, rewritten.entries)


if __name__ == "__main__":
    unittest.main()

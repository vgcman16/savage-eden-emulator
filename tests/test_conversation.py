from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from emulator.protocol.conversation import ConversationScript


class ConversationScriptTests(unittest.TestCase):
    def test_loads_match_and_response_hex(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            script_path = Path(tmp_dir) / "login-script.json"
            script_path.write_text(
                json.dumps(
                    {
                        "match_hex": "01026C6F67696E",
                        "response_hex": "90000000",
                    }
                ),
                encoding="utf-8",
            )
            script = ConversationScript.load(script_path)
            self.assertEqual(script.match_bytes, b"\x01\x02login")
            self.assertEqual(script.response_bytes, b"\x90\x00\x00\x00")


if __name__ == "__main__":
    unittest.main()

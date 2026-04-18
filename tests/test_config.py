from pathlib import Path
import unittest

from emulator.config import EmulatorConfig


class EmulatorConfigTests(unittest.TestCase):
    def test_defaults_match_milestone_one_expectations(self) -> None:
        config = EmulatorConfig()

        self.assertEqual(config.bind_host, "127.0.0.1")
        self.assertEqual(config.http_port, 8080)
        self.assertEqual(config.login_port, 4021)
        self.assertEqual(config.capture_root, Path("captures"))


if __name__ == "__main__":
    unittest.main()

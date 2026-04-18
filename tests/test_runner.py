from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from emulator import runner


class RunnerTests(unittest.TestCase):
    def test_main_once_starts_and_stops_services(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            exit_code = runner.main(
                [
                    "--capture-root",
                    tmp_dir,
                    "--http-port",
                    "0",
                    "--login-port",
                    "0",
                    "--once",
                ]
            )

            self.assertEqual(exit_code, 0)
            run_dirs = list(Path(tmp_dir).glob("*"))
            self.assertEqual(len(run_dirs), 1)
            self.assertTrue((run_dirs[0] / "summary.md").exists())


if __name__ == "__main__":
    unittest.main()

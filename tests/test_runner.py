from pathlib import Path
from tempfile import TemporaryDirectory
import json
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

    def test_main_once_accepts_script_path_and_records_it_in_summary(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            script_path = tmp_path / "login-script.json"
            script_path.write_text(
                json.dumps(
                    {
                        "match_hex": "01026C6F67696E",
                        "response_hex": "90000000",
                    }
                ),
                encoding="utf-8",
            )

            exit_code = runner.main(
                [
                    "--capture-root",
                    tmp_dir,
                    "--http-port",
                    "0",
                    "--login-port",
                    "0",
                    "--script-path",
                    str(script_path),
                    "--once",
                ]
            )

            self.assertEqual(exit_code, 0)
            run_dir = next(tmp_path.glob("*"))
            summary = (run_dir / "summary.md").read_text(encoding="utf-8")
            self.assertIn(f"script_path={script_path}", summary)

    def test_main_once_accepts_proxy_target_and_records_it_in_summary(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            exit_code = runner.main(
                [
                    "--capture-root",
                    tmp_dir,
                    "--http-port",
                    "0",
                    "--login-port",
                    "0",
                    "--proxy-host",
                    "127.0.0.1",
                    "--proxy-port",
                    "4005",
                    "--once",
                ]
            )

            self.assertEqual(exit_code, 0)
            run_dir = next(tmp_path.glob("*"))
            summary = (run_dir / "summary.md").read_text(encoding="utf-8")
            self.assertIn("proxy_target=127.0.0.1:4005", summary)

    def test_main_once_accepts_extra_proxy_specs_and_records_them_in_summary(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            exit_code = runner.main(
                [
                    "--capture-root",
                    tmp_dir,
                    "--http-port",
                    "0",
                    "--login-port",
                    "0",
                    "--proxy-host",
                    "127.0.0.1",
                    "--proxy-port",
                    "4005",
                    "--extra-proxy",
                    "4007:4007",
                    "--extra-proxy",
                    "4008:4008",
                    "--once",
                ]
            )

            self.assertEqual(exit_code, 0)
            run_dir = next(tmp_path.glob("*"))
            summary = (run_dir / "summary.md").read_text(encoding="utf-8")
            self.assertIn("extra_proxy=4007->127.0.0.1:4007", summary)
            self.assertIn("extra_proxy=4008->127.0.0.1:4008", summary)


if __name__ == "__main__":
    unittest.main()

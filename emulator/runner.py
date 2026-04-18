from __future__ import annotations

import argparse
from pathlib import Path

from emulator.config import EmulatorConfig
from emulator.logging.trace_writer import TraceWriter
from emulator.services.http_probe import HttpProbeService
from emulator.services.login_gateway import LoginGatewayService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind-host", default="127.0.0.1")
    parser.add_argument("--http-port", type=int, default=8080)
    parser.add_argument("--login-port", type=int, default=4021)
    parser.add_argument("--capture-root", default="captures")
    parser.add_argument("--script-path")
    parser.add_argument("--once", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    script_path = Path(args.script_path) if args.script_path else None
    config = EmulatorConfig(
        bind_host=args.bind_host,
        http_port=args.http_port,
        login_port=args.login_port,
        capture_root=Path(args.capture_root),
    )
    writer = TraceWriter(config.capture_root)
    run_dir = writer.start_run("runner")
    http_probe = HttpProbeService(config.bind_host, config.http_port, writer)
    login_gateway = LoginGatewayService(
        config.bind_host,
        config.login_port,
        writer,
        script_path=script_path,
    )
    http_probe.start()
    login_gateway.start()
    writer.write_text(
        "summary.md",
        (
            f"bind_host={config.bind_host}\n"
            f"http_port={http_probe.port}\n"
            f"login_port={login_gateway.port}\n"
            f"script_path={script_path}\n"
            f"run_dir={run_dir}\n"
        ),
    )
    if args.once:
        http_probe.stop()
        login_gateway.stop()
        return 0
    try:
        while True:
            pass
    except KeyboardInterrupt:
        http_probe.stop()
        login_gateway.stop()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

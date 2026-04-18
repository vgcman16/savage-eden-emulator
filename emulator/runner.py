from __future__ import annotations

import argparse
from pathlib import Path

from emulator.config import EmulatorConfig
from emulator.logging.trace_writer import TraceWriter
from emulator.services.http_probe import HttpProbeService
from emulator.services.login_gateway import LoginGatewayService


def _parse_extra_proxy_spec(raw_spec: str, default_host: str | None) -> tuple[int, str, int]:
    parts = raw_spec.split(":")
    if len(parts) == 2:
        if default_host is None:
            raise ValueError("extra-proxy requires proxy-host unless the target host is included")
        listen_port_text, target_port_text = parts
        return int(listen_port_text), default_host, int(target_port_text)
    if len(parts) == 3:
        listen_port_text, target_host, target_port_text = parts
        return int(listen_port_text), target_host, int(target_port_text)
    raise ValueError(f"extra-proxy must use listen:target-port or listen:target-host:target-port: {raw_spec}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind-host", default="127.0.0.1")
    parser.add_argument("--http-port", type=int, default=8080)
    parser.add_argument("--login-port", type=int, default=4021)
    parser.add_argument("--capture-root", default="captures")
    parser.add_argument("--script-path")
    parser.add_argument("--proxy-host")
    parser.add_argument("--proxy-port", type=int)
    parser.add_argument("--extra-proxy", action="append", default=[])
    parser.add_argument("--once", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.script_path and args.proxy_host:
        raise ValueError("script-path and proxy-host are mutually exclusive")
    if args.proxy_port is not None and not args.proxy_host:
        raise ValueError("proxy-port requires proxy-host")
    extra_proxy_specs = [
        _parse_extra_proxy_spec(raw_spec, args.proxy_host)
        for raw_spec in args.extra_proxy
    ]
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
        proxy_host=args.proxy_host,
        proxy_port=args.proxy_port,
    )
    extra_proxies = [
        LoginGatewayService(
            config.bind_host,
            listen_port,
            writer,
            proxy_host=target_host,
            proxy_port=target_port,
            packet_dir=f"packets/proxy-{listen_port}",
        )
        for listen_port, target_host, target_port in extra_proxy_specs
    ]
    services = [http_probe, login_gateway, *extra_proxies]
    for service in services:
        service.start()
    extra_proxy_lines = "".join(
        f"extra_proxy={listen_port}->{target_host}:{target_port}\n"
        for listen_port, target_host, target_port in extra_proxy_specs
    )
    writer.write_text(
        "summary.md",
        (
            f"bind_host={config.bind_host}\n"
            f"http_port={http_probe.port}\n"
            f"login_port={login_gateway.port}\n"
            f"script_path={script_path}\n"
            f"proxy_target={args.proxy_host}:{args.proxy_port}\n"
            f"{extra_proxy_lines}"
            f"run_dir={run_dir}\n"
        ),
    )
    if args.once:
        for service in reversed(services):
            service.stop()
        return 0
    try:
        while True:
            pass
    except KeyboardInterrupt:
        for service in reversed(services):
            service.stop()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

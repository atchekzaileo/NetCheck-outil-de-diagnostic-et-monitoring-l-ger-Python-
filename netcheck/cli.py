from __future__ import annotations

import argparse
import asyncio
from typing import Any, Dict, List, Tuple

from .checks import dns_lookup, http_check, ping, tcp_connect, tls_expiry
from .report import build_report, format_console
from .utils import clamp, write_json


def parse_tcp_list(s: str) -> List[Tuple[str, int]]:
    out: List[Tuple[str, int]] = []
    for item in (x.strip() for x in s.split(",")):
        if not item:
            continue
        if ":" not in item:
            raise ValueError(f"Invalid tcp target: {item} (expected host:port)")
        host, port_s = item.split(":", 1)
        port = int(port_s)
        out.append((host.strip(), port))
    return out


def parse_url_list(s: str) -> List[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="netcheck", description="Network diagnostics: DNS, TCP, HTTP(S), TLS expiry, ping + JSON report")
    p.add_argument("--dns", help="Hostname to resolve (ex: google.com)")
    p.add_argument("--ping", dest="ping_host", help="Host to ping (ex: 1.1.1.1 or google.com)")
    p.add_argument("--ping-count", type=int, default=3)
    p.add_argument("--tcp", help="Comma list of host:port (ex: google.com:443,1.1.1.1:53)")
    p.add_argument("--http", help="Comma list of URLs (ex: https://example.com,https://github.com)")
    p.add_argument("--tls", help="Host for TLS expiry (ex: github.com)")
    p.add_argument("--tls-port", type=int, default=443)
    p.add_argument("--json-out", help="Write JSON report to a file (ex: report.json)")
    return p


async def run_checks(args: argparse.Namespace) -> Dict[str, Any]:
    results: Dict[str, Any] = {}

    tasks = []

    if args.dns:
        tasks.append(("dns", dns_lookup(args.dns)))

    if args.ping_host:
        c = clamp(args.ping_count, 1, 10)
        tasks.append(("ping", ping(args.ping_host, count=c)))

    tcp_tasks = []
    if args.tcp:
        for host, port in parse_tcp_list(args.tcp):
            tcp_tasks.append(tcp_connect(host, port))
    if tcp_tasks:
        results["tcp"] = await asyncio.gather(*tcp_tasks)

    http_tasks = []
    if args.http:
        for url in parse_url_list(args.http):
            http_tasks.append(http_check(url))
    if http_tasks:
        results["http"] = await asyncio.gather(*http_tasks)

    if args.tls:
        tasks.append(("tls", tls_expiry(args.tls, port=args.tls_port)))

    if tasks:
        done = await asyncio.gather(*(coro for _, coro in tasks))
        for (k, _), v in zip(tasks, done):
            results[k] = v

    return results


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not any([args.dns, args.ping_host, args.tcp, args.http, args.tls]):
        parser.print_help()
        return 2

    results = asyncio.run(run_checks(args))
    report = build_report(results)
    print(format_console(report))

    if args.json_out:
        write_json(args.json_out, report)

    return 0 if report["ok"] else 1

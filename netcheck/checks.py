from __future__ import annotations

import asyncio
import socket
import ssl
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from .utils import Timed, now_ms


@dataclass
class DNSResult:
    ok: bool
    hostname: str
    ips: list[str]
    error: str | None
    ms: float


async def dns_lookup(hostname: str, timeout_s: float = 2.5) -> DNSResult:
    start = now_ms()
    try:
        loop = asyncio.get_running_loop()
        infos = await asyncio.wait_for(loop.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP), timeout=timeout_s)
        ips = sorted({info[4][0] for info in infos})
        return DNSResult(ok=True, hostname=hostname, ips=ips, error=None, ms=now_ms() - start)
    except Exception as e:
        return DNSResult(ok=False, hostname=hostname, ips=[], error=str(e), ms=now_ms() - start)


@dataclass
class TCPResult:
    ok: bool
    host: str
    port: int
    ms: float
    error: str | None


async def tcp_connect(host: str, port: int, timeout_s: float = 2.5) -> TCPResult:
    start = now_ms()
    try:
        fut = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(fut, timeout=timeout_s)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return TCPResult(ok=True, host=host, port=port, ms=now_ms() - start, error=None)
    except Exception as e:
        return TCPResult(ok=False, host=host, port=port, ms=now_ms() - start, error=str(e))


@dataclass
class HTTPResult:
    ok: bool
    url: str
    status: int | None
    ms: float
    error: str | None


async def http_check(url: str, timeout_s: float = 4.0, method: str = "GET") -> HTTPResult:
    start = now_ms()

    def _req() -> Tuple[int, int]:
        req = urllib.request.Request(url=url, method=method, headers={"User-Agent": "netcheck/1.0"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return int(resp.status), int(resp.getheader("Content-Length") or 0)

    try:
        loop = asyncio.get_running_loop()
        status, _ = await asyncio.wait_for(loop.run_in_executor(None, _req), timeout=timeout_s + 0.5)
        return HTTPResult(ok=True, url=url, status=status, ms=now_ms() - start, error=None)
    except Exception as e:
        return HTTPResult(ok=False, url=url, status=None, ms=now_ms() - start, error=str(e))


@dataclass
class TLSResult:
    ok: bool
    host: str
    port: int
    not_after: str | None
    days_left: int | None
    ms: float
    error: str | None


async def tls_expiry(host: str, port: int = 443, timeout_s: float = 3.5) -> TLSResult:
    start = now_ms()

    def _fetch_cert() -> Dict[str, Any]:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout_s) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                return ssock.getpeercert()

    try:
        loop = asyncio.get_running_loop()
        cert = await asyncio.wait_for(loop.run_in_executor(None, _fetch_cert), timeout=timeout_s + 0.5)
        not_after_raw = cert.get("notAfter")
        if not not_after_raw:
            return TLSResult(ok=False, host=host, port=port, not_after=None, days_left=None, ms=now_ms() - start, error="no notAfter")
        dt = datetime.strptime(not_after_raw, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        days = (dt - datetime.now(timezone.utc)).days
        return TLSResult(ok=True, host=host, port=port, not_after=dt.isoformat(), days_left=days, ms=now_ms() - start, error=None)
    except Exception as e:
        return TLSResult(ok=False, host=host, port=port, not_after=None, days_left=None, ms=now_ms() - start, error=str(e))


@dataclass
class PingResult:
    ok: bool
    host: str
    transmitted: int
    received: int
    loss_pct: float
    avg_ms: float | None
    ms: float
    error: str | None


def _ping_cmd(host: str, count: int, timeout_s: int) -> list[str]:
    if sys.platform.startswith("win"):
        return ["ping", "-n", str(count), "-w", str(timeout_s * 1000), host]
    return ["ping", "-c", str(count), "-W", str(timeout_s), host]


async def ping(host: str, count: int = 3, timeout_s: int = 2) -> PingResult:
    start = now_ms()
    cmd = _ping_cmd(host, count=count, timeout_s=timeout_s)

    def _run() -> Tuple[int, str]:
        p = subprocess.run(cmd, capture_output=True, text=True)
        out = (p.stdout or "") + "\n" + (p.stderr or "")
        return p.returncode, out

    try:
        loop = asyncio.get_running_loop()
        code, out = await loop.run_in_executor(None, _run)

        transmitted = count
        received = 0
        avg = None

        if "Received =" in out and "Lost =" in out:
            try:
                part = out.split("Packets:")[1]
                segs = part.split(",")
                rec = [s for s in segs if "Received" in s][0]
                received = int("".join(ch for ch in rec if ch.isdigit()))
            except Exception:
                received = 0
            if "Average" in out:
                try:
                    avg_part = out.split("Average =")[1].strip()
                    num = "".join(ch for ch in avg_part if ch.isdigit())
                    avg = float(num) if num else None
                except Exception:
                    avg = None
        else:
            if "packets transmitted" in out and "received" in out:
                try:
                    line = [l for l in out.splitlines() if "packets transmitted" in l][0]
                    received = int(line.split("received")[0].split()[-1])
                except Exception:
                    received = 0
            if "min/avg/max" in out:
                try:
                    line = [l for l in out.splitlines() if "min/avg/max" in l][0]
                    avg = float(line.split("=")[1].split("/")[1].strip())
                except Exception:
                    avg = None

        loss_pct = 0.0 if transmitted == 0 else (1.0 - (received / transmitted)) * 100.0
        ok = (code == 0) and received > 0
        return PingResult(ok=ok, host=host, transmitted=transmitted, received=received, loss_pct=loss_pct, avg_ms=avg, ms=now_ms() - start, error=None if ok else None)
    except Exception as e:
        return PingResult(ok=False, host=host, transmitted=count, received=0, loss_pct=100.0, avg_ms=None, ms=now_ms() - start, error=str(e))

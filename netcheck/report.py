from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List


def to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "__dict__"):
        return asdict(obj)
    return dict(obj)


def build_report(results: Dict[str, Any]) -> Dict[str, Any]:
    ok = True
    for v in results.values():
        if isinstance(v, list):
            ok = ok and all(getattr(x, "ok", False) for x in v)
        else:
            ok = ok and bool(getattr(v, "ok", False))

    return {
        "ok": ok,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": {k: [to_dict(x) for x in v] if isinstance(v, list) else to_dict(v) for k, v in results.items()},
    }


def format_console(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"NetCheck — status: {'OK' if report['ok'] else 'ISSUES'}")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")

    res = report["results"]

    def block(title: str) -> None:
        lines.append(title)
        lines.append("-" * len(title))

    if "dns" in res:
        block("DNS")
        r = res["dns"]
        lines.append(f"{'OK' if r['ok'] else 'FAIL'}  {r['hostname']}  {', '.join(r['ips']) if r['ips'] else ''}  ({r['ms']:.1f} ms)")
        if r.get("error"):
            lines.append(f"      {r['error']}")
        lines.append("")

    if "ping" in res:
        block("PING")
        r = res["ping"]
        extra = f"avg={r['avg_ms']} ms" if r.get("avg_ms") is not None else ""
        lines.append(f"{'OK' if r['ok'] else 'FAIL'}  {r['host']}  rx={r['received']}/{r['transmitted']} loss={r['loss_pct']:.1f}% {extra} ({r['ms']:.1f} ms)")
        if r.get("error"):
            lines.append(f"      {r['error']}")
        lines.append("")

    if "tcp" in res:
        block("TCP")
        for r in res["tcp"]:
            lines.append(f"{'OK' if r['ok'] else 'FAIL'}  {r['host']}:{r['port']}  ({r['ms']:.1f} ms)")
            if r.get("error"):
                lines.append(f"      {r['error']}")
        lines.append("")

    if "http" in res:
        block("HTTP")
        for r in res["http"]:
            status = r["status"] if r.get("status") is not None else "-"
            lines.append(f"{'OK' if r['ok'] else 'FAIL'}  {r['url']}  status={status}  ({r['ms']:.1f} ms)")
            if r.get("error"):
                lines.append(f"      {r['error']}")
        lines.append("")

    if "tls" in res:
        block("TLS")
        r = res["tls"]
        dl = f"{r['days_left']} days left" if r.get("days_left") is not None else ""
        lines.append(f"{'OK' if r['ok'] else 'FAIL'}  {r['host']}:{r['port']}  {dl}")
        if r.get("not_after"):
            lines.append(f"      expires: {r['not_after']}")
        if r.get("error"):
            lines.append(f"      {r['error']}")
        lines.append("")

    return "\n".join(lines)

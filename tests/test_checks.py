import asyncio
import socket
import pytest

from netcheck.checks import dns_lookup, tcp_connect


@pytest.mark.asyncio
async def test_dns_lookup_example():
    r = await dns_lookup("example.com")
    assert r.hostname == "example.com"
    assert isinstance(r.ok, bool)
    assert isinstance(r.ms, float)


@pytest.mark.asyncio
async def test_tcp_connect_localhost_closed_port():
    r = await tcp_connect("127.0.0.1", 9, timeout_s=0.6)
    assert r.host == "127.0.0.1"
    assert r.port == 9
    assert isinstance(r.ok, bool)

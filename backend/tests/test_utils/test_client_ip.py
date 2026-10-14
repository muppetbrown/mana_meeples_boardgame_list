"""Client IP resolution: only proxy-appended X-Forwarded-For entries are trusted."""
from unittest.mock import Mock

import pytest

import config
from utils.client_ip import get_client_ip


def _request(forwarded=None, host="10.0.0.9"):
    request = Mock()
    request.headers = {"x-forwarded-for": forwarded} if forwarded is not None else {}
    request.client = Mock(host=host) if host else None
    return request


@pytest.fixture(autouse=True)
def one_proxy(monkeypatch):
    monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 1)


def test_uses_entry_appended_by_our_proxy():
    assert get_client_ip(_request("203.0.113.7")) == "203.0.113.7"


def test_spoofed_leftmost_entry_is_ignored():
    # The attacker sends "1.1.1.1"; the proxy appends the address it actually saw.
    assert get_client_ip(_request("1.1.1.1, 203.0.113.7")) == "203.0.113.7"


def test_two_trusted_proxies_skip_the_proxy_hop(monkeypatch):
    monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 2)
    assert get_client_ip(_request("1.1.1.1, 203.0.113.7, 172.70.0.1")) == "203.0.113.7"


def test_more_trusted_hops_than_entries_uses_leftmost(monkeypatch):
    monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 5)
    assert get_client_ip(_request("203.0.113.7")) == "203.0.113.7"


def test_header_ignored_when_no_proxy_is_trusted(monkeypatch):
    monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 0)
    assert get_client_ip(_request("1.1.1.1", host="198.51.100.2")) == "198.51.100.2"


def test_falls_back_to_socket_address_without_header():
    assert get_client_ip(_request(None, host="198.51.100.2")) == "198.51.100.2"


def test_blank_header_falls_back_to_socket_address():
    assert get_client_ip(_request(" , ", host="198.51.100.2")) == "198.51.100.2"


def test_unknown_when_nothing_available():
    assert get_client_ip(_request(None, host=None)) == "unknown"

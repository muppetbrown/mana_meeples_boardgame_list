"""Client IP resolution: only proxy-appended X-Forwarded-For entries are trusted."""
from unittest.mock import Mock

import pytest

import config
import utils.client_ip as client_ip_module


def _request(forwarded=None, host="10.0.0.9"):
    request = Mock()
    request.headers = {"x-forwarded-for": forwarded} if forwarded is not None else {}
    request.client = Mock(host=host) if host else None
    return request


@pytest.fixture(autouse=True)
def one_proxy(monkeypatch):
    monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 1)


def test_uses_entry_appended_by_our_proxy():
    assert client_ip_module.get_client_ip(_request("203.0.113.7")) == "203.0.113.7"


def test_spoofed_leftmost_entry_is_ignored():
    # The attacker sends "1.1.1.1"; the proxy appends the address it actually saw.
    assert client_ip_module.get_client_ip(_request("1.1.1.1, 203.0.113.7")) == "203.0.113.7"


def test_two_trusted_proxies_skip_the_proxy_hop(monkeypatch):
    monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 2)
    assert client_ip_module.get_client_ip(_request("1.1.1.1, 203.0.113.7, 172.70.0.1")) == "203.0.113.7"


def test_more_trusted_hops_than_entries_uses_leftmost(monkeypatch):
    monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 5)
    assert client_ip_module.get_client_ip(_request("203.0.113.7")) == "203.0.113.7"


def test_header_ignored_when_no_proxy_is_trusted(monkeypatch):
    monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 0)
    assert client_ip_module.get_client_ip(_request("1.1.1.1", host="198.51.100.2")) == "198.51.100.2"


def test_falls_back_to_socket_address_without_header():
    assert client_ip_module.get_client_ip(_request(None, host="198.51.100.2")) == "198.51.100.2"


def test_blank_header_falls_back_to_socket_address():
    assert client_ip_module.get_client_ip(_request(" , ", host="198.51.100.2")) == "198.51.100.2"


def test_unknown_when_nothing_available():
    assert client_ip_module.get_client_ip(_request(None, host=None)) == "unknown"


def test_chain_length_is_logged_once_without_addresses(caplog):
    client_ip_module._log_chain_length_once.cache_clear()
    with caplog.at_level("INFO", logger="utils.client_ip"):
        client_ip_module.get_client_ip(_request("1.1.1.1, 203.0.113.7"))
        client_ip_module.get_client_ip(_request("1.1.1.1, 203.0.113.7"))
    messages = [r.getMessage() for r in caplog.records if "X-Forwarded-For arrived" in r.getMessage()]
    assert len(messages) == 1
    assert "2 entries" in messages[0]
    assert "203.0.113.7" not in messages[0]


def test_chain_labels():
    assert client_ip_module._chain_label(1) == "1 entry"
    assert client_ip_module._chain_label(3) == "3 entries"
    assert client_ip_module._chain_label(9) == "4 or more entries"

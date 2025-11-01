import json
from urllib.error import URLError
import types
import pytest

from backend.core.gmx_core.clients.gmx_rest_client import GmxRestClient

class DummyResp:
    def __init__(self, payload: dict):
        self._payload = payload
    def read(self):
        return json.dumps(self._payload).encode("utf-8")
    def __enter__(self): return self
    def __exit__(self, *a): return False

def test_rest_client_fallback_and_tickers(monkeypatch):
    payload = {"ETH": {"price": 3456.78}}

    def fake_urlopen(req, timeout=10.0):
        url = req.full_url
        if "bad-host" in url:
            raise URLError("boom")
        assert "/prices/tickers" in url
        return DummyResp(payload)

    monkeypatch.setattr("backend.core.gmx_core.clients.gmx_rest_client.urlopen", fake_urlopen)

    client = GmxRestClient(["https://bad-host", "https://good-host"])
    data = client.get_tickers()
    assert data["ETH"]["price"] == 3456.78

def test_markets_info(monkeypatch):
    markets_payload = {"markets": [{"address": "0xabc", "indexToken": {"symbol": "ETH"}}]}

    def fake_urlopen(req, timeout=10.0):
        return DummyResp(markets_payload)

    monkeypatch.setattr("backend.core.gmx_core.clients.gmx_rest_client.urlopen", fake_urlopen)

    client = GmxRestClient(["https://good-host"])
    info = client.get_markets_info()
    assert "markets" in info and info["markets"][0]["address"] == "0xabc"

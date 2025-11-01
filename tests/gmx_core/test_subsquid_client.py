import json
import pytest

from backend.core.gmx_core.clients.subsquid_client import SubsquidClient, GqlError

class DummyResp:
    def __init__(self, payload: dict):
        self._payload = payload
    def read(self):
        return json.dumps(self._payload).encode("utf-8")
    def __enter__(self): return self
    def __exit__(self, *a): return False

def test_subsquid_basic_query(monkeypatch):
    payload = {"data": {"positions": [{"id": "p1"}]}}
    def fake_urlopen(req, timeout=12.0):
        return DummyResp(payload)

    monkeypatch.setattr("backend.core.gmx_core.clients.subsquid_client.urlopen", fake_urlopen)

    client = SubsquidClient("https://squid.example/graphql")
    res = client.query("query Q{positions{ id }}")
    assert res["data"]["positions"][0]["id"] == "p1"

def test_subsquid_errors_raise(monkeypatch):
    payload = {"errors": [{"message": "bad query"}]}
    def fake_urlopen(req, timeout=12.0):
        return DummyResp(payload)

    monkeypatch.setattr("backend.core.gmx_core.clients.subsquid_client.urlopen", fake_urlopen)

    client = SubsquidClient("https://squid.example/graphql")
    with pytest.raises(GqlError):
        client.query("query Broken{}")

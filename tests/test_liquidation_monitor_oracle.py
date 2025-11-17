import types

from backend.core.monitor_core import liquidation_monitor as lm


class DummyDL:
    def __init__(self):
        self.alerts = []
        self.db = object()

    def __getattr__(self, name):
        # Let dl_alerts.ensure_schema(dl) and other things not explode
        raise AttributeError(name)


def test_liquidation_monitor_uses_oracle_thresholds(monkeypatch):
    dl = DummyDL()

    # Patch ConfigOracle to return a single threshold
    class FakeOracle:
        @staticmethod
        def get_liquid_thresholds():
            return {"BTC": 5.0}

    monkeypatch.setattr(lm, "ConfigOracle", FakeOracle, raising=False)

    # Make nearest map return a BTC distance below threshold
    monkeypatch.setattr(
        lm,
        "_get_nearest_map",
        lambda _dl: {"BTC": 4.0},
    )

    # Don’t hit real dl_alerts or Twilio
    monkeypatch.setattr(
        lm,
        "dl_alerts",
        types.SimpleNamespace(
            ensure_schema=lambda _d: None,
            upsert_open=lambda *_a, **_k: {"id": 1},
            resolve_open=lambda *_a, **_k: None,
        ),
    )
    monkeypatch.setattr(lm, "dispatch_voice", lambda *_a, **_k: None)

    result = lm._run_impl(dl, default_json_path=None)
    assert result["thresholds"]["BTC"] == 5.0
    assert "BTC" in result["open"]

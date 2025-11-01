import sys
import types

from backend.core.gmx_core.dl.positions_writer import write_positions

class NP:
    def __init__(self, **kw): self.__dict__.update(kw)

def sample_positions(n=2):
    return [NP(venue="GMX_V2", chain="arbitrum", account=f"0x{i}", symbol="ETH-USD",
               side="LONG", size_usd=10000.0, entry_price=3400.0, mark_price=3500.0,
               collateral_token="0xusdc", collateral_amount=1000.0,
               liquidation_price=2800.0, market_address="0xabc") for i in range(n)]

def test_writer_dry_run(capsys):
    write_positions(dl=None, positions=sample_positions(1), dry_run=True)
    out = capsys.readouterr().out
    assert "Dry run" in out

def test_writer_with_dl_object():
    calls = {}
    class DL:
        def upsert_positions(self, lst):
            calls["n"] = len(lst)

    write_positions(dl=DL(), positions=sample_positions(3), dry_run=False)
    assert calls["n"] == 3

def test_writer_module_fallback(monkeypatch):
    # Inject a dummy backend.data.dl_positions module
    mod = types.ModuleType("backend.data.dl_positions")
    called = {"n": 0}
    def upsert_positions(lst): called["n"] = len(lst)
    mod.upsert_positions = upsert_positions
    sys.modules["backend"] = types.ModuleType("backend")
    sys.modules["backend.data"] = types.ModuleType("backend.data")
    sys.modules["backend.data.dl_positions"] = mod

    write_positions(dl=None, positions=sample_positions(2), dry_run=False)
    assert called["n"] == 2

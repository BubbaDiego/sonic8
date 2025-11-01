import os
import textwrap
from pathlib import Path
from types import SimpleNamespace
import importlib

from backend.core.gmx_core.console import console as cmod

def make_cfg(tmp_path: Path):
    p = tmp_path / "gmx_chains.yaml"
    p.write_text(textwrap.dedent("""
    chains:
      arbitrum:
        chain_id: 42161
        rpc_http: "https://arb1.example/rpc"
        rest_hosts: ["https://rest.arb"]
        subsquid_url: "https://squid.arb/graphql"
    """), encoding="utf-8")
    return str(p)

class FakeRest:
    def get_markets_info(self): return {"markets": []}
class FakeSquid:
    def __init__(self, url): self.url = url

class FakeSource:
    def __init__(self, chain, rest, squid):
        self.chain = chain; self.rest = rest; self.squid = squid
    def list_open_positions(self, wallet, limit=1000):
        from backend.core.gmx_core.services.position_source import GMXPosition
        return [GMXPosition(
            account=wallet, market_address="0xabc", is_long=True,
            size_usd=10000.0, size_in_tokens=3.0, collateral_token="0xusdc",
            collateral_amount=1000.0, entry_price=3400.0, liquidation_price=2800.0,
            created_at=1, updated_at=2
        )]
    def normalize(self, positions):
        from backend.core.gmx_core.services.position_source import NormalizedPosition
        return [NormalizedPosition(
            venue="GMX_V2", chain=self.chain, account=positions[0].account,
            symbol="ETH-USD", side="LONG", size_usd=10000.0,
            entry_price=3400.0, mark_price=3500.0, collateral_token="0xusdc",
            collateral_amount=1000.0, liquidation_price=2800.0, market_address="0xabc"
        )]

def test_console_markets_and_positions(monkeypatch, tmp_path, capsys):
    cfg_path = make_cfg(tmp_path)

    # Monkeypatch clients and source inside console module
    monkeypatch.setattr(cmod, "GmxRestClient", lambda hosts: FakeRest())
    monkeypatch.setattr(cmod, "SubsquidClient", lambda url: FakeSquid(url))
    monkeypatch.setattr(cmod, "GMXPositionSource", FakeSource)

    # markets
    cmod.main(["--config", cfg_path, "markets", "--chain", "arbitrum"])
    out = capsys.readouterr().out
    assert "markets/info fetched for arbitrum" in out

    # positions (raw)
    cmod.main(["--config", cfg_path, "positions", "--chain", "arbitrum", "--wallet", "0x111", "--raw"])
    out = capsys.readouterr().out
    assert "0x111" in out

    # positions (normalize)
    cmod.main(["--config", cfg_path, "positions", "--chain", "arbitrum", "--wallet", "0x111", "--normalize"])
    out = capsys.readouterr().out
    assert "ETH-USD" in out and "GMX_V2" in out

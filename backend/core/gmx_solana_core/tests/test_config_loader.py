import os
import tempfile
import textwrap
from backend.core.gmx_solana_core.config_loader import load_solana_config, ConfigError

def test_load_solana_config(tmp_path, monkeypatch):
    p = tmp_path / "sol.yaml"
    p.write_text(textwrap.dedent("""
    solana:
      cluster: mainnet
      rpc_http: "ENV:SOL_RPC"
    """), encoding="utf-8")
    monkeypatch.setenv("SOL_RPC", "https://api.mainnet-beta.solana.com")
    cfg = load_solana_config(str(p))
    assert cfg["rpc_http"] == "https://api.mainnet-beta.solana.com"

def test_missing_solana_section(tmp_path):
    p = tmp_path / "sol.yaml"
    p.write_text("other: true")
    try:
        load_solana_config(str(p))
        assert False, "should have thrown"
    except ConfigError:
        assert True

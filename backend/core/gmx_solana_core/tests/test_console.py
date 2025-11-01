import textwrap
from pathlib import Path
from backend.core.gmx_solana_core.console import console as cmod

def make_cfg(tmp_path):
    p = tmp_path / "sol.yaml"
    p.write_text(textwrap.dedent("""
    solana:
      cluster: mainnet
      rpc_http: "https://api.mainnet-beta.solana.com"
    """), encoding="utf-8")
    return str(p)

def test_console_ping(capsys):
    exitcode = cmod.main(["ping"])
    out = capsys.readouterr().out
    assert "alive" in out

def test_console_config_show(tmp_path, capsys):
    path = make_cfg(tmp_path)
    cmod.main(["config", "--config", path])
    out = capsys.readouterr().out
    assert "rpc_http" in out

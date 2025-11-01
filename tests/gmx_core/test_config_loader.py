import os
import tempfile
from pathlib import Path
import textwrap
import pytest

from backend.core.gmx_core.config_loader import load_config, get_chain_cfg, ConfigError

def write_yaml(tmp_path: Path, content: str) -> str:
    p = tmp_path / "gmx_chains.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return str(p)

def test_load_config_and_env_resolution(tmp_path, monkeypatch):
    # Arrange
    monkeypatch.setenv("ARB_HTTP_RPC", "https://arb1.example/rpc")
    monkeypatch.setenv("ARB_REST_HOST", "https://rest.arb")
    monkeypatch.setenv("ARB_SUBSQUID_URL", "https://squid.arb/graphql")

    cfg_path = write_yaml(tmp_path, """
    chains:
      arbitrum:
        chain_id: 42161
        rpc_http: "ENV:ARB_HTTP_RPC"
        rest_hosts:
          - "ENV:ARB_REST_HOST"
          - "https://arbitrum-api.gmxinfra.io"
        subsquid_url: "ENV:ARB_SUBSQUID_URL"
    """)

    # Act
    cfg = load_config(cfg_path)
    arb = get_chain_cfg(cfg, "arbitrum")

    # Assert
    assert arb["rpc_http"] == "https://arb1.example/rpc"
    assert arb["rest_hosts"][0] == "https://rest.arb"
    assert arb["subsquid_url"] == "https://squid.arb/graphql"

def test_missing_env_raises(tmp_path, monkeypatch):
    # No env for ARB_HTTP_RPC
    cfg_path = write_yaml(tmp_path, """
    chains:
      arbitrum:
        chain_id: 42161
        rpc_http: "ENV:ARB_HTTP_RPC"
    """)

    with pytest.raises(ConfigError):
        load_config(cfg_path)

def test_unknown_chain_key(tmp_path, monkeypatch):
    monkeypatch.setenv("ARB_HTTP_RPC", "https://arb1.example/rpc")
    cfg_path = write_yaml(tmp_path, """
    chains:
      arbitrum:
        chain_id: 42161
        rpc_http: "ENV:ARB_HTTP_RPC"
    """)

    cfg = load_config(cfg_path)
    with pytest.raises(ConfigError):
        get_chain_cfg(cfg, "avalanche")

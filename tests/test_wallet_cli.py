import asyncio
import base64
from pathlib import Path

import pytest
from solders.keypair import Keypair

import wallet_cli


def _make_secret(seed_start: int = 0):
    seed = bytes(range(seed_start, seed_start + 32))
    kp = Keypair.from_seed(seed)
    secret = base64.b64encode(bytes(kp)).decode()
    return kp, secret


def test_secret_env(monkeypatch, capsys):
    kp, secret = _make_secret()
    monkeypatch.setenv("WALLET_SECRET_BASE64", secret)
    wallet_cli.args = wallet_cli.parser.parse_args([])
    asyncio.run(wallet_cli._amain())
    out = capsys.readouterr().out
    assert str(kp.pubkey()) in out


def test_cli_overrides_env(monkeypatch, capsys):
    kp_env, secret_env = _make_secret(10)
    kp_cli, secret_cli = _make_secret(20)
    monkeypatch.setenv("WALLET_SECRET_BASE64", secret_env)
    wallet_cli.args = wallet_cli.parser.parse_args(["--secret-b64", secret_cli])
    asyncio.run(wallet_cli._amain())
    out = capsys.readouterr().out
    assert str(kp_cli.pubkey()) in out
    assert str(kp_env.pubkey()) not in out


def test_secret_from_file(tmp_path: Path, capsys):
    kp, secret = _make_secret(30)
    file = tmp_path / "secret.txt"
    file.write_text(secret)
    wallet_cli.args = wallet_cli.parser.parse_args(["--secret-b64-file", str(file)])
    asyncio.run(wallet_cli._amain())
    out = capsys.readouterr().out
    assert str(kp.pubkey()) in out


def test_missing_secret(monkeypatch):
    monkeypatch.delenv("WALLET_SECRET_BASE64", raising=False)
    monkeypatch.delenv("MNEMONIC_BASE64", raising=False)
    wallet_cli.args = wallet_cli.parser.parse_args([])
    with pytest.raises(SystemExit) as exc:
        asyncio.run(wallet_cli._amain())
    assert "Missing secret" in str(exc.value)


def test_expected_pubkey_mismatch(capsys):
    kp, secret = _make_secret(40)
    wrong = Keypair.from_seed(bytes(range(50, 82)))
    wallet_cli.args = wallet_cli.parser.parse_args(["--secret-b64", secret, "--expected-pubkey", str(wrong.pubkey())])
    with pytest.raises(SystemExit) as exc:
        asyncio.run(wallet_cli._amain())
    msg = str(exc.value)
    assert "does not match expected pubkey" in msg
    assert str(wrong.pubkey()) in msg

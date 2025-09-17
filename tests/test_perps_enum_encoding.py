import sys
import types

import pytest


def _ensure_stubbed_modules() -> None:
    if "requests" not in sys.modules:
        requests_stub = types.ModuleType("requests")
        requests_stub.post = lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("requests stub invoked")
        )
        sys.modules["requests"] = requests_stub

    if "solders" in sys.modules:
        return

    solders_pkg = types.ModuleType("solders")
    sys.modules["solders"] = solders_pkg

    compute_budget = types.ModuleType("solders.compute_budget")
    compute_budget.set_compute_unit_limit = lambda *args, **kwargs: None
    compute_budget.set_compute_unit_price = lambda *args, **kwargs: None
    sys.modules["solders.compute_budget"] = compute_budget
    solders_pkg.compute_budget = compute_budget

    class _FakeHash:
        @classmethod
        def from_string(cls, _value: str):
            return cls()

    hash_module = types.ModuleType("solders.hash")
    hash_module.Hash = _FakeHash
    sys.modules["solders.hash"] = hash_module
    solders_pkg.hash = hash_module

    instruction_module = types.ModuleType("solders.instruction")
    instruction_module.AccountMeta = type("AccountMeta", (), {})
    instruction_module.Instruction = type("Instruction", (), {})
    sys.modules["solders.instruction"] = instruction_module
    solders_pkg.instruction = instruction_module

    class _FakePubkey:
        def __init__(self, raw: bytes | None = None):
            self._raw = raw or (b"\x00" * 32)

        @classmethod
        def from_string(cls, _value: str):
            return cls()

        def __bytes__(self) -> bytes:
            return self._raw

    pubkey_module = types.ModuleType("solders.pubkey")
    pubkey_module.Pubkey = _FakePubkey
    sys.modules["solders.pubkey"] = pubkey_module
    solders_pkg.pubkey = pubkey_module

    message_module = types.ModuleType("solders.message")
    message_module.MessageV0 = type("MessageV0", (), {})
    sys.modules["solders.message"] = message_module
    solders_pkg.message = message_module

    keypair_module = types.ModuleType("solders.keypair")
    keypair_module.Keypair = type("Keypair", (), {})
    sys.modules["solders.keypair"] = keypair_module
    solders_pkg.keypair = keypair_module

    transaction_module = types.ModuleType("solders.transaction")
    transaction_module.VersionedTransaction = type("VersionedTransaction", (), {})
    sys.modules["solders.transaction"] = transaction_module
    solders_pkg.transaction = transaction_module


_ensure_stubbed_modules()

from backend.services.perps.positions_request import _enc_value


def _enum_types() -> dict:
    return {
        "TestEnum": {
            "kind": "enum",
            "variants": [
                {
                    "name": "WithPayload",
                    "fields": [
                        {"name": "count", "type": "u16"},
                        {"name": "flag", "type": "bool"},
                    ],
                },
                {"name": "WithoutPayload"},
            ],
        }
    }


def test_enum_named_payload_encodes_all_fields():
    types = _enum_types()
    encoded = _enc_value(
        {"defined": "TestEnum"},
        {"WithPayload": {"count": 513, "flag": True}},
        types,
    )

    assert encoded == b"\x00" + (513).to_bytes(2, "little") + b"\x01"


def test_enum_requires_payload_when_fields_present():
    types = _enum_types()

    with pytest.raises(RuntimeError, match="requires payload values"):
        _enc_value({"defined": "TestEnum"}, "WithPayload", types)

import pytest
import importlib
import importlib.util
import sys
import types
from pathlib import Path

from flask import Flask


def load_blueprint():
    base = Path(__file__).resolve().parents[2] / "gpt"
    pkg = types.ModuleType("gpt")
    pkg.__path__ = [str(base)]
    original_gpt = sys.modules.get("gpt")
    sys.modules["gpt"] = pkg

    core_mod = types.ModuleType("gpt.gpt_core")

    class DummyCore:
        expected_strategy = "none"

        def __init__(self, *a, **k):
            self.client = None
            pass

        def analyze(self, instructions: str = "") -> str:
            return "analysis"

        def ask_gpt_about_portfolio(self) -> str:
            return "portfolio"

        def ask_oracle(self, topic: str, strategy_name: str = "none") -> str:
            if topic not in ("portfolio", "positions"):
                raise ValueError("Unknown topic")
            assert strategy_name == self.expected_strategy
            return f"{topic} result"

    core_mod.GPTCore = DummyCore
    original_gpt_core = sys.modules.get("gpt.gpt_core")
    sys.modules["gpt.gpt_core"] = core_mod

    persona_mod = types.ModuleType("oracle_core.persona_manager")

    class DummyPersona:
        def __init__(self, name="test"):
            self.name = name
            self.system_message = "sys"
            self.instructions = "inst"

    class DummyPersonaManager:
        def __init__(self, *a, **k):
            pass

        def get(self, name: str):
            if name != "test":
                raise KeyError(name)
            return DummyPersona(name)

        def list_personas(self):  # ensure compatibility with other tests
            return ["test"]

        def merge_modifiers(self, base, persona):  # pragma: no cover - simple stub
            return base

    persona_mod.PersonaManager = DummyPersonaManager
    persona_mod.Persona = DummyPersona
    original_persona_mod = sys.modules.get("oracle_core.persona_manager")
    sys.modules["oracle_core.persona_manager"] = persona_mod

    oracle_mod = types.ModuleType("oracle_core")

    class DummyOracle:
        DEFAULT_INSTRUCTIONS = {"portfolio": "inst", "positions": "inst"}
        DEFAULT_SYSTEM_MESSAGES = {"portfolio": "sys", "positions": "sys"}

        def __init__(self, *a, **k):
            self.handlers = {
                "portfolio": types.SimpleNamespace(get_context=lambda: {}),
                "positions": types.SimpleNamespace(get_context=lambda: {})
            }
            self.client = None

        def build_prompt(self, topic, ctx, instructions):
            return [
                {"role": "system", "content": "sys"},
                {"role": "system", "content": "{}"},
                {"role": "user", "content": instructions},
            ]

        def query_gpt(self, messages):
            return "oracle_reply"

        def _get_context_and_instructions(self, topic, strategy_name):
            return {}, "inst"

    oracle_mod.OracleCore = DummyOracle
    original_oracle_mod = sys.modules.get("oracle_core")
    sys.modules["oracle_core"] = oracle_mod

    path = base / "gpt_bp.py"
    spec = importlib.util.spec_from_file_location("gpt.gpt_bp", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    return module.gpt_bp, {
        "gpt": original_gpt,
        "gpt.gpt_core": original_gpt_core,
        "oracle_core.persona_manager": original_persona_mod,
        "oracle_core": original_oracle_mod,
    }


@pytest.fixture
def client():
    gpt_bp, originals = load_blueprint()
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(gpt_bp)
    with app.test_client() as client:
        try:
            yield client
        finally:
            for name, mod in originals.items():
                if mod is not None:
                    sys.modules[name] = mod
                else:
                    sys.modules.pop(name, None)


def test_oracle_portfolio_reply(client):
    from gpt.gpt_core import GPTCore as DummyCore
    DummyCore.expected_strategy = "none"
    resp = client.get("/gpt/oracle/portfolio")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "reply" in data


def test_oracle_positions_reply(client):
    from gpt.gpt_core import GPTCore as DummyCore
    DummyCore.expected_strategy = "none"
    resp = client.get("/gpt/oracle/positions")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "reply" in data


def test_oracle_invalid_topic(client):
    resp = client.get("/gpt/oracle/unknown")
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_oracle_with_strategy(client):
    from gpt.gpt_core import GPTCore as DummyCore
    DummyCore.expected_strategy = "test"
    resp = client.get("/gpt/oracle/portfolio?strategy=test")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "reply" in data


def test_oracle_positions_with_strategy(client):
    from gpt.gpt_core import GPTCore as DummyCore
    DummyCore.expected_strategy = "test"
    resp = client.get("/gpt/oracle/positions?strategy=test")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "reply" in data

def test_oracle_query_endpoint(client):
    resp = client.get("/gpt/oracle/query?persona=test")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["reply"] == "oracle_reply"

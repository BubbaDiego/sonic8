import ast
from pathlib import Path

FILE = Path("backend/core/monitor_core/sonic_monitor.py")


def _get_sonic_cycle_node():
    tree = ast.parse(FILE.read_text())
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "sonic_cycle":
            return node
    raise AssertionError("sonic_cycle not found")


def test_sonic_cycle_runs_liquid_monitor():
    node = _get_sonic_cycle_node()
    consts = [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert "liquid_monitor" in consts


def test_sonic_cycle_uses_market_monitor():
    node = _get_sonic_cycle_node()
    consts = [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert "market_monitor" in consts

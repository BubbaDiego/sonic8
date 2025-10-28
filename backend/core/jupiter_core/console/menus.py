from __future__ import annotations

import json
from typing import Optional

from ..config import get_config
from ..services import JupiterService, PositionsService, WalletService
from ..services.positions_bridge import PositionsBridge
from .views import kv_table, panel, rows_table


def _prompt(msg: str, default: Optional[str] = None) -> str:
    hint = f" [{default}]" if default is not None else ""
    val = input(f"{msg}{hint}: ").strip()
    return val or (default or "")


def show_preflight(svc: JupiterService) -> None:
    cfg = svc.describe()
    # Try to show signer info if available; otherwise just config.
    try:
        wallet_info = WalletService().read_signer_info()
    except Exception:
        wallet_info = None
    if wallet_info:
        cfg = {
            **cfg,
            "owner_pubkey": wallet_info["public_key"],
            "signer_path": wallet_info["signer_path"],
        }
    kv_table("🧭 Jupiter Config", cfg)


def menu_wallet_show() -> None:
    try:
        svc = WalletService()
        info = svc.read_signer_info()
        balance = svc.fetch_sol_balance(info["public_key"])
    except Exception as exc:
        panel("Wallet Error", f"{type(exc).__name__}: {exc}")
        return

    rows = {
        "signer_path": info["signer_path"],
        "derivation_path": info["derivation_path"],
        "public_key": info["public_key"],
        "mnemonic_words": info["mnemonic_words"],
        "bip39_passphrase": info["bip39_passphrase"],
    }
    if "error" in balance:
        rows["sol_balance_error"] = balance["error"]
    else:
        rows["lamports"] = balance["lamports"]
        rows["SOL"] = balance["sol"]

    kv_table("👛 Wallet (signer.txt)", rows)


def menu_wallet_balances() -> None:
    try:
        svc = WalletService()
        info = svc.read_signer_info()
    except Exception as exc:
        panel("Balances Error", f"{type(exc).__name__}: {exc}")
        return

    balances = svc.fetch_standard_balances(info["public_key"])

    def _fmt(value: object) -> object:
        if isinstance(value, dict):
            if "uiAmount" in value:
                return value["uiAmount"]
            if "sol" in value:
                return value["sol"]
        return value

    rows = [[token, _fmt(result)] for token, result in balances.items()]
    rows_table("💰 Wallet Balances (SOL + SPL)", ["Token", "Amount (UI)"], rows)
    panel("Balances (raw)", json.dumps(balances, indent=2)[:4000])


def menu_positions_core() -> None:
    """Show ACTIVE PositionCore rows, syncing once if empty."""

    try:
        wallet_service = WalletService()
        signer_info = wallet_service.read_signer_info()
        owner_pubkey = signer_info["public_key"]
    except Exception:
        owner_pubkey = None

    bridge = PositionsBridge()
    out = bridge.list_active_positions(owner_pubkey=owner_pubkey, sync_if_empty=True)
    positions = out.get("positions") or []
    filtered_by = out.get("filtered_by") or "—"
    synced = bool(out.get("synced"))

    if not positions:
        kv_table(
            "📈 Open Perps Positions (PositionCore)",
            {
                "filtered_by_wallet": filtered_by,
                "synced_now": synced,
                "count": 0,
            },
        )
        panel("Positions", "No ACTIVE positions found.")
        return

    rows = []
    for pos in positions:
        rows.append(
            [
                pos.get("wallet_name") or pos.get("wallet") or "?",
                pos.get("asset_type")
                or pos.get("asset")
                or pos.get("market")
                or "?",
                pos.get("position_type") or pos.get("side") or "?",
                pos.get("size")
                or pos.get("contracts")
                or pos.get("positionSize")
                or "?",
                pos.get("entry_price")
                or pos.get("avg_entry")
                or pos.get("avg_price")
                or "?",
                pos.get("liquidation_price")
                or pos.get("liqPrice")
                or pos.get("liquidation")
                or "?",
                pos.get("pnl_after_fees_usd")
                or pos.get("pnl")
                or pos.get("unrealizedPnl")
                or "?",
                pos.get("last_updated") or pos.get("updatedAt") or pos.get("ts") or "—",
            ]
        )

    rows_table(
        "📈 Open Perps Positions (PositionCore)",
        ["wallet", "asset", "side", "size", "entry", "liq", "pnl", "updated"],
        rows,
    )
    kv_table("Source", {"filtered_by_wallet": filtered_by, "synced_now": synced})


def menu_quote(svc: JupiterService) -> None:
    cfg = get_config()
    input_mint = _prompt("Input mint", cfg.default_input_mint)
    output_mint = _prompt("Output mint", cfg.default_output_mint)
    amount = int(_prompt("Amount (atomic units)", "1000000"))
    slippage = int(_prompt("Slippage (bps)", "50"))
    res = svc.quote(input_mint=input_mint, output_mint=output_mint, amount=amount, slippage_bps=slippage)
    summary = {
        "in": res.input_mint,
        "out": res.output_mint,
        "amount": res.amount,
        "outAmount": res.raw.get("outAmount"),
        "priceImpactPct": res.raw.get("priceImpactPct") or res.raw.get("priceImpact"),
        "routePlanLen": len(res.raw.get("routePlan", []) or res.raw.get("routes", [])),
    }
    kv_table("🧮 Quote Result", summary)
    panel("Quote (raw)", json.dumps(res.raw, indent=2)[:4000])


def menu_ultra_order(svc: JupiterService) -> None:
    cfg = get_config()
    input_mint = _prompt("Input mint", cfg.default_input_mint)
    output_mint = _prompt("Output mint", cfg.default_output_mint)
    amount = int(_prompt("Amount (atomic units)", "1000000"))
    slippage = int(_prompt("Slippage (bps)", "50"))
    owner = _prompt("Owner public key (optional)", "")
    res = svc.ultra_order(
        input_mint=input_mint,
        output_mint=output_mint,
        amount=amount,
        slippage_bps=slippage,
        user_public_key=owner or None,
    )
    tx_b64 = res.get_serialized_tx_b64()
    kv_table(
        "🧱 Ultra Order Built",
        {
            "tx_base64_present": bool(tx_b64),
            "input_mint": res.input_mint,
            "output_mint": res.output_mint,
            "amount": res.amount,
            "slippage_bps": res.slippage_bps,
        },
    )
    if tx_b64:
        panel(
            "Serialized Transaction (base64)",
            (tx_b64[:2400] + "...") if len(tx_b64) > 2400 else tx_b64,
        )


def menu_ultra_execute(svc: JupiterService) -> None:
    tx_b64 = _prompt("Paste SIGNED transaction (base64)", "")
    if not tx_b64:
        panel("Error", "No signed transaction provided.")
        return
    res = svc.ultra_execute(signed_tx_base64=tx_b64)
    kv_table(
        "🚀 Execute Result",
        {
            "signature": res.signature,
            "ok": bool(res.signature),
        },
    )
    panel("Execute (raw)", json.dumps(res.raw, indent=2)[:4000])


def menu_trigger_list(svc: JupiterService) -> None:
    owner = _prompt("Owner public key", "")
    raw = svc.trigger_list(owner=owner)
    orders = raw.get("orders") or raw.get("data") or []
    rows = []
    for o in orders:
        rows.append(
            [
                o.get("id") or o.get("orderId") or "?",
                o.get("market") or o.get("pair") or "?",
                o.get("side") or "?",
                o.get("price") or o.get("triggerPrice") or "?",
                o.get("remaining") or o.get("remainingAmount") or "?",
                o.get("status") or "?",
            ]
        )
    rows_table("⏱ Trigger Orders", ["id", "market", "side", "price", "remaining", "status"], rows)
    panel("Orders (raw)", json.dumps(raw, indent=2)[:4000])


def menu_trigger_cancel(svc: JupiterService) -> None:
    payload_raw = _prompt("Cancel payload JSON (id + owner + ...)", "")
    try:
        payload = json.loads(payload_raw)
    except Exception as exc:
        panel("Error", f"Invalid JSON: {exc}")
        return
    raw = svc.trigger_cancel(payload)
    panel("Cancel (raw)", json.dumps(raw, indent=2)[:4000])


def menu_trigger_create(svc: JupiterService) -> None:
    payload_raw = _prompt("Create payload JSON", "")
    try:
        payload = json.loads(payload_raw)
    except Exception as exc:
        panel("Error", f"Invalid JSON: {exc}")
        return
    raw = svc.trigger_create(payload)
    panel("Create (raw)", json.dumps(raw, indent=2)[:4000])


def menu_positions_probe() -> None:
    try:
        svc = WalletService()
        info = svc.read_signer_info()
    except Exception as exc:
        panel("Positions Error", f"{type(exc).__name__}: {exc}")
        return

    positions_service = PositionsService()
    result = positions_service.probe_positions(owner_pubkey=info["public_key"])
    if "error" in result:
        panel("Positions", result["error"])
        return

    positions = result.get("positions", [])
    if not isinstance(positions, list):
        positions = [positions]
    rows = []
    for pos in positions:
        rows.append(
            [
                pos.get("market") or pos.get("symbol") or "?",
                pos.get("side") or "?",
                pos.get("size")
                or pos.get("contracts")
                or pos.get("positionSize")
                or "?",
                pos.get("entryPrice") or pos.get("avgEntry") or "?",
                pos.get("liqPrice") or pos.get("liquidation") or "?",
                pos.get("pnl") or pos.get("unrealizedPnl") or "?",
                pos.get("updatedAt") or pos.get("ts") or "?",
            ]
        )

    rows_table(
        "📈 Open Perps Positions (Probe)",
        ["market", "side", "size", "entry", "liq", "pnl", "updated"],
        rows,
    )
    kv_table("Source", {"endpoint": result.get("endpoint", "?"), "owner": info["public_key"]})

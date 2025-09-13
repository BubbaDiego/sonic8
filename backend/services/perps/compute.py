from __future__ import annotations

import math
import requests
from typing import Any, Dict, Optional

Q64 = 2 ** 64

def _num(x: Any) -> Optional[float]:
    try:
        if x is None: return None
        if isinstance(x, (int, float)): return float(x)
        if isinstance(x, str):
            s = x.strip()
            if s.lower().startswith("0x"):  # hex strings
                return float(int(s, 16))
            return float(s)
        v = getattr(x, "value", None)  # some anchor wrappers
        return float(v) if v is not None else None
    except Exception:
        return None

def _q64_to_float(v: Any) -> Optional[float]:
    n = _num(v)
    if n is None: return None
    # if it looks too large to be a spot price, assume Q64.64
    return n / Q64 if n > 1e9 else n

def _decimals_from(pos: Dict[str, Any]) -> int:
    for k in ("decimals", "baseDecimals", "assetDecimals"):
        if k in pos:
            try: return int(pos[k])
            except Exception: pass
    return 9

def extract_fields(pos: Dict[str, Any]) -> Dict[str, Any]:
    # side
    side: Optional[str] = None
    if "isLong" in pos:
        side = "LONG" if bool(pos["isLong"]) else "SHORT"
    elif "side" in pos:
        v = pos["side"]
        try:
            vi = int(v); side = "LONG" if vi > 0 else "SHORT"
        except Exception:
            s = str(v).lower()
            side = "LONG" if "long" in s else "SHORT" if "short" in s else None

    # size (atoms)
    size_atoms = None
    for k in ("size", "baseSize", "qty", "quantity", "positionSize"):
        if k in pos:
            size_atoms = _num(pos[k])
            if size_atoms is not None:
                break

    decs = _decimals_from(pos)
    size_ui = size_atoms / (10 ** decs) if size_atoms is not None else None

    # entry price
    entry = None
    for k in ("entryPrice", "avgEntryPrice", "openPrice"):
        if k in pos:
            entry = _num(pos[k])
            if entry is not None: break
    if entry is None and "entryPriceX64" in pos:
        entry = _q64_to_float(pos["entryPriceX64"])

    # mint (optional)
    base_mint = None
    for k in ("assetMint", "baseMint", "mint", "tokenMint"):
        if k in pos and pos[k]:
            base_mint = str(pos[k]); break

    return {"side": side, "sizeUi": size_ui, "entryPx": entry, "decimals": decs, "baseMint": base_mint}

def get_mark_price_usdc(mint: Optional[str]) -> Optional[float]:
    if not mint: return None
    try:
        r = requests.get("https://price.jup.ag/v6/price", params={"ids": mint, "vsToken": "USDC"}, timeout=8)
        r.raise_for_status()
        data = r.json().get("data", {})
        if mint in data and "price" in data[mint]:
            return float(data[mint]["price"])
        if data:  # fallback: first item
            return float(next(iter(data.values())).get("price"))
    except Exception:
        return None
    return None

def est_pnl_usd(side: Optional[str], size_ui: Optional[float],
                entry_px: Optional[float], mark_px: Optional[float]) -> Optional[float]:
    if None in (side, size_ui, entry_px, mark_px): return None
    dirn = 1.0 if side == "LONG" else -1.0
    return (mark_px - entry_px) * size_ui * dirn

from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from ..config import get_config
from .audit_service import AuditService
from .wallet_service import WalletService


@dataclass
class TPSLRequest:
    owner_pubkey: str
    market_symbol: str
    is_long: bool
    trigger_price_usd: int
    entire_position: bool
    size_usd_delta: Optional[int] = None
    kind: str = "tp"


class PerpsManageService:
    """
    Orchestrate TP/SL attachments by delegating the heavy lifting to a native
    executable (``NATIVE_PERPS_EXEC``).

    The native client returns an unsigned transaction (base64). We try to sign and
    submit it locally; otherwise the console falls back to manual signing.
    """

    def __init__(self, locker: Any = None) -> None:
        self.cfg = get_config()
        self.audit = AuditService(self.cfg, locker=locker)
        self.wallet = WalletService(self.cfg)

    # ---- public ---------------------------------------------------------
    def attach_tp_or_sl(self, req: TPSLRequest) -> Dict[str, Any]:
        payload = {
            "op": "attach_tpsl",
            "params": {
                "owner": req.owner_pubkey,
                "marketSymbol": req.market_symbol,
                "isLong": req.is_long,
                "triggerPriceUsdAtomic": str(req.trigger_price_usd),
                "entirePosition": bool(req.entire_position),
                "sizeUsdDelta": str(req.size_usd_delta)
                if req.size_usd_delta is not None
                else None,
                "kind": req.kind,
            },
        }

        unsigned_b64, request_pda = self._call_native(payload)
        self.audit.log(
            kind=f"perps_{req.kind}_create",
            status="built",
            request=payload,
            response={"requestPda": request_pda},
        )

        # Try to sign locally. If unavailable return the unsigned tx so the console can
        # prompt the operator for a manual signature.
        try:
            signed_b64 = self.wallet.sign_tx_base64(unsigned_b64)
        except Exception as exc:
            return {
                "unsignedTxBase64": unsigned_b64,
                "requestPda": request_pda,
                "needsSigning": True,
                "why": f"{type(exc).__name__}: {exc}",
            }

        signature = self.wallet.submit_signed_tx(signed_b64)
        self.audit.log(
            kind="perps_submit",
            status="ok",
            response={"signature": signature, "requestPda": request_pda},
        )
        return {
            "signature": signature,
            "requestPda": request_pda,
            "needsSigning": False,
        }

    # ---- helpers --------------------------------------------------------
    def _native_exec(self) -> Tuple[str, ...]:
        path = os.getenv("NATIVE_PERPS_EXEC")
        if not path:
            raise RuntimeError(
                "NATIVE_PERPS_EXEC not set. Point it to a script that returns unsigned tx base64 JSON."
            )
        return tuple(shlex.split(path))

    def _call_native(self, body: Dict[str, Any]) -> Tuple[str, Optional[str]]:
        cmd = self._native_exec()
        proc = subprocess.run(  # noqa: S603,S607 - intentional exec of trusted script
            cmd,
            input=json.dumps(body).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )
        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="ignore")
            raise RuntimeError(f"Native client failed: {stderr}")
        try:
            payload = json.loads(proc.stdout.decode("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"Native client returned non-JSON: {exc}") from exc

        unsigned_b64 = (
            payload.get("unsignedTxBase64")
            or payload.get("transaction")
            or payload.get("tx")
        )
        if not unsigned_b64:
            raise RuntimeError("Native client did not return 'unsignedTxBase64'")
        request_pda = payload.get("requestPda")
        return unsigned_b64, request_pda

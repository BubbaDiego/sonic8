from __future__ import annotations

import json
import os
import subprocess
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import get_config
from .wallet_service import WalletService
from .audit_service import AuditService


@dataclass
class TPSLRequest:
    owner_pubkey: str
    market_symbol: str
    is_long: bool
    trigger_price_usd: int
    entire_position: bool
    size_usd_delta: Optional[int] = None
    kind: str = "tp"  # "tp" | "sl"
    context: Optional[Dict[str, Any]] = None   # <-- position row, PDAs, etc.


class PerpsManageService:
    """
    TP/SL orchestrator:
      - calls native builder (Anchor) to build real PositionRequest (Trigger)
      - signs in Python if possible, else accepts native-signed or manual paste
    """

    def __init__(self, locker: Any = None) -> None:
        self.cfg = get_config()
        self.audit = AuditService(self.cfg, locker=locker)
        self.wallet = WalletService(self.cfg)

    def attach_tp_or_sl(self, req: TPSLRequest) -> Dict[str, Any]:
        body = {
            "op": "attach_tpsl",
            "params": {
                "owner": req.owner_pubkey,
                "marketSymbol": req.market_symbol,
                "isLong": req.is_long,
                "triggerPriceUsdAtomic": str(req.trigger_price_usd),
                "entirePosition": bool(req.entire_position),
                "sizeUsdDelta": str(req.size_usd_delta) if req.size_usd_delta is not None else None,
                "kind": req.kind,
            },
            "context": req.context or {},   # pass position row
        }
        native_out = self._call_native(body)
        unsigned_b64 = native_out.get("unsignedTxBase64")
        request_pda = native_out.get("requestPda")

        # If native already signed, submit immediately
        signed_b64 = native_out.get("signedTxBase64")
        if signed_b64:
            sig = self.wallet.submit_signed_tx(signed_b64)
            self.audit.log(kind=f"perps_{req.kind}_create", status="built", request=body, response={"requestPda": request_pda})
            self.audit.log(kind="perps_submit", status="ok", response={"signature": sig, "requestPda": request_pda})
            return {"signature": sig, "requestPda": request_pda, "needsSigning": False}

        # Try to sign in Python
        try:
            signed_b64 = self.wallet.sign_tx_base64(unsigned_b64)
        except Exception as e:
            self.audit.log(kind=f"perps_{req.kind}_create", status="built", request=body, response={"requestPda": request_pda})
            return {"unsignedTxBase64": unsigned_b64, "requestPda": request_pda, "needsSigning": True, "why": f"{type(e).__name__}: {e}"}

        sig = self.wallet.submit_signed_tx(signed_b64)
        self.audit.log(kind="perps_submit", status="ok", response={"signature": sig, "requestPda": request_pda})
        return {"signature": sig, "requestPda": request_pda, "needsSigning": False}

    # ---------------- helpers ----------------
    def _resolve_native(self) -> list[str]:
        exec_cmd = os.getenv("NATIVE_PERPS_EXEC", "node").strip()
        script = os.getenv("NATIVE_PERPS_SCRIPT", "").strip()
        if not script:
            here = Path(__file__).resolve()
            script = str(here.parents[3] / "native" / "perps_client" / "cli.mjs")
        extra = os.getenv("NATIVE_PERPS_ARGS", "").strip()
        argv = [exec_cmd, script]
        if extra:
            argv.extend(shlex.split(extra, posix=(os.name != "nt")))
        return argv

    def _call_native(self, body: Dict[str, Any]) -> Dict[str, Any]:
        argv = self._resolve_native()
        # Merge current process env + explicit perps hints from config
        env = os.environ.copy()
        cfg = self.cfg
        if cfg.perps_program_id:
            env["JUP_PERPS_PROGRAM_ID"] = cfg.perps_program_id
        if cfg.perps_idl_path:
            env["JUP_PERPS_IDL"] = cfg.perps_idl_path
        if cfg.perps_method_trigger:
            env["JUP_PERPS_METHOD_TRIGGER"] = cfg.perps_method_trigger
        # Also forward RPC if set
        if cfg.solana_rpc_url:
            env["SOLANA_RPC_URL"] = cfg.solana_rpc_url

        proc = subprocess.run(
            argv,
            input=json.dumps(body).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
            shell=False,
            env=env,  # <-- ensure Node sees the values
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Native client failed: {proc.stderr.decode('utf-8', errors='ignore')}")
        try:
            return json.loads(proc.stdout.decode("utf-8"))
        except Exception as e:
            raise RuntimeError(f"Native client returned non-JSON: {e}")

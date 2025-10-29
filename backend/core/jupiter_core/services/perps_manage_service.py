from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

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
    kind: str = "tp"  # "tp" | "sl"


class PerpsManageService:
    """
    TP/SL orchestrator:
    - calls a 'native' perps client to build an unsigned base64 tx
      (envs: NATIVE_PERPS_EXEC, NATIVE_PERPS_SCRIPT, NATIVE_PERPS_ARGS)
    - signs & submits if Python has signing libs; else returns unsigned for manual signing
    """

    def __init__(self, locker: Any = None) -> None:
        self.cfg = get_config()
        self.audit = AuditService(self.cfg, locker=locker)
        self.wallet = WalletService(self.cfg)

    # ---- public -------------------------------------------------------------
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

        # Try to sign in Python
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

    # ---- helpers ------------------------------------------------------------
    def _resolve_native(self) -> list[str]:
        """
        Build the argv list to exec the native client robustly on Windows/Unix.

        Accepted envs:
          - NATIVE_PERPS_EXEC   e.g., "node" (default: node)
          - NATIVE_PERPS_SCRIPT e.g., "C:\\sonic7\\native\\perps_client\\cli.mjs"
          - NATIVE_PERPS_ARGS   optional extra args string
        Also supports legacy single var usage where EXEC points to the .mjs directly.
        """

        exec_cmd = os.getenv("NATIVE_PERPS_EXEC", "").strip()
        script = os.getenv("NATIVE_PERPS_SCRIPT", "").strip()
        extra = os.getenv("NATIVE_PERPS_ARGS", "").strip()

        # Legacy: if EXEC ends with .js/.mjs, treat it as script path; default exec to 'node'
        if not script and exec_cmd.lower().endswith((".js", ".mjs")):
            script = exec_cmd
            exec_cmd = "node"

        # Defaults
        if not exec_cmd:
            exec_cmd = "node"
        if not script:
            # Try repo default: <repo>/native/perps_client/cli.mjs
            here = Path(__file__).resolve()
            script = str(here.parents[3] / "native" / "perps_client" / "cli.mjs")

        argv: list[str] = [exec_cmd, script]

        if extra:
            # windows-aware split
            posix = os.name != "nt"
            argv.extend(shlex.split(extra, posix=posix))

        return argv

    def _call_native(self, body: Dict[str, Any]) -> tuple[str, Optional[str]]:
        argv = self._resolve_native()
        try:
            proc = subprocess.run(  # noqa: S603,S607 - intentional exec of trusted script
                argv,
                input=json.dumps(body).encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=None,
                timeout=120,
                shell=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(f"Native client exec not found: {argv[0]} ({exc})") from exc

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

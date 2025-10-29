from __future__ import annotations

import json
import os
import shlex
import subprocess
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
    context: Optional[Dict[str, Any]] = None


class PerpsManageService:
    """
    TP/SL orchestrator: calls native perps client (Node/Anchor), tries to sign & submit,
    and emits rich debug if anything fails.
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
        native = self._call_native(body)
        unsigned_b64 = native.get("unsignedTxBase64")
        request_pda = native.get("requestPda")

        # If native already signed, submit that directly.
        signed_b64 = native.get("signedTxBase64")
        if signed_b64:
            sig = self.wallet.submit_signed_tx(signed_b64)
            self.audit.log(kind=f"perps_{req.kind}_create", status="built", request=body, response={"requestPda": request_pda})
            self.audit.log(kind="perps_submit", status="ok", response={"signature": sig, "requestPda": request_pda})
            return {"signature": sig, "requestPda": request_pda, "needsSigning": False}

        # Otherwise try to sign in Python
        try:
            signed_b64 = self.wallet.sign_tx_base64(unsigned_b64)
        except Exception as e:
            self.audit.log(kind=f"perps_{req.kind}_create", status="built", request=body, response={"requestPda": request_pda})
            return {
                "unsignedTxBase64": unsigned_b64,
                "requestPda": request_pda,
                "needsSigning": True,
                "why": f"{type(e).__name__}: {e}",
            }

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

        # Merge env and forward perps hints explicitly so Node ALWAYS sees them.
        env = os.environ.copy()
        cfg = self.cfg

        def _cfg(attr: str) -> Optional[str]:
            # Safe getattr, even if config lacks the field.
            try:
                return getattr(cfg, attr)
            except Exception:
                return None

        # Prefer config values if present; otherwise keep existing env.
        env["JUP_PERPS_PROGRAM_ID"] = _cfg("perps_program_id") or env.get("JUP_PERPS_PROGRAM_ID", "")
        env["JUP_PERPS_IDL"] = _cfg("perps_idl_path") or env.get("JUP_PERPS_IDL", "")
        env["JUP_PERPS_METHOD_TRIGGER"] = _cfg("perps_method_trigger") or env.get("JUP_PERPS_METHOD_TRIGGER", "")
        env["SOLANA_RPC_URL"] = getattr(cfg, "solana_rpc_url", None) or env.get("SOLANA_RPC_URL", "")

        # Bubble full debug when DEBUG_NATIVE=1
        if os.getenv("DEBUG_NATIVE", "") == "1":
            env["DEBUG_NATIVE"] = "1"

        try:
            proc = subprocess.run(
                argv,
                input=json.dumps(body).encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=None,
                timeout=240,
                shell=False,
                env=env,
            )
        except FileNotFoundError as e:
            raise RuntimeError(f"Native exec not found. ARGV={argv} :: {e}")

        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="ignore")
            stdout = proc.stdout.decode("utf-8", errors="ignore")
            # Surface EVERYTHING so we stop guessing
            raise RuntimeError(
                "Native client failed\n"
                f"ARGV: {argv}\n"
                f"ENV(perps): program_id={env.get('JUP_PERPS_PROGRAM_ID')!r} "
                f"idl={env.get('JUP_PERPS_IDL')!r} method={env.get('JUP_PERPS_METHOD_TRIGGER')!r} "
                f"rpc={env.get('SOLANA_RPC_URL')!r}\n"
                f"STDERR:\n{stderr}\n"
                f"STDOUT:\n{stdout}\n"
            )

        try:
            return json.loads(proc.stdout.decode("utf-8"))
        except Exception as e:
            raise RuntimeError(
                f"Native client returned non-JSON. ARGV={argv}\n"
                f"ENV(perps): program_id={env.get('JUP_PERPS_PROGRAM_ID')!r} idl={env.get('JUP_PERPS_IDL')!r} "
                f"method={env.get('JUP_PERPS_METHOD_TRIGGER')!r}\n"
                f"STDOUT(raw)={proc.stdout[:4000]!r}\n"
                f"{type(e).__name__}: {e}"
            )

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
    TP/SL orchestrator:
    - calls native perps client to build (and optionally sign) a tx
    - tries Python signing; if that fails, automatically retries with native signing
    - submits on success; only asks user to paste as a last resort
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
            "context": req.context or {},
        }

        # 1) First native call (may already be signed if NATIVE_SIGNER=1 in env)
        native_out = self._call_native(body)
        unsigned_b64 = native_out.get("unsignedTxBase64")
        request_pda = native_out.get("requestPda")

        # If native already signed, submit directly
        if native_out.get("signedTxBase64"):
            sig = self.wallet.submit_signed_tx(native_out["signedTxBase64"])
            self.audit.log(kind=f"perps_{req.kind}_create", status="built", request=body, response={"requestPda": request_pda})
            self.audit.log(kind="perps_submit", status="ok", response={"signature": sig, "requestPda": request_pda})
            return {"signature": sig, "requestPda": request_pda, "needsSigning": False}

        # 2) Try Python signer
        try:
            signed_b64 = self.wallet.sign_tx_base64(unsigned_b64)
            sig = self.wallet.submit_signed_tx(signed_b64)
            self.audit.log(kind=f"perps_{req.kind}_create", status="built", request=body, response={"requestPda": request_pda})
            self.audit.log(kind="perps_submit", status="ok", response={"signature": sig, "requestPda": request_pda})
            return {"signature": sig, "requestPda": request_pda, "needsSigning": False}
        except Exception as py_err:
            # 3) Python signer failed → automatically retry with native signing
            signer_path = self._resolve_signer_path_for_native()
            try_native = self._call_native(body, env_override={"NATIVE_SIGNER": "1", "SIGNER_PATH": signer_path})
            if try_native.get("signedTxBase64"):
                sig = self.wallet.submit_signed_tx(try_native["signedTxBase64"])
                resolved_request_pda = try_native.get("requestPda") or request_pda
                self.audit.log(kind=f"perps_{req.kind}_create", status="built", request=body, response={"requestPda": resolved_request_pda})
                self.audit.log(kind="perps_submit", status="ok", response={"signature": sig, "requestPda": resolved_request_pda})
                return {"signature": sig, "requestPda": resolved_request_pda, "needsSigning": False}

            # 4) Last resort: return unsigned for manual paste
            self.audit.log(kind=f"perps_{req.kind}_create", status="built", request=body, response={"requestPda": request_pda})
            return {
                "unsignedTxBase64": unsigned_b64,
                "requestPda": request_pda,
                "needsSigning": True,
                "why": f"Python signing failed ({type(py_err).__name__}); native signing unavailable",
            }

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

    def _call_native(self, body: Dict[str, Any], env_override: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
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

        if env_override:
            env.update(env_override)

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

    def _resolve_signer_path_for_native(self) -> str:
        # Reuse WalletService path resolution via read_signer_info
        try:
            info = self.wallet.read_signer_info()
            return info.get("signer_path") or "signer.txt"
        except Exception:
            return os.getenv("SIGNER_PATH", "signer.txt")

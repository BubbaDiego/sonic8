from __future__ import annotations

from typing import Any, Dict, Optional

import requests

from ..clients import JupSwapClient, JupTriggerClient, JupUltraClient
from ..config import JupiterConfig, get_config
from ..models import ExecuteResult, QuoteResult, UltraOrderResult
from .audit_service import AuditService


class JupiterService:
    """Facade for interacting with Jupiter APIs and audit logging."""

    def __init__(
        self,
        cfg: Optional[JupiterConfig] = None,
        locker: Any = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.cfg = cfg or get_config()
        self.session = session or requests.Session()
        self.audit = AuditService(self.cfg, locker=locker)
        self.swap = JupSwapClient(self.cfg, session=self.session)
        self.ultra = JupUltraClient(self.cfg, session=self.session)
        self.trigger = JupTriggerClient(self.cfg, session=self.session)

    # ------------------------
    # Health / config surface
    # ------------------------
    def describe(self) -> Dict[str, Any]:
        return {
            "tier": self.cfg.tier,
            "use_ultra": self.cfg.use_ultra,
            "ultra_base": self.cfg.ultra_base,
            "swap_base": self.cfg.swap_base,
            "trigger_base": self.cfg.trigger_base,
            "mother_db_path": self.cfg.mother_db_path,
        }

    # -------------
    # Quotes / Swap
    # -------------
    def quote(
        self,
        *,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50,
    ) -> QuoteResult:
        payload = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount,
            "slippageBps": slippage_bps,
        }
        try:
            raw = self.swap.get_quote(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount,
                slippage_bps=slippage_bps,
            )
            self.audit.log(kind="quote", status="ok", request=payload, response=raw)
            return QuoteResult(input_mint=input_mint, output_mint=output_mint, amount=amount, raw=raw)
        except Exception as exc:  # pragma: no cover - network failures vary
            self.audit.log(kind="quote", status="error", request=payload, response={"error": str(exc)})
            raise

    # -----------
    # Ultra flow
    # -----------
    def ultra_order(
        self,
        *,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50,
        user_public_key: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> UltraOrderResult:
        body = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount,
            "slippageBps": slippage_bps,
            "userPublicKey": user_public_key,
        }
        try:
            raw = self.ultra.order(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount,
                slippage_bps=slippage_bps,
                user_public_key=user_public_key,
                extra=extra,
            )
            self.audit.log(kind="ultra_order", status="ok", request=body, response=raw)
            return UltraOrderResult(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount,
                slippage_bps=slippage_bps,
                raw=raw,
            )
        except Exception as exc:  # pragma: no cover - network failures vary
            self.audit.log(kind="ultra_order", status="error", request=body, response={"error": str(exc)})
            raise

    def ultra_execute(self, *, signed_tx_base64: str) -> ExecuteResult:
        try:
            raw = self.ultra.execute(signed_tx_base64=signed_tx_base64)
            sig = raw.get("signature") or raw.get("txid") or raw.get("result", {}).get("signature")
            self.audit.log(kind="ultra_execute", status="ok", response=raw, signature=sig)
            return ExecuteResult(signature=sig, raw=raw)
        except Exception as exc:  # pragma: no cover - network failures vary
            self.audit.log(kind="ultra_execute", status="error", response={"error": str(exc)})
            raise

    # ----------
    # Triggers
    # ----------
    def trigger_list(self, *, owner: str) -> Dict[str, Any]:
        raw = self.trigger.list_orders(owner=owner)
        self.audit.log(kind="trigger_list", status="ok", request={"owner": owner}, response=raw)
        return raw

    def trigger_create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raw = self.trigger.create_order(payload)
        self.audit.log(kind="trigger_create", status="ok", request=payload, response=raw)
        return raw

    def trigger_cancel(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raw = self.trigger.cancel_order(payload)
        self.audit.log(kind="trigger_cancel", status="ok", request=payload, response=raw)
        return raw

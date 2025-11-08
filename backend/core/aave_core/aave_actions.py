from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from web3 import Web3  # type: ignore

from .aave_client import AaveGraphQLClient
from .aave_config import AaveConfig

log = logging.getLogger(__name__)


# ---------------- data shapes ----------------

@dataclass
class TxRequest:
    to: str
    data: str
    value: int | None = None


@dataclass
class ExecutionPlan:
    """Execution plan from Aave GraphQL: optional approval + primary tx."""
    approval: Optional[TxRequest]
    primary: TxRequest


# ---------------- mapping helpers ----------------

def _map_tx(obj: Dict[str, Any]) -> TxRequest:
    return TxRequest(
        to=obj.get("to"),
        data=obj.get("data"),
        value=int(obj.get("value", 0)) if obj.get("value") is not None else None,
    )


def _map_plan(obj: Dict[str, Any]) -> ExecutionPlan:
    t = obj.get("__typename")
    if t == "TransactionRequest":
        return ExecutionPlan(approval=None, primary=_map_tx(obj))
    if t == "ApprovalRequired":
        return ExecutionPlan(
            approval=_map_tx(obj.get("approval", {})),
            primary=_map_tx(obj.get("originalTransaction", {})),
        )
    if t == "InsufficientBalanceError":
        required = ((obj.get("required") or {}).get("value"))
        raise RuntimeError(f"Aave: Insufficient balance for requested operation (need {required}).")
    raise RuntimeError(f"Aave: Unexpected plan typename: {t}")


# ---------------- tx executor ----------------

class EthereumTxExecutor:
    """Minimal tx sender for EVM networks (Polygon)."""

    def __init__(self, cfg: AaveConfig, private_key: str):
        if cfg.evm_rpc_url == "MISSING":
            raise RuntimeError("EVM_RPC_URL is not configured.")
        self.w3 = Web3(Web3.HTTPProvider(cfg.evm_rpc_url))
        self.acct = self.w3.eth.account.from_key(private_key)
        self.chain_id = cfg.chain_id

    def _send(self, req: TxRequest) -> str:
        nonce = self.w3.eth.get_transaction_count(self.acct.address)
        tx = {
            "to": Web3.to_checksum_address(req.to),
            "data": req.data,
            "value": req.value or 0,
            "nonce": nonce,
            "chainId": self.chain_id,
            "gasPrice": self.w3.eth.gas_price,
        }
        est = self.w3.eth.estimate_gas({"to": tx["to"], "data": tx["data"], "from": self.acct.address, "value": tx["value"]})
        tx["gas"] = int(est * 12 // 10)  # +20%
        signed = self.acct.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    def execute_plan(self, plan: ExecutionPlan) -> List[str]:
        hashes: List[str] = []
        if plan.approval:
            hashes.append(self._send(plan.approval))
        hashes.append(self._send(plan.primary))
        return hashes


# ---------------- public actions ----------------


def _get_pk() -> str:
    pk = os.getenv("EVM_PRIVATE_KEY")
    if not pk or pk.strip() == "":
        raise RuntimeError("EVM_PRIVATE_KEY not set; required for sending transactions.")
    return pk


def _ensure_market(cfg: AaveConfig, market: Optional[str]) -> Optional[str]:
    return market or cfg.pool


def plan_supply(cfg: AaveConfig, *, user: str, reserve: str, amount: str, market: Optional[str] = None) -> ExecutionPlan:
    client = AaveGraphQLClient(cfg)
    resp = client.plan_supply(market=_ensure_market(cfg, market), user=user, reserve=reserve, amount=amount)
    return _map_plan(resp)


def plan_withdraw(cfg: AaveConfig, *, user: str, reserve: str, amount: str, market: Optional[str] = None) -> ExecutionPlan:
    client = AaveGraphQLClient(cfg)
    resp = client.plan_withdraw(market=_ensure_market(cfg, market), user=user, reserve=reserve, amount=amount)
    return _map_plan(resp)


def plan_borrow(cfg: AaveConfig, *, user: str, reserve: str, amount: str, market: Optional[str] = None) -> ExecutionPlan:
    client = AaveGraphQLClient(cfg)
    resp = client.plan_borrow(market=_ensure_market(cfg, market), user=user, reserve=reserve, amount=amount)
    return _map_plan(resp)


def plan_repay(cfg: AaveConfig, *, user: str, reserve: str, amount: str, market: Optional[str] = None) -> ExecutionPlan:
    client = AaveGraphQLClient(cfg)
    resp = client.plan_repay(market=_ensure_market(cfg, market), user=user, reserve=reserve, amount=amount)
    return _map_plan(resp)


def send_plan(cfg: AaveConfig, plan: ExecutionPlan) -> List[str]:
    pk = _get_pk()
    execu = EthereumTxExecutor(cfg, pk)
    return execu.execute_plan(plan)


# Convenience: plan + send in one call


def supply(cfg: AaveConfig, *, user: str, reserve: str, amount: str, market: Optional[str] = None) -> List[str]:
    return send_plan(cfg, plan_supply(cfg, user=user, reserve=reserve, amount=amount, market=market))


def withdraw(cfg: AaveConfig, *, user: str, reserve: str, amount: str, market: Optional[str] = None) -> List[str]:
    return send_plan(cfg, plan_withdraw(cfg, user=user, reserve=reserve, amount=amount, market=market))


def borrow(cfg: AaveConfig, *, user: str, reserve: str, amount: str, market: Optional[str] = None) -> List[str]:
    return send_plan(cfg, plan_borrow(cfg, user=user, reserve=reserve, amount=amount, market=market))


def repay(cfg: AaveConfig, *, user: str, reserve: str, amount: str, market: Optional[str] = None) -> List[str]:
    return send_plan(cfg, plan_repay(cfg, user=user, reserve=reserve, amount=amount, market=market))

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from web3 import Web3  # type: ignore

from .aave_config import AaveConfig

log = logging.getLogger(__name__)


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
        tx["gas"] = int(est * 1.2)
        signed = self.acct.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    def execute_plan(self, plan: ExecutionPlan) -> List[str]:
        hashes: List[str] = []
        if plan.approval:
            hashes.append(self._send(plan.approval))
        hashes.append(self._send(plan.primary))
        return hashes


# NOTE: The actual preparation of ExecutionPlan objects comes from Aave GraphQL
# (supply/borrow/withdraw/repay mutations). We keep this module focused on
# signing/sending. Codex will wire the planner when we enable writes in Phase 2.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class QuoteResult:
    input_mint: str
    output_mint: str
    amount: int
    raw: Dict[str, Any]


@dataclass
class UltraOrderResult:
    input_mint: str
    output_mint: str
    amount: int
    slippage_bps: int
    raw: Dict[str, Any]

    def get_serialized_tx_b64(self) -> Optional[str]:
        """Return the base64 transaction payload if present in the response."""

        return (
            self.raw.get("tx")
            or self.raw.get("transaction")
            or self.raw.get("serializedTransaction")
        )


@dataclass
class ExecuteResult:
    signature: Optional[str]
    raw: Dict[str, Any]

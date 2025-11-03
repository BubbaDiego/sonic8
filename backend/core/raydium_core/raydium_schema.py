from __future__ import annotations
from typing import Optional, Dict, List
from pydantic import BaseModel, Field


class TokenBalance(BaseModel):
    mint: str
    amount_raw: int = Field(..., description="On-chain integer amount")
    decimals: int
    ui_amount: float = Field(..., description="amount_raw / 10**decimals")
    ata: Optional[str] = Field(None, description="Associated token account (if available)")
    symbol: Optional[str] = None
    token_program: Optional[str] = None  # token-2022 or classic


class WalletBalances(BaseModel):
    owner: str
    sol_lamports: int
    sol: float
    tokens: List[TokenBalance]
    context_slot: Optional[int] = None


class TokenInfo(BaseModel):
    address: str
    symbol: Optional[str] = None
    name: Optional[str] = None
    decimals: Optional[int] = None
    tags: Optional[List[str]] = None
    extensions: Optional[Dict[str, str]] = None

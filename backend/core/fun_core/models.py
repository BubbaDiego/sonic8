
"""Shared Pydantic models for fun_core."""
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

class FunType(str, Enum):
    joke = "joke"
    trivia = "trivia"
    quote = "quote"

class FunContent(BaseModel):
    type: FunType
    text: str
    source: str
    fetched_at: datetime
    extra: Optional[Dict[str, Any]] = None

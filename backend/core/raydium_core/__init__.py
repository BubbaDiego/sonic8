"""
Raydium core package for Sonic.

Purpose:
- Headless (no browser wallet) reads: wallet balances via Solana RPC.
- Read-only Raydium public API v3: token list, pools, etc.

This mirrors Sonic's core/data layering: a thin service in core, IO in data.

No side-effects on import.
"""

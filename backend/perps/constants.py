
from pathlib import Path
from solders.pubkey import Pubkey
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PERPS_PROGRAM_ID = Pubkey.from_string("PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu")
POOL             = Pubkey.from_string("5BUwFW4nRbftYTDMbgxykoFWqWHPzahFSNAaaaJtVKsq")
CUSTODY_SOL      = Pubkey.from_string("7xS2gz2bTp3fwCC7knJvUWTEU9Tycczu6VhJYKgi1wdz")
CUSTODY_USDC     = Pubkey.from_string("G18jKKXQwBbrHeiK3C9MRXhkHsLHf7XgCSisykV46EZa")

USDC_MINT        = Pubkey.from_string(os.getenv("MINT_USDC", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"))

TOKEN_PROGRAM            = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
SYSTEM_PROGRAM           = Pubkey.from_string("11111111111111111111111111111111")
ASSOCIATED_TOKEN_PROGRAM = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
RENT_SYSVAR_DEPRECATED   = Pubkey.from_string("SysvarRent111111111111111111111111111111111")

IDL_PATH = PROJECT_ROOT / "idl" / "jupiter_perps.json"

LAMPORTS_PER_SOL = 1_000_000_000
USDC_DECIMALS    = 6
MIN_SOL_LAMPORTS = int(os.getenv("MIN_SOL_LAMPORTS", "10000000"))

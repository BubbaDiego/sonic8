# backend/routes/wallet_preflight.py
from __future__ import annotations
import base64, json, os, requests
from typing import Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.hash import Hash
from solders.instruction import Instruction, AccountMeta
from solders.message import MessageV0, to_bytes_versioned
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price

from backend.services.signer_loader import load_signer  # <<< unify signer

router = APIRouter(prefix="/api/wallet", tags=["wallet"])

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
RPC_URL        = os.getenv("RPC_URL", f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}")

SYSTEM_PROGRAM        = Pubkey.from_string("11111111111111111111111111111111")
SPL_TOKEN_PROGRAM     = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROG = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
RENT_SYSVAR           = Pubkey.from_string("SysvarRent111111111111111111111111111111111")
SOL_MINT  = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

CU_LIMIT=800_000
CU_PRICE=100_000

def rpc(method: str, params: Any)->Any:
    r=requests.post(RPC_URL,json={"jsonrpc":"2.0","id":1,"method":method,"params":params},timeout=25)
    r.raise_for_status(); j=r.json()
    if j.get("error"): raise HTTPException(400,str(j["error"]))
    return j["result"]

def recent_blockhash()->Hash:
    return Hash.from_string(rpc("getLatestBlockhash",[{"commitment":"finalized"}])["value"]["blockhash"])

def ata(owner:Pubkey,mint:Pubkey)->Pubkey:
    from solders.pubkey import Pubkey as P
    seeds=[bytes(owner),bytes(SPL_TOKEN_PROGRAM),bytes(mint)]
    return P.find_program_address(seeds,ASSOCIATED_TOKEN_PROG)[0]

def account_exists(pub:Pubkey)->bool:
    try:
        res=rpc("getAccountInfo",[str(pub),{"encoding":"base64","commitment":"confirmed"}])
        return bool(res.get("value"))
    except: return False

def get_min_rent_exempt(size:int)->int:
    return int(rpc("getMinimumBalanceForRentExemption",[size]))

# use shared load_signer() above

class PreflightReq(BaseModel):
    mint: str = Field(..., description="Mint address or SOL/USDC")
    to:   str = Field(..., description="Recipient")
    amountAtoms: int = Field(..., gt=0)

@router.post("/preflight-send")
def preflight_send(req:PreflightReq):
    # minimal normalization
    mint=req.mint.upper()
    if mint=="SOL": mint=SOL_MINT
    if mint=="USDC": mint=USDC_MINT

    kp=load_signer(); payer=kp.pubkey()
    mint_pub=None if mint==SOL_MINT else Pubkey.from_string(mint)
    to_owner=Pubkey.from_string(req.to)

    ixs:List[Instruction]=[ set_compute_unit_limit(CU_LIMIT), set_compute_unit_price(CU_PRICE) ]

    if mint==SOL_MINT:
        lamports = int(req.amountAtoms)
        data = (2).to_bytes(4,"little") + lamports.to_bytes(8,"little")
        ixs.append(Instruction(
            SYSTEM_PROGRAM,
            data,
            [AccountMeta(payer,True,True), AccountMeta(to_owner,False,True)]
        ))
    else:
        src_ata=ata(payer,mint_pub); dst_ata=ata(to_owner,mint_pub)
        if not account_exists(src_ata):
            ixs.append(Instruction(ASSOCIATED_TOKEN_PROG,b"",[
                AccountMeta(payer,True,True), AccountMeta(src_ata,False,True), AccountMeta(payer,False,False),
                AccountMeta(mint_pub,False,False), AccountMeta(SYSTEM_PROGRAM,False,False),
                AccountMeta(SPL_TOKEN_PROGRAM,False,False), AccountMeta(RENT_SYSVAR,False,False)
            ]))
        if not account_exists(dst_ata):
            ixs.append(Instruction(ASSOCIATED_TOKEN_PROG,b"",[
                AccountMeta(payer,True,True), AccountMeta(dst_ata,False,True), AccountMeta(to_owner,False,False),
                AccountMeta(mint_pub,False,False), AccountMeta(SYSTEM_PROGRAM,False,False),
                AccountMeta(SPL_TOKEN_PROGRAM,False,False), AccountMeta(RENT_SYSVAR,False,False)
            ]))
        decimals=6 if mint==USDC_MINT else 9
        data=bytes([12])+int(req.amountAtoms).to_bytes(8,"little")+bytes([decimals])
        ixs.append(Instruction(SPL_TOKEN_PROGRAM,data,[
            AccountMeta(src_ata,False,True), AccountMeta(mint_pub,False,False),
            AccountMeta(dst_ata,False,True), AccountMeta(payer,True,False)
        ]))

    bh=recent_blockhash()
    msg=MessageV0.try_compile(payer, ixs, [], bh)
    from solders.message import to_bytes_versioned
    msg_b64=base64.b64encode(to_bytes_versioned(msg)).decode()
    fee_info=rpc("getFeeForMessage",[msg_b64,{"commitment":"finalized"}])
    fee=int(fee_info.get("value") or 5000)

    rent=0
    if mint_pub:
        rent_token=get_min_rent_exempt(165)
        if not account_exists(ata(payer,mint_pub)): rent+=rent_token
        if not account_exists(ata(to_owner,mint_pub)): rent+=rent_token

    bal=int(rpc("getBalance",[str(payer)])["value"])
    return {"feeLamports":fee, "rentLamports":rent, "balanceLamports":bal,
            "needLamports": max(0, fee+rent - bal)}

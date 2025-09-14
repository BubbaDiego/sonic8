from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import base64, json, os, requests
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.hash import Hash
from solders.instruction import Instruction
from solders.account_meta import AccountMeta
from solders.message import MessageV0
from solders.transaction import VersionedTransaction

router = APIRouter(prefix="/api/wallet", tags=["wallet"])

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
RPC_URL = os.getenv("RPC_URL", f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}")
SPL_TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROG = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")

SIGNER_PATH = os.getenv("SIGNER_PATH", os.path.join(os.path.dirname(__file__), "..", "signer_id.json"))  # adjust

SOL_MINT = "So11111111111111111111111111111111111111112"

class SendReq(BaseModel):
  mint: str
  to: str
  amountAtoms: int

def rpc(method, params):
  r = requests.post(RPC_URL, json={"jsonrpc":"2.0","id":1,"method":method,"params":params}, timeout=20)
  r.raise_for_status()
  data = r.json()
  if data.get("error"):
    raise HTTPException(400, str(data["error"]))
  return data["result"]

def load_signer(path: str) -> Keypair:
  txt = open(path,"r",encoding="utf-8").read()
  obj = json.loads(txt)
  if isinstance(obj, list):  # id.json
    return Keypair.from_bytes(bytes(obj))
  if isinstance(obj, dict) and "secretKey" in obj:
    return Keypair.from_bytes(bytes(obj["secretKey"]))
  raise HTTPException(500, "Unsupported signer format")

def recent_blockhash() -> Hash:
  return Hash.from_string(rpc("getLatestBlockhash", [{"commitment":"finalized"}])["value"]["blockhash"])

def ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
  seeds = [bytes(owner), bytes(SPL_TOKEN_PROGRAM), bytes(mint)]
  return Pubkey.find_program_address(seeds, ASSOCIATED_TOKEN_PROG)[0]

@router.post("/send")
def send_token_api(req: SendReq):
  try:
    kp = load_signer(SIGNER_PATH)
    payer = kp.pubkey()
    to_owner = Pubkey.from_string(req.to)

    bh = recent_blockhash()
    ixs: list[Instruction] = []

    # compute-boost (optional)
    from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
    ixs.append(set_compute_unit_limit(800_000))
    ixs.append(set_compute_unit_price(100_000))  # adjust priority if needed

    if req.mint == SOL_MINT:
      # system transfer Lamports
      data = b"\x02" + int(req.amountAtoms).to_bytes(8, "little")  # SystemProgram::Transfer
      ixs.append(Instruction(SYSTEM_PROGRAM, data, [
        AccountMeta(payer, True, True),
        AccountMeta(to_owner, False, True),
      ]))
    else:
      # SPL: ensure recipient ATA exists (create if missing)
      mint = Pubkey.from_string(req.mint)
      dest_ata = ata(to_owner, mint)
      # This single CPI creates ATA if absent (Associated Token Program)
      create_ata_ix = Instruction(
        ASSOCIATED_TOKEN_PROG, b"",
        [
          AccountMeta(payer, True, True),          # payer
          AccountMeta(dest_ata, False, True),      # associated account
          AccountMeta(to_owner, False, False),     # owner
          AccountMeta(mint, False, False),         # mint
          AccountMeta(SYSTEM_PROGRAM, False, False),
          AccountMeta(SPL_TOKEN_PROGRAM, False, False),
        ]
      )
      ixs.append(create_ata_ix)

      # token::transfer (checked)
      # Tag = 3 (TransferChecked), amount u64, decimals u8
      # We can read decimals from IDL/metadata; for common mints we know them:
      decimals = 6 if req.mint == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" else 9
      data = bytes([12]) + int(req.amountAtoms).to_bytes(8, "little") + bytes([decimals])  # TransferChecked tag=12
      src_ata = ata(payer, mint)
      ixs.append(Instruction(
        SPL_TOKEN_PROGRAM, data,
        [
          AccountMeta(src_ata, False, True),     # source
          AccountMeta(mint, False, False),
          AccountMeta(dest_ata, False, True),    # dest
          AccountMeta(payer, True, False)        # authority
        ]
      ))

    msg = MessageV0.try_compile(
      payer=payer,
      instructions=ixs,
      address_lookup_tables=[],
      recent_blockhash=bh
    )
    tx = VersionedTransaction(msg, [kp])
    sig = rpc("sendTransaction", [base64.b64encode(bytes(tx)).decode(), {"skipPreflight": False, "maxRetries": 3}])
    return {"signature": sig}
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(400, f"send failed: {e}")

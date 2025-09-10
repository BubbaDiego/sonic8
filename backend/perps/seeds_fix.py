
import re
from typing import Optional, List
from solders.pubkey import Pubkey

SEEDS_ERR = re.compile(r"^Program log:\s*AnchorError caused by account:\s*([a-zA-Z_]+)\. Error Code: ConstraintSeeds")
RIGHT_INLINE = re.compile(r"^Program log:\s*Right:\s*([1-9A-HJ-NP-Za-km-z]{32,44})$")
RIGHT_LINE = re.compile(r"^Program log:\s*Right:\s*$")
PUBKEY_LINE = re.compile(r"^Program log:\s*([1-9A-HJ-NP-Za-km-z]{32,44})\s*$")

def parse_seeds_violation(logs: List[str]) -> tuple[Optional[str], Optional[Pubkey]]:
    acct = None; right = None
    for i, line in enumerate(logs or []):
        m = SEEDS_ERR.match(line.strip())
        if m: acct = m.group(1)
        m2 = RIGHT_INLINE.match(line.strip())
        if m2:
            try: right = Pubkey.from_string(m2.group(1))
            except Exception: pass
        if RIGHT_LINE.match(line.strip()) and i + 1 < len(logs):
            m3 = PUBKEY_LINE.match(logs[i+1].strip())
            if m3:
                try: right = Pubkey.from_string(m3.group(1))
                except Exception: pass
    return acct, right

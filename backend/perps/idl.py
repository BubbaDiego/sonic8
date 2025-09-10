
import json
from typing import Optional
from anchorpy import Idl
from .constants import IDL_PATH

def say(s): print(f"\n🟠 {s} …", flush=True)
def done(s="done"): print(f"   ✅ {s}", flush=True)

async def ensure_idl() -> Idl:
    say("Ensuring IDL")
    if not IDL_PATH.exists(): raise SystemExit(f"❌ IDL JSON not found at {IDL_PATH}")
    text = IDL_PATH.read_text(encoding="utf-8")
    try: idl = Idl.from_json(text)
    except TypeError: idl = Idl.from_json(json.loads(text))
    done("IDL loaded from disk")
    return idl

def _load_idl_json(path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def _find_ix_json(idl_json: dict, ix_name: str) -> Optional[dict]:
    for ix in idl_json.get("instructions", []):
        if ix.get("name") == ix_name:
            return ix
    snake = _camel_to_snake(ix_name)
    for ix in idl_json.get("instructions", []):
        if ix.get("name") == snake:
            return ix
    return None

def _find_type_json(idl_json: dict, name: str) -> Optional[dict]:
    for t in idl_json.get("types", []) or []:
        if t.get("name") == name:
            return t
    return None

def _enum_json_variant_index(idl_json: dict, enum_name: str, want: str) -> int:
    t = _find_type_json(idl_json, enum_name)
    want_low = (want or "").lower()
    if t and t.get("type", {}).get("kind") == "enum":
        for i, v in enumerate(t["type"].get("variants", [])):
            nm = v.get("name","")
            if nm.lower() == want_low: return i
        return 0
    return 0

def _camel_to_snake(name: str) -> str:
    out=[]
    for ch in name: out.append("_"+ch.lower() if ch.isupper() else ch)
    s="".join(out); return s[1:] if s.startswith("_") else s

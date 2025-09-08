import os, json, re
from pathlib import Path
from urllib.request import urlopen

OUT_PATH = Path(r"C:\sonic5\idl\jupiter_perps.json")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# 1) Direct JSON (fast path). This repo tracks a clean Perps IDL JSON.
URLS_JSON_FIRST = [
    "https://raw.githubusercontent.com/Garrett-Weber/jupiter-perpetuals-cpi/main/idl.json",
]

# 2) Fallback to TS source from the repo Jupiter links in their docs.
TS_URL = "https://raw.githubusercontent.com/julianfssen/jupiter-perps-anchor-idl-parsing/main/src/idl/jupiter-perpetuals-idl.ts"

def fetch(url: str) -> str:
    with urlopen(url) as r:
        return r.read().decode("utf-8")

def try_download_json():
    for u in URLS_JSON_FIRST:
        try:
            text = fetch(u)
            # sanity: must parse as JSON
            obj = json.loads(text)
            with OUT_PATH.open("w", encoding="utf-8") as f:
                json.dump(obj, f, indent=2)
            print(f"✅ Saved JSON IDL from {u} -> {OUT_PATH}")
            return True
        except Exception as e:
            print(f"Skip {u}: {e}")
    return False

def strip_trailing_commas(s: str) -> str:
    # Remove trailing commas before } or ] (simple heuristic that works for IDLs)
    return re.sub(r",(\s*[}\]])", r"\1", s)

def extract_object_from_ts(ts: str) -> str:
    """
    Find the first 'export const <name> = { ... } as const' and return the {...} payload.
    We do real brace matching so extra exports after the object won't matter.
    """
    # find the '=' after 'export const'
    m = re.search(r"export\s+const\s+\w+\s*=\s*", ts)
    if not m:
        raise ValueError("No 'export const <name> =' found")
    i = m.end()

    # find the first '{' after '='
    while i < len(ts) and ts[i] != '{':
        i += 1
    if i >= len(ts) or ts[i] != '{':
        raise ValueError("No opening '{' after export const =")

    # brace-match until depth returns to 0
    depth = 0
    j = i
    in_str = False
    str_quote = ''
    escape = False
    while j < len(ts):
        ch = ts[j]
        if in_str:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == str_quote:
                in_str = False
        else:
            if ch in ('"', "'"):
                in_str = True
                str_quote = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    j += 1
                    break
        j += 1
    if depth != 0:
        raise ValueError("Unbalanced braces while parsing TS object")

    obj_text = ts[i:j]  # includes the outer braces
    obj_text = strip_trailing_commas(obj_text)
    return obj_text

def try_download_ts_and_convert():
    ts = fetch(TS_URL)
    payload = extract_object_from_ts(ts)
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError as e:
        # last-ditch cleanup if TS has comments (rare)
        clean = re.sub(r"//.*?$|/\*.*?\*/", "", payload, flags=re.MULTILINE|re.DOTALL)
        clean = strip_trailing_commas(clean)
        obj = json.loads(clean)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    print(f"✅ Converted TS → JSON and saved to {OUT_PATH}")

def main():
    if try_download_json():
        return
    print("Falling back to TS → JSON conversion …")
    try_download_ts_and_convert()

if __name__ == "__main__":
    main()

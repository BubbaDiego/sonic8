import argparse, base64, hashlib, json, sys, time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Anchor discriminator for the 'Store' account type
STORE_DISC = hashlib.sha256(b"account:Store").digest()[:8]

def rpc_call(rpc, method, params):
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req  = Request(rpc, data=body, headers={"Content-Type":"application/json", "User-Agent":"sonic7-gmsol-find-store"})
    with urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    if "error" in data:
        raise RuntimeError(f"RPC error {method}: {data['error']}")
    return data["result"]

def iter_program_accounts_v2(rpc, program_id, limit):
    page = 1
    while True:
        cfg = {"encoding":"base64", "page":page, "limit":limit, "commitment":"confirmed"}
        try:
            res = rpc_call(rpc, "getProgramAccountsV2", [program_id, cfg])
        except RuntimeError as e:
            # Fallback to classic GPA if v2 not supported
            if "Method not found" in str(e) or "getProgramAccountsV2" in str(e):
                res = rpc_call(rpc, "getProgramAccounts", [program_id, {"encoding":"base64","commitment":"confirmed"}])
                # Classic GPA returns everything at once; yield and break
                for a in res:
                    yield a
                return
            raise
        if not res:
            return
        for a in res:
            yield a
        if len(res) < limit:
            return
        page += 1
        time.sleep(0.15)  # be nice to RPC

def find_store_account(rpc, program_id, limit=1000, want_size_debug=False):
    matches = []
    sizes = {}
    for acc in iter_program_accounts_v2(rpc, program_id, limit):
        info = acc.get("account") or {}
        data = info.get("data")
        if isinstance(data, list) and len(data) >= 1:
            raw = base64.b64decode(data[0])
        elif isinstance(data, str):
            raw = base64.b64decode(data)
        else:
            continue
        if want_size_debug:
            sizes[len(raw)] = sizes.get(len(raw), 0) + 1
        if len(raw) >= 8 and raw[:8] == STORE_DISC:
            matches.append({"pubkey": acc.get("pubkey"), "space": len(raw)})
    return matches, sizes

def load_console_json(path):
    try:
        return json.loads(open(path, "r", encoding="utf-8").read())
    except FileNotFoundError:
        return {}
    except Exception as e:
        raise RuntimeError(f"Failed to read {path}: {e}")

def save_console_json(path, obj):
    txt = json.dumps(obj, indent=2)
    open(path, "w", encoding="utf-8").write(txt)

def main():
    ap = argparse.ArgumentParser(description="Find GMX‑Solana Store account by Anchor discriminator.")
    ap.add_argument("--rpc", required=True, help="RPC endpoint (Helius OK)")
    ap.add_argument("--program", required=True, help="GMX‑Solana Store program id (e.g. Gmso1uvJ...)")
    ap.add_argument("--limit", type=int, default=1000, help="Page size for V2 scan (default 1000)")
    ap.add_argument("--console-json", default=r"C:\\sonic7\\gmx_solana_console.json", help="Console config to write store_account into")
    ap.add_argument("--set", action="store_true", help="Write discovered store_account into console JSON")
    ap.add_argument("--sizes", action="store_true", help="Print size histogram")
    args = ap.parse_args()

    matches, sizes = find_store_account(args.rpc, args.program, args.limit, want_size_debug=args.sizes)
    out = {"program": args.program, "found": matches}
    if args.sizes:
        out["size_histogram"] = dict(sorted(sizes.items(), key=lambda kv: kv[0]))
    print(json.dumps(out, indent=2))

    if args.set:
        if len(matches) == 1 and matches[0].get("pubkey"):
            cfg = load_console_json(args.console_json)
            cfg["store_account"] = matches[0]["pubkey"]
            save_console_json(args.console_json, cfg)
            print(f"✅ Wrote store_account={matches[0]['pubkey']} to {args.console_json}")
        elif len(matches) == 0:
            print("⚠️  No Store account found. (Check RPC/program id.)")
            sys.exit(2)
        else:
            print("⚠️  Multiple Store accounts found. Not writing to config.")
            sys.exit(3)

if __name__ == "__main__":
    main()

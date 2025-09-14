import requests, json

HELIUS_API_KEY = "a8809bee-20ba-48e9-b841-0bd2bafd60b9"
RPC = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
POOL = "5BUwFW4nRbftYTDMbgxykoFWqWHPzahFSNAaaaJtVKsq"  # JLP Pool from Jupiter docs

def rpc(method, params):
    r = requests.post(RPC, json={"jsonrpc":"2.0","id":1,"method":method,"params":params}, timeout=20)
    r.raise_for_status()
    data = r.json()
    if data.get("error"): raise RuntimeError(data["error"])
    return data.get("result")

def main():
    # 1) owner of Pool -> true Perps program id
    res = rpc("getAccountInfo", [POOL, {"encoding":"jsonParsed","commitment":"confirmed"}])
    v = res.get("value") if isinstance(res, dict) else None
    owner = v.get("owner") if isinstance(v, dict) else None
    print("Pool:", POOL)
    print("Perps Program ID (owner):", owner)

    # 2) page the program with V2 — must return at least 1 item if PID is right
    v2 = rpc("getProgramAccountsV2", [owner, {"encoding":"base64","page":1,"limit":5}])
    print("First V2 page count:", len(v2) if isinstance(v2, list) else v2)

if __name__ == "__main__":
    main()

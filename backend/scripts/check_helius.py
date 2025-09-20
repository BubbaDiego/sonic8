import os, json, requests

KEY = os.getenv("HELIUS_API_KEY")
assert KEY and KEY != "<YOUR_KEY>", "HELIUS_API_KEY missing or placeholder"

URL = f"https://rpc.helius.xyz/?api-key={KEY}"
payload = {"jsonrpc":"2.0","id":1,"method":"getLatestBlockhash","params":[{"commitment":"processed"}]}

r = requests.post(URL, json=payload, timeout=10)
print("HTTP", r.status_code)
print(r.text)
r.raise_for_status()
resp = r.json()
assert "result" in resp, f"Unexpected response: {resp}"
print("Helius RPC OK ✅")

import os
import json
import asyncio
import signal
import sys
from pathlib import Path

# pip install websockets
import websockets

# Derive WS url from .env or CLI
def load_ws_url() -> str:
    # prefer explicit HELIUS_WS_URL, else build from RPC_URL
    env = Path(r"C:\sonic5\.env")
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("RPC_URL="):
                rpc = line.split("=", 1)[1].strip()
                if rpc.startswith("http"):
                    return rpc.replace("http", "ws", 1)  # http(s) -> ws(s)
    # fallback to env vars if python-dotenv already loaded by parent
    rpc = os.getenv("RPC_URL", "").strip()
    if rpc.startswith("http"):
        return rpc.replace("http", "ws", 1)
    # last resort: require explicit
    ws = os.getenv("HELIUS_WS_URL", "").strip()
    if not ws:
        raise SystemExit("Set HELIUS_WS_URL or RPC_URL in C:\\sonic5\\.env")
    return ws

async def account_subscribe(ws, account: str, id_=1, commitment="confirmed"):
    msg = {
        "jsonrpc": "2.0",
        "id": id_,
        "method": "accountSubscribe",
        "params": [account, {"encoding": "jsonParsed", "commitment": commitment}],
    }
    await ws.send(json.dumps(msg))

async def signature_subscribe(ws, sig: str, id_=1000, commitment="confirmed"):
    msg = {
        "jsonrpc": "2.0",
        "id": id_,
        "method": "signatureSubscribe",
        "params": [sig, {"commitment": commitment}],
    }
    await ws.send(json.dumps(msg))

async def run(accounts: list[str], signatures: list[str]):
    url = load_ws_url()
    print(f"🔌 WS → {url}")
    backoff = 0.5
    while True:
        try:
            async with websockets.connect(url, ping_interval=20, ping_timeout=20, close_timeout=5) as ws:
                print("✅ Connected to Helius WS")
                # subscribe
                rid = 1
                for acc in accounts:
                    print(f"🛰️  subscribing account: {acc}")
                    await account_subscribe(ws, acc, id_=rid); rid += 1
                for sig in signatures:
                    print(f"🛰️  subscribing signature: {sig}")
                    await signature_subscribe(ws, sig, id_=rid); rid += 1

                backoff = 0.5  # reset on success
                while True:
                    raw = await ws.recv()
                    msg = json.loads(raw)
                    # Notifications
                    if msg.get("method") == "accountNotification":
                        val = msg["params"]["result"]["value"]
                        slot = msg["params"]["result"]["context"]["slot"]
                        print(f"📦 account update @ slot {slot}")
                        print(json.dumps(val, indent=2))
                    elif msg.get("method") == "signatureNotification":
                        result = msg["params"]["result"]
                        print(f"🧾 signature status: {result}")
                    else:
                        # subscription acks etc.
                        if "result" in msg and "id" in msg:
                            print(f"✅ sub ack id={msg['id']} → {msg['result']}")
        except (websockets.ConnectionClosedError, websockets.ConnectionClosedOK) as e:
            print(f"🔁 WS closed: {e} — reconnecting …")
        except Exception as e:
            print(f"⚠️  WS error: {e} — reconnecting …")
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 5.0)

def parse_args():
    import argparse
    p = argparse.ArgumentParser(description="Helius WS watcher")
    p.add_argument("--account", action="append", default=[], help="Account to accountSubscribe (repeatable)")
    p.add_argument("--sig", action="append", default=[], help="Signature to signatureSubscribe (repeatable)")
    return p.parse_args()

def main():
    args = parse_args()
    loop = asyncio.get_event_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        try: loop.add_signal_handler(s, loop.stop)
        except: pass
    loop.run_until_complete(run(args.account, args.sig))

if __name__ == "__main__":
    main()

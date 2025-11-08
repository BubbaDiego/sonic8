/**
 * Registration sanity checks for Raydium Perps (Orderly-backed)
 *
 * What this script does:
 *  1) probe — public check: is a wallet already registered on Orderly under a broker?
 *     GET /v1/get_account?address=...&broker_id=...&chain_type=SOL
 *  2) auth-check — private check: verify your ORDERLY_* creds by calling a signed endpoint
 *     GET /v1/client/info
 *
 * This follows the official Orderly docs (no inventions):
 * - Registration flow + broker/account checks: https://orderly.network/docs/build-on-omnichain/user-flows/accounts
 * - Auth/signing (ed25519 + base64url): https://orderly.network/docs/build-on-omnichain/evm-api/api-authentication
 *
 * Raydium’s public API docs entrypoint (for later perps endpoints):
 * - https://docs.raydium.io/raydium/protocol/developers/api  -> https://api-v3.raydium.io/docs/
 */

import { buildOrderlyHeaders } from "./auth.js";

const ORDERLY_BASE = process.env.ORDERLY_USE_TESTNET ? "https://testnet-api.orderly.org" : "https://api.orderly.org";

type Args = { cmd: "probe" | "auth-check"; address?: string; brokerId?: string; chainType?: "SOL" | "EVM" };

function parseArgs(): Args {
  const [, , cmd, ...rest] = process.argv;
  if (cmd !== "probe" && cmd !== "auth-check") {
    console.error("Usage:");
    console.error("  tsx registration_test.ts probe --address <SOL_ADDRESS> --broker <brokerId> [--chain SOL|EVM]");
    console.error("  tsx registration_test.ts auth-check");
    process.exit(2);
  }
  const args: Args = { cmd } as any;
  for (let i = 0; i < rest.length; i += 2) {
    const k = rest[i];
    const v = rest[i + 1];
    if (!v) break;
    if (k === "--address") args.address = v;
    if (k === "--broker") args.brokerId = v;
    if (k === "--chain") args.chainType = v as any;
  }
  return args;
}

async function httpGet(pathWithQuery: string, headers?: Record<string, string>) {
  const url = ORDERLY_BASE + pathWithQuery;
  const res = await fetch(url, { method: "GET", headers });
  const txt = await res.text();
  let json: any = undefined;
  try { json = JSON.parse(txt); } catch {}
  return { status: res.status, ok: res.ok, json, text: txt, url };
}

async function probe(address: string, brokerId: string, chainType: "SOL" | "EVM") {
  const path = `/v1/get_account?address=${encodeURIComponent(address)}&broker_id=${encodeURIComponent(brokerId)}&chain_type=${encodeURIComponent(chainType)}`;
  const r = await httpGet(path); // public endpoint (no signature)
  if (!r.ok) {
    console.error(`[probe] HTTP ${r.status} ${r.url}\n${r.text}`);
    process.exit(1);
  }
  console.log(JSON.stringify({ ok: true, step: "probe", request: { address, brokerId, chainType }, response: r.json }, null, 2));
}

async function authCheck() {
  // Signed private endpoint to confirm ORDERLY_* creds are correct.
  // Example private endpoint: GET /v1/client/info
  const method = "GET";
  const path = "/v1/client/info";
  const headers = buildOrderlyHeaders(method, path);
  const r = await httpGet(path, headers);
  if (!r.ok) {
    console.error(`[auth-check] HTTP ${r.status} ${r.url}\n${r.text}`);
    process.exit(1);
  }
  console.log(JSON.stringify({ ok: true, step: "auth-check", endpoint: path, response: r.json }, null, 2));
}

async function main() {
  const args = parseArgs();
  if (args.cmd === "probe") {
    const address = args.address ?? process.env.SOL_ADDRESS;
    const brokerId = args.brokerId ?? process.env.ORDERLY_BROKER_ID ?? "raydium";
    const chainType = args.chainType ?? (process.env.ORDERLY_CHAIN_TYPE as any) ?? "SOL";
    if (!address) {
      console.error("Missing wallet address. Pass --address <SOL_ADDRESS> or set SOL_ADDRESS env.");
      process.exit(2);
    }
    await probe(address, brokerId, chainType);
  } else {
    // Requires env: ORDERLY_ACCOUNT_ID, ORDERLY_KEY, ORDERLY_SECRET
    await authCheck();
  }
}
main().catch((e) => {
  console.error(e);
  process.exit(1);
});

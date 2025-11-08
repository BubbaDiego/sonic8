// Minimal Orderly request signer (ed25519 + base64url) per docs
// https://orderly.network/docs/build-on-omnichain/evm-api/api-authentication
import nacl from "tweetnacl";
import bs58 from "bs58";

export type AuthEnv = {
  ORDERLY_ACCOUNT_ID: string; // required
  ORDERLY_KEY: string;        // public ed25519 key (no "ed25519:" prefix preferred)
  ORDERLY_SECRET: string;     // base58 private key (with or without "ed25519:" prefix)
};

export function requireAuthEnv(): AuthEnv {
  const { ORDERLY_ACCOUNT_ID, ORDERLY_KEY, ORDERLY_SECRET } = process.env as Record<string, string | undefined>;
  if (!ORDERLY_ACCOUNT_ID || !ORDERLY_KEY || !ORDERLY_SECRET) {
    throw new Error("Missing ORDERLY_ACCOUNT_ID / ORDERLY_KEY / ORDERLY_SECRET in env");
  }
  return { ORDERLY_ACCOUNT_ID, ORDERLY_KEY: stripPrefix(ORDERLY_KEY), ORDERLY_SECRET };
}

export function stripPrefix(v: string): string {
  return v.startsWith("ed25519:") ? v.slice("ed25519:".length) : v;
}

function toBase64Url(buf: Uint8Array): string {
  const b64 = Buffer.from(buf).toString("base64");
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function privateKeyFromBase58(secret58: string): Uint8Array {
  const raw = bs58.decode(stripPrefix(secret58));
  if (raw.length === 64) return new Uint8Array(raw); // secretKey (seed+pub)
  if (raw.length === 32) {
    // seed -> derive full secretKey
    const kp = nacl.sign.keyPair.fromSeed(new Uint8Array(raw));
    const sk = new Uint8Array(64);
    sk.set(kp.secretKey);
    return sk;
  }
  throw new Error(`Unexpected ORDERLY_SECRET length ${raw.length}. Expect 32 (seed) or 64 (secretKey).`);
}

/**
 * Build signed headers for Orderly REST, per normalization rules:
 *   signature over: <timestamp><METHOD><pathWithQuery>[<jsonBody>]
 */
export function buildOrderlyHeaders(
  method: string,
  pathWithQuery: string,
  bodyJson?: string,
  env?: Partial<AuthEnv>
): Record<string, string> {
  const provided = env ?? {};
  const hasAllProvided = Boolean(provided.ORDERLY_ACCOUNT_ID && provided.ORDERLY_KEY && provided.ORDERLY_SECRET);
  const defaults = hasAllProvided
    ? {
        ORDERLY_ACCOUNT_ID: provided.ORDERLY_ACCOUNT_ID!,
        ORDERLY_KEY: stripPrefix(provided.ORDERLY_KEY!),
        ORDERLY_SECRET: provided.ORDERLY_SECRET!
      }
    : requireAuthEnv();
  const accountId = provided.ORDERLY_ACCOUNT_ID ?? defaults.ORDERLY_ACCOUNT_ID;
  const orderlyKey = stripPrefix(provided.ORDERLY_KEY ?? defaults.ORDERLY_KEY);
  const orderlySecret = provided.ORDERLY_SECRET ?? defaults.ORDERLY_SECRET;
  const ts = Date.now().toString();
  const normalized = ts + method.toUpperCase() + pathWithQuery + (bodyJson ?? "");
  const secretKey = privateKeyFromBase58(orderlySecret);
  const sig = nacl.sign.detached(Buffer.from(normalized), secretKey);
  const signature = toBase64Url(sig);
  return {
    "Content-Type": method === "GET" || method === "DELETE" ? "application/x-www-form-urlencoded" : "application/json",
    "orderly-account-id": accountId,
    "orderly-key": orderlyKey,
    "orderly-timestamp": ts,
    "orderly-signature": signature
  };
}

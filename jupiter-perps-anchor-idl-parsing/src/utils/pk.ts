import { PublicKey } from "@solana/web3.js";

const B58 = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;

export function toPk(label: string, v: unknown): PublicKey {
  if (v instanceof PublicKey) return v;
  if (typeof v === "string") {
    const s = v.trim();
    if (!B58.test(s)) {
      const preview = s.length > 80 ? s.slice(0, 80) + "…" : s;
      throw new Error(`Invalid base58 for ${label}: "${preview}"`);
    }
    return new PublicKey(s);
  }
  // Numeric or object slip-through — make it obvious
  throw new Error(`Invalid PublicKey for ${label}: type=${typeof v} value=${String(v)}`);
}

import { Connection, PublicKey } from "@solana/web3.js";
import { BorshCoder, Idl } from "@coral-xyz/anchor";
import yargs from "yargs";
import { hideBin } from "yargs/helpers";
import BN from "bn.js";
import { createHash } from "crypto";

import { IDL as JUP_PERPS_IDL } from "../idl/jupiter-perpetuals-idl.js";
import { bar, info, kv, warn } from "../utils/logger.js";

const argv = await yargs(hideBin(process.argv))
  .scriptName("perps_watch_position")
  .option("rpc", { type: "string", demandOption: true, desc: "RPC URL" })
  .option("position", { type: "string", desc: "Position account to watch" })
  .option("request", { type: "string", desc: "PositionRequest account to watch" })
  .option("program", {
    type: "string",
    default: (JUP_PERPS_IDL as any)?.metadata?.address ?? "PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu",
    desc: "Perps program id (for metadata only)"
  })
  .option("poll-ms", {
    type: "number",
    default: 2000,
    desc: "Polling interval in milliseconds"
  })
  .option("once", {
    type: "boolean",
    default: false,
    desc: "Fetch once then exit"
  })
  .check(args => {
    if (!args.position && !args.request) {
      throw new Error("Provide --position, --request, or both");
    }
    return true;
  })
  .help()
  .strict()
  .argv;

type WatchKind = "Position" | "PositionRequest";

type WatchTarget = {
  label: string;
  pubkey: PublicKey;
  order: readonly string[];
};

const WATCH_ORDERS: Record<WatchKind, readonly string[]> = {
  Position: ["Position", "position", "positionAccount"],
  PositionRequest: ["PositionRequest", "positionRequest", "position_request"]
};

function normalize(value: any): any {
  if (value instanceof PublicKey) return value.toBase58();
  if (BN.isBN(value)) return value.toString();
  if (Array.isArray(value)) return value.map(normalize);
  if (value && typeof value === "object") {
    const out: Record<string, any> = {};
    for (const [k, v] of Object.entries(value)) out[k] = normalize(v);
    return out;
  }
  if (value instanceof Uint8Array) return Buffer.from(value).toString("base64");
  return value;
}

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

function hashData(buf: Buffer): string {
  return createHash("sha256").update(buf).digest("hex");
}

async function decodeWithOrder(coder: BorshCoder, order: readonly string[], data: Buffer) {
  for (const name of order) {
    try {
      return { name, decoded: coder.accounts.decode(name as any, data) };
    } catch {
      // continue trying other variants
    }
  }
  return null;
}

async function watchTarget(connection: Connection, coder: BorshCoder, target: WatchTarget, pollMs: number, once: boolean) {
  let lastHash: string | null = null;
  do {
    try {
      const res = await connection.getAccountInfoAndContext(target.pubkey, "confirmed");
      const infoValue = res.value;
      if (!infoValue) {
        warn(`${target.label}: account not found`);
      } else {
        const data = Buffer.from(infoValue.data);
        const hash = hashData(data);
        if (hash !== lastHash) {
          lastHash = hash;
          const decoded = await decodeWithOrder(coder, target.order, data);
          const slot = res.context.slot;
          const header = `${target.label} @ slot ${slot} (lamports=${infoValue.lamports}, hash=${hash.slice(0, 12)}…)`;
          bar(header, "👀");
          kv("Pubkey", target.pubkey.toBase58());
          kv("Data length", data.length);
          if (decoded) {
            info("✅", `Decoded as ${decoded.name}`);
            console.dir(normalize(decoded.decoded), { depth: 8 });
          } else {
            warn(`${target.label}: unable to decode with provided IDL; dumping base64`);
            console.log(data.toString("base64"));
          }
        }
      }
    } catch (err) {
      warn(`${target.label}: ${err instanceof Error ? err.message : String(err)}`);
    }
    if (!once) await sleep(pollMs);
  } while (!once);
}

async function main() {
  const rpc = argv.rpc;
  const connection = new Connection(rpc, { commitment: "confirmed" });
  const coder = new BorshCoder(JUP_PERPS_IDL as Idl);

  bar("Perps account watcher", "🛰️");
  kv("RPC", rpc);
  kv("Program", argv.program);

  const targets: WatchTarget[] = [];
  if (argv.position) {
    targets.push({
      label: "Position",
      pubkey: new PublicKey(argv.position),
      order: WATCH_ORDERS.Position
    });
  }
  if (argv.request) {
    targets.push({
      label: "PositionRequest",
      pubkey: new PublicKey(argv.request),
      order: WATCH_ORDERS.PositionRequest
    });
  }

  if (targets.length === 0) {
    throw new Error("Nothing to watch");
  }

  await Promise.all(targets.map(target => watchTarget(connection, coder, target, argv["poll-ms"], argv.once)));
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});

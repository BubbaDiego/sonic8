import { Connection, PublicKey } from "@solana/web3.js";
import { AnchorProvider, BorshCoder, Program, Idl } from "@coral-xyz/anchor";
import yargs from "yargs";
import { hideBin } from "yargs/helpers";
import BN from "bn.js";

const argv = yargs(hideBin(process.argv))
  .option("rpc", { type: "string", demandOption: true, desc: "RPC URL" })
  .option("id", { type: "string", demandOption: true, desc: "Account pubkey to read" })
  .option("program", {
    type: "string",
    default: "PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu",
    desc: "Perps program id"
  })
  .option("kind", {
    type: "string",
    choices: ["auto", "position", "request"],
    default: "auto",
    desc: "Hint for decoder"
  })
  .help()
  .strict()
  .parseSync();

function normalize(x: any): any {
  if (x instanceof BN) return x.toString();
  if (Array.isArray(x)) return x.map(normalize);
  if (x && typeof x === "object") {
    const out: any = {};
    for (const [k, v] of Object.entries(x)) out[k] = normalize(v);
    return out;
  }
  return x;
}

async function main() {
  const connection = new Connection(argv.rpc, "confirmed");
  const acctPk = new PublicKey(argv.id);
  const programId = new PublicKey(argv.program);

  const info = await connection.getAccountInfo(acctPk, "confirmed");
  if (!info) throw new Error("Account not found");

  console.log("🔎 Account:", acctPk.toBase58());
  console.log("• Owner  :", info.owner.toBase58());
  console.log("• Lamports:", info.lamports);
  console.log("• Data len:", info.data.length);

  // Try to fetch IDL and decode nicely. Fall back to raw if not available.
  let idl: Idl | null = null;
  try {
    const provider = new AnchorProvider(connection, {} as any, AnchorProvider.defaultOptions());
    idl = await Program.fetchIdl(programId, provider);
  } catch (e) {
    // ignore; we’ll print raw below
  }

  if (!idl) {
    console.log("⚠️  No IDL fetched; dumping base64 data:");
    console.log(Buffer.from(info.data).toString("base64"));
    return;
  }

  const coder = new BorshCoder(idl);
  const order =
    argv.kind === "position"
      ? ["Position", "position", "positionAccount"]
      : argv.kind === "request"
      ? ["PositionRequest", "positionRequest", "position_request"]
      : ["PositionRequest", "positionRequest", "Position", "position", "Pool", "Perpetuals"];

  for (const name of order) {
    try {
      const decoded = coder.accounts.decode(name as any, info.data);
      console.log("✅ Decoded as:", name);
      console.dir(normalize(decoded), { depth: 8 });
      return;
    } catch {
      // try next
    }
  }

  console.log("⚠️  Could not decode with IDL. Dumping base64:");
  console.log(Buffer.from(info.data).toString("base64"));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

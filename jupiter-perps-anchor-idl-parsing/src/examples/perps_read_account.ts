import { Connection, PublicKey } from "@solana/web3.js";
import { AnchorProvider, BorshCoder, Program, Idl } from "@coral-xyz/anchor";
import yargs from "yargs";
import { hideBin } from "yargs/helpers";
import BN from "bn.js";

function shortPk58(s: string) {
  return s.length > 10 ? `${s.slice(0, 4)}…${s.slice(-4)}` : s;
}
function toPk58(x: any) {
  try {
    return new PublicKey(x).toBase58();
  } catch {
    return String(x);
  }
}

const argv = await yargs(hideBin(process.argv))
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
  .argv;

function norm(x: any): any {
  if (x instanceof BN) return x.toString();
  if (Array.isArray(x)) return x.map(norm);
  if (x && typeof x === "object") {
    const o: any = {};
    for (const [k, v] of Object.entries(x)) o[k] = norm(v);
    return o;
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
  console.log("• Owner   :", info.owner.toBase58());
  console.log("• Lamports:", info.lamports);
  console.log("• DataLen :", info.data.length);

  let idl: Idl | null = null;
  try {
    const provider = new AnchorProvider(connection, {} as any, AnchorProvider.defaultOptions());
    idl = await Program.fetchIdl(programId, provider);
  } catch {}

  if (!idl) {
    console.log("⚠️  No IDL; dumping base64:");
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
      if (name.toLowerCase().includes("position")) {
        const pos: any = decoded;
        const owner58 = toPk58(pos.owner),
          pool58 = toPk58(pos.pool);
        const cust58 = toPk58(pos.custody),
          col58 = toPk58(pos.collateralCustody);
        console.log(
          "🔎 Compact:",
          "owner:",
          shortPk58(owner58),
          "pool:",
          shortPk58(pool58),
          "cust:",
          shortPk58(cust58),
          "colCust:",
          shortPk58(col58)
        );
      }
      console.dir(norm(decoded), { depth: 8 });
      return;
    } catch {}
  }

  console.log("⚠️  Could not decode with IDL. Base64 dump:");
  console.log(Buffer.from(info.data).toString("base64"));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

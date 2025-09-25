import { Connection, PublicKey } from "@solana/web3.js";
import { getAccount, getMint } from "@solana/spl-token";
import yargs from "yargs";
import { hideBin } from "yargs/helpers";

const argv = await yargs(hideBin(process.argv))
  .option("rpc", { type: "string", demandOption: true })
  .option("ata", { type: "string", demandOption: true })
  .help().strict().argv;

(async () => {
  const connection = new Connection(argv.rpc, "confirmed");
  const ataPk = new PublicKey(argv.ata);

  try {
    const acc = await getAccount(connection, ataPk);
    const mintInfo = await getMint(connection, acc.mint);
    const ui = Number(acc.amount) / 10 ** mintInfo.decimals;
    console.log("🔎 Token Account:", ataPk.toBase58());
    console.log("• Mint   :", acc.mint.toBase58());
    console.log("• Owner  :", acc.owner.toBase58());
    console.log("• Amount :", acc.amount.toString(), `(dec=${mintInfo.decimals}, ui=${ui})`);
    console.log("• State  :", acc.isInitialized ? "initialized" : "uninitialized");
  } catch (e: any) {
    console.log("🔎 Token Account:", ataPk.toBase58());
    console.log("• Status : MISSING (not created on-chain yet)");
  }
})();

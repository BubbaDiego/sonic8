// Try plausible seed orders to discover the exact Position PDA recipe.
// Usage:
//   npx ts-node --transpile-only src/tools/find_position_pda.ts \
//     --program PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu \
//     --owner <OWNER_PUBKEY> \
//     --pool  5BUwFW4nRbftYTDMbgxykoFWqWHPzahFSNAaaaJtVKsq \
//     --custody <MARKET_CUSTODY_PUBKEY> \
//     --collat <COLLATERAL_CUSTODY_PUBKEY> \
//     [--expect 8oWD2JvGDiNU4jfCKEuVm3M6amCz11k36La2T2PJ2gvq]
//
// Tip: we print all candidates; if --expect is given, we'll tag any match.

import yargs from "yargs";
import { hideBin } from "yargs/helpers";
import { PublicKey } from "@solana/web3.js";

(async () => {
  const argv = await yargs(hideBin(process.argv))
    .option("program", { type: "string", demandOption: true })
    .option("owner",   { type: "string", demandOption: true })
    .option("pool",    { type: "string", demandOption: true })
    .option("custody", { type: "string", demandOption: true })
    .option("collat",  { type: "string", demandOption: true })
    .option("expect",  { type: "string" })
    .parse();

  const PROGRAM = new PublicKey(argv.program);
  const OWNER   = new PublicKey(argv.owner);
  const POOL    = new PublicKey(argv.pool);
  const CUSTODY = new PublicKey(argv.custody);
  const COLLAT  = new PublicKey(argv.collat);
  const EXPECT  = argv.expect ? new PublicKey(argv.expect) : undefined;

  const prefixes = [ "position", "Position" ];
  const sets: Buffer[][] = [];

  // plausible orders seen in perps-style programs
  for (const pfx of prefixes) {
    const P = Buffer.from(pfx);
    sets.push([P, OWNER.toBuffer(), POOL.toBuffer(), CUSTODY.toBuffer(), COLLAT.toBuffer()]);
    sets.push([P, OWNER.toBuffer(), CUSTODY.toBuffer(), COLLAT.toBuffer(), POOL.toBuffer()]);
    sets.push([P, POOL.toBuffer(), OWNER.toBuffer(), CUSTODY.toBuffer(), COLLAT.toBuffer()]);
    sets.push([P, POOL.toBuffer(), COLLAT.toBuffer(), CUSTODY.toBuffer(), OWNER.toBuffer()]);
    sets.push([P, CUSTODY.toBuffer(), COLLAT.toBuffer(), OWNER.toBuffer(), POOL.toBuffer()]);
    sets.push([P, COLLAT.toBuffer(), CUSTODY.toBuffer(), OWNER.toBuffer(), POOL.toBuffer()]);
  }

  // de-dup
  const uniq = new Map<string, Buffer[]>();
  for (const s of sets) uniq.set(s.map(b => b.length).join("-"), s);
  const candidates = Array.from(uniq.values());

  let hit = 0;
  for (const s of candidates) {
    const [addr, bump] = PublicKey.findProgramAddressSync(s, PROGRAM);
    const tag = EXPECT && addr.equals(EXPECT) ? "  <= MATCH expected" : "";
    console.log(addr.toBase58(), " bump=", bump, tag);
    if (tag) hit++;
  }
  if (EXPECT && hit === 0) {
    console.log("\n(no match for --expect; try other orders or a different prefix)");
  }
})();

// Discover the canonical Position PDA recipe by brute-trying plausible seed combos.
// It auto-loads pool + custodies, tries seed orders, and flags any match to --expect.
//
// Usage (example):
//   npx ts-node --transpile-only src/tools/discover_position_pda.ts \
//     --rpc https://api.mainnet-beta.solana.com \
//     --owner CofTLEqPUXscsigdvP8YWkRTDmCQ6W7GKBVKRsZ6UvLn \
//     --expect 8oWD2JvGDiNU4jfCKEuVm3M6amCz11k36La2T2PJ2gvq
//
// Prints candidates and " <= MATCH expected" when a recipe yields the Right address.
import yargs from "yargs";
import { hideBin } from "yargs/helpers";
import { Connection, PublicKey } from "@solana/web3.js";
import { Program, AnchorProvider } from "@coral-xyz/anchor";
import { IDL as PERPS_IDL } from "../idl/jupiter-perpetuals-idl.js";
const B = Buffer;
function tryCombo(programId, prefix, parts, expect) {
    const seeds = [B.from(prefix), ...parts.map((p) => p.toBuffer())];
    const [addr, bump] = PublicKey.findProgramAddressSync(seeds, programId);
    return { addr, bump, match: expect ? addr.equals(expect) : false };
}
(async () => {
    const argv = await yargs(hideBin(process.argv))
        .option("rpc", { type: "string", demandOption: true })
        .option("owner", { type: "string", demandOption: true })
        .option("expect", { type: "string" })
        .parse();
    const conn = new Connection(argv.rpc, "confirmed");
    const owner = new PublicKey(argv.owner);
    const expect = argv.expect ? new PublicKey(argv.expect) : undefined;
    const programId = new PublicKey(PERPS_IDL.metadata.address);
    const provider = new AnchorProvider(conn, {}, {});
    const program = new Program(PERPS_IDL, programId, provider);
    // Load singleton pool + custodies (so we have stable inputs)
    const pools = await program.account.pool.all();
    if (!pools?.length)
        throw new Error("No pool found");
    const poolPk = pools[0].publicKey;
    const poolAcc = pools[0].account;
    const custodies = poolAcc.custodies || [];
    console.log("program =", programId.toBase58());
    console.log("owner   =", owner.toBase58());
    console.log("pool    =", poolPk.toBase58());
    console.log("custodies =", custodies.map((c) => c.toBase58()));
    // Candidate prefixes and parts orders (keep list small and sane)
    const prefixes = ["position", "Position"];
    const parts = [owner, poolPk, ...custodies];
    function uniqPKs(arr) {
        const seen = new Set();
        const out = [];
        for (const x of arr) {
            const k = x.toBase58();
            if (!seen.has(k)) {
                seen.add(k);
                out.push(x);
            }
        }
        return out;
    }
    // Build a small set of permutations: [owner,pool], [pool,owner], and with one custody sprinkled in
    const combos = [];
    combos.push([owner, poolPk]);
    combos.push([poolPk, owner]);
    for (const c of custodies.slice(0, 4)) {
        combos.push(uniqPKs([owner, poolPk, c]));
        combos.push(uniqPKs([owner, c, poolPk]));
        combos.push(uniqPKs([poolPk, owner, c]));
    }
    let hits = 0;
    for (const pfx of prefixes) {
        for (const arr of combos) {
            const { addr, bump, match } = tryCombo(programId, pfx, arr, expect);
            const tag = match ? "  <= MATCH expected" : "";
            console.log(`${pfx} :: [${arr
                .map((x) => x.toBase58().slice(0, 4))
                .join(",")}] => ${addr.toBase58()}  bump=${bump}${tag}`);
            if (match)
                hits++;
        }
    }
    if (expect && hits === 0) {
        console.log("\nNo match for expected. Try adding/removing a custody in the combo, or different prefix case.");
    }
})();
//# sourceMappingURL=discover_position_pda.js.map
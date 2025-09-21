#!/usr/bin/env node
/* eslint-disable no-console */
import "source-map-support/register.js";
import fs from "fs";
import chalk from "chalk";
import yargs from "yargs";
import { hideBin } from "yargs/helpers";
import { PublicKey, Connection, TransactionMessage, VersionedTransaction, Keypair } from "@solana/web3.js";
import * as anchor from "@coral-xyz/anchor";
import BN from "bn.js";
import { readStdinJSON, writeJSON, resolveRepoPath, debugBlock, debugKV, prettyError, sideToIdlEnum } from "./utils.js";
function pkey(s) { return new PublicKey(s); }
function eventAuthorityFor(programId) {
    // Anchor's event authority PDA = ["__event_authority"]
    return PublicKey.findProgramAddressSync([Buffer.from("__event_authority")], programId)[0];
}
function ensureOrientation(i) {
    // Expect SOL(base)=7xS2..., USDC(quote)=G18j...
    const expectedBase = "7xS2gz2bTp3fwCC7knJvUWTEU9Tycczu6VhJYKgi1wdz";
    const expectedQuote = "G18jKKXQwBbrHeiK3C9MRXhkHsLHf7XgCSisykV46EZa";
    const swaps = [];
    let custody = i.custody;
    let collateral = i.collateralCustody;
    const baseOk = custody === expectedBase && collateral === expectedQuote;
    const flipOk = custody === expectedQuote && collateral === expectedBase;
    if (!baseOk && flipOk) {
        // Flip to correct orientation and inform caller.
        [custody, collateral] = [collateral, custody];
        swaps.push("custody<->collateralCustody");
        debugBlock(`${chalk.yellow("⚠")} Orientation fix`, [
            `Switching custody to ${custody}`,
            `Switching collateralCustody to ${collateral}`,
        ]);
    }
    // Return corrected
    return { custody, collateral, swaps };
}
async function simulateIx(conn, ix) {
    const payer = Keypair.generate(); // ephemeral
    const { blockhash } = await conn.getLatestBlockhash({ commitment: "confirmed" });
    const msg = new TransactionMessage({
        payerKey: payer.publicKey,
        recentBlockhash: blockhash,
        instructions: [ix],
    }).compileToV0Message();
    const vtx = new VersionedTransaction(msg);
    // simulate without sig verify
    const sim = await conn.simulateTransaction(vtx, { sigVerify: false, replaceRecentBlockhash: true });
    return sim;
}
function parseAnchorFromLogs(logs) {
    if (!logs)
        return {};
    const out = {};
    for (const l of logs) {
        const acc = l.match(/account:\s*([a-zA-Z_]+)/);
        if (acc)
            out.account = acc[1];
        const code = l.match(/Error Code:\s*([a-zA-Z0-9_]+)/);
        if (code)
            out.errorCode = code[1];
        if (l.trim() === "Program log: Left:")
            out._leftNext = true;
        else if (l.trim() === "Program log: Right:")
            out._rightNext = true;
        else if (out._leftNext && l.startsWith("Program log: ")) {
            out.left = l.replace("Program log: ", "").trim();
            out._leftNext = false;
        }
        else if (out._rightNext && l.startsWith("Program log: ")) {
            out.right = l.replace("Program log: ", "").trim();
            out._rightNext = false;
        }
    }
    delete out._leftNext;
    delete out._rightNext;
    return out;
}
async function cmdDryRunIncrease() {
    const input = await readStdinJSON();
    const start = Date.now();
    const rpcUrl = input.rpcUrl ?? process.env.RPC_URL ?? "https://api.mainnet-beta.solana.com";
    const programId = pkey(input.programId ?? "PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu");
    const idlPath = input.idlPath ?? resolveRepoPath("jupiter-perpetuals-idl-json.json");
    const idl = JSON.parse(fs.readFileSync(idlPath, "utf8"));
    const connection = new Connection(rpcUrl, { commitment: "confirmed" });
    const wallet = new anchor.Wallet(Keypair.generate());
    const provider = new anchor.AnchorProvider(connection, wallet, { commitment: "confirmed" });
    anchor.setProvider(provider);
    const program = new anchor.Program(idl, programId, provider);
    // Orientation check →
    const { custody, collateral, swaps } = ensureOrientation(input);
    const eventAuthority = eventAuthorityFor(programId);
    // Build accounts map (caller provides PDAs today; we’ll grow automatic PDA derivation next)
    const accountsStrict = {
        owner: input.owner,
        fundingAccount: input.fundingAccount,
        perpetuals: input.perpetuals,
        pool: input.pool,
        position: input.position, // expected provided by caller for now
        positionRequest: input.positionRequest, // idem
        positionRequestAta: input.positionRequestAta, // idem
        custody: custody,
        collateralCustody: collateral,
        inputMint: input.inputMint,
        referral: input.referral ?? input.owner, // if none, default owner
        tokenProgram: "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        associatedTokenProgram: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
        systemProgram: "11111111111111111111111111111111",
        eventAuthority: eventAuthority.toBase58(),
        program: programId.toBase58()
    };
    // Params
    const p = input.params;
    const side = sideToIdlEnum(p.side);
    const args = {
        sizeUsdDelta: new BN(p.sizeUsdDelta ?? 0),
        collateralTokenDelta: new BN(p.collateralTokenDelta ?? 0),
        side,
        priceSlippage: new BN(p.priceSlippage ?? 0),
        jupiterMinimumOut: null, // wire-up when needed
        counter: new BN(p.counter ?? 0),
    };
    // Build instruction dynamically from IDL
    const method = program.methods["createIncreasePositionMarketRequest"];
    if (!method) {
        throw new Error("IDL does not contain method createIncreasePositionMarketRequest");
    }
    const builder = method(args);
    const ix = await builder.accountsStrict(accountsStrict).instruction();
    // Simulate
    const sim = await simulateIx(connection, ix);
    const anchorInfo = parseAnchorFromLogs(sim.value?.logs ?? []);
    // Shape result
    const out = {
        ok: sim.value?.err == null,
        instruction: "createIncreasePositionMarketRequest",
        accounts: {
            ordered: ix.keys.map((k) => k.pubkey.toBase58()),
            byName: accountsStrict
        },
        logs: sim.value?.logs ?? [],
        anchor: anchorInfo,
        corrections: { swapsApplied: swaps, custodyBase: custody, custodyQuote: collateral },
        info: {
            consumedCU: sim.value?.unitsConsumed ?? 0,
            rpcUrl,
            programId: program.programId.toBase58(),
            version: "cli-perps@0.1.0"
        }
    };
    // Pretty debug (stderr)
    debugKV("RPC", { url: rpcUrl });
    debugKV("Program", { id: program.programId.toBase58(), eventAuthority: eventAuthority.toBase58() });
    debugKV("Accounts (names → pks)", accountsStrict);
    if (anchorInfo?.errorCode) {
        debugBlock(`${chalk.red("✖")} Anchor`, [
            `Code    : ${anchorInfo.errorCode}`,
            anchorInfo.account ? `Account : ${anchorInfo.account}` : "",
            anchorInfo.left ? `Left    : ${anchorInfo.left}` : "",
            anchorInfo.right ? `Right   : ${anchorInfo.right}` : "",
        ].filter(Boolean));
    }
    else {
        debugBlock(`${chalk.green("✔")} Simulation`, [
            `units: ${sim.value?.unitsConsumed ?? 0}`,
            `err  : ${sim.value?.err ? JSON.stringify(sim.value.err) : "null"}`,
        ]);
    }
    writeJSON(out);
}
async function cmdIdlNames() {
    const where = resolveRepoPath("jupiter-perpetuals-idl-json.json");
    const idl = JSON.parse(fs.readFileSync(where, "utf8"));
    const names = {
        instructions: (idl.instructions ?? []).map((i) => i.name),
        accounts: (idl.accounts ?? []).map((a) => a.name),
        types: (idl.types ?? []).map((t) => t.name),
    };
    debugBlock("IDL Catalog", [
        `instructions: ${names.instructions.length}`,
        `accounts    : ${names.accounts.length}`,
        `types       : ${names.types.length}`,
    ]);
    writeJSON({ ok: true, idlPath: where, names });
}
async function main() {
    try {
        const argv = await yargs(hideBin(process.argv))
            .scriptName("perps")
            .command("dry-run:increase", "Simulate createIncreasePositionMarketRequest. JSON on stdin", {}, async () => {
            await cmdDryRunIncrease();
        })
            .command("idl:names", "List available IDL instructions/accounts", {}, async () => {
            await cmdIdlNames();
        })
            .demandCommand(1)
            .help()
            .parse();
    }
    catch (err) {
        prettyError(err);
        writeJSON({ ok: false, error: err.message });
        process.exit(1);
    }
}
main();
//# sourceMappingURL=perps.js.map
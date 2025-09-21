/* Withdraw collateral only (collateralUsdDelta, sizeUsdDelta=0) */
import yargs from "yargs";
import { hideBin } from "yargs/helpers";
import { PublicKey, SystemProgram } from "@solana/web3.js";
import { bar, kv, ok, fail, info } from "../utils/logger.js";
import { bootstrap, getSingletonPerpetuals, getSingletonPool, findCustodyByMint, ensureAtaIx, MINTS, SYS, } from "../config/perps.js";
import { toMicroUsd, derivePdaFromIdl, sideToEnum } from "../utils/resolve.js";
import { IDL as JUP_PERPS_IDL } from "../idl/jupiter-perpetuals-idl.js";
(async () => {
    const argv = await yargs(hideBin(process.argv))
        .option("rpc", { type: "string", demandOption: true })
        .option("kp", { type: "string", demandOption: true })
        .option("market", { type: "string", choices: ["SOL", "ETH", "BTC"], demandOption: true })
        .option("side", { type: "string", choices: ["long", "short"], demandOption: true })
        .option("withdraw-usd", { type: "number", demandOption: true, describe: "USD value to withdraw from collateral" })
        .option("desired-mint", { type: "string", describe: "Receiving mint (default: collateral mint)" })
        .option("oracle-price", { type: "number" })
        .option("slip", { type: "number" })
        .option("max-price", { type: "number" })
        .option("min-price", { type: "number" })
        .option("dry-run", { type: "boolean", default: false })
        .parse();
    const { program, programId, provider, wallet } = bootstrap(argv.rpc, argv.kp);
    const perpetuals = await getSingletonPerpetuals(program);
    const pool = await getSingletonPool(program);
    const marketMint = MINTS[argv.market];
    const sideEnum = sideToEnum(argv.side);
    const custody = await findCustodyByMint(program, pool.account, marketMint);
    // For withdraw, default receiving mint = collateral mint for that side
    const defaultCollat = argv.side === "long" ? marketMint : MINTS.USDC;
    const collateralMint = new PublicKey(argv["desired-mint"] ?? defaultCollat);
    const collateralCustody = await findCustodyByMint(program, pool.account, collateralMint);
    bar("PDAs", "🧩");
    const [position] = derivePdaFromIdl(JUP_PERPS_IDL, programId, "position", {
        owner: wallet.publicKey, pool: pool.publicKey, custody: custody.pubkey, collateralCustody: collateralCustody.pubkey,
    });
    const unique = Math.floor(Date.now() / 1000);
    const [positionRequest] = derivePdaFromIdl(JUP_PERPS_IDL, programId, "positionRequest", {
        owner: wallet.publicKey, pool: pool.publicKey, custody: custody.pubkey, collateralCustody: collateralCustody.pubkey,
        seed: unique, position,
    });
    kv("Position", position.toBase58());
    kv("PosRequest", positionRequest.toBase58());
    // Receiving ATA for withdrawn tokens
    const ataInit = await ensureAtaIx(provider.connection, collateralMint, wallet.publicKey, wallet.publicKey);
    // Guardrail (must provide)
    let priceGuard = null;
    if (typeof argv["oracle-price"] === "number" && typeof argv["slip"] === "number") {
        // Withdrawing reduces exposure; for LONG use min guard, for SHORT use max guard
        const factor = argv.side === "long" ? (1 - argv.slip) : (1 + argv.slip);
        priceGuard = toMicroUsd(argv["oracle-price"] * factor);
    }
    else if (typeof argv["max-price"] === "number" && argv.side === "short") {
        priceGuard = toMicroUsd(argv["max-price"]);
    }
    else if (typeof argv["min-price"] === "number" && argv.side === "long") {
        priceGuard = toMicroUsd(argv["min-price"]);
    }
    if (!priceGuard) {
        fail("Provide guardrail: --oracle-price + --slip OR --max-price/--min-price");
        process.exit(1);
    }
    const collateralUsdDelta = toMicroUsd(argv["withdraw-usd"]);
    bar("Amounts", "🧮");
    kv("Withdraw USD", `${argv["withdraw-usd"].toFixed(6)} → ${collateralUsdDelta.toString()} μUSD`);
    // Build Tx: createDecreasePositionMarketRequest (collateral only)
    const accounts = {
        owner: wallet.publicKey,
        receivingAccount: ataInit.ata,
        position,
        positionRequest,
        custody: custody.pubkey,
        collateralCustody: collateralCustody.pubkey,
        desiredMint: collateralMint,
        perpetuals: perpetuals.publicKey,
        pool: pool.publicKey,
        tokenProgram: SYS.TOKEN_PROGRAM_ID,
        associatedTokenProgram: SYS.ASSOCIATED_TOKEN_PROGRAM_ID,
        systemProgram: SystemProgram.programId,
    };
    try {
        const [eventAuthority] = PublicKey.findProgramAddressSync([Buffer.from("__event_authority")], programId);
        accounts.eventAuthority = eventAuthority;
        accounts.program = programId;
    }
    catch { }
    const method = program.methods.createDecreasePositionMarketRequest({
        collateralUsdDelta,
        sizeUsdDelta: new (await import("../config/perps.js")).BN(0),
        side: sideEnum,
        priceSlippage: priceGuard,
    });
    const tx = await method.accounts(accounts).transaction();
    tx.feePayer = wallet.publicKey;
    tx.add(...ataInit.ixs);
    tx.recentBlockhash = (await provider.connection.getLatestBlockhash()).blockhash;
    if (argv["dry-run"]) {
        info("🧪", "Simulation only (dry-run)");
        const sim = await provider.connection.simulateTransaction(tx, [provider.wallet.payer]);
        console.log(sim);
        process.exit(0);
    }
    const sig = await provider.sendAndConfirm(tx, [provider.wallet.payer]);
    ok(`Tx sent: ${sig}`);
    info("📝", `PositionRequest = ${positionRequest.toBase58()}  (keeper will execute)\n`);
})();
//# sourceMappingURL=perps_withdraw_collateral.js.map
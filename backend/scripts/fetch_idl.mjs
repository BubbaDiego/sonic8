import { Connection, PublicKey } from "@solana/web3.js";
import * as anchor from "@coral-xyz/anchor";

const PROGRAM_ID = new PublicKey("PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu");

// Use your Helius key (or fallback to public mainnet if not set)
const RPC_URL =
  process.env.HELIUS_API_KEY
    ? `https://mainnet.helius-rpc.com/?api-key=${process.env.HELIUS_API_KEY}`
    : "https://api.mainnet-beta.solana.com";

const connection = new Connection(RPC_URL, "confirmed");

// Dummy wallet; fetchIdl does not sign
const dummyWallet = {
  publicKey: PublicKey.default,
  signAllTransactions: async (txs) => txs,
  signTransaction: async (tx) => tx
};

const provider = new anchor.AnchorProvider(connection, dummyWallet, {});
const idl = await anchor.Program.fetchIdl(PROGRAM_ID, provider);

if (!idl) {
  console.error("IDL not found on-chain for", PROGRAM_ID.toBase58());
  process.exit(1);
}

idl.metadata = idl.metadata || {};
idl.metadata.address = PROGRAM_ID.toBase58();
console.log(JSON.stringify(idl, null, 2));

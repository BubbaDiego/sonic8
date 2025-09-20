import { PublicKey } from "@solana/web3.js";

export const PERPETUALS_PROGRAM_ID = "PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu";
export const USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";

const PROGRAM_PK = new PublicKey(PERPETUALS_PROGRAM_ID);

const PERPETUALS_PDA = PublicKey.findProgramAddressSync(
  [Buffer.from("perpetuals")],
  PROGRAM_PK
)[0].toBase58();

const EVENT_AUTHORITY_PDA = PublicKey.findProgramAddressSync(
  [Buffer.from("__event_authority")],
  PROGRAM_PK
)[0].toBase58();

export type MarketConfig = {
  pool: string;
  baseCustody: string;
  quoteCustody: string;
  perpetuals?: string;
  fundingAccount?: string;
  referral?: string;
  eventAuthority?: string;
  baseMint?: string;
  quoteMint?: string;
};

export const MARKETS: Record<string, MarketConfig> = {
  "SOL-PERP": {
    perpetuals: PERPETUALS_PDA,
    pool: "5BUwFW4nRbftYTDMbgxykoFWqWHPzahFSNAaaaJtVKsq",
    baseCustody: "7xS2gz2bTp3fwCC7knJvUWTEU9Tycczu6VhJYKgi1wdz",
    quoteCustody: "G18jKKXQwBbrHeiK3C9MRXhkHsLHf7XgCSisykV46EZa",
    eventAuthority: EVENT_AUTHORITY_PDA,
    baseMint: "So11111111111111111111111111111111111111112",
    quoteMint: USDC_MINT,
  },
};

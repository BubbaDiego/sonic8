use std::{fs, path::PathBuf, str::FromStr, time::SystemTime};

use anyhow::{anyhow, Result};
use bip39::{Language, Mnemonic, Seed};
use bs58;
use clap::{Parser, Subcommand};
use ed25519_dalek::{Keypair, PublicKey, SecretKey};
use serde::Serialize;
use serde_json::json;
use slip10::{BIP32Path, Curve};

mod ops;

#[derive(Parser, Debug)]
#[command(name = "gmx_runner", version)]
struct Cli {
    /// Subcommand to run
    #[command(subcommand)]
    command: Commands,

    /// Cluster (mainnet|devnet). We’ll use this later for GMX endpoints.
    #[arg(long, default_value = "mainnet")]
    cluster: String,

    /// Optional explicit path to signer.txt (12-word mnemonic) or a JSON keypair file
    #[arg(long)]
    signer: Option<PathBuf>,

    /// Print only JSON to stdout
    #[arg(long)]
    json: bool,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Quick sanity: derive wallet, print pubkey & cluster
    Health,
    /// List available perp markets (stub until SDK wired)
    Markets,
    /// List your perp positions (stub until SDK wired)
    Positions,
    /// Deposit USDC (stub placeholder)
    Deposit { amount: f64 },
    /// Open position (stub placeholder)
    Open {
        market: String,
        side: String,
        size_usd: f64,
        #[arg(long)] price: Option<f64>,
    },
    /// Close position (stub placeholder)
    Close { market: String },
    /// Cancel order by id (stub placeholder)
    Cancel { order_id: String },
}

#[derive(Debug)]
struct Wallet {
    keypair: Keypair,
    pubkey_bs58: String,
}

#[derive(thiserror::Error, Debug)]
enum WalletErr {
    #[error("signer not found")]
    NotFound,
    #[error("unsupported signer file format")]
    Unsupported,
    #[error("invalid mnemonic: {0}")]
    BadMnemonic(String),
    #[error("derivation failed: {0}")]
    Derive(String),
}

fn read_text(path: &PathBuf) -> Result<String> {
    Ok(fs::read_to_string(path)?)
}

fn try_find_signer_txt() -> Option<PathBuf> {
    // Walk up a few parents to find repo-root/signerr.txt
    let mut cur = std::env::current_dir().ok()?;
    for _ in 0..6 {
        let candidate = cur.join("signer.txt");
        if candidate.exists() {
            return Some(candidate);
        }
        cur = cur.parent()?.to_path_buf();
    }
    None
}

fn wallet_from_mnemonic_words(words: &str) -> std::result::Result<Wallet, WalletErr> {
    let clean = words.trim().replace('\n', " ");
    let wc = clean.split_whitespace().count();
    if wc != 12 && wc != 24 {
        return Err(WalletErr::BadMnemonic(format!(
            "expected 12 or 24 words, got {}",
            wc
        )));
    }
    let mnemonic = Mnemonic::parse_in(Language::English, clean)
        .map_err(|e| WalletErr::BadMnemonic(e.to_string()))?;
    let seed = Seed::new(&mnemonic, ""); // no passphrase
    // Standard Solana path: m/44'/501'/0'/0'
    let path = BIP32Path::from_str("m/44'/501'/0'/0'")
        .map_err(|e| WalletErr::Derive(e.to_string()))?;
    let derived =
        slip10::derive_key_from_path(seed.as_bytes(), Curve::Ed25519, &path)
            .map_err(|e| WalletErr::Derive(e.to_string()))?;

    let secret = SecretKey::from_bytes(&derived.key)
        .map_err(|e| WalletErr::Derive(e.to_string()))?;
    let public = PublicKey::from(&secret);
    let mut bytes = [0u8; 64];
    bytes[..32].copy_from_slice(&secret.to_bytes());
    bytes[32..].copy_from_slice(&public.to_bytes());
    let keypair = Keypair::from_bytes(&bytes)
        .map_err(|e| WalletErr::Derive(e.to_string()))?;
    let pubkey_bs58 = bs58::encode(public.to_bytes()).into_string();
    Ok(Wallet { keypair, pubkey_bs58 })
}

fn wallet_from_signer_path(path: &PathBuf) -> std::result::Result<Wallet, WalletErr> {
    // If file looks like JSON keypair array, we could support it later.
    // For now we expect 12/24-word mnemonic in signer.txt.
    let content = read_text(path).map_err(|_| WalletErr::NotFound)?;
    wallet_from_mnemonic_words(&content)
}

fn resolve_wallet(signer_flag: &Option<PathBuf>) -> Result<Wallet> {
    let path = if let Some(p) = signer_flag {
        p.to_path_buf()
    } else if let Some(p) = try_find_signer_txt() {
        p
    } else {
        return Err(anyhow!(WalletErr::NotFound));
    };
    Ok(wallet_from_signer_path(&path)?)
}

#[derive(Serialize)]
struct ErrorBody<'a> {
    ok: bool,
    code: u16,
    err: &'a str,
}

fn print_json<T: Serialize>(val: &T) {
    println!("{}", serde_json::to_string_pretty(val).unwrap());
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();
    let wallet = resolve_wallet(&cli.signer)?;
    let now = SystemTime::now();
    match cli.command {
        Commands::Health => {
            let body = ops::Health {
                ok: true,
                cluster: cli.cluster.clone(),
                wallet_pubkey: wallet.pubkey_bs58.clone(),
            };
            print_json(&body);
        }
        Commands::Markets => {
            let markets = ops::list_markets().await?;
            print_json(&json!({
                "ok": true,
                "cluster": cli.cluster,
                "wallet_pubkey": wallet.pubkey_bs58,
                "markets": markets,
                "ts": now.duration_since(SystemTime::UNIX_EPOCH).unwrap().as_secs()
            }));
        }
        Commands::Positions => {
            let positions = ops::list_positions(&wallet.pubkey_bs58).await?;
            print_json(&json!({
                "ok": true,
                "cluster": cli.cluster,
                "wallet_pubkey": wallet.pubkey_bs58,
                "positions": positions,
                "ts": now.duration_since(SystemTime::UNIX_EPOCH).unwrap().as_secs()
            }));
        }
        Commands::Deposit { .. } => {
            print_json(&ErrorBody { ok: false, code: 501, err: "deposit not yet implemented" });
        }
        Commands::Open { .. } => {
            print_json(&ErrorBody { ok: false, code: 501, err: "open not yet implemented" });
        }
        Commands::Close { .. } => {
            print_json(&ErrorBody { ok: false, code: 501, err: "close not yet implemented" });
        }
        Commands::Cancel { .. } => {
            print_json(&ErrorBody { ok: false, code: 501, err: "cancel not yet implemented" });
        }
    }
    Ok(())
}

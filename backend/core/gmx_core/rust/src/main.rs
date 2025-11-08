use std::{fs, path::PathBuf, str::FromStr};

use anyhow::{anyhow, Result};
use bip39::{Language, Mnemonic, Seed};
use clap::{Parser, Subcommand};
use serde_json::json;
use slip10::{BIP32Path, Curve};

use solana_sdk::signature::{Keypair as SolKeypair, Signer};

mod ops;

#[derive(Parser, Debug)]
#[command(name = "gmx_runner", version)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
    #[arg(long, default_value = "mainnet")]
    cluster: String,
    #[arg(long)]
    signer: Option<PathBuf>,
    #[arg(long)]
    json: bool,
}

#[derive(Subcommand, Debug)]
enum Commands {
    Health,
    Markets,
    Positions,
}

#[derive(thiserror::Error, Debug)]
enum WalletErr {
    #[error("signer not found")]
    NotFound,
    #[error("invalid mnemonic: {0}")]
    BadMnemonic(String),
    #[error("derivation failed: {0}")]
    Derive(String),
}

fn read_text(path: &PathBuf) -> Result<String> {
    Ok(fs::read_to_string(path)?)
}

fn try_find_signer_txt() -> Option<PathBuf> {
    let mut cur = std::env::current_dir().ok()?;
    for _ in 0..6 {
        let candidate = cur.join("signer.txt");
        if candidate.exists() { return Some(candidate); }
        cur = cur.parent()?.to_path_buf();
    }
    None
}

fn solana_keypair_from_mnemonic(words: &str) -> std::result::Result<SolKeypair, WalletErr> {
    let clean = words.trim().replace('\n', " ");
    let wc = clean.split_whitespace().count();
    if wc != 12 && wc != 24 { return Err(WalletErr::BadMnemonic(format!("got {wc} words"))); }
    let mnemonic = Mnemonic::parse_in(Language::English, clean)
        .map_err(|e| WalletErr::BadMnemonic(e.to_string()))?;
    let seed = Seed::new(&mnemonic, "");
    let path = BIP32Path::from_str("m/44'/501'/0'/0'")
        .map_err(|e| WalletErr::Derive(e.to_string()))?;
    let derived = slip10::derive_key_from_path(seed.as_bytes(), Curve::Ed25519, &path)
        .map_err(|e| WalletErr::Derive(e.to_string()))?;
    let kp = SolKeypair::from_bytes(&{
        use ed25519_dalek::{SecretKey, PublicKey};
        let secret = SecretKey::from_bytes(&derived.key).map_err(|e| WalletErr::Derive(e.to_string()))?;
        let public = PublicKey::from(&secret);
        let mut bytes = [0u8; 64];
        bytes[..32].copy_from_slice(&secret.to_bytes());
        bytes[32..].copy_from_slice(&public.to_bytes());
        bytes
    }).map_err(|e| WalletErr::Derive(e.to_string()))?;
    Ok(kp)
}

fn resolve_wallet(signer_flag: &Option<PathBuf>) -> Result<SolKeypair> {
    let path = if let Some(p) = signer_flag { p.clone() }
               else if let Some(p) = try_find_signer_txt() { p }
               else { return Err(anyhow!(WalletErr::NotFound)); };
    let content = read_text(&path)?;
    Ok(solana_keypair_from_mnemonic(&content)?)
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();
    let wallet = resolve_wallet(&cli.signer)?;
    let client = ops::build_client(&cli.cluster, &wallet)?;

    match cli.command {
        Commands::Health => {
            let body = ops::health(&client, &wallet, &cli.cluster).await?;
            println!("{}", serde_json::to_string_pretty(&body)?);
        }
        Commands::Markets => {
            println!("{}", serde_json::to_string_pretty(&json!({"ok":false,"err":"markets not wired yet"}))?);
        }
        Commands::Positions => {
            println!("{}", serde_json::to_string_pretty(&json!({"ok":false,"err":"positions not wired yet"}))?);
        }
    }
    Ok(())
}

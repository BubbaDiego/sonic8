use anyhow::Result;
use serde::Serialize;

use solana_sdk::signature::{Keypair as SolKeypair, Signer};
use solana_sdk::pubkey::Pubkey;

use gmsol_sdk::{
    Client,
    ops::ExchangeOps,
    solana_utils::cluster::Cluster,
    pda,
};

#[derive(Debug, Serialize)]
pub struct Health {
    pub ok: bool,
    pub cluster: String,
    pub wallet_pubkey: String,
    pub store_address: String,
}

/// Build a GMSOL client from a solana Keypair
pub fn build_client(cluster: &str, wallet: &SolKeypair) -> Result<Client<'_>> {
    let cl = match cluster {
        "mainnet" => Cluster::Mainnet,
        "devnet" => Cluster::Devnet,
        other => anyhow::bail!("unsupported cluster: {other}"),
    };
    Ok(Client::new(cl, wallet)?)
}

pub async fn health(client: &Client<'_>, wallet: &SolKeypair, cluster: &str) -> Result<Health> {
    let store = client.find_store_address("");
    Ok(Health {
        ok: true,
        cluster: cluster.to_string(),
        wallet_pubkey: wallet.pubkey().to_string(),
        store_address: store.to_string(),
    })
}

/* ---- Upcoming wiring (next pass) ----

pub async fn list_markets(client: &Client<'_>) -> Result<Vec<Market>> {
    // Option A: discovery helpers (SDK): gmsol_sdk::discover::market::MarketDiscovery
    // Option B: read TokenMap/Market accounts via SDK RPC helpers.
    todo!()
}

pub async fn list_positions(client: &Client<'_>, owner: &Pubkey) -> Result<Vec<Position>> {
    // Use PDAs + decode with SDK types:
    //  - pda::find_position_address(...)
    //  - fetch & serde decode to gmsol_store::states::Position
    todo!()
}

pub async fn open_position(client: &Client<'_>, market_token: &Pubkey, is_long: bool,
                           size_usd: u64, is_market: bool, acceptable_price: u128) -> Result<String> {
    let store = client.find_store_address("");
    let (txn, _order) = client
        .market_increase(&store, market_token, is_long, size_usd, is_market, acceptable_price)
        .build_with_address()
        .await?;
    let sig = txn.send().await?;
    Ok(sig.to_string())
}

*/

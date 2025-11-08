use serde::Serialize;

#[derive(Debug, Serialize)]
pub struct Health {
    pub ok: bool,
    pub cluster: String,
    pub wallet_pubkey: String,
}

#[derive(Debug, Serialize)]
pub struct Market {
    pub symbol: String,
    pub status: String,
}

#[derive(Debug, Serialize)]
pub struct Position {
    pub market: String,
    pub side: String,
    pub size_usd: f64,
    pub entry_price: f64,
    pub mark_price: f64,
    pub pnl_usd: f64,
    pub liq_price: Option<f64>,
    pub updated_at: String,
}

/// Placeholder: return empty market list until we wire GMX SDK.
pub async fn list_markets() -> anyhow::Result<Vec<Market>> {
    Ok(vec![]) // to be filled with sanctioned GMX markets
}

/// Placeholder: return empty positions until SDK is wired.
pub async fn list_positions(_wallet: &str) -> anyhow::Result<Vec<Position>> {
    Ok(vec![]) // to be filled with sanctioned GMX positions
}

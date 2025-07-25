
"""DailySwingService – fetch 24 h high / low for BTC, ETH, SOL.

Primary source: CoinGecko. Fallback: Binance single‑ticker endpoint.
Simplified implementation; production code should add retry / back‑off / caching.

Returned dict shape:
    { "BTC": {"high": 69000.0, "low": 66000.0}, ... }
"""

import requests
import logging
from typing import Dict

class DailySwingService:
    CG_URL = "https://api.coingecko.com/api/v3/coins/markets"
    BINANCE_URL = "https://api.binance.com/api/v3/ticker/24hr"

    def _from_coingecko(self, assets):
        ids_map = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana"}
        params = {
            "vs_currency": "usd",
            "ids": ",".join(ids_map[a] for a in assets),
        }
        r = requests.get(self.CG_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        out = {}
        for entry in data:
            sym = entry["symbol"].upper()
            if sym == "BTC":
                sym = "BTC"
            elif sym == "ETH":
                sym = "ETH"
            elif sym == "SOL":
                sym = "SOL"
            out[sym] = {"high": float(entry["high_24h"]), "low": float(entry["low_24h"])}
        return out

    def _from_binance(self, assets):
        out = {}
        for sym in assets:
            pair = f"{sym}USDT"
            r = requests.get(self.BINANCE_URL, params={"symbol": pair}, timeout=10)
            if r.status_code != 200:
                raise RuntimeError("Binance API failure")
            j = r.json()
            out[sym] = {"high": float(j["highPrice"]), "low": float(j["lowPrice"])}
        return out

    def fetch(self, assets):
        try:
            return self._from_coingecko(assets)
        except Exception as e:
            logging.warning("CoinGecko fetch failed, fallback to Binance: %s", e)
            return self._from_binance(assets)

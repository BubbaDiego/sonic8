# monitor/core/monitor_service.py

import subprocess
import time
import requests
import os
import glob
from datetime import datetime
from backend.core.logging import log

class MonitorService:
    def fetch_sp500_index(self):
        """Fetch the current S&P 500 index price using Yahoo Finance."""
        url = "https://query1.finance.yahoo.com/v7/finance/quote"
        params = {"symbols": "^GSPC"}
        delay = 0.5
        attempts = 2
        for attempt in range(1, attempts + 1):
            try:
                response = requests.get(url, params=params, timeout=(2.0, 4.0))
                response.raise_for_status()
                data = response.json()
                quote = data.get("quoteResponse", {}).get("result", [{}])[0]
                return quote.get("regularMarketPrice")
            except (requests.Timeout, requests.ConnectionError) as exc:
                log.warning(
                    f"[SP500Fetch] timeout ({attempt}/{attempts}): {exc}",
                    source="MonitorService",
                )
            except Exception as exc:
                log.error(f"[SP500Fetch] failed: {exc}")
                break
            if attempt < attempts:
                time.sleep(delay)
                delay *= 2
        return None

    def fetch_prices(self):
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": "bitcoin,ethereum,solana", "vs_currencies": "usd"}
        delay = 0.5
        attempts = 2
        for attempt in range(1, attempts + 1):
            try:
                response = requests.get(url, params=params, timeout=(2.0, 4.0))
                response.raise_for_status()
                data = response.json()
                return {
                    "BTC": data.get("bitcoin", {}).get("usd"),
                    "ETH": data.get("ethereum", {}).get("usd"),
                    "SOL": data.get("solana", {}).get("usd"),
                    "SPX": self.fetch_sp500_index(),
                }
            except (requests.Timeout, requests.ConnectionError) as exc:
                log.warning(
                    f"[PriceFetch] timeout ({attempt}/{attempts}): {exc}",
                    source="MonitorService",
                )
            except Exception as exc:
                log.error(f"[PriceFetch] failed: {exc}")
                break
            if attempt < attempts:
                time.sleep(delay)
                delay *= 2
        return {}


    def run_post_tests(self, test_pattern="test_core/tests/test_*.py"):

        """Run a small POST-test suite if available."""
        files = sorted(glob.glob(test_pattern))
        if not files:
            log.warning(f"POST tests not found: {test_pattern}")
            return {"success": True, "skipped": True, "timestamp": datetime.utcnow().isoformat()}

        result = subprocess.run(
            ["pytest", *files],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.decode(),
            "stderr": result.stderr.decode(),
            "timestamp": datetime.utcnow().isoformat()
        }

    def check_xcom(self):
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Stubbed XCOM check passed"
        }

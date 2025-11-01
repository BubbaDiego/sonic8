import json
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

Json = Dict[str, Any]

class HttpError(RuntimeError):
    pass

class GmxRestClient:
    """
    Minimal REST v2 client for GMX.

    Docs: REST v2 (tickers, tokens, markets, markets/info, candles, apy)
    """
    def __init__(self, hosts: List[str], timeout: float = 10.0, ua: str = "sonic7-gmx-core/phase2"):
        self.hosts = [h.rstrip("/") for h in hosts if h]
        if not self.hosts:
            raise ValueError("At least one REST host required")
        self.timeout = timeout
        self.ua = ua

    def _get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Json:
        q = f"?{urlencode(params)}" if params else ""
        last_err: Optional[Exception] = None
        for base in self.hosts:
            url = f"{base}{path}{q}"
            req = Request(url, headers={"User-Agent": self.ua})
            try:
                with urlopen(req, timeout=self.timeout) as resp:
                    data = resp.read().decode("utf-8")
                    return json.loads(data)
            except (HTTPError, URLError, TimeoutError) as e:
                last_err = e
                continue
        raise HttpError(f"All REST hosts failed for {path}{q}: {last_err}")

    # ---- Oracle / prices
    def ping(self) -> Json:
        return self._get_json("/ping")

    def get_tickers(self) -> Json:
        # Returns latest price data keyed by tokenSymbol
        return self._get_json("/prices/tickers")

    def get_candles(self, token_symbol: str, period: str = "1h", start: Optional[int] = None, end: Optional[int] = None) -> Json:
        params: Dict[str, Any] = {"tokenSymbol": token_symbol, "period": period}
        if start: params["startTime"] = start
        if end: params["endTime"] = end
        return self._get_json("/prices/candles", params)

    # ---- Tokens / markets
    def get_tokens(self) -> Json:
        return self._get_json("/tokens")

    def get_markets(self) -> Json:
        return self._get_json("/markets")

    def get_markets_info(self) -> Json:
        # Detailed market info (liquidity, open interest, rates, etc.)
        return self._get_json("/markets/info")


Endpoints per GMX docs (Oracle, Markets, Info). 
docs.gmx.io
+1

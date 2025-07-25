Free Crypto APIs for 24h High/Low Price Data

To reliably obtain 24-hour high and low prices for Bitcoin (BTC), Ethereum (ETH), and Solana (SOL), several free APIs are available. Below we compare three solid options that meet the criteria: no-cost (with generous or no API key requirements), accurate data, and support for 24h stats (with some flexibility for historical or custom intervals). For each API, key details like endpoints, authentication, update frequency, rate limits, historical data, and any quirks or reliability notes are provided.

CoinGecko API

CoinGecko is a popular cryptocurrency data aggregator offering a free public REST API. It provides up-to-date market data for thousands of coins without requiring an API key

bannerbear.com

. High and low prices over the past 24 hours are directly included in its responses for each asset. Key features:

Endpoint Example: GET https://api.coingecko.com/api/v3/coins/markets?vs\_currency=USD\&ids=bitcoin,ethereum,solana – returns a JSON array of coins with fields like high\_24h and low\_24h for the last 24h period

coingecko.com

. For example, the JSON contains "high\_24h": ... and "low\_24h": ... values for each coin’s 24h high and low

coingecko.com

. (Alternatively, the /coins/{id} endpoint’s market\_data also includes high\_24h/low\_24h for multiple currencies.)

Authentication: None required for the free API. No API key is needed by default

bannerbear.com

. (CoinGecko does offer a “demo” API key for higher stable rate limits, but it’s optional for basic use.)

Data Refresh Frequency: CoinGecko updates most market data on a 1–5 minute interval on the free API

support.coingecko.com

. This ensures 24h high/low stats are very fresh (usually within a few minutes of real-time). Paid tiers have faster updates (e.g. 30s), but for free users data is cached roughly every few minutes

support.coingecko.com

.

Rate Limits: The public plan allows around 5–15 calls per minute (dynamically, depending on load)

support.coingecko.com

. With a free registered API key (demo plan), this increases to a stable 30 calls/minute

support.coingecko.com

. In practice, moderate use is fine; hitting the API too fast may result in 429 errors. For occasional queries (e.g. a few times per hour) this is well within limits.

Historical Data: CoinGecko’s API supports historical price data. While it doesn’t let you query an arbitrary “rolling” window by a single call, it offers endpoints to get daily OHLC or price charts. For example, /coins/{id}/ohlc or /market\_chart can provide past daily open/high/low/close data

coingecko.com

coingecko.com

. You can retrieve up to 90 days of minute/hour data or extensive daily data (CoinGecko provides at least 90 days of history without an API key, and more with certain endpoints)

mixedanalytics.com

. This means you can calculate historical daily high-low swings by fetching the OHLC for those days.

Reliability \& Maintenance: CoinGecko is well-known for data quality and is actively maintained. The free API has been around for years and is used in many projects. One quirk is that heavy usage might require an API key or backoff – if you need higher throughput or more stability, using their free key (or paid plans) is suggested. Overall, CoinGecko’s data (sourced from many exchanges) is comprehensive and long-term viable, making it a top choice for 24h high/low stats.

CoinPaprika API

CoinPaprika provides a free cryptocurrency API that’s also rich in market data. It is an aggregator like CoinGecko and covers many coins. Notably, the free tier allows querying price statistics including (in USD by default) possibly the 24h high and low. Important details:

Endpoint Example: GET https://api.coinpaprika.com/v1/tickers/{coin\_id}?quotes=USD – returns the ticker data for a given coin (e.g. use btc-bitcoin, eth-ethereum, sol-solana as the coin\_id for BTC, ETH, SOL respectively) with USD quote data. The JSON includes fields under a quotes object. For example, you’ll see quotes.USD.price for current price, and associated 24h metrics. CoinPaprika’s documentation indicates it provides ATH, percent changes, volume, etc., and it’s expected to include 24h high and low if available. (If 24h high/low aren’t directly given, they can be derived from historical data — see below.) By default only USD data is returned unless specified. You can request multiple quote currencies (e.g. quotes=USD,BTC) if needed

api.coinpaprika.com

.

Authentication: No API key required for the open free endpoints. The ticker endpoints are public. (They do have paid plans and an optional API key system, but for basic use no key or account is needed.)

Data Refresh Frequency: CoinPaprika’s ticker data updates every 1 minute on the free API

api.coinpaprika.com

. This means the 24h high/low values will be recalculated or updated each minute, providing very up-to-date stats.

Rate Limits: The free usage is quite generous. According to CoinPaprika, a single IP can do up to 10 requests per second (i.e. 600 per minute) before being limited

api.coinpaprika.com

. Additionally, the free tier allows ~20,000 calls per month for personal projects

coinpaprika.com

coinpaprika.com

. In practice, this is plenty for querying a few coins’ data periodically. Hitting the 600/minute burst limit is unlikely in typical use; if you stay well under that (e.g. a few calls per minute) you’ll be safe from throttling.

Historical Data: CoinPaprika’s API supports historical OHLCV data. On the free plan, you have access to 1 year of daily historical data for coins

coinpaprika.com

coinpaprika.com

. There is an endpoint like /v1/coins/{coin\_id}/ohlcv/today or /historical that provides daily open, high, low, close, volume for past dates

api.coinpaprika.com

marketplace.quicknode.com

. This means you can retrieve the daily high and low for each day going back up to a year (free tier) – useful if you need to compute daily swings over time. However, the free API may not support arbitrary window queries (e.g. you cannot directly ask “what was the high between 10am and 4pm yesterday” – you would need to pull the relevant historical data and calculate it).

Reliability \& Quirks: CoinPaprika is a reliable service known for fast updates. It aggregates data from many sources and has been in operation for several years. One quirk is that the set of quote currencies for free calls is somewhat limited (USD, BTC, ETH are allowed by default)

api.coinpaprika.com

. USD is usually the main quote for price stats, so this is fine for most cases. Another consideration is the free tier limits: 20k calls/month means it’s free for non-commercial use but heavy enterprise usage would require a paid plan. For long-term viability, CoinPaprika appears committed to maintaining a free tier for basic users (with active documentation and even client libraries). In summary, it’s a solid choice for 24h high/low data with the bonus of easy access to historical daily highs and lows.

Binance API (Exchange Data)

Binance – as one of the largest crypto exchanges – offers a free API endpoint for 24-hour price statistics on trading pairs. Using Binance’s API for BTC, ETH, and SOL (against a stablecoin like USDT) gives you real-time 24h high and low directly from the exchange’s market data. Key points:

Endpoint Example: GET https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT – returns 24h stats for Bitcoin/USDT. The JSON response includes fields highPrice and lowPrice, which are the highest and lowest traded prices in the last 24 hours

developers.binance.com

. For example, a response snippet looks like: "highPrice": "100.00000000", "lowPrice": "0.10000000", ... (along with other stats such as volume, price change, etc.)

developers.binance.com

. You would use ETHUSDT for Ethereum and SOLUSDT for Solana, respectively, or any other trading pair available on Binance (e.g. BTCBUSD).

Authentication: No API key required for this public endpoint. Binance’s public market data APIs can be accessed freely. (No sign-up needed unless you start using private account endpoints.)

Data Refresh Frequency: The data is essentially real-time, since it’s coming directly from live market prices on Binance. The 24hr ticker endpoint provides a rolling 24-hour window ending at the time of your request

developers.binance.com

. Every request pulls the latest 24h high/low up to that second. There’s no caching delay on Binance’s end for this endpoint – it reflects the exchange’s current stats (Binance updates these continuously as trades occur).

Rate Limits: Binance uses a weight-based rate limit system. Each single-symbol /ticker/24hr request has a small weight (1), and an IP can use up to 1200 weight per minute (equivalent to 1200 single requests/min) in the default limits. In practical terms, you can query this endpoint very frequently without hitting limits – e.g. querying a few symbols even every few seconds is fine. (If you omit the symbol to get all market tickers in one call, that has a higher weight of 40

developers.binance.com

, but for just 3 symbols it’s more efficient to call 3 times separately.) Binance’s limits are generous on the free API, making it suitable for high-frequency data pulls if needed.

Historical Data: Binance’s API supports historical price data via its Klines (candlesticks) endpoint. For flexibility beyond the last 24h, you can use GET /api/v3/klines with interval=1d to retrieve daily OHLC data for each asset. For example, you can get yesterday’s candle (which includes that day’s high and low) or a range of days. This allows you to gather daily high/low values for past dates. If you needed a custom time window (say, high/low over the last 6 hours), you could use a shorter interval (like 1-minute klines) to get the price data and then compute the high/low. However, Binance does not provide a direct “rolling X-hour high/low” – you’d have to derive that from raw data.

Reliability \& Quirks: Binance’s API is very reliable and fast for real-time data. Because it’s an exchange, the prices represent Binance’s market specifically – which for major assets is usually in line with global averages, though minor discrepancies can exist across exchanges. One consideration is market pair selection: to use this for “the price of BTC”, you must choose a trading pair (BTC vs USD stablecoin). BTC/USDT is the most liquid pair on Binance and a good proxy for USD price. Users in certain regions may face geographical restrictions with the main Binance API domain; Binance has alternative domains (like data.binance.com or api.binance.us for US) if needed

mixedanalytics.com

mixedanalytics.com

. For most, the standard endpoint is accessible. In terms of long-term viability, Binance is a major platform and is expected to maintain its API, though note it’s an exchange API (focused on current market data) rather than a historical data service. It’s excellent for live 24h stats and robust under heavy load.

Additional Considerations

Each of the above APIs offers free access to 24-hour high/low price data, but they have different strengths:

Data Quality: Aggregators like CoinGecko and CoinPaprika provide a broad market view (averaged across many exchanges) which can be useful for a general “global” price high/low. Binance provides a specific exchange’s data, which is extremely accurate for that marketplace (and by extension a good indicator for global price, since Binance has high liquidity). All are reputable in terms of data accuracy.

Flexibility in Time Windows: None of these free APIs directly let you query an arbitrary time window’s high/low in one call (they default to the standard rolling 24h or daily periods). However, both CoinGecko and CoinPaprika have historical endpoints that you can leverage to compute high/low over custom periods. For example, to get the high-low for a specific date, you might fetch that day’s OHLC data. If truly flexible intraday windows are needed (e.g. 12h window), you could retrieve smaller interval data (Binance’s 1-min candles or CoinGecko’s market\_chart data) and calculate the min/max. This may require some coding on your end, since free APIs typically don’t offer an out-of-the-box “custom window” high/low.

Rate Limits and Usage: For light to moderate use (a few API calls per minute), all three options work without cost. If your application needs higher request volumes, Binance’s API stands out as it can handle very frequent calls without hitting limits easily. CoinGecko and CoinPaprika free tiers are sufficient for periodic updates (e.g. updating a dashboard every few minutes). If you find CoinGecko’s default limit (5-15/min) too restrictive, using their free demo key (30/min) or switching to CoinPaprika (much higher limit) are solutions.

Long-term Viability: CoinGecko and CoinPaprika have explicit commitments to their free APIs (with optional paid plans) and active documentation, suggesting they will remain available long-term for the community. Binance’s API is also expected to persist (it's critical for many traders/bots), though being an exchange, changes can occur if market conditions or regulations change – they generally give notice for any breaking changes.

If none of the free options fully meet your needs (for example, if you require multiple custom time-frame queries or enterprise-level reliability), you might consider using a combination of these services or looking at paid plans. There are also other free APIs not detailed here (e.g. CryptoCompare offers free API keys with generous monthly limits and provides 24h stats and historical data

mixedanalytics.com

coingecko.com

, though an API key is required). In practice, many developers use CoinGecko’s free API as a first choice for its ease of use and no-key access, perhaps backed by exchange APIs like Binance for real-time data. By comparing and possibly blending these sources, you can ensure you have accurate 24-hour high/low data for BTC, ETH, and SOL with the flexibility to calculate daily price swings and even extended periods as needed. Sources:

CoinGecko API Documentation – 24h high/low in coin market data

coingecko.com

bannerbear.com

CoinGecko Support – Data update frequency and rate limits

support.coingecko.com

support.coingecko.com

CoinPaprika API Docs – Ticker endpoint info and update interval

api.coinpaprika.com

api.coinpaprika.com

CoinPaprika Terms – Free API rate limit (10 requests/sec per IP)

api.coinpaprika.com

CoinPaprika Pricing – Free plan features (1-year history, call limits)

coinpaprika.com

coinpaprika.com

Binance API Docs – 24hr ticker endpoint example (highPrice/lowPrice)

developers.binance.com

Binance API Docs – Note on 24hr rolling window vs request time

developers.binance.com

Citations



How to Visualize Cryptocurrency Updates with CoinGecko and Bannerbear (No Code) - Bannerbear



https://www.bannerbear.com/blog/how-to-visualize-cryptocurrency-updates-with-coingecko-no-code/



Crypto API for Analytics \& Tools - CoinGecko



https://www.coingecko.com/en/api/analytics-tools



How often does data get updated or refreshed? – CoinGecko



https://support.coingecko.com/hc/en-us/articles/4538807536665-How-often-does-data-get-updated-or-refreshed



What is the rate limit for CoinGecko API (public plan)? – CoinGecko



https://support.coingecko.com/hc/en-us/articles/4538771776153-What-is-the-rate-limit-for-CoinGecko-API-public-plan



How to Fetch Crypto Data Using Python (With Examples) | CoinGecko API



https://www.coingecko.com/learn/python-query-coingecko-api



How to Fetch Crypto Data Using Python (With Examples) | CoinGecko API



https://www.coingecko.com/learn/python-query-coingecko-api



Top Free Public Crypto APIs for Google Sheets \[2024] | API Connector



https://mixedanalytics.com/knowledge-base/top-free-crypto-apis/

Coinpaprika



https://api.coinpaprika.com/

Coinpaprika



https://api.coinpaprika.com/

Coinpaprika API (1.5.5)



https://api.coinpaprika.com/docs/1.5



CoinPaprika API - Plans and Pricing



https://coinpaprika.com/api/pricing/



CoinPaprika API - Plans and Pricing



https://coinpaprika.com/api/pricing/



CoinPaprika API - Plans and Pricing



https://coinpaprika.com/api/pricing/

Coinpaprika API (1.6.1)



https://api.coinpaprika.com/docs/1.6



Coinpaprika Crypto Price API - QuickNode Marketplace



https://marketplace.quicknode.com/add-on/coinpaprika-price-market-data



24hr Ticker Price Change Statistics | Binance Open Platform



https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/24hr-Ticker-Price-Change-Statistics



All Market Tickers Streams | Binance Open Platform



https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/All-Market-Tickers-Streams



24hr Ticker Price Change Statistics | Binance Open Platform



https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/24hr-Ticker-Price-Change-Statistics



Top Free Public Crypto APIs for Google Sheets \[2024] | API Connector



https://mixedanalytics.com/knowledge-base/top-free-crypto-apis/



Top Free Public Crypto APIs for Google Sheets \[2024] | API Connector



https://mixedanalytics.com/knowledge-base/top-free-crypto-apis/



Top Free Public Crypto APIs for Google Sheets \[2024] | API Connector



https://mixedanalytics.com/knowledge-base/top-free-crypto-apis/



Most Comprehensive Cryptocurrency Price \& Market Data API



https://www.coingecko.com/en/api

All Sources



bannerbear



coingecko



support.coingecko



mixedanalytics

api.coinpaprika



coinpaprika


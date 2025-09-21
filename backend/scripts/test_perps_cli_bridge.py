import json

from services.perps_bridge.perps_service import dry_run_increase


def main() -> None:
    payload = {
        "rpcUrl": "https://rpc.helius.xyz/?api-key=***REDACTED***",
        "programId": "PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu",
        "owner": "CzRzD26vfaSgNVxM93Hpy2VHtiaLmQrVNCRbSWd1ikR7",
        "fundingAccount": "AASbgu3zccypDbQPSC76BKxpdYEsxVABHiDgD6j7xpvi",
        "perpetuals": "H4ND9aYttUVLFmNypZqLjZ52FYiGvdEB45GmwNoKEjTj",
        "pool": "5BUwFW4nRbftYTDMbgxykoFWqWHPzahFSNAaaaJtVKsq",
        "position": "FVXtPsVrTepKFytmJ31AXaZWHjtNY2APtMm99YuwsGYP",
        "positionRequest": "12RNaHjt6cuSP3H1Mt2Z7JLpcJJDdq3voLGDdGRQmhWU",
        "positionRequestAta": "2j3FyHpDGeRv8JeshrJcJyPD7157Kbc4aHiaUTd1nHHB",
        "custody": "G18jKKXQwBbrHeiK3C9MRXhkHsLHf7XgCSisykV46EZa",
        "collateralCustody": "7xS2gz2bTp3fwCC7knJvUWTEU9Tycczu6VhJYKgi1wdz",
        "inputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "referral": "CzRzD26vfaSgNVxM93Hpy2VHtiaLmQrVNCRbSWd1ikR7",
        "params": {
            "sizeUsdDelta": 11_000_000,
            "collateralTokenDelta": 11_000_000,
            "side": "long",
            "priceSlippage": 0,
            "jupiterMinimumOut": None,
            "counter": 1,
        },
    }

    res = dry_run_increase(payload)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()

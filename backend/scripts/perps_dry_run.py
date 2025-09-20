from backend.services.perps.positions_request import load_signer, dry_run_open_position_request


if __name__ == "__main__":
    w = load_signer()
    rep = dry_run_open_position_request(
        wallet=w,
        market="SOL-PERP",
        side="long",
        size_usd=11,
        collateral_usd=11,
    )
    # Minimal console dump
    print("OK?", rep["ok"])
    print("Instruction:", rep["instruction"])
    print("Position:", rep["position"])
    print("Request:", rep["positionRequest"])
    print("Request ATA:", rep["positionRequestAta"])
    print("Final mapping:", rep["finalMapping"])
    for step in rep["steps"]:
        print("\n== STEP:", step["label"], "OK?", step["ok"])
        print("Error:", step["errorCode"], "-", step["errorMessage"])
        print("RightPdaHint:", step["rightPdaHint"], "Unknown:", step["unknownAccount"])
        print("\n".join(step["logs"][:10]))

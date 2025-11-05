Set-Location C:\sonic7
if (Test-Path .\.venv\Scripts\Activate.ps1) { .\.venv\Scripts\Activate.ps1 }
$env:PYTHONPATH = "C:\sonic7;$env:PYTHONPATH"
if (-not $env:SOL_RPC) { $env:SOL_RPC = "https://mainnet.helius-rpc.com/?api-key=a8809bee-20ba-48e9-b841-0bd2bafd60b9" }
python -m backend.core.gmx_solana_core.console.menu_console

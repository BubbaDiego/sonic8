# Ensure paths exist
$ErrorActionPreference = "Stop"
$target1 = "backend\core\monitor_core\liquidation_monitor.py"
$target2 = "backend\core\monitor_core\liquid_monitor.py"
ni -ItemType Directory -Force (Split-Path $target1) | Out-Null

# Write files
@'
<PASTE liquidation_monitor.py CONTENT FROM ABOVE>
'@ | Set-Content -Encoding UTF8 $target1

@'
<PASTE shim liquid_monitor.py CONTENT FROM ABOVE>
'@ | Set-Content -Encoding UTF8 $target2

# Clean pyc
gci -Recurse -Directory -Filter __pycache__ .\backend | ri -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "✅ Dropped liquidation_monitor + shim. Ready to run." -ForegroundColor Green

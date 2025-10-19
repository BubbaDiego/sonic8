<# =======================================================================
 Full Sonic – Uno (single window, split panes)
 -------------------------------------------------------------------------
 - Keeps existing launch commands intact (no renames/ports/env changes).
 - Uses Windows Terminal (wt.exe) to tile panes:
     Top          : Sonic Monitor (≈65% height)
     Bottom-left  : Backend (FastAPI)
     Bottom-right : Frontend (Vite)
 - If wt.exe is missing, falls back to legacy #1 flow (three windows).
 - All panes use PowerShell and stay open (-NoExit) to show logs/errors.
 ======================================================================= #>

param(
  [string]$RepoRoot = (Resolve-Path "$PSScriptRoot\..").Path,
  [string]$ApiHost  = "127.0.0.1",
  [int]   $ApiPort  = 5000
)

# ---------- helpers (do NOT change existing commands/ports/env) ----------
function Get-Python {
  # Prefer repo venv python; fall back to py -3; then python
  $venvPy = Join-Path $RepoRoot ".venv\Scripts\python.exe"
  if (Test-Path $venvPy) { return "`"$venvPy`"" }  # already quoted
  $py = (Get-Command py -ErrorAction SilentlyContinue)
  if ($py) { return "py -3" }
  return (Get-Command python -ErrorAction Stop).Source
}

function Get-FrontendRunner {
  # Use existing tool the same way you do today; safest order
  if (Get-Command pnpm -ErrorAction SilentlyContinue) { return "pnpm dev" }
  if (Get-Command yarn -ErrorAction SilentlyContinue) { return "yarn dev" }
  return "npm run dev"
}

# ---------- detect Windows Terminal ----------
$wt = Get-Command wt.exe -ErrorAction SilentlyContinue
$python = Get-Python
$frontendCmd = Get-FrontendRunner
$frontendDir = Join-Path $RepoRoot "frontend"

# Build pane commands (PowerShell in each pane; keep -NoExit)
# NOTE: use escaped quotes so wt.exe parses them correctly.
$monCmd = "powershell -NoExit -Command `"& $python `".\backend\core\monitor_core\sonic_monitor.py`"`""
$apiCmd = "powershell -NoExit -Command `"& $python -m uvicorn backend.sonic_backend_app:app --host $ApiHost --port $ApiPort --reload`"`""
$webCmd = "powershell -NoExit -Command `"$frontendCmd`""

if (-not $wt) {
  Write-Host "Windows Terminal (wt.exe) not found → falling back to legacy #1 (three windows)..." -ForegroundColor Yellow
  # Legacy: start three separate consoles (same behavior as Menu #1)
  Start-Process -WorkingDirectory $RepoRoot    -FilePath "powershell.exe" -ArgumentList "-NoExit","-Command","& $python -m uvicorn backend.sonic_backend_app:app --host $ApiHost --port $ApiPort --reload"
  Start-Process -WorkingDirectory $frontendDir -FilePath "powershell.exe" -ArgumentList "-NoExit","-Command",$frontendCmd
  Start-Process -WorkingDirectory $RepoRoot    -FilePath "powershell.exe" -ArgumentList "-NoExit","-Command","& $python .\backend\core\monitor_core\sonic_monitor.py"
  exit 0
}

# ---------- Windows Terminal layout ----------
# new-tab          → top monitor
# split-pane -V    → add bottom pane (vertical split = below), size ~35%
# split-pane -H    → split the active bottom pane into left/right (backend/ frontend)
& $wt.Source `
  new-tab     --title "Sonic Monitor"      -d "$RepoRoot"   $monCmd `
  ; split-pane -V --size 0.35 --title "Backend • API" -d "$RepoRoot"   $apiCmd `
  ; split-pane -H            --title "Frontend • Vite" -d "$frontendDir" $webCmd

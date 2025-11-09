<# ------------------------------------------------------------------------
webterm_up.ps1
Launch a browser-accessible terminal for Sonic on Windows:
  - Kills old ttyd / cloudflared
  - Picks a free port (or uses the one you give)
  - Starts ttyd with a real shell (pwsh -> powershell -> cmd fallback)
  - Starts Cloudflare quick tunnel and extracts the REAL trycloudflare URL
  - Prints a clickable hyperlink + helpful debug

USAGE EXAMPLES
  .\webterm_up.ps1                          # defaults; auto port, auto shell, cloudflare quick
  .\webterm_up.ps1 -Port 7690               # force a port
  .\webterm_up.ps1 -Shell pwsh              # force PowerShell 7 shell
  .\webterm_up.ps1 -Shell cmd               # force classic CMD
  .\webterm_up.ps1 -NoTunnel                # serve locally only ( http://127.0.0.1:<port> )
  .\webterm_up.ps1 -User geno -Pass secret  # enable Basic Auth on ttyd

NOTES
- Requires: ttyd.exe, cloudflared.exe in PATH.
- If you want to run Sonic automatically in the terminal, set -Sonic $true.
------------------------------------------------------------------------ #>

param(
  [int]$Port = 0,                     # 0 = auto-pick
  [ValidateSet('auto','pwsh','powershell','cmd')]
  [string]$Shell = 'auto',
  [switch]$Sonic,                     # if set: auto-run Sonic in the shell
  [string]$SonicRoot = 'C:\sonic7',
  [string]$SonicPy  = 'C:\sonic7\.venv\Scripts\python.exe',
  [string]$SonicEntrypoint = 'C:\sonic7\launch_pad.py',

  [switch]$NoTunnel,                  # skip Cloudflare; local only
  [string]$Provider = 'cloudflare',   # future: 'tailscale' support
  [string]$User,                      # Basic auth (omit for none)
  [string]$Pass,

  [int]$PortSearchStart = 7681,
  [int]$PortSearchMax   = 12
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# --- paths & logs
$Reports = Join-Path $PSScriptRoot 'reports'
New-Item -ItemType Directory -Path $Reports -Force | Out-Null
$TtydLog = Join-Path $Reports 'ttyd.log'
$CfLog   = Join-Path $Reports 'cloudflared.log'

function Write-Info($msg){ Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn($msg){ Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err ($msg){ Write-Host "[FAIL] $msg" -ForegroundColor Red }

function Test-PortInUse([int]$p){
  try {
    $tcp = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
    return $tcp | Where-Object { $_.Port -eq $p } | ForEach-Object { $true } | Select-Object -First 1
  } catch { $false }
}

function Pick-FreePort([int]$start,[int]$max){
  for($i=0; $i -lt $max; $i++){
    $p = $start + $i
    if(!(Test-PortInUse $p)){ return $p }
  }
  throw "No free port in range $start..$($start+$max-1)"
}

function Resolve-Exe($name){
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if($cmd){ return $cmd.Source }
  throw "Missing dependency: $name not found in PATH"
}

function Shell-CmdLine([string]$pref,[switch]$RunSonic){
  # Build absolute shell path + arguments. Returns @{Exe='...'; Args=@('...','...')}
  $pwsh = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
  $ps5  = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
  $cmd  = "$env:WINDIR\Sysnative\cmd.exe"

  $exe = $null; $args = @()
  if($pref -eq 'pwsh' -or ($pref -eq 'auto' -and $pwsh)){ $exe = $pwsh; $args += @('-NoLogo','-NoExit') }
  elseif($pref -eq 'powershell' -or ($pref -eq 'auto' -and (Test-Path $ps5))){ $exe = $ps5; $args += @('-NoLogo','-NoExit') }
  else{ $exe = $cmd; $args += @('/K') }

  if($RunSonic){
    if($exe -like '*cmd.exe'){
      $cmdStr = "title Sonic WebTerm && cd /d $SonicRoot && `"$SonicPy`" `"$SonicEntrypoint`""
      $args[-1] = "$($args[-1]) $cmdStr"
    } else {
      $psCmd = "Set-Location '$SonicRoot'; & '$SonicPy' '$([IO.Path]::GetFileName($SonicEntrypoint))'"
      if(-not (Test-Path $SonicEntrypoint)) { $psCmd = "Set-Location '$SonicRoot'; & '$SonicPy' '$SonicEntrypoint'" }
      $args += @('-Command', $psCmd)
    }
  }

  return @{ Exe = $exe; Args = $args }
}

function Start-Ttyd([int]$p,[hashtable]$sh,[string]$user,[string]$pass){
  $ttyd = Resolve-Exe 'ttyd.exe'
  $args = @('--writable','--port',"$p")
  if($user -and $pass){ $args += @('-c', "$user`:$pass") }
  $args += @('--', $sh.Exe) + $sh.Args
  Write-Info ("ttyd: {0} {1}" -f $ttyd, ($args -join ' '))
  $pinfo = New-Object System.Diagnostics.ProcessStartInfo
  $pinfo.FileName = $ttyd
  $pinfo.RedirectStandardOutput = $true
  $pinfo.RedirectStandardError  = $true
  $pinfo.UseShellExecute = $false
  $pinfo.CreateNoWindow = $true
  foreach($a in $args){ $null = $pinfo.ArgumentList.Add($a) }

  $proc = New-Object System.Diagnostics.Process
  $proc.StartInfo = $pinfo
  $ok = $proc.Start()
  if($ok){
    # async log tee
    $stdout = [System.IO.StreamReader]$proc.StandardOutput
    $stderr = [System.IO.StreamReader]$proc.StandardError
    Start-Job -ScriptBlock {
      param($o,$e,$log)
      $sw = [IO.StreamWriter]::new($log,$false,[Text.UTF8Encoding]::new($false))
      while(-not ($o.EndOfStream -and $e.EndOfStream)){
        if(-not $o.EndOfStream){ $line=$o.ReadLine(); $sw.WriteLine($line) }
        if(-not $e.EndOfStream){ $line=$e.ReadLine(); $sw.WriteLine($line) }
        Start-Sleep -Milliseconds 50
      }
      $sw.Flush(); $sw.Close()
    } -ArgumentList $stdout,$stderr,$TtydLog | Out-Null
  } else { throw "Failed to start ttyd" }
  return $proc
}

function Wait-Port([int]$p,[int]$ms=10000){
  $deadline = (Get-Date).AddMilliseconds($ms)
  do {
    try {
      $c = New-Object System.Net.Sockets.TcpClient
      $c.Connect('127.0.0.1',$p)
      $c.Close(); return $true
    } catch { Start-Sleep -Milliseconds 200 }
  } while((Get-Date) -lt $deadline)
  return $false
}

function Start-Cloudflare([int]$p){
  $cf = Resolve-Exe 'cloudflared.exe'
  if($NoTunnel){ return @{Proc=$null; Url=$null} }

  # wipe old log
  if(Test-Path $CfLog){ Remove-Item $CfLog -Force -ErrorAction SilentlyContinue }
  $args = @('tunnel','--url',"http://127.0.0.1:$p",'--no-autoupdate','--logfile',"$CfLog")
  Write-Info ("cloudflared: {0} {1}" -f $cf, ($args -join ' '))
  $cfProc = Start-Process -FilePath $cf -ArgumentList $args -NoNewWindow -PassThru

  # wait for URL to appear
  $url = $null
  $rx  = [regex]::new('https?://[a-z0-9\-]+(?:\.[a-z0-9\-]+)*\.trycloudflare\.com','IgnoreCase')
  for($i=0; $i -lt 120 -and -not $url; $i++){
    if(Test-Path $CfLog){
      $text = Get-Content $CfLog -Raw -ErrorAction SilentlyContinue
      $m = $rx.Match($text)
      if($m.Success){ $url = $m.Value; break }
    }
    Start-Sleep -Milliseconds 250
  }
  return @{ Proc = $cfProc; Url = $url }
}

function Write-Link($label,$url){
  # OSC-8 hyperlink (Windows Terminal/VSCode/iTerm)
  $ESC = [char]27
  $open = "$ESC]8;;$url$ESC\"
  $close = "$ESC]8;;$ESC\"
  Write-Host ("{0}{1}{2}" -f $open, $label, $close) -NoNewline
  Write-Host "  ->  $url"
}

# 0) Kill anything stale
foreach($n in 'ttyd','cloudflared'){
  Stop-Process -Name $n -Force -ErrorAction SilentlyContinue
}

# 1) Port
if($Port -le 0){ $Port = Pick-FreePort -start $PortSearchStart -max $PortSearchMax }
elseif(Test-PortInUse $Port){ Write-Warn "Port $Port in use; picking another."; $Port = Pick-FreePort -start ($Port+1) -max $PortSearchMax }

# 2) Shell & command
$sh = Shell-CmdLine -pref $Shell -RunSonic:$Sonic

# 3) Start ttyd
$ttydProc = Start-Ttyd -p $Port -sh $sh -user $User -pass $Pass
if(!(Wait-Port -p $Port -ms 10000)){ Write-Err "ttyd failed to listen on $Port"; exit 2 }

# 4) Start tunnel (if any)
$result = Start-Cloudflare -p $Port
$url    = if($NoTunnel){ "http://127.0.0.1:$Port" } else { $result.Url }

# 5) Print debug
Write-Host ""
Write-Host "────────────────────────────────────────────────────────────────────────" -ForegroundColor Green
Write-Info ("Shell     : {0} {1}" -f $sh.Exe, ($sh.Args -join ' '))
Write-Info ("ttyd PID  : {0}   log: {1}" -f $ttydProc.Id, $TtydLog)
if(-not $NoTunnel){
  $cfpid = if($result.Proc){ $result.Proc.Id } else { '(none)' }
  Write-Info ("cf PID    : {0}   log: {1}" -f $cfpid, $CfLog)
}
Write-Info ("Local URL : http://127.0.0.1:{0}" -f $Port)
if($url){
  Write-Info ("Public URL: {0}" -f $url)
  Write-Host ""
  Write-Link -label "Open Web Terminal" -url $url
} else {
  if($NoTunnel){ Write-Warn "No tunnel requested; use the Local URL above." }
  else { Write-Warn "Tunnel URL not ready yet; tail the log:  Get-Content `"$CfLog`" -Tail 200 -Wait" }
}
Write-Host "────────────────────────────────────────────────────────────────────────" -ForegroundColor Green

# 6) Keep the script alive briefly to show logs if launched from double-click
Write-Host ""
Write-Host "Tip: Ctrl+C to exit this launcher. This does NOT kill ttyd/cloudflared." -ForegroundColor DarkGray

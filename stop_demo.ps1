$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

$running = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "python.exe" -and $_.CommandLine -like "*shop_assist*main.py*"
}

if (-not $running) {
    Write-Step "No running shop_assist backend process found"
    exit 0
}

Write-Step "Stopping shop_assist backend process"
foreach ($proc in $running) {
    Write-Host "Stopping PID $($proc.ProcessId)" -ForegroundColor Yellow
    Stop-Process -Id $proc.ProcessId -Force
}

Write-Host "shop_assist demo stopped." -ForegroundColor Green

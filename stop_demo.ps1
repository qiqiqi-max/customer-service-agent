$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

$running = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "python.exe" -and $_.CommandLine -like "*customer-service-agent*main.py*"
}

if (-not $running) {
    Write-Step "No running customer-service-agent backend process found"
    exit 0
}

Write-Step "Stopping customer-service-agent backend process"
foreach ($proc in $running) {
    Write-Host "Stopping PID $($proc.ProcessId)" -ForegroundColor Yellow
    Stop-Process -Id $proc.ProcessId -Force
}

Write-Host "customer-service-agent demo stopped." -ForegroundColor Green

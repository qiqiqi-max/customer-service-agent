$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendDir = Join-Path $scriptDir "frontend"
$pythonExe = Join-Path $scriptDir ".venv\Scripts\python.exe"
$alembicExe = Join-Path $scriptDir ".venv\Scripts\alembic.exe"
$envFile = Join-Path $scriptDir ".env.local"

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Load-EnvFile {
    param([string]$Path)

    Get-Content -Path $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }

        $parts = $line -split "=", 2
        if ($parts.Count -ne 2) {
            return
        }

        [System.Environment]::SetEnvironmentVariable(
            $parts[0].Trim(),
            $parts[1].Trim(),
            "Process"
        )
    }
}

function Wait-ForService {
    param(
        [string]$HealthUrl,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing $HealthUrl -TimeoutSec 3
            if ($response.StatusCode -eq 200) {
                return
            }
        } catch {
            Start-Sleep -Milliseconds 800
        }
    }

    throw "Backend service did not become healthy within $TimeoutSeconds seconds."
}

Set-Location $scriptDir

if (-not (Test-Path $pythonExe)) {
    throw "Python virtual environment not found: $pythonExe"
}

if (-not (Test-Path $alembicExe)) {
    throw "Alembic executable not found: $alembicExe"
}

if (-not (Test-Path $envFile)) {
    throw "Missing .env.local. Copy .env.local.example to .env.local first."
}

if (-not (Test-Path $frontendDir)) {
    throw "Frontend directory not found: $frontendDir"
}

Write-Step "Loading local environment"
Load-EnvFile -Path $envFile

Write-Step "Applying database migrations"
& $alembicExe upgrade head

Write-Step "Seeding MySQL data"
& $pythonExe -m tools.seed_mysql_data

$port = [System.Environment]::GetEnvironmentVariable("_FAAS_RUNTIME_PORT", "Process")
if (-not $port) {
    $port = "8080"
}

$backendUrl = "http://127.0.0.1:$port"
$workbenchUrl = "http://127.0.0.1:5173"

$backendRunning = $false
try {
    $ping = Invoke-WebRequest -UseBasicParsing "$backendUrl/v1/ping" -TimeoutSec 3
    $backendRunning = $ping.StatusCode -eq 200
} catch {
    $backendRunning = $false
}

if (-not $backendRunning) {
    Write-Step "Starting backend"
    Start-Process -FilePath $pythonExe -ArgumentList "main.py" -WorkingDirectory $scriptDir -WindowStyle Hidden | Out-Null
    Wait-ForService -HealthUrl "$backendUrl/v1/ping"
}

if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Step "Installing frontend dependencies"
    Push-Location $frontendDir
    npm.cmd install
    Pop-Location
}

$frontendRunning = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like "*customer-service-agent*frontend*" -and
    ($_.CommandLine -like "*vite*" -or $_.CommandLine -like "*npm*")
}

if (-not $frontendRunning) {
    Write-Step "Starting frontend workbench"
    Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory $frontendDir -WindowStyle Hidden | Out-Null
    Start-Sleep -Seconds 3
}

Write-Step "Workbench is ready"
Write-Host ""
Write-Host "Frontend URL: $workbenchUrl" -ForegroundColor Green
Write-Host "Backend URL:  $backendUrl" -ForegroundColor Green
Write-Host ""
Start-Process $workbenchUrl | Out-Null

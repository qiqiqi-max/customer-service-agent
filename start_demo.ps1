$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path $scriptDir ".env.local"
$pythonExe = Join-Path $scriptDir ".venv\Scripts\python.exe"
$alembicExe = Join-Path $scriptDir ".venv\Scripts\alembic.exe"

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

        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

function Test-RequiredEnv {
    $mockMode = [System.Environment]::GetEnvironmentVariable("MOCK_MODE", "Process")
    if ($mockMode -and $mockMode.ToLower() -in @("true", "1", "t", "yes")) {
        return
    }

    $knowledgeProvider = [System.Environment]::GetEnvironmentVariable("KNOWLEDGE_PROVIDER", "Process")
    if ($knowledgeProvider -and $knowledgeProvider.ToLower() -eq "dify") {
        $missingKnowledge = @()
        if (-not [System.Environment]::GetEnvironmentVariable("DIFY_API_KEY", "Process")) {
            $missingKnowledge += "DIFY_API_KEY"
        }
        if (-not [System.Environment]::GetEnvironmentVariable("DIFY_DATASET_ID", "Process")) {
            $missingKnowledge += "DIFY_DATASET_ID"
        }
        if ($missingKnowledge.Count -gt 0) {
            throw "Missing required environment variables: $($missingKnowledge -join ', ')"
        }
    }

    $provider = [System.Environment]::GetEnvironmentVariable("LLM_PROVIDER", "Process")
    if ($provider -and $provider.ToLower() -in @("deepseek", "openai_compatible")) {
        if (-not [System.Environment]::GetEnvironmentVariable("DEEPSEEK_API_KEY", "Process")) {
            throw "Missing required environment variables: DEEPSEEK_API_KEY"
        }
        return
    }

    if ($provider -and $provider.ToLower() -eq "zhipu") {
        $zhipuKey = [System.Environment]::GetEnvironmentVariable("ZHIPU_API_KEY", "Process")
        $zaiKey = [System.Environment]::GetEnvironmentVariable("ZAI_API_KEY", "Process")
        if (-not $zhipuKey -and -not $zaiKey) {
            throw "Missing required environment variables: ZHIPU_API_KEY"
        }
        return
    }

    $required = @(
        "VOLC_ACCESSKEY",
        "VOLC_SECRETKEY",
        "COLLECTION_NAME",
        "FAQ_COLLECTION_NAME",
        "LLM_ENDPOINT_ID",
        "BUCKET_NAME",
        "USE_SERVER_AUTH",
        "ARK_API_KEY",
        "LANGUAGE"
    )

    $missing = @()
    foreach ($name in $required) {
        if (-not [System.Environment]::GetEnvironmentVariable($name, "Process")) {
            $missing += $name
        }
    }

    if ($missing.Count -gt 0) {
        throw "Missing required environment variables: $($missing -join ', ')"
    }
}

function Wait-ForService {
    param(
        [string]$HealthUrl,
        [int]$TimeoutSeconds = 25
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

    throw "Service did not become healthy within $TimeoutSeconds seconds."
}

Set-Location $scriptDir

if (-not (Test-Path $pythonExe)) {
    throw "Python virtual environment not found: $pythonExe"
}

if (-not (Test-Path $alembicExe)) {
    throw "Alembic executable not found: $alembicExe"
}

if (-not (Test-Path $envFile)) {
    throw "Missing .env.local. Copy .env.local.example to .env.local and fill in your real values first."
}

Write-Step "Loading local environment variables from .env.local"
Load-EnvFile -Path $envFile

Write-Step "Applying database migrations"
& $alembicExe upgrade head
Test-RequiredEnv
$port = [System.Environment]::GetEnvironmentVariable("_FAAS_RUNTIME_PORT", "Process")
if (-not $port) {
    $port = "8080"
}
$url = "http://127.0.0.1:$port/demo"

$running = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "python.exe" -and $_.CommandLine -like "*customer-service-agent*main.py*"
}

if ($running) {
    Write-Step "Detected an existing customer-service-agent service. Stopping old process first"
    foreach ($proc in $running) {
        Stop-Process -Id $proc.ProcessId -Force
    }
    Start-Sleep -Seconds 1
}

Write-Step "Starting backend service"
$process = Start-Process -FilePath $pythonExe -ArgumentList "main.py" -WorkingDirectory $scriptDir -WindowStyle Hidden -PassThru

try {
    Write-Step "Waiting for health check"
    Wait-ForService -HealthUrl "http://127.0.0.1:$port/v1/ping"
    Write-Step "Service is ready"
    Write-Host ""
    Write-Host "Demo URL: $url" -ForegroundColor Green
    Write-Host "Process ID: $($process.Id)" -ForegroundColor Green
    Write-Host ""
    Write-Host "If the page opens but chat fails, re-check the values in .env.local." -ForegroundColor Yellow
    Start-Process $url | Out-Null
} catch {
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
    }
    throw
}

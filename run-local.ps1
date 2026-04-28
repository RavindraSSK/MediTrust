[CmdletBinding()]
param(
    [switch]$SkipDocker,
    [switch]$Reload,
    [string]$ListenHost = "127.0.0.1",
    [int]$Port = 8001
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$envFile = Join-Path $projectRoot "backend\.env"

if (-not (Test-Path $pythonExe)) {
    throw "Project virtual environment was not found at .venv\Scripts\python.exe"
}

if (-not (Test-Path $envFile)) {
    throw "Missing backend\.env. Create it before starting the backend."
}

Push-Location $projectRoot
try {
    Write-Host "Project root: $projectRoot"

    if (-not $SkipDocker) {
        if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
            throw "Docker is not installed or not available in this PowerShell session."
        }

        Write-Host "Starting PostgreSQL container with docker compose..."
        & docker compose up -d

        if ($LASTEXITCODE -ne 0) {
            throw "docker compose up -d failed."
        }
    }

    Write-Host ""
    Write-Host "Backend URL:  http://$ListenHost`:$Port"
    Write-Host "API docs:     http://$ListenHost`:$Port/docs"
    Write-Host "Frontend:     Serve the frontend folder with VS Code Live Server on port 5500 or 5501"
    Write-Host "Backend mode: $(if ($Reload) { 'reload enabled' } else { 'reload disabled' })"
    Write-Host ""
    Write-Host "Press Ctrl+C to stop the backend."
    Write-Host ""

    $uvicornArgs = @(
        "-m", "uvicorn",
        "app.main:app",
        "--app-dir", "backend",
        "--host", $ListenHost,
        "--port", $Port
    )

    if ($Reload) {
        $uvicornArgs += "--reload"
    }

    & $pythonExe @uvicornArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}

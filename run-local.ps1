[CmdletBinding()]
param(
    [switch]$SkipDocker,
    [switch]$Reload,
    [string]$ListenHost = "127.0.0.1",
    [int]$Port = 8001
)

# Starts the MediTrust API for local development on Windows.
# Frontend: in another terminal run `cd frontend; npm install; npm run dev` (http://127.0.0.1:5173).

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$pythonExe = if (Test-Path $venvPython) { $venvPython } else { "python" }
$envFile = Join-Path $projectRoot "backend\.env"

if (-not (Test-Path $envFile)) {
    Write-Host "backend\.env not found; copying backend\.env.example (edit ADMIN_PASSWORD / DATABASE_URL)."
    Copy-Item (Join-Path $projectRoot "backend\.env.example") $envFile
}

Push-Location $projectRoot
try {
    if (-not $SkipDocker) {
        if (Get-Command docker -ErrorAction SilentlyContinue) {
            Write-Host "Starting PostgreSQL container with docker compose..."
            & docker compose up -d db
        } else {
            Write-Host "Docker not found; the API will use the SQLite DATABASE_URL from backend\.env (or its default)."
        }
    }

    Write-Host ""
    Write-Host "Backend URL:  http://$ListenHost`:$Port"
    Write-Host "API docs:     http://$ListenHost`:$Port/docs"
    Write-Host "Model card:   http://$ListenHost`:$Port/model/info"
    Write-Host "Frontend:     cd frontend; npm run dev   (http://127.0.0.1:5173)"
    Write-Host ""

    $uvicornArgs = @("-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", $ListenHost, "--port", $Port)
    if ($Reload) { $uvicornArgs += "--reload" }

    & $pythonExe @uvicornArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}

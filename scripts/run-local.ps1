$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Set-Location $ProjectDir

# Setup virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
}

& "venv\Scripts\Activate.ps1"
pip install -r requirements.txt

# Setup .env if needed
if (-not (Test-Path ".env")) {
    Write-Host "No .env file found. Please create one based on the template in the repo."
}

Write-Host ""
Write-Host "Starting Stats Microservice on port 3038..."
Write-Host ""

uvicorn src.api:app --host 0.0.0.0 --port 3038 --reload

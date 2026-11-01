param(
    [ValidateRange(1, 65535)][int]$Port = 8000,
    [switch]$SeedDemo
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed: $Executable (exit $LASTEXITCODE)" }
}

if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    Invoke-Checked 'python' @('-m', 'venv', '.venv')
}
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
Invoke-Checked $taskPython @('-m', 'pip', 'install', '-r', 'backend\requirements.lock.txt')

if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
$taskEnvironment = [IO.File]::ReadAllText((Join-Path $PSScriptRoot '.env'))
if ($taskEnvironment -match '(?m)^JWT_SECRET=[ \t]*\r?$') {
    $taskRandom = New-Object byte[] 48
    $taskGenerator = [Security.Cryptography.RandomNumberGenerator]::Create()
    $taskGenerator.GetBytes($taskRandom)
    $taskGenerator.Dispose()
    $taskSecret = [Convert]::ToBase64String($taskRandom)
    $taskEnvironment = [regex]::Replace($taskEnvironment, '(?m)^JWT_SECRET=[ \t]*\r?$', "JWT_SECRET=$taskSecret")
    [IO.File]::WriteAllText((Join-Path $PSScriptRoot '.env'), $taskEnvironment)
}

Push-Location -LiteralPath 'frontend'
try {
    Invoke-Checked 'npm.cmd' @('ci')
    Invoke-Checked 'npm.cmd' @('run', 'build')
} finally { Pop-Location }

# This launcher is for local HTTP development. Hosted containers enforce production settings.
$env:ENVIRONMENT = 'development'
$env:SERVE_FRONTEND = 'true'
$env:PORT = [string]$Port
$env:CORS_ORIGINS = "http://localhost:$Port,http://127.0.0.1:$Port"
$env:SEED_DEMO = if ($SeedDemo) { 'true' } else { 'false' }
Write-Host "TraceBack AI will serve at http://127.0.0.1:$Port after initialization. Press Ctrl+C to stop."
Invoke-Checked $taskPython @('-m', 'backend.boot')

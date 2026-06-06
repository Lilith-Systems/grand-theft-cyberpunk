param([switch]$Force)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $root ".venv-ngd"
$python = Join-Path $venv "Scripts\python.exe"

$launcher = Get-Command py -ErrorAction SilentlyContinue
if (-not $launcher) { $launcher = Get-Command python -ErrorAction SilentlyContinue }
if (-not $launcher) { throw "Python 3.10 or newer was not found. Install Python from python.org, then run this script again." }

if ($Force -and (Test-Path $venv)) { Remove-Item -LiteralPath $venv -Recurse -Force }
if (-not (Test-Path $python)) {
    if ($launcher.Name -eq "py.exe") { & $launcher.Source -3 -m venv $venv }
    else { & $launcher.Source -m venv $venv }
}

& $python -m pip install --upgrade pip
& $python -m pip install $root
& (Join-Path $PSScriptRoot "verify-windows.ps1")

Write-Host ""
Write-Host "Installed. Start with: .\scripts\start-ngd.ps1"

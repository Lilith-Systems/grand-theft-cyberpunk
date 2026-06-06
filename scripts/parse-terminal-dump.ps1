param(
  [Parameter(Mandatory=$true)]
  [string]$Path
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv-ngd\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Local environment not found. Run .\scripts\install-windows.ps1 first." }
Get-Content $Path -Raw | & $python -m ngd.term_events

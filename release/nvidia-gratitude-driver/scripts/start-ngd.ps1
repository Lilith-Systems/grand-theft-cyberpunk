param(
  [string]$Runtime = ".\runtime\nvidia_gratitude_driver",
  [double]$Interval = 1.0
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv-ngd\Scripts\python.exe"
$runtimePath = [System.IO.Path]::GetFullPath((Join-Path $root $Runtime))

if (-not (Test-Path $python)) {
  throw "Local environment not found. Run .\scripts\install-windows.ps1 first."
}

& $python -m ngd.driver --runtime $runtimePath --interval $Interval

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv-ngd\Scripts\python.exe"

if (-not (Test-Path $python)) { throw "Local environment not found. Run .\scripts\install-windows.ps1 first." }

& $python -c "import ngd; print('ngd import: OK')"
if ($LASTEXITCODE -ne 0) { throw "Package import failed." }
& $python -m ngd.diagnostics --runtime (Join-Path $root "runtime\nvidia_gratitude_driver")
if ($LASTEXITCODE -ne 0) { throw "Diagnostics failed." }

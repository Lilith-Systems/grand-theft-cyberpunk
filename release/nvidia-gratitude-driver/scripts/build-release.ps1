param([string]$Output = "nvidia-gratitude-driver")

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$releaseRoot = [System.IO.Path]::GetFullPath((Join-Path $root "release"))
$outputPath = [System.IO.Path]::GetFullPath((Join-Path $releaseRoot $Output))
if (-not $outputPath.StartsWith($releaseRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Output must remain inside $releaseRoot"
}
if (Test-Path $outputPath) { Remove-Item -LiteralPath $outputPath -Recurse -Force }
New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
Copy-Item "$root\src","$root\tests","$root\scripts","$root\README.md","$root\HERMES_INTEGRATION.md","$root\SECURITY.md","$root\LICENSE","$root\pyproject.toml","$root\requirements.txt" -Destination $outputPath -Recurse
Get-ChildItem $outputPath -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
Get-ChildItem $outputPath -Recurse -Directory -Filter *.egg-info | Remove-Item -Recurse -Force
Get-ChildItem $outputPath -Recurse -File -Include *.pyc | Remove-Item -Force
Compress-Archive -Path "$outputPath\*" -DestinationPath "$outputPath.zip" -Force
$hash = Get-FileHash "$outputPath.zip" -Algorithm SHA256
$hash.Hash + "  " + (Split-Path -Leaf "$outputPath.zip") | Set-Content "$outputPath.zip.sha256" -Encoding ascii
$hash | Format-List

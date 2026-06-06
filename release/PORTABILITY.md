# Windows Release Portability

The release ZIP is relocatable. Extract it to any writable directory; no `D:\pub` checkout,
administrator access, PATH changes, or globally installed Python packages are required.

## Install and verify

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install-windows.ps1
.\scripts\verify-windows.ps1
.\scripts\start-ngd.ps1
```

Python 3.10 or newer must be available through the Windows `py` launcher or `python` command.
Installation downloads declared Python dependencies from the configured pip index.

## Release integrity

Each ZIP is accompanied by a `.sha256` file. Verify it before sharing:

```powershell
Get-FileHash .\nvidia-gratitude-driver.zip -Algorithm SHA256
Get-Content .\nvidia-gratitude-driver.zip.sha256
```

The values must match. Antivirus tools can inspect PowerShell scripts and Python packages;
do not bypass warnings unless the artifact hash and source are trusted.

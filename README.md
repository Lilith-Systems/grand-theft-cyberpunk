# NVIDIA Gratitude Driver

A safe user-mode companion for gaming/performance optimization and edge-cloud LLM routing.

This is not a kernel driver. It does not replace NVIDIA drivers, inject into games, bypass anti-cheat, bypass API limits,
or automate quota abuse. It reads local telemetry, parses terminal mouse/focus telemetry when explicitly fed a log/stdin,
and emits conservative routing recommendations.

## What it does

- Reads NVIDIA GPU telemetry through NVML (`nvidia-ml-py`) when available.
- Falls back to `nvidia-smi` on Windows/Linux when NVML Python bindings are absent.
- Tracks smoothed VRAM/GPU telemetry with EWMA and hysteresis to prevent load/unload flapping.
- Parses leaked terminal mouse/focus events such as:
  - `[555;93;23M`
  - `\x1b[<35;93;23M`
  - `\x1b[I` / `\x1b[O`
- Writes:
  - `runtime/nvidia_gratitude_driver/status.json`
  - `runtime/nvidia_gratitude_driver/telemetry.jsonl`
- Provides a quota-respecting Nemotron prompt governor:
  - cache hashes
  - compression hints
  - backoff recommendations
  - no rate-limit bypassing
- Reports aggregate Chrome coexistence telemetry without reading browser content.
- Rotates telemetry logs at a configurable size.
- Provides a diagnostic command and deterministic release builder.

## Friend-ready Windows install

Prerequisites: Windows 10/11, PowerShell 5.1 or newer, and Python 3.10 or newer.
Extract the release ZIP anywhere you can write files, open PowerShell in that folder, and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install-windows.ps1
.\scripts\start-ngd.ps1
```

The installer creates a private `.venv-ngd` beside the extracted files, installs the package
without modifying global Python packages, and runs diagnostics. No fixed drive or checkout path
is required. Re-run with `-Force` to rebuild the private environment.

## Run and verify

```powershell
.\scripts\start-ngd.ps1
.\scripts\verify-windows.ps1
```

## Validate and package

```powershell
.\scripts\build-release.ps1
```

The builder writes `release\nvidia-gratitude-driver.zip` and a matching `.sha256` file.
The ZIP includes the Windows install, verification, launch, and terminal parsing scripts.

## Parse leaked terminal event logs

```powershell
Get-Content .\mouse_dump.txt | python -m ngd.term_events
```

## Suggested Hermes integration

Use this as a Local Cerebellum telemetry tool:

```text
Read runtime/nvidia_gratitude_driver/status.json before local model load.
If route == CLOUD_CORTEX, do not reload local model until cooldown_until.
If route == LOCAL_CEREBELLUM, local inference is allowed.
If route == HYBRID, run local intent parsing only; send heavy planning to cloud.
```

## Safety model

- No kernel hooks.
- No DLL injection.
- No game memory reads.
- No screen capture.
- No network exfiltration.
- No browser content, URL, cookie, credential, or history reads.
- No API abuse.
- No provider-limit bypassing.

The intended "gratitude" to NVIDIA is efficiency: fewer wasted tokens, fewer pointless retries,
less GPU thrash, and cleaner performance telemetry.

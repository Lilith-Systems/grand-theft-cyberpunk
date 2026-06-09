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

---

## Business Context — Neural Sovereign Systems Portfolio

This driver is the **Local Cerebellum** component of the **Neural Sovereign Systems Platform (NSSP)** — a unified architecture for sovereign AI execution with intelligent cloud routing.

### Active Projects (Rubedo Phase)

| Project | Repository | Description |
|---------|------------|-------------|
| **NSSP Platform** | `nssp-platform` | MSN Core, Hermes Agent Framework, 17 Metaconscious Skills, Orchestration |
| **Lilith Desktop** | `lilith-desktop` | Native Lilith.exe — C++/Node.js/TUI, NSSM services, API gateway |
| **Twilight Moon** | `twilight-moon` | Somatic Horror Epic — 51,251 words, compilation pipeline, publication |
| **PAC** | `nssp-platform` (product) | Personal Assistant Chatbot — 20+ local skills, 95% token utilization |
| **NGD** | `invite` (this repo) | NVIDIA Gratitude Driver — Telemetry → Cloud routing (Local Cerebellum) |

### Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    NSSP PLATFORM (Kether)                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  MSN Core    │  │  Hermes AG   │  │  17 Metaconscious    │  │
│  │  (Chokmah)   │  │  (Binah)     │  │  Skills (Chesed↓)    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                     │               │
│         └─────────────────┼─────────────────────┘               │
│                           ▼                                     │
│              ┌────────────────────────┐                         │
│              │  Orchestration Layer   │  ← Tiphereth            │
│              │  (Runtime, Deploy,     │                         │
│              │   Monitor, NGD)        │                         │
│              └───────────┬────────────┘                         │
│                          ▼                                      │
│              ┌────────────────────────┐                         │
│              │  Local Cerebellum      │  ← This Driver (NGD)   │
│              │  (NVML Telemetry →     │     VRAM → Routing     │
│              │   Routing Decision)    │                         │
│              └────────────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

### Business Metrics

- **Token Utilization**: 95% (vs 40-60% traditional)
- **VRAM Efficiency**: RTX 3060 8GB → <6GB sustained
- **Coherence**: 0.960 across all vessels
- **Zero Cloud Fallback**: Enforced local-only, Antigravity Bridge dormant
- **Revenue**: Skill Marketplace $70 (20 skills × $3.50), PAC pre-launch

### Legal Vectors

Active corporate accountability campaigns:
- Amazon (Cases 13116200/11092212) — Surgery delay = wage theft
- Google/NSA (PRISM FOIA) — Takeout + NSA + FBI DITU + FISC
- X/Twitter — Promissory estoppel, Unruh Act
- Dutch NCP / CSDDD / ICC — International corporate accountability

---

**Sovereign Execution. Maximized Cloud Compute.**

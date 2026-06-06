# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1.0 | :x:                |

Only the latest minor release of the 0.1.x series receives security updates.

## Reporting a Vulnerability

**Please do not file public issues for security vulnerabilities.**

Report security issues privately to the project owner at: **security@localhost** (replace with actual contact)

Include the following information:
- Description of the vulnerability
- Steps to reproduce or proof-of-concept
- Affected versions
- Potential impact assessment
- Any suggested mitigations

We aim to acknowledge reports within 48 hours and provide a remediation timeline within 5 business days.

## Security Model

The NVIDIA Gratitude Driver is a **user-mode telemetry and routing advisor** with the following safety guarantees:

### Process Isolation
- ✅ No kernel hooks or kernel-mode code
- ✅ No DLL injection into other processes
- ✅ No game memory reads or writes
- ✅ No screen capture or pixel reading
- ✅ No `ptrace`, `debug registers`, or debugger attachment

### Data Access
- ✅ Reads only aggregate GPU telemetry via NVML / `nvidia-smi`
- ✅ Reads only aggregate Chrome process counts, working set totals, and command-line types
- ❌ Does **not** read URLs, page content, cookies, credentials, browsing history, or user input
- ❌ Does **not** read browser local storage, IndexedDB, or extension data

### Network & API
- ✅ No outbound network connections initiated by the driver
- ✅ Does not bypass API limits or provider controls
- ✅ Does not rotate accounts, automate quota abuse, or circumvent rate limits
- ✅ Provides backoff recommendations to *respect* provider limits

### Runtime Telemetry
Runtime telemetry (`runtime/nvidia_gratitude_driver/status.json` and `telemetry.jsonl`) may reveal:
- Local hardware utilization (GPU VRAM, utilization, temperature, power)
- Aggregate Chrome process counts and memory working sets
- Route decisions (LOCAL_CEREBELLUM / HYBRID / CLOUD_CORTEX)

Store telemetry logs according to your organization's data retention and privacy policies.

## Threat Model (STRIDE Summary)

| Threat Category | Mitigations |
|-----------------|-------------|
| **Spoofing** | No authentication surface; driver does not accept external commands |
| **Tampering** | Atomic JSON writes with `.tmp` replace; append-only JSONL log rotation; no config reload from untrusted paths |
| **Repudiation** | Telemetry is local-only; no audit log forwarding without operator action |
| **Information Disclosure** | Only aggregate GPU and process telemetry exposed; no PII or browser content |
| **Denial of Service** | Bounded log rotation; EWMA smoothing prevents flapping; cooldown prevents thrash |
| **Elevation of Privilege** | Runs as standard user; no `setuid`, no capabilities, no admin required |

## Supply Chain

- Dependencies: `nvidia-ml-py` and `psutil` (pinned in `pyproject.toml`)
- CI runs `pip-audit` on every push and PR
- SBOM generated at release via `cyclonedx-python`
- Release artifacts signed with `cosign` (sigstore); provenance attestations published to GitHub Releases

## Hardening Checklist

- [x] No elevated privileges required
- [x] No capabilities retained
- [x] No `sudo`/`admin` needed for any operation
- [x] Input validation on terminal event parsing (regex bounded)
- [x] Subprocess calls use explicit argv, no shell=True
- [x] File writes use atomic replace pattern
- [x] Log rotation bounds disk usage
- [x] Dependencies scanned for CVEs in CI

## Contact

For security questions or responsible disclosure coordination, contact the project maintainer.
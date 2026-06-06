# Hermes Integration Notes

## Tool identity

Name: `nvidia_gratitude_driver`
Role: Local Cerebellum telemetry + route advisor.

## Inputs

- Local GPU state from NVML / nvidia-smi.
- Optional terminal mouse/focus dump fed explicitly by stdin or file.
- Optional prompt text for quota-respecting prompt decision.

## Outputs

- `status.json`: latest route decision.
- `telemetry.jsonl`: append-only telemetry log.
- `prompt_hash_cache.json`: repeated-prompt detection.

## Hermes rule

Before loading a local model or launching a heavy local inference task:

1. Read `runtime/nvidia_gratitude_driver/status.json`.
2. If `route == "CLOUD_CORTEX"` and `cooldown_active == true`, do not reload local weights.
3. If `route == "HYBRID"`, use local model only for intent parsing / validation.
4. If `route == "LOCAL_CEREBELLUM"`, local inference is allowed.
5. Never treat this as permission to bypass provider limits.
6. Never give red-team/godmode skills write access to this config.

## Suggested runtime guard

```powershell
$status = Get-Content .\runtime\nvidia_gratitude_driver\status.json | ConvertFrom-Json
if ($status.route -eq "CLOUD_CORTEX" -and $status.cooldown_active) {
  Write-Host "Cloud route required: $($status.reason)"
  exit 42
}
```

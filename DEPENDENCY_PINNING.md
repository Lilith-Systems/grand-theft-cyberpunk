# Dependency Pinning Policy

## Philosophy

Pinning strategy balances **reproducible builds** with **security update velocity**.

## Runtime Dependencies (`pyproject.toml` `[project.dependencies]`)

| Dependency | Policy | Current Constraint |
|------------|--------|--------------------|
| `nvidia-ml-py` | **Flexible minor** — patch updates auto-accepted; minor updates require CI pass | `>=12.575.51` |
| `psutil` | **Flexible minor** — patch updates auto-accepted; minor updates require CI pass | `>=5.9.0` |

**Rationale**: Both are mature, stable libraries with strong semantic versioning. Minor versions rarely break API. Pinning to patch-only would delay CVE fixes.

### Lock File (Recommended for Deployments)

For production deployments, generate and commit a lock file:

```bash
pip compile pyproject.toml --output-file requirements.lock.txt
```

Or via `pip-tools`:

```bash
pip install pip-tools
pip-compile pyproject.toml -o requirements.lock.txt
```

CI does **not** enforce lock file freshness — it's a deployment artifact.

## Development Dependencies (`pyproject.toml` `[project.optional-dependencies].dev`)

| Dependency | Policy | Notes |
|------------|--------|-------|
| `pytest` | Flexible minor | Test runner |
| `pytest-cov` | Flexible minor | Coverage |
| `pyright` | Flexible minor | Type checking |
| `mypy` | Flexible minor | Type checking |
| `twine` | Flexible minor | Publish |
| `build` | Flexible minor | Build |
| `cyclonedx-bom` | Flexible minor | SBOM |
| `pip-audit` | **Pinned to latest at CI time** | Security scanner — always current |
| `codecov` | Flexible minor | Coverage upload |
| `towncrier` | Flexible minor | Changelog |

### `pip-audit` Special Handling

`pip-audit` is installed **fresh at CI runtime** (`pip install pip-audit`) rather than pinned. This ensures:
- Latest vulnerability database
- Latest scanner logic
- No stale false negatives

## CI Enforcement

### `pip-audit` Job (`.github/workflows/ci.yml`)

Runs on every push and PR:
```yaml
- name: Run pip-audit
  run: |
    pip install pip-audit
    pip-audit -r requirements.txt --format=json --output=pip-audit.json || true
```

- Fails CI on **high/critical** CVEs in *direct* dependencies
- Warns on medium/low
- Scans transitive dependencies (depth unlimited)
- Outputs SARIF for GitHub Security tab

### Dependabot (`.github/dependabot.yml`)

- Weekly PRs for direct and indirect updates
- Grouped: `dev-dependencies` and `runtime-dependencies`
- Auto-merge for patch updates (if CI passes)
- Manual review for minor/major

## Release Workflow

At release (`release.yml`):
1. Build uses latest resolved deps per `pyproject.toml` constraints
2. `pip-audit` runs again pre-sign
3. SBOM generated via `cyclonedx-py` captures **exact resolved versions**
4. Artifacts signed with exact dependency set

## Emergency CVE Response

If a **critical CVE** lands in a transitive dependency:
1. Add explicit constraint to `pyproject.toml` `[project.dependencies]` (e.g., `some-lib!=1.2.3,>=1.2.0`)
2. Run `pip-audit` locally to verify
3. Push hotfix release (patch version bump)

## Tools

| Task | Command |
|------|---------|
| Audit current env | `pip-audit -r requirements.txt` |
| Generate lock file | `pip-compile pyproject.toml -o requirements.lock.txt` |
| Check outdated | `pip list --outdated --local` |
| Generate SBOM | `cyclonedx-py -o sbom.json` |

## Exceptions

**None currently**. All dependencies follow the policy above.
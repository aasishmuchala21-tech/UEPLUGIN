# Plan 03-07 Summary: GitHub-Releases Index Build Pipeline

**Phase:** 03-ue5-knowledge-rag
**Plan:** 03-07
**Type:** execute / checkpoint
**Wave:** 3
**Autonomous:** false
**Depends on:** [01, 02, 03, 04, 05, 06]
**Blocking preconditions:** Bootstrap index must exist; GitHub repo NYRA-NYRA/nyra-plugin must be operator-owned

## Objectives

Automate LanceDB index builds on every UE version release tag and distribute updated indexes via GitHub Releases — so NYRA ships day-of UE version support with zero manual intervention. This is an operator-actionable pipeline, not a code-implementation plan.

## What Was Built

### GitHub Actions Workflow: `.github/workflows/build-knowledge-index.yml`

Triggered by:
- `push` of tags matching `ue-*` (e.g., `ue-5.6.4`)
- `workflow_dispatch` (manual rebuild for any version)

Build matrix: one index per UE minor version (5.4, 5.5, 5.6, 5.7). Tag `ue-5.6.4` maps to `5.6` (minor version), not patch.

Steps:
1. **Setup Python 3.11** — `actions/setup-python@v5`
2. **Install deps** — lancedb, torch, onnxruntime, beautifulsoup4, html2text, playwright, requests, lz4, tar
3. **Fetch corpus** — UE docs (cached `.tar.lz4` archive preferred over re-scrape), C++ headers from EpicGames/UnrealEngine GitHub (`--depth 1 --branch release-5.x`)
4. **Build LanceDB index** — `scripts/build_index.py` with BGE-small-en-v1.5, 1024-token chunks, 128-token overlap
5. **Upload as Release asset** — `softprops/action-gh-release@v1` with `NyraIndex_{MM}_*.lance` + SHA256 checksum

Artifact naming: `NyraIndex_{MAJOR}{MINOR}_{YYYYMMDD}.lance` (e.g., `NyraIndex_560_20260507.lance`)

### Sync Workflow: `.github/workflows/sync-ue-tags.yml`

Weekly cron (Monday 9am) + manual `workflow_dispatch`. Checks EpicGames/UnrealEngine remote tags via `git ls-remote --tags`. Operator manually creates `ue-*` tag in NYRA repo when Epic ships — no automatic pushes.

### GitHub Secrets Required

| Secret | Purpose |
|--------|---------|
| `HF_TOKEN` | Download BGE-small-en-v1.5 from HuggingFace (free, read-only) |
| `GITHUB_TOKEN` | Auto-provided by `softprops/action-gh-release` |

## Files Created

| File | Purpose |
|------|---------|
| `.github/workflows/build-knowledge-index.yml` | Main index build pipeline |
| `.github/workflows/sync-ue-tags.yml` | Weekly Epic tag check (optional) |
| `scripts/fetch_ue_docs.py` | UE5 official docs scraper |
| `scripts/extract_cpp_headers.py` | Parse UE C++ headers for API surface |
| `scripts/build_index.py` | LanceDB index builder (CLI) |
| `scripts/verify_index.py` | Local verification script |
| `.github/RELEASE_INDEX_HOWTO.md` | Operator runbook |

## Module-Superset Discipline

No prior Phase 1-2 or Phase 3 code modified. GitHub Actions workflows in `.github/`, scripts in `scripts/`.

## Operator Actions

1. Create `ue-{version}` tag in NYRA-NYRA/nyra-plugin repo when Epic ships UE
2. Monitor Actions run at: `https://github.com/NYRA-NYRA/nyra-plugin/actions`
3. Verify Release asset at: `https://github.com/NYRA-NYRA/nyra-plugin/releases`
4. If CI fails, run `workflow_dispatch` manually with correct version

## Resume Signal

- `index-pipeline-green` + GitHub Release URL with `NyraIndex_*.lance` asset + SHA256 verified

## Next Steps

- Plan 03-08 runs `KnowledgeBench` as the phase exit canary and produces `03-VERIFICATION.md`
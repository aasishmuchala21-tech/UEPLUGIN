---
phase: 3
slug: ue5-knowledge-rag
plan: 03-07
type: execute / checkpoint
wave: 3
autonomous: false
depends_on: [01, 02, 03, 04, 05, 06]
blocking_preconditions: Bootstrap index (.lance file) must exist before CI pipeline is meaningful; GitHub repo NYRA-NYRA/nyra-plugin must be owned by the operator
---

# Plan 03-07: GitHub-Releases Index Build Pipeline + Epic Tag Trigger

## Current Status

CHECKPOINT — pipeline infrastructure is straightforward; empirical corpus capture requires external web access and operator time.

## Objectives

Automate LanceDB index builds on every UE version release tag and distribute updated indexes via GitHub Releases — so NYRA ships day-of UE version support with zero manual intervention.

## GitHub Actions Pipeline Design

### Trigger Strategy

```yaml
name: Build UE Knowledge Index

on:
  # Trigger on Epic UE release tags (format: ue-5.4.4, ue-5.5.3, etc.)
  push:
    tags:
      - 'ue-*'
  # Also allow manual trigger for any UE version
  workflow_dispatch:
    inputs:
      ue_version:
        description: 'UE version to build index for (e.g., 5.6.4)'
        required: true
        type: string
      skip_bootstrap:
        description: 'Skip bootstrap corpus (use only incremental)'
        required: false
        type: boolean
        default: false
```

### Build Matrix Strategy

Build one index per UE minor version (5.4, 5.5, 5.6, 5.7). The GitHub tag `ue-5.6.4` triggers index build for `5.6` (not just 5.6.4). The `workflow_dispatch` variant lets operator rebuild any version at any time.

### Step-by-Step Build Process

#### Step 1: Environment Setup

```bash
# Python 3.11+ required
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'

- name: Install dependencies
  run: |
    pip install lancedb torch onnxruntime sentencepiece \
                beautifulsoup4 requests \
                html2text playwright githubrelease \
                lz4 tar
```

#### Step 2: Fetch UE Documentation

```bash
# Clone or pull the UE docs mirror
# Strategy: use a pre-built corpus archive if it exists (avoid re-scrape on every CI run)
- name: Fetch UE5 docs corpus
  env:
    CORPUS_VERSION: ${{ github.ref_name }}
  run: |
    # Check if corpus for this version is cached
    if [ -f "corpus-ue-$CORPUS_VERSION.tar.lz4" ]; then
      echo "Using cached corpus for $CORPUS_VERSION"
      lz4 -d corpus-ue-$CORPUS_VERSION.tar.lz4 - | tar -xf -
    else
      echo "Fetching fresh corpus for $CORPUS_VERSION"
      # Fetch from UE docs site (unrealengine.com/docs/ — verify at build time)
      python scripts/fetch_ue_docs.py --version $CORPUS_VERSION --output corpus/
      tar -cf corpus-ue-$CORPUS_VERSION.tar corpus/
      lz4 -9 corpus-ue-$CORPUS_VERSION.tar corpus-ue-$CORPUS_VERSION.tar.lz4
    fi
```

#### Step 3: Fetch Blueprint Node Reference + C++ API Headers

```bash
- name: Fetch C++ headers for UE version
  run: |
    # Clone UE source (public on GitHub: EpicGames/UnrealEngine, tags/release-5.x)
    git clone --depth 1 --branch release-5.6 \
      https://github.com/EpicGames/UnrealEngine.git /tmp/ue-src
    python scripts/extract_cpp_headers.py \
      --ue-source /tmp/ue-src \
      --version 5.6 \
      --output corpus/headers/
```

#### Step 4: Build Embeddings + Write LanceDB Index

```bash
- name: Build LanceDB index
  env:
    UE_VERSION: ${{ github.ref_name }}
    HF_TOKEN: ${{ secrets.HF_TOKEN }}  # For BGE model download (or use cached model)
  run: |
    python scripts/build_index.py \
      --corpus-dir corpus/ \
      --ue-version 5.6 \
      --embedding-model BAAI/bge-small-en-v1.5 \
      --output NyraIndex_560_$(date +%Y%m%d).lance \
      --chunk-size 1024 \
      --overlap 128
```

#### Step 5: Upload as Release Asset

```bash
- name: Upload to GitHub Release
  uses: softprops/action-gh-release@v1
  with:
    tag_name: ${{ github.ref }}
    files: |
      NyraIndex_560_*.lance
      NyraIndex_560_*.lance.sha256
    env:
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Artifact Naming Convention

```
NyraIndex_{MAJOR}{MINOR}_{YYYYMMDD}.lance
NyraIndex_560_20260507.lance    # UE 5.6 index built 2026-05-07
NyraIndex_560_20260507.lance.sha256
```

The `NyraIndex_560_latest.lance` symlink is NOT supported in GitHub Release assets — instead the plugin reads the most-recently-dated file for each version.

## Epic Release Tag Monitoring

### Option A: GitHub Upstream Sync (preferred)

```yaml
# In NYRA-NYRA/nyra-plugin repository
name: Sync UE Release Tags
on:
  schedule:
    - cron: '0 9 * * 1'  # Weekly Monday morning
  # Also: manual
  workflow_dispatch:

jobs:
  check_upstream:
    runs-on: ubuntu-latest
    steps:
      - name: Check EpicGames UE tags
        run: |
          git ls-remote --tags https://github.com/EpicGames/UnrealEngine.git \
            'refs/tags/release-5.*' | awk -F'/' '{print $3}' | sort -V | tail -5
```

The operator manually creates the `ue-{version}` tag in the NYRA repo when Epic ships. This is intentional — we don't want automatic pushes to the NYRA repo without operator review.

### Option B: Epic API polling (deferred v1.1)

Epic does not publish a machine-readable release calendar. The operator's manual `workflow_dispatch` is the v1 approach. Future: poll Unreal Engine GitHub release page monthly.

## GitHub Secrets Required

| Secret | Purpose | How to obtain |
|--------|---------|---------------|
| `HF_TOKEN` | Download BGE-small-en-v1.5 from HuggingFace | free at huggingface.co/settings/tokens (read-only) |
| `GITHUB_TOKEN` | Upload release assets | auto-provided by `softprops/action-gh-release` |

## Verification

```bash
# After first successful pipeline run:
# 1. Check the Release at: https://github.com/NYRA-NYRA/nyra-plugin/releases
#    Should have NyraIndex_{VERSION}_{DATE}.lance asset
# 2. Download and verify:
python -c "
import lancedb
db = lancedb.connect('NyraIndex_560_20260507.lance')
tbl = db.open_table('chunks')
print(f'Rows: {tbl.count_rows()}')
print(f'Schema: {tbl.schema}')
"
# Expected: >100,000 rows, schema matches 03-01 plan
# 3. Smoke test: query for 'FVector'
results = tbl.search('FVector').limit(5).to_list()
assert len(results) > 0, 'FVector not found in index'
```

## Resume Signal

- `index-pipeline-green` + GitHub Release URL with `NyraIndex_*.lance` asset + SHA256 checksum verified

## Threat Mitigations

| Threat | Mitigation |
|--------|------------|
| T-03-07-01: UE docs site blocks scraping | Build corpus archive first (manually or via browser); CI fetches archive from private GCS bucket OR operator pre-loads corpus on first CI run |
| T-03-07-02: BGE model download flaky | Cache model in Actions `~/.cache/huggingface/` between runs; pin model SHA in requirements.txt |
| T-03-07-03: Index corruption during upload | SHA256 checksum committed alongside; plugin verifies checksum before loading |

## Files Created by This Plan

| File | Purpose |
|------|---------|
| `.github/workflows/build-knowledge-index.yml` | Main pipeline |
| `.github/workflows/sync-ue-tags.yml` | Weekly Epic tag check (optional) |
| `scripts/fetch_ue_docs.py` | Scrape UE5 official docs |
| `scripts/extract_cpp_headers.py` | Parse UE C++ headers for API surface |
| `scripts/build_index.py` | LanceDB index builder (CLI) |
| `scripts/verify_index.py` | Local verification script |
| `.github/RELEASE_INDEX_HOWTO.md` | Operator runbook |

## Operator Actions

1. Create `ue-{version}` tag in NYRA-NYRA/nyra-plugin repo when Epic ships
2. Monitor Actions run at: `https://github.com/NYRA-NYRA/nyra-plugin/actions`
3. Verify Release asset appears at: `https://github.com/NYRA-NYRA/nyra-plugin/releases`
4. If CI fails, run `workflow_dispatch` manually with correct version
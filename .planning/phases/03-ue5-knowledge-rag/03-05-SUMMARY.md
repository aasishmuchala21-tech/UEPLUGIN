# Plan 03-05 Summary: Version-Tagged Chunk Deduplication and Index Update

**Phase:** 03-ue5-knowledge-rag
**Plan:** 03-05
**Type:** execute / TDD
**Wave:** 2
**Autonomous:** true | **TDD:** true
**Depends on:** [02, 03]
**Blocking preconditions:** 03-02 retrieval pipeline complete, 03-03 manifest builder complete

## Objectives

Extend the single-index system from 03-02 to per-version index files (`index_54.lance`, `index_56.lance`, `index_57.lance`), implement content deduplication across versions, and build the "Update Knowledge" button that fetches the latest index from GitHub Releases.

## What Was Built

### `ContentDedup` — SHA-256 content fingerprint deduplicator

```python
@dataclass
class DedupResult:
    chunk_id: str        # preserved for citation traceability
    fingerprint: str      # SHA-256 hex — canonical id
    content: str          # original raw text
    metadata: dict        # shallow copy
    versions: list[str]   # ["5.4", "5.6"] — accumulated
    is_new: bool          # True if fingerprint not in dedup log
```

On-disk fingerprint log (`fingerprint\tversion1,version2\n` per line) makes re-runs incremental — only new chunks get embedded. The dedup log appends on `flush()`, never rewrites.

### `IndexManager` — per-version index lifecycle

```python
class IndexManager:
    DEFAULT_INDEX_DIR = Path.home() / "AppData" / "Local" / "NYRA" / "knowledge"

    def list_indexes() -> list[IndexStatus]:
        """Returns status for all supported versions + bootstrap."""

    def resolve_index(ue_version: str) -> Path:
        """Priority: exact match → nearest earlier → bootstrap → empty path."""

    def check_for_update(ue_version, github_repo) -> UpdateCheckResult:
        """GET /repos/{repo}/releases — finds knowledge-v{version}-{date}.tar.lz4."""

    def download_and_swap(ue_version, download_url, *, progress_callback):
        """Downloads → staging dir → atomic swap → writes index_meta.json."""
```

Archive format: `.tar.lz4` (lzma2 compression, ~30% smaller than raw LanceDB directory copies for text-heavy UE docs). Atomic swap ensures the active index is never in a partial state.

### HTTP Endpoints

```python
GET /knowledge/status  → {"indexes": [{version, exists, chunk_count, built_at, source, size_bytes}]}
POST /knowledge/update → {ue_version} → download + swap → {"status": "updated"} or "up_to_date"
```

## Tests

- `test_index_manager.py` — List all versions, resolve fallback chain, update check (mocked GitHub), atomic swap behavior
- `test_deduplicator.py` — identical content across 3 versions merges to 1 result with `versions: ["5.4","5.6","5.7"]`, second pass marks `is_new: False`

## Files Created

| File | Purpose |
|------|---------|
| `NyraHost/nyra_host/knowledge/deduplicator.py` | ContentDedup + SHA-256 fingerprint log |
| `NyraHost/nyra_host/knowledge/index_manager.py` | IndexManager + IndexStatus + UpdateCheckResult |
| `NyraHost/nyra_host/knowledge/http_server.py` (update) | `/knowledge/status` + `/knowledge/update` routes |
| `NyraHost/tests/test_index_manager.py` | Full TDD suite |
| `NyraHost/tests/test_deduplicator.py` | Dedup tests |

## Module-Superset Discipline

No prior Phase 1-2 code modified. `NyraHost/nyra_host/knowledge/` package (sibling to `rag/` and `symbols/`).

## Next Steps

- Plan 03-06 wires Gemma 3 4B as offline Q&A engine (uses IndexManager via KnowledgeRetriever)
- Plan 03-07 builds the GitHub Actions pipeline that produces the release assets this plan downloads
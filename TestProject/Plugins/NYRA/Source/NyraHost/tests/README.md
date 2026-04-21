# NyraHost tests

Runs against the developer's system Python 3.12 with
`requirements-dev.lock` installed — NOT the bundled runtime python
(CONTEXT.md D-13 / D-14).

## Setup (dev machine, once)

```
cd TestProject/Plugins/NYRA/Source/NyraHost
python -m venv .venv-dev
.venv-dev\Scripts\activate
pip install -r requirements-dev.lock
```

macOS / Linux developers substitute `source .venv-dev/bin/activate`.

## Run

Quick (fail fast):
```
pytest tests/ -x
```

Full verbose:
```
pytest tests/ -v
```

Integration (spawns real subprocesses; slower):
```
pytest tests/ -v -m integration
```

Collection-only (no execution — Wave 0 smoke check):
```
pytest tests/ --collect-only -q
```

## Test files -> Plan mapping

Each test file is a Wave 0 placeholder with a single `@pytest.mark.skip`
function. The listed Plan owns the final implementation; the **VALIDATION
ID** column cross-references
`.planning/phases/01-plugin-shell-three-process-ipc/01-VALIDATION.md`
"Per-Task Verification Map".

| File                    | Plan | Test ID per VALIDATION |
|-------------------------|------|------------------------|
| test_auth.py            | 06   | 1-02-04                |
| test_handshake.py       | 06   | 1-02-05                |
| test_bootstrap.py       | 06   | 1-02-06                |
| test_infer_spawn.py     | 08   | 1-03-01                |
| test_ollama_detect.py   | 08   | 1-03-02                |
| test_sse_parser.py      | 08   | 1-03-03                |
| test_gemma_download.py  | 09   | 1-03-04                |
| test_storage.py         | 07   | 1-04-06                |
| test_attachments.py     | 07   | 1-04-07                |

## Shared fixtures (conftest.py)

- `tmp_project_dir` — unique Path mirroring `<ProjectDir>/Saved/NYRA/`
  with `logs/`, `models/`, `attachments/` subdirs pre-created.
- `mock_handshake_file` — writes a byte-exact D-06 handshake JSON
  (port 54321, deterministic pids, fresh 32-byte hex token) and returns
  its Path.
- `mock_llama_server` (async) — Wave 0 stub; Plan 08 implements the
  real port-capturing subprocess mock.
- `mock_ollama_transport` — Wave 0 stub; Plan 08 implements the real
  `httpx.MockTransport` covering `GET /api/tags`.

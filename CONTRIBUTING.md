# Contributing to NYRA

Thanks for considering a contribution. NYRA is solo-founder pace, so the bar
for landed PRs is high — but the path to your first PR is short.

## TL;DR

- Fork, clone, run `prebuild.ps1` on Windows, open `TestProject.uproject`
  in UE 5.6.
- Hack on `Source/NyraEditor` (C++/Slate) or `Source/NyraHost` (Python).
- `pytest -q` from `TestProject/Plugins/NYRA/Source/NyraHost/` must stay green.
- `RunUAT.bat BuildPlugin -Plugin=NYRA.uplugin` must succeed against UE 5.6.
- One-shot PRs only — no force-pushes after review starts.

## Prerequisites

| | Required |
|---|---|
| OS | Windows 10/11 x64 (Mac/Linux build land in v1.1) |
| UE | 5.4, 5.5, 5.6, or 5.7 (5.6 is the primary target) |
| Visual Studio | 2022 with "Game development with C++" workload |
| Python | 3.12 (the bundled CPython is 3.12; tests on 3.10+ work via the conftest shim) |
| Git LFS | yes (Icon128.png + future bundled assets are LFS) |
| PowerShell | 5.1+ for `prebuild.ps1` |

## First-time setup

```powershell
git clone https://github.com/aasishmuchala21-tech/UEPLUGIN.git
cd UEPLUGIN/TestProject/Plugins/NYRA

# Fetch CPython + llama.cpp builds (CUDA / Vulkan / CPU); SHA-256 verified
PowerShell -ExecutionPolicy Bypass -File prebuild.ps1

# Optional — Python dev environment for the sidecar
cd Source/NyraHost
python -m venv .venv
.venv/Scripts/Activate.ps1
pip install -e ".[dev]"
```

Open `UEPLUGIN/TestProject/TestProject.uproject` in Unreal Editor 5.6.
Tools menu → NYRA → Chat. Status pill turns green within 30 s if NyraHost
spawned cleanly.

## Repository layout (where to add what)

| You're touching | Module | Path |
|---|---|---|
| Slate chat panel widget | NyraEditor | `Source/NyraEditor/Public/Panel/`, `Source/NyraEditor/Private/Panel/` |
| New JSON-RPC method | NyraHost | `Source/NyraHost/src/nyrahost/handlers/` + register in `app.py::build_and_run::register` |
| New MCP tool the agent can call | NyraHost | `Source/NyraHost/src/nyrahost/tools/<your_tool>.py` |
| External API client (something on the public Internet) | NyraHost | `Source/NyraHost/src/nyrahost/external/` |
| Editor-side automation spec test | NyraEditor | `Source/NyraEditor/Private/Tests/<Your>Spec.cpp` |
| Python sidecar test | NyraHost | `Source/NyraHost/tests/test_<your>.py` |
| Wire-protocol change | docs | `docs/JSONRPC.md` (canonical), `docs/HANDSHAKE.md`, `docs/ERROR_CODES.md` |
| Decision record | planning | `.planning/phases/<NN>-<slug>/` — copy the shape of an existing phase |

## Coding style

### Python (`Source/NyraHost/`)

- `from __future__ import annotations` at every module head.
- 100-char line limit (`tool.ruff.line-length`, `tool.black.line-length`).
- Public types use `dataclass(frozen=True)` where they don't need mutation.
- Errors return JSON-RPC envelopes via the local `_err(code, message, ...)`
  helper, not raised exceptions across the WS boundary. Internal exceptions
  propagate upward and are caught by `server._dispatch`.
- Every module's docstring traces back to a numbered decision in
  `CLAUDE.md` or `.planning/phases/`. Don't add new code without the trail.
- No `shell=True`, no `os.system`, no `eval`, no `pickle.load`,
  no `yaml.load`, no string-concatenated SQL. Use parameterised everything.
- New disk writes go through `staging.StagingManifest._validate_path`.
- New external HTTP outbound goes via `httpx` (sidecar default) or
  `aiohttp` (when the existing module uses it).

### C++ (`Source/NyraEditor/`)

- C++20, `bUseUnity=false`, `BuildSettingsVersion.V5`.
- File header: `// SNyra<Name>.<ext> — <one-line purpose>.\n// Plan <NN>-<NN>.
  Build status: pending_manual_verification.`
- Module export macro is `NYRAEDITOR_API` on every public class.
- `NYRAEDITOR_API` is mandatory on widget classes used cross-module.
- `Invalidate(EInvalidateWidget::Paint)` after every state change in a
  Slate widget (the WR-08 convention).
- File-local color palette in an anonymous namespace — reuse the
  existing `Dominant / Accent / TextDim` from `SNyraImageDropZone.cpp`
  for visual consistency.
- Every Slate event is a `DECLARE_DELEGATE_OneParam(FOnNyra<...>, ...)`
  declared above the class and exposed via `SLATE_EVENT(...)`.

## Tests

```bash
# Python sidecar
cd TestProject/Plugins/NYRA/Source/NyraHost
pytest -v

# UE C++ automation specs (need a UE 5.6 install)
"%UE_56_DIR%/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" \
    %CD%/TestProject/TestProject.uproject \
    -ExecCmds="Automation RunTests Nyra;Quit" \
    -unattended -nopause -nullrhi
```

A `tests/conftest.py` shim makes the suite runnable on Python 3.10 (it
polyfills `enum.StrEnum` so older interpreters can collect the router
module). Production runs on the bundled 3.12 and ignores the shim.

Tests must be hermetic — mock `httpx.AsyncClient`, `aiohttp.ClientSession`,
`unreal.*` (the editor Python module isn't importable outside UE).

## CI

- `.github/workflows/plugin-matrix.yml` — `RunUAT.bat BuildPlugin` against
  UE 5.4 / 5.5 / 5.6 / 5.7 on a self-hosted Windows runner labelled
  `[self-hosted, Windows, unreal]`.
- `.github/workflows/pytest-host.yml` — full Python suite on the same
  runner.
- A new GitHub-hosted Linux runner for Python-only tests is in the v1.1
  backlog so external contributors can validate before PR.

If your fork doesn't have the self-hosted runner, the CI matrix won't run
on your branch — that's expected. We'll re-run on merge.

## Pull-request checklist

Before opening a PR:

- [ ] Branch named `feat/`, `fix/`, `docs/`, or `chore/` per [conventional commits](https://www.conventionalcommits.org/)
- [ ] Commit messages follow the repo's existing shape (look at recent log)
- [ ] All new code traces back to a decision in `CLAUDE.md` or `.planning/`
- [ ] `pytest -q` is green locally
- [ ] If you touched C++, you ran `RunUAT.bat BuildPlugin` against at
      least UE 5.6
- [ ] If you added a JSON-RPC method, you updated `docs/JSONRPC.md`
- [ ] If you added an error code, you appended it to `docs/ERROR_CODES.md`
- [ ] If you changed user-visible behaviour, you updated `README.md`
- [ ] No `localStorage`, `sessionStorage`, `eval`, `shell=True`, or other
      anti-patterns called out in `CLAUDE.md`

## Reporting bugs

Open an issue with:

1. UE version + NYRA tag/commit
2. Output of `Tools menu → NYRA → Tools → Export Chat`
3. The relevant `Saved/NYRA/logs/` excerpt
4. A minimal repro `TestProject` if behaviour is project-specific

For security-sensitive reports, email the founder directly (see `nyra.ai/support`).
Do not file public issues for things that look like RCE, credential
disclosure, or auth-bypass.

## What's out of scope

We will not accept PRs that:

- Bundle a paid third-party API key in the source tree
- Add SaaS-side telemetry or phone-home behaviour
- Disable, weaken, or work around `safe_mode.is_safe_mode() == True`
- Add browser automation that defeats Anthropic / OpenAI ToS
- Introduce GPL-incompatible licensing on bundled redistributables

## Where to start

Good first issues:

- **Documentation** — port any `CLAUDE.md` section into `docs.nyra.ai`
- **Tests** — every Python module under `tools/` should have ≥80% coverage
- **i18n** — replace raw `FText::FromString` calls in `Source/NyraEditor/Private/Panel/`
  with `LOCTEXT(...)` so the panel can be translated
- **`.editorconfig`** — settle the tabs-vs-spaces drift across `.cpp` files
- **Tier 1 panel UI** — wire one of the Phase 8 PARITY tools into the
  panel's Tools sidebar (see `.planning/phases/09-aura-killers/09-CONTEXT.md`)

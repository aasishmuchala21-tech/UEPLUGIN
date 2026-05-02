#!/bin/bash
# Phase 2 Wave 0 commit script
# Run from: /Users/aasish/Desktop/UEPLUG/UEPLUGIN

set -e
cd "$(dirname "$0")"

echo "=== Staging files for Phase 2 Wave 0 (Plans 02-01, 02-02, 02-03, 02-04) ==="

git add \
  docs/JSONRPC.md \
  docs/ERROR_CODES.md \
  .github/workflows/plugin-matrix.yml \
  .github/workflows/pytest-host.yml \
  .github/workflows/README-CI.md \
  legal/ev-cert-acquisition-runbook.md \
  legal/ev-cert-renewal-playbook.md \
  TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h \
  TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraCompatSpec.cpp \
  TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/__init__.py \
  TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/base.py \
  TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/gemma.py \
  TestProject/Plugins/NYRA/Source/NyraHost/tests/test_backend_interface.py \
  TestProject/Plugins/NYRA/Source/NyraHost/tests/test_gemma_backend_adapter.py \
  TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/chat.py

echo "Staged. Committing..."

# Commit 1: 02-02 docs
git commit -m "$(cat <<'EOF'
docs(02-02): extend JSONRPC spec + error codes for Phase 2

- docs/JSONRPC.md §4: add 10 new Phase 2 methods (§4.1–§4.10):
  chat/send.backend extension (claude), session/set-mode, plan/preview,
  plan/decision, console/exec, log/tail, log/message-log-list,
  diagnostics/backend-state, diagnostics/pie-state, claude/auth-status
- docs/ERROR_CODES.md: append Phase 2 codes -32007..-32014 with
  remediation templates + usage-by-plan matrix
- Phase 1 §1–§3 preserved verbatim (D-23/D-24 module-superset)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"

# Commit 2: 02-01 CI
git add .github/workflows/ TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraCompatSpec.cpp
git commit -m "$(cat <<'EOF'
feat(02-01): CI matrix workflow + plugin-matrix.yml + runner provision runbook + NYRACompat.h skeleton

- .github/workflows/plugin-matrix.yml: four-version UE BuildPlugin +
  Automation matrix (5.4/5.5/5.6/5.7), fail-fast:false, artifact upload
- .github/workflows/pytest-host.yml: single version-agnostic pytest job
- .github/workflows/README-CI.md: runner provisioning runbook
- TestProject/Plugins/NYRA/Source/NyraEditor/Public/NYRACompat.h: exports
  NYRA_UE_AT_LEAST macro + empty NYRA::Compat namespace
- TestProject/Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraCompatSpec.cpp:
  Nyra.Compat.Macro smoke-test It block for Automation runner discovery

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"

# Commit 3: 02-04 legal
git add legal/
git commit -m "$(cat <<'EOF'
docs(02-04): EV cert acquisition runbook (DigiCert + Azure Key Vault)

- legal/ev-cert-acquisition-runbook.md: 10-step founder runbook from
  business entity setup through GitHub Actions secrets population,
  including 6 binary targets to sign and timeline budget
- legal/ev-cert-renewal-playbook.md: day-300 calendar reminder,
  RFC 3161 timestamping safety net, renewal steps, Trusted Signing
  migration note for v2+

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"

# Commit 4: 02-03 backend interface
git add \
  TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/ \
  TestProject/Plugins/NYRA/Source/NyraHost/tests/test_backend_interface.py \
  TestProject/Plugins/NYRA/Source/NyraHost/tests/test_gemma_backend_adapter.py \
  TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/chat.py

git commit -m "$(cat <<'EOF'
feat(02-03): add AgentBackend ABC + extract GemmaBackend from Phase 1 router

- nyrahost/backends/base.py: AgentBackend ABC + BackendEvent tagged union
  (Delta/ToolUse/ToolResult/Done/Error/Retry) + HealthState str Enum
- nyrahost/backends/gemma.py: GemmaBackend(AgentBackend) wrapping
  Phase 1 InferRouter with zero behaviour change
- nyrahost/backends/__init__.py: BACKEND_REGISTRY + get_backend() factory
- handlers/chat.py: Phase 2 dispatch by params.backend; gemma-local
  preserves Phase 1 behaviour; claude raises NotImplementedError
  pointing to Plan 02-04
- test_backend_interface.py + test_gemma_backend_adapter.py: 12 tests
  covering ABC enforcement, registry contract, GemmaBackend adapter

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"

echo "=== All commits created ==="
git log --oneline -4
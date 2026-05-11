"""nyrahost.i18n_catalog — Phase 18-E source-of-truth string catalog.

Tier 3 polish. The UE chat panel uses raw `FText::FromString` calls
for most labels because adding LOCTEXT for each one piecemeal is
tedious. This module ships the catalog in one Python place so:

  1. UE-side i18n work (Phase 14-I / 15-B-style LOCTEXT extraction)
     has a single export point.
  2. Future translation contributors get a clean JSON file per
     locale instead of grepping .cpp.
  3. The WS handler `i18n/catalog` returns the catalog so an
     IDE-mode integration can render the panel in JP / ZH / KR
     without UE-side changes when an external translator returns
     a locale JSON.

The catalog is intentionally LIMITED to chat-panel + Tools-sidebar
strings — not a substitute for UE's built-in localisation pipeline.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Final

import structlog

log = structlog.get_logger("nyrahost.i18n_catalog")

CATALOG_NAMESPACE: Final[str] = "NyraPanel"

# Canonical English strings used in the chat panel + sidebar.
# Each key is (namespace, key) per UE LOCTEXT shape.
# Update IN ONE PLACE; future translators extract from here.
CATALOG: Final[dict[str, str]] = {
    # Chat panel
    "panel.title":             "NYRA Chat",
    "panel.send":              "Send",
    "panel.cancel":            "Cancel",
    "panel.clear":             "Clear",
    "panel.attach":            "Attach…",
    "panel.history":           "History",
    "panel.settings":          "Settings",
    "panel.new_chat":          "New chat",
    "panel.status.ready":      "Ready",
    "panel.status.connecting": "Connecting…",
    "panel.status.spawning":   "Spawning sidecar…",
    "panel.status.crashed":    "NyraHost crashed — restarting",
    "panel.status.unstable":   "NyraHost unstable — see logs",

    # Mode toggle (Phase 11)
    "mode.ask":   "Ask",
    "mode.plan":  "Plan",
    "mode.agent": "Agent",
    "mode.ask.tooltip":   "Read-only — knowledge tools only, mutations refuse",
    "mode.plan.tooltip":  "Generate a preview; you Approve before each mutation",
    "mode.agent.tooltip": "Auto-execute pre-approved plans; safe-mode still ON",

    # Model selector (Phase 10)
    "model.default":     "(default)",
    "model.cheap":       "claude-haiku-4-5",
    "model.balanced":    "claude-sonnet-4-6",
    "model.expensive":   "claude-opus-4-7",

    # Settings tab (Phase 18-F)
    "settings.title":          "NYRA Settings",
    "settings.instructions":   "Custom Instructions",
    "settings.instructions.hint": "Don't paste secrets — this file may be checked into git.",
    "settings.privacy":        "Privacy Mode",
    "settings.privacy.tooltip": "Refuses any outbound HTTP to Anthropic / Meshy / ComfyUI / OpenAI.",
    "settings.cost":           "Cost forecast",
    "settings.audit":          "Audit log",
    "settings.repro_seed":     "Reproducibility seed",
    "settings.repro_temp":     "Sampling temperature",
    "settings.mcp_install":    "Install in your IDE",
    "settings.user_tools":     "User tools",
    "settings.marketplace":    "Plugin marketplace",
    "settings.multiplayer":    "Multiplayer rooms",

    # Sidebar (Phase 14-I)
    "sidebar.authoring":          "Authoring agents",
    "sidebar.whole_project":      "Whole-project agents",
    "sidebar.bt":                 "Behavior Tree",
    "sidebar.niagara":            "Niagara VFX",
    "sidebar.animbp":             "Animation Blueprint",
    "sidebar.metasound":          "MetaSound",
    "sidebar.cpp_live":           "C++ Live Coding",
    "sidebar.perf":               "Performance profiling",
    "sidebar.material":           "Material",
    "sidebar.hygiene":            "Asset Hygiene",
    "sidebar.perf_budget":        "Perf Budget check",
    "sidebar.crash_rca":          "Crash RCA",
    "sidebar.test_gen":           "Test scaffolding",
    "sidebar.doc_from_code":      "Doc-from-code",
    "sidebar.replication":        "Replication scaffold",
    "sidebar.cinematic":          "Cinematic / DOP",
    "sidebar.localization":       "Localization",

    # Common errors / remediation
    "err.privacy_refused":      "Privacy Mode is on — outbound HTTP refused. Disable in Settings to allow.",
    "err.gemma_not_installed":  "Gemma model not downloaded yet. Click Download in Settings.",
    "err.local_sd_not_installed": "On-device Stable Diffusion needs diffusers + torch. See Settings → Install.",
}


def export_locale(strings: dict[str, str], *, locale: str) -> str:
    """Render a locale JSON for shipping to translators.

    Translator returns the same file with values replaced; the panel
    side loads via i18n/load (the WS handler below).
    """
    body = {
        "$schema": "nyra-i18n-v1",
        "namespace": CATALOG_NAMESPACE,
        "locale": locale,
        "strings": dict(strings),
    }
    return json.dumps(body, indent=2, ensure_ascii=False)


def lookup(key: str, *, default: str | None = None) -> str:
    """Sidecar-side lookup, useful when the chat handler needs to
    render an error string (e.g. for the audit log payload) in the
    user's UI locale rather than English."""
    return CATALOG.get(key, default or key)


# WS handler
async def on_catalog(params: dict, session=None, ws=None) -> dict:
    return {
        "namespace": CATALOG_NAMESPACE,
        "locale": "en",
        "strings": dict(CATALOG),
        "version": "phase-18",
    }


__all__ = [
    "CATALOG",
    "CATALOG_NAMESPACE",
    "export_locale",
    "lookup",
    "on_catalog",
]

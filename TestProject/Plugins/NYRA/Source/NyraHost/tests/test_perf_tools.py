"""Plan 08-06 PARITY-06 — Performance Profiling tools.

Coverage map (per the plan's "Tests" table + user's commit grouping):

    C1  PerfStatReadTool    — schema + WS forward + duration cap + bad args
    C1  parse_stat_unit_text — regex over `stat unit` text (unit fixture)
    C2  PerfInsightsQueryTool — path validation + missing-trace remediation
                                 (live `.utrace` parse is operator-runbook
                                 deferred per RESEARCH.md A7; documented in
                                 08-06-VERIFICATION.md)
    C3  PerfExplainHotspotTool — LOCKED-05 schema + T-08-05 dual path:
                                  (a) KB index loaded -> citations populated
                                  (b) KB index missing -> citations_status
                                      "no_index_loaded" + remediation populated
                                  Plus error propagation when KbSearchTool errs.
"""
from __future__ import annotations

from pathlib import Path

from nyrahost.tools.base import NyraToolResult
from nyrahost.tools.perf_tools import (
    MAX_DURATION_MS,
    VALID_STATS,
    PerfExplainHotspotTool,
    handle_nyra_perf_insights_query,
    handle_nyra_perf_stat_read,
    parse_stat_unit_text,
)


# =============================================================================
# C1 — handle_nyra_perf_stat_read (WS forwarder)
# =============================================================================


SAMPLE_STAT_UNIT_TEXT = """
Frame: 16.7 ms (60 FPS)
Game: 8.2 ms
Draw: 4.1 ms
GPU: 12.5 ms
RHIT: 1.2 ms
DynRes: 1080p
""".strip()


class TestPerfStatReadDefaults:
    def test_max_duration_cap(self):
        assert MAX_DURATION_MS == 5000

    def test_valid_stats_set(self):
        assert "unit" in VALID_STATS
        assert "unitgraph" in VALID_STATS
        assert "memory" in VALID_STATS
        assert "gpu" in VALID_STATS


class TestPerfStatReadHandler:
    """Mirrors test_log_tail.TestLogTailHandler shape."""

    async def test_emits_perf_stat_read_ws_method(self):
        calls = []

        async def mock_emit(method, params):
            calls.append({"method": method, "params": params})
            return {"raw_text": "Frame: 16.7 ms", "parsed": {}}

        await handle_nyra_perf_stat_read({"stat": "unit"}, mock_emit)
        assert calls[0]["method"] == "perf/stat-read"
        assert calls[0]["params"]["stat"] == "unit"

    async def test_default_stat_is_unit(self):
        calls = []

        async def mock_emit(method, params):
            calls.append(params)
            return {}

        await handle_nyra_perf_stat_read({}, mock_emit)
        assert calls[0]["stat"] == "unit"

    async def test_default_duration_ms(self):
        calls = []

        async def mock_emit(method, params):
            calls.append(params)
            return {}

        await handle_nyra_perf_stat_read({"stat": "gpu"}, mock_emit)
        assert calls[0]["duration_ms"] == 1000

    async def test_duration_cap_enforced(self):
        calls = []

        async def mock_emit(method, params):
            calls.append(params)
            return {}

        await handle_nyra_perf_stat_read(
            {"stat": "unit", "duration_ms": 99999}, mock_emit
        )
        assert calls[0]["duration_ms"] <= MAX_DURATION_MS

    async def test_negative_duration_clamped_to_zero(self):
        calls = []

        async def mock_emit(method, params):
            calls.append(params)
            return {}

        await handle_nyra_perf_stat_read(
            {"stat": "unit", "duration_ms": -500}, mock_emit
        )
        assert calls[0]["duration_ms"] == 0

    async def test_invalid_stat_rejected(self):
        async def mock_emit(method, params):  # pragma: no cover — should not be called
            raise AssertionError("emit invoked on bad input")

        result = await handle_nyra_perf_stat_read(
            {"stat": "frame_time"}, mock_emit
        )
        assert "error" in result
        assert result["error"]["code"] == -32602
        assert "stat must be one of" in result["error"]["message"]

    async def test_non_integer_duration_rejected(self):
        async def mock_emit(method, params):  # pragma: no cover
            raise AssertionError("emit invoked on bad input")

        result = await handle_nyra_perf_stat_read(
            {"stat": "unit", "duration_ms": "soon"}, mock_emit
        )
        assert "error" in result
        assert result["error"]["code"] == -32602

    async def test_passes_through_ws_payload(self):
        async def mock_emit(method, params):
            return {"raw_text": "Frame: 16.7 ms (60 FPS)", "parsed": {"frame": 16.7}}

        result = await handle_nyra_perf_stat_read({"stat": "unit"}, mock_emit)
        assert result["raw_text"].startswith("Frame:")
        assert result["parsed"]["frame"] == 16.7


# =============================================================================
# C1 — parse_stat_unit_text (regex over `stat unit` console output)
# =============================================================================


class TestParseStatUnitText:
    def test_parses_canonical_stat_unit_block(self):
        parsed = parse_stat_unit_text(SAMPLE_STAT_UNIT_TEXT)
        assert parsed["frame"] == 16.7
        assert parsed["fps"] == 60.0
        assert parsed["game"] == 8.2
        assert parsed["draw"] == 4.1
        assert parsed["gpu"] == 12.5
        assert parsed["rhit"] == 1.2

    def test_empty_input_returns_empty_dict(self):
        assert parse_stat_unit_text("") == {}

    def test_none_input_returns_empty_dict(self):
        assert parse_stat_unit_text(None) == {}  # type: ignore[arg-type]

    def test_malformed_lines_skipped(self):
        text = "Frame: 16.7 ms (60 FPS)\nGarbage\n??? :: bad\nGame: 8.2 ms"
        parsed = parse_stat_unit_text(text)
        assert parsed["frame"] == 16.7
        assert parsed["game"] == 8.2

    def test_single_line_no_fps(self):
        parsed = parse_stat_unit_text("Draw: 4.1 ms")
        assert parsed == {"draw": 4.1}

    def test_no_matches_returns_empty(self):
        assert parse_stat_unit_text("Hello world") == {}


# =============================================================================
# C2 — handle_nyra_perf_insights_query (WS forwarder + path validation)
# =============================================================================


class TestPerfInsightsQuery:
    async def test_missing_trace_path_rejected(self):
        async def mock_emit(method, params):  # pragma: no cover
            raise AssertionError("emit invoked on bad input")

        result = await handle_nyra_perf_insights_query({}, mock_emit)
        assert "error" in result
        assert result["error"]["code"] == -32602

    async def test_empty_string_trace_path_rejected(self):
        async def mock_emit(method, params):  # pragma: no cover
            raise AssertionError("emit invoked on bad input")

        result = await handle_nyra_perf_insights_query(
            {"trace_path": "   "}, mock_emit
        )
        assert "error" in result

    async def test_nonexistent_trace_returns_remediation(self, tmp_path: Path):
        async def mock_emit(method, params):  # pragma: no cover
            raise AssertionError("emit invoked on missing trace")

        result = await handle_nyra_perf_insights_query(
            {"trace_path": str(tmp_path / "does-not-exist.utrace")},
            mock_emit,
        )
        assert result["status"] == "no_trace_loaded"
        assert "remediation" in result
        assert "Saved/Profiling" in result["remediation"]

    async def test_wrong_extension_rejected(self, tmp_path: Path):
        bad = tmp_path / "trace.txt"
        bad.write_bytes(b"not a utrace")

        async def mock_emit(method, params):  # pragma: no cover
            raise AssertionError("emit invoked on bad suffix")

        result = await handle_nyra_perf_insights_query(
            {"trace_path": str(bad)}, mock_emit
        )
        assert "error" in result
        assert ".utrace" in result["error"]["message"]

    async def test_valid_trace_forwards_to_ws(self, tmp_path: Path):
        # Synthesize a tiny placeholder file. Per RESEARCH.md A7, the
        # binary `.utrace` format is engine-internal — we cannot
        # synthesize a valid trace on the dev box. The Python tool
        # validates path + suffix and forwards; the UE-side helper
        # reports `status: "unsupported"` when Insights headless export
        # is unavailable, which is the v1 deferred state.
        trace = tmp_path / "fake.utrace"
        trace.write_bytes(b"\x00\x00")  # placeholder bytes

        captured = []

        async def mock_emit(method, params):
            captured.append({"method": method, "params": params})
            return {"status": "unsupported", "remediation": "Insights -ExportCSV not available"}

        result = await handle_nyra_perf_insights_query(
            {"trace_path": str(trace)}, mock_emit
        )
        assert captured[0]["method"] == "perf/insights-export"
        assert captured[0]["params"]["trace_path"].endswith("fake.utrace")
        assert captured[0]["params"]["output_path"].endswith("fake.csv")
        # The "unsupported" envelope passes through verbatim — never
        # silent no-op (T-08-05 lesson generalised).
        assert result["status"] == "unsupported"


# =============================================================================
# C3 — PerfExplainHotspotTool (LOCKED-05 + T-08-05 dual-path)
# =============================================================================


class _FakeKb:
    """Drop-in fake of KbSearchTool exposing only `.execute()`."""

    def __init__(self, result: NyraToolResult) -> None:
        self._result = result
        self.calls: list[dict] = []

    def execute(self, params: dict) -> NyraToolResult:
        self.calls.append(params)
        return self._result


class TestPerfExplainHotspotSchema:
    def test_rejects_missing_label(self):
        tool = PerfExplainHotspotTool()
        result = tool.execute({})
        assert not result.is_ok
        assert "hotspot_label_required" in result.error

    def test_rejects_blank_label(self):
        tool = PerfExplainHotspotTool()
        result = tool.execute({"hotspot_label": "   "})
        assert not result.is_ok

    def test_rejects_oversized_label(self):
        tool = PerfExplainHotspotTool()
        result = tool.execute({"hotspot_label": "x" * 300})
        assert not result.is_ok
        assert "too_long" in result.error

    def test_rejects_non_string_metric(self):
        tool = PerfExplainHotspotTool()
        result = tool.execute(
            {"hotspot_label": "Draw", "hotspot_metric": 12.5}
        )
        assert not result.is_ok
        assert "hotspot_metric" in result.error


class TestPerfExplainHotspotCitationsOK:
    """LOCKED-05 path A — KB index loaded → citations populated."""

    def test_citations_populated_when_index_loaded(self):
        tool = PerfExplainHotspotTool()
        fake_kb = _FakeKb(
            NyraToolResult.ok(
                {
                    "status": "ok",
                    "indexed_chunks": 42,
                    "results": [
                        {
                            "chunk_id": "ue-rendering.md#0",
                            "source_path": "ue-rendering.md",
                            "heading_path": ["Rendering", "Optimization"],
                            "body": (
                                "DrawIndexedPrimitive batches geometry "
                                "by material. Reduce material variants "
                                "to lower draw-call count."
                            ),
                            "score": 0.91,
                        },
                        {
                            "chunk_id": "ue-perf.md#3",
                            "source_path": "ue-perf.md",
                            "heading_path": ["Performance", "GPU"],
                            "body": "Profile with stat GPU; hotspots over 12 ms warrant investigation.",
                            "score": 0.74,
                        },
                    ],
                }
            )
        )
        tool._kb = fake_kb

        result = tool.execute(
            {"hotspot_label": "DrawIndexedPrimitive", "hotspot_metric": "12.5 ms"}
        )

        assert result.is_ok
        d = result.data
        # LOCKED-05 — all six fields MUST be present.
        assert d["hotspot_label"] == "DrawIndexedPrimitive"
        assert d["hotspot_metric"] == "12.5 ms"
        assert isinstance(d["explanation"], str)
        assert len(d["explanation"]) > 0
        assert d["citations"] == ["ue-rendering.md", "ue-perf.md"]
        assert d["citations_status"] == "ok"
        assert d["citations_remediation"] is None

    def test_dedupes_citations_by_source_path(self):
        tool = PerfExplainHotspotTool()
        # Two chunks from the same docs file should produce one citation.
        tool._kb = _FakeKb(
            NyraToolResult.ok(
                {
                    "status": "ok",
                    "results": [
                        {
                            "chunk_id": "ue-rendering.md#0",
                            "source_path": "ue-rendering.md",
                            "body": "Sentence one. Sentence two.",
                            "score": 0.9,
                        },
                        {
                            "chunk_id": "ue-rendering.md#1",
                            "source_path": "ue-rendering.md",
                            "body": "Sentence three.",
                            "score": 0.8,
                        },
                    ],
                }
            )
        )

        result = tool.execute({"hotspot_label": "Draw"})
        assert result.is_ok
        assert result.data["citations"] == ["ue-rendering.md"]
        assert result.data["citations_status"] == "ok"

    def test_explanation_uses_first_sentences(self):
        tool = PerfExplainHotspotTool()
        tool._kb = _FakeKb(
            NyraToolResult.ok(
                {
                    "status": "ok",
                    "results": [
                        {
                            "chunk_id": "x.md#0",
                            "source_path": "x.md",
                            "body": "GPU bottleneck most often comes from overdraw. Then secondary text.",
                            "score": 0.9,
                        }
                    ],
                }
            )
        )
        result = tool.execute({"hotspot_label": "GPU"})
        assert "overdraw" in result.data["explanation"].lower()
        # Must NOT contain the second sentence — first-sentence heuristic only.
        assert "secondary text" not in result.data["explanation"].lower()

    def test_query_includes_optimization_bias(self):
        tool = PerfExplainHotspotTool()
        fake = _FakeKb(NyraToolResult.ok({"status": "ok", "results": []}))
        tool._kb = fake

        tool.execute({"hotspot_label": "StaticMeshDrawCalls"})
        # Query is biased toward optimization guidance per the design.
        assert "performance optimization" in fake.calls[0]["query"].lower()
        assert "StaticMeshDrawCalls" in fake.calls[0]["query"]


class TestPerfExplainHotspotCitationsDegraded:
    """LOCKED-05 + T-08-05 path B — KB index missing → graceful degrade.

    THIS IS THE NON-NEGOTIABLE TEST. The "beats Aura" claim requires the
    citations field to NEVER silently come back empty paired with
    citations_status="ok".
    """

    def test_no_index_loaded_populates_remediation(self):
        tool = PerfExplainHotspotTool()
        tool._kb = _FakeKb(
            NyraToolResult.ok(
                {
                    "status": "no_index_loaded",
                    "results": [],
                    "remediation": (
                        "No UE5 knowledge index found. Open NYRA "
                        "settings and click 'Download UE5 Knowledge "
                        "Index'."
                    ),
                }
            )
        )

        result = tool.execute(
            {"hotspot_label": "DrawIndexedPrimitive", "hotspot_metric": "12.5 ms"}
        )

        assert result.is_ok
        d = result.data
        # LOCKED-05 — all six fields STILL present in the degraded path.
        assert d["hotspot_label"] == "DrawIndexedPrimitive"
        assert d["hotspot_metric"] == "12.5 ms"
        assert isinstance(d["explanation"], str) and len(d["explanation"]) > 0
        # T-08-05 — empty list, status flipped, remediation populated.
        assert d["citations"] == []
        assert d["citations_status"] == "no_index_loaded"
        assert d["citations_remediation"] is not None
        assert "Download" in d["citations_remediation"]

    def test_no_index_never_emits_ok_with_empty_citations(self):
        """The exact failure mode T-08-05 forbids."""
        tool = PerfExplainHotspotTool()
        tool._kb = _FakeKb(
            NyraToolResult.ok(
                {
                    "status": "no_index_loaded",
                    "results": [],
                    "remediation": "load the index",
                }
            )
        )

        result = tool.execute({"hotspot_label": "X"})
        assert result.is_ok
        # The forbidden combination:
        forbidden = (
            result.data["citations"] == []
            and result.data["citations_status"] == "ok"
        )
        assert not forbidden, (
            "T-08-05 violation: empty citations + status='ok'. "
            "Must flip status to 'no_index_loaded' with remediation."
        )

    def test_uses_kb_remediation_verbatim(self):
        tool = PerfExplainHotspotTool()
        tool._kb = _FakeKb(
            NyraToolResult.ok(
                {
                    "status": "no_index_loaded",
                    "results": [],
                    "remediation": "RUN_NYRA_KB_INDEX_BUILD_FIRST_PLEASE",
                }
            )
        )

        result = tool.execute({"hotspot_label": "X"})
        assert (
            result.data["citations_remediation"]
            == "RUN_NYRA_KB_INDEX_BUILD_FIRST_PLEASE"
        )

    def test_kb_error_propagates(self):
        tool = PerfExplainHotspotTool()
        tool._kb = _FakeKb(NyraToolResult.err("kb_index_load_failed: bad json"))

        result = tool.execute({"hotspot_label": "Draw"})
        assert not result.is_ok
        assert "kb_search_failed" in result.error
        assert "bad json" in result.error


class TestPerfExplainHotspotIntegrationWithRealKbSearch:
    """End-to-end path through the real KbSearchTool (no mocks).

    Confirms the composition wiring is correct without relying solely
    on the _FakeKb shim — exercises the real
    KbSearchTool._resolve_index_path → "no_index_loaded" branch, which
    is what an operator with no index will hit.
    """

    def test_real_kb_search_no_index_branch(self, tmp_path: Path, monkeypatch):
        # Force KbSearchTool's resolution chain to find no index at all
        # — including the bundled seed corpus that ships with NyraHost.
        from nyrahost.tools import kb_search as kb_module
        monkeypatch.setattr(
            kb_module,
            "_default_index_paths",
            lambda: [tmp_path / "nope-1.json", tmp_path / "nope-2.json"],
        )

        tool = PerfExplainHotspotTool()
        result = tool.execute({"hotspot_label": "DrawIndexedPrimitive"})

        assert result.is_ok
        d = result.data
        assert d["citations"] == []
        assert d["citations_status"] == "no_index_loaded"
        assert d["citations_remediation"] is not None
        # The verbatim remediation comes from KbSearchTool — must
        # mention "Download" or the LOCALAPPDATA path so the operator
        # knows what to do.
        rem = d["citations_remediation"]
        assert "Download" in rem or "LOCALAPPDATA" in rem

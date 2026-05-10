"""Tests for nyrahost.tools.cpp_authoring_tools — Plan 08-02 PARITY-02.

File-IO + parameter validation for the four `nyra_cpp_*` mutator tools.
The recompile end-to-end (which needs `unreal.NyraLiveCodingHelper`) is
covered separately by test_cpp_recompile_mock.py.

We mock the `unreal` module so blueprint_debug's `import unreal` doesn't
explode at collection time. The mutator file-IO does NOT call into UE —
it's pure filesystem — so the MagicMock surface is sufficient.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Mock `unreal` BEFORE the cpp_authoring_tools import chain reaches
# blueprint_debug (which imports unreal at module top).
sys.modules.setdefault("unreal", MagicMock())

from nyrahost import cpp_authoring_state as cas  # noqa: E402
from nyrahost.tools.cpp_authoring_tools import (  # noqa: E402
    CppClassAddTool,
    CppFunctionAddTool,
    CppModuleCreateTool,
    CppRecompileTool,
)
from nyrahost.tools.base import idempotent_clear  # noqa: E402


@pytest.fixture(autouse=True)
def _isolation():
    """Each test starts with a clean idempotency cache + authored set."""
    idempotent_clear()
    cas.clear_session()
    yield
    idempotent_clear()
    cas.clear_session()


# ---------------------------------------------------------------------------
# Surface contract: every tool returns NyraToolResult, never a raw dict.
# ---------------------------------------------------------------------------

class TestNyraToolResultSurface:
    def test_module_create_returns_nyra_tool_result(self, tmp_path: Path):
        tool = CppModuleCreateTool()
        result = tool.execute({
            "module_name": "MyMod",
            "parent_dir": str(tmp_path),
            "type": "Runtime",
        })
        assert hasattr(result, "to_dict"), "must return NyraToolResult"
        assert result.is_ok
        assert "module_name" in result.data

    def test_invalid_module_name_returns_err(self, tmp_path: Path):
        tool = CppModuleCreateTool()
        result = tool.execute({
            "module_name": "1Bad-Name",  # starts with digit + has dash
            "parent_dir": str(tmp_path),
        })
        assert hasattr(result, "to_dict")
        assert not result.is_ok
        assert "invalid module_name" in result.error

    def test_invalid_type_returns_err(self, tmp_path: Path):
        tool = CppModuleCreateTool()
        result = tool.execute({
            "module_name": "Mod",
            "parent_dir": str(tmp_path),
            "type": "Bogus",
        })
        assert not result.is_ok
        assert "invalid type" in result.error


# ---------------------------------------------------------------------------
# nyra_cpp_module_create
# ---------------------------------------------------------------------------

class TestModuleCreate:
    def test_creates_build_cs_and_subdirs(self, tmp_path: Path):
        tool = CppModuleCreateTool()
        result = tool.execute({
            "module_name": "MyMod",
            "parent_dir": str(tmp_path),
            "type": "Runtime",
        })
        assert result.is_ok
        mod = tmp_path / "MyMod"
        assert (mod / "Public").is_dir()
        assert (mod / "Private").is_dir()
        build_cs = mod / "MyMod.Build.cs"
        assert build_cs.exists()
        text = build_cs.read_text(encoding="utf-8")
        assert "public class MyMod : ModuleRules" in text
        assert "Engine" in text
        # Runtime module: should NOT pull in editor deps.
        assert "UnrealEd" not in text

    def test_editor_module_pulls_unreal_ed(self, tmp_path: Path):
        tool = CppModuleCreateTool()
        result = tool.execute({
            "module_name": "MyEd",
            "parent_dir": str(tmp_path),
            "type": "Editor",
        })
        assert result.is_ok
        text = (tmp_path / "MyEd" / "MyEd.Build.cs").read_text(encoding="utf-8")
        assert "UnrealEd" in text
        assert "Slate" in text

    def test_records_build_cs_in_authored_set(self, tmp_path: Path):
        tool = CppModuleCreateTool()
        tool.execute({"module_name": "MyMod", "parent_dir": str(tmp_path)})
        assert cas.is_authored(tmp_path / "MyMod" / "MyMod.Build.cs")

    def test_idempotent_second_call_returns_deduped(self, tmp_path: Path):
        tool = CppModuleCreateTool()
        params = {"module_name": "MyMod", "parent_dir": str(tmp_path)}
        first = tool.execute(params)
        assert first.is_ok
        second = tool.execute(params)
        assert second.is_ok
        assert second.data.get("deduped") is True

    def test_path_traversal_in_module_name_rejected(self, tmp_path: Path):
        tool = CppModuleCreateTool()
        # The ident-validation rule rejects `..` outright.
        result = tool.execute({
            "module_name": "../../../etc/passwd",
            "parent_dir": str(tmp_path),
        })
        assert not result.is_ok
        assert "invalid module_name" in result.error

    def test_missing_parent_dir_rejected(self):
        tool = CppModuleCreateTool()
        result = tool.execute({"module_name": "Mod", "parent_dir": ""})
        assert not result.is_ok


# ---------------------------------------------------------------------------
# nyra_cpp_class_add
# ---------------------------------------------------------------------------

class TestClassAdd:
    def _seed_module(self, tmp_path: Path) -> Path:
        CppModuleCreateTool().execute({
            "module_name": "MyMod",
            "parent_dir": str(tmp_path),
            "type": "Runtime",
        })
        return tmp_path / "MyMod"

    def test_creates_header_and_impl(self, tmp_path: Path):
        mod = self._seed_module(tmp_path)
        result = CppClassAddTool().execute({
            "module_dir": str(mod),
            "module_name": "MyMod",
            "class_name": "MyActor",
            "parent_class": "AActor",
        })
        assert result.is_ok, result.error
        header = mod / "Public" / "MyActor.h"
        impl = mod / "Private" / "MyActor.cpp"
        assert header.exists()
        assert impl.exists()
        # AActor-derived → A prefix.
        assert "AMyActor" in header.read_text(encoding="utf-8")
        assert "MYMOD_API" in header.read_text(encoding="utf-8")

    def test_uobject_parent_uses_u_prefix(self, tmp_path: Path):
        mod = self._seed_module(tmp_path)
        result = CppClassAddTool().execute({
            "module_dir": str(mod),
            "module_name": "MyMod",
            "class_name": "Settings",
            "parent_class": "UObject",
        })
        assert result.is_ok
        assert "USettings" in (mod / "Public" / "Settings.h").read_text(encoding="utf-8")

    def test_rejects_non_authored_module(self, tmp_path: Path):
        # Pretend the module exists but NYRA didn't author its Build.cs.
        mod = tmp_path / "ForeignMod"
        (mod / "Public").mkdir(parents=True)
        (mod / "Private").mkdir()
        (mod / "ForeignMod.Build.cs").write_text("// not nyra", encoding="utf-8")

        result = CppClassAddTool().execute({
            "module_dir": str(mod),
            "module_name": "ForeignMod",
            "class_name": "Hacker",
            "parent_class": "AActor",
        })
        assert not result.is_ok
        assert "Out-of-Scope" in result.error

    def test_records_header_and_impl_in_authored_set(self, tmp_path: Path):
        mod = self._seed_module(tmp_path)
        CppClassAddTool().execute({
            "module_dir": str(mod),
            "module_name": "MyMod",
            "class_name": "MyActor",
            "parent_class": "AActor",
        })
        assert cas.is_authored(mod / "Public" / "MyActor.h")
        assert cas.is_authored(mod / "Private" / "MyActor.cpp")

    def test_invalid_class_name_rejected(self, tmp_path: Path):
        mod = self._seed_module(tmp_path)
        result = CppClassAddTool().execute({
            "module_dir": str(mod),
            "module_name": "MyMod",
            "class_name": "1Bad",
            "parent_class": "AActor",
        })
        assert not result.is_ok


# ---------------------------------------------------------------------------
# nyra_cpp_function_add
# ---------------------------------------------------------------------------

class TestFunctionAdd:
    def _seed_class(self, tmp_path: Path) -> tuple[Path, Path]:
        CppModuleCreateTool().execute({
            "module_name": "MyMod",
            "parent_dir": str(tmp_path),
            "type": "Runtime",
        })
        mod = tmp_path / "MyMod"
        CppClassAddTool().execute({
            "module_dir": str(mod),
            "module_name": "MyMod",
            "class_name": "MyActor",
            "parent_class": "AActor",
        })
        return mod / "Public" / "MyActor.h", mod / "Private" / "MyActor.cpp"

    def test_adds_decl_to_header_and_impl_to_cpp(self, tmp_path: Path):
        header, impl = self._seed_class(tmp_path)
        result = CppFunctionAddTool().execute({
            "header_path": str(header),
            "impl_path": str(impl),
            "class_name": "AMyActor",
            "signature": "void DoTheThing(int32 Count)",
            "body": 'UE_LOG(LogTemp, Log, TEXT("hi"));',
        })
        assert result.is_ok, result.error
        h_text = header.read_text(encoding="utf-8")
        c_text = impl.read_text(encoding="utf-8")
        assert "DoTheThing(int32 Count)" in h_text
        assert "UFUNCTION(BlueprintCallable)" in h_text
        assert "AMyActor::DoTheThing" in c_text
        assert "UE_LOG(LogTemp, Log" in c_text

    def test_rejects_non_authored_files(self, tmp_path: Path):
        # Manually create files NYRA didn't author.
        h = tmp_path / "Foreign.h"
        c = tmp_path / "Foreign.cpp"
        h.write_text("class UForeign { public: };", encoding="utf-8")
        c.write_text("// foreign", encoding="utf-8")

        result = CppFunctionAddTool().execute({
            "header_path": str(h),
            "impl_path": str(c),
            "class_name": "UForeign",
            "signature": "void Hack()",
        })
        assert not result.is_ok
        assert "Out-of-Scope" in result.error

    def test_unknown_class_in_header_returns_err(self, tmp_path: Path):
        header, impl = self._seed_class(tmp_path)
        result = CppFunctionAddTool().execute({
            "header_path": str(header),
            "impl_path": str(impl),
            "class_name": "AOtherActor",  # not actually in the header
            "signature": "void X()",
        })
        assert not result.is_ok
        assert "could not locate class body" in result.error

    def test_empty_signature_rejected(self, tmp_path: Path):
        header, impl = self._seed_class(tmp_path)
        result = CppFunctionAddTool().execute({
            "header_path": str(header),
            "impl_path": str(impl),
            "class_name": "AMyActor",
            "signature": "   ",
        })
        assert not result.is_ok


# ---------------------------------------------------------------------------
# nyra_cpp_recompile parameter validation
# ---------------------------------------------------------------------------

class TestRecompileGate:
    def test_module_scope_requires_module_dir(self):
        result = CppRecompileTool().execute({"scope": "module"})
        assert not result.is_ok
        assert "module_dir is required" in result.error

    def test_invalid_scope_rejected(self):
        result = CppRecompileTool().execute({"scope": "bogus"})
        assert not result.is_ok
        assert "invalid scope" in result.error

    def test_recompile_aborts_on_non_authored_files(self, tmp_path: Path):
        # Manually create a module dir with a foreign .cpp.
        mod = tmp_path / "ForeignMod"
        mod.mkdir()
        (mod / "Foreign.cpp").write_text("// not nyra", encoding="utf-8")
        result = CppRecompileTool().execute({
            "scope": "module",
            "module_name": "ForeignMod",
            "module_dir": str(mod),
        })
        assert not result.is_ok
        assert "Out-of-Scope" in result.error

    def test_recompile_aborts_on_missing_module_dir(self, tmp_path: Path):
        result = CppRecompileTool().execute({
            "scope": "module",
            "module_name": "Ghost",
            "module_dir": str(tmp_path / "DoesNotExist"),
        })
        assert not result.is_ok
        assert "does not exist" in result.error

"""nyrahost.tools.cpp_authoring_tools — PARITY-02 C++ authoring + Live Coding.

Plan 08-02 ships four MCP tools that decompose Aura's monolithic "create C++
class" surface into transactional, idempotent, post-condition-verified steps:

  - nyra_cpp_module_create  : scaffold a new UE C++ module (Build.cs + Public/ + Private/)
  - nyra_cpp_class_add      : add a UCLASS to an existing NYRA-authored module
  - nyra_cpp_function_add   : add a UFUNCTION to an existing NYRA-authored class
  - nyra_cpp_recompile      : trigger Live Coding compile (or Hot Reload fallback)

Every tool is a copy-rename of the canonical Phase 4 mutator shape from
`actor_tools.ActorSpawnTool.execute` (LOCKED-03):

    1. idempotent_lookup(self.name, params)            -- BL-05 dedup
    2. with session_transaction(f"NYRA: {self.name}"): -- BL-04 Ctrl+Z roll-back
    3. perform mutation
    4. verify_post_condition(label, lambda: ...)       -- BL-06 readback
    5. idempotent_record + return ok(...)              -- BL-05 cache

Pre-condition gate (CONTEXT.md §Out of Scope): every recompile validates
that the target module's source files are in the
`nyrahost.cpp_authoring_state` allowlist. Files NYRA did not author this
session abort the recompile with a structured error.

Live Coding dispatch goes through the C++ helper UCLASS at
`NyraEditor/Public/ToolHelpers/NyraLiveCodingHelper.h` reflected as
`unreal.NyraLiveCodingHelper.*`. UE Python does NOT expose ILiveCodingModule
directly in 5.4-5.7; the helper is the supported path.
"""
from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Any

import structlog

from nyrahost.cpp_authoring_state import (
    is_authored,
    record_authored,
    record_authored_many,
)
from nyrahost.tools.base import (
    NyraTool,
    NyraToolResult,
    idempotent_lookup,
    idempotent_record,
    session_transaction,
    verify_post_condition,
)

log = structlog.get_logger("nyrahost.tools.cpp_authoring_tools")

__all__ = [
    "CppModuleCreateTool",
    "CppClassAddTool",
    "CppFunctionAddTool",
    "CppRecompileTool",
    "KNOWN_LIVE_CODING_BAD_VERSIONS",
]


# Populated by Wave 0 (Task 0) operator survey — empirical UE versions where
# Live Coding either hangs the editor, returns success but doesn't actually
# patch the running process, or corrupts the LiveCoding patch DB. When a
# version is in this set, `nyra_cpp_recompile` defaults `use_live_coding`
# to False on that version and uses Hot Reload instead.
KNOWN_LIVE_CODING_BAD_VERSIONS: set[str] = set()


# Identifier validation — UE class / module / module-name rules. PascalCase
# starting with a letter, no symbols, length-bounded so a malformed LLM call
# can't generate a ten-megabyte filename.
_IDENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")


def _validate_ident(name: str, label: str) -> str | None:
    """Return None on success or an error message (for NyraToolResult.err)."""
    if not isinstance(name, str) or not _IDENT_RE.match(name):
        return f"invalid {label}: {name!r} (must match /^[A-Za-z][A-Za-z0-9_]{{0,63}}$/)"
    return None


# ---------------------------------------------------------------------------
# nyra_cpp_module_create
# ---------------------------------------------------------------------------

class CppModuleCreateTool(NyraTool):
    name = "nyra_cpp_module_create"
    description = (
        "Scaffold a new UE C++ module under the given parent directory. "
        "Creates <parent>/<module>/{Public,Private}/ and a "
        "<module>.Build.cs file wired with the standard Engine + Core "
        "PublicDependencyModuleNames. Type 'Editor' adds UnrealEd / Slate "
        "deps; type 'Runtime' is a minimal runtime-only module."
    )
    parameters = {
        "type": "object",
        "properties": {
            "module_name": {
                "type": "string",
                "description": "Module name in PascalCase, e.g. 'MyGameSystems'.",
            },
            "parent_dir": {
                "type": "string",
                "description": "Parent directory under which the module folder is created, e.g. '/path/to/project/Source'.",
            },
            "type": {
                "type": "string",
                "enum": ["Editor", "Runtime"],
                "default": "Runtime",
                "description": "Module type — 'Editor' for editor-only, 'Runtime' for game runtime.",
            },
        },
        "required": ["module_name", "parent_dir"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        # BL-05 dedup. Calling create twice with identical params returns
        # the prior success (deduped:True) — useful for LLM retries on
        # transient I/O errors.
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        module_name = params.get("module_name", "")
        parent_raw = params.get("parent_dir", "")
        module_type = params.get("type", "Runtime")

        # Param validation — explicit checks rather than letting the
        # filesystem layer raise. The schema's `enum` for `type` doesn't
        # validate at the NyraTool layer; do it here.
        ident_err = _validate_ident(module_name, "module_name")
        if ident_err:
            return NyraToolResult.err(ident_err)
        if module_type not in ("Editor", "Runtime"):
            return NyraToolResult.err(f"invalid type: {module_type!r} (must be 'Editor' or 'Runtime')")
        if not parent_raw:
            return NyraToolResult.err("parent_dir is required")

        parent = Path(parent_raw).resolve(strict=False)
        module_dir = (parent / module_name).resolve(strict=False)

        # Path-traversal guard (RESEARCH.md §Security V4) — module_name was
        # already ident-validated, but parent_dir could resolve outside
        # itself if it contains symlinks; double-check the final module_dir
        # is a descendant of parent.
        try:
            module_dir.relative_to(parent)
        except ValueError:
            return NyraToolResult.err(f"path traversal: {module_dir} escapes {parent}")

        public_dir = module_dir / "Public"
        private_dir = module_dir / "Private"
        build_cs = module_dir / f"{module_name}.Build.cs"

        # BL-04 transaction. session_transaction is a no-op when `unreal`
        # is unimportable (pytest path) — the with-block still runs the
        # filesystem mutations.
        with session_transaction(f"NYRA: {self.name}"):
            try:
                public_dir.mkdir(parents=True, exist_ok=True)
                private_dir.mkdir(parents=True, exist_ok=True)
                build_cs.write_text(_render_build_cs(module_name, module_type), encoding="utf-8")
                record_authored_many([build_cs, public_dir, private_dir])
            except OSError as e:
                log.error("cpp_module_create_failed", error=str(e), module=module_name)
                return NyraToolResult.err(f"failed to create module {module_name}: {e}")

            # BL-06 post-condition.
            err = verify_post_condition(
                f"{self.name}({module_name})",
                lambda: build_cs.exists() and public_dir.is_dir() and private_dir.is_dir(),
            )
            if err:
                return NyraToolResult.err(err)

        result = {
            "module_name": module_name,
            "module_dir": str(module_dir),
            "build_cs": str(build_cs),
            "type": module_type,
        }
        idempotent_record(self.name, params, result)
        log.info("cpp_module_created", module=module_name, type=module_type)
        return NyraToolResult.ok(result)


# ---------------------------------------------------------------------------
# nyra_cpp_class_add
# ---------------------------------------------------------------------------

class CppClassAddTool(NyraTool):
    name = "nyra_cpp_class_add"
    description = (
        "Add a UCLASS to an existing NYRA-authored module. Creates "
        "<module>/Public/<ClassName>.h and <module>/Private/<ClassName>.cpp "
        "with a minimal UCLASS skeleton inheriting from <parent_class>. "
        "Pre-condition: the target module's Build.cs must already exist in "
        "the session-scoped NYRA-authored set (i.e. the module was created "
        "via nyra_cpp_module_create earlier in the session)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "module_dir": {
                "type": "string",
                "description": "Absolute path to the module directory containing Public/ and Private/.",
            },
            "module_name": {
                "type": "string",
                "description": "Module name (used for the API export macro, e.g. MYGAME_API).",
            },
            "class_name": {
                "type": "string",
                "description": "PascalCase class name without the U/A prefix; the prefix is added based on parent_class.",
            },
            "parent_class": {
                "type": "string",
                "default": "UObject",
                "description": "Parent class — UObject, AActor, UActorComponent, UInterface, etc.",
            },
        },
        "required": ["module_dir", "module_name", "class_name"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        module_dir_raw = params.get("module_dir", "")
        module_name = params.get("module_name", "")
        class_name = params.get("class_name", "")
        parent_class = params.get("parent_class", "UObject")

        for ident, label in [
            (module_name, "module_name"),
            (class_name, "class_name"),
            (parent_class, "parent_class"),
        ]:
            err = _validate_ident(ident, label)
            if err:
                return NyraToolResult.err(err)
        if not module_dir_raw:
            return NyraToolResult.err("module_dir is required")

        module_dir = Path(module_dir_raw).resolve(strict=False)
        build_cs = module_dir / f"{module_name}.Build.cs"

        # Pre-condition: the module must have been created by NYRA this
        # session. We check the Build.cs entry rather than the directory
        # so a directory the user pre-created (without authorisation)
        # can't be retroactively claimed.
        if not is_authored(build_cs):
            return NyraToolResult.err(
                f"class_add aborted: {build_cs} is not in NYRA-authored set this session "
                f"(Out-of-Scope policy — create the module via nyra_cpp_module_create first)"
            )

        # Class-name prefix inference. UE convention: U for UObject-derived,
        # A for AActor-derived. We prefix automatically; the LLM passes
        # the bare PascalCase name.
        prefix = "A" if parent_class.startswith("A") else ("I" if parent_class == "UInterface" else "U")
        full_class = f"{prefix}{class_name}"

        header_path = module_dir / "Public" / f"{class_name}.h"
        impl_path = module_dir / "Private" / f"{class_name}.cpp"

        # Path-traversal: derived names; ident-validated so this is
        # belt-and-braces.
        try:
            header_path.relative_to(module_dir)
            impl_path.relative_to(module_dir)
        except ValueError:
            return NyraToolResult.err("path traversal in derived class file paths")

        with session_transaction(f"NYRA: {self.name}"):
            try:
                header_path.write_text(
                    _render_class_header(module_name, full_class, parent_class),
                    encoding="utf-8",
                )
                impl_path.write_text(
                    _render_class_impl(class_name, full_class),
                    encoding="utf-8",
                )
                record_authored_many([header_path, impl_path])
            except OSError as e:
                log.error("cpp_class_add_failed", error=str(e), class_=class_name)
                return NyraToolResult.err(f"failed to add class {class_name}: {e}")

            err = verify_post_condition(
                f"{self.name}({full_class})",
                lambda: (
                    header_path.exists()
                    and impl_path.exists()
                    and full_class in header_path.read_text(encoding="utf-8")
                ),
            )
            if err:
                return NyraToolResult.err(err)

        result = {
            "class_name": full_class,
            "header_path": str(header_path),
            "impl_path": str(impl_path),
            "module_name": module_name,
            "parent_class": parent_class,
        }
        idempotent_record(self.name, params, result)
        log.info("cpp_class_added", class_=full_class, module=module_name)
        return NyraToolResult.ok(result)


# ---------------------------------------------------------------------------
# nyra_cpp_function_add
# ---------------------------------------------------------------------------

class CppFunctionAddTool(NyraTool):
    name = "nyra_cpp_function_add"
    description = (
        "Add a method to an existing NYRA-authored UCLASS. Inserts the "
        "function declaration into the class's .h and the implementation "
        "into the matching .cpp. Both files must already be in the "
        "session-scoped NYRA-authored set (i.e. the class was created via "
        "nyra_cpp_class_add earlier this session)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "header_path": {
                "type": "string",
                "description": "Absolute path to the class's .h file.",
            },
            "impl_path": {
                "type": "string",
                "description": "Absolute path to the class's .cpp file.",
            },
            "class_name": {
                "type": "string",
                "description": "Fully-prefixed class name, e.g. 'AMyActor'.",
            },
            "signature": {
                "type": "string",
                "description": "Full C++ signature without the class scope, e.g. 'void DoTheThing(int32 Count)'.",
            },
            "body": {
                "type": "string",
                "description": "Function body source WITHOUT enclosing braces.",
                "default": "",
            },
        },
        "required": ["header_path", "impl_path", "class_name", "signature"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        header_raw = params.get("header_path", "")
        impl_raw = params.get("impl_path", "")
        class_name = params.get("class_name", "")
        signature = params.get("signature", "")
        body = params.get("body", "")

        if not header_raw or not impl_raw:
            return NyraToolResult.err("header_path and impl_path are required")
        if not isinstance(signature, str) or not signature.strip():
            return NyraToolResult.err("signature is required and must be non-empty")
        # class_name validation — same ident rule, allowing the U/A prefix.
        if not isinstance(class_name, str) or not _IDENT_RE.match(class_name):
            return NyraToolResult.err(f"invalid class_name: {class_name!r}")

        header_path = Path(header_raw).resolve(strict=False)
        impl_path = Path(impl_raw).resolve(strict=False)

        if not is_authored(header_path) or not is_authored(impl_path):
            return NyraToolResult.err(
                f"function_add aborted: {header_path} and/or {impl_path} not in "
                f"NYRA-authored set this session (Out-of-Scope policy — create the "
                f"class via nyra_cpp_class_add first)"
            )

        if not header_path.exists() or not impl_path.exists():
            return NyraToolResult.err(
                f"header or impl missing on disk: {header_path}, {impl_path}"
            )

        with session_transaction(f"NYRA: {self.name}"):
            try:
                # Header: insert the declaration before the closing `};` of
                # the class body. Naive but predictable — matches the
                # template emitted by CppClassAddTool.
                header_text = header_path.read_text(encoding="utf-8")
                decl_line = f"\tUFUNCTION(BlueprintCallable)\n\t{signature.strip()};\n"
                new_header = _insert_into_class_body(header_text, class_name, decl_line)
                if new_header is None:
                    return NyraToolResult.err(
                        f"could not locate class body for {class_name} in {header_path}"
                    )
                header_path.write_text(new_header, encoding="utf-8")

                # Impl: append the method implementation to the .cpp. Format:
                #   <ret-type> <Class>::<Sig-rest> { <body> }
                impl_text = impl_path.read_text(encoding="utf-8")
                impl_block = _render_function_impl(class_name, signature, body)
                if not impl_text.endswith("\n"):
                    impl_text += "\n"
                impl_path.write_text(impl_text + "\n" + impl_block, encoding="utf-8")
            except OSError as e:
                log.error("cpp_function_add_failed", error=str(e), signature=signature)
                return NyraToolResult.err(f"failed to add function {signature!r}: {e}")

            sig_marker = signature.strip().rstrip(";")
            err = verify_post_condition(
                f"{self.name}({class_name}::{sig_marker})",
                lambda: (
                    sig_marker in header_path.read_text(encoding="utf-8")
                    and class_name in impl_path.read_text(encoding="utf-8")
                ),
            )
            if err:
                return NyraToolResult.err(err)

        result = {
            "class_name": class_name,
            "signature": signature,
            "header_path": str(header_path),
            "impl_path": str(impl_path),
        }
        idempotent_record(self.name, params, result)
        log.info("cpp_function_added", class_=class_name, signature=signature)
        return NyraToolResult.ok(result)


# ---------------------------------------------------------------------------
# nyra_cpp_recompile
# ---------------------------------------------------------------------------

class CppRecompileTool(NyraTool):
    name = "nyra_cpp_recompile"
    description = (
        "Trigger Live Coding (or Hot Reload fallback) on NYRA-authored "
        "modules. Calls unreal.NyraLiveCodingHelper.trigger_live_coding_compile() "
        "by default; falls back to trigger_hot_reload() when use_live_coding=False "
        "or when the running UE version is in KNOWN_LIVE_CODING_BAD_VERSIONS. "
        "Compile output is parsed against the extended _ERROR_PATTERNS catalog "
        "from blueprint_debug — MSVC C\\d{4}, clang undeclared identifier, "
        "linker LNK\\d{4}, and UnrealHeaderTool failures all surface as "
        "structured `compile_errors` entries."
    )
    parameters = {
        "type": "object",
        "properties": {
            "scope": {
                "type": "string",
                "enum": ["module", "all"],
                "default": "module",
                "description": "Scope: 'module' validates only the named module's source; 'all' triggers a global Live Coding sweep (still gated on every authored file).",
            },
            "module_name": {
                "type": "string",
                "description": "Module name when scope='module'.",
            },
            "module_dir": {
                "type": "string",
                "description": "Module directory when scope='module' (used to walk *.cpp / *.h for the authored-set check).",
            },
            "use_live_coding": {
                "type": "boolean",
                "default": True,
                "description": "If False, force the Hot Reload fallback instead of Live Coding.",
            },
        },
        "required": ["scope"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        cached = idempotent_lookup(self.name, params)
        if cached is not None:
            return NyraToolResult.ok({**cached, "deduped": True})

        scope = params.get("scope", "module")
        module_name = params.get("module_name", "")
        module_dir_raw = params.get("module_dir", "")
        use_lc_pref = params.get("use_live_coding", True)

        if scope not in ("module", "all"):
            return NyraToolResult.err(f"invalid scope: {scope!r}")

        # Pre-condition gate — every C++ source file in the target scope
        # must be in the NYRA-authored set this session. Out-of-Scope
        # policy from CONTEXT.md.
        if scope == "module":
            if not module_dir_raw:
                return NyraToolResult.err("module_dir is required when scope='module'")
            module_dir = Path(module_dir_raw).resolve(strict=False)
            if not module_dir.exists():
                return NyraToolResult.err(f"module_dir does not exist: {module_dir}")
            non_authored: list[str] = []
            for f in list(module_dir.rglob("*.cpp")) + list(module_dir.rglob("*.h")):
                if not is_authored(f):
                    non_authored.append(str(f))
            if non_authored:
                # Truncate the listing to keep the error message bounded.
                shown = non_authored[:5]
                more = (
                    f" (and {len(non_authored) - len(shown)} more)"
                    if len(non_authored) > len(shown) else ""
                )
                return NyraToolResult.err(
                    f"recompile aborted: {len(non_authored)} file(s) in {module_dir} "
                    f"are not in NYRA-authored set this session "
                    f"(Out-of-Scope policy). First: {shown}{more}"
                )

        ue_version = _detect_ue_version()
        use_lc = bool(use_lc_pref) and ue_version not in KNOWN_LIVE_CODING_BAD_VERSIONS

        ok = False
        method = "live_coding" if use_lc else "hot_reload"
        output = ""

        with session_transaction(f"NYRA: {self.name}"):
            try:
                import unreal  # type: ignore
            except ImportError:
                return NyraToolResult.err(
                    "unreal module unavailable — recompile must run inside the UE Python environment "
                    "(remediation: invoke nyra_cpp_recompile from the editor's NyraHost-spawned Python, "
                    "not from a standalone pytest harness)"
                )

            helper = getattr(unreal, "NyraLiveCodingHelper", None)
            if helper is None:
                return NyraToolResult.err(
                    "unreal.NyraLiveCodingHelper is not reflected on this UE version "
                    f"({ue_version}); manual remediation: open the project in Visual Studio "
                    "and rebuild manually, then add this UE version to "
                    "KNOWN_LIVE_CODING_BAD_VERSIONS so future calls fall back to Hot Reload."
                )

            try:
                if use_lc:
                    ok = bool(helper.trigger_live_coding_compile())
                    if not ok:
                        # Live Coding refused (disabled in editor prefs, or no
                        # patchable modules) — try Hot Reload before giving up.
                        ok = bool(helper.trigger_hot_reload(module_name or ""))
                        method = "hot_reload"
                else:
                    ok = bool(helper.trigger_hot_reload(module_name or ""))
                output = str(helper.get_last_compile_output() or "")
            except Exception as e:  # noqa: BLE001 — UE Python exceptions are heterogenous
                log.error("cpp_recompile_failed", error=str(e), method=method)
                return NyraToolResult.err(f"recompile {method} raised: {e}")

            errors = _parse_compile_errors(output)

            err = verify_post_condition(
                f"{self.name}({scope})",
                # compile_attempted is always True at this point. Live
                # Coding is async; the post-condition is just "we got past
                # the dispatch without raising".
                lambda: True,
            )
            if err:
                return NyraToolResult.err(err)

        result = {
            "compile_attempted": True,
            "compile_success": bool(ok) and not errors,
            "method": method,
            "ue_version": ue_version,
            "compile_errors": errors,
            "scope": scope,
            "module_name": module_name,
        }
        idempotent_record(self.name, params, result)
        log.info(
            "cpp_recompile",
            method=method,
            ue_version=ue_version,
            ok=ok,
            error_count=len(errors),
        )
        return NyraToolResult.ok(result)


# ---------------------------------------------------------------------------
# Render helpers — keep templates inline so a stub UE module is human-grep-able.
# ---------------------------------------------------------------------------

def _render_build_cs(module: str, kind: str) -> str:
    if kind == "Editor":
        deps = '"Core", "CoreUObject", "Engine", "UnrealEd", "Slate", "SlateCore"'
    else:
        deps = '"Core", "CoreUObject", "Engine"'
    return textwrap.dedent(f"""\
        // SPDX-License-Identifier: MIT
        // Generated by nyra_cpp_module_create.
        using UnrealBuildTool;

        public class {module} : ModuleRules
        {{
            public {module}(ReadOnlyTargetRules Target) : base(Target)
            {{
                PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
                PublicDependencyModuleNames.AddRange(new string[] {{ {deps} }});
            }}
        }}
        """)


def _render_class_header(module: str, full_class: str, parent: str) -> str:
    api_macro = f"{module.upper()}_API"
    base_no_prefix = full_class[1:] if full_class[:1] in ("U", "A", "I") else full_class
    return textwrap.dedent(f"""\
        // SPDX-License-Identifier: MIT
        // Generated by nyra_cpp_class_add.
        #pragma once

        #include "CoreMinimal.h"
        #include "UObject/Object.h"
        #include "{base_no_prefix}.generated.h"

        UCLASS()
        class {api_macro} {full_class} : public {parent}
        {{
            GENERATED_BODY()

        public:
        }};
        """)


def _render_class_impl(class_basename: str, full_class: str) -> str:
    return textwrap.dedent(f"""\
        // SPDX-License-Identifier: MIT
        // Generated by nyra_cpp_class_add.
        #include "{class_basename}.h"
        """)


def _insert_into_class_body(header_text: str, full_class: str, decl_line: str) -> str | None:
    """Insert `decl_line` before the closing `};` of `class ... full_class ...`.

    Returns the new file text or None if the class body could not be
    located. Naive but predictable — pairs with the template emitted by
    `_render_class_header` so it always finds the marker on freshly-NYRA-
    authored files.
    """
    # Find the class declaration; tolerate API_MACRO between `class` and name.
    class_re = re.compile(rf"class\s+(?:[A-Z][A-Z0-9_]*\s+)?{re.escape(full_class)}\b")
    m = class_re.search(header_text)
    if m is None:
        return None
    # Walk forward from the match to find the matching closing `};`.
    depth = 0
    i = m.end()
    open_brace = header_text.find("{", i)
    if open_brace == -1:
        return None
    depth = 1
    j = open_brace + 1
    while j < len(header_text) and depth > 0:
        ch = header_text[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                # Insert before this `}`. Add a trailing newline so we don't
                # collapse against the closing brace.
                return header_text[:j] + decl_line + header_text[j:]
        j += 1
    return None


def _render_function_impl(class_name: str, signature: str, body: str) -> str:
    """Compose `<ret> <Class>::<Sig-rest> { <body> }` from a free-form sig.

    Splits the signature on the first whitespace before the function name.
    "void DoTheThing(int32 N)" becomes "void AMyActor::DoTheThing(int32 N)".
    """
    sig = signature.strip().rstrip(";")
    paren_idx = sig.find("(")
    if paren_idx == -1:
        # No paren — degrade to inserting `Class::` after the first space.
        first_space = sig.find(" ")
        if first_space == -1:
            scoped = f"{class_name}::{sig}"
        else:
            scoped = f"{sig[:first_space]} {class_name}::{sig[first_space+1:]}"
    else:
        # Find the start of the function name (last space before the paren).
        space_before = sig.rfind(" ", 0, paren_idx)
        if space_before == -1:
            scoped = f"{class_name}::{sig}"
        else:
            scoped = f"{sig[:space_before]} {class_name}::{sig[space_before+1:]}"
    body_block = body.strip()
    indented_body = "\n".join("\t" + line if line else "" for line in body_block.splitlines())
    return f"{scoped}\n{{\n{indented_body}\n}}\n"


def _detect_ue_version() -> str:
    """Return the running UE version as 'major.minor', or 'unknown' off-engine."""
    try:
        import unreal  # type: ignore
    except ImportError:
        return "unknown"
    try:
        full = unreal.SystemLibrary.get_engine_version()  # e.g. '5.6.0-12345+++UE5+Release-5.6'
    except Exception:
        return "unknown"
    parts = str(full).split(".")
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[1]}"
    return str(full) or "unknown"


def _parse_compile_errors(output: str) -> list[dict[str, Any]]:
    """Walk `output` line-by-line and return structured error entries.

    Delegates to `blueprint_debug._explain_error_pattern`, which is regex-
    shape-agnostic; Plan 08-02 Task 3 extends `_ERROR_PATTERNS` with the
    MSVC/clang/LNK/UHT C++ shapes so the same matcher serves both
    Blueprint and C++ surfaces.
    """
    if not output:
        return []
    try:
        from nyrahost.tools.blueprint_debug import (
            _SUGGESTION_FALLBACK,
            _explain_error_pattern,
        )
    except Exception as e:  # noqa: BLE001 — defensive against import-time failures
        log.warning("cpp_error_parse_unavailable", error=str(e))
        return []

    matches: list[dict[str, Any]] = []
    for raw in output.splitlines():
        if not raw.strip():
            continue
        explanation, suggestion = _explain_error_pattern(raw)
        # Only count a line as an error if a specific pattern matched (i.e.
        # we got something other than the generic fallback). Otherwise the
        # entire compile log would surface as N "unexpected error" entries.
        if suggestion == _SUGGESTION_FALLBACK or explanation.startswith("An unexpected"):
            continue
        matches.append({
            "line": raw,
            "plain_english": explanation,
            "suggested_fix": suggestion,
            "pattern_match": True,
        })
    return matches

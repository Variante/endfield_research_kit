#!/usr/bin/env python3
"""Generate Endfield IL2CPP DummyDll assemblies for AnimeStudio.

The script discovers the build-specific IL2CPP registration addresses, prepares
the pinned Cpp2IL-Endfield release, generates assemblies into a staging folder,
validates the complete metadata image set, and atomically publishes tools/DummyDll.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if __package__ == "scripts.animestudio":
    from ..common import resolve_installed_game_data_root, sha256_file
else:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.common import resolve_installed_game_data_root, sha256_file
DEFAULT_CPP2IL_SOURCE = ROOT / "tools" / "Cpp2IL-Endfield"
DEFAULT_OUTPUT = ROOT / "tools" / "DummyDll"
DEFAULT_ANIMESTUDIO = (
    ROOT
    / "tools"
    / "AnimeStudio"
    / "AnimeStudio.CLI"
    / "bin"
    / "Release"
    / "net9.0-windows"
    / "AnimeStudio.CLI.exe"
)
CPP2IL_REPOSITORY = "https://github.com/Variante/Cpp2IL-Endfield.git"
CPP2IL_TAG = "endfield-2022.0.7-v4"
CPP2IL_COMMIT = "8e53b485b3ae4fac71a533ee47681e831c14658b"
IL2CPP_HELPER = ROOT / "tools" / "endfield-il2cpp" / "map_body_targets_to_gameassembly.py"
METADATA_HELPER = ROOT / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
REQUIRED_ASSEMBLIES = {
    "Assembly-CSharp.dll",
    "Gameplay.Beyond.dll",
    "UnityEngine.CoreModule.dll",
}
MIN_PREVIOUS_BYTE_RATIO = 0.5


def fail(message: str) -> "NoReturn":
    raise SystemExit(message)


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        fail(f"Unable to load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module




def parse_int(value: str) -> int:
    return int(value, 0)


def configured_game_root() -> Path:
    """Resolve the installed Endfield_Data root shared by every builder."""
    return resolve_installed_game_data_root()


def resolve_game_paths(game_root: Path) -> tuple[Path, Path, Path, str]:
    candidate = game_root.expanduser().resolve()
    if candidate.name.casefold().endswith("_data"):
        data_root = candidate
        install_root = candidate.parent
        exe_name = candidate.name[:-5]
    else:
        install_root = candidate
        data_roots = sorted(path for path in install_root.glob("*_Data") if path.is_dir())
        if len(data_roots) != 1:
            fail(
                f"Expected one *_Data directory under {install_root}; found {len(data_roots)}. "
                "Pass --game-root with the installed Endfield_Data directory."
            )
        data_root = data_roots[0]
        exe_name = data_root.name[:-5]
    gameassembly = install_root / "GameAssembly.dll"
    metadata = data_root / "il2cpp_data" / "Metadata" / "global-metadata.dat"
    executable = install_root / f"{exe_name}.exe"
    for label, path in (
        ("game executable", executable),
        ("GameAssembly", gameassembly),
        ("global metadata", metadata),
    ):
        if not path.is_file():
            fail(f"Missing {label}: {path}")
    return install_root, gameassembly, metadata, exe_name


def run_command(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    check: bool = True,
    show: bool = True,
) -> subprocess.CompletedProcess[str]:
    if show:
        print(f"> {' '.join(argv)}")
    result = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        errors="replace",
        check=False,
    )
    if show and result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if check and result.returncode:
        fail(f"Command failed with exit code {result.returncode}: {' '.join(argv)}")
    return result


def canonical_git_remote(value: str) -> str:
    return value.strip().rstrip("/").removesuffix(".git").casefold()


def cpp2il_tracked_changes(source: Path) -> str:
    return run_command(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=source,
        show=False,
    ).stdout.strip()


def prepare_cpp2il(source: Path, *, dry_run: bool) -> bool:
    """Clone or safely advance a clean checkout to the immutable source pin."""

    if not source.exists():
        if dry_run:
            print(f"Would clone Cpp2IL {CPP2IL_TAG} into {source}")
            return False
        source.parent.mkdir(parents=True, exist_ok=True)
        run_command(
            [
                "git", "clone", "--depth", "1", "--branch", CPP2IL_TAG,
                CPP2IL_REPOSITORY, str(source),
            ],
            cwd=ROOT,
        )
    if not (source / ".git").exists():
        fail(f"Cpp2IL source is not a Git checkout: {source}")
    current = cpp2il_source_commit(source)
    if current == CPP2IL_COMMIT:
        return True
    changes = cpp2il_tracked_changes(source)
    if changes:
        fail(
            "Refusing to update a Cpp2IL-Endfield checkout with tracked local "
            f"changes: {source}"
        )
    origin = run_command(
        ["git", "remote", "get-url", "origin"], cwd=source, show=False
    ).stdout.strip()
    if canonical_git_remote(origin) != canonical_git_remote(CPP2IL_REPOSITORY):
        fail(
            f"Cpp2IL-Endfield origin is {origin!r}, expected {CPP2IL_REPOSITORY!r}."
        )
    if dry_run:
        print(
            f"Would update clean Cpp2IL-Endfield checkout from {current} to "
            f"{CPP2IL_COMMIT} ({CPP2IL_TAG})"
        )
        return False
    run_command(
        ["git", "fetch", "--depth", "1", "origin", "tag", CPP2IL_TAG],
        cwd=source,
    )
    tag_commit = run_command(
        ["git", "rev-parse", f"refs/tags/{CPP2IL_TAG}^{{}}"],
        cwd=source,
        show=False,
    ).stdout.strip().casefold()
    if tag_commit != CPP2IL_COMMIT:
        fail(
            f"Cpp2IL-Endfield tag {CPP2IL_TAG} resolves to {tag_commit}, "
            f"expected {CPP2IL_COMMIT}."
        )
    run_command(["git", "checkout", "--detach", CPP2IL_COMMIT], cwd=source)
    return True


def cpp2il_source_commit(source: Path) -> str:
    return run_command(
        ["git", "rev-parse", "HEAD"], cwd=source, show=False
    ).stdout.strip().casefold()


def validate_cpp2il_source(source: Path) -> None:
    commit = cpp2il_source_commit(source)
    if commit != CPP2IL_COMMIT:
        fail(
            f"Cpp2IL-Endfield source is at {commit}, expected pinned commit "
            f"{CPP2IL_COMMIT} ({CPP2IL_TAG})."
        )
    changes = cpp2il_tracked_changes(source)
    if changes:
        fail(f"Cpp2IL-Endfield source has tracked local changes: {source}")
    markers = {
        source / "LibCpp2IL" / "Il2CppBinary.cs": "CPP2IL_METADATA_REGISTRATION",
        source / "LibCpp2IL" / "Metadata" / "Il2CppTypeDefinition.cs": "endfieldUnknownIndex",
        source / "Cpp2IL.Core" / "StubAssemblyBuilder.cs": "TryAddType",
        source / "Cpp2IL.Core" / "AssemblyPopulator.cs": "Skipping malformed image",
        source / "Cpp2IL.Core" / "AssemblyPopulator.cs": "Skipping malformed field default",
        source / "Cpp2IL.Core" / "Cpp2IlApi.cs": "Skipping malformed generic constraint",
        source / "Cpp2IL" / "Program.cs": "if (!runtimeArgs.SuppressAttributes)",
    }
    missing = [str(path) for path, marker in markers.items() if not path.is_file() or marker not in path.read_text(encoding="utf-8-sig")]
    if missing:
        fail("Cpp2IL-Endfield checkout is missing required compatibility markers: " + ", ".join(missing))


def discover_registrations(
    gameassembly: Path,
    metadata: Path,
    code_override: int | None,
    metadata_override: int | None,
) -> tuple[
    int,
    int,
    set[str],
    dict[str, Any],
    dict[tuple[str, int], str],
]:
    il2cpp = load_module("endfield_dummydll_il2cpp", IL2CPP_HELPER)
    catalog = load_module("endfield_dummydll_metadata", METADATA_HELPER)
    print(f"Loading IL2CPP metadata: {metadata}")
    md = catalog.Metadata(metadata)
    image_names = {md.string(image.name_index) for image in md.images}
    if not image_names:
        fail("global-metadata.dat contains no image definitions")
    print(f"Metadata images: {len(image_names)}")

    print(f"Scanning registration structures: {gameassembly}")
    pe = il2cpp.PeImage(gameassembly)
    if code_override is None:
        candidates = il2cpp.find_code_registration_candidates(pe, image_names)
        if len(candidates) != 1:
            rendered = ", ".join(f"0x{value:x}" for value in candidates) or "none"
            fail(
                "CodeRegistration discovery did not produce exactly one complete module-table "
                f"match (candidates: {rendered}). Pass --code-registration only after validating it."
            )
        code_registration = candidates[0]
    else:
        code_registration = code_override
    modules = il2cpp.parse_codegen_modules(pe, code_registration)
    if {name.casefold() for name in modules} != {name.casefold() for name in image_names}:
        fail(
            f"CodeRegistration 0x{code_registration:x} does not match the complete metadata image set."
        )

    metadata_registration = metadata_override or il2cpp.find_metadata_registration(
        pe, code_registration
    )
    if metadata_registration is None or not il2cpp.metadata_registration_is_plausible(
        pe, metadata_registration
    ):
        fail(
            "MetadataRegistration discovery failed its pointer checks. Pass "
            "--metadata-registration only after validating it against this exact GameAssembly."
        )
    summary = {
        "code": il2cpp.code_registration_summary(pe, code_registration),
        "metadata": il2cpp.metadata_registration_summary(pe, metadata_registration),
        "metadataImageCount": len(md.images),
        "metadataTypeCount": len(md.types),
    }
    print(f"CodeRegistration: 0x{code_registration:x}")
    print(f"MetadataRegistration: 0x{metadata_registration:x}")
    expected_identities: dict[tuple[str, int], str] = {}
    for type_def in md.types:
        image_name = md.image_name_by_type_index.get(type_def.index, "")
        if (
            not image_name.casefold().endswith(".dll")
            or md.string(type_def.name_index) == "<Module>"
        ):
            continue
        key = (image_name.casefold(), int(type_def.token))
        if key in expected_identities:
            fail(
                "Metadata contains a duplicate type identity key: "
                f"{image_name} token=0x{type_def.token:08x}"
            )
        expected_identities[key] = md.type_full_name(type_def)
    return (
        code_registration,
        metadata_registration,
        image_names,
        summary,
        expected_identities,
    )


def validate_generated(raw_output: Path, image_names: set[str]) -> list[Path]:
    dlls = sorted(raw_output.glob("*.dll"), key=lambda path: path.name.casefold())
    actual_names = {path.name.casefold() for path in dlls}
    expected_names = {name.casefold() for name in image_names if name.casefold().endswith(".dll")}
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        extra = sorted(actual_names - expected_names)
        fail(
            "Cpp2IL output does not match the metadata DLL image set; "
            f"missing={missing[:12]}, extra={extra[:12]}. Raw output retained at {raw_output}"
        )
    missing_required = sorted(name for name in REQUIRED_ASSEMBLIES if name.casefold() not in actual_names)
    if missing_required:
        fail(f"Cpp2IL output is missing required assemblies: {', '.join(missing_required)}")
    for path in dlls:
        data = path.read_bytes()
        if len(data) < 512 or not data.startswith(b"MZ") or b"BSJB" not in data:
            fail(f"Generated file is not a managed PE assembly: {path}")
    return dlls


def compare_schema_identities(
    expected: dict[tuple[str, int], str], payload: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """Compare indexed managed TypeDefs with exact metadata identities."""

    failures: list[str] = []
    if payload.get("schema") != "animestudio.dummydll-index.v1":
        failures.append(f"unexpected index schema {payload.get('schema')!r}")
    if not payload.get("complete"):
        failures.append("AnimeStudio reported an incomplete DummyDll index")
    if payload.get("errors"):
        failures.append(f"AnimeStudio reported {len(payload['errors'])} assembly errors")
    invalid_count = int(payload.get("invalidTypeCount") or 0)
    if invalid_count:
        failures.append(f"{invalid_count} indexed types have invalid FullName values")

    actual: dict[tuple[str, int], str] = {}
    duplicate_keys: list[tuple[str, int]] = []
    for assembly in payload.get("assemblies") or []:
        module = str(assembly.get("module") or "").casefold()
        for type_row in assembly.get("types") or []:
            key = (module, parse_int(str(type_row["token"])))
            if key in actual:
                duplicate_keys.append(key)
            actual[key] = str(type_row["fullName"])
    if duplicate_keys:
        failures.append(f"{len(duplicate_keys)} duplicate assembly/token keys in index")

    expected_keys = set(expected)
    actual_keys = set(actual)
    missing = sorted(expected_keys - actual_keys)
    extra = sorted(actual_keys - expected_keys)
    mismatched = sorted(
        key for key in expected_keys & actual_keys if expected[key] != actual[key]
    )
    if missing:
        failures.append(f"{len(missing)} metadata type identities are missing")
    if extra:
        failures.append(f"{len(extra)} indexed type identities are unexpected")
    if mismatched:
        samples = "; ".join(
            f"{key[0]} 0x{key[1]:08x}: expected {expected[key]!r}, got {actual[key]!r}"
            for key in mismatched[:5]
        )
        failures.append(f"{len(mismatched)} FullName values mismatch ({samples})")
    summary = {
        "status": "failed" if failures else "passed",
        "schema": payload.get("schema"),
        "expectedTypeCount": len(expected),
        "indexedTypeCount": len(actual),
        "exactIdentityCount": len(expected_keys & actual_keys) - len(mismatched),
        "invalidFullNameCount": invalid_count,
        "missingIdentityCount": len(missing),
        "unexpectedIdentityCount": len(extra),
        "mismatchedFullNameCount": len(mismatched),
        "failureSamples": failures[:10],
    }
    return summary, failures


def validate_schema_identities(
    animestudio: Path,
    raw_output: Path,
    work_dir: Path,
    expected: dict[tuple[str, int], str],
) -> dict[str, Any]:
    if not animestudio.is_file():
        fail(
            "AnimeStudio CLI is required for the DummyDll semantic publication gate: "
            f"{animestudio}. Build it with the AnimeStudio workflow first."
        )
    index_path = work_dir / "dummydll-index.json"
    run_command(
        [
            str(animestudio),
            "dummydll-index",
            "--input",
            str(raw_output),
            "--output",
            str(index_path),
        ],
        cwd=ROOT,
    )
    payload = json.loads(index_path.read_text(encoding="utf-8-sig"))
    summary, failures = compare_schema_identities(expected, payload)
    if failures:
        fail(
            "DummyDll semantic identity gate failed: "
            + "; ".join(failures)
            + f". Raw output and index retained at {work_dir}."
        )
    return summary


def current_output_status(
    output: Path, gameassembly: Path, metadata: Path
) -> tuple[str, str]:
    """Validate the published manifest and every recorded assembly."""

    if not output.exists():
        return "missing", f"output directory is missing: {output}"
    manifest_path = output / "generation.json"
    if not manifest_path.is_file():
        return "unverified", "generation.json is missing"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if manifest.get("schema") != 1:
            return "invalid", f"unsupported manifest schema {manifest.get('schema')!r}"
        recorded_game = manifest["game"]
        stale_inputs = []
        if recorded_game["gameAssemblySha256"] != sha256_file(gameassembly):
            stale_inputs.append("GameAssembly.dll")
        if recorded_game["metadataSha256"] != sha256_file(metadata):
            stale_inputs.append("global-metadata.dat")
        recorded_cpp2il = manifest.get("cpp2il") or {}
        if recorded_cpp2il.get("repository") != CPP2IL_REPOSITORY:
            stale_inputs.append("Cpp2IL-Endfield repository")
        if recorded_cpp2il.get("tag") != CPP2IL_TAG:
            stale_inputs.append("Cpp2IL-Endfield release")
        if str(recorded_cpp2il.get("commit") or "").casefold() != CPP2IL_COMMIT:
            stale_inputs.append("Cpp2IL-Endfield commit")
        if manifest.get("generatorSha256") != sha256_file(Path(__file__)):
            stale_inputs.append("generator")
        if stale_inputs:
            return "stale", "changed inputs: " + ", ".join(stale_inputs)

        assemblies = manifest["assemblies"]
        rows = assemblies["files"]
        if not isinstance(rows, list):
            return "invalid", "assemblies.files is not a list"
        names = [str(row["name"]) for row in rows]
        folded_names = [name.casefold() for name in names]
        if len(set(folded_names)) != len(folded_names):
            return "invalid", "manifest contains duplicate assembly names"
        disk = sorted(output.glob("*.dll"), key=lambda path: path.name.casefold())
        if {path.name.casefold() for path in disk} != set(folded_names):
            return "invalid", "published DLL names differ from generation.json"
        if assemblies["count"] != len(rows) or assemblies["count"] != len(disk):
            return "invalid", "assembly count does not match manifest and disk"
        by_name = {path.name.casefold(): path for path in disk}
        total_bytes = 0
        for row in rows:
            path = by_name[str(row["name"]).casefold()]
            size = path.stat().st_size
            total_bytes += size
            if row["bytes"] != size:
                return "invalid", f"assembly size mismatch: {path.name}"
            if str(row["sha256"]).casefold() != sha256_file(path).casefold():
                return "invalid", f"assembly hash mismatch: {path.name}"
        if assemblies["bytes"] != total_bytes:
            return "invalid", "assembly byte total does not match manifest"
        schema_validation = manifest.get("schemaIdentityValidation") or {}
        if schema_validation.get("status") != "passed":
            return "invalid", "semantic type identity validation is missing or failed"
        if schema_validation.get("exactIdentityCount") != schema_validation.get(
            "expectedTypeCount"
        ):
            return "invalid", "semantic type identity coverage is incomplete"
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return "invalid", f"generation manifest validation failed: {exc}"
    gaps = manifest.get("cpp2il") or {}
    skipped_images = {
        str(name).casefold() for name in gaps.get("skippedMalformedImages") or []
    }
    skipped_required = sorted(
        name for name in REQUIRED_ASSEMBLIES if name.casefold() in skipped_images
    )
    skipped_types = int(gaps.get("skippedMalformedTypeCount") or 0)
    detail = (
        f"{len(rows)} assemblies; coverage gaps: "
        f"{int(gaps.get('skippedMalformedImageCount') or 0)} images, "
        f"{int(gaps.get('skippedMalformedTypeCount') or 0)} types"
    )
    if skipped_required:
        return "degraded", detail + "; required images skipped: " + ", ".join(skipped_required)
    if skipped_types:
        return "degraded", detail + "; type population is incomplete"
    return "current", detail


def report_current_output_status(
    output: Path, gameassembly: Path, metadata: Path
) -> str:
    status, detail = current_output_status(output, gameassembly, metadata)
    print(f"Current DummyDll status: {status} ({detail})")
    return status


def generation_manifest(
    *,
    gameassembly: Path,
    metadata: Path,
    code_registration: int,
    metadata_registration: int,
    registration_summary: dict[str, Any],
    source: Path,
    dlls: list[Path],
    cpp2il_output: str,
    schema_identity_validation: dict[str, Any],
) -> dict[str, Any]:
    commit = cpp2il_source_commit(source)
    clean_cpp2il_output = re.sub(r"\x1b\[[0-9;]*m", "", cpp2il_output)
    skipped_image_rows = re.findall(
        r"Skipping malformed image ([^:]+):\s*([^\r\n]+)", clean_cpp2il_output
    )
    skipped_images = sorted({name for name, _reason in skipped_image_rows})
    skipped_type_count = sum(
        int(value) for value in re.findall(r"Skipped (\d+) malformed types", clean_cpp2il_output)
    )
    skipped_field_defaults = re.findall(
        r"Skipping malformed field default for ([^\r\n]+)", clean_cpp2il_output
    )
    skipped_generic_constraints = re.findall(
        r"Skipping malformed generic constraint for ([^\r\n]+)", clean_cpp2il_output
    )
    return {
        "schema": 1,
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/animestudio/generate_dummydll.py",
        "generatorSha256": sha256_file(Path(__file__)),
        "game": {
            "gameAssembly": str(gameassembly),
            "gameAssemblyBytes": gameassembly.stat().st_size,
            "gameAssemblySha256": sha256_file(gameassembly),
            "metadata": str(metadata),
            "metadataBytes": metadata.stat().st_size,
            "metadataSha256": sha256_file(metadata),
        },
        "registrations": {
            "codeRegistration": f"0x{code_registration:x}",
            "metadataRegistration": f"0x{metadata_registration:x}",
            "validation": registration_summary,
        },
        "cpp2il": {
            "repository": CPP2IL_REPOSITORY,
            "tag": CPP2IL_TAG,
            "commit": commit,
            "skippedMalformedImageCount": len(skipped_images),
            "skippedMalformedImages": skipped_images,
            "skippedMalformedImageDiagnostics": [
                {"name": name, "reason": reason}
                for name, reason in skipped_image_rows
            ],
            "skippedMalformedTypeCount": skipped_type_count,
            "expectedTypeCount": int(registration_summary.get("metadataTypeCount") or 0),
            "skippedMalformedFieldDefaultCount": len(skipped_field_defaults),
            "skippedMalformedFieldDefaultSamples": skipped_field_defaults[:50],
            "skippedMalformedGenericConstraintCount": len(skipped_generic_constraints),
            "skippedMalformedGenericConstraintSamples": skipped_generic_constraints[:50],
        },
        "assemblies": {
            "count": len(dlls),
            "bytes": sum(path.stat().st_size for path in dlls),
            "files": [
                {
                    "name": path.name,
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
                for path in dlls
            ],
        },
        "schemaIdentityValidation": schema_identity_validation,
        "limitations": [
            "DummyDll assemblies contain recovered type/schema metadata, not original managed implementations.",
            "Publication rejects any Cpp2IL type-population failure; field-default and generic-constraint omissions remain explicit coverage gaps.",
            "The set is valid only for the recorded GameAssembly.dll and global-metadata.dat hashes.",
        ],
    }


def publication_regressions(output: Path, manifest: dict[str, Any]) -> list[str]:
    """Return fail-closed coverage regressions against the current publication."""

    regressions: list[str] = []
    skipped = {
        str(name).casefold()
        for name in manifest.get("cpp2il", {}).get("skippedMalformedImages", [])
    }
    required_skipped = sorted(
        name for name in REQUIRED_ASSEMBLIES if name.casefold() in skipped
    )
    if required_skipped:
        regressions.append("required images skipped: " + ", ".join(required_skipped))
    cpp2il = manifest.get("cpp2il", {})
    skipped_types = int(cpp2il.get("skippedMalformedTypeCount") or 0)
    if skipped_types:
        regressions.append(
            f"type population incomplete: {skipped_types} malformed types"
        )

    previous_path = output / "generation.json"
    if not previous_path.is_file():
        return regressions
    try:
        previous = json.loads(previous_path.read_text(encoding="utf-8-sig"))
        previous_assemblies = previous["assemblies"]
        next_assemblies = manifest["assemblies"]
        previous_names = {
            str(row["name"]).casefold() for row in previous_assemblies["files"]
        }
        next_names = {str(row["name"]).casefold() for row in next_assemblies["files"]}
        previous_bytes = int(previous_assemblies["bytes"])
        next_bytes = int(next_assemblies["bytes"])
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return regressions
    if (
        previous_names == next_names
        and previous_bytes > 0
        and next_bytes < previous_bytes * MIN_PREVIOUS_BYTE_RATIO
    ):
        regressions.append(
            "total assembly bytes collapsed to "
            f"{next_bytes}/{previous_bytes} ({next_bytes / previous_bytes:.1%})"
        )
    return regressions


def publish(
    output: Path,
    dlls: list[Path],
    manifest: dict[str, Any],
    *,
    replace: bool,
    stamp: str,
) -> Path | None:
    output = output.resolve()
    if output.exists() and not replace:
        fail(f"Output already exists: {output}. Pass --replace after reviewing the dry run.")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = output.parent / f".{output.name}.stage-{stamp}"
    if stage.exists():
        fail(f"Refusing to reuse staging path: {stage}")
    stage.mkdir()
    for dll in dlls:
        shutil.copy2(dll, stage / dll.name)
    (stage / "generation.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    backup = None
    try:
        if output.exists():
            backup = output.parent / f"{output.name}.previous-{stamp}"
            if backup.exists():
                fail(f"Refusing to overwrite backup path: {backup}")
            output.replace(backup)
        stage.replace(output)
    except BaseException:
        if backup is not None and backup.exists() and not output.exists():
            backup.replace(output)
        raise
    return backup


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate and validate Endfield DummyDll assemblies for AnimeStudio."
    )
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cpp2il-source", type=Path, default=DEFAULT_CPP2IL_SOURCE)
    parser.add_argument("--animestudio", type=Path, default=DEFAULT_ANIMESTUDIO)
    parser.add_argument("--dotnet", default="dotnet")
    parser.add_argument("--code-registration", type=parse_int)
    parser.add_argument("--metadata-registration", type=parse_int)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--keep-work-dir", action="store_true")
    parser.add_argument(
        "--allow-coverage-regression",
        action="store_true",
        help="publish despite a required-image skip or catastrophic size regression",
    )
    parser.add_argument(
        "--no-prepare",
        action="store_true",
        help="Require an existing checkout of the pinned Cpp2IL-Endfield release; do not clone it.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="validate the current published set without scanning registrations or running Cpp2IL",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    game_root = args.game_root or configured_game_root()
    install_root, gameassembly, metadata, exe_name = resolve_game_paths(game_root)
    output = args.output.expanduser().resolve()
    if args.status_only:
        status = report_current_output_status(output, gameassembly, metadata)
        return 0 if status == "current" else 1
    (
        code_registration,
        metadata_registration,
        image_names,
        registration_summary,
        expected_identities,
    ) = discover_registrations(
        gameassembly,
        metadata,
        args.code_registration,
        args.metadata_registration,
    )
    source = args.cpp2il_source.expanduser().resolve()
    print(f"Cpp2IL source: {source}")
    print(f"Publish target: {output}")
    report_current_output_status(output, gameassembly, metadata)

    if args.no_prepare:
        if not source.exists():
            fail(f"Cpp2IL source does not exist: {source}")
    else:
        source_ready = prepare_cpp2il(source, dry_run=args.dry_run)
    if args.dry_run:
        if source.exists() and (args.no_prepare or source_ready):
            validate_cpp2il_source(source)
        print("Dry run complete; no build, generation, or publication was performed.")
        print(
            "If script-derived schemas are needed, rerun without --dry-run and "
            "with --replace."
        )
        return 0
    validate_cpp2il_source(source)
    if output.exists() and not args.replace:
        fail(f"Output already exists: {output}. Rerun with --replace after reviewing --dry-run.")

    if not args.skip_build:
        run_command(
            [args.dotnet, "build", "Cpp2IL/Cpp2IL.csproj", "-c", "Release"],
            cwd=source,
        )
    cpp2il = source / "Cpp2IL" / "bin" / "Release" / "net6.0" / "Cpp2IL.exe"
    if not cpp2il.is_file():
        fail(f"Cpp2IL-Endfield executable was not built: {cpp2il}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    work_dir = ROOT / "tmp" / "animestudio" / "dummydll" / stamp
    raw_output = work_dir / "cpp2il-output"
    raw_output.mkdir(parents=True, exist_ok=False)
    cpp2il_env = os.environ.copy()
    cpp2il_env["CPP2IL_CODE_REGISTRATION"] = f"0x{code_registration:x}"
    cpp2il_env["CPP2IL_METADATA_REGISTRATION"] = f"0x{metadata_registration:x}"
    command = [
        str(cpp2il),
        "--game-path", str(install_root),
        "--exe-name", exe_name,
        "--output-root", str(raw_output),
        "--skip-analysis",
        "--skip-metadata-txts",
        "--suppress-attributes",
        "--disable-registration-prompts",
    ]
    result = run_command(command, cwd=ROOT, env=cpp2il_env, check=False)
    (work_dir / "cpp2il.log").write_text(result.stdout or "", encoding="utf-8")
    if result.returncode:
        fail(f"Cpp2IL failed with exit code {result.returncode}; retained work directory: {work_dir}")
    match = re.search(
        r"Got Binary codereg:\s*0x([0-9A-Fa-f]+),\s*metareg:\s*0x([0-9A-Fa-f]+)",
        result.stdout or "",
    )
    if not match or int(match.group(1), 16) != code_registration or int(match.group(2), 16) != metadata_registration:
        fail(f"Cpp2IL did not confirm the validated registration addresses; retained: {work_dir}")

    dlls = validate_generated(raw_output, image_names)
    schema_identity_validation = validate_schema_identities(
        args.animestudio.expanduser().resolve(),
        raw_output,
        work_dir,
        expected_identities,
    )
    manifest = generation_manifest(
        gameassembly=gameassembly,
        metadata=metadata,
        code_registration=code_registration,
        metadata_registration=metadata_registration,
        registration_summary=registration_summary,
        source=source,
        dlls=dlls,
        cpp2il_output=result.stdout or "",
        schema_identity_validation=schema_identity_validation,
    )
    regressions = publication_regressions(output, manifest)
    manifest["publicationGate"] = {
        "status": "override" if regressions and args.allow_coverage_regression else (
            "blocked" if regressions else "passed"
        ),
        "regressions": regressions,
        "minimumPreviousByteRatio": MIN_PREVIOUS_BYTE_RATIO,
        "maximumSkippedTypeCount": 0,
    }
    if regressions and not args.allow_coverage_regression:
        fail(
            "Refusing to publish degraded DummyDll output: "
            + "; ".join(regressions)
            + f". Raw output and cpp2il.log retained at {work_dir}. "
            "Fix Cpp2IL-Endfield or the generator, or use --allow-coverage-regression only after review."
        )
    backup = publish(output, dlls, manifest, replace=args.replace, stamp=stamp)
    print(f"Published {len(dlls)} assemblies to {output}")
    print(f"Generation manifest: {output / 'generation.json'}")
    if backup is not None:
        print(f"Previous DummyDll set retained at {backup}")
    if args.keep_work_dir:
        print(f"Raw work directory retained at {work_dir}")
    else:
        resolved_work = work_dir.resolve()
        safe_root = (ROOT / "tmp" / "animestudio" / "dummydll").resolve()
        if safe_root not in resolved_work.parents:
            fail(f"Refusing to clean work directory outside {safe_root}: {resolved_work}")
        shutil.rmtree(resolved_work)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

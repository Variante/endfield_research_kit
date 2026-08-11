#!/usr/bin/env python3
"""Recover nonplayable canonical character models and build the 33-actor viewer."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable

from .all_characters import (
    DEFAULT_ALL_CHARACTER_CATALOG_PATH,
    DEFAULT_ALL_CHARACTER_WORK_ROOT,
    build_all_character_plan,
    write_all_character_plan_outputs,
)
from .catalog import DEFAULT_ASSET_MAPS, DEFAULT_CHARACTER_TABLE
from .extraction import (
    CharacterImportError,
    build_compact_manifest_asset_maps,
    collect_hierarchy_asset_ids,
    extract_character_materials,
    extract_character_meshes,
    extract_character_ui_clips,
    extract_postmodel_hierarchy,
    resolve_asset_entries,
    select_character_material_entries,
    sample_character_ui_clips,
    select_character_mesh_entries,
)
from .manifest import build_ui_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UNITY_EXE = Path(r"D:\Program Files\2022.3.62f3\Editor\Unity.exe")
UNITY_BUILD_METHOD = (
    "EndfieldGraphShaderLabEditor.EndfieldCharacterRecoverySetup.BuildAllCharacters"
)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _parse_actor_tokens(values: Iterable[str]) -> set[str] | None:
    tokens: set[str] = set()
    for value in values:
        for item in value.split(","):
            item = item.strip().casefold()
            if item.startswith("chr_") and item.count("_") >= 2:
                item = item.split("_", 2)[2]
            if item:
                tokens.add(item)
    return tokens or None


def _invoke_unity(unity_exe: Path, work_root: Path) -> dict[str, Any]:
    if not unity_exe.is_file():
        raise CharacterImportError(f"Unity 2022.3.62f3 executable not found: {unity_exe}")
    log_path = work_root / "unity_all_character_model_import.log"
    command = [
        str(unity_exe),
        "-batchmode",
        "-quit",
        "-projectPath",
        str(PROJECT_ROOT),
        "-force-d3d12",
        "-executeMethod",
        UNITY_BUILD_METHOD,
        "-logFile",
        str(log_path),
    ]
    print("+ " + subprocess.list2cmdline(command), flush=True)
    started = time.monotonic()
    completed = subprocess.run(command, cwd=str(PROJECT_ROOT), check=False)
    result = {
        "command": command,
        "return_code": completed.returncode,
        "wall_seconds": round(time.monotonic() - started, 3),
        "log": str(log_path.resolve()),
    }
    if completed.returncode != 0:
        raise CharacterImportError(
            f"Unity all-character import failed with exit code {completed.returncode}; "
            f"log: {log_path}"
        )
    return result


def _run_pipeline(args: argparse.Namespace, plan: dict[str, Any]) -> int:
    work_root = args.work_root.resolve()
    enabled = [character for character in plan["characters"] if character["import_enabled"]]
    run_report_path = work_root / "all_character_model_import_run.json"
    report: dict[str, Any] = {
        "schema_version": 1,
        "status": "running",
        "roster_count": plan["roster_count"],
        "import_character_count": len(enabled),
        "started_unix": time.time(),
        "characters": {
            character["character_id"]: {
                "actor_token": character["actor_token"],
                "actor_class": character["actor_class"],
                "animation_profile": character["ui_animation"]["animation_profile"],
                "selected_source_clips": list(character["ui_animation"]["selected_names"]),
                "stages": {},
                "errors": [],
            }
            for character in enabled
        },
        "compact_asset_maps": {},
        "unity": {},
    }

    def checkpoint() -> None:
        report["updated_unix"] = time.time()
        _write_json(run_report_path, report)

    def stage(character_id: str, name: str, state: str, **details: Any) -> None:
        report["characters"][character_id]["stages"][name] = {
            "state": state,
            **details,
        }

    checkpoint()
    failures: set[str] = set()
    asset_ids_by_character: dict[str, dict[str, set[int]]] = {}

    for character in enabled:
        character_id = character["character_id"]
        try:
            print(f"\n[{character_id}] extract canonical character post-model hierarchy")
            extract_postmodel_hierarchy(
                character,
                allowed_root=work_root,
                force=args.force,
                dry_run=args.dry_run,
            )
            if args.dry_run:
                stage(character_id, "hierarchy", "planned")
                continue
            asset_ids = collect_hierarchy_asset_ids(Path(character["work_paths"]["hierarchy"]))
            asset_ids_by_character[character_id] = asset_ids
            stage(
                character_id,
                "hierarchy",
                "ok",
                mesh_path_ids=len(asset_ids["Mesh"]),
                material_path_ids=len(asset_ids["Material"]),
            )
        except Exception as exc:
            failures.add(character_id)
            report["characters"][character_id]["errors"].append(f"hierarchy: {exc}")
            stage(character_id, "hierarchy", "failed")
            print(f"ERROR [{character_id}] hierarchy: {exc}", file=sys.stderr)
            if args.fail_fast:
                checkpoint()
                raise
        checkpoint()

    if args.dry_run:
        report["status"] = "dry_run_complete"
        checkpoint()
        return 0

    wanted = {"Mesh": set(), "Material": set()}
    for asset_ids in asset_ids_by_character.values():
        wanted["Mesh"].update(asset_ids["Mesh"])
        wanted["Material"].update(asset_ids["Material"])
    resolved = resolve_asset_entries(args.asset_map, wanted)

    for character in enabled:
        character_id = character["character_id"]
        if character_id in failures:
            continue
        try:
            mesh_entries = select_character_mesh_entries(
                character,
                asset_ids_by_character[character_id],
                resolved,
            )
            material_entries = select_character_material_entries(
                character,
                asset_ids_by_character[character_id],
                resolved,
            )
            print(
                f"\n[{character_id}] extract {len(mesh_entries)} exact meshes and "
                f"{len(material_entries)} exact materials"
            )
            extract_character_meshes(
                character,
                mesh_entries,
                allowed_root=work_root,
                force=args.force,
            )
            extract_character_materials(
                character,
                material_entries,
                allowed_root=work_root,
                force=args.force,
            )
            stage(
                character_id,
                "meshes",
                "ok",
                selected_asset_count=len(mesh_entries),
            )
            stage(
                character_id,
                "materials",
                "ok",
                selected_asset_count=len(material_entries),
            )
            clip_count = int(character["ui_animation"].get("selected_count") or 0)
            if clip_count:
                print(f"[{character_id}] extract {clip_count} exact source preview clip")
                extract_character_ui_clips(
                    character,
                    allowed_root=work_root,
                    force=args.force,
                )
            stage(
                character_id,
                "animation_clip_json",
                "ok" if clip_count else "source_proven_zero",
                selected_asset_count=clip_count,
            )
        except Exception as exc:
            failures.add(character_id)
            report["characters"][character_id]["errors"].append(f"extraction: {exc}")
            stage(character_id, "source_extraction", "failed")
            print(f"ERROR [{character_id}] extraction: {exc}", file=sys.stderr)
            if args.fail_fast:
                checkpoint()
                raise
        checkpoint()

    compact_ids = {
        character_id: asset_ids
        for character_id, asset_ids in asset_ids_by_character.items()
        if character_id not in failures
    }
    compact_maps: list[Path] = []
    if compact_ids:
        compact_maps, compact_summary = build_compact_manifest_asset_maps(
            args.asset_map,
            compact_ids,
            output_root=work_root / "compact_asset_maps",
            material_json_roots=(
                Path(character["work_paths"]["materials"])
                for character in enabled
                if character["character_id"] not in failures
            ),
        )
        report["compact_asset_maps"] = compact_summary
        checkpoint()

    for character in enabled:
        character_id = character["character_id"]
        if character_id in failures:
            continue
        try:
            clip_count = int(character["ui_animation"].get("selected_count") or 0)
            if clip_count:
                sample_result = sample_character_ui_clips(
                    character,
                    allowed_root=work_root,
                    force=args.force,
                )
                stage(character_id, "sampling", "ok", **sample_result)
            else:
                stage(
                    character_id,
                    "sampling",
                    "source_proven_zero",
                    missing_samples=[],
                )
            manifest_report = build_ui_manifest(character, compact_maps)
            stage(
                character_id,
                "manifest",
                "ok",
                manifest=manifest_report["manifest"],
                imported_clip_count=len(manifest_report["selected_ui_clips"]),
                renderer_count=int(
                    (manifest_report.get("renderer_summary") or {}).get(
                        "active_lod_renderers"
                    )
                    or 0
                ),
            )
        except Exception as exc:
            failures.add(character_id)
            report["characters"][character_id]["errors"].append(f"manifest: {exc}")
            stage(character_id, "manifest", "failed")
            print(f"ERROR [{character_id}] manifest: {exc}", file=sys.stderr)
            if args.fail_fast:
                checkpoint()
                raise
        checkpoint()

    if args.unity and not failures:
        try:
            report["unity"] = _invoke_unity(args.unity_exe.resolve(), work_root)
        except Exception as exc:
            report["unity"] = {"status": "failed", "error": str(exc)}
            report["status"] = "failed"
            checkpoint()
            print(f"ERROR Unity import: {exc}", file=sys.stderr)
            return 1
    elif args.unity:
        report["unity"] = {
            "status": "skipped",
            "reason": "one or more source recovery/manifest stages failed",
        }

    report["finished_unix"] = time.time()
    report["failed_character_ids"] = sorted(failures)
    report["successful_character_count"] = len(enabled) - len(failures)
    report["status"] = "ok" if not failures else "partial_failure"
    checkpoint()
    print(
        f"\nCanonical character import finished: "
        f"successful={len(enabled) - len(failures)}/{len(enabled)} "
        f"report={run_report_path}"
    )
    return 0 if not failures else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character-table", type=Path, default=DEFAULT_CHARACTER_TABLE)
    parser.add_argument("--asset-map", type=Path, action="append", default=None)
    parser.add_argument("--work-root", type=Path, default=DEFAULT_ALL_CHARACTER_WORK_ROOT)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_ALL_CHARACTER_CATALOG_PATH)
    parser.add_argument(
        "--actor",
        action="append",
        default=[],
        help=(
            "Limit execution to an actor token/character ID; by default the "
            "nonplayable canonical character identities are recovered"
        ),
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--unity", action="store_true")
    parser.add_argument(
        "--unity-exe",
        type=Path,
        default=Path(os.environ.get("UNITY_EXE", str(DEFAULT_UNITY_EXE))),
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.asset_map = tuple(args.asset_map or DEFAULT_ASSET_MAPS)
    plan = build_all_character_plan(
        args.character_table,
        args.asset_map,
        selected_actor_tokens=_parse_actor_tokens(args.actor),
        work_root=args.work_root,
    )
    plan_path, catalog_path = write_all_character_plan_outputs(
        plan,
        work_root=args.work_root,
        catalog_path=args.catalog,
    )
    print("\nAll-character model import plan")
    print(f"  roster: {plan['roster_count']} canonical character identities")
    print(f"  playable: {plan['playable_roster_count']}")
    print(f"  nonplayable character identities: {plan['nonplayable_character_count']}")
    print(f"  enabled this run: {plan['import_character_count']}")
    print(f"  plan: {plan_path}")
    print(f"  Unity catalog: {catalog_path}")
    if plan["missing_required_clip_sets"]:
        raise CharacterImportError(
            "a selected playable character is missing its required overview pair: "
            + ", ".join(
                item["character_id"] for item in plan["missing_required_clip_sets"]
            )
        )
    if not args.execute:
        print("Plan/catalog refreshed. Add --execute to recover assets; add --unity to build the resident viewer.")
        return 0
    return _run_pipeline(args, plan)


if __name__ == "__main__":
    raise SystemExit(main())

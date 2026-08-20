#!/usr/bin/env python3
"""Targeted AnimeStudio extraction and animation sampling helpers."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from endfield_asset_map_filter import iter_asset_entries


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent
ANIMESTUDIO_CLI = (
    REPO_ROOT
    / "tools"
    / "AnimeStudio"
    / "AnimeStudio.CLI"
    / "bin"
    / "Release"
    / "net9.0-windows"
    / "AnimeStudio.CLI.exe"
)
ACL_SAMPLE_EXPORTER = REPO_ROOT / "tools" / "endfield_acl_sampler" / "export_actor_samples.py"
MUSCLE_CLIP_SAMPLER = PROJECT_ROOT / "tools" / "unity_muscleclip_sampler.py"
DEFAULT_EXPORT_ROOT = REPO_ROOT / "export_full" / "recovered" / "AnimeStudio-cli"

# Narrow dependency-bearing type set for catalogued external UI-effect
# prefabs.  RectTransform is parsed as a dependency; MonoBehaviour is exported
# so the object-index carrier can retain exact script/PPtr evidence.
EXTERNAL_UI_EFFECT_TYPES = (
    "GameObject:Both",
    "Transform:Both",
    "RectTransform:Parse",
    "Animator:Both",
    "AnimationClip:Both",
    "Renderer:Both",
    "MeshRenderer:Both",
    "SkinnedMeshRenderer:Both",
    "LineRenderer:Both",
    "TrailRenderer:Both",
    "ParticleSystem:Both",
    "ParticleSystemRenderer:Both",
    "MonoBehaviour:Both",
    "MeshFilter:Both",
    "Mesh:Both",
    "Material:Both",
    "Texture2D:Both",
)


class CharacterImportError(RuntimeError):
    """Raised when a source recovery stage cannot produce trustworthy output."""


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _asset_root_for_map(path: Path) -> str:
    return path.parent.parent.name if path.parent.name.lower() == "maps" else path.stem


def _public_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in entry.items() if not key.startswith("_")}


def _entry_identity(entry: dict[str, Any]) -> tuple[str, str, int, str, int]:
    return (
        str(entry.get("_asset_root") or ""),
        str(entry.get("Source") or ""),
        int(entry.get("PathID") or 0),
        str(entry.get("Type") or ""),
        int(entry.get("Offset") or 0),
    )


def _dedupe_entries(entries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int, str, int]] = set()
    for entry in entries:
        identity = _entry_identity(entry)
        if identity in seen:
            continue
        seen.add(identity)
        result.append(entry)
    return result


def _source_snapshots(entries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = sorted(
        {str(entry.get("Source") or "") for entry in entries},
        key=str.casefold,
    )
    snapshots: list[dict[str, Any]] = []
    for source in sources:
        if not source:
            raise CharacterImportError("asset-map row has no source")
        path = Path(source)
        try:
            stat = path.stat()
        except OSError as exc:
            raise CharacterImportError(
                f"installed VFS source is missing or unreadable: {source}"
            ) from exc
        if not path.is_file():
            raise CharacterImportError(f"installed VFS source is not a file: {source}")
        snapshots.append(
            {
                "source": str(path.resolve()),
                "bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
        )
    return snapshots


def _run(command: list[str], *, dry_run: bool = False) -> None:
    print("+ " + subprocess.list2cmdline(command), flush=True)
    if dry_run:
        return
    completed = subprocess.run(command, cwd=str(REPO_ROOT), check=False)
    if completed.returncode != 0:
        raise CharacterImportError(
            f"command failed with exit code {completed.returncode}: {subprocess.list2cmdline(command)}"
        )


def _fingerprint(
    entries: Iterable[dict[str, Any]],
    types: Iterable[str],
    *,
    object_index_jsonl: bool = False,
) -> str:
    selected = list(entries)
    value = {
        "entries": [
            {
                "asset_root": entry.get("_asset_root", ""),
                "source": entry.get("Source", ""),
                "path_id": int(entry.get("PathID") or 0),
                "type": entry.get("Type", ""),
                "offset": int(entry.get("Offset") or 0),
            }
            for entry in sorted(selected, key=_entry_identity)
        ],
        "types": list(types),
        "source_snapshots": _source_snapshots(selected),
    }
    # Preserve old cache fingerprints when the optional object-index carrier
    # is not requested, but never reuse a stage without its requested sidecar.
    if object_index_jsonl:
        value["object_index_jsonl"] = True
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def _assert_scoped_output(path: Path, allowed_root: Path) -> None:
    resolved = path.resolve()
    root = allowed_root.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise CharacterImportError(f"refusing to modify output outside {root}: {resolved}") from exc
    if not relative.parts:
        raise CharacterImportError(f"refusing to clear the character import root itself: {resolved}")


def _has_payload(path: Path) -> bool:
    return path.is_dir() and any(item.name != ".character_import_stage.json" for item in path.iterdir())


def _prepare_stage_output(
    output: Path,
    allowed_root: Path,
    fingerprint: str,
    *,
    force: bool,
    dry_run: bool,
) -> bool:
    """Return True when the stage must run, False when an exact cache exists."""

    stamp = output / ".character_import_stage.json"
    if stamp.is_file() and _has_payload(output):
        try:
            cached = json.loads(stamp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cached = {}
        if cached.get("fingerprint") == fingerprint:
            print(f"reuse exact stage cache: {output}")
            return False

    if output.exists() and _has_payload(output):
        if not force:
            raise CharacterImportError(
                f"stale or incomplete stage output exists at {output}; rerun with --force to replace only this scoped cache"
            )
        _assert_scoped_output(output, allowed_root)
        print(f"reset scoped stage output: {output}")
        if not dry_run:
            shutil.rmtree(output)

    if not dry_run:
        output.mkdir(parents=True, exist_ok=True)
    return True


def _finish_stage(
    output: Path,
    fingerprint: str,
    entries: list[dict[str, Any]],
    types: list[str],
    *,
    object_index_jsonl: bool = False,
) -> None:
    stamp = {
        "fingerprint": fingerprint,
        "entry_count": len(entries),
        "types": types,
        "source_snapshots": _source_snapshots(entries),
    }
    if object_index_jsonl:
        stamp["object_index_jsonl"] = True
    _write_json(
        output / ".character_import_stage.json",
        stamp,
    )


def require_exact_stage_cache(
    entries: Iterable[dict[str, Any]],
    *,
    output: Path,
    types: list[str],
    stage_name: str,
) -> dict[str, Any]:
    """Fail closed unless a stage cache matches the current VFS source snapshot."""

    selected = _dedupe_entries(entries)
    if not selected:
        raise CharacterImportError(f"{stage_name}: source selection is empty")
    expected = _fingerprint(selected, types)
    stamp = output / ".character_import_stage.json"
    if not stamp.is_file() or not _has_payload(output):
        raise CharacterImportError(
            f"{stage_name}: exact extraction cache is missing at {output}; rerun with --extract"
        )
    try:
        cached = json.loads(stamp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CharacterImportError(
            f"{stage_name}: extraction cache stamp is unreadable: {stamp}"
        ) from exc
    if cached.get("fingerprint") != expected:
        raise CharacterImportError(
            f"{stage_name}: extraction cache does not match the current VFS source snapshot; "
            "rerun with --extract --force"
        )
    return cached


def extract_entries(
    entries: Iterable[dict[str, Any]],
    *,
    output: Path,
    filters_root: Path,
    allowed_root: Path,
    types: list[str],
    stage_name: str,
    force: bool = False,
    dry_run: bool = False,
    object_index_root: Path | None = None,
) -> bool:
    """Export exact map rows, grouped by their original VFS chunk."""

    selected = _dedupe_entries(entries)
    if not selected:
        raise CharacterImportError(f"{stage_name}: source selection is empty")
    if not ANIMESTUDIO_CLI.is_file():
        raise CharacterImportError(f"AnimeStudio CLI not found: {ANIMESTUDIO_CLI}")
    fingerprint = _fingerprint(
        selected,
        types,
        object_index_jsonl=object_index_root is not None,
    )
    if not _prepare_stage_output(
        output,
        allowed_root,
        fingerprint,
        force=force,
        dry_run=dry_run,
    ):
        return False
    if not dry_run and object_index_root is not None:
        _assert_scoped_output(object_index_root, allowed_root)
        object_index_root.mkdir(parents=True, exist_ok=True)

    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in selected:
        source = str(entry.get("Source") or "")
        if not source:
            raise CharacterImportError(f"{stage_name}: asset-map row has no source: {entry}")
        if not Path(source).is_file():
            raise CharacterImportError(f"{stage_name}: installed VFS source is missing: {source}")
        by_source[source].append(entry)

    for index, (source, source_entries) in enumerate(sorted(by_source.items()), start=1):
        filter_path = filters_root / f"{stage_name}_{index:03d}_{Path(source).stem}.json"
        if not dry_run:
            _write_json(filter_path, [_public_entry(entry) for entry in source_entries])
        command = [
            str(ANIMESTUDIO_CLI),
            source,
            str(output),
            "--game",
            "ArknightsEndfield",
            "--types",
            *types,
            "--export_type",
            "JSON",
            "--group_assets",
            "ByType",
            "--logger_flags",
            "Warning",
            "Error",
            "--filter_data",
            str(filter_path),
        ]
        if object_index_root is not None:
            object_index_path = object_index_root / f"{index:03d}_{Path(source).stem}.jsonl"
            _assert_scoped_output(object_index_path, allowed_root)
            command.extend(["--object_index_jsonl", str(object_index_path)])
        _run(command, dry_run=dry_run)

    if not dry_run:
        _finish_stage(
            output,
            fingerprint,
            selected,
            types,
            object_index_jsonl=object_index_root is not None,
        )
    return True


def extract_postmodel_hierarchy(
    character: dict[str, Any],
    *,
    allowed_root: Path,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    paths = character["work_paths"]
    extract_entries(
        [character["postmodel"]],
        output=Path(paths["hierarchy"]),
        filters_root=Path(paths["filters"]),
        allowed_root=allowed_root,
        types=["GameObject:Both", "Transform:Both", "SkinnedMeshRenderer:Both", "Animator:Both"],
        stage_name="postmodel_hierarchy",
        force=force,
        dry_run=dry_run,
    )


def extract_character_widget_hierarchies(
    character: dict[str, Any],
    *,
    allowed_root: Path,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    paths = character["work_paths"]
    entries = list((character.get("ui_item_widgets") or {}).get("prefab_entries") or [])
    if not entries:
        return
    extract_entries(
        entries,
        output=Path(paths["widget_hierarchy"]),
        filters_root=Path(paths["filters"]),
        allowed_root=allowed_root,
        types=[
            "GameObject:Both",
            "Transform:Both",
            "SkinnedMeshRenderer:Both",
            "MeshRenderer:Both",
            "MeshFilter:Both",
            "Animator:Both",
        ],
        stage_name="ui_item_widget_hierarchies",
        force=force,
        dry_run=dry_run,
    )


def _ref_path_id(value: Any) -> int:
    if isinstance(value, dict):
        try:
            return int(value.get("m_PathID") or 0)
        except (TypeError, ValueError):
            return 0
    return 0


def collect_hierarchy_asset_ids(hierarchy_root: Path) -> dict[str, set[int]]:
    game_objects = hierarchy_root / "GameObject"
    if not game_objects.is_dir():
        raise CharacterImportError(f"GameObject hierarchy output is missing: {game_objects}")
    mesh_ids: set[int] = set()
    material_ids: set[int] = set()
    renderer_count = 0
    for path in game_objects.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CharacterImportError(f"could not read hierarchy JSON {path}: {exc}") from exc
        skinned_renderer = data.get("m_SkinnedMeshRenderer") or {}
        mesh_renderer = data.get("m_MeshRenderer") or {}
        mesh_filter = data.get("m_MeshFilter") or {}
        renderer = skinned_renderer or mesh_renderer
        if not renderer:
            continue
        renderer_count += 1
        mesh_id = _ref_path_id(
            skinned_renderer.get("m_Mesh") if skinned_renderer else mesh_filter.get("m_Mesh")
        )
        if mesh_id:
            mesh_ids.add(mesh_id)
        for reference in renderer.get("m_Materials") or []:
            material_id = _ref_path_id(reference)
            if material_id:
                material_ids.add(material_id)
    if renderer_count == 0 or not mesh_ids:
        raise CharacterImportError(f"no mesh-renderer references found in {game_objects}")
    return {"Mesh": mesh_ids, "Material": material_ids}


def resolve_asset_entries(
    asset_maps: Iterable[Path],
    wanted: dict[str, set[int]],
) -> dict[tuple[str, int], list[dict[str, Any]]]:
    """Resolve exact type/path-ID references with one streaming map pass."""

    result: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for map_path in asset_maps:
        asset_root = _asset_root_for_map(map_path)
        for raw_entry in iter_asset_entries(map_path):
            asset_type = str(raw_entry.get("Type") or "")
            wanted_ids = wanted.get(asset_type)
            if not wanted_ids:
                continue
            try:
                path_id = int(raw_entry.get("PathID") or 0)
            except (TypeError, ValueError):
                continue
            if path_id not in wanted_ids:
                continue
            entry = dict(raw_entry)
            entry["_asset_root"] = asset_root
            result[(asset_type, path_id)].append(entry)
    return result


def _external_effect_text(value: Any) -> str:
    return str(value or "").replace("\\", "/").casefold()


def _external_effect_container_key(value: Any) -> str:
    container = _external_effect_text(value)
    parts = container.split("/")
    if len(parts) < 2 or parts[-2] != "prefabs" or not parts[-1].endswith(".prefab"):
        return ""
    if not parts[-1].startswith("p_fxui_"):
        return ""
    return container


def _external_effect_identity(entry: dict[str, Any], *, asset_root: str | None = None) -> tuple[Any, ...]:
    source = str(entry.get("Source") or "")
    name = str(entry.get("Name") or "")
    container = str(entry.get("Container") or "").replace("\\", "/")
    entry_type = str(entry.get("Type") or "")
    if not source or not name or not container or not entry_type:
        raise CharacterImportError("external UI-effect AssetMap row has incomplete identity fields")
    try:
        path_id = int(entry["PathID"])
        offset = int(entry["Offset"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CharacterImportError(
            f"external UI-effect row {name!r} lacks integer PathID/Offset"
        ) from exc
    if path_id == 0 or offset < 0:
        raise CharacterImportError(
            f"external UI-effect row {name!r} has invalid PathID/Offset: {path_id}/{offset}"
        )
    root = str(asset_root or entry.get("_asset_root") or "")
    if not root:
        raise CharacterImportError(f"external UI-effect row {name!r} lacks AssetMap root")
    return (
        root.casefold(),
        _external_effect_text(source),
        path_id,
        offset,
        entry_type,
        name,
        _external_effect_text(container),
        str(entry.get("Hash") or ""),
    )


def select_external_ui_effect_entries(
    character: dict[str, Any],
    asset_maps: Iterable[Path],
) -> dict[str, Any]:
    """Expand catalogued prefab roots to every exact same-container map row."""

    ui = character.get("ui_animation") or {}
    prefab_entries = list(ui.get("external_ui_effect_prefab_entries") or [])
    clip_entries = list(ui.get("external_ui_effect_entries") or [])
    if not prefab_entries:
        raise CharacterImportError(
            f"{character.get('character_id', 'character')}: no catalogued external UI-effect prefab roots"
        )
    containers: dict[str, dict[str, Any]] = {}
    for entry in prefab_entries:
        if not isinstance(entry, dict) or str(entry.get("Type") or "") != "Animator":
            raise CharacterImportError("external UI-effect prefab evidence contains a non-Animator root")
        key = _external_effect_container_key(entry.get("Container"))
        if not key:
            raise CharacterImportError(
                f"external UI-effect root {entry.get('Name')!r} is not in an explicit p_fxui prefab container"
            )
        prefab_name = key.rsplit("/", 1)[-1][:-7]
        if str(entry.get("Name") or "").casefold() != prefab_name:
            raise CharacterImportError(
                f"external UI-effect root {entry.get('Name')!r} does not match its exact prefab container"
            )
        if key in containers:
            raise CharacterImportError(f"duplicate external UI-effect prefab container: {key}")
        source = Path(str(entry.get("Source") or ""))
        if not source.is_file():
            raise CharacterImportError(
                f"external UI-effect source is missing for {entry.get('Name')!r}: {source}"
            )
        containers[key] = {
            "name": str(entry.get("Name") or ""),
            "container": str(entry.get("Container") or "").replace("\\", "/"),
            "root_entry": entry,
            "clip_entries": [],
        }

    selected_clip_identities: set[tuple[Any, ...]] = set()
    for entry in clip_entries:
        if not isinstance(entry, dict):
            continue
        key = _external_effect_container_key(entry.get("Container"))
        if key not in containers or str(entry.get("Type") or "") != "AnimationClip":
            continue
        name = str(entry.get("Name") or "")
        token = str(character.get("actor_token") or "")
        if not name.casefold().startswith(f"a_fx_{token.casefold()}_ui_"):
            continue
        _external_effect_identity(entry)
        containers[key]["clip_entries"].append(entry)
        selected_clip_identities.add(_external_effect_identity(entry))

    maps = [Path(path).resolve() for path in asset_maps]
    if not maps:
        raise CharacterImportError("external UI-effect selection requires at least one AssetMap")
    for map_path in maps:
        if not map_path.is_file():
            raise CharacterImportError(f"AssetMap is missing or unreadable: {map_path}")

    found: dict[tuple[Any, ...], dict[str, Any]] = {}
    duplicate: set[tuple[Any, ...]] = set()
    for map_path in maps:
        asset_root = _asset_root_for_map(map_path)
        for raw_entry in iter_asset_entries(map_path):
            key = _external_effect_container_key(raw_entry.get("Container"))
            if key not in containers:
                continue
            entry = dict(raw_entry)
            entry["_asset_root"] = asset_root
            identity = _external_effect_identity(entry, asset_root=asset_root)
            source = Path(str(entry.get("Source") or ""))
            if not source.is_file():
                raise CharacterImportError(
                    f"external UI-effect source is missing: {source}"
                )
            if identity in found:
                duplicate.add(identity)
            else:
                found[identity] = entry
    if duplicate:
        raise CharacterImportError(
            f"external UI-effect AssetMap closure has duplicate exact rows: {len(duplicate)}"
        )

    expected_roots = {
        _external_effect_identity(group["root_entry"])
        for group in containers.values()
    }
    expected_clips = selected_clip_identities
    missing_roots = expected_roots - set(found)
    missing_clips = expected_clips - set(found)
    if missing_roots or missing_clips:
        raise CharacterImportError(
            "external UI-effect exact root/clip identities are absent from AssetMap: "
            f"roots={len(missing_roots)} clips={len(missing_clips)}"
        )

    for group in containers.values():
        group["entries"] = sorted(
            [entry for identity, entry in found.items() if identity[6] == _external_effect_text(group["container"])],
            key=lambda entry: (
                str(entry.get("Type") or "").casefold(),
                str(entry.get("Name") or "").casefold(),
                int(entry.get("PathID") or 0),
                int(entry.get("Offset") or 0),
            ),
        )
        if not group["entries"]:
            raise CharacterImportError(f"external UI-effect prefab container is empty: {group['container']}")

    all_entries = [entry for group in containers.values() for entry in group["entries"]]
    return {
        "asset_maps": [str(path) for path in maps],
        "prefabs": list(containers.values()),
        "entries": all_entries,
        "entry_count": len(all_entries),
        "expected_root_identities": sorted(expected_roots, key=str),
        "expected_clip_identities": sorted(expected_clips, key=str),
        "evidence_boundary": (
            "exact same-container AssetMap closure and terminal object-index provenance only; "
            "no mount, playback, hierarchy-root, or renderability claim"
        ),
    }


def validate_object_index_jsonl_summary(path: Path) -> dict[str, Any]:
    """Require a schema-v1 terminal summary with ``complete=true``."""

    if not path.is_file():
        raise CharacterImportError(f"object-index JSONL is missing: {path}")
    rows: list[dict[str, Any]] = []
    try:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError("row is not an object")
            rows.append(value)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise CharacterImportError(f"object-index JSONL is malformed at {path}: {exc}") from exc
    if not rows:
        raise CharacterImportError(f"object-index JSONL is empty: {path}")
    summary = rows[-1]
    if (
        summary.get("recordType") != "summary"
        or summary.get("schemaVersion") != 1
        or summary.get("complete") is not True
    ):
        raise CharacterImportError(
            f"object-index JSONL lacks a terminal complete schema-v1 summary: {path}"
        )
    if any(row.get("recordType") == "summary" for row in rows[:-1]):
        raise CharacterImportError(f"object-index JSONL has a non-terminal summary: {path}")
    return summary


def validate_external_ui_effect_export(
    output: Path,
    selection: dict[str, Any],
    object_index_paths: Iterable[Path],
) -> dict[str, Any]:
    """Validate terminal object indexes and exact exported root/clip metadata."""

    summaries = [validate_object_index_jsonl_summary(path) for path in object_index_paths]
    expected = set(selection["expected_root_identities"]) | set(selection["expected_clip_identities"])
    exported: set[tuple[Any, ...]] = set()
    for path in output.rglob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        metadata = data.get("$animestudio") if isinstance(data, dict) else None
        if not isinstance(metadata, dict):
            continue
        try:
            exported.add(
                (
                    str(metadata.get("sourceOriginalPath") or "").replace("\\", "/").casefold(),
                    int(metadata.get("pathId") or 0),
                    int(metadata.get("sourceOffset") or 0),
                    str(metadata.get("type") or ""),
                    str(metadata.get("name") or ""),
                )
            )
        except (TypeError, ValueError):
            continue
    expected_root_clip = {
        (identity[1], identity[2], identity[3], identity[4], identity[5])
        for identity in expected
    }
    missing = expected_root_clip - exported
    if missing:
        raise CharacterImportError(
            f"external UI-effect export is missing exact root/clip metadata rows: {len(missing)}"
        )
    return {"object_index_summaries": summaries, "root_clip_count": len(expected_root_clip)}


def extract_external_ui_effect_stage(
    character: dict[str, Any],
    asset_maps: Iterable[Path],
    *,
    output: Path,
    allowed_root: Path,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run one exact external-effect stage with object-index provenance."""

    selection = select_external_ui_effect_entries(character, asset_maps)
    output = output.resolve()
    allowed_root = allowed_root.resolve()
    _assert_scoped_output(output, allowed_root)
    object_index_root = output / "object_index"
    extract_entries(
        selection["entries"],
        output=output,
        filters_root=output / "filters",
        allowed_root=allowed_root,
        types=list(EXTERNAL_UI_EFFECT_TYPES),
        stage_name="external_ui_effects",
        force=force,
        dry_run=dry_run,
        object_index_root=object_index_root,
    )
    sources = sorted(
        {str(entry.get("Source") or "") for entry in selection["entries"]},
        key=str.casefold,
    )
    object_index_paths = [
        object_index_root / f"{index:03d}_{Path(source).stem}.jsonl"
        for index, source in enumerate(sources, start=1)
    ]
    report = {
        "schema_version": 1,
        "character_id": character.get("character_id"),
        "actor_token": character.get("actor_token"),
        "entry_count": selection["entry_count"],
        "container_count": len(selection["prefabs"]),
        "types": list(EXTERNAL_UI_EFFECT_TYPES),
        "source_maps": selection["asset_maps"],
        "object_index_paths": [str(path) for path in object_index_paths],
        "expected_root_count": len(selection["expected_root_identities"]),
        "expected_clip_count": len(selection["expected_clip_identities"]),
        "evidence_boundary": selection["evidence_boundary"],
        "status": "planned" if dry_run else "running",
    }
    if dry_run:
        return report
    report["validation"] = validate_external_ui_effect_export(
        output,
        selection,
        object_index_paths,
    )
    report["status"] = "ok"
    _write_json(output / "external_ui_effect_stage.json", report)
    return report


def _actor_entry_score(entry: dict[str, Any], actor_token: str) -> tuple[int, int, int, str]:
    name = str(entry.get("Name") or "").lower()
    container = str(entry.get("Container") or "").replace("\\", "/").lower()
    source = Path(str(entry.get("Source") or ""))
    actor_prefix = f"s_actor_{actor_token.lower()}_"
    return (
        0 if name.startswith(actor_prefix) else 1,
        0 if f"/{actor_token.lower()}/" in container else 1,
        0 if source.is_file() else 1,
        container,
    )


def select_character_mesh_entries(
    character: dict[str, Any],
    asset_ids: dict[str, set[int]],
    resolved: dict[tuple[str, int], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    missing: list[int] = []
    token = str(character["actor_token"])
    for path_id in sorted(asset_ids.get("Mesh") or set()):
        candidates = resolved.get(("Mesh", path_id), [])
        if not candidates:
            missing.append(path_id)
            continue
        selected.append(sorted(candidates, key=lambda entry: _actor_entry_score(entry, token))[0])
    if missing:
        raise CharacterImportError(
            f"{character['character_id']}: {len(missing)} post-model mesh path IDs are absent from the asset maps: "
            + ", ".join(str(value) for value in missing[:12])
        )
    return selected


def select_character_material_entries(
    character: dict[str, Any],
    asset_ids: dict[str, set[int]],
    resolved: dict[tuple[str, int], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Resolve every source Material PPtr without accepting identity collisions."""

    selected: list[dict[str, Any]] = []
    missing: list[int] = []
    ambiguous: list[dict[str, Any]] = []
    for path_id in sorted(asset_ids.get("Material") or set()):
        candidates = resolved.get(("Material", path_id), [])
        if not candidates:
            missing.append(path_id)
            continue
        identities = {
            (
                str(entry.get("Name") or ""),
                str(entry.get("Container") or "").replace("\\", "/").casefold(),
            )
            for entry in candidates
        }
        if len(identities) != 1:
            ambiguous.append(
                {
                    "path_id": path_id,
                    "candidates": [
                        {
                            "name": str(entry.get("Name") or ""),
                            "container": str(entry.get("Container") or ""),
                            "source": str(entry.get("Source") or ""),
                            "asset_root": str(entry.get("_asset_root") or ""),
                        }
                        for entry in candidates
                    ],
                }
            )
            continue
        selected.append(
            sorted(
                candidates,
                key=lambda entry: (
                    0 if entry.get("_asset_root") == "StreamingAssets" else 1,
                    str(entry.get("Source") or "").casefold(),
                ),
            )[0]
        )
    if missing:
        raise CharacterImportError(
            f"{character['character_id']}: {len(missing)} post-model Material path IDs are absent from the asset maps: "
            + ", ".join(str(value) for value in missing[:12])
        )
    if ambiguous:
        raise CharacterImportError(
            f"{character['character_id']}: source Material PathID ownership is ambiguous: "
            + json.dumps(ambiguous[:8], ensure_ascii=False, sort_keys=True)
        )
    return selected


def extract_character_meshes(
    character: dict[str, Any],
    mesh_entries: list[dict[str, Any]],
    *,
    allowed_root: Path,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    paths = character["work_paths"]
    extract_entries(
        mesh_entries,
        output=Path(paths["meshes"]),
        filters_root=Path(paths["filters"]),
        allowed_root=allowed_root,
        types=["Mesh:Both"],
        stage_name="postmodel_meshes",
        force=force,
        dry_run=dry_run,
    )


def extract_character_materials(
    character: dict[str, Any],
    material_entries: list[dict[str, Any]],
    *,
    allowed_root: Path,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    paths = character["work_paths"]
    extract_entries(
        material_entries,
        output=Path(paths["materials"]),
        filters_root=Path(paths["filters"]),
        allowed_root=allowed_root,
        types=["Material:Both"],
        stage_name="postmodel_materials",
        force=force,
        dry_run=dry_run,
    )


def extract_character_widget_meshes(
    character: dict[str, Any],
    mesh_entries: list[dict[str, Any]],
    *,
    allowed_root: Path,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    if not mesh_entries:
        return
    paths = character["work_paths"]
    extract_entries(
        mesh_entries,
        output=Path(paths["widget_meshes"]),
        filters_root=Path(paths["filters"]),
        allowed_root=allowed_root,
        types=["Mesh:Both"],
        stage_name="ui_item_widget_meshes",
        force=force,
        dry_run=dry_run,
    )


def extract_character_ui_clips(
    character: dict[str, Any],
    *,
    allowed_root: Path,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    paths = character["work_paths"]
    entries = list((character.get("ui_animation") or {}).get("selected_entries") or [])
    extract_entries(
        entries,
        output=Path(paths["animation_clips"]),
        filters_root=Path(paths["filters"]),
        allowed_root=allowed_root,
        types=["AnimationClip:Both"],
        stage_name=f"ui_clips_{character['ui_animation']['clip_scope']}",
        force=force,
        dry_run=dry_run,
    )


def extract_character_widget_ui_clips(
    character: dict[str, Any],
    *,
    allowed_root: Path,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    paths = character["work_paths"]
    entries = list(
        (character.get("ui_animation") or {}).get("selected_companion_widget_entries") or []
    )
    if not entries:
        return
    extract_entries(
        entries,
        output=Path(paths["widget_animation_clips"]),
        filters_root=Path(paths["filters"]),
        allowed_root=allowed_root,
        types=["AnimationClip:Both"],
        stage_name=f"ui_item_widget_clips_{character['ui_animation']['clip_scope']}",
        force=force,
        dry_run=dry_run,
    )


def _sample_fingerprint(character: dict[str, Any]) -> str:
    names = list((character.get("ui_animation") or {}).get("selected_names") or [])
    value = {
        "character_id": character.get("character_id"),
        "postmodel_root": character.get("postmodel_root"),
        "clips": sorted(names, key=str.casefold),
        "buffers": ["TransformBufferData", "UnityMuscleClip"],
        "animation_abi": "endfield_101_muscle_206_index_v1",
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def sample_character_ui_clips(
    character: dict[str, Any],
    *,
    allowed_root: Path,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    paths = character["work_paths"]
    clip_root = Path(paths["animation_clips"]) / "AnimationClip"
    hierarchy_root = Path(paths["hierarchy"])
    sample_root = Path(paths["samples"])
    fingerprint = _sample_fingerprint(character)
    if not _prepare_stage_output(
        sample_root,
        allowed_root,
        fingerprint,
        force=force,
        dry_run=dry_run,
    ):
        return {"reused": True, "missing_samples": []}
    if not dry_run and not clip_root.is_dir():
        raise CharacterImportError(f"AnimationClip export is missing: {clip_root}")
    for required in (ACL_SAMPLE_EXPORTER, MUSCLE_CLIP_SAMPLER):
        if not required.is_file():
            raise CharacterImportError(f"animation sampler is missing: {required}")

    _run(
        [
            sys.executable,
            str(ACL_SAMPLE_EXPORTER),
            "--clip-dir",
            str(clip_root),
            "--output-dir",
            str(sample_root),
            "--actor",
            f"A_actor_{character['actor_token']}_",
            "--buffer",
            "TransformBufferData",
        ],
        dry_run=dry_run,
    )
    muscle_summary = sample_root / "unity_muscleclip_summary.json"
    _run(
        [
            sys.executable,
            str(MUSCLE_CLIP_SAMPLER),
            "--clip-dir",
            str(clip_root),
            "--hierarchy-dir",
            str(hierarchy_root),
            "--root-name",
            str(character["postmodel_root"]),
            "--output-dir",
            str(sample_root),
            "--actor-token",
            str(character["actor_token"]),
            "--summary-json",
            str(muscle_summary),
        ],
        dry_run=dry_run,
    )

    missing: list[str] = []
    if not dry_run:
        for name in character["ui_animation"]["selected_names"]:
            sample_path = sample_root / f"{name}.json"
            if not sample_path.is_file() or sample_path.stat().st_size == 0:
                missing.append(name)
        if missing:
            raise CharacterImportError(
                f"{character['character_id']}: no decoded transform sample was produced for: "
                + ", ".join(missing)
            )
        _finish_stage(
            sample_root,
            fingerprint,
            list(character["ui_animation"]["selected_entries"]),
            ["TransformBufferData", "UnityMuscleClip"],
        )
    return {"reused": False, "missing_samples": missing}


def sample_character_widget_ui_clips(
    character: dict[str, Any],
    *,
    allowed_root: Path,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Decode selected private-widget transform buffers without inventing bindings.

    Hierarchy matching happens while the manifest is built.  A clip with no
    ACL TransformBufferData remains an explicit gap instead of failing the
    character's otherwise valid UI-deco geometry import.
    """

    paths = character["work_paths"]
    entries = list(
        (character.get("ui_animation") or {}).get("selected_companion_widget_entries") or []
    )
    names = [str(entry.get("Name") or "") for entry in entries]
    if not entries:
        return {"reused": True, "selected": 0, "missing_samples": []}

    clip_root = Path(paths["widget_animation_clips"]) / "AnimationClip"
    sample_root = Path(paths["widget_samples"])
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "character_id": character.get("character_id"),
                "widget_prefabs": [
                    str(entry.get("Name") or "")
                    for entry in (character.get("ui_item_widgets") or {}).get("prefab_entries") or []
                ],
                "clips": sorted(names, key=str.casefold),
                "buffer": "TransformBufferData",
                "acl_selection": "all_exported_selected_widget_clips_v2",
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    if not _prepare_stage_output(
        sample_root,
        allowed_root,
        fingerprint,
        force=force,
        dry_run=dry_run,
    ):
        missing = [
            name
            for name in names
            if not any(sample_root.glob(f"**/{name}.json"))
        ]
        return {"reused": True, "selected": len(names), "missing_samples": missing}
    if not dry_run and not clip_root.is_dir():
        raise CharacterImportError(f"item-widget AnimationClip export is missing: {clip_root}")
    if not ACL_SAMPLE_EXPORTER.is_file():
        raise CharacterImportError(f"ACL animation sampler is missing: {ACL_SAMPLE_EXPORTER}")

    _run(
        [
            sys.executable,
            str(ACL_SAMPLE_EXPORTER),
            "--clip-dir",
            str(clip_root),
            "--output-dir",
            str(sample_root),
            "--actor",
            # clip_root is already an exact, source-filtered stage.  An empty
            # substring deliberately selects every exported clip, including
            # lower-case families such as widget_dapan_* as well as generic
            # controller-owned A_item_widget_* and A_wpn_misc_* families.
            "",
            "--buffer",
            "TransformBufferData",
        ],
        dry_run=dry_run,
    )

    # UI-deco clips frequently use Unity's streamed/dense/constant
    # MuscleClip storage rather than ACL TransformBufferData. Decode each
    # exact private prefab independently so a same-named Root hierarchy from a
    # different decoration cannot be selected accidentally.
    hierarchy_root = Path(paths["widget_hierarchy"])
    for prefab in (character.get("ui_item_widgets") or {}).get("prefab_entries") or []:
        prefab_name = str(prefab.get("Name") or "")
        if not prefab_name:
            continue
        prefab_output = sample_root / prefab_name
        summary_path = prefab_output / "unity_muscleclip_summary.json"
        command = [
            sys.executable,
            str(MUSCLE_CLIP_SAMPLER),
            "--clip-dir",
            str(clip_root),
            "--hierarchy-dir",
            str(hierarchy_root),
            "--root-name",
            prefab_name,
            "--output-dir",
            str(prefab_output),
            "--summary-json",
            str(summary_path),
        ]
        for name in names:
            command.extend(["--clip-name", name])
        _run(command, dry_run=dry_run)

    missing: list[str] = []
    if not dry_run:
        missing = [
            name
            for name in names
            if not any(
                path.is_file() and path.stat().st_size > 0
                for path in sample_root.glob(f"**/{name}.json")
            )
        ]
        _finish_stage(sample_root, fingerprint, entries, ["TransformBufferData"])
    return {"reused": False, "selected": len(names), "missing_samples": missing}


def _find_material_json(export_root: Path, entry: dict[str, Any]) -> Path | None:
    name = str(entry.get("Name") or "")
    path_id = int(entry.get("PathID") or 0)
    if not name and path_id == 0:
        return None
    roots = [str(entry.get("_asset_root") or ""), "StreamingAssets", "Persistent"]
    seen: set[str] = set()
    for asset_root in roots:
        if not asset_root or asset_root.lower() in seen:
            continue
        seen.add(asset_root.lower())
        folder = export_root / asset_root / "json_by_type" / "Material"
        direct = folder / f"{name}.json"
        if direct.is_file():
            return direct
        matches = sorted(folder.glob(f"{name}_p*.json")) if folder.is_dir() else []
        if matches:
            return matches[0]
        if path_id and folder.is_dir():
            suffix = f"_p{path_id & 0xFFFFFFFFFFFFFFFF:016X}.json"
            matches = sorted(folder.glob(f"*{suffix}"))
            if matches:
                return matches[0]
    return None


def _material_dependency_ids(path: Path) -> dict[str, set[int]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    shader_ids: set[int] = set()
    texture_ids: set[int] = set()
    shader_id = _ref_path_id(data.get("m_Shader"))
    if shader_id:
        shader_ids.add(shader_id)
    raw_tex_envs = ((data.get("m_SavedProperties") or {}).get("m_TexEnvs") or {})
    tex_envs: dict[str, Any] = {}
    if isinstance(raw_tex_envs, dict):
        tex_envs.update(raw_tex_envs)
    elif isinstance(raw_tex_envs, list):
        for entry in raw_tex_envs:
            if isinstance(entry, dict):
                tex_envs.update(entry)
    for value in tex_envs.values():
        texture_id = _ref_path_id((value or {}).get("m_Texture") if isinstance(value, dict) else None)
        if texture_id:
            texture_ids.add(texture_id)
    return {"Shader": shader_ids, "Texture2D": texture_ids}


def _find_scoped_material_json(
    material_json_roots: Iterable[Path],
    path_id: int,
) -> Path | None:
    suffix = f"_p{path_id & 0xFFFFFFFFFFFFFFFF:016X}.json"
    matches: list[Path] = []
    for root in material_json_roots:
        folder = Path(root)
        if folder.name != "Material":
            folder = folder / "Material"
        if folder.is_dir():
            matches.extend(sorted(folder.glob(f"*{suffix}")))
    unique = sorted({path.resolve() for path in matches})
    if not unique:
        return None
    payload_hashes = {
        hashlib.sha256(path.read_bytes()).hexdigest() for path in unique
    }
    if len(payload_hashes) != 1:
        raise CharacterImportError(
            f"Material PathID {path_id} has conflicting scoped JSON payloads: "
            + ", ".join(str(path) for path in unique)
        )
    return unique[0]


def build_compact_manifest_asset_maps(
    asset_maps: Iterable[Path],
    character_asset_ids: dict[str, dict[str, set[int]]],
    *,
    output_root: Path,
    export_root: Path = DEFAULT_EXPORT_ROOT,
    material_json_roots: Iterable[Path] = (),
) -> tuple[list[Path], dict[str, Any]]:
    """Write small map files containing only dependencies used by the roster."""

    map_paths = tuple(path.resolve() for path in asset_maps)
    first_wanted: dict[str, set[int]] = {"Mesh": set(), "Material": set()}
    for ids in character_asset_ids.values():
        first_wanted["Mesh"].update(ids.get("Mesh") or set())
        first_wanted["Material"].update(ids.get("Material") or set())
    first = resolve_asset_entries(map_paths, first_wanted)

    dependencies: dict[str, set[int]] = {"Shader": set(), "Texture2D": set()}
    missing_material_json: list[dict[str, Any]] = []
    scoped_material_roots = tuple(Path(path) for path in material_json_roots)
    for path_id in sorted(first_wanted["Material"]):
        entries = first.get(("Material", path_id), [])
        if not entries:
            missing_material_json.append({"path_id": path_id, "reason": "asset-map row missing"})
            continue
        material_path = _find_scoped_material_json(
            scoped_material_roots,
            path_id,
        ) or next(
            (path for entry in entries if (path := _find_material_json(export_root, entry)) is not None),
            None,
        )
        if material_path is None:
            missing_material_json.append(
                {
                    "path_id": path_id,
                    "names": sorted({str(entry.get("Name") or "") for entry in entries}),
                    "reason": "exported Material JSON missing",
                }
            )
            continue
        material_dependencies = _material_dependency_ids(material_path)
        dependencies["Shader"].update(material_dependencies["Shader"])
        dependencies["Texture2D"].update(material_dependencies["Texture2D"])

    second = resolve_asset_entries(map_paths, dependencies)
    combined_entries: list[dict[str, Any]] = []
    for groups in (first, second):
        for entries in groups.values():
            combined_entries.extend(entries)
    combined_entries = _dedupe_entries(combined_entries)

    by_root: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in combined_entries:
        by_root[str(entry.get("_asset_root") or "Unknown")].append(_public_entry(entry))

    output_paths: list[Path] = []
    roots = sorted(set(by_root) | {"StreamingAssets", "Persistent"}, key=str.casefold)
    for asset_root in roots:
        output_path = output_root / asset_root / "maps" / "character_manifest_assets.json"
        _write_json(
            output_path,
            {
                "GameType": "ArknightsEndfield",
                "AssetEntries": sorted(
                    by_root.get(asset_root, []),
                    key=lambda entry: (
                        str(entry.get("Type") or ""),
                        str(entry.get("Name") or "").casefold(),
                        int(entry.get("PathID") or 0),
                    ),
                ),
            },
        )
        output_paths.append(output_path)

    summary = {
        "mesh_path_id_count": len(first_wanted["Mesh"]),
        "material_path_id_count": len(first_wanted["Material"]),
        "shader_path_id_count": len(dependencies["Shader"]),
        "texture_path_id_count": len(dependencies["Texture2D"]),
        "compact_entry_count": len(combined_entries),
        "missing_material_json": missing_material_json,
        "map_paths": [str(path.resolve()) for path in output_paths],
    }
    _write_json(output_root / "compact_asset_map_summary.json", summary)
    return output_paths, summary

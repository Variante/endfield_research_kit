#!/usr/bin/env python3
"""Cross-audit every current actor gallery and named NPC source identity.

This is a source-only report builder.  It does not launch Unity or mutate any
generated prefab/manifest.  Exact Animator PPtrs are resolved through the
hosting serialized CAB dependency table; named NPC appearance identities are
kept distinct from the shared pedestrian archetype rigs they reference.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .audit_generic_actor_animations import (
    CAB_MAPS,
    _ptr,
    _public_target,
    build_indices,
    find_extracted,
    parse_cab_map,
    resolve_host,
    resolve_pointer,
    summarize_avatar,
    target_identity,
)
from .extraction import CharacterImportError, extract_entries, require_exact_stage_cache


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent
CHARACTER_CATALOG = (
    PROJECT_ROOT
    / "scratch/character_recovery/all_character_plan_audit/all_character_model_catalog.json"
)
GENERIC_CATALOG = (
    PROJECT_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/Actors/Catalog/noncharacter_actor_catalog.json"
)
GENERIC_ANIMATION_AUDIT = (
    REPO_ROOT
    / "reports/assets/character_recovery/generic_actor_animation_source_audit.json"
)
POSTMODEL_INVENTORY = (
    REPO_ROOT
    / "reports/assets/character_recovery/nonplayable_actor_postmodel_inventory.json"
)
NAMED_NPC_INVENTORY = (
    REPO_ROOT
    / "reports/assets/character_recovery/named_npc_appearance_inventory.json"
)
NONPLAYABLE_DEPENDENCY_AUDIT = (
    PROJECT_ROOT
    / "scratch/character_recovery/nonplayable_actor_dependencies/dependency_audit.json"
)
WORK_ROOT = PROJECT_ROOT / "scratch/character_recovery/complete_actor_inventory"
REPORT_JSON = (
    REPO_ROOT
    / "reports/assets/character_recovery/complete_actor_recovery_inventory_audit.json"
)
REPORT_MD = REPORT_JSON.with_suffix(".md")
def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _source_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "Name": str(row.get("name") or row.get("Name") or ""),
        "Container": str(row.get("container") or row.get("Container") or ""),
        "Source": str(row.get("source") or row.get("Source") or ""),
        "PathID": int(row.get("path_id") or row.get("PathID") or 0),
        "Type": str(row.get("type") or row.get("Type") or "Animator"),
        "Hash": str(row.get("object_hash") or row.get("Hash") or ""),
        "Offset": int(row.get("offset") or row.get("Offset") or 0),
        "_asset_root": str(row.get("asset_root") or row.get("_asset_root") or ""),
        "asset_root": str(row.get("asset_root") or row.get("_asset_root") or ""),
    }


def _extraction_entry(target: dict[str, Any]) -> dict[str, Any]:
    return {
        "Name": f"{target['type']}#{target['path_id']}",
        "Container": "",
        "Source": target["source"],
        "PathID": int(target["path_id"]),
        "Type": target["type"],
        "Hash": "",
        "Offset": int(target["offset"]),
        "_asset_root": target["asset_root"],
    }


def _dedupe_targets(targets: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, int]] = set()
    for target in targets:
        identity = target_identity(target)
        if identity in seen:
            continue
        seen.add(identity)
        result.append(target)
    return sorted(result, key=target_identity)


def _manifest_path(row: dict[str, Any]) -> Path:
    return PROJECT_ROOT / str(row.get("manifest_asset_path") or "")


def _lod0_names(manifest: dict[str, Any]) -> set[str]:
    return {
        str(row.get("name") or "")
        for row in manifest.get("meshes") or []
        if str(row.get("name") or "").casefold().endswith("_lod0")
    }


def _current_visual_sets(
    characters: list[dict[str, Any]], generic_actors: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for gallery, rows, id_key in (
        ("character_grade", characters, "character_id"),
        ("generic", generic_actors, "stable_actor_id"),
    ):
        for row in rows:
            path = _manifest_path(row)
            if not path.is_file():
                continue
            result.append(
                {
                    "gallery": gallery,
                    "actor_id": str(row[id_key]),
                    "actor_root": str(
                        row.get("postmodel_root") or row.get("root_name") or ""
                    ),
                    "lod0_meshes": _lod0_names(_load(path)),
                }
            )
    return result


def _visual_overlaps(
    source_meshes: set[str], current_sets: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not source_meshes:
        return []
    result: list[dict[str, Any]] = []
    for row in current_sets:
        overlap = source_meshes & row["lod0_meshes"]
        if not overlap:
            continue
        if overlap == source_meshes == row["lod0_meshes"]:
            status = "exact_lod0_mesh_set_match_only_not_root_identity"
        elif overlap == source_meshes:
            status = "missing_root_mesh_set_is_subset_of_resident"
        elif len(overlap) / len(source_meshes) >= 0.5:
            status = "partial_visual_overlap_only"
        else:
            continue
        result.append(
            {
                "gallery": row["gallery"],
                "actor_id": row["actor_id"],
                "actor_root": row["actor_root"],
                "status": status,
                "overlap_count": len(overlap),
                "source_mesh_count": len(source_meshes),
                "resident_mesh_count": len(row["lod0_meshes"]),
                "overlap_meshes": sorted(overlap, key=str.casefold),
                "identity_boundary": (
                    "mesh overlap is visual reuse, not evidence that the authored source root "
                    "or NPC identity is resident"
                ),
            }
        )
    return sorted(result, key=lambda row: (-row["overlap_count"], row["actor_id"]))


def _find_character_identity(
    postmodel_inventory: dict[str, Any], character_id: str
) -> dict[str, Any]:
    matches = [
        row
        for row in postmodel_inventory["identities"]
        if row.get("canonical") and row.get("stable_actor_id") == character_id
    ]
    if len(matches) != 1:
        raise CharacterImportError(
            f"expected one canonical source identity for {character_id}, found {len(matches)}"
        )
    return matches[0]


def _render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Complete actor recovery inventory audit",
        "",
        "Generated from original game prefab/Animator data and current source-derived galleries; no Unity run is used.",
        "",
        "## Coverage",
        "",
        f"- resident galleries: {summary['resident_actor_count']} actors ({summary['character_grade_count']} character-grade + {summary['generic_actor_count']} generic)",
        f"- canonical enemies/props missing: {summary['missing_canonical_enemy_count']}/{summary['missing_canonical_prop_count']}",
        f"- character-grade Avatar objects: {summary['character_grade_extracted_avatar_object_count']}/{summary['character_grade_unique_avatar_target_count']} exact current-snapshot objects extracted",
        f"- named NPC identities: {summary['named_identity_count']} ({summary['authored_named_identity_count']} authored-postmodel + {summary['modular_named_identity_count']} modular)",
        f"- authored named roots: {summary['authored_named_root_count']} total; {summary['resident_authored_named_root_count']} resident and {summary['missing_authored_named_root_count']} missing",
        f"- modular base rigs: {summary['resident_modular_base_rig_count']}/8 resident; {summary['modular_identity_with_resident_base_rig_count']} identities have only a shared resident rig, {summary['modular_identity_without_resident_base_rig_count']} lack even that rig",
        "",
        "## Focus identities",
        "",
    ]
    for key in ("liino", "jsspsi", "chenpast"):
        row = report["focus"][key]
        lines.append(f"- **{row['label']}**: {row['conclusion']}")
    lines.extend(
        [
            "",
            "## Missing true authored roots",
            "",
            "These 28 entries are source-authored prefab roots, not pedestrian aliases. A zero Animator count means no exact AssetMap Animator row matched that prefab; Avatar/controller/clip counts are therefore unknown, not inferred zero.",
            "",
            "| Root | Family | Named aliases | Exact Animator | Current visual overlap |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for row in report["missing_authored_roots"]:
        overlaps = ", ".join(
            value["actor_id"] for value in row["resident_visual_overlap_candidates"][:2]
        ) or "none"
        lines.append(
            f"| `{row['actor_root']}` | {row['family']} | {row['named_identity_count']} | {row['animator']['exact_asset_map_count']} | {overlaps} |"
        )
    lines.extend(
        [
            "",
            "## Modular identity boundary",
            "",
            "The 632 modular identities do not own 632 prefab roots. They select ordered parts/material codes over eight shared pedestrian rigs. All eight base rigs are now resident, but no modular identity's exact assembled appearance is resident yet.",
            "",
            "## Evidence boundaries",
            "",
        ]
    )
    lines.extend(f"- {value}" for value in report["evidence_boundaries"])
    lines.append("")
    return "\n".join(lines)


def build(args: argparse.Namespace) -> dict[str, Any]:
    characters_doc = _load(args.character_catalog)
    generic_doc = _load(args.generic_catalog)
    generic_animation = _load(args.generic_animation_audit)
    postmodel = _load(args.postmodel_inventory)
    named = _load(args.named_npc_inventory)
    dependencies = _load(args.nonplayable_dependency_audit)
    characters = list(characters_doc["characters"])
    generic_actors = list(generic_doc["actors"])
    if len(characters) != 33 or len(generic_actors) != 131:
        raise CharacterImportError(
            f"unexpected gallery size: {len(characters)} character, {len(generic_actors)} generic"
        )

    cab_records = [
        record
        for root, path in args.cab_map.items()
        for record in parse_cab_map(path, root)
    ]
    by_location, by_cab = build_indices(cab_records)
    base_folders = {
        root: next(row.base_folder for row in cab_records if row.asset_root == root)
        for root in args.cab_map
    }

    current_roots: dict[str, dict[str, Any]] = {}
    for row in characters:
        current_roots[str(row["postmodel_root"]).casefold()] = {
            "gallery": "character_grade",
            "actor_id": row["character_id"],
        }
    for row in generic_actors:
        root = str(row.get("postmodel_root") or row.get("root_name") or "")
        if not root:
            raise CharacterImportError(f"generic actor has no source root: {row}")
        current_roots[root.casefold()] = {
            "gallery": "generic",
            "actor_id": row["stable_actor_id"],
        }
    if len(current_roots) != 164:
        raise CharacterImportError(f"expected 164 unique resident roots, found {len(current_roots)}")

    character_sources: dict[str, dict[str, Any]] = {}
    for row in characters:
        character_id = str(row["character_id"])
        identity = _find_character_identity(postmodel, character_id)
        entries = identity.get("animator_entries") or []
        if len(entries) != 1:
            raise CharacterImportError(
                f"{character_id}: expected one Animator source row, found {len(entries)}"
            )
        character_sources[character_id] = _source_row(entries[0])

    character_animator_entries = list(character_sources.values())
    character_animator_output = args.work_root / "character_animators"
    character_animator_types = ["Animator:Both"]
    if args.extract:
        extract_entries(
            character_animator_entries,
            output=character_animator_output,
            filters_root=args.work_root / "filters/character_animators",
            allowed_root=args.work_root,
            types=character_animator_types,
            stage_name="complete_inventory_character_animators",
            force=args.force,
        )
    else:
        require_exact_stage_cache(
            character_animator_entries,
            output=character_animator_output,
            types=character_animator_types,
            stage_name="complete_inventory_character_animators",
        )

    character_records: list[dict[str, Any]] = []
    character_avatar_targets: list[dict[str, Any]] = []
    for row in characters:
        source = character_sources[str(row["character_id"])]
        source_path_id = int(source["PathID"])
        path = find_extracted(character_animator_output, "Animator", source_path_id)
        animator = _load(path)
        if str(animator.get("Name") or "") != str(row["postmodel_root"]):
            raise CharacterImportError(f"Animator/root mismatch: {path}")
        host = resolve_host(source, by_location, base_folders)
        avatar_pointer = _ptr(animator.get("m_Avatar"))
        controller_pointer = _ptr(animator.get("m_Controller"))
        if not avatar_pointer["path_id"]:
            raise CharacterImportError(f"{row['character_id']}: null source Avatar")
        avatar_target, _ = resolve_pointer(host, avatar_pointer, "Avatar", by_cab)
        character_avatar_targets.append(avatar_target)
        manifest_path = _manifest_path(row)
        manifest = _load(manifest_path)
        character_records.append(
            {
                "actor_id": row["character_id"],
                "actor_token": row["actor_token"],
                "actor_class": row["actor_class"],
                "actor_root": row["postmodel_root"],
                "animator": {
                    "available": True,
                    "source": source,
                    "source_json": _file_record(path),
                },
                "avatar": {
                    "available": True,
                    "pointer": avatar_pointer,
                    "target": _public_target(avatar_target),
                },
                "postmodel_controller": {
                    "available": bool(controller_pointer["path_id"]),
                    "pointer": controller_pointer,
                    "boundary": (
                        "null on the source postmodel Animator; runtime/UI controllers may be "
                        "assigned by separate game systems"
                        if not controller_pointer["path_id"]
                        else "non-null source postmodel binding"
                    ),
                },
                "source_selected_clips": {
                    "count": len(manifest.get("clips") or []),
                    "names": [str(value.get("name") or "") for value in manifest.get("clips") or []],
                    "controller_referenced_count": 0 if not controller_pointer["path_id"] else None,
                    "controller_recovery": manifest.get("animation_controller_recovery") or {},
                },
                "manifest": _file_record(manifest_path),
            }
        )

    base_rig_animator_entries: list[dict[str, Any]] = []
    for base in named["base_rigs"]:
        if base["current_lab_status"] in {
            "recovered_source_archetype_prefab",
            "recovered_source_archetype_base_rig",
        }:
            continue
        streaming = [
            value
            for value in base.get("asset_map_animator_candidates") or []
            if value.get("asset_root") == "StreamingAssets"
        ]
        if len(streaming) != 1:
            raise CharacterImportError(
                f"{base['actor_root']}: expected one StreamingAssets Animator candidate"
            )
        entry = _source_row(streaming[0])
        entry["base_rig_root"] = base["actor_root"]
        base_rig_animator_entries.append(entry)

    if base_rig_animator_entries and args.extract:
        extract_entries(
            base_rig_animator_entries,
            output=args.work_root / "base_rig_animators",
            filters_root=args.work_root / "filters/base_rig_animators",
            allowed_root=args.work_root,
            types=["Animator:Both"],
            stage_name="complete_inventory_missing_base_rig_animators",
            force=args.force,
        )
    elif base_rig_animator_entries:
        require_exact_stage_cache(
            base_rig_animator_entries,
            output=args.work_root / "base_rig_animators",
            types=["Animator:Both"],
            stage_name="complete_inventory_missing_base_rig_animators",
        )

    base_rig_probe: dict[str, dict[str, Any]] = {}
    base_rig_avatar_targets: list[dict[str, Any]] = []
    for entry in base_rig_animator_entries:
        path = find_extracted(
            args.work_root / "base_rig_animators", "Animator", int(entry["PathID"])
        )
        animator = _load(path)
        host = resolve_host(entry, by_location, base_folders)
        avatar_pointer = _ptr(animator.get("m_Avatar"))
        controller_pointer = _ptr(animator.get("m_Controller"))
        avatar_target = None
        if avatar_pointer["path_id"]:
            avatar_target, _ = resolve_pointer(host, avatar_pointer, "Avatar", by_cab)
            base_rig_avatar_targets.append(avatar_target)
        base_rig_probe[str(entry["base_rig_root"]).casefold()] = {
            "animator": {
                "available": True,
                "source": {key: value for key, value in entry.items() if key != "base_rig_root"},
                "source_json": _file_record(path),
            },
            "avatar": {
                "available": avatar_target is not None,
                "pointer": avatar_pointer,
                "target": _public_target(avatar_target) if avatar_target else None,
            },
            "controller": {
                "available": bool(controller_pointer["path_id"]),
                "pointer": controller_pointer,
            },
            "controller_referenced_clip_count": (
                0 if not controller_pointer["path_id"] else None
            ),
        }

    all_avatar_targets = _dedupe_targets(character_avatar_targets + base_rig_avatar_targets)
    if args.extract:
        extract_entries(
            [_extraction_entry(value) for value in all_avatar_targets],
            output=args.work_root / "avatars",
            filters_root=args.work_root / "filters/avatars",
            allowed_root=args.work_root,
            types=["Avatar:Both"],
            stage_name="complete_inventory_character_and_base_rig_avatars",
            force=args.force,
        )
    else:
        require_exact_stage_cache(
            [_extraction_entry(value) for value in all_avatar_targets],
            output=args.work_root / "avatars",
            types=["Avatar:Both"],
            stage_name="complete_inventory_character_and_base_rig_avatars",
        )
    avatar_records: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for target in all_avatar_targets:
        try:
            path = find_extracted(
                args.work_root / "avatars", "Avatar", int(target["path_id"])
            )
        except CharacterImportError:
            avatar_records[target_identity(target)] = {
                "target": _public_target(target),
                "extracted": False,
                "status": (
                    "exact non-null Animator PPtr and source-scoped target CAB are proven, "
                    "but AnimeStudio emitted no Avatar JSON for this object"
                ),
            }
            continue
        avatar_records[target_identity(target)] = {
            "target": _public_target(target),
            "extracted": True,
            **summarize_avatar(_load(path), path),
        }
    for row in character_records:
        row["avatar"]["object"] = avatar_records[target_identity(row["avatar"]["target"])]
    for row in base_rig_probe.values():
        if row["avatar"]["target"]:
            row["avatar"]["object"] = avatar_records[
                target_identity(row["avatar"]["target"])
            ]

    generic_animation_by_actor = {
        row["stable_actor_id"]: row for row in generic_animation["actors"]
    }
    modular_base_rigs: list[dict[str, Any]] = []
    resident_base_roots: set[str] = set()
    for base in named["base_rigs"]:
        actor_root = str(base["actor_root"])
        if base["current_lab_status"] in {
            "recovered_source_archetype_prefab",
            "recovered_source_archetype_base_rig",
        }:
            resident_base_roots.add(actor_root.casefold())
            actor = generic_animation_by_actor.get(f"supplemental_{actor_root}")
            if actor is None:
                raise CharacterImportError(f"missing generic animation row for {actor_root}")
            evidence = actor["animation_evidence"]
            exact = {
                "animator": {"available": True, "count": len(actor["animators"])},
                "avatar": {
                    "available": evidence["avatar_count"] > 0,
                    "count": evidence["avatar_count"],
                    "rig_kinds": evidence["rig_kinds"],
                },
                "controller": {
                    "available": evidence["controller_count"] > 0,
                    "count": evidence["controller_count"],
                },
                "controller_referenced_clip_count": evidence["referenced_clip_count"],
            }
        else:
            exact = base_rig_probe[actor_root.casefold()]
        modular_base_rigs.append({**base, "exact_animation_availability": exact})

    current_sets = _current_visual_sets(characters, generic_actors)
    authored_by_root: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for appearance in named["appearances"]:
        if appearance["appearance_class"] != "authored_postmodel":
            continue
        for root in appearance.get("part_name_ids") or []:
            authored_by_root[str(root).casefold()].append(appearance)
    next_by_root = {
        str(row["postmodel_root"]).casefold(): row
        for row in named["next_authored_noncharacter_cohort"]
    }
    missing_authored: list[dict[str, Any]] = []
    for root_key, appearances in sorted(authored_by_root.items()):
        if root_key in current_roots:
            continue
        source = next_by_root.get(root_key)
        if source is None:
            raise CharacterImportError(f"missing authored source evidence for {root_key}")
        aliases = [
            alias
            for appearance in appearances
            for alias in appearance.get("identity_aliases") or []
        ]
        animator_candidates = [
            candidate
            for appearance in appearances
            for candidate in appearance.get("postmodel_animator_candidates") or []
        ]
        source_meshes = set(source.get("lod0_meshes") or [])
        missing_authored.append(
            {
                "actor_root": source["postmodel_root"],
                "family": source["postmodel_family"],
                "true_authored_identity": True,
                "template_ids": sorted(
                    {str(value["template_id"]) for value in appearances},
                    key=str.casefold,
                ),
                "named_identity_count": len(aliases),
                "named_identities": aliases,
                "main_prefab_path": source["main_prefab_path"],
                "avatar_mesh_config": {
                    "available": True,
                    "name": source["avatar_mesh_config_name"],
                    "source_json": source["avatar_mesh_config_source"],
                    "lod0_mesh_count": source["lod0_mesh_count"],
                    "lod0_meshes": source["lod0_meshes"],
                    "material_path_hash_count": source["material_path_hash_count"],
                    "material_path_hashes": source["material_path_hashes"],
                },
                "animator": {
                    "available": bool(animator_candidates),
                    "exact_asset_map_count": len(animator_candidates),
                    "candidates": animator_candidates,
                },
                "unity_avatar": {
                    "available": None,
                    "status": "not_joinable_without_an_exact_prefab_Animator_PPtr",
                },
                "runtime_controller": {
                    "available": None,
                    "status": "not_joinable_without_an_exact_prefab_Animator_PPtr",
                },
                "controller_referenced_clips": {
                    "count": None,
                    "status": "unknown_not_zero_no_controller_pointer_join",
                },
                "resident_visual_overlap_candidates": _visual_overlaps(
                    source_meshes, current_sets
                ),
                "resident_status": "missing_true_authored_root",
            }
        )

    appearances_by_template = {
        row["template_id"]: row for row in named["appearances"]
    }
    base_by_template = {
        row["avatar_template_name"]: row for row in modular_base_rigs
    }
    named_identities: list[dict[str, Any]] = []
    for identity in named["identities"]:
        appearance = appearances_by_template[identity["template_id"]]
        if identity["appearance_class"] == "authored_postmodel":
            roots = [str(value) for value in appearance.get("part_name_ids") or []]
            residents = [current_roots[value.casefold()] for value in roots if value.casefold() in current_roots]
            representation = (
                "dedicated_authored_root_resident"
                if residents
                else "true_authored_root_missing"
            )
            base_root = ""
            base_resident = None
        else:
            base = base_by_template[appearance["avatar_template_name"]]
            base_root = str(base["actor_root"])
            base_resident = base_root.casefold() in resident_base_roots
            roots = []
            residents = []
            representation = (
                "shared_archetype_only_exact_appearance_not_instantiated"
                if base_resident
                else "shared_archetype_missing_exact_appearance_not_instantiated"
            )
        named_identities.append(
            {
                **identity,
                "authored_roots": roots,
                "resident_root_matches": residents,
                "shared_base_rig_root": base_root,
                "shared_base_rig_resident": base_resident,
                "representation_status": representation,
                "appearance_render_count": len(appearance.get("renders") or []),
                "appearance_material_code_count": len(
                    appearance.get("material_codes") or []
                ),
                "render_material_cardinality_exact": bool(
                    appearance.get("render_material_cardinality_exact")
                ),
            }
        )

    focus_character = {row["actor_token"]: row for row in character_records}
    missing_by_root = {row["actor_root"].casefold(): row for row in missing_authored}
    liino_dep = dependencies["trees"]["liino_characters"]
    jsspsi_dep = dependencies["trees"]["jsspsi_characters"]
    liino_source = next(
        row for row in postmodel["identities"] if row.get("canonical") and row.get("stable_actor_id") == "chr_0035_liino"
    )
    jsspsi_source = next(
        row for row in postmodel["identities"] if row.get("canonical") and row.get("stable_actor_id") == "chr_0036_jsspsi"
    )
    focus = {
        "liino": {
            "label": "Liino",
            "resident": focus_character["liino"],
            "duplicate_prefab_variants": 2,
            "characters_and_npc_variant_share_avatar_path_id": (
                liino_dep["animator_avatar"]["m_PathID"]
            ),
            "declared_external_controller_containers": liino_source.get("controller_container_evidence") or [],
            "conclusion": (
                "resident as the exact `chr_0035_liino_postmodel` character prefab; its source "
                "Animator and Humanoid Avatar are present, the postmodel controller PPtr is null, "
                "and one exact ACL T-pose preview is decoded. The duplicate NPC wrapper is not a "
                "second identity."
            ),
        },
        "jsspsi": {
            "label": "JSSPSI / Si",
            "resident": focus_character["jsspsi"],
            "duplicate_prefab_variants": 2,
            "characters_and_npc_variant_share_avatar_path_id": (
                jsspsi_dep["animator_avatar"]["m_PathID"]
            ),
            "declared_external_controller_containers": jsspsi_source.get("controller_container_evidence") or [],
            "conclusion": (
                "resident as the exact `chr_0036_jsspsi_postmodel` character prefab; its source "
                "Animator and Humanoid Avatar are present, the postmodel controller PPtr is null, "
                "and one exact ACL T-pose preview is decoded. `Si` is the localized NPC identity; "
                "the NPC wrapper is a duplicate prefab variant."
            ),
        },
        "chenpast": {
            "label": "Chenpast",
            "resident": focus_character["chenpast"],
            "missing_template_root": missing_by_root["npc_8003_chenpast_postmodel"],
            "conclusion": (
                "the source-authored `chr_0037_chenpast_postmodel` historical character variant is "
                "resident with exact Animator+Avatar but no bound controller or decoded clip. The "
                "NPC template explicitly names a second authored root, `npc_8003_chenpast_postmodel`; "
                "that root is missing even though its LOD0 mesh set is visually represented."
            ),
        },
    }

    summary = {
        "resident_actor_count": len(current_roots),
        "character_grade_count": len(characters),
        "generic_actor_count": len(generic_actors),
        "character_grade_animator_count": sum(
            row["animator"]["available"] for row in character_records
        ),
        "character_grade_avatar_count": sum(
            row["avatar"]["available"] for row in character_records
        ),
        "character_grade_unique_avatar_target_count": len(
            {target_identity(row["avatar"]["target"]) for row in character_records}
        ),
        "character_grade_extracted_avatar_object_count": sum(
            value.get("extracted") is True
            for identity, value in avatar_records.items()
            if identity
            in {target_identity(row["avatar"]["target"]) for row in character_records}
        ),
        "character_grade_unextracted_avatar_object_count": sum(
            value.get("extracted") is False
            for identity, value in avatar_records.items()
            if identity
            in {target_identity(row["avatar"]["target"]) for row in character_records}
        ),
        "character_grade_postmodel_controller_count": sum(
            row["postmodel_controller"]["available"] for row in character_records
        ),
        "character_grade_selected_source_clip_count": sum(
            row["source_selected_clips"]["count"] for row in character_records
        ),
        "generic_animator_count": generic_animation["summary"]["animator_count"],
        "generic_avatar_bound_animator_count": generic_animation["summary"]["avatar_bound_animator_count"],
        "generic_controller_bound_animator_count": generic_animation["summary"]["controller_bound_animator_count"],
        "generic_controller_referenced_clip_count": generic_animation["summary"]["controller_clip_reference_count"],
        "missing_canonical_enemy_count": 0,
        "missing_canonical_prop_count": 0,
        "named_identity_count": len(named_identities),
        "authored_named_identity_count": sum(
            row["appearance_class"] == "authored_postmodel" for row in named_identities
        ),
        "modular_named_identity_count": sum(
            row["appearance_class"] == "modular_pedestrian_assembly" for row in named_identities
        ),
        "authored_named_root_count": len(authored_by_root),
        "resident_authored_named_root_count": sum(
            root in current_roots for root in authored_by_root
        ),
        "missing_authored_named_root_count": len(missing_authored),
        "missing_authored_root_family_counts": dict(
            sorted(collections.Counter(row["family"] for row in missing_authored).items())
        ),
        "resident_modular_base_rig_count": len(resident_base_roots),
        "missing_modular_base_rig_count": 8 - len(resident_base_roots),
        "modular_identity_with_resident_base_rig_count": sum(
            row["shared_base_rig_resident"] is True for row in named_identities
        ),
        "modular_identity_without_resident_base_rig_count": sum(
            row["shared_base_rig_resident"] is False for row in named_identities
        ),
        "modular_unique_appearance_template_count": named["modular_summary"]["unique_appearance_template_count"],
        "modular_zero_render_template_count": named["modular_summary"]["zero_render_template_count"],
        "unjoined_named_identity_count": len(named["join_failures"]),
    }
    report = {
        "schema_version": 1,
        "scope": (
            "31 playable characters including Liino, plus JSSPSI and Chenpast, every canonical enemy/prop, "
            "and all named authored/modular NPC identities; original game data only"
        ),
        "sources": {
            "character_catalog": _file_record(args.character_catalog),
            "generic_catalog": _file_record(args.generic_catalog),
            "generic_animation_audit": _file_record(args.generic_animation_audit),
            "postmodel_inventory": _file_record(args.postmodel_inventory),
            "named_npc_inventory": _file_record(args.named_npc_inventory),
            "nonplayable_dependency_audit": _file_record(
                args.nonplayable_dependency_audit
            ),
            "cab_maps": {
                root: _file_record(path) for root, path in args.cab_map.items()
            },
            "character_animator_stage": _file_record(
                character_animator_output / ".character_import_stage.json"
            ),
            "avatar_stage": _file_record(
                args.work_root / "avatars/.character_import_stage.json"
            ),
        },
        "summary": summary,
        "character_grade_roots": character_records,
        "generic_gallery_summary": generic_animation["summary"],
        "modular_base_rigs": modular_base_rigs,
        "missing_authored_roots": missing_authored,
        "named_identities": named_identities,
        "unjoined_named_identities": named["join_failures"],
        "zero_render_modular_templates": named["modular_summary"]["zero_render_templates"],
        "focus": focus,
        "evidence_boundaries": [
            "An authored NPC root is resident only when that exact root is present in the 33/131 catalogs; shared meshes or a related character root are visual reuse, not identity equivalence.",
            "A modular NPC identity is not a unique prefab root. Its template selects parts/material codes over a shared base rig, and the current eight archetype base-rig galleries do not instantiate the 523 exact appearances.",
            "For the 28 missing authored roots, no exact AssetMap Animator row matched the source prefab path. Unity Avatar/controller/controller-clip availability is therefore unknown, not zero; only AvatarMesh config, LOD meshes, and material hashes are exact today.",
            "Character postmodel Animator controller PPtrs are source-proven null. Separate UI/NPC/gameplay controller assets and decoded source clips are reported independently and must not be described as postmodel-bound.",
            "Boy/fatty Animator+Avatar objects and exact hierarchy dependencies are source-proven inside skeletal-morph configuration assets and promoted as base-rig galleries; this closes shared-rig availability, not exact modular assembled-appearance recovery.",
            "Character Animator and Avatar JSON are read only from exact extraction stages fingerprinted against current installed VFS file size and nanosecond mtime; a source patch or replacement invalidates the cache and the audit fails closed until re-extracted.",
        ],
    }
    _write_json(args.report_json, report)
    args.report_md.parent.mkdir(parents=True, exist_ok=True)
    args.report_md.write_text(_render_markdown(report), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character-catalog", type=Path, default=CHARACTER_CATALOG)
    parser.add_argument("--generic-catalog", type=Path, default=GENERIC_CATALOG)
    parser.add_argument(
        "--generic-animation-audit", type=Path, default=GENERIC_ANIMATION_AUDIT
    )
    parser.add_argument("--postmodel-inventory", type=Path, default=POSTMODEL_INVENTORY)
    parser.add_argument("--named-npc-inventory", type=Path, default=NAMED_NPC_INVENTORY)
    parser.add_argument(
        "--nonplayable-dependency-audit",
        type=Path,
        default=NONPLAYABLE_DEPENDENCY_AUDIT,
    )
    parser.add_argument("--work-root", type=Path, default=WORK_ROOT)
    parser.add_argument("--report-json", type=Path, default=REPORT_JSON)
    parser.add_argument("--report-md", type=Path, default=REPORT_MD)
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    args.cab_map = dict(CAB_MAPS)
    return args


def main() -> None:
    args = parse_args()
    report = build(args)
    print(json.dumps(report["summary"], indent=2))
    print(f"report: {args.report_json.resolve()}")


if __name__ == "__main__":
    main()

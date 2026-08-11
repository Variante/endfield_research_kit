#!/usr/bin/env python3
"""Audit source Mesh identity through all generated playable-character assets."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from playable_roster import catalog_character_rows


LAB_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = (
    LAB_ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "Characters"
    / "Catalog"
    / "playable_character_ui_catalog.json"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def generated_root(manifest_path: Path) -> Path:
    return manifest_path.parent


def highest_quality_lod(mesh: dict[str, Any]) -> bool:
    path = str(mesh.get("path") or "")
    for segment in path.replace("\\", "/").split("/"):
        match = re.fullmatch(r"lod(\d+)", segment, re.IGNORECASE)
        if match:
            return int(match.group(1)) == 0
    match = re.search(r"_lod(\d+)(?:$|_)", str(mesh.get("name") or ""), re.IGNORECASE)
    return match is None or int(match.group(1)) == 0


def source_geometry(mesh: dict[str, Any]) -> tuple[int, list[int]]:
    source_path = Path(str(mesh.get("mesh_json") or ""))
    require(source_path.is_file(), f"source Mesh JSON is missing: {source_path}")
    source = load_json(source_path)
    return (
        int(source["m_VertexCount"]),
        [int(item["indexCount"]) for item in source.get("m_SubMeshes") or []],
    )


def generated_geometry(asset_path: Path) -> tuple[int, list[int]]:
    text = asset_path.read_text(encoding="utf-8")
    vertex_match = re.search(r"^\s*m_VertexCount:\s*(\d+)\s*$", text, re.MULTILINE)
    require(vertex_match is not None, f"generated vertex count is missing: {asset_path}")
    return (
        int(vertex_match.group(1)),
        [int(value) for value in re.findall(r"^\s*indexCount:\s*(\d+)\s*$", text, re.MULTILINE)],
    )


def asset_guid(meta_path: Path) -> str:
    match = re.search(
        r"^guid:\s*([0-9a-f]+)\s*$",
        meta_path.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    require(match is not None, f"Unity asset GUID is missing: {meta_path}")
    return match.group(1)


def audit(catalog_path: Path, require_assets: bool, source_only: bool) -> dict[str, Any]:
    characters = catalog_character_rows(catalog_path)

    collisions: list[dict[str, Any]] = []
    characters_result: list[dict[str, Any]] = []
    totals: defaultdict[str, int] = defaultdict(int)

    for character in characters:
        actor = str(character.get("actor_token") or "")
        manifest_asset_path = str(character.get("manifest_asset_path") or "")
        manifest_path = LAB_ROOT / manifest_asset_path
        require(manifest_path.is_file(), f"{actor}: manifest is missing: {manifest_path}")
        manifest = load_json(manifest_path)
        rows = [item for item in manifest.get("meshes") or [] if highest_quality_lod(item)]
        scene_paths = {str(item.get("path") or "") for item in manifest.get("scene_transforms") or []}
        clip_by_name = {
            str(item.get("name") or ""): item for item in manifest.get("clips") or []
        }
        prefab_roots = {
            str(item.get("prop_root") or "")
            for item in ((manifest.get("ui_item_widgets") or {}).get("prefabs") or [])
        }
        # Zhuangfy's piaodai is an exact timeline-owned effect clone rather
        # than a regular ``ui_item_widgets.prefab_entries`` row.  Its
        # recovered_effects contract still supplies the authoritative
        # actor-local root, so include that root in the same ownership set
        # instead of treating the source effect mesh as an orphan.
        recovered_effect_root = str(
            (manifest.get("recovered_effects") or {}).get("effect_root") or ""
        )
        if recovered_effect_root:
            prefab_roots.add(recovered_effect_root)
        private_rows = [item for item in rows if bool(item.get("recovered_prop"))]
        for mesh in private_rows:
            mesh_path = str(mesh.get("path") or "")
            prop_root = str(mesh.get("prop_root_path") or "")
            require(mesh_path in scene_paths, f"{actor}: private mesh path is absent from scene transforms: {mesh_path}")
            require(prop_root in scene_paths, f"{actor}: private prop root is absent from scene transforms: {prop_root}")
            require(prop_root in prefab_roots, f"{actor}: private mesh has no exact source-prefab root: {prop_root}")
            require(mesh_path.startswith(prop_root + "/"), f"{actor}: private mesh escapes its prop root: {mesh_path}")
            for bone_path in mesh.get("bone_paths") or []:
                require(str(bone_path) in scene_paths, f"{actor}: private mesh bone path is missing: {bone_path}")
            root_bone_path = str(mesh.get("root_bone_path") or "")
            if root_bone_path:
                require(root_bone_path in scene_paths, f"{actor}: private root-bone path is missing: {root_bone_path}")

        private_static_rows = [
            item for item in manifest.get("static_props") or []
            if bool(item.get("recovered_prop"))
        ]
        for mesh in private_static_rows:
            mesh_path = str(mesh.get("path") or "")
            prop_root = str(mesh.get("prop_root_path") or "")
            require(mesh_path in scene_paths, f"{actor}: private static-mesh path is absent: {mesh_path}")
            require(prop_root in prefab_roots, f"{actor}: private static mesh has no exact prefab root: {prop_root}")
            require(mesh_path.startswith(prop_root + "/"),
                    f"{actor}: private static mesh escapes its prop root: {mesh_path}")
            require(Path(str(mesh.get("mesh_obj") or "")).is_file(),
                    f"{actor}: private static mesh OBJ is missing: {mesh.get('mesh_obj')}")

        widget_clip_count = 0
        widget_clip_binding_path_count = 0
        for clip in clip_by_name.values():
            prefab_name = str(clip.get("widget_prefab") or "")
            if not prefab_name:
                continue
            widget_clip_count += 1
            prop_root = f"RecoveredProps/{prefab_name}"
            require(prop_root in prefab_roots, f"{actor}: widget clip owner has no private prefab root: {prefab_name}")
            for bone in clip.get("bones") or []:
                path = str(bone.get("path") or "")
                require(path in scene_paths, f"{actor}: widget clip binding path is missing: {path}")
                require(path.startswith(prop_root + "/") or path == prop_root,
                        f"{actor}: widget clip binding escapes {prop_root}: {path}")
                widget_clip_binding_path_count += 1

        visible_prop_path_count = 0
        recovered_state_layer_count = 0
        for state in manifest.get("recovered_states") or []:
            visible_props = {str(path) for path in state.get("visible_props") or []}
            for path in visible_props:
                require(path in prefab_roots, f"{actor}: recovered-state visibility path is not an exact private prefab root: {path}")
                visible_prop_path_count += 1
            for layer in state.get("layers") or []:
                clip_name = str(layer.get("clip") or "")
                require(clip_name in clip_by_name, f"{actor}: recovered-state layer clip is missing: {clip_name}")
                layer_clip = clip_by_name[clip_name]
                layer_prefab = str(layer_clip.get("widget_prefab") or "")
                if layer_prefab:
                    layer_prop_path = f"RecoveredProps/{layer_prefab}"
                else:
                    # A timeline-owned effect clip is not a widget controller
                    # clip.  Its exact prop root is carried by the effect
                    # contract and must still be visible in the same state.
                    effect_root = str(
                        (manifest.get("recovered_effects") or {}).get("effect_root") or ""
                    )
                    require(
                        layer_clip.get("clip_category") == "ui_effect"
                        and str(layer_clip.get("widget_prop_path") or "") == effect_root,
                        f"{actor}: recovered-state layer is not an owned widget/effect clip: {clip_name}",
                    )
                    layer_prop_path = effect_root
                require(layer_prop_path in visible_props,
                        f"{actor}: layer {clip_name} has no matching visible prop path")
                recovered_state_layer_count += 1

        overview_widget_path_count = 0
        for widget in (manifest.get("overview_playback") or {}).get("item_widgets") or []:
            prop_path = str(widget.get("prop_path") or "")
            prefab_name = str(widget.get("prefab") or "")
            require(prop_path == f"RecoveredProps/{prefab_name}",
                    f"{actor}: overview widget path/prefab mismatch: {prop_path} {prefab_name}")
            require(prop_path in prefab_roots, f"{actor}: overview widget path is missing: {prop_path}")
            widget_clips = [str(widget.get(role) or "") for role in ("start_clip", "loop_clip")]
            require(any(widget_clips), f"{actor}: overview widget has no source clip: {prop_path}")
            for role in ("start_clip", "loop_clip"):
                clip_name = str(widget.get(role) or "")
                if not clip_name:
                    continue
                require(clip_name in clip_by_name, f"{actor}: overview widget {role} is missing: {clip_name}")
                clip = clip_by_name[clip_name]
                widget_owner = str(clip.get("widget_prefab") or "")
                effect_owner = str(clip.get("widget_prop_path") or "")
                require(
                    widget_owner == prefab_name
                    or (
                        clip.get("clip_category") == "ui_effect"
                        and effect_owner == prop_path
                    ),
                    f"{actor}: overview widget {role} owner mismatch: {clip_name}",
                )
            overview_widget_path_count += 1
        prefab_path = LAB_ROOT / str(character.get("prefab_asset_path") or "")
        prefab_text = prefab_path.read_text(encoding="utf-8") if prefab_path.is_file() else ""
        mesh_root = generated_root(manifest_path) / "Meshes"

        by_name: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        by_asset_name: defaultdict[str, set[int]] = defaultdict(set)
        for mesh in rows:
            by_name[str(mesh.get("name") or "").casefold()].append(mesh)
            asset_name = str(mesh.get("mesh_asset_name") or mesh.get("name") or "")
            by_asset_name[asset_name.casefold()].add(int(mesh.get("mesh_path_id") or 0))

        for asset_name, path_ids in by_asset_name.items():
            require(
                len(path_ids) <= 1,
                f"{actor}: generated mesh asset {asset_name} aliases source path IDs {sorted(path_ids)}",
            )

        actor_collisions = 0
        for name, group in sorted(by_name.items()):
            path_ids = {int(item.get("mesh_path_id") or 0) for item in group}
            if len(path_ids) <= 1:
                continue
            actor_collisions += 1
            asset_names = [str(item.get("mesh_asset_name") or "") for item in group]
            require(all(asset_names), f"{actor}: collision {name} lacks explicit mesh_asset_name")
            require(
                len({value.casefold() for value in asset_names}) == len(path_ids),
                f"{actor}: collision {name} does not map each path ID to a distinct asset",
            )
            collisions.append(
                {
                    "actor": actor,
                    "authored_name": group[0].get("name"),
                    "renderer_count": len(group),
                    "source_path_ids": sorted(path_ids),
                    "mesh_asset_names": asset_names,
                    "paths": [item.get("path") for item in group],
                    "includes_private_deco": any(bool(item.get("recovered_prop")) for item in group),
                    "private_deco_renderer_count": sum(
                        1 for item in group if bool(item.get("recovered_prop"))
                    ),
                }
            )

        checked_assets: set[str] = set()
        existing_assets = 0
        pending_assets = 0
        prefab_guid_references = 0
        generated_asset_errors: list[str] = []
        for mesh in rows:
            asset_name = str(mesh.get("mesh_asset_name") or mesh.get("name") or "")
            asset_key = asset_name.casefold()
            if asset_key in checked_assets:
                continue
            checked_assets.add(asset_key)
            asset_path = mesh_root / f"{asset_name}.asset"
            meta_path = Path(f"{asset_path}.meta")
            if source_only:
                continue
            if not asset_path.is_file() or not meta_path.is_file():
                pending_assets += 1
                if require_assets:
                    raise AssertionError(f"{actor}: generated mesh asset is missing: {asset_path}")
                continue

            try:
                expected = source_geometry(mesh)
                actual = generated_geometry(asset_path)
                require(actual == expected, f"generated/source geometry differs: {asset_name}")
                existing_assets += 1
                if prefab_text:
                    guid = asset_guid(meta_path)
                    require(guid in prefab_text, f"prefab does not reference mesh asset {asset_name}")
                    prefab_guid_references += 1
            except (AssertionError, OSError, ValueError, KeyError) as exc:
                generated_asset_errors.append(str(exc))
        character_result = {
            "actor": actor,
            "mesh_renderer_count": len(rows),
            "source_mesh_path_id_count": len({int(item.get("mesh_path_id") or 0) for item in rows}),
            "private_deco_mesh_count": len(private_rows),
            "private_deco_static_mesh_count": len(private_static_rows),
            "private_widget_clip_count": widget_clip_count,
            "private_widget_clip_binding_path_count": widget_clip_binding_path_count,
            "recovered_state_visible_prop_path_count": visible_prop_path_count,
            "recovered_state_layer_count": recovered_state_layer_count,
            "overview_widget_path_count": overview_widget_path_count,
            "authored_name_collision_count": actor_collisions,
            "existing_generated_asset_count": existing_assets,
            "pending_generated_asset_count": pending_assets,
            "prefab_guid_reference_count": prefab_guid_references,
            "generated_asset_error_count": len(generated_asset_errors),
        }
        if generated_asset_errors:
            character_result["generated_asset_errors"] = generated_asset_errors
        characters_result.append(character_result)
        for key, value in character_result.items():
            if key != "actor" and isinstance(value, int):
                totals[key] += int(value)

    if source_only:
        status = "source_ok"
    elif totals["generated_asset_error_count"]:
        status = "generated_asset_mismatch"
    elif totals["pending_generated_asset_count"]:
        status = "pending_unity_assets"
    else:
        status = "ok"
    return {
        "status": status,
        "catalog": str(catalog_path.resolve()),
        "character_count": len(characters_result),
        "totals": dict(sorted(totals.items())),
        "collisions": collisions,
        "characters": characters_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--require-assets", action="store_true")
    parser.add_argument(
        "--source-only",
        action="store_true",
        help="Validate manifests, source identities, and exact visibility/binding paths without reading Unity-generated assets",
    )
    parser.add_argument("--json", action="store_true", help="Print the complete JSON payload")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.source_only and args.require_assets:
        parser.error("--source-only and --require-assets cannot be combined")
    try:
        result = audit(args.catalog.resolve(), args.require_assets, args.source_only)
    except (AssertionError, OSError, ValueError, KeyError) as exc:
        if args.json:
            print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        else:
            print("Playable mesh identity: failed")
            print(f"  error={exc}")
        return 1
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    if args.json:
        print(payload, end="")
    else:
        totals = result["totals"]
        print(f"Playable mesh identity: {result['status']}")
        print(
            f"  characters={result['character_count']} renderers={totals['mesh_renderer_count']} "
            f"source-path-ids={totals['source_mesh_path_id_count']} "
            f"private-deco-skinned={totals['private_deco_mesh_count']} "
            f"private-deco-static={totals['private_deco_static_mesh_count']}"
        )
        print(
            f"  collisions={totals['authored_name_collision_count']} "
            f"widget-clips={totals['private_widget_clip_count']} "
            f"widget-binding-paths={totals['private_widget_clip_binding_path_count']}"
        )
        print(
            f"  state-visible-paths={totals['recovered_state_visible_prop_path_count']} "
            f"state-layers={totals['recovered_state_layer_count']} "
            f"overview-widget-paths={totals['overview_widget_path_count']}"
        )
        if not args.source_only:
            print(
                f"  generated-assets={totals['existing_generated_asset_count']} "
                f"pending={totals['pending_generated_asset_count']} "
                f"asset-errors={totals['generated_asset_error_count']} "
                f"prefab-guid-refs={totals['prefab_guid_reference_count']}"
            )
        for collision in result["collisions"]:
            ids = ",".join(str(value) for value in collision["source_path_ids"])
            print(f"  collision {collision['actor']}: {collision['authored_name']} path-ids={ids}")
        if args.output:
            print(f"  report={args.output.resolve()}")
    return 0 if result["status"] in {"ok", "source_ok", "pending_unity_assets"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

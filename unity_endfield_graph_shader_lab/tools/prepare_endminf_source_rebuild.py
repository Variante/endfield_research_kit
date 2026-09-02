#!/usr/bin/env python3
"""Validate local Endminf rebuild inputs and stage its two ACL import jobs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from unity_endfield_graph_shader_lab.tools.build_recovered_acl_clip_data import (  # noqa: E402
    build_contract,
)
from unity_endfield_graph_shader_lab.tools.verify_endminf_overview_effect_stage import (  # noqa: E402
    validate as validate_effect_stage,
)
from scripts.common import check_installed_native_inputs  # noqa: E402


LAB = REPO / "unity_endfield_graph_shader_lab"
MANIFEST = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/"
    "endminf_ui_recovery_manifest.json"
)
PROFILE_SOURCE = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/"
    "CharInfoPlayableProfiles/source_profiles.json"
)
CHARACTER_RENDER_PARAMETERS = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters/"
    "character_render_parameters.json"
)
OPERATOR_LIGHTS = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters/"
    "operator_lights.json"
)
BACKGROUND_PORTRAIT_MANIFEST = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/"
    "CharInfoBackgroundPortrait/source_manifest.json"
)
EFFECT_LOD_ACTIVATION_CONTRACT = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/"
    "endminf_effect_lod_activation_contract.json"
)
EFFECT_LOD_ACTIVATION_CONTRACT_SHA256 = (
    "bde2fcd48a7562610933d19698445d94aa558dfe7dfcfedfccc57c701f8a427b"
)
EFFECT_LOD_NATIVE_HASHES = {
    "gameAssembly": "c24495e51b406f03b03890c4788ee618ae022c991405be5d5b8b787cb775ae89",
    "metadata": "0076743397acadf03d3b0064343a963c7c88863b8160526d397e4b3efb96f02e",
}
EFFECT_ANIMATION_CONTRACT = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/"
    "endminf_effect_animation_source_curve_contract.json"
)
EFFECT_ANIMATION_CONTRACT_SHA256 = (
    "ba01b72a7d476b7b8d0e16b806c9e18d8ac07b623d1951f4f0e53f55f5649d1d"
)
SUIKUAI_MATERIAL_SOURCE = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/"
    "CharInfoPresentation/Materials/"
    "M_fx_common_teleport_03_p19E6A2A7AE736DA5.raw.json"
)
SUIKUAI_MATERIAL_SHA256 = (
    "8309e72e17d9fe1cc44a8ba1bd81ab39535db679c2899c29996cc4fd189d39c5"
)
EFFECT_STAGE = (
    LAB
    / "scratch/character_recovery/endminf_external_fx_rig/"
    "exact_four_root_stage"
)
EFFECT_CLOSURE = (
    LAB
    / "scratch/character_recovery/endminf_external_fx_rig/"
    "exact_four_root_closure.json"
)
MATERIAL_SOURCE = (
    REPO
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
    "json_by_type/Material"
)
MESH_SOURCE = (
    REPO
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
    "convert_by_type/Mesh"
)
TEXTURE_SOURCE = (
    REPO
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/"
    "convert_by_type/Texture2D"
)
DEFAULT_OUTPUT = LAB / "tmp/character_recovery/endminf_source_rebuild"
TARGET_CLIPS = (
    "A_actor_endminf_ui_overview_start",
    "A_actor_endminf_ui_overview_loop",
)
EXPECTED_PROFILE_COUNT = 31
ACL_ASSET_ROOT = (
    "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/"
    "Animations/ACL"
)


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def load_json(path: Path) -> dict:
    require(path.is_file(), f"missing JSON input: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def resolve_repo_path(value: object, owner: Path) -> Path:
    text = str(value or "")
    require(bool(text), f"missing path in {owner}")
    path = Path(text)
    return path if path.is_absolute() else REPO / path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_text_sha256(path: Path) -> str:
    payload = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_effect_lod_activation_contract(
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, int]:
    require(
        EFFECT_LOD_ACTIVATION_CONTRACT.is_file()
        and canonical_text_sha256(EFFECT_LOD_ACTIVATION_CONTRACT)
        == EFFECT_LOD_ACTIVATION_CONTRACT_SHA256,
        "Endminf effect LOD activation contract hash drifted: "
        f"{EFFECT_LOD_ACTIVATION_CONTRACT}",
    )
    payload = load_json(EFFECT_LOD_ACTIVATION_CONTRACT)
    defaults = payload.get("runtimeDefaults") or {}
    native = payload.get("nativeEvidence") or {}
    owners = native.get("setAllTargetLayersCallerOwners") or []
    require(
        payload.get("schema") == "endfield.endminf-effect-lod-activation.v1"
        and payload.get("status") == "source_closed_normal_creation_defaults"
        and defaults == {
            "qualitySettingLodLevel": 8,
            "qualityNormalizationDomain": [1, 2, 4, 8],
            "targetLayers": 1,
        },
        "Endminf effect LOD runtime defaults/normalization drifted",
    )
    require(
        native.get("gameAssemblySha256") == EFFECT_LOD_NATIVE_HASHES["gameAssembly"]
        and native.get("globalMetadataSha256") == EFFECT_LOD_NATIVE_HASHES["metadata"]
        and native.get("recordedInstalledIfixNonreplacement") is True
        and native.get("normalCreationRouteDirectCallerExcluded") is True,
        "Endminf effect LOD native evidence/default route gate drifted",
    )
    owner_keys = {
        str((row.get("owner") or {}).get("key")) for row in owners
        if isinstance(row, dict)
    }
    require(
        owner_keys == {
            "battle_normal_refresh_guard_lod_alpha",
            "battle_normal_refresh_tower_lod",
        },
        f"Endminf SetAllTargetLayers caller ownership drifted: {sorted(owner_keys)}",
    )
    installed = check_installed_native_inputs(
        EFFECT_LOD_NATIVE_HASHES["gameAssembly"],
        EFFECT_LOD_NATIVE_HASHES["metadata"],
        gameassembly=gameassembly,
        metadata=metadata,
    )
    require(
        installed.validated,
        f"Endminf effect LOD native inputs failed closed ({installed.status}): "
        f"{installed.detail}",
    )
    rows = payload.get("rows") or []
    require(
        len(rows) == 101 and all(row.get("authoredInitialActive") is True for row in rows),
        "Endminf effect LOD authored-active row census drifted",
    )
    return {"rows": len(rows), "callerOwners": len(owners)}


def validate_profile_inputs() -> int:
    payload = load_json(PROFILE_SOURCE)
    render_parameters = load_json(CHARACTER_RENDER_PARAMETERS)
    operator_lights = load_json(OPERATOR_LIGHTS)
    rows = payload.get("characters")
    declared = int(payload.get("character_count") or 0)
    require(
        payload.get("schema") == "endfield.playable-charinfo-presentation-profiles.v1"
        and (payload.get("validation") or {}).get("ok") is True,
        f"playable CharInfo profile contract failed closed: {PROFILE_SOURCE}",
    )
    require(
        isinstance(rows, list)
        and declared == EXPECTED_PROFILE_COUNT
        and len(rows) == EXPECTED_PROFILE_COUNT,
        "playable CharInfo profile count is incomplete: "
        f"expected {EXPECTED_PROFILE_COUNT}, declared {declared}, "
        f"found {len(rows) if isinstance(rows, list) else 'non-list'}",
    )
    require(
        render_parameters.get("schema")
        == "endfield.original-character-render-parameters.v1"
        and (render_parameters.get("validation") or {}).get("ok") is True,
        f"character render-parameter contract failed closed: {CHARACTER_RENDER_PARAMETERS}",
    )
    require(
        operator_lights.get("schema") == "endfield.original-operator-lights.v1"
        and (operator_lights.get("validation") or {}).get("ok") is True,
        f"operator-light contract failed closed: {OPERATOR_LIGHTS}",
    )
    render_actors = render_parameters.get("characters") or {}
    light_actors = operator_lights.get("actors") or {}
    actor_tokens = [str(row.get("actor_token") or "").strip() for row in rows]
    root_names = [str(row.get("root_name") or "").strip() for row in rows]
    require(
        all(actor_tokens)
        and len({value.casefold() for value in actor_tokens})
        == EXPECTED_PROFILE_COUNT
        and all(root_names)
        and len({value.casefold() for value in root_names})
        == EXPECTED_PROFILE_COUNT,
        "playable CharInfo profile actor/root identities are empty or duplicated",
    )
    for row in rows:
        root_name = str(row.get("root_name") or "<unnamed>")
        actor_token = str(row.get("actor_token") or "")
        render_actor = render_actors.get(actor_token) or {}
        light_actor = light_actors.get(actor_token) or {}
        require(
            len(render_actor.get("modifier_serialized_parameters") or {}) == 30
            and bool(
                render_actor.get("post_use_data_on_volume")
                or render_actor.get("resolved_active_overrides")
            ),
            f"{root_name} character render parameters are incomplete",
        )
        require(
            bool(light_actor.get("lights")),
            f"{root_name} overview operator-light rows are missing",
        )
        texture = ((row.get("portrait") or {}).get("texture_png") or {})
        source = resolve_repo_path(texture.get("path"), PROFILE_SOURCE)
        expected = str(texture.get("sha256") or "").lower()
        require(source.is_file(), f"{root_name} portrait PNG is missing: {source}")
        require(
            len(expected) == 64 and sha256(source) == expected,
            f"{root_name} portrait PNG hash drifted: {source}",
        )
    return declared


def validate_background_portrait_manifest() -> int:
    payload = load_json(BACKGROUND_PORTRAIT_MANIFEST)
    actors = payload.get("actors") or {}
    require(
        payload.get("schema") == "endfield.charinfo.background-portrait.original-data.v1"
        and set(actors) == {"Wulfa", "Zhuangfy"},
        f"legacy CharInfo background-portrait source manifest drifted: "
        f"{BACKGROUND_PORTRAIT_MANIFEST}",
    )
    for actor, row in actors.items():
        source = resolve_repo_path(row.get("source_texture_png"), BACKGROUND_PORTRAIT_MANIFEST)
        expected = str(row.get("source_texture_png_sha256") or "").lower()
        require(source.is_file(), f"{actor} background portrait PNG is missing: {source}")
        require(
            len(expected) == 64 and sha256(source) == expected,
            f"{actor} background portrait PNG hash drifted: {source}",
        )
    return len(actors)


def validate_effect_dependency_closure() -> dict[str, int]:
    stage_result = validate_effect_stage(EFFECT_STAGE, EFFECT_CLOSURE)
    require(
        EFFECT_ANIMATION_CONTRACT.is_file()
        and canonical_text_sha256(EFFECT_ANIMATION_CONTRACT)
        == EFFECT_ANIMATION_CONTRACT_SHA256,
        f"Endminf effect animation semantic contract drifted: {EFFECT_ANIMATION_CONTRACT}",
    )
    require(
        SUIKUAI_MATERIAL_SOURCE.is_file()
        and canonical_text_sha256(SUIKUAI_MATERIAL_SOURCE)
        == SUIKUAI_MATERIAL_SHA256,
        f"Endminf suikuai source material drifted: {SUIKUAI_MATERIAL_SOURCE}",
    )
    closure = load_json(EFFECT_CLOSURE)
    roots = {
        "Material": (MATERIAL_SOURCE, ".json"),
        "Mesh": (MESH_SOURCE, ".obj"),
        "Texture2D": (TEXTURE_SOURCE, ".png"),
    }
    counts = {name: 0 for name in roots}
    material_paths: list[Path] = []
    for target_type, (root, suffix) in roots.items():
        require(root.is_dir(), f"missing {target_type} export root: {root}")
        for row in closure.get("identities") or []:
            if row.get("targetType") != target_type or row.get("status") != "resolved":
                continue
            path_id_hex = str(row.get("pathIdHex") or "").upper()
            require(len(path_id_hex) == 16, f"malformed {target_type} PathID in closure")
            matches = list(root.glob(f"*_p{path_id_hex}{suffix}"))
            require(
                len(matches) == 1,
                f"{target_type} p{path_id_hex} expected one exported source, "
                f"found {len(matches)} under {root}",
            )
            if target_type == "Material":
                material_paths.append(matches[0])
            counts[target_type] += 1
    require(
        counts == {"Material": 39, "Mesh": 12, "Texture2D": 1},
        f"render dependency closure census drifted: {counts}",
    )
    texture_ids: set[int] = set()
    for material_path in material_paths:
        material = load_json(material_path)
        saved = material.get("m_SavedProperties") or {}
        texture_environments = saved.get("m_TexEnvs") or {}
        require(
            isinstance(texture_environments, dict),
            f"material texture environment is malformed: {material_path}",
        )
        for row in texture_environments.values():
            texture = row.get("m_Texture") if isinstance(row, dict) else None
            path_id = int((texture or {}).get("m_PathID") or 0)
            if path_id:
                texture_ids.add(path_id & ((1 << 64) - 1))
    for path_id in sorted(texture_ids):
        path_id_hex = f"{path_id:016X}"
        matches = list(TEXTURE_SOURCE.glob(f"*_p{path_id_hex}.png"))
        require(
            len(matches) == 1,
            f"material Texture2D p{path_id_hex} expected one decoded source, "
            f"found {len(matches)} under {TEXTURE_SOURCE}",
        )
    require(
        len(texture_ids) == 44,
        f"material texture dependency census drifted: {len(texture_ids)}",
    )
    counts["MaterialTexture"] = len(texture_ids)
    return {**counts, **stage_result}


def build_acl_jobs(output_root: Path, write: bool) -> list[dict[str, str]]:
    manifest = load_json(MANIFEST)
    require(
        manifest.get("character_id") == "chr_0003_endminf",
        f"Endminf character identity drifted: {MANIFEST}",
    )
    clips = manifest.get("clips")
    require(isinstance(clips, list) and clips, "Endminf manifest contains no clips")
    missing_samples = []
    for row in clips:
        sample_text = str(row.get("sample_json") or "")
        if not sample_text or not resolve_repo_path(sample_text, MANIFEST).is_file():
            missing_samples.append(str(row.get("name") or "<unnamed>"))
    require(
        not missing_samples,
        "Endminf source animation samples are missing: " + ", ".join(missing_samples),
    )

    jobs: list[dict[str, str]] = []
    for clip_name in TARGET_CLIPS:
        matches = [row for row in clips if row.get("name") == clip_name]
        require(len(matches) == 1, f"expected one Endminf clip row: {clip_name}")
        sample_path = resolve_repo_path(matches[0].get("sample_json"), MANIFEST)
        sample = load_json(sample_path)
        clip_path = resolve_repo_path(sample.get("source_json"), sample_path)
        contract = build_contract(clip_path, sample_path, MANIFEST)
        require(
            contract.get("sourceClipName") == clip_name,
            f"ACL contract identity drifted: {clip_name}",
        )
        contract_path = output_root / f"{clip_name}.runtime.json"
        if write:
            output_root.mkdir(parents=True, exist_ok=True)
            contract_path.write_text(
                json.dumps(contract, indent=2) + "\n", encoding="utf-8"
            )
        jobs.append(
            {
                "contractJson": str(contract_path.resolve()),
                "assetPath": f"{ACL_ASSET_ROOT}/{clip_name}.asset",
            }
        )
    return jobs


def prepare(output_root: Path, write: bool = True,
            gameassembly: Path | None = None,
            metadata: Path | None = None) -> dict:
    # This gate must run before build_acl_jobs can create or replace any file;
    # the batch invokes this process before it launches Unity/BuildActor.
    lod_activation = validate_effect_lod_activation_contract(gameassembly, metadata)
    profiles = validate_profile_inputs()
    background_portraits = validate_background_portrait_manifest()
    effects = validate_effect_dependency_closure()
    jobs = build_acl_jobs(output_root.resolve(), write)
    job_path = output_root.resolve() / "acl_import_job.json"
    if write:
        job_path.write_text(json.dumps({"items": jobs}, indent=2) + "\n", encoding="utf-8")
    return {
        "effectLodActivationRows": lod_activation["rows"],
        "effectLodTargetLayerCallerOwners": lod_activation["callerOwners"],
        "profiles": profiles,
        "backgroundPortraits": background_portraits,
        "effectRoots": effects["roots"],
        "effectHierarchyNodes": effects["hierarchyNodes"],
        "materials": effects["Material"],
        "meshes": effects["Mesh"],
        "textures": effects["Texture2D"],
        "materialTextures": effects["MaterialTexture"],
        "aclClips": len(jobs),
        "job": str(job_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="validate without writing ACL jobs")
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    args = parser.parse_args()
    result = prepare(
        args.output_root, write=not args.check,
        gameassembly=args.gameassembly, metadata=args.metadata,
    )
    print("prepare_endminf_source_rebuild: OK " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

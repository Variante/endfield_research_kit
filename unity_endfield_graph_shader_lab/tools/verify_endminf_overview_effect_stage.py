#!/usr/bin/env python3
"""Fail-closed validation for the four behavior-owned Endminf Overview effects."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STAGE = ROOT / "unity_endfield_graph_shader_lab/scratch/character_recovery/endminf_external_fx_rig/exact_four_root_stage"
DEFAULT_CLOSURE = (
    ROOT
    / "unity_endfield_graph_shader_lab/scratch/character_recovery/endminf_external_fx_rig/exact_four_root_closure.json"
)
IMPORTER = (
    ROOT
    / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/EndfieldEndminfOverviewEffectImporter.cs"
)
CAPTURE = (
    ROOT
    / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/EndfieldEndminfViewerPlayModeCapture.cs"
)
SPAWNER = (
    ROOT
    / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
    "EndfieldRecoveredCharEffectSpawner.cs"
)
LITEFFECT_BINDING_BUILDER = (
    ROOT
    / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldEndminfLitEffectCompatibilityBindingBuilder.cs"
)
M27_ABI_PROBE = (
    ROOT
    / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldEndminfM27ParticleAbiProbe.cs"
)
BLOCKED_CENSUS = (
    ROOT
    / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldEndminfBlockedRendererCensus.cs"
)

ROOTS = {
    "P_fxui_endminm003_overview_01": (644358100928130169, 772927267),
    "P_fxui_endminm003_overview_02": (7701914037140635122, 373845082),
    "P_fxui_endminm003_overview_03": (6277198576094749248, 67616247),
    "P_fxui_endminm003_overview_04": (-3166230417407544182, 241640789),
}
ROOT_TRANSFORMS = {
    "P_fxui_endminm003_overview_01": 8425642429156191353,
    "P_fxui_endminm003_overview_02": 8369328719590309362,
    "P_fxui_endminm003_overview_03": -7537240925946174912,
    "P_fxui_endminm003_overview_04": 2872757505452405898,
}
ROOT_COUNTS = {
    "P_fxui_endminm003_overview_01": (58, 33),
    "P_fxui_endminm003_overview_02": (20, 18),
    "P_fxui_endminm003_overview_03": (8, 6),
    "P_fxui_endminm003_overview_04": (15, 13),
}
CLIPS = {
    "A_fx_endminf_ui_overview_02": (8413816528141668220, 772927267),
    "A_fx_endminf_ui_overview_03": (8378992340436559080, 373845082),
    "A_fx_endminf_ui_overview_04": (-2625895420410042749, 772927267),
    "A_actor_endminf_ui_overview_02": (-7994037904239017215, 937624865),
}
STAGE_FINGERPRINT = "130cf736dcc4c4f031e9a4f15521157e90bc7fed9085b9354cc61748f6249ea3"
STAGE_CONTENT_SHA256 = "873f17793284de92f7680448b7efe282b73cbaea85522297e3f412e49508d302"
STAGE_CONTENT_TYPES = (
    "GameObject", "Transform", "ParticleSystem",
    "ParticleSystemRenderer", "MonoBehaviour", "AnimationClip",
)
SHAPE_TEXTURE_PATH_ID = 6970530313307194154
SHAPE_TEXTURE_SHA256 = "8eeab0f7fad4e618db4d033180c5bee70aee6f9229a19566cd6bbba513b3d1eb"
SHAPE_TEXTURE = (
    ROOT / "export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Texture2D/"
    "T_fx_flow_121_M_p60BC4C6374C4832A.png"
)


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def load(path: Path) -> dict:
    require(path.is_file(), f"missing JSON: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def metadata(path: Path) -> tuple[str, int]:
    value = load(path)
    source = value.get("$animestudio") or {}
    encoded = path.stem.rsplit("_p", 1)[-1]
    unsigned = int(encoded, 16)
    filename_path_id = unsigned if unsigned < (1 << 63) else unsigned - (1 << 64)
    return (
        str(value.get("m_Name") or value.get("Name") or ""),
        int(source.get("pathId") or filename_path_id),
    )


def pptr_id(value: object) -> int:
    return int(value.get("m_PathID", 0)) if isinstance(value, dict) else 0


def objects_by_path_id(stage: Path, type_name: str) -> dict[int, dict]:
    result: dict[int, dict] = {}
    for path in sorted((stage / type_name).glob("*.json")):
        _, path_id = metadata(path)
        require(path_id not in result, f"duplicate {type_name} PathID: {path_id}")
        result[path_id] = load(path)
    return result


def stage_content_sha256(stage: Path) -> str:
    rows: list[str] = []
    for type_name in STAGE_CONTENT_TYPES:
        for path in sorted((stage / type_name).glob("*.json"), key=lambda p: p.name):
            payload = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            rows.append(
                f"{type_name}/{path.name}:"
                f"{hashlib.sha256(payload).hexdigest()}\n"
            )
    return hashlib.sha256("".join(rows).encode("utf-8")).hexdigest()


def validate(stage: Path, closure_path: Path) -> dict:
    require(
        stage_content_sha256(stage) == STAGE_CONTENT_SHA256,
        "exact per-owner stage content drifted",
    )
    report = load(stage / "external_ui_effect_stage.json")
    require(report.get("status") == "ok", "external effect stage is not complete")
    validation = report.get("validation") or {}
    require(validation.get("stage_fingerprint") == STAGE_FINGERPRINT, "stage fingerprint drifted")
    require(report.get("expected_root_count") == 4, "expected root count drifted")
    require(report.get("expected_clip_count") == 1, "expected rig clip count drifted")
    summaries = validation.get("object_index_summaries") or []
    require(len(summaries) == 2 and all(row.get("complete") is True for row in summaries),
            "object index is incomplete")
    for row in summaries:
        counts = row.get("counts") or {}
        require(counts.get("errors") == 0 and counts.get("suppressedErrors") == 0,
                "object index contains errors")

    for type_name, expected in (("GameObject", ROOTS), ("AnimationClip", CLIPS)):
        found: dict[str, int] = {}
        for path in sorted((stage / type_name).glob("*.json")):
            name, path_id = metadata(path)
            if name in expected:
                require(name not in found, f"duplicate exact {type_name}: {name}")
                found[name] = path_id
        require(set(found) == set(expected), f"exact {type_name} set drifted")
        for name, (path_id, _) in expected.items():
            require(found[name] == path_id, f"{type_name} PathID drifted: {name}")

    game_objects = objects_by_path_id(stage, "GameObject")
    transforms = objects_by_path_id(stage, "Transform")
    particles = objects_by_path_id(stage, "ParticleSystem")
    renderers = objects_by_path_id(stage, "ParticleSystemRenderer")
    require(len(game_objects) == 101 and len(transforms) == 101,
            "four-root hierarchy census drifted")
    require(len(particles) == 70 and len(renderers) == 70,
            "four-root particle/renderer census drifted")

    transform_by_game_object: dict[int, int] = {}
    for transform_id, row in transforms.items():
        game_object_id = pptr_id(row.get("m_GameObject"))
        require(game_object_id in game_objects,
                f"Transform {transform_id} lost its staged GameObject")
        require(game_object_id not in transform_by_game_object,
                f"GameObject {game_object_id} has duplicate staged Transforms")
        transform_by_game_object[game_object_id] = transform_id
        father_id = pptr_id(row.get("m_Father"))
        require(father_id == 0 or father_id in transforms,
                f"Transform {transform_id} has an external parent")
    require(set(transform_by_game_object) == set(game_objects),
            "GameObject/Transform closure drifted")

    root_rows = {
        str(game_objects[pptr_id(row.get("m_GameObject"))].get("m_Name") or ""):
        (pptr_id(row.get("m_GameObject")), transform_id)
        for transform_id, row in transforms.items()
        if pptr_id(row.get("m_Father")) == 0
    }
    require(set(root_rows) == set(ROOTS), "serialized effect-root hierarchy drifted")
    for root_name, (game_object_id, transform_id) in root_rows.items():
        require(
            game_object_id == ROOTS[root_name][0] and
            transform_id == ROOT_TRANSFORMS[root_name],
            f"serialized effect-root identity pair drifted: {root_name}",
        )

    root_by_transform: dict[int, str] = {}
    def find_root(transform_id: int) -> str:
        if transform_id in root_by_transform:
            return root_by_transform[transform_id]
        row = transforms[transform_id]
        father = pptr_id(row.get("m_Father"))
        result = (
            str(game_objects[pptr_id(row.get("m_GameObject"))].get("m_Name") or "")
            if father == 0 else find_root(father)
        )
        root_by_transform[transform_id] = result
        return result

    for root_name, (expected_hierarchy, expected_particles) in ROOT_COUNTS.items():
        hierarchy_count = sum(
            1 for transform_id in transforms if find_root(transform_id) == root_name
        )
        particle_count = sum(
            1 for row in particles.values()
            if find_root(transform_by_game_object[pptr_id(row.get("m_GameObject"))]) ==
            root_name
        )
        require(
            (hierarchy_count, particle_count) ==
            (expected_hierarchy, expected_particles),
            f"per-root hierarchy/particle census drifted: {root_name}",
        )

    scaling_modes = [int(row.get("scalingMode", -1)) for row in particles.values()]
    move_with_transform = [bool(row.get("moveWithTransform")) for row in particles.values()]
    shape_pairs = [
        (bool((row.get("ShapeModule") or {}).get("enabled")),
         int((row.get("ShapeModule") or {}).get("type", -1)))
        for row in particles.values()
    ]
    require(scaling_modes.count(1) == 60 and scaling_modes.count(0) == 10,
            "particle scaling-mode census drifted")
    require(move_with_transform.count(True) == 10,
            "particle move-with-transform census drifted")
    require(shape_pairs.count((True, 0)) == 16 and
            shape_pairs.count((True, 4)) == 3,
            "particle shape-module census drifted")
    shape_texture_owners = [
        row for row in particles.values()
        if pptr_id((row.get("ShapeModule") or {}).get("m_Texture")) ==
        SHAPE_TEXTURE_PATH_ID
    ]
    require(len(shape_texture_owners) == 4 and
            all(bool((row.get("ShapeModule") or {}).get("enabled"))
                for row in shape_texture_owners),
            "particle shape-texture ownership drifted")
    require(SHAPE_TEXTURE.is_file() and
            hashlib.sha256(SHAPE_TEXTURE.read_bytes()).hexdigest() ==
            SHAPE_TEXTURE_SHA256,
            "particle shape-texture payload drifted")
    require(all(
        not bool((row.get("LightsModule") or {}).get("enabled")) and
        pptr_id((row.get("LightsModule") or {}).get("light")) == 0
        for row in particles.values()),
        "source particle LightsModule unexpectedly gained a Light owner")

    particle_hosts = [pptr_id(row.get("m_GameObject")) for row in particles.values()]
    renderer_hosts = [pptr_id(row.get("m_GameObject")) for row in renderers.values()]
    require(len(set(particle_hosts)) == 70 and
            set(particle_hosts) == set(renderer_hosts),
            "particle/renderer host ownership drifted")
    material_ids = [
        pptr_id(material)
        for row in renderers.values()
        for material in row.get("m_Materials", [])
    ]
    require(all(bool(row.get("m_Enabled")) for row in renderers.values()),
            "a source particle renderer became disabled")
    require(len(material_ids) == 78 and len(set(material_ids)) == 41 and
            all(material_ids),
            "particle material-owner census drifted")

    closure = load(closure_path)
    require(closure.get("status") == "incomplete_ambiguous", "PPtr closure status drifted")
    identities = closure.get("identities") or []
    ambiguous = [row for row in identities if row.get("status") == "ambiguous"]
    require(ambiguous and all(row.get("targetType") == "MonoScript" for row in ambiguous),
            "non-script PPtr closure became ambiguous")
    require(all(row.get("status") == "resolved" for row in identities
                if row.get("targetType") in {"Material", "Mesh", "Texture2D"}),
            "render dependency closure is incomplete")
    require(not any("overview_06" in path.name for path in (stage / "GameObject").glob("*.json")),
            "obsolete overview_06 root remains staged")
    importer = IMPORTER.read_text(encoding="utf-8")
    capture = CAPTURE.read_text(encoding="utf-8")
    spawner = SPAWNER.read_text(encoding="utf-8")
    liteffect_builder = LITEFFECT_BINDING_BUILDER.read_text(encoding="utf-8")
    m27_abi_probe = M27_ABI_PROBE.read_text(encoding="utf-8")
    blocked_census = BLOCKED_CENSUS.read_text(encoding="utf-8")
    for token in (
        f'ExpectedStageFingerprint =\n            "{STAGE_FINGERPRINT}"',
        f'ExpectedStageContentSha256 =\n            "{STAGE_CONTENT_SHA256}"',
        '"Endminf exact per-owner stage content drifted"',
        '"Endminf exact effect stage provenance drifted"',
        '"Endminf particle transform/scaling-mode census drifted"',
        '"Endminf particle shape-module census drifted"',
        '"Endminf source unexpectedly gained a ParticleSystem Light owner"',
        "EndminfShapeTexture = 6970530313307194154L;",
        f'"{SHAPE_TEXTURE_SHA256}"',
        '"Exact Endminf particle shape texture is unavailable"',
        'ConfigureExactEndminfShapeTexture(shapeTextureAsset);',
        'texture.width == 256 && texture.height == 256',
        'texture.mipmapCount == 9',
        'loaded.filterMode == FilterMode.Bilinear',
        'loaded.anisoLevel == 1',
        'loaded.wrapModeU == TextureWrapMode.Repeat',
        "context.textures[EndminfShapeTexture] = shapeTexture;",
        "marker.sourceHierarchy = hierarchyFor(rootTransformId);",
        "marker.sourceGameObjectPathId = goByTransform[rootTransformId];",
        "marker.sourceTransformPathId = rootTransformId;",
        "marker.hierarchyNodes = generated",
        "hierarchy = hierarchyFor(transformId),",
        "generatedParticleSystem = system,",
        "generatedRenderer = renderer,",
        "resolvedSourceMaterials = materialIds.All(",
        "resolvedSourceMeshes = meshIds.All(context.meshes.ContainsKey)",
        "sourceMoveWithTransform = L.Bool(",
        "VerifyTopLevelDictionary(",
        ".VerifyNamedDictionary(",
        ".TryValidateEndminfV2MarkerForRecoveryAudit(",
        "ValidateMoveWithTransform(row)",
    ):
        require(token in importer, f"Unity stage gate missing {token!r}")
    for token in (
        '"endfield.endminf-overview-particle-stage.v2"',
        "TryGetEndminfOverviewRootContract(",
        "node.generatedParticleSystem",
        "node.generatedRenderer",
        "node.resolvedSourceMaterials",
        "node.resolvedSourceMeshes",
        "sourceLightPathId != 0",
        "shapeTextureOwnerCount != expectedShapeTextureOwners",
    ):
        require(token in spawner, f"Endminf v2 runtime gate missing {token!r}")
    for label, text in (
        ("LitEffect binding builder", liteffect_builder),
        ("M27 ABI probe", m27_abi_probe),
        ("blocked renderer census", blocked_census),
    ):
        require(
            ".generatedRenderer" in text,
            f"{label} does not use the v2 direct renderer reference",
        )
        require(
            "renderers[index]" not in text,
            f"{label} still joins Endminf owners by component-array order",
        )
    require(
        "EndfieldEndminfOverviewEffectImporter.BuildAndValidate();" in capture,
        "targeted/canonical capture does not rebuild the exact effect stage",
    )
    return {
        "roots": len(ROOTS),
        "hierarchyNodes": len(transforms),
        "particleRenderers": len(renderers),
        "materialOwners": len(set(material_ids)),
        "shapeTextureOwners": len(shape_texture_owners),
        "particleLightOwners": 0,
        "stageContentSha256": STAGE_CONTENT_SHA256,
        "clips": len(CLIPS),
        "ambiguousMonoScripts": len(ambiguous),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, default=DEFAULT_STAGE)
    parser.add_argument("--closure", type=Path, default=DEFAULT_CLOSURE)
    args = parser.parse_args()
    result = validate(args.stage.resolve(), args.closure.resolve())
    print("verify_endminf_overview_effect_stage: OK " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

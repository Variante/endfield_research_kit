#!/usr/bin/env python3
"""Verify current installed Eye/brow ForwardLit identity and lab integration."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
ASSET_ROOT = LAB_ROOT / "Assets" / "EndfieldGraphShaderLab"
CONTRACT_PATH = (
    ASSET_ROOT
    / "Generated"
    / "OriginalData"
    / "RenderParameters"
    / "eye_brow_forward_contract.json"
)
PLAYABLE_ROOT = ASSET_ROOT / "Generated" / "Characters" / "Playable"
EYE_SHADER = ASSET_ROOT / "Shaders" / "Recovered" / "EndfieldCharacterEyeRecovered.shader"
IMPORTER = (
    ASSET_ROOT
    / "Editor"
    / "CharacterRecovery"
    / "EndfieldManifestCharacterSetup.cs"
)
EYE_SHADER_GUID = "3eb702bb5e4b91e4886f3379493f2abf"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(payload: dict[str, Any], *, pin_bytes: bool = True) -> Path:
    path = REPO_ROOT / payload["path"]
    if not path.is_file():
        raise AssertionError(f"missing pinned artifact: {path}")
    if pin_bytes:
        if path.stat().st_size != int(payload["size"]):
            raise AssertionError(f"size mismatch: {path}")
        if sha256(path) != payload["sha256"]:
            raise AssertionError(f"SHA-256 mismatch: {path}")
    return path


def require(text: str, token: str, label: str) -> None:
    if token not in text:
        raise AssertionError(f"{label}: missing {token!r}")


def parse_dump(path: Path) -> tuple[list[str], int, list[str]]:
    text = path.read_text(encoding="utf-8")

    def string_array(field: str, next_field: str) -> list[str]:
        match = re.search(
            rf"vector {re.escape(field)}\s+Array Array\s+int size = (\d+)(.*?)"
            rf"(?=\n\t{re.escape(next_field)})",
            text,
            re.S,
        )
        if not match:
            raise AssertionError(f"missing {field}: {path}")
        values = re.findall(r'string data = "([^"]+)"', match.group(2))
        if len(values) != int(match.group(1)):
            raise AssertionError(f"{field} count mismatch: {path}")
        return values

    queue_match = re.search(r"int m_CustomRenderQueue = (-?\d+)", text)
    if not queue_match:
        raise AssertionError(f"missing m_CustomRenderQueue: {path}")
    return (
        string_array("m_ValidKeywords", "vector m_InvalidKeywords"),
        int(queue_match.group(1)),
        string_array("disabledShaderPasses", "UnityPropertySheet m_SavedProperties"),
    )


def verify_variants(contract: dict[str, Any]) -> None:
    expected_sample_counts = {
        "iris_matcap_highlight": {"_33.Sample": 1, "_34.Sample": 1},
        "brow_shadow_lut": {"_33.Sample": 2, "_34.Sample": 1},
        "brow_plain": {"_33.Sample": 1, "_34.Sample": 1},
    }
    for variant_id, variant in contract["variants"].items():
        raw = verify_file(variant["raw_fragment"])
        metadata_path = verify_file(variant["metadata"])
        hlsl_path = verify_file(variant["ruri_hlsl"])
        metadata = load_json(metadata_path)
        if metadata["SourceSubShaderIndex"] != 0 or metadata["SourcePassIndex"] != 0:
            raise AssertionError(f"{variant_id}: not subshader0/pass0")
        if metadata["SourcePassName"] != "ForwardLit":
            raise AssertionError(f"{variant_id}: pass identity mismatch")
        if metadata["SourceCompilerPlatform"] != "d3d11":
            raise AssertionError(f"{variant_id}: compiler platform mismatch")
        if metadata["SourceCompiledKeywords"] != variant["compiled_keywords"]:
            raise AssertionError(f"{variant_id}: compiled keyword mismatch")
        if "HG_ENABLE_SCREEN_SPACE_SHADOW_MASK" not in variant["compiled_keywords"]:
            raise AssertionError(f"{variant_id}: current mandatory screen-mask keyword missing")
        expected_debug = (
            f"subshader0/pass0:ForwardLit/vertex/blob{variant['blob']}/33"
        )
        if metadata["DebugName"] != expected_debug:
            raise AssertionError(f"{variant_id}: blob identity mismatch")
        if raw.read_bytes()[:4] != b"DXBC":
            raise AssertionError(f"{variant_id}: selected fragment is not DXBC")

        texture_names = {entry["Name"] for entry in metadata["TextureParameters"]}
        if "_ScreenSpaceShadowMask" not in texture_names:
            raise AssertionError(f"{variant_id}: screen-mask resource missing")
        hlsl = hlsl_path.read_text(encoding="utf-8")
        require(hlsl, "_23.Load(int3(uint2", f"{variant_id} screen-mask integer load")
        require(hlsl, "SV_Target.w = (asfloat(asuint(", f"{variant_id} alpha select")
        require(hlsl, ") ? _", f"{variant_id} alpha ternary")
        require(hlsl, ": 1.0f;", f"{variant_id} opaque alpha endpoint")
        require(hlsl, "SV_Target_1.z = 1.0f;", f"{variant_id} scene-MV z")
        require(
            hlsl,
            "SV_Target_1.w = 0.4000000059604644775390625f;",
            f"{variant_id} scene-MV w",
        )
        for token, expected in expected_sample_counts[variant_id].items():
            if hlsl.count(token) != expected:
                raise AssertionError(
                    f"{variant_id}: {token} count {hlsl.count(token)} != {expected}"
                )


def verify_materials(contract: dict[str, Any]) -> dict[str, Path]:
    actor_manifests: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(PLAYABLE_ROOT.glob("*/*_ui_recovery_manifest.json")):
        manifest = load_json(path)
        actor_manifests[manifest["actor_token"]] = (path, manifest)
    if len(actor_manifests) != 31:
        raise AssertionError(f"playable manifest count mismatch: {len(actor_manifests)}")

    queue_counts: collections.Counter[int] = collections.Counter()
    depth_counts: collections.Counter[bool] = collections.Counter()
    class_counts: collections.Counter[int] = collections.Counter()
    actor_counts: collections.Counter[str] = collections.Counter()
    generated_paths: dict[str, Path] = {}
    for key, material in contract["materials"].items():
        actor = material["actor"]
        manifest_path, manifest = actor_manifests[actor]
        expected_key = f"pathid_{material['path_id']}"
        if key != expected_key:
            raise AssertionError(f"contract key mismatch: {key} != {expected_key}")
        info = manifest["materials"].get(expected_key)
        if not info:
            raise AssertionError(f"{actor}: missing exact Eye material {expected_key}")
        if info["name"] != material["name"]:
            raise AssertionError(f"{actor}: Eye material name mismatch")
        if info["shader_name"] != "HGRP/CharacterNPR_Eye":
            raise AssertionError(f"{actor}: Eye shader-name mismatch")
        if int(info["shader_path_id"]) != int(material["shader_path_id"]):
            raise AssertionError(f"{actor}: Eye shader PathID mismatch")

        for name, expected in material["required_float_state"].items():
            actual = info["floats"].get(name)
            if actual is None or abs(float(actual) - float(expected)) > 1e-6:
                raise AssertionError(f"{actor}/{material['name']}: float mismatch {name}")
        if set(info["textures"]) != set(material["textures"]):
            raise AssertionError(f"{actor}/{material['name']}: texture set mismatch")
        for name, expected in material["textures"].items():
            actual = info["textures"][name]
            if (
                actual["name"] != expected["name"]
                or int(actual["path_id"]) != int(expected["path_id"])
                or not Path(actual["file"]).is_file()
            ):
                raise AssertionError(f"{actor}/{material['name']}: texture mismatch {name}")

        # AnimeStudio JSON formatting can change when the exporter is updated;
        # validate its current semantic fields below and reserve byte-level
        # pinning for the raw TypeTree dump.
        source_path = verify_file(material["source_json"], pin_bytes=False)
        source = load_json(source_path)
        if source["m_Name"] != material["name"]:
            raise AssertionError(f"{actor}: source material name mismatch")
        if int(source["m_Shader"]["m_PathID"]) != int(material["shader_path_id"]):
            raise AssertionError(f"{actor}: source material Shader PPtr mismatch")
        source_floats = source["m_SavedProperties"]["m_Floats"]
        for name, expected in material["required_float_state"].items():
            if abs(float(source_floats[name]) - float(expected)) > 1e-6:
                raise AssertionError(f"{actor}: source float mismatch {name}")

        dump_path = verify_file(material["source_dump"])
        keywords, queue, disabled = parse_dump(dump_path)
        if keywords != material["valid_keywords"]:
            raise AssertionError(f"{actor}: serialized valid-keyword mismatch")
        if queue != int(material["custom_render_queue"]):
            raise AssertionError(f"{actor}: serialized queue mismatch")
        if disabled != material["disabled_shader_passes"]:
            raise AssertionError(f"{actor}: disabled-pass mismatch")
        if ("DepthOnly" not in disabled) != bool(material["depth_only_enabled"]):
            raise AssertionError(f"{actor}: DepthOnly enable-state mismatch")

        queue_counts[queue] += 1
        depth_counts[bool(material["depth_only_enabled"])] += 1
        class_counts[int(material["variant_class"])] += 1
        actor_counts[actor] += 1
        generated_paths[key] = (
            manifest_path.parent
            / "Materials"
            / f"actor_{actor}_pathid_{material['path_id']}.mat"
        )

    if queue_counts != collections.Counter({2000: 47, 2015: 11, 2050: 1}):
        raise AssertionError(f"Eye queue census mismatch: {queue_counts}")
    if depth_counts != collections.Counter({False: 49, True: 10}):
        raise AssertionError(f"Eye DepthOnly census mismatch: {depth_counts}")
    if class_counts != collections.Counter({1: 30, 2: 21, 3: 8}):
        raise AssertionError(f"Eye variant-class census mismatch: {class_counts}")
    if dict(sorted(actor_counts.items())) != {
        key: value
        for key, value in sorted(contract["scope"]["actor_material_counts"].items())
        if value
    }:
        raise AssertionError("Eye actor material-count census mismatch")
    return generated_paths


def verify_implementation() -> None:
    importer = IMPORTER.read_text(encoding="utf-8")
    for token in (
        "EyeBrowForwardContractAssetPath",
        "ExactRecoveredEyeBrowForwardVariant(",
        '"_RecoveredEyeForwardVariantClass"',
        'material.renderQueue = Int(',
        'material.SetShaderPassEnabled(\n                    "CAMERA_DEPTH_COPY",',
        '"depth_only_enabled"',
        "textures.Count != requiredTextures.Count",
    ):
        require(importer, token, "Eye importer integration")

    shader = EYE_SHADER.read_text(encoding="utf-8")
    for token in (
        "_RecoveredEyeForwardVariantClass",
        "EndfieldRecoveredEyeVariantIs(1.0h)",
        "EndfieldRecoveredEyeVariantIs(2.0h)",
        "if (_RecoveredEyeForwardVariantClass > 0.5h)",
        "The three current playable variants compile without",
        "return half4(max(recoveredEyeColor, 0.0h), 1.0h);",
        "#if defined(ENDFIELD_RECOVERED_EYE_SCREEN_SHADOW_MASK_R)",
        "EndfieldHGRPLoadScreenSpaceShadowMaskR(i.pos.xy);",
        "the neutral attachment diagnostic cannot",
        "the exact scene-R content producer remains open",
        "#pragma multi_compile __ ENDFIELD_RECOVERED_EYE_SCREEN_SHADOW_MASK_R",
    ):
        require(shader, token, "recovered Eye shader")
    source_start = shader.index("if (_RecoveredEyeForwardVariantClass > 0.5h)")
    source_end = shader.index("#endif", source_start)
    exact_source_block = shader[source_start:source_end]
    if "tex2D(_EmissionMap" in exact_source_block:
        raise AssertionError("exact current Eye branch still samples unsupported emission")


def generated_material_state(path: Path) -> tuple[int, int | None, bool | None]:
    if not path.is_file():
        return -9999, None, None
    text = path.read_text(encoding="utf-8")
    queue_match = re.search(r"m_CustomRenderQueue: (-?\d+)", text)
    class_match = re.search(
        r"- _RecoveredEyeForwardVariantClass:\s*([^\s]+)", text
    )
    if class_match and class_match.group(1) == "m_Value:":
        class_match = re.search(
            r"- _RecoveredEyeForwardVariantClass:\s*\n\s*m_Value: ([^\s]+)",
            text,
        )
    disabled_match = re.search(
        r"(?:m_DisabledShaderPasses|disabledShaderPasses):[^\r\n]*\r?\n"
        r"((?:\s*- .*?(?:\r?\n|$))*)",
        text,
    )
    disabled = [] if not disabled_match else re.findall(
        r"- ([^\r\n]+)", disabled_match.group(1)
    )
    return (
        int(queue_match.group(1)) if queue_match else -9999,
        int(round(float(class_match.group(1)))) if class_match else None,
        "CAMERA_DEPTH_COPY" not in disabled,
    )


def verify_generated_materials(
    contract: dict[str, Any],
    generated_paths: dict[str, Path],
    require_generated: bool,
) -> int:
    pending = 0
    for key, material in contract["materials"].items():
        path = generated_paths[key]
        queue, variant_class, depth_enabled = generated_material_state(path)
        expected = (
            int(material["custom_render_queue"]),
            int(material["variant_class"]),
            bool(material["depth_only_enabled"]),
        )
        if (queue, variant_class, depth_enabled) != expected:
            pending += 1
            if require_generated:
                raise AssertionError(
                    f"generated Eye material needs refresh: {path}: "
                    f"{(queue, variant_class, depth_enabled)} != {expected}"
                )
        elif EYE_SHADER_GUID not in path.read_text(encoding="utf-8"):
            raise AssertionError(f"generated Eye material shader GUID mismatch: {path}")
    return pending


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-generated", action="store_true")
    args = parser.parse_args()

    contract = load_json(CONTRACT_PATH)
    if contract["schema"] != "endfield.eye-brow-forward-contract.v1":
        raise AssertionError("Eye/brow contract schema mismatch")
    if contract["scope"]["playable_actor_count"] != 31:
        raise AssertionError("playable actor scope mismatch")
    if contract["scope"]["eye_family_actor_count"] != 29:
        raise AssertionError("Eye-family actor scope mismatch")
    if contract["scope"]["source_proven_zero_actors"] != ["antal", "dapan"]:
        raise AssertionError("source-proven zero actor scope mismatch")
    if len(contract["materials"]) != 59:
        raise AssertionError("Eye material scope mismatch")
    shader_path = verify_file(contract["shader"])
    if shader_path.stat().st_size != 33434983:
        raise AssertionError("current installed Eye shader size mismatch")
    if contract["shader"]["sha256"] != (
        "72a95dad99913db4c4ced15dfe8647a1f748b950a73fd460974ebeec39973c79"
    ):
        raise AssertionError("current installed Eye shader hash mismatch")
    if contract["shader"]["d3d11_sidecar_count"] != 104:
        raise AssertionError("current Eye D3D11 sidecar count mismatch")

    verify_variants(contract)
    generated_paths = verify_materials(contract)
    verify_implementation()
    pending = verify_generated_materials(
        contract, generated_paths, args.require_generated
    )
    print(
        "Eye/brow ForwardLit recovery passed: 31 actors (29 Eye-family, 2 "
        "source-zero), 59 exact materials, 3 current D3D11 fragments, queues "
        "2000/2015/2050, DepthOnly 10 enabled / 49 disabled, opaque Target0.a=1, "
        "packed scene-MV MRT, and mandatory screen-mask R consumption pinned; "
        f"generated materials pending refresh={pending}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

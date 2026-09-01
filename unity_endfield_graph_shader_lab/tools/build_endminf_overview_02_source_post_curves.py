#!/usr/bin/env python3
"""Build the exact source-curve payload for Endminf overview effect 02."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
SOURCE_CLIP = (
    REPO
    / "scratch/character_recovery/endminf_overview_effect_stage/AnimationClip"
    / "A_fx_endminf_ui_overview_02_p74C3E18DD531CF7C.json"
)
NATIVE_AUDIT = (
    REPO / "reports/assets/endminf_overview_02_post_curve_native_audit.json"
)
OUTPUT = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Resources/EndfieldEndminfSourcePost"
    / "endminf_overview_02_source_post_curves.json"
)

EXPECTED_CLIP_SHA256 = (
    "9814b9de92d5af7902b1967c295f98d29327824bdd7b478984527c5ccccd076c"
)
EXPECTED_GAMEASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
)
EXPECTED_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
)
EXPECTED_NATIVE_AUDIT_SHA256 = (
    "6b01af7b64931b26a616de75ed927aa1a71010a1fdbd0f1d868e349017c109cb"
)
EXPECTED_NATIVE_APPLY_MAP_SHA256 = (
    "950d61814100c7992a7166849fe1d60a9062ec36b3943bbfbdb3aa1d70ebe415"
)
EXPECTED_TARGET_PATH_CRC32 = 669740077
EXPECTED_INTENSITY_ATTRIBUTE = 2754484623
EXPECTED_POWER_ATTRIBUTE = 565374268
CHROMATIC_SCRIPT_PATH_ID = 6948449919205830506
RADIAL_SCRIPT_PATH_ID = 317588138045017993
EXPECTED_APPLY_METHODS = {
    "HG.Rendering.Runtime.VFXPPChromaticAberration": {
        "token": "0x06000b87",
        "bodySha256": "da30ec2809ba5eef7e3f8e8a102e3f49a9c0d7489e314e626b801c360e74fc89",
    },
    "HG.Rendering.Runtime.VFXPPRadialBlur": {
        "token": "0x06000c1b",
        "bodySha256": "ff5ac818a479aa258542d410b878d5be617b09fb19daa3c4776225f272d00824",
    },
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_text_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    ).hexdigest()


def load_sampler() -> Any:
    path = LAB / "tools/unity_muscleclip_sampler.py"
    spec = importlib.util.spec_from_file_location(
        "endminf_source_post_unity_muscleclip_sampler", path
    )
    require(spec is not None and spec.loader is not None, "sampler import failed")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def binding_script_path_id(binding: dict[str, Any]) -> int:
    return int((binding.get("script") or {}).get("m_PathID") or 0)


def encode_stream_curve(role: str, script_type: str, binding: dict[str, Any], keys: list[Any]) -> dict[str, Any]:
    return {
        "role": role,
        "storage": "streamed-cubic-polynomial",
        "scriptType": script_type,
        "scriptPathId": binding_script_path_id(binding),
        "pathCrc32": int(binding.get("path") or 0),
        "attributeCrc32": int(binding.get("attribute") or 0),
        "keys": [
            {
                "time": key.time,
                "a": key.coeff[0],
                "b": key.coeff[1],
                "c": key.coeff[2],
                "d": key.coeff[3],
            }
            for key in keys
        ],
    }


def build() -> dict[str, Any]:
    require(SOURCE_CLIP.is_file(), f"source clip is missing: {SOURCE_CLIP}")
    require(NATIVE_AUDIT.is_file(), f"native audit is missing: {NATIVE_AUDIT}")
    require(
        sha256(SOURCE_CLIP) == EXPECTED_CLIP_SHA256,
        "source overview-02 clip hash drifted",
    )
    require(
        normalized_text_sha256(NATIVE_AUDIT) == EXPECTED_NATIVE_AUDIT_SHA256,
        "native post audit content hash drifted",
    )

    clip = json.loads(SOURCE_CLIP.read_text(encoding="utf-8"))
    audit = json.loads(NATIVE_AUDIT.read_text(encoding="utf-8"))
    require(clip.get("m_Name") == "A_fx_endminf_ui_overview_02", "clip name drifted")
    require(float(clip.get("m_SampleRate") or 0.0) == 30.0, "clip rate drifted")
    muscle = clip.get("m_MuscleClip") or {}
    require(float(muscle.get("m_StartTime") or 0.0) == 0.0, "clip start drifted")
    require(float(muscle.get("m_StopTime") or 0.0) == 4.6, "clip stop drifted")
    require(muscle.get("m_LoopTime") is False, "clip loop state drifted")

    require(
        audit.get("schema")
        == "endfield.endminf-overview-02-post-curves-native-audit.v2",
        "native audit schema drifted",
    )
    require(
        audit.get("status") == "pinned_apply_writes_closed_composition_unresolved",
        "native audit status drifted",
    )
    inputs = audit.get("inputs") or {}
    require(inputs.get("clipSha256") == EXPECTED_CLIP_SHA256, "audit clip hash drifted")
    require(
        inputs.get("gameAssemblySha256") == EXPECTED_GAMEASSEMBLY_SHA256,
        "audit GameAssembly hash drifted",
    )
    require(
        inputs.get("globalMetadataSha256") == EXPECTED_METADATA_SHA256,
        "audit metadata hash drifted",
    )
    require(
        inputs.get("nativeApplyMapSha256") == EXPECTED_NATIVE_APPLY_MAP_SHA256,
        "audit native Apply map hash drifted",
    )
    require(
        audit.get("targetPath")
        == {"name": "post (1)", "crc32": EXPECTED_TARGET_PATH_CRC32},
        "post target identity drifted",
    )
    require(
        audit.get("resolvedMembers")
        == {
            str(EXPECTED_INTENSITY_ATTRIBUTE): "_intensity",
            str(EXPECTED_POWER_ATTRIBUTE): "_power",
        },
        "native member mapping drifted",
    )
    script_types = {
        row.get("fullName"): row for row in (audit.get("scriptTypes") or [])
    }
    apply_methods: list[dict[str, str]] = []
    for type_name, expected in EXPECTED_APPLY_METHODS.items():
        script_type = script_types.get(type_name) or {}
        rows = [
            row
            for row in (script_type.get("methods") or [])
            if row.get("method") == "Apply"
        ]
        require(len(rows) == 1, f"native {type_name}.Apply census drifted")
        row = rows[0]
        require(
            row.get("token") == expected["token"]
            and row.get("bodySha256") == expected["bodySha256"],
            f"native {type_name}.Apply identity drifted",
        )
        apply_methods.append({
            "type": type_name,
            "token": expected["token"],
            "bodySha256": expected["bodySha256"],
        })

    bindings = (clip.get("m_ClipBindingConstant") or {}).get("genericBindings") or []
    require(len(bindings) == 3, "expected exactly three post scalar bindings")
    expected_bindings = (
        (CHROMATIC_SCRIPT_PATH_ID, EXPECTED_INTENSITY_ATTRIBUTE),
        (RADIAL_SCRIPT_PATH_ID, EXPECTED_INTENSITY_ATTRIBUTE),
        (RADIAL_SCRIPT_PATH_ID, EXPECTED_POWER_ATTRIBUTE),
    )
    for index, (script_path_id, attribute) in enumerate(expected_bindings):
        binding = bindings[index]
        require(binding.get("typeID") == "MonoBehaviour", f"binding {index} type drifted")
        require(
            int(binding.get("path") or 0) == EXPECTED_TARGET_PATH_CRC32,
            f"binding {index} target path drifted",
        )
        require(
            binding_script_path_id(binding) == script_path_id
            and int(binding.get("attribute") or 0) == attribute,
            f"binding {index} script/member identity drifted",
        )

    raw = muscle.get("m_Clip") or {}
    streamed = raw.get("m_StreamedClip") or {}
    dense = raw.get("m_DenseClip") or {}
    constant = raw.get("m_ConstantClip") or {}
    require(int(streamed.get("curveCount") or 0) == 2, "streamed curve count drifted")
    require(int(dense.get("m_CurveCount") or 0) == 0, "unexpected dense curves")
    require(constant.get("data") == [1.0], "radial power constant drifted")

    sampler = load_sampler()
    frames = sampler.parse_stream_frames(streamed.get("data") or [])
    curves, warnings = sampler.build_stream_curves(frames, 2)
    require(not warnings, f"streamed source curves are incomplete: {warnings}")
    require(set(curves) == {0, 1}, "streamed curve indices drifted")
    require(len(curves[0]) == 5 and len(curves[1]) == 5, "source key census drifted")

    audit_bindings = audit.get("bindings") or []
    require(len(audit_bindings) == 3, "native audit binding census drifted")
    for index, keys in ((0, curves[0]), (1, curves[1])):
        audit_keys = audit_bindings[index].get("keys") or []
        require(
            [(row.get("time"), row.get("value")) for row in audit_keys]
            == [(key.time, key.value) for key in keys],
            f"native audit/source curve {index} key join drifted",
        )

    source_relative = SOURCE_CLIP.relative_to(REPO).as_posix()
    audit_relative = NATIVE_AUDIT.relative_to(REPO).as_posix()
    return {
        "schema": "endfield.endminf-overview-02-source-post-curves.v1",
        "sourceClip": {
            "name": "A_fx_endminf_ui_overview_02",
            "path": source_relative,
            "sha256": EXPECTED_CLIP_SHA256,
            "sampleRate": 30.0,
            "startSeconds": 0.0,
            "stopSeconds": 4.6,
            "loop": False,
        },
        "nativeAudit": {
            "path": audit_relative,
            "sha256": EXPECTED_NATIVE_AUDIT_SHA256,
            "schema": audit["schema"],
            "status": audit["status"],
            "gameAssemblySha256": EXPECTED_GAMEASSEMBLY_SHA256,
            "globalMetadataSha256": EXPECTED_METADATA_SHA256,
            "nativeApplyMapSha256": EXPECTED_NATIVE_APPLY_MAP_SHA256,
            "applyMethods": apply_methods,
        },
        "target": {"name": "post (1)", "pathCrc32": EXPECTED_TARGET_PATH_CRC32},
        "curves": [
            encode_stream_curve(
                "chromaticIntensity",
                "HG.Rendering.Runtime.VFXPPChromaticAberration",
                bindings[0],
                curves[0],
            ),
            encode_stream_curve(
                "radialIntensity",
                "HG.Rendering.Runtime.VFXPPRadialBlur",
                bindings[1],
                curves[1],
            ),
            {
                "role": "radialPower",
                "storage": "constant",
                "scriptType": "HG.Rendering.Runtime.VFXPPRadialBlur",
                "scriptPathId": RADIAL_SCRIPT_PATH_ID,
                "pathCrc32": EXPECTED_TARGET_PATH_CRC32,
                "attributeCrc32": EXPECTED_POWER_ATTRIBUTE,
                "keys": [
                    {"time": 0.0, "a": 0.0, "b": 0.0, "c": 0.0, "d": 1.0}
                ],
            },
        ],
        "runtimeBoundary": (
            "This payload recovers the exact serialized source curves and the pinned native "
            "MonoBehaviour field/apply identities. The separate v4 effect trigger contract "
            "proves that FromOveview owns overview_01 and, on the conditional pinned unpatched "
            "route, passes one raw length*normalizedTime seed after effect start; its recorded "
            "installed local IFix snapshot excludes those route targets. Runtime/remote patch "
            "state, alternate native branches, the retail EffectInstance tick domain, "
            "cross-component render-pass composition, SceneColor chronology, and a "
            "retail-equivalent Unity presentation path remain outside this payload."
        ),
    }


def encode(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def canonicalize_newlines(payload: bytes) -> bytes:
    return payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = encode(build())
    if args.check:
        require(OUTPUT.is_file(), f"published source-post payload is missing: {OUTPUT}")
        require(
            canonicalize_newlines(OUTPUT.read_bytes()) == payload,
            "published source-post payload drifted",
        )
        print(f"build_endminf_overview_02_source_post_curves: OK {OUTPUT}")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(payload)
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

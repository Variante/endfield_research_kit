#!/usr/bin/env python3
"""Scope the selected deferred resolver's actual ShaderVariablesGlobal reads."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
GAME_ASSEMBLY = Path(r"D:/Program Files/Endfield Game/GameAssembly.dll")
SOURCES = {
    "selectedFragment": (
        LAB_ROOT
        / "scratch/reverse_engineering/sphereoutside_deferred_variant/"
        "selected_fragment.hlsl"
    ),
    "selectedDxbcFragment": (
        LAB_ROOT
        / "scratch/reverse_engineering/sphereoutside_deferred_variant/"
        "selected_fragment_dxbc.hlsl"
    ),
    "selectedMetadata": (
        LAB_ROOT
        / "scratch/reverse_engineering/sphereoutside_deferred_variant/"
        "selected_fragment.enriched.metadata.json"
    ),
    "heightFogReset": (
        REPO_ROOT
        / "scratch/reverse_engineering/gacha_deferred_exact_binding_contents/"
        "native_height_fog_reset.json"
    ),
    "globalMipBias": (
        REPO_ROOT
        / "scratch/reverse_engineering/global_mip_bias_producer/"
        "global_mip_bias_producer_report.json"
    ),
    "inactiveIrradianceV2": (
        LAB_ROOT
        / "scratch/character_recovery/charinfo_pass0_resources/"
        "charinfo_v2_irradiance.json"
    ),
}
EXPECTED_HASHES = {
    "gameAssembly": (
        "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
    ),
    "selectedFragment": (
        "44dc5090af87a8f65ffca870f9e02b8525c4cfe14f84cf8feaa3ea6c49e4b9db"
    ),
    "selectedDxbcFragment": (
        "c748ee49a72794ef81f6795bee934775e42958ad74e9560c0730e8d83686906d"
    ),
    "selectedMetadata": (
        "c296317ff6e7aa8d5d35b1c6705117dbdee37ff4163b4b093e69262e85e3a826"
    ),
    "heightFogReset": (
        "44bb502de793304f3db0543602fb43afd022f247f320b52506e50bddff617740"
    ),
    "globalMipBias": (
        "bdd8901d5c5b89fa2105eb3425cd1807a6592ba1e21436986f31f1c84f62035f"
    ),
    "inactiveIrradianceV2": (
        "1f77756f536c394efcbfcd1d6d00fca9ed4b40e86f7cdad9c14cf7379af5a5b3"
    ),
}
OUTPUT = (
    LAB_ROOT
    / "scratch/character_recovery/deferred_shader_variables_global/audit.json"
)

# These methods are the current installed non-IFix reset producers. Hashing the
# complete method bodies makes the decoded vectors below fail closed on drift.
NATIVE_METHODS = {
    "atmosphereFogReset": {
        "method": (
            "HG.Rendering.Runtime.HGAtmosphereRenderer."
            "ResetShaderVariablesGlobalAtmosphereFog"
        ),
        "methodIndex": 284536,
        "va": "0x189cdf408",
        "fileOffset": 0x9CDDA08,
        "size": 0x1A0,
        "sha256": (
            "40e8d04110fb803de8e3559f07169a643c44e42b39723b4fc96929e14dac6a8c"
        ),
        "vectors": {
            "c71": [0.0, 0.0, 0.0, 0.0],
            "c72": [0.0, 0.0, 1.0, 0.0010000000474974513],
            "c73": [9.999999747378752e-06] * 3 + [0.0],
            "c74": [0.0, 0.0, 0.0, -1.0],
            "c75": [0.0, 0.0, 0.0, 0.0],
            "c76": [0.0, 0.0, 0.0, -65535.0],
        },
    },
    "heightFogReset": {
        "method": (
            "HG.Rendering.Runtime.HGAtmosphereRenderer."
            "ResetShaderVariablesGlobalHeightFog"
        ),
        "methodIndex": 284538,
        "va": "0x189cdf664",
        "fileOffset": 0x9CDDC64,
        "size": 0x128,
        "sha256": (
            "e3c3397a936002165d66bc6f61f9ff7b7acb0730cd09fa0938644f587bb156ea"
        ),
        "vectors": {
            "c77": [0.0, 0.0, 0.0, 0.0],
            "c78": [0.0, 0.0, 0.0, 0.0],
            "c79": [0.0, 0.0, 0.0, 1.0],
            "c80": [0.0, 0.0, 0.0, 0.0],
            "c81": [0.0, 1.0, 0.0, 0.0],
            "c82": [0.0, 0.0, 0.0, 1.0],
        },
    },
    "volumetricFogReset": {
        "method": (
            "HG.Rendering.Runtime.HGVolumetricFogRenderer."
            "ResetShaderVariablesGlobalVolumetricFog"
        ),
        "methodIndex": 284730,
        "va": "0x189cee4bc",
        "fileOffset": 0x9CECABC,
        "size": 0xB8,
        "sha256": (
            "310ada3d2bdc604c4bd60fabeda47bebc76a577f9e9255e73a8609beb6be072b"
        ),
        "vectors": {
            f"c{row}": [0.0, 0.0, 0.0, 0.0]
            for row in range(83, 88)
        },
    },
}

EXPECTED_USED_FIELDS = {
    "AtmosphereFogParams0",
    "AtmosphereFogParams1",
    "AtmosphereFogParams2",
    "AtmosphereFogParams3",
    "AtmosphereFogParams4",
    "AtmosphereFogParams5",
    "BinningBufferOffsets",
    "EnvironmentGlobalParams0",
    "ExponentialFogParams0",
    "ExponentialFogParams1",
    "ExponentialFogParams2",
    "ExponentialFogParams3",
    "ExponentialFogParams4",
    "ExponentialFogParams5",
    "f_48",
    "FrameCount",
    "GlobalMipBias",
    "GraphicsFeaturesGlobalParam0",
    "GraphicsFeaturesGlobalParam1",
    "IVDefaultSHAb",
    "IVDefaultSHAg",
    "IVDefaultSHAr",
    "IVParam0",
    "IVParam1",
    "IVParam2",
    "ScreenSize",
    "unity_OrthoParams",
    "VolumetricFogParams0",
    "VolumetricFogParams1",
    "VolumetricFogParams2",
    "VolumetricFogParams3",
    "VolumetricFogParams4",
    "WaterWetnessMaskParam0",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(check: str, actual: object, expected: object) -> None:
    if actual != expected:
        raise AssertionError(
            "Deferred ShaderVariablesGlobal audit failed: "
            f"check={check}; expected={expected!r}; actual={actual!r}"
        )


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def parse_layout(source: str) -> dict[str, dict[str, object]]:
    match = re.search(
        r"cbuffer type_ShaderVariablesGlobal.*?\n\{(.*?)\n\};",
        source,
        re.DOTALL,
    )
    require("b35_declaration", match is not None, True)
    pattern = re.compile(
        r"\b(?:column_major\s+)?(?:float|int|uint)(?:[1-4](?:x[1-4])?)?\s+"
        r"ShaderVariablesGlobal_([A-Za-z0-9_]+)(?:\[(\d+)\])?\s*:\s*"
        r"packoffset\(c(\d+)(?:\.([xyzw]))?\);"
    )
    layout: dict[str, dict[str, object]] = {}
    for row in pattern.finditer(match.group(1)):
        layout[row.group(1)] = {
            "row": int(row.group(3)),
            "lane": row.group(4) or "xyzw",
            "arrayCount": int(row.group(2) or "1"),
        }
    return layout


def parse_body_uses(source: str, layout: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    body_offset = source.find("void frag_main")
    if body_offset < 0:
        body_offset = source.find("void main")
    require("fragment_body", body_offset >= 0, True)
    body = source[body_offset:]
    uses: list[dict[str, object]] = []
    pattern = re.compile(
        r"ShaderVariablesGlobal_([A-Za-z0-9_]+)(?:\[[^\]]+\])?"
        r"(?:\.([xyzw]+))?"
    )
    for match in pattern.finditer(body):
        field = match.group(1)
        require(f"layout_for_{field}", field in layout, True)
        line = source.count("\n", 0, body_offset + match.start()) + 1
        uses.append(
            {
                "field": field,
                "row": layout[field]["row"],
                "lanes": match.group(2) or layout[field]["lane"],
                "line": line,
            }
        )
    return uses


def build_audit() -> dict[str, object]:
    hashes = {name: sha256(path) for name, path in SOURCES.items()}
    game_hash = sha256(GAME_ASSEMBLY)
    require("gameAssembly_sha256", game_hash, EXPECTED_HASHES["gameAssembly"])
    for name, expected in EXPECTED_HASHES.items():
        if name == "gameAssembly":
            continue
        require(f"{name}_sha256", hashes[name], expected)

    game_bytes = GAME_ASSEMBLY.read_bytes()
    for name, method in NATIVE_METHODS.items():
        start = method["fileOffset"]
        body = game_bytes[start : start + method["size"]]
        require(f"{name}_size", len(body), method["size"])
        require(
            f"{name}_sha256",
            hashlib.sha256(body).hexdigest(),
            method["sha256"],
        )

    source = SOURCES["selectedFragment"].read_text(encoding="utf-8")
    dxbc = SOURCES["selectedDxbcFragment"].read_text(encoding="utf-8")
    layout = parse_layout(source)
    uses = parse_body_uses(source, layout)
    used_fields = {row["field"] for row in uses}
    require("used_fields", used_fields, EXPECTED_USED_FIELDS)
    require(
        "spirv_b35_vector_count",
        max(v["row"] + v["arrayCount"] for v in layout.values()),
        200,
    )
    require("d3d11_b1_prefix", "float4 _57_m0[157]" in dxbc, True)
    require("d3d11_b1_alias_prefix", "float4 _62_m0[157]" in dxbc, True)

    mip = json.loads(SOURCES["globalMipBias"].read_text(encoding="utf-8"))
    require("selected_mip_bias", mip["labPublishedPair"]["_GlobalMipBias"], 0.0)
    iv = json.loads(SOURCES["inactiveIrradianceV2"].read_text(encoding="utf-8"))
    inactive = iv["activeClipmaps"]["installedMissingMapState"]["parameters"]
    for index in range(3):
        require(f"inactive_iv_param{index}", inactive[f"param{index}"], [0.0] * 4)

    compact_uses: dict[str, dict[str, object]] = {}
    for row in uses:
        entry = compact_uses.setdefault(
            row["field"],
            {"row": row["row"], "lanes": set(), "lines": []},
        )
        entry["lanes"].update(row["lanes"])
        entry["lines"].append(row["line"])
    lane_order = "xyzw"
    rendered_uses = [
        {
            "field": field,
            "row": value["row"],
            "lanes": "".join(lane for lane in lane_order if lane in value["lanes"]),
            "lines": sorted(set(value["lines"])),
        }
        for field, value in sorted(compact_uses.items(), key=lambda item: (item[1]["row"], item[0]))
    ]

    return {
        "schema": "endfield.deferred-shader-variables-global-audit.v1",
        "status": "selected_consumer_exactly_scoped_but_not_fully_source_closed",
        "binding": {
            "canonicalName": "ShaderVariablesGlobal",
            "spirvSet": 3,
            "spirvBinding": 35,
            "spirvBytes": 3200,
            "spirvVectors": 200,
            "d3d11Register": "b1",
            "d3d11BridgeName": "EndfieldCB1",
            "d3d11SelectedBytes": 2512,
            "d3d11SelectedVectors": 157,
        },
        "actualSelectedBodyUses": rendered_uses,
        "nativeResetProducers": {
            name: {
                key: value
                for key, value in method.items()
                if key not in {"fileOffset"}
            }
            | {"fileOffset": hex(method["fileOffset"])}
            for name, method in NATIVE_METHODS.items()
        },
        "closedSelectedRows": {
            "c4.w": "perspective ExternalCamera => unity_OrthoParams.w=0",
            "c26.x": "selected HGAdditionalCameraData materialMipBias=0",
            "c28": "same-frame recovered light/reflection binning offsets",
            "c29": "serialized CharInfo environment exposure/reflection scale",
            "c71..c76": "exact installed atmosphere-fog reset producer",
            "c77..c82": "exact installed height-fog reset producer",
            "c83..c87": "exact installed disabled-volumetric reset producer; c83.z gates the branch off",
            "c132..c134": "installed no-reload V2 irradiance result parameters are all zero",
            "c156.x": "serialized CharInfo wetness is disabled/zero",
        },
        "branchDeadSelectedReads": {
            "c26.w": "FrameCount is read only inside the c83.z > 0 volumetric branch",
            "c84..c87": "volumetric parameters are zero and downstream reads are gated by c83.z=0",
        },
        "remainingSelectedRows": {
            "c0.zw": "same-target inverse screen dimensions; producer formula is known but target-frame dimensions remain dynamic",
            "c3.y": "depth/z-bin projection term; exact HGCamera producer expression/value remains open",
            "c30.xy": "two native graphics-feature booleans need selected-camera values; c30.zw are exact 1.0",
            "c31.x": "reflection mip/exposure feature scalar remains open",
            "c135..c137": "IVDefaultSHAr/Ag/Ab remain live and exact selected-scene values are not yet recovered",
        },
        "decision": (
            "Do not publish EndfieldCB1 or enable pass 0 yet. The reset producers "
            "close fog rows exactly, but c3.y, c30.xy, c31.x, and c135..c137 "
            "still affect the selected resolver outside dead branches."
        ),
        "sources": {
            "gameAssembly": {
                "path": str(GAME_ASSEMBLY),
                "sha256": game_hash,
            }
        }
        | {
            name: {"path": relative(path), "sha256": hashes[name]}
            for name, path in SOURCES.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(build_audit(), indent=2) + "\n"
    if args.check:
        if not OUTPUT.is_file():
            raise AssertionError(f"missing generated audit: {OUTPUT}")
        require("generated_audit", OUTPUT.read_text(encoding="utf-8"), rendered)
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered, encoding="utf-8")
    print(
        "Deferred ShaderVariablesGlobal audit passed: 33 selected fields; "
        "fog resets exact; b1 remains blocked by c3/c30/c31/c135..c137."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Pin Li Zhiyan's current-build after-DOF native scheduling/ABI boundary."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path
from typing import Any


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
OUTPUT = (
    LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/"
    "LiZhiyanOverviewFinger/lizhiyan_after_dof_native_abi.json"
)
SHADER_CONTRACT = OUTPUT.with_name("lizhiyan_overview_vfxbasev2_variants.json")
CODE_REGISTRATION = 0x18B9217D0
EXPECTED = {
    "gameAssembly": "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE",
    "metadata": "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E",
    "shaderContract": "1191F96B45FD11C47D31C71681B25E77B3DF2CBD2179F21B4D2854D3AD90796B",
}
METHODS = [
    (287274, "HG.Rendering.Runtime.ForwardPassUtils",
     "PrepareAfterDOFTranparentRendererList", 0x189BAB274, 0x189BAB4E2,
     "319799A95260B1717084D16AA8C2E0CCAD668CEDF3E52E9465B99A31EC44A5E0"),
    (287316, "HG.Rendering.Runtime.TransparentAfterDOFPassConstructor",
     "ConstructPass", 0x189BB2E40, 0x189BB346A,
     "D54DCF38AC17E6062573C476BF988FF8CBEE70E89F2B02FB341E5588DA3612CC"),
    (287324, "HG.Rendering.Runtime.TransparentAfterDOFPassConstructor+<>c",
     "<.cctor>b__10_0", 0x189BB5264, 0x189BB558A,
     "D49C4DE691A7B65184532D8C9E46E1209F35AF2A76C0E23FA82B8E35593011CC"),
    (288225, "HG.Rendering.Runtime.HGRendererListUtils",
     "RenderForwardRendererList", 0x189C0A6EC, 0x189C0A7CC,
     "76DC5D1B4730F4A5BB937F3776A776DE2A8E960B4BB4A47B983BA5F264555879"),
    (288226, "HG.Rendering.Runtime.HGRendererListUtils",
     "RenderForwardECSRendererList", 0x189C0A628, 0x189C0A6EA,
     "BBA699B59C1081CDF6870E95B3B17469DD0D8791234E166D1D403D85786E6F42"),
    (288241, "HG.Rendering.Runtime.HGRendererListUtils",
     "CreateTransparentRendererListDesc", 0x189C08904, 0x189C08BC8,
     "08E90A05982967C1F0AA45950FDF24F069FA6B639238EE3F6429FEF2DE697163"),
]
CALLS = [
    (0x189BAB3C2, 0x189C08904, "PrepareAfterDOF -> CreateTransparentRendererListDesc"),
    (0x189BB3299, 0x189BAB274, "ConstructPass -> PrepareAfterDOFTranparentRendererList"),
    (0x189BB332B, 0x189B2AB5C, "ConstructPass -> CreateRendererList"),
    (0x189BB334B, 0x189B36820, "ConstructPass -> UseRendererList"),
    (0x189BB54F1, 0x189C0A6EC, "callback -> RenderForwardRendererList"),
    (0x189BB5541, 0x189C0A628, "callback -> RenderForwardECSRendererList"),
    (0x189BB5401, 0x18B2DE0CC, "callback -> DrawFullScreen"),
    (0x189C08967, 0x1832512C0, "CreateTransparentRendererListDesc -> Camera.get_cullingMask"),
    (0x189C0897E, 0x189B736B0, "CreateTransparentRendererListDesc -> RemoveWorldUILayer"),
    (0x189C089A4, 0x18B3F4A7C, "CreateTransparentRendererListDesc -> RendererListDesc.ctor"),
]


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build(game_root: Path) -> dict[str, Any]:
    game_assembly = game_root / "GameAssembly.dll"
    metadata = game_root / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat"
    for key, path in (("gameAssembly", game_assembly), ("metadata", metadata)):
        require(path.is_file(), f"missing explicitly selected native input: {path}")
        require(sha256(path) == EXPECTED[key], f"selected native input drifted: {key}")
    require(sha256(SHADER_CONTRACT) == EXPECTED["shaderContract"],
            "Li Zhiyan shader ABI contract drifted")

    metadata_module = load_module(
        "lizhiyan_after_dof_metadata",
        REPO / "tools/endfield-il2cpp/catalog_option_flow_metadata.py")
    mapper = load_module(
        "lizhiyan_after_dof_mapper",
        REPO / "tools/endfield-il2cpp/map_body_targets_to_gameassembly.py")
    md = metadata_module.Metadata(metadata)
    pe = mapper.PeImage(game_assembly)
    modules = mapper.parse_codegen_modules(pe, CODE_REGISTRATION)
    image_ranges = mapper.image_method_ranges(md)
    pointers, _ = mapper.build_pointer_indexes(pe, md, modules, image_ranges)

    pdata = next(section for section in pe.sections if section["name"] == ".pdata")
    function_ends: dict[int, int] = {}
    for pos in range(pdata["rawPointer"], pdata["rawPointer"] + pdata["rawSize"] - 11, 12):
        begin_rva, end_rva, _ = struct.unpack_from("<III", pe.buf, pos)
        if begin_rva and end_rva > begin_rva:
            function_ends[pe.image_base + begin_rva] = pe.image_base + end_rva

    methods = []
    for index, expected_type, expected_name, expected_va, expected_end, expected_hash in METHODS:
        method = md.methods[index]
        owner = md.types[method.declaring_type]
        require(md.type_full_name(owner) == expected_type, f"method owner drift: {index}")
        require(md.string(method.name_index) == expected_name, f"method name drift: {index}")
        image = next(row for row in md.images
                     if row.type_start <= owner.index < row.type_start + row.type_count)
        image_name = md.string(image.name_index)
        va = pointers[image_name][index - image_ranges[image_name]["methodStart"]]
        require(va == expected_va and function_ends.get(va) == expected_end,
                f"method function span drift: {index}")
        body = pe.bytes_at_va(va, expected_end - va)
        body_hash = hashlib.sha256(body).hexdigest().upper()
        require(body_hash == expected_hash, f"method body drift: {index}")
        methods.append({
            "methodIndex": index,
            "type": expected_type,
            "name": expected_name,
            "token": f"0x{method.token:08x}",
            "va": f"0x{va:x}",
            "functionEnd": f"0x{expected_end:x}",
            "functionBytes": len(body),
            "functionSha256": body_hash,
        })

    calls = []
    for callsite, expected_target, label in CALLS:
        data = pe.bytes_at_va(callsite, 5)
        require(len(data) == 5 and data[0] == 0xE8, f"missing rel32 call: {label}")
        target = callsite + 5 + struct.unpack_from("<i", data, 1)[0]
        require(target == expected_target, f"call target drift: {label}")
        calls.append({"label": label, "callsite": f"0x{callsite:x}",
                      "target": f"0x{target:x}"})

    shader = json.loads(SHADER_CONTRACT.read_text(encoding="utf-8"))
    return {
        "schema": "endfield.lizhiyan-after-dof-native-abi.v1",
        "status": "current_build_native_schedule_and_static_shader_abi_closed_live_draw_pending",
        "sources": {
            "gameAssembly": {"path": str(game_assembly), "sha256": EXPECTED["gameAssembly"]},
            "metadata": {"path": str(metadata), "sha256": EXPECTED["metadata"]},
            "shaderContract": {"path": SHADER_CONTRACT.relative_to(REPO).as_posix(),
                               "sha256": EXPECTED["shaderContract"]},
        },
        "codeRegistrationVA": f"0x{CODE_REGISTRATION:x}",
        "methods": methods,
        "decisiveCalls": calls,
        "rendererList": {
            "queue": {"first": 3660, "default": 3700, "last": 3740},
            "sortingCriteria": 87,
            "sortingSemantic": "CommonTransparent | OptimizeStateChanges | RendererPriority",
            "shaderTagsWithoutOutline": ["TransparentBackface", "ForwardOnly", "Forward",
                                          "ForwardCharacterOnly", "SRPDefaultUnlit", "Distortion"],
            "layerMask": "RemoveWorldUILayer(camera.cullingMask)",
            "stateBlock": {"hasValue": False, "source": "zero-initialized nullable"},
            "overrideMaterial": None,
            "excludeObjectMotionVectors": False,
            "perObjectData": "bakedLightingConfig | GetPerObjectMotionVectorConfig(hgCamera)",
            "liveInputsPending": ["cullingResults", "camera", "screenCullingRatio",
                                  "screenCullingRatioDistance", "screenCullingLayerMask",
                                  "outlineEnabled", "bakedLightingConfig", "survivorsAndSortOrder"],
        },
        "attachments": shader["renderScheduling"]["attachments"],
        "callbackExecution": ["profiling", "sceneColor/global texture setup", "fullscreen draw",
                              "forward renderer list", "forward ECS renderer list"],
        "rendererConsumers": {
            "opaqueArgument": False,
            "frameSettingsGate": "TransparentObjects",
            "classic": "CoreUtils.DrawRendererList(renderContext, cmd, rendererList)",
            "ecs": "HGMeshRender.DrawECSRendererList(cmd, rendererListHandle)",
            "consumerResortingOrOverride": "none; descriptor/list construction owns filtering and order",
            "survivorIdentity": "runtime renderer-list and ECS handles pending",
        },
        "shaderAbi": {
            "selectedMaterialGates": shader["selectedMaterialGates"],
            "variantCount": len(shader["variants"]),
            "constantBuffers": shader["variants"][0]["stages"]["fragment"]
                ["staticResourceSemantics"]["constantBuffers"],
            "variantResources": [
                {"materialKeywords": row["materialKeywords"],
                 "texturesAndSamplers": row["stages"]["fragment"]
                    ["staticResourceSemantics"]["texturesAndSamplers"]}
                for row in shader["variants"]
            ],
        },
        "nativeBoundary": {
            "callbackConstantBufferPublication": "not_present",
            "callbackGlobalVectorAndTexturePublication": "present",
            "serializedBindingsAreD3D12RootParameters": False,
            "pending": ["live descriptor-table handles", "root-parameter mapping",
                        "PSO overrides", "physical MRT/depth descriptors",
                        "feature-switch values", "renderer-list survivors/order",
                        "final compositing"],
        },
        "unityDecision": {
            "visibleAdmission": False,
            "vfxParams1PublicationRequiredForSelectedMaterials": False,
            "transformHistoryRequiredForSelectedMaterials": False,
            "reason": "all selected materials serialize _IsSceneEffect=0 and _EnableTransparentMV=0",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-root", type=Path, required=True,
                        help="Explicit Endfield install root containing GameAssembly.dll")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(args.game_root.resolve()), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        require(OUTPUT.is_file() and OUTPUT.read_text(encoding="utf-8") == payload,
                "serialized native ABI contract drifted")
        print("Li Zhiyan after-DOF native ABI contract verified")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(payload, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT}: sha256={sha256(OUTPUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

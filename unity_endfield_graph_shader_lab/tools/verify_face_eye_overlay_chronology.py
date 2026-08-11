#!/usr/bin/env python3
"""Verify the source-closed face/eye/overlay attachment and draw chronology."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
SCRATCH = PROJECT_ROOT / "scratch" / "face_eye_chronology"
SHADER_ROOT = SCRATCH / "current_convert" / "Shader"
RAW_SHADER_ROOT = SCRATCH / "current_raw" / "Shader"
MATERIAL_ROOT = SCRATCH / "current_material_json" / "Material"
OLD_EVIDENCE_ROOT = (
    REPO_ROOT
    / "scratch"
    / "reverse_engineering"
    / "pregbuffer_draw_order_recovery_20260713"
)
TYPE_TREE_MATERIAL_ROOT = OLD_EVIDENCE_ROOT / "original_material_dumps" / "Material"
QUEUE_EVIDENCE = OLD_EVIDENCE_ROOT / "material_scheduling_mapping.json"
NATIVE_EVIDENCE = SCRATCH / "render_native.json"
CHRONOLOGY_EVIDENCE = SCRATCH / "face_eye_overlay_chronology_evidence.json"
PIPELINE = (
    PROJECT_ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Runtime"
    / "Rendering"
    / "HGCompatRenderPipeline.cs"
)
RECOVERED_OVERLAY = (
    PROJECT_ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Shaders"
    / "Recovered"
    / "EndfieldCharacterOverlayShadowRecovered.shader"
)
RECOVERED_SURFACE_ROOT = RECOVERED_OVERLAY.parent
FRACTAL_ROOT = (
    REPO_ROOT
    / "tools"
    / "FractalMiner"
    / "Assets"
    / "Project"
    / "EndField"
    / "HGRP"
    / "packages"
    / "com.hg.render-pipelines"
    / "runtime"
    / "HG"
    / "Rendering"
    / "Runtime"
)


SHADER_HASHES = {
    "HGRP_CharacterNPR_Eye_pE852494D61D6F176.shader":
        "4d106a230222b08969aef1e01235190fb97705a9e8abf2e6e46dc0ad16075947",
    "HGRP_CharacterNPR_Hair_p8FA556110AA47B6F.shader":
        "b9fed00569e540e511212880067ee9568e2b5326e6df347b6c44cd62e9508554",
    "HGRP_CharacterNPR_OverlayShadow_p1B3C2C084B83F71F.shader":
        "bdbdfe6d3b0a511af28612554cfd094a780d7b8f44bd5e05081e3ad11f756252",
    "HGRP_CharacterNPR_Skin_p3E3D05CF72D25122.shader":
        "ee9607ea85796d17006314d48608717427db632987bd46488ec548e033e57374",
}
RAW_SHADER_HASHES = {
    "HGRP_CharacterNPR_Eye_pE852494D61D6F176.dat":
        "07a42fc3488a0e82ba7e66461f38e8b9c1abc609b9d04cde7d19576d98625d62",
    "HGRP_CharacterNPR_Hair_p8FA556110AA47B6F.dat":
        "a0d7c0b6467e04c57c09fae8e422556e8610d504b74e20516333a93a0c3f515f",
    "HGRP_CharacterNPR_OverlayShadow_p1B3C2C084B83F71F.dat":
        "2e339e4ab7d96385efea5007e42c8a8137a88eb898d5ebf91876dfd72919c112",
    "HGRP_CharacterNPR_Skin_p3E3D05CF72D25122.dat":
        "4968b70bc5071b201f31f0016380963da13d4417f17ae51a1679670c4f6a1b0e",
}
SOURCE_HASHES = {
    "ForwardPassUtils.cs":
        "6964668b3ff26e783f60241b243385b18154cebff465d2faca5a3ec331f6360f",
    "TransparentPassConstructor.cs":
        "6d17272fe78d3a90cdd63a753f02061189d7a68a89a98bd059d657884a52f6ae",
    "HGRendererListUtils.cs":
        "59cf2e1bd5be9320fd796acfbbb7f6381211e275d7824ee969f03b3729333084",
    "HGRenderPathDefaultDeferred.cs":
        "14ecad2562d11cb2569a3eef3277859a65743e18f8085979528e5650aaaf90fe",
    "DepthPrepassConstructor.cs":
        "6467925f2e39c6af02a93225ca487f92693b2e163cf4d774d7a347925e1fcaef",
    "GBufferPassConstructor.cs":
        "e1312bf0d541078c802fc5bdde83c580d6fc82c3e8a1a6d21c5bb218964f92d8",
}
FORWARD_TRANSPARENT_QUEUE_TOKENS = (
    "FrameSettingsField__Enum_LowResTransparent",
    "k_RenderQueue_Transparent",
    "k_RenderQueue_TransparentWithLowRes",
    "k_RenderQueue_PreRefraction",
    "FrameSettingsField__Enum_Refraction",
    "k_RenderQueue_AllTransparent",
    "k_RenderQueue_AllTransparentWithLowRes",
    "(PerObjectData__Enum)(additionalConfig | backedLightingConfig)",
    "screenCullingLayerMask",
)
TRANSPARENT_DESCRIPTOR_TOKENS = (
    "HGCamera::RemoveWorldUILayer",
    "v54.screenCullingLayerMask = screenCullingLayerMask;",
    "v54.screenCullingRatio = screenCullingRatio;",
    "v54.screenRatioCullingDistance = screenRatioCullingDistance;",
    "v54.layerMask = m_Mask;",
    "v54.rendererConfiguration = rendererConfiguration;",
    "v54.renderQueueRange = k_RenderQueue_AllTransparent;",
    "v54.overrideMaterial = overrideMaterial;",
    "v54.drawableFeedbackPtr = drawableFeedbackPtr;",
    "v54.excludeObjectMotionVectors = excludeObjectMotionVectors;",
    "IFix::WrappersManagerImpl::IsPatched(2589",
    "IFix::WrappersManagerImpl::IsPatched(1047",
)
GAME_ASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
)
GLOBAL_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
)
UNITY_PLAYER_SHA256 = (
    "b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2"
)
METHOD_SLICES = {
    # file offset, exact method span, SHA-256
    "RenderForwardTransparent": (
        0x9BAB5CC,
        3148,
        "1cc8c118706f7e028b2f5898f15c95a1a984230dcb20e6447aa3eae056179792",
    ),
    "DrawECSMeshRendererListWithSRPRendererList": (
        0x9C07C4C,
        168,
        "128b5bc7f4288906af5a2820a3d51b84e6c86e97588699b03e9c1188415c401a",
    ),
    "TransparentPassConstructor.ConstructPass": (
        0x9BB1BA4,
        4808,
        "a2b5589767b68ff535d2cffa5b6e1ae6d993aafe1b253b398fa6e2cbc2a00226",
    ),
    "CreateTransparentRendererListDesc.Array": (
        0x9C06F04,
        708,
        "08e90a05982967c1f0aa45950fdf24f069fa6b639238ee3f6429fef2de697163",
    ),
}


CURRENT_MATERIALS = {
    # file: (hash, property, exact value)
    "M_eyeshadow_common_01_pFA612A3BFE879A51.json": (
        "8018e13dc37686d0744a416d3b403cc1576cb6fc198613403f53a50331475713",
        "_ShadowOverIris",
        20.0,
    ),
    "M_eyewhiteshadow_common_01_pA423D7A5BCB61B0A.json": (
        "be6fdcf79d7cef355fe1e59085552b16322766a6e8a88eba311fcfee20148f22",
        "_ShadowOverIris",
        4.0,
    ),
    "M_hairshadow_common_01_p1312A50913D98AE9.json": (
        "d876b16ec2825cde0058c2ce44d098e21166b534109cbaa0ebac79116900ec1a",
        "_ShadowOverIris",
        4.0,
    ),
    "M_hairshadow_common_09_p846B48124D0D9DD7.json": (
        "b12f1c0922cf59b3aec2747f677fb6a9b23f16b912f4e12f60ba6088dea37229",
        "_ShadowOverIris",
        4.0,
    ),
    "M_actor_wulfa_eyebrow_01_p009D8AFBB07A0925.json": (
        "ee1efcc7e3ae7d3b04f65303ca75934fd7a2b77953b5aacddee00341800a3ae8",
        "_PreZStencilRefOption",
        52.0,
    ),
    "M_actor_wulfa_iris_01_p21CB671CF4538F4D.json": (
        "59c34e82eaa223bcd569baa98ba719e0266ace4bbd65299ae0cc480086041a39",
        "_PreZStencilRefOption",
        52.0,
    ),
    "M_actor_zhuangfy_brow_01_p6E3CA0A2511057CB.json": (
        "a61cb028547e049ce3027bb7e8dc7642b23049f5369dcf2accc638ac42e9e0b1",
        "_PreZStencilRefOption",
        52.0,
    ),
    "M_actor_zhuangfy_brow_02_p4EFC3A22AF6FF6AC.json": (
        "81e582e22616ba6148088bd80fb53a95f5569aaf6f4b990a104cffb2fd517ea5",
        "_PreZStencilRefOption",
        52.0,
    ),
    "M_actor_zhuangfy_iris_01_p9E8F74E8F81E1178.json": (
        "88dcd537243eaba4e89aacfec5c863c9d3a1c2ecb3daf8122325dd8a0b8bafcd",
        "_PreZStencilRefOption",
        52.0,
    ),
    "M_actor_zhuangfy_iris_02_p2EE8F0B5FFDEC266.json": (
        "3ea5323f450d5f5c5b8045547b02df6a24d19ae0529b907da6a191eac7f6b653",
        "_PreZStencilRefOption",
        52.0,
    ),
    "M_actor_zhuangfy_face_02_pE32D9DC9DC4611C5.json": (
        "aef6ed9bc9cdd11bbfc61c5956d5c2421c2771c48fec31b458ca866fd1ac5129",
        "_PreZStencilRefOption",
        36.0,
    ),
}


DISABLED_OVERLAY_MATERIALS = {
    "M_eyeshadow_common_01_pFA612A3BFE879A51.txt":
        "c8a8bbad46f2bb9f0b5b156b0f864490032e0983079dbbb013a520db0b7d0242",
    "M_eyeshadow_common_05_p65D54F510D76590E.txt":
        "aa0a8cd7ffbc4f175edde6c5bf53fbece1b4eaced2e1a3f3d9a6a8766028e89f",
    "M_eyewhiteshadow_common_01_pA423D7A5BCB61B0A.txt":
        "19c2c8b90f1f28cd79cd1be8a774c672db565551874bdc7686fce335d0cec64f",
    "M_hairshadow_common_01_p1312A50913D98AE9.txt":
        "7007d85d9bbf5d1345ebf98b9d6d78647cc7bb703d88acb3ce34afab87888752",
    "M_hairshadow_common_09_p846B48124D0D9DD7.txt":
        "69fb1e9259a26a0b97549a05de387bf33c98d6f6dcd451c806ebd459252e1eb8",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_hash(path: Path, expected: str) -> None:
    actual = sha256(path)
    if actual != expected:
        raise AssertionError(f"{path}: SHA-256 {actual}, expected {expected}")


def require_tokens(text: str, tokens: list[str], label: str) -> None:
    for token in tokens:
        if token not in text:
            raise AssertionError(f"{label}: missing token {token!r}")


def extract_pass(text: str, pass_name: str) -> str:
    marker = f'Name "{pass_name}"'
    marker_index = text.find(marker)
    if marker_index < 0:
        raise AssertionError(f"missing pass {pass_name!r}")
    pass_index = text.rfind("Pass", 0, marker_index)
    brace_index = text.find("{", pass_index, marker_index)
    depth = 0
    for index in range(brace_index, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[pass_index : index + 1]
    raise AssertionError(f"unterminated pass {pass_name!r}")


def verify_native_submission() -> None:
    require_hash(
        CHRONOLOGY_EVIDENCE,
        "e8a04bea1750d25961dbdfbd1331130ff0d33475bdb8254619d98dc122217675",
    )
    chronology = json.loads(CHRONOLOGY_EVIDENCE.read_text(encoding="utf-8-sig"))
    contract = chronology["transparent_contract"]
    assert contract["depth_attachment"] == "input.sceneDepth"
    assert contract["depth_access"] == "Read"
    assert contract["sorting_criteria_numeric"] == 87
    assert [row["queue"] for row in contract["queue_order"]] == [2900, 2985, 3000]

    require_hash(NATIVE_EVIDENCE, "ffda5baaf138acaf375270c1d8e0bd5d766b37a7f76cdf8a21583a78f1eb050a")
    evidence = json.loads(NATIVE_EVIDENCE.read_text(encoding="utf-8-sig"))
    game_assembly = Path(evidence["metadata"]["gameAssembly"])
    metadata = Path(evidence["metadata"]["metadataPath"])
    unity_player = game_assembly.parent / "UnityPlayer.dll"
    require_hash(game_assembly, GAME_ASSEMBLY_SHA256)
    require_hash(metadata, GLOBAL_METADATA_SHA256)
    require_hash(unity_player, UNITY_PLAYER_SHA256)
    player_bytes = unity_player.read_bytes()
    require_tokens(
        player_bytes.decode("latin-1"),
        [
            "UnityEngine.Rendering.CommandBuffer::AddDrawECSMeshRendererListWithSRPRendererList_Injected",
            "DrawECSMeshRendererListWithSRPRendererList",
        ],
        "custom UnityPlayer mixed renderer-list command registration",
    )

    bodies = {body["method"]: body for body in evidence["bodyTargets"]}
    expected_bodies = {
        "RenderForwardTransparent": (287276, "0x189bacfcc", "0x9bab5cc", 3148),
        "DrawECSMeshRendererListWithSRPRendererList": (
            288211,
            "0x189c0964c",
            "0x9c07c4c",
            168,
        ),
        "ConstructPass": None,
    }
    for method, expected in expected_bodies.items():
        if method == "ConstructPass":
            continue
        body = bodies[method]
        assert (
            body["methodIndex"],
            body["methodPointerVa"],
            body["fileOffset"],
            body["scanBytes"],
        ) == expected

    transparent_construct = next(
        body
        for body in evidence["bodyTargets"]
        if body["type"].endswith("TransparentPassConstructor")
        and body["method"] == "ConstructPass"
    )
    assert (
        transparent_construct["methodIndex"],
        transparent_construct["methodPointerVa"],
        transparent_construct["fileOffset"],
        transparent_construct["scanBytes"],
    ) == (287308, "0x189bb35a4", "0x9bb1ba4", 4808)

    mixed_edges = [
        edge
        for edge in evidence["directCallEdges"]
        if edge["caller"]["method"] == "RenderForwardTransparent"
        and any(
            callee["method"] == "DrawECSMeshRendererListWithSRPRendererList"
            for callee in edge["callees"]
        )
    ]
    assert len(mixed_edges) == 1
    assert (mixed_edges[0]["offset"], mixed_edges[0]["targetVa"]) == (
        2503,
        "0x189c0964c",
    )

    assembly_bytes = game_assembly.read_bytes()
    for label, (offset, length, expected_hash) in METHOD_SLICES.items():
        actual = hashlib.sha256(assembly_bytes[offset : offset + length]).hexdigest()
        if actual != expected_hash:
            raise AssertionError(f"{label}: method-slice hash drifted to {actual}")


def verify_decompiled_render_path() -> None:
    for name, expected in SOURCE_HASHES.items():
        require_hash(FRACTAL_ROOT / name, expected)

    forward = (FRACTAL_ROOT / "ForwardPassUtils.cs").read_text(
        encoding="utf-8-sig", errors="replace"
    )
    transparent = (FRACTAL_ROOT / "TransparentPassConstructor.cs").read_text(
        encoding="utf-8-sig", errors="replace"
    )
    lists = (FRACTAL_ROOT / "HGRendererListUtils.cs").read_text(
        encoding="utf-8-sig", errors="replace"
    )
    require_tokens(
        forward,
        [
            "forwardTransparentECSList = data.fields.forwardTransparentECSList;",
            "data.fields.transparentRenderList",
            "DrawECSMeshRendererListWithSRPRendererList(",
            "forwardTransparentECSList,",
            "HGDrawUIRendererListImpl(",
        ],
        "ForwardPassUtils.RenderForwardTransparent",
    )
    require_tokens(
        forward,
        list(FORWARD_TRANSPARENT_QUEUE_TOKENS),
        "ForwardPassUtils.PrepareForwardTransparentRendererList queue selector",
    )
    require_tokens(
        transparent,
        [
            "&input.sceneDepth,",
            "DepthAccess__Enum_Read,",
            "PrepareForwardTransparentRendererList(",
        ],
        "TransparentPassConstructor.ConstructPass",
    )
    require_tokens(
        lists,
        [
            "v54.sortingCriteria = 87;",
            "DrawECSMeshRendererListWithSRPRendererList(cmd, ecsList",
            "IFix::WrappersManagerImpl::IsPatched(2633",
        ],
        "HGRendererListUtils",
    )
    require_tokens(
        lists,
        list(TRANSPARENT_DESCRIPTOR_TOKENS),
        "HGRendererListUtils.CreateTransparentRendererListDesc descriptor ABI",
    )


def verify_original_shaders_and_materials() -> None:
    for name, expected in SHADER_HASHES.items():
        require_hash(SHADER_ROOT / name, expected)
    for name, expected in RAW_SHADER_HASHES.items():
        require_hash(RAW_SHADER_ROOT / name, expected)

    eye = (SHADER_ROOT / next(name for name in SHADER_HASHES if "_Eye_" in name)).read_text(
        encoding="utf-8-sig", errors="replace"
    )
    hair = (SHADER_ROOT / next(name for name in SHADER_HASHES if "_Hair_" in name)).read_text(
        encoding="utf-8-sig", errors="replace"
    )
    skin = (SHADER_ROOT / next(name for name in SHADER_HASHES if "_Skin_" in name)).read_text(
        encoding="utf-8-sig", errors="replace"
    )
    overlay = (
        SHADER_ROOT / next(name for name in SHADER_HASHES if "_OverlayShadow_" in name)
    ).read_text(encoding="utf-8-sig", errors="replace")
    require_tokens(
        eye,
        [
            "[Enum(Off, 36, On, 52)] _PreZStencilRefOption",
            'Name "ForwardLit"',
            '"LIGHTMODE" = "ForwardCharacterOnly"',
            'Name "PreGBuffer"',
            '"LIGHTMODE" = "DepthCharacterOnly"',
            "Comp Always",
            "Pass Replace",
        ],
        "original eye shader",
    )
    require_tokens(
        hair,
        [
            "[Enum(On, 36, Off, 52)] [HideInInspector] _HairStencilRef",
            'Name "ForwardLit"',
            '"LIGHTMODE" = "ForwardCharacterOnly"',
            'Name "PreGBuffer"',
            "ReadMask 16",
            "WriteMask 239",
            "Comp GEqual",
            "Pass Replace",
        ],
        "original hair shader",
    )
    require_tokens(
        skin,
        [
            'Name "ForwardLit"',
            '"LIGHTMODE" = "ForwardCharacterOnly"',
            'Name "PreGBuffer"',
            '"LIGHTMODE" = "DepthCharacterOnly"',
            "Ref 36",
            "Comp Always",
            "Pass Replace",
        ],
        "original skin shader",
    )
    require_tokens(
        overlay,
        [
            'Tags { "QUEUE" = "Transparent-100"',
            'Name "OverlayShadowPreDepth"',
            '"LIGHTMODE" = "ForwardOnly"',
            'Name "OverlayShadow"',
            '"LIGHTMODE" = "ForwardCharacterOnly"',
            "ReadMask 20",
            "Comp Equal",
            "Pass Keep",
        ],
        "original overlay shader",
    )

    for name, (expected_hash, property_name, expected_value) in CURRENT_MATERIALS.items():
        path = MATERIAL_ROOT / name
        require_hash(path, expected_hash)
        material = json.loads(path.read_text(encoding="utf-8-sig"))
        actual = material["m_SavedProperties"]["m_Floats"][property_name]
        assert actual == expected_value, (name, property_name, actual)

    for name, expected_hash in DISABLED_OVERLAY_MATERIALS.items():
        path = TYPE_TREE_MATERIAL_ROOT / name
        require_hash(path, expected_hash)
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        require_tokens(
            text,
            [
                'string data = "ForwardOnly"',
                'string first = "_EnablePreDepthPass"',
                "float second = 0",
            ],
            name,
        )

    require_hash(
        QUEUE_EVIDENCE,
        "b0904c787e55c6326187aa696b08c971602ced2d8a68c9b4a52ab20334163988",
    )
    queue_evidence = json.loads(QUEUE_EVIDENCE.read_text(encoding="utf-8-sig"))
    assert [
        (row["effective_render_queue"], row["role"])
        for row in queue_evidence["observed_queue_schedule"]
    ] == [
        (2000, "skin/cloth/body/eye/brow/attachments"),
        (2015, "hair"),
        (2900, "overlay shadow"),
        (2985, "hair shell"),
        (3000, "body/cloth layer"),
    ]

    # ReadMask 20 observes bits 0x10 and 0x04. Ref 52 selects eye/brow/iris;
    # ref 36 selects the face/hair side of the same shared attachment.
    assert 52 & 20 == 20
    assert 36 & 20 == 4


def verify_lab_schedule() -> None:
    pipeline = PIPELINE.read_text(encoding="utf-8-sig")
    overlay = RECOVERED_OVERLAY.read_text(encoding="utf-8-sig")
    color_pass = extract_pass(overlay, "OVERLAY_SHADOW")
    predepth_pass = extract_pass(overlay, "PREDEPTH")
    require_tokens(
        color_pass,
        ['Tags { "LightMode"="ForwardCharacterOnly" }', "ReadMask 20", "Comp Equal"],
        "recovered overlay color pass",
    )
    require_tokens(
        predepth_pass,
        ['Tags { "LightMode"="Always" }', "ReadMask 20", "Comp Equal"],
        "bounded recovered overlay predepth compatibility pass",
    )

    recovered_surface_stencil = {
        "EndfieldCharacterSkinRecovered.shader": "Ref [_StencilRefOption]",
        "EndfieldCharacterEyeRecovered.shader": "Ref [_PreZStencilRefOption]",
        "EndfieldCharacterHairRecovered.shader": "Ref [_HairStencilRef]",
        "EndfieldCharacterClothRecovered.shader": "Ref [_PreZStencilRefOption]",
    }
    for name, stencil_ref in recovered_surface_stencil.items():
        surface = (RECOVERED_SURFACE_ROOT / name).read_text(encoding="utf-8-sig")
        forward_pass = extract_pass(surface, "FORWARD")
        require_tokens(
            forward_pass,
            [
                'Tags { "LightMode"="ForwardBase" }',
                stencil_ref,
                "ReadMask 20",
                "WriteMask 20",
                "Comp Always",
                "Pass Replace",
            ],
            f"recovered canonical forward stencil producer {name}",
        )
    for forbidden in (
        'DrawRecoveredAuxiliaryPasses(context, camera, "PREDEPTH");',
        'DrawRecoveredAuxiliaryPasses(context, camera, "OVERLAY_SHADOW");',
    ):
        if forbidden in pipeline:
            raise AssertionError(f"lab still issues compatibility draw {forbidden!r}")

    pass_array = re.search(
        r"private static readonly ShaderTagId\[\] TransparentShaderPasses\s*=\s*\{(?P<body>.*?)\};",
        pipeline,
        re.DOTALL,
    )
    if pass_array is None:
        raise AssertionError("missing recovered transparent pass-name list")
    names = re.findall(r'new ShaderTagId\("([^"]+)"\)', pass_array.group("body"))
    assert names == [
        "TransparentBackface",
        "ForwardOnly",
        "Forward",
        "ForwardCharacterOnly",
        "CharacterOutline",
        "SRPDefaultUnlit",
        "ForwardLit",
        "ForwardBase",
        "UniversalForward",
    ]
    require_tokens(
        pipeline,
        [
            "SortingCriteria.CommonTransparent | SortingCriteria.RendererPriority",
            "ordinaryTransparentLayerMask,",
            "TransparentShaderPasses);",
        ],
        "recovered mixed transparent-list surrogate",
    )


def main() -> int:
    verify_native_submission()
    verify_decompiled_render_path()
    verify_original_shaders_and_materials()
    verify_lab_schedule()
    print(
        "Face/eye/overlay chronology verification passed: current installed "
        "GameAssembly/global-metadata/UnityPlayer, four raw+converted CharacterNPR shaders, "
        "four native method slices, decompiled HGRP sources, exact source "
        "materials, and the 2900/2985/3000 queue inventory are hash-pinned. "
        "Retail uses sceneDepth read-only for one mixed ECS+SRP transparent "
        "submission; overlay ForwardCharacterOnly at 2900 therefore precedes "
        "hair 2985 and body/cloth 3000 on shared stencil. Current overlays "
        "disable ForwardOnly/predepth. The lab preserves that schedule and "
        "CommonTransparent|RendererPriority, with Skin/Eye/Hair/Cloth canonical "
        "forward stencil producers checked. Custom UnityPlayer same-queue tie "
        "ordering and possible runtime IFix patches remain intentionally open."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

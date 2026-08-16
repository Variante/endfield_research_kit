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
BACKEND_OBSERVATION = OUTPUT.with_name("lizhiyan_retail_backend_observation.json")
VIEWER_SCENE = (
    LAB / "Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/"
    "CharacterRecoveryViewer.unity"
)
CODE_REGISTRATION = 0x18B9217D0
EXPECTED = {
    "gameAssembly": "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE",
    "metadata": "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E",
    "unityPlayer": "B47728BA10F09C46E8A107B4C7055E48CFE402D3D8C88A4529074981F9672AA2",
    "shaderContract": "1191F96B45FD11C47D31C71681B25E77B3DF2CBD2179F21B4D2854D3AD90796B",
    "viewerScene": "593CD693538F30CAC0BB381AB31FB160D21212B8C6682072325328DE6CB0B027",
    "backendObservation": "058A57833EB75815963693E4FCCCC4210F8F8EA2AF22BE13B084017657D14EE3",
}
METHODS = [
    (286728, "HG.Rendering.Runtime.HGCamera",
     ".ctor", 0x1837DD570, 0x1837DDD44,
     "00ACC65F4685738CB190BF536900D5AE7B421F4A2CAEDC25C3D2D0B7E2EB3162"),
    (286732, "HG.Rendering.Runtime.HGCamera",
     "DoECSCullingCPP", 0x1834502D0, 0x1834503CE,
     "56CC43CF0F18122D3DE44731D2680F6951F48104A5A2986B9F35161CC883EC7F"),
    (286733, "HG.Rendering.Runtime.HGCamera",
     "DoECSCulling", 0x189B721CC, 0x189B72A1D,
     "ECD06129C7B75CF85A127A5D5E543C956CC9FA4B23C1846A893CAE9464A3AD3E"),
    (286724, "HG.Rendering.Runtime.HGCamera",
     "get_screenCullingLayerMask", 0x183E68CB0, 0x183E68CD4,
     "0D5928FA5F343C7F072A857C5B0FE6CA8943506877C71FA9A6257EF5F2983B7E"),
    (286739, "HG.Rendering.Runtime.HGCamera",
     "Update", 0x183100120, 0x183100171,
     "B5A2AB43A40014751793CA227CD2F535AEF7470A1F3E71A93B24297ED9C40FCC"),
    (286740, "HG.Rendering.Runtime.HGCamera",
     "BeginRender", 0x189B720E0, 0x189B72162,
     "525783A3D1731620269FBA6F156031EFDE5068FFA4ACC3FAFD1B4EFD0EA0948F"),
    (286741, "HG.Rendering.Runtime.HGCamera",
     "UpdateAllViewConstants", 0x189B74308, 0x189B74387,
     "88DFB9FB0D8B0B867A507E41AB2123C6E2830262290A1AB10616FD3A55DA2421"),
    (284150, "HG.Rendering.Runtime.HGRenderPipeline",
     "GetPerObjectMotionVectorConfig", 0x189BC753C, 0x189BC759B,
     "DA8AB25AC903EEAE24FED48535F016BEA19C3BE7A21A7628C67BED63C7C83922"),
    (284093, "HG.Rendering.Runtime.HGRenderPipeline",
     ".ctor", 0x183947230, 0x1839488E2,
     "B0D85048FC518253694C8BD1FC9B9F40C7F14DAA87B95EB180419233B28DD59D"),
    (284103, "HG.Rendering.Runtime.HGRenderPipeline",
     "ConfigureKeywords", 0x189BC6A38, 0x189BC6B7E,
     "BD2E3852A86737D9F2732283AF677FA2A0F4209DD3FFB3F9476C957C67125A10"),
    (284106, "HG.Rendering.Runtime.HGRenderPipeline",
     "Render", 0x183455030, 0x18345A6E4,
     "08CA0296209FB21E02AFC9E2F5B02B06F0CA86A699A26BCD9951099D93F6926A"),
    (284111, "HG.Rendering.Runtime.HGRenderPipeline",
     "ExecuteRenderRequestCPP", 0x183106970, 0x183113581,
     "6EFA8CEFFB982A2B6E4944B79DDDEBD5853166DC3B7CD0A10E8188048E27A6E0"),
    (286702, "HG.Rendering.Runtime.HGCamera",
     "get_enableMV", 0x189B74654, 0x189B7469F,
     "8C1488DC4A09BEB9F142B4EA2DD5CB7B98770D5DE48DA545E94655EE3538B329"),
    (287999, "HG.Rendering.Runtime.HGRenderPathDeferred",
     "OnPreRendering", 0x189BF6CBC, 0x189BF7A9D,
     "E1E497BAD2F5AA44B25F7E6D0F7ECA208CD81F4C49AE8D64070A4FB1D0E6187A"),
    (478062, "UnityEngine.HyperGryph.HGMeshRender",
     "CreateRendererList", 0x18B3FA0A4, 0x18B3FA10F,
     "8C8113556AB580A5337118F93A8B5E7A38BD79A8F656128FE768CF22B727261F"),
    (288027, "HG.Rendering.Runtime.HGRenderPathScene",
     ".ctor", 0x182ED94E0, 0x182ED991D,
     "C0D8BACD8084FAA9D608A95C2F56076A9FBC3FB57AB450AA8A2F403614C11E98"),
    (288006, "HG.Rendering.Runtime.HGRenderPathForward",
     "OnPreRendering", 0x189BF7BDC, 0x189BF7F2B,
     "499191DAF06A7B6985A8684B1435D6CC8DA7ECEA1A3C0623CFBAF8EC671ABCD5"),
    (287274, "HG.Rendering.Runtime.ForwardPassUtils",
     "PrepareAfterDOFTranparentRendererList", 0x189BAB274, 0x189BAB4E2,
     "319799A95260B1717084D16AA8C2E0CCAD668CEDF3E52E9465B99A31EC44A5E0"),
    (287316, "HG.Rendering.Runtime.TransparentAfterDOFPassConstructor",
     "ConstructPass", 0x189BB2E40, 0x189BB346A,
     "D54DCF38AC17E6062573C476BF988FF8CBEE70E89F2B02FB341E5588DA3612CC"),
    (288038, "HG.Rendering.Runtime.HGRenderPathScene",
     "RenderPostProcessPhase1", 0x189BFFEB0, 0x189C009EF,
     "4695B2B6C39CB3522C067976FCC2F2677BC94692382C5611EF9E2EA743F145C5"),
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
    (0x189C0057C, 0x183E68CB0, "Phase1 -> HGCamera.get_screenCullingLayerMask"),
    (0x189C00740, 0x189BB2E40, "Phase1 -> TransparentAfterDOF.ConstructPass"),
    (0x189BF7684, 0x189B73644, "Deferred.OnPreRendering -> RemoveWorldUILayer(-1)"),
    (0x189BF7823, 0x189B7470C, "Deferred.OnPreRendering -> get_enableTransparentAfterDOF"),
    (0x189BF789F, 0x18B3FA0A4, "Deferred.OnPreRendering -> CreateRendererList(TransparentAfterPP)"),
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
    unity_player = game_root / "UnityPlayer.dll"
    metadata = game_root / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat"
    for key, path in (("gameAssembly", game_assembly), ("metadata", metadata),
                      ("unityPlayer", unity_player)):
        require(path.is_file(), f"missing explicitly selected native input: {path}")
        require(sha256(path) == EXPECTED[key], f"selected native input drifted: {key}")
    require(sha256(SHADER_CONTRACT) == EXPECTED["shaderContract"],
            "Li Zhiyan shader ABI contract drifted")
    require(sha256(VIEWER_SCENE) == EXPECTED["viewerScene"],
            "selected CharacterRecoveryViewer scene drifted")
    require(sha256(BACKEND_OBSERVATION) == EXPECTED["backendObservation"],
            "retail graphics-backend observation drifted")
    backend_observation = json.loads(BACKEND_OBSERVATION.read_text(encoding="utf-8"))
    viewer_text = VIEWER_SCENE.read_text(encoding="utf-8")
    require("--- !u!20 &1562276706" in viewer_text and
            "m_Bits: 4294967295" in viewer_text,
            "selected viewer camera identity/culling mask drifted")

    metadata_module = load_module(
        "lizhiyan_after_dof_metadata",
        REPO / "tools/endfield-il2cpp/catalog_option_flow_metadata.py")
    mapper = load_module(
        "lizhiyan_after_dof_mapper",
        REPO / "tools/endfield-il2cpp/map_body_targets_to_gameassembly.py")
    md = metadata_module.Metadata(metadata)
    pe = mapper.PeImage(game_assembly)
    unity_pe = mapper.PeImage(unity_player)
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

    unity_native_spans = [
        ("HGMeshRender.CreateRendererList icall adapter", 0x1801F1E40, 0x1801F1F0E,
         "EB9B02F891CD670E726D8EF73C52D62D40FDC6756BE41BCE76ED8EA901AC153C"),
        ("HGMeshRender renderer-list request packer", 0x18104E7A0, 0x18104E856,
         "8125E686DC149173B7CB2A9FF3D0BA40E41162E72E1D9BC4353BD211ECAF1C7E"),
        ("HGMeshRender renderer-list registration core", 0x18104E300, 0x18104E7A0,
         "9FC913F47D5E88710E13D9C555F2C81F7DAAEBA22C6AEB22F2FAA969170ACC80"),
        ("HGMeshRender renderer-list resource record builder", 0x18104E920, 0x18104EC17,
         "02F2E295CF8BB8247824AA7A3EE6B4E0BAD7D58C1C06D59ECD155CAB6E3C81BD"),
        ("CommandBuffer AddDrawECSMeshRendererList icall", 0x180063180, 0x180063209,
         "2C36DF6649DEF8EB9748739C336F0F33371C81A0892BDCD3100D12BC69E0443F"),
        ("AddDrawECSMeshRendererList opcode writer", 0x1804C77B0, 0x1804C7850,
         "F7D90308048F1EA0A2410C600FB241039B44F14ED278966060F64DBDCE34F8BF"),
        ("HGMesh renderer-list command consumer", 0x181005C10, 0x181005E53,
         "3448107F9F252D1388D908D576542FF6B66E7C0D2B3450CDB9915BC58E2D65C2"),
        ("HGMesh renderer-list resource callback thunk", 0x180FEADE0, 0x180FEADE5,
         "263BDC075313E7654E4E3AECE30F98F04B90E34A187ADFC10BE71BF3D7E7472F"),
        ("HGMesh renderer-list resource callback", 0x181047160, 0x181047280,
         "51FF1225A752F4309247DAFA545ABB237FEF2E9A38BFD1579BDCE6F0A07ADAE6"),
        ("HGMesh 64-byte record sorter", 0x181043BD0, 0x181043D36,
         "5C5EF082DD8E341F18C421C196B90ECF4E17BD8604E43627130DF869E6E8C5B2"),
        ("HGMesh 16-byte sort-key comparator", 0x180FE0740, 0x180FE0766,
         "40944DA8A54834536C143E79E9E555C77220D4DE40F7F206D54B43DD33164D3A"),
        ("HGMesh sorted-record publication entry", 0x18103F160, 0x18103F1B2,
         "82E3367CC8AF44B0D48F4F653A77AFC699086A6EB4853238CB852F11EFE2055A"),
        ("HGMesh sorted-record ID resolver", 0x181059410, 0x181059483,
         "B243001126EEF35B00EA79DF5705EC21C74F9C462C6903BD62CCA7AA7735E303"),
        ("HGMesh sorted-record pointer append", 0x18105E350, 0x18105E36B,
         "A53FE724C2528138F922D4923A10DB06489DF710A8B8AC0D891EE28A41A3EBA4"),
        ("HGMesh 64-byte survivor-record append", 0x18105E400, 0x18105E4CC,
         "62712E9CCFEF1F7614BCCD33785031DEFC6DB9AF132E78885DD5727CB515555F"),
        ("HG render context slot-0x14 accessor", 0x180FC5E60, 0x180FC5E6A,
         "C247F5C67F284C727F1467D68F5AC5551A863009E47967951FAB800CFCB2DBC3"),
        ("HG singleton table indexed accessor", 0x18030F100, 0x18030F10F,
         "E59255837C34F83D3AEC9902E38E1589F3F7BACBD138EEA3F31756783425E089"),
        ("HG singleton table generic setter", 0x18030F5B0, 0x18030F5BF,
         "C5EF3665EB9B1344138CF41D75382729C34CE76CE05FB36142F1D5C0A5EFFF5C"),
        ("HG singleton bulk registrar", 0x180319E60, 0x18031A1E7,
         "6170F0F9E47CF94D6EFA1696C2FCCCE40C180B57F6DA079C543C319218D7729D"),
        ("HG singleton global teardown", 0x18058CC20, 0x18058D46D,
         "8906BE4ECA853038B30BFEF1E6A9AA4F51631BA66CBBD65A510BF392ABFD261F"),
        ("HG singleton generic virtual cleanup", 0x18031AEC0, 0x18031AF0C,
         "7843C1A52391DFC295106F0DB4DF3951681FFD4FB04028A9E2D7B5EC3C6C2105"),
        ("HG singleton nested-resource cleanup", 0x18031AF80, 0x18031B0D7,
         "F02609397543ECC6B0CCECAE38BA64426BB1BF711C10D5FD4AE197505A42C9D1"),
        ("HG slot-0x14 context vtable", 0x181E1C328, 0x181E1C3E0,
         "BDA27AB011238775BB5D588AAF32197902484074443D642CBC86339E222F2B82"),
        ("HG slot-0x14 context constructor", 0x180FC21D0, 0x180FC25F0,
         "0E99AAD0009FCCFF7F7904242EC234EFBEC22693757291606560219BA43B7452"),
        ("HG slot-0x14 context destructor", 0x180FC2E00, 0x180FC2E8F,
         "834A1FE2E1C2A1D22E32A563AB66022295151C5E767DC8B3B52291C264C33042"),
        ("HG slot-0x14 context construction", 0x180FC3500, 0x180FC36A1,
         "47CA93DDAC12DF93FA32FFC7D2C5D7CCC7FCD4240F5618A418CF240E303B7187"),
        ("HG slot-0x14 context subobject construction", 0x180FC7030, 0x180FC807E,
         "9AD6623C33CC7D7A5FE619F2057703327AE89328512E68C53E7605D86F5DDEDA"),
        ("HGMesh manager construction", 0x1810454C0, 0x18104558C,
         "802256A241F4135D1E6F3A06AC0F0EE07AC245E1A248935EF5350155075DCEDF"),
        ("HG slot-0x14 context subobject destruction", 0x180FC3FC0, 0x180FC4C0F,
         "C017D07CB2739600899091DE97D782C1FABD069E76097927E489EB29D8B0BD4B"),
        ("HGMesh manager destruction", 0x1810459F0, 0x181045A17,
         "87D830A411690C6DDDA9CF86DDA74FA125848EC92FFD0A19EBD2BAC9DAA3C488"),
        ("HGMesh manager nested-entry destruction", 0x18105FE30, 0x181060027,
         "E5EEA4CCDC4117C5C6A3E70AF43A3DF6EA0D9C583C3D2B71FB27549EF2CF4739"),
        ("HGMesh manager logical reset", 0x181060330, 0x181060413,
         "3ED02EBE6DAF9221ED85DA089938B8872ED68DAE8CA9CE68CD78742FA584B7AB"),
        ("HG runtime manager type-ID resolver", 0x1807C5240, 0x1807C52C1,
         "62833856294ED99CDBF08D4BDA73FFD80A38766750F883B80E1B0A3A658A38C3"),
        ("HG runtime manager registry lookup", 0x18012BE60, 0x18012BED0,
         "A5997AAFF12FB476035C292B92984AF9951750FDB2CD32C15CFD16B701F23DC2"),
        ("HG runtime manager indirect allocator", 0x18031A370, 0x18031A569,
         "70DE6C7E28EB5FE8E6EAFC081FBABAD1790B858051AE073859FC485D96B1B3E6"),
        ("HG generic opcode 0x2730 producer helper", 0x180623EF0, 0x180624654,
         "707E05C87AC50FACCF48FA9D3B2A726B4632DD98AB399EDFBB03721839249CFC"),
        ("HGMesh publication descriptor-state bridge", 0x180619CF0, 0x180619E70,
         "8BF0F56A5B4FEA3557C92E752E58064FEB13226FB88B285A358D9053788475D7"),
        ("HG generic opcode 0x2731 producer candidate 1", 0x1805A3790, 0x1805A37EF,
         "83703481F4250CA18BF24D88A288476F4A3870A35C7010110C2340A8CF589909"),
        ("HG generic opcode 0x2731 producer candidate 2", 0x1805A37F0, 0x1805A388C,
         "29AF35733B2986E351A9694ED04F496C6F10576438E189ACCCB548281C44D212"),
        ("HGMesh publication result callback thunk", 0x180FEAEA0, 0x180FEAEB0,
         "81B8F2B5B4595C749325A06A9D4D6B29521CA4B4E2616E5D3108A3151517D417"),
        ("HGMesh publication front-end handoff part 1", 0x1810484E0, 0x18104863E,
         "C8A9A53B3526B581D67246D073C5D5CCD15836D60298EB17FA65F48AF74D589C"),
        ("HGMesh publication front-end handoff part 2", 0x18104863E, 0x181048FA7,
         "3D78BF5375EFA462134EDEE4DD2E8046E5D3F879D14C17B63E52F9818829A046"),
        ("HGMesh publication front-end handoff part 3", 0x181048FA7, 0x181049007,
         "FCDFB6FED884A3C3A411D7766740A2FE13D2C59A9C16B841C2DA66E8C4861AA7"),
        ("HG graphics backend selector", 0x18072F7E0, 0x18072F810,
         "BC8214BAE9562674E4E4CB569AE070858C910E735F85E65D705A1C88803BCEDC"),
        ("HG API-2 backend factory", 0x180891210, 0x180891318,
         "0AB4290E23A9DF80B96304DE3859208FFD9F0E66A010CA2D8103D08FE7B9D7C2"),
        ("HG graphics-front context constructor", 0x1809258C0, 0x180925900,
         "0EA52075DDB56042F1EF9D9CAB8EFFAFA307D85FE64B5748C598896391FEC621"),
        ("HG graphics-front vtable", 0x181DCB360, 0x181DCB6E8,
         "8EC9781EC1C410B80E11A79D405528E9F8C0FD65EF9EB5AA7C02C7EA1D020132"),
        ("HG API-2 backend table", 0x181DBC098, 0x181DBCFC8,
         "86EECEFB04596DAB252D480476864310EF833556C4F614C2BEE103E1A86C4E08"),
        ("HG graphics-front opcode 0x2748 writer", 0x180939640, 0x180939751,
         "F3F33DE37A4D10E0F3F46C1D7AC1FF6696A297B5E19283DFC91EC8A111D989B1"),
        ("HG graphics-front opcode 0x274a writer", 0x18093A920, 0x18093AAA4,
         "7D2D4D560E53C0E5C10309850249039A5F73C6660CCC6C2D5D18FDABC9200E48"),
        ("HG low-level command interpreter", 0x1813AEE90, 0x1813BB9BC,
         "6D4D2E594245F8B1267CFE8B39D5D753077D5DC1A163D04356EDCFC792067774"),
        ("HG low-level command dispatch table", 0x1813BB574, 0x1813BB9BC,
         "E51223E243CB963CE476B2FC9AB466D3CA17A312F8A6F7F253D7384D71AAFA19"),
        ("HG API-2 resource-state loop entry", 0x180842370, 0x1808423A4,
         "47B98F080E61F06F8391D385CC3CF95777B5418E34ED72CE161CE012E96ECF2F"),
        ("HG API-2 resource-state loop hot range", 0x180842370, 0x18084283B,
         "C1153C92ACA078C82F59278F3F51119A9454FA67330259B728E0A19047DD17B5"),
        ("HG API-2 resource-state loop cold range", 0x18084283B, 0x180843065,
         "3015D0A8DBF3541D20E390AA7CFFE5F45A35C4B77C02D2787CA10382B03C8D34"),
        ("HG opcode 0x2748 decoder", 0x1813B1624, 0x1813B1694,
         "DAD23669C2757305E4902726B122906E398781C0062DAB1E35444CA23D244602"),
        ("HG opcode 0x274a decoder", 0x1813B16F0, 0x1813B1857,
         "804FE555D51C89DD3AA453DC90802C212B9483D8E49C1589F4D4B9F3124E7356"),
        ("HG opcode 0x2730 descriptor-state handler", 0x1813AFB6B, 0x1813AFECF,
         "F5280DEC414D0CFF6B8C2DF5BE3DF60A04F9FE40E720BBCA03EA048E62198410"),
        ("HG opcode 0x2731 execute handler", 0x1813AFECF, 0x1813AFEE4,
         "0D2414D9A9FDB7CC1D270C248CEA88060A483226C01531AE64D43F50497F0A6D"),
        ("HG graphics-front opcode 0x2730 writer", 0x18093AE10, 0x18093B762,
         "A200B3D694C08C7F99A9D7BAEF230D72435D204368476F4BE4D611882E0698DD"),
        ("HG graphics-front opcode 0x2731 writer", 0x18092E350, 0x18092E639,
         "7B4E200A34EA1C9DB6A1EEF25F8B8B815904C348A59F6F3DBF07D8F5C5E838A0"),
        ("HG graphics-front recording begin", 0x180926F60, 0x180927001,
         "94394D9001A438CC009BD87D52CF273E7EE477BB7CEDE0240AF533845A601B7C"),
        ("HG graphics-front recording end", 0x1809261B0, 0x1809262AE,
         "A960E088B16052E8F53F15F84CD6C04B39BFBC2AD10F5E7FC103C29D06FE1CB2"),
        ("HG bounded-substream parser wrapper", 0x1813AEA00, 0x1813AEA89,
         "53C4234D8425270041E02D8546F0D41987E13BCBF5AED45CE51FC7EEDD24A1E9"),
        ("HG API-2 descriptor-state wrapper", 0x180843BF0, 0x180843CDA,
         "2BE9B903998C6E9208A723FE819CF5D99EDBF757C291973A5CC9CB4A109798E3"),
        ("HG API-2 Vulkan descriptor update", 0x18083F680, 0x1808406C0,
         "F00BA4BA9FFDE864CF0A4BE024E974F5EF8194AEC3DC295CD5AC9C09213A32C9"),
        ("HG Vulkan vertex-index binding callback", 0x18082D6B0, 0x18082D79A,
         "AF9E75A85F4B5207EC3F7570989585122B3842396352C0988CA3F22068E13A1B"),
        ("HG Vulkan pipeline-descriptor state callback", 0x18082E660, 0x18082E754,
         "9C55A6D8EE58B004FEA73473C0EB126EE7DF3E4F399A231F74F4F2A3386D22CB"),
        ("HG Vulkan indirect-draw callback", 0x18082E820, 0x18082E94B,
         "E7BD8B97049438804582C226E553DAFDBC56785337E0D9636AA6BE40AFE173A8"),
        ("HG Vulkan direct-draw helper", 0x18083D264, 0x18083D3A7,
         "12489C1AD1B5940E35DBD716D7EC8F32DD768676F43DB5EDE53F40D184CF7588"),
        ("HG Vulkan master-list executor entry", 0x180843D60, 0x180843F2A,
         "3481D18AE0BD3FC6C2CD9CB7333053C5B8F5500CF8909E3688DEB9C9CB2D37B7"),
        ("HG Vulkan master-list executor continuation", 0x180843F2A, 0x180845386,
         "63A20255D99B7ABD9D3C6B18D7991F8DD391409D505E5C6993A0EB714156BF7B"),
        ("HG Vulkan resource-state callback-list builder", 0x18083E720, 0x18083EC58,
         "072B6F87A4052722F182F63C05894B84FB3833646983DF0268747C497B0C3F46"),
        ("HG Vulkan indirect-draw callback-list builder", 0x18083EC60, 0x18083F13E,
         "06E17D305BFA04AD6D1F1B2630BF8DF6CEA7833CB3DFC786832B600690153B63"),
        ("HG Vulkan master-node packager", 0x180841C40, 0x180841D4A,
         "38FB333878F3D2883A14B148AE9D6432B1345303AAA9414C8FF95AA2C506A46E"),
    ]
    unity_native_methods = []
    for label, va, end, expected_hash in unity_native_spans:
        body = unity_pe.bytes_at_va(va, end - va)
        body_hash = hashlib.sha256(body).hexdigest().upper()
        require(body_hash == expected_hash, f"UnityPlayer native span drifted: {label}")
        unity_native_methods.append({"label": label, "va": f"0x{va:x}",
                                     "functionEnd": f"0x{end:x}",
                                     "functionBytes": len(body),
                                     "functionSha256": body_hash})

    shader = json.loads(SHADER_CONTRACT.read_text(encoding="utf-8"))
    return {
        "schema": "endfield.lizhiyan-after-dof-native-abi.v1",
        "status": "current_build_native_schedule_and_static_shader_abi_closed_live_draw_pending",
        "sources": {
            "gameAssembly": {"path": str(game_assembly), "sha256": EXPECTED["gameAssembly"]},
            "metadata": {"path": str(metadata), "sha256": EXPECTED["metadata"]},
            "unityPlayer": {"path": str(unity_player), "sha256": EXPECTED["unityPlayer"]},
            "shaderContract": {"path": SHADER_CONTRACT.relative_to(REPO).as_posix(),
                               "sha256": EXPECTED["shaderContract"]},
            "viewerScene": {"path": VIEWER_SCENE.relative_to(REPO).as_posix(),
                            "sha256": EXPECTED["viewerScene"]},
        },
        "codeRegistrationVA": f"0x{CODE_REGISTRATION:x}",
        "methods": methods,
        "unityPlayerNativeMethods": unity_native_methods,
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
            "perObjectData": {
                "bakedLightingConfig": 15,
                "motionVectorConfigForNonNullHGCamera": 32,
                "combined": 47,
                "expression": "m_CurrentRendererConfigurationBakedLighting | GetPerObjectMotionVectorConfig(hgCamera)",
                "normalBranchEvidence": "pipeline ctor and ConfigureKeywords write 15; get_enableMV returns true; motion helper returns 32",
                "ifixBoundary": "patch ids 568, 462, and 463 can replace the normal branches",
            },
            "screenCulling": {
                "constructorDefaults": {"ratio": 0.005, "distance": 30.0},
                "hgCameraOffsets": {"ratio": "0x9d8", "distance": "0x9dc", "layerMask": "0xa20"},
                "layerNames": ["Default", "TransparentFX", "Ignore Raycast", "Water", "UI",
                               "Walkable", "Climbable", "Trigger", "UIPP", "UIModel", "Building",
                               "UIInteract", "WorldUI", "Projectile", "AbilityEntity", "Terrain", "IK"],
                "layerMaskConstruction": "lazy LayerMask.GetMask of the 17 names",
                "ratioDistanceWriters": "HGCamera..ctor only among mapped HG.RenderPipelines.Runtime methods",
                "layerMaskWriters": [
                    "HGCamera..ctor initializes 0xffffffff",
                    "HGCamera.DoECSCullingCPP copies lightweight-camera results +0x168/+0x16c",
                    "HGCamera.DoECSCulling rewrites current/lightweight camera masks",
                    "HGRenderPipeline.Render propagates lightweight-camera results",
                ],
                "requestPropagation": "ExecuteRenderRequestCPP copies ratio/distance to request +0x68/+0x6c, then reads the layer-mask getter",
                "descriptorBoundary": "values travel through custom request/PassInput data; ordinary Unity RendererListDesc has no equivalent fields",
                "runtimeInstanceValues": "pending selected-camera observation; layer mask is runtime-mutated and cannot be assumed to remain 0xffffffff",
                "unityEquivalent": "standard DrawRenderers exposes no HG screen-culling fields",
            },
            "passInputOffsets": {
                "characterOutlineEnabled": "0x00",
                "forwardTransparentAfterDOFECSList": "0x04",
                "screenCullingLayerMask": "0x08",
                "screenCullingRatio": "0x0c",
                "screenCullingRatioDistance": "0x10",
                "bakedLightConfig": "0x14",
                "shadowResult": "0x18",
                "cullingResults": "0x58",
                "sceneColor": "0x68",
                "sceneDepth": "0x78",
                "sceneMV": "0x88",
                "hgrp": "0x98",
                "bytes": 160,
            },
            "ecsRendererListProducer": {
                "owner": "HGRenderPathDeferred.OnPreRendering",
                "field": "m_forwardTransparentAfterDOFECSList",
                "fieldOffset": "0x1388",
                "handleType": "System.UInt32",
                "constructorSentinelWriteVA": "0x182ed9507",
                "validGate": "HGGraphicsFeatureManager.forwardTransparent.enabled && hgCamera.enableTransparentAfterDOF",
                "invalidSentinel": 4294967295,
                "createCallVA": "0x189bf789f",
                "createTargetVA": "0x18b3fa0a4",
                "viewHandle": "hgCamera.cullingViewHandle",
                "renderFlagsMask": "0x4400 (TransparentAfterPP | ShadowOnly)",
                "renderFlagsValue": "0x4000 (TransparentAfterPP)",
                "lightModeMask": "0x20e0 | (characterOutlineState << 9)",
                "globalKeywords": 0,
                "multiDraw": True,
                "transparentSorting": True,
                "cullingLayerMask": "HGCamera.RemoveWorldUILayer(0xffffffff)",
                "noAlphaTest": False,
                "excludeGPUDriven": False,
                "lifecycle": "recreated or reset to 0xffffffff by deferred OnPreRendering each camera frame",
                "phase1ReadVA": "0x189c00568",
                "forwardPath": "HGRenderPathForward.OnPreRendering creates ordinary transparent/opaque/pre-Z lists but never writes 0x1388 or creates a 0x4400/0x4000 AfterPP list",
                "nativeAdapter": {
                    "icallSignature": "UnityEngine.HyperGryph.HGMeshRender::CreateRendererList(System.UInt32,System.UInt32,System.UInt32,System.UInt32,System.UInt16,System.IntPtr,System.Boolean,System.Boolean,System.UInt32,System.Boolean,System.UInt32*,System.Boolean)",
                    "registrationIndex": 395,
                    "unityPlayerVA": "0x1801f1e40",
                    "functionEnd": "0x1801f1f0e",
                    "functionBytes": 206,
                    "functionSha256": "EB9B02F891CD670E726D8EF73C52D62D40FDC6756BE41BCE76ED8EA901AC153C",
                    "requestPackerVA": "0x18104e7a0",
                    "registrationCoreVA": "0x18104e300",
                    "resourceRecordBuilderVA": "0x18104e920",
                    "behavior": "canonicalizes arguments, packs a 0x68-byte request, and registers a list handle; contains no entity iteration, survivor writes, sort loop, multi-draw dispatch, or final draw",
                        "handleTable": {
                            "vectorBaseOffset": "0x08",
                            "countOffset": "0x18",
                            "encodedCapacityOffset": "0x20",
                            "slotStride": 16,
                        "returnedHandle": "zero-based append index (old count)",
                        "slotIdOffset": "0x00",
                        "slotStatePointerOffset": "0x08",
                            "stateBytes": 48,
                            "stateCallbackVA": "0x1810398f0",
                            "registrationLifecycle": "reads the old count as the handle, grows through 0x1802ed7d0 -> 0x180662870 when required, increments count, zeroes the new slot, allocates a 0x30-byte state through 0x1802fd650, and stores it at slot +0x08",
                            "consumerMutation": "opcode 0x4e consumer 0x181005c10 reads slot +0x08 but does not modify the manager vector or count",
                            "resetAudit": "no count decrement, in-place reset, slot-clear loop, free, or reuse owner occurs in the pinned registration/interpreter/consumer spans; external context replacement or teardown remains possible",
                            "contextOwnership": {
                                "slotAccessorVA": "0x180fc5e60",
                                "indexedAccessorVA": "0x18030f100",
                                "singletonTableVA": "0x182168800",
                                "contextSlot": "0x14",
                                "contextPointerCellVA": "0x1821688a0",
                                "managerOffset": "0xb0",
                                "parallelHGTreeOffset": "0xc0",
                                "genericSetterVA": "0x18030f5b0",
                                "bulkRegistrarVA": "0x180319e60",
                                "bulkRegistrarBehavior": "loops indices 0..0x15 and conditionally writes slot 0x14 through the generic setter",
                                "globalTeardownVA": "0x18058cc20",
                                "globalTeardownBehavior": "walks indices 0x1a down to 1, invokes object cleanup, and necessarily clears slot 0x14 through the generic setter",
                                "genericCleanupVA": "0x18031aec0",
                                "nestedCleanupVA": "0x18031af80",
                                "genericCleanupBehavior": "releases object +0x10 through nested cleanup, then invokes object vtable slot 0 before the singleton cell is cleared",
                                "contextVtableVA": "0x181e1c328",
                                "contextDestructorVA": "0x180fc2e00",
                                "contextConstructorVA": "0x180fc21d0",
                                "contextInitializationVA": "0x180fc3500",
                                "subobjectConstructionVA": "0x180fc7030",
                                "managerAllocation": "0x180fc7030 allocates 0x70 bytes, calls 0x1810454c0 with type/category 0xb5, and stores the result at context +0xb0",
                                "managerLayout": "+0x00 type/category 0xb5, +0x08 entry vector base, +0x18 count, +0x28 auxiliary allocation; entries are 16 bytes",
                                "managerResetVA": "0x181060330",
                                "managerDestructionVA": "0x1810459f0",
                                "managerNestedEntryDestructionVA": "0x18105fe30",
                                "managerDestruction": "context cleanup 0x180fc3fc0 calls 0x1810459f0; it destroys nested entries, frees +0x28 and +0x08 storage, clears count, and frees the 0x70-byte manager",
                                "registryFactoryPath": "bulk registrar 0x180319e60 resolves a binary descriptor to a runtime type ID through 0x1807c5240, looks it up through 0x18012be60, and ultimately allocates through runtime descriptor callback [descriptor+0x08] at 0x18031a370",
                                "registryFactoryBoundary": "the slot-0x14 descriptor is an unreadable globalgamemanagers binary prefix and its allocator callback is initialized dynamically; no static type-name or callback identity is proven",
                                "provenBoundary": "slot-0x14 context vtable/constructor/initialization/destruction, +0xb0 HGMesh-manager allocation/reset/nested-entry destruction, and global cell clearing are proven; the runtime registry descriptor name and allocator callback identity remain unresolved",
                            },
                        },
                    "invalidRequestGate": "request[0] == 0xffffffff returns 0xffffffff without appending",
                    "maskCombination": "view record +0x40/+0x48 OR request +0x50/+0x58",
                    "nextConsumerBoundary": "HGMesh opcode 0x4e reaches 0x181005c10; survivor/order/final draw remain downstream of its resource callback",
                    "commandConsumer": {
                        "family": "HGMeshRender (distinct from HGTree opcode 0x55)",
                        "commandBufferIcallVA": "0x180063180",
                        "opcodeWriterVA": "0x1804c77b0",
                        "opcode": "0x4e",
                        "interpreterCaseVA": "0x1804ce43a",
                        "managerSingletonOffset": "0xb0",
                        "consumerVA": "0x181005c10",
                        "slotStride": 16,
                        "slotStatePointerOffset": "0x08",
                        "callbackThunkVA": "0x180feade0",
                        "callbackVA": "0x181047160",
                        "behavior": "validates the 0xffffffff sentinel, resolves the same 16-byte HGMesh slot, constructs command/resource state, and installs a resource-lifetime callback; no entity iteration, survivor write, sort loop, indirect draw, or queue submission is present",
                        "excludedParallelFamily": "HGTree uses CommandBuffer opcode 0x55, singleton +0xc0, 24-byte slots, and consumer 0x18106aae0",
                    },
                    "survivorSortPublication": {
                        "workerSelection": "resource builder 0x18104e920 chooses one of 14 post-filter record workers from live request/view/resource flags",
                        "recordStride": 64,
                        "sortVA": "0x181043bd0",
                        "sortHelpers": ["0x181042950", "0x181042fc0"],
                        "comparatorVA": "0x180fe0740",
                        "comparatorKeyBytes": 16,
                        "comparator": "unsigned-byte lexicographic order over record bytes 0x00..0x0f",
                        "recordAppendVA": "0x18105e400",
                        "keyConstructionScope": "worker-family-dependent packed layout; 0x18105e400 preserves record byte order, but the quantized-float rank is not assigned to one universal dword",
                        "workerKeyLayouts": {
                            "standardFamily": [
                                "dword 0 combines ((asuint(float) >> 15) & 0xffff) with a selector shifted by 16",
                                "dword 1 packs a masked 20-bit source, another selector shifted by 20, then a byte lane",
                                "dword 2 packs context/resource state plus a conditional 0x01000000 marker",
                                "dword 3 packs type/context/index selectors",
                            ],
                            "alternateFamily": [
                                "dword 0 packs a masked 20-bit source, another source shifted by 20, and a byte flag",
                                "dword 1 combines source +0x08, a byte selector, and a 16-bit source value",
                                "dword 2 combines source +0x0c, selector bits, and a conditional 0x01000000 marker",
                                "dword 3 combines context byte state, source +0x22 u16, and ((~asuint(float)) >> 17) & 0x3fff",
                            ],
                        },
                        "semanticKey": "opaque packed renderer-state key; byte/bit construction is proven but field names remain unresolved",
                        "commonAcceptanceGates": [
                            "(source[0x10:0x20] & context[0x40:0x50]) == 0",
                            "(source+0x10 qword & context+0x50 qword) != 0",
                            "source+0x10 has at least one 0x60000 bit",
                            "source+0x10 has at least one 0x7f00 bit",
                            "(source+0x10 & 0xc0) == 0xc0",
                            "context+0x34 & viewMask[index] != 0",
                            "source bit 45 is clear",
                        ],
                        "variantGate": "four resource-state worker variants additionally require signed dword source+0x2c > 0 in the source+0x18 bit-15 path",
                        "workerSelectionFields": "request +0x28 multiDraw, +0x29 transparentSorting, +0x30 noAlphaTest plus live resource presence; excludeGPUDriven is request +0x40 and is not independently reread as a worker-local Boolean",
                        "invalidRecordGate": "publication skips record +0x20 == 0xffffffff",
                        "idResolverVA": "0x181059410",
                        "idResolverSemantics": {
                            "inputEncoding": "key=record_dword_0x20>>1; selector=record_dword_0x20&1",
                            "lookup": "0x1801f7410 searches the ctx+0x18 table whose bounded size is derived from ctx+0x20",
                            "resourceTable": "the found entry +0x08 indexes ctx+0x10 at 0x80-byte stride",
                            "selector0": "returns the 0x80-byte resource record base",
                            "selector1": "returns resource record +0x78",
                            "identityBoundary": "this is an internal ID-table selector, not ordinary Renderer entityID +0x268 or HGMeshRenderer entity +0x50",
                        },
                        "pointerAppendVA": "0x18105e350",
                        "cpuPublicationBoundary": {
                            "helperVA": "0x1810469a0",
                            "behavior": "packs CPU publication/result arrays and derived resource pairs; downstream outputs use 0x90-byte stride",
                            "excludedDirectEdges": [
                                "ordinary per-draw resolver 0x1804255f0",
                                "Renderer +0x268",
                                "HGMeshRenderer +0x50",
                                "material identity",
                                "queue 3704",
                                "descriptor or PSO update",
                                "draw or queue submit",
                            ],
                            "callbackTrampolines": ["0x18103adbc", "0x18103bd0c", "0x18103cc7c", "0x18103decc", "0x18103f11c", "0x18104034c"],
                            "callbackRoute": "each finalizer stores the output object at callback+0x08 and 0x180feaea0 at callback+0x10; the thunk enters 0x1810484e0, which replays the same key/selector and 0x80-byte resource-table resolver semantics before API-2 dispatch",
                            "result": "record publication reaches an internal 0x80-byte resource table, CPU arrays, and the API-2 resource-recording callback; one particular final draw identity is not yet statically proven",
                        },
                        "provenPipeline": "post-filter 64-byte records -> in-place key sort -> invalid-record skip -> ID/resource resolve -> pointer-vector publication",
                        "backendBoundary": {
                            "resultCallbackThunkVA": "0x180feaea0",
                            "frontEndHandoffVA": "0x1810484e0",
                            "frontEndHandoffEndVA": "0x181049007",
                            "behavior": "consumes the CPU publication/result object, repeats its resource-table lookup, records 0x2748/0x274a, invokes resource-array builders, and has a descriptor-mode-conditional path to opcode 0x2730; neither Li's branch value nor a same-AfterDOF-interval 0x2731/particular draw identity is proven",
                            "publicationResultLayout": "pair +0x00 is a 0x90-stride CPU-record base, +0x08 auxiliary resource/state, +0x10 count; each record keeps resource/object +0x08 and descriptor +0x10 among selector/payload fields",
                            "graphicsFront": {
                                "contextGetterVA": "0x180725dc0",
                                "constructorVA": "0x1809258c0",
                                "vtableVA": "0x181dcb360",
                                "backendObjectOffset": "0x2708",
                                "recordingModeOffset": "0x2711",
                                "resourceAppendSlot": "vtable +0x268 -> 0x180939640, opcode 0x2748",
                                "resourceBindSlot": "vtable +0x280 -> 0x18093a920, opcode 0x274a",
                                "descriptorUpdateSlot": "vtable +0x2a0 -> 0x18093ae10, opcode 0x2730",
                                "executeSlot": "vtable +0x3e8 -> 0x18092e350, opcode 0x2731",
                                "beginRecordingSlot": "vtable +0xf78 -> 0x180926f60 sets context +0x2711 and selects context +0x2720",
                                "endRecordingSlot": "vtable +0x880 -> 0x1809261b0 clears context +0x2711 and may append control opcode 0x27cb",
                            },
                            "commandInterpreter": {
                                "interpreterVA": "0x1813aee90",
                                "dispatchTableVA": "0x1813bb574",
                                "opcode2748CaseVA": "0x1813b1624",
                                "opcode2748Layout": "u32 opcode, alignment/padding, aligned u64 resource-object pointer; writer increments resource +0x0c",
                                "opcode2748Route": "front +0x268 -> record 0x2748 -> interpreter -> selected backend +0x268 -> 0x1808547c0 -> mode 1 at 0x180842370",
                                "opcode274aCaseVA": "0x1813b16f0",
                                "opcode274aLayout": "u32 opcode, alignment/padding, u64 token-or-length-like result of 0x1805d1e80, then variable serialized payload",
                                "opcode274aRoute": "front +0x280 -> record 0x274a -> interpreter -> selected backend +0x280 -> 0x180855200 -> mode 0 at 0x180842370",
                                "api2ResourceCollection": "context +0x2e48, 16-byte records holding payload/key at +0x00 and type/key at +0x08",
                                "sharedRecorder": "all 0x2748/0x274a/0x2730/0x2731 writers for one graphics-front instance share context +0x2711 recording flag, +0x2720 command buffer, buffer +0x140 base, +0x148 cursor, and +0x14c capacity; append order equals invocation order",
                                "opcode2730Layout": "u32 opcode, eight-byte alignment, seven u64 values, u32 element count, then count*u32 payload; dispatches to API-2 +0xe90",
                                "opcode2731Layout": "u32 opcode only; dispatches to API-2 +0xde8 with no payload",
                                "batchBoundary": "begin recording selects the current buffer and enables append; end recording disables append and may emit 0x27cb; bounded-substream parser 0x1813aea00 repeatedly advances one shared cursor",
                                "sequenceBoundary": "the HGMesh front has a descriptor-mode-conditional static path to 0x2730 on the same recorder family, but Li's branch value is unknown and no static producer edge proves a later 0x2731 occurs in the same AfterDOF recording interval or belongs to this draw-list",
                                "handoffWriterOrder": "within each 0x90-byte HGMesh publication record, 0x181048848 invokes front +0x268 with record resource at +0x60, then 0x1810488dc invokes front +0x280 with its local serialized payload on the same graphics-front context",
                                "descriptorProducerRoute": "0x1810487e1 -> 0x180619cf0; descriptor+0x450 conditionally selects 0x180623d80, 0x180623e70, or 0x180623ef0. Only the 0x180623ef0 branch reacquires the graphics-front family through 0x180725dc0 and invokes vtable +0x2a0 at 0x1806243d3, the 0x2730 writer",
                                "resourceBuilderCalls": "0x181048dc7/0x181048f2f invoke vtable +0xda0 and 0x181048df8/0x181048f60 invoke +0x380; these enter the API-2 resource-array builder family rather than directly issuing a draw",
                                "handoffExcludedWriter": "0x1810484e0..0x181049007 has no direct front +0x3e8 (0x2731) invocation; the +0x2a0 edge is indirect through 0x180619cf0 -> 0x180623ef0",
                                "executeProducerCandidates": "getter-backed 0x1805a3790/0x1805a37f0 invoke +0x3e8 on the same recorder family, but no static edge places either call in this AfterDOF recording interval",
                                "executeBracket": "0x1805a3790 success path invokes runtime callback [0x1821afd40](1), calls 0x1805a37f0 -> graphics-front +0x3e8/0x2731, then invokes the same callback with 0; the HGMesh callback has no static edge into this bracket",
                                "resourceToBindingState": "0x2748 passes the original pointer unchanged; 0x180842370 resolves object-local maps at resource +0x20..+0x30/+0x50/+0x70 and writes descriptor-like state under S+0x2a0 plus payload backing under S+0x22d0",
                                "provenBoundary": "both opcodes are API-2 resource/state operations, not draw opcodes; 0x2748 identity reaches backend binding state while the 0x274a qword semantics remain unresolved",
                            },
                            "backendSelection": {
                                "selectorVA": "0x18072f7e0",
                                "api2FactoryVA": "0x180891210",
                                "api2TableVA": "0x181dbc098",
                                "api2Meaning": "internal Hypergryph backend-family ID, not Unity's public GraphicsDeviceType numeric enum",
                                "vulkanDrawFlush": "API-2 +0xde8 -> 0x18083f1e0 -> 0x180843d60 resolves Vulkan pipeline/descriptor/draw/queue operations",
                                "vulkanCommandCells": "vkCmdDraw 0x1821d35b0, vkCmdDrawIndirect 0x1821d35c0, vkCmdDrawIndexedIndirect 0x1821d35c8, vkQueueSubmit 0x1821d32c0",
                            },
                            "vulkanExecution": {
                                "descriptorUpdateRoute": "opcode 0x2730 -> API-2 +0xe90 0x180843bf0 -> 0x18083f680 -> vkUpdateDescriptorSetWithTemplate at 0x18083f89d",
                                "descriptorIdentityBoundary": "the HGMesh front conditionally reaches the generic 0x2730 producer when descriptor+0x450 selects 0x180623ef0, and the handler packages S+0x22d0/S+0x22a8/S+0x2a0 into the Vulkan descriptor-update worker; Li's selected branch and the later 0x2731 interval/draw-list attribution remain open",
                                "callbackListBuilders": "API-2 +0xda0 0x18083e720 builds resource-binding and pipeline/descriptor-state child nodes; +0xda8 0x18083ec60 builds an indirect-draw child node; 0x180841c40 packages child heads +0x2b58/+0x2b60 into master nodes at +0x2b50",
                                "resourceBindingNode": "0x68-byte node callback reaches 0x18082d6b0; payload includes wrapper/resource handle, index format/offset, vertex-buffer pointer range, and vertex offsets",
                                "pipelineDescriptorNode": "0x40-byte node callback reaches 0x18082e660; payload includes pipeline, layout, stencil/depth state, descriptor-set array/count, and dynamic offsets",
                                "indirectDrawNode": "0x50-byte node callback reaches 0x18082e820; payload adds indirect buffer/resource +0x30 and byte offset +0x38, draw count 1, stride 0",
                                "hgmeshAttributionBoundary": "the ordinary HGMesh renderer-list wrappers and publication handoff contain no static +0xda8, +0xde8, indirect-draw, or queue-submit edge; +0xda0/+0xda8 nodes are generic API-2 capabilities and must not be attributed to HGMesh without runtime identity",
                                "masterList": "context +0x2b50; callbacks are invoked through [node+0x08] with payload node+0x10 by 0x180843d60",
                                "resourceBinding": "0x18082d6b0 binds index and vertex buffers",
                                "pipelineDescriptorState": "0x18082e660 binds pipeline/descriptors and sets depth bias/stencil reference",
                                "indirectDraw": "0x18082e820 issues vkCmdDrawIndexedIndirect or vkCmdDrawIndirect",
                                "directDraw": "0x18083d264 updates a descriptor template, binds pipeline/descriptors, then issues vkCmdDraw(3,1,0,0)",
                                "queueSubmitCallsites": ["0x180844a09", "0x180844bd3"],
                                "commandStreamInvariantBoundary": "0x2730 and 0x2731 are independent parser cases on one cursor. 0x2730 stores no mandatory-next flag/generation; 0x2731 has no payload and does not read 0x2730 identity. API-2 +0xde8 can package and execute current child lists without a preceding 0x2730",
                                "remainingIdentityEdge": "proof that Li selects the 0x180623ef0/0x2730 descriptor branch, that a later 0x2731 execution occurs in the same AfterDOF recorder interval, and that the resulting +0x2b50 callback node is the particular HGMesh draw record rather than another shared-recorder command",
                            },
                            "d3d12StaticBoundary": "D3D12 is absent and the image contains 'D3D12 support not compiled in!'; D3D11 dynamic bootstrap/fallback code exists but is not the observed session backend",
                            "observedRuntimeBackend": backend_observation,
                            "activeBackend": "Vulkan is proven by the recorded 2026-08-15 installed-client log session and the API-2 table resolves Vulkan draw/submit operations; the log lacks a UnityPlayer hash and no HGMesh resource identity is yet joined to a specific Vulkan command",
                        },
                        "notYetProven": ["semantic names of packed key fields", "HGMesh-derived descriptor state reaching one specific Vulkan draw/submit and visible pixel", "slot-0x14 registry factory identity"],
                    },
                    "runtimeCaptureBoundary": {
                        "authorization": "contract only; attaching or injecting into the retail process requires separate explicit authorization",
                        "retailOracle": "videos/2026-08-15_10-32-32.mkv, Li Zhiyan 38-47 s, strongest hand-adjacent teal layer near 40 s",
                        "observationOnlyHooks": [
                            "0x1801f1e40 CreateRendererList adapter",
                            "0x18104e300 registration core",
                            "0x181005c10 opcode-0x4e consumer",
                            "0x18105e400 complete 64-byte record append",
                            "0x18105e350 resolved-resource pointer append",
                            "0x1813b1624 opcode-0x2748 decoder preserving the resource pointer",
                            "0x18083f89d Vulkan descriptor-template update callsite",
                            "0x1813afed9 opcode-0x2731 API-2 execution dispatch",
                        ],
                        "boundedFields": [
                            "session/PID/module hashes, monotonic timestamp, thread ID, and present interval",
                            "renderer-list handle, manager count, 16-byte slot, and 0x30-byte state",
                            "complete 64-byte record, first 16 key bytes, +0x20 marker, +0x22 u16, +0x2c signed field, and resolved resource pointer",
                            "0x2748 stream position/object pointer, matching 0x2730 descriptor-update state, 0x2731 execution position, callback node, and Vulkan draw parameters",
                        ],
                        "requiredPositiveJoin": "same build and frame: CreateRendererList handle -> opcode 0x4e consumer -> accepted/sorted 64-byte record -> resolved resource identity -> specific Vulkan draw/submit -> visible Li Zhiyan after-DOF pixel",
                        "negativeControl": "repeat with Li Zhiyan absent or replaced by Wulfa; timing coincidence alone is insufficient",
                        "stopRule": "stop on attach refusal, protection termination, module/hash/prologue drift, or target instability; never retry through evasion",
                    },
                },
            },
            "liveInputsPending": ["cullingResults", "camera", "screenCullingRatio",
                                  "screenCullingRatioDistance", "screenCullingLayerMask",
                                  "outlineEnabled", "screen-culling instance values",
                                  "survivorsAndSortOrder"],
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
            "selectedViewerCamera": {
                "fileID": 1562276706,
                "unityCullingMask": 4294967295,
                "serializedHGScreenCullingOverrides": False,
            },
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

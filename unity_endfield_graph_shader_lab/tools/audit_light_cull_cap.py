#!/usr/bin/env python3
"""Audit the installed retail punctual-light shortlist and cap contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
GAME_ROOT = Path(r"D:/Program Files/Endfield Game")
GAME_ASSEMBLY = GAME_ROOT / "GameAssembly.dll"
GLOBAL_METADATA = GAME_ROOT / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat"
INIT_BUNDLE_CHUNK = (
    GAME_ROOT
    / "Endfield_Data/StreamingAssets/VFS/0CE8FA57/"
    "19F0903A12BA87C0D43E67E64889B525.chk"
)
HGRP_ROOT = (
    REPO_ROOT
    / "tools/FractalMiner/Assets/Project/EndField/HGRP/packages/"
    "com.hg.render-pipelines/runtime/HG/Rendering/Runtime"
)
DEVICE_TYPE_SOURCE = HGRP_ROOT / "HGDeviceType.cs"
SETTING_HUB_SOURCE = HGRP_ROOT / "HGRenderPipelineSettingHub.cs"
SETTING_PARAMETERS_SOURCE = HGRP_ROOT / "HGSettingParameters.cs"
LIGHT_CLUSTER_SOURCE = HGRP_ROOT / "LightClusteringPassConstructor.cs"
IFIX_STATE = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/"
    "CharInfoPresentation/installed_ifix_patch_state.json"
)
DEFAULT_EXTRACTED_ROOT = (
    REPO_ROOT
    / "scratch/animestudio/light_cull_cap/"
    "text_assets_selected/TextAsset"
)
OUTPUT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/"
    "CharInfoPresentation/light_cull_cap_recovery.json"
)

EXPECTED_HASHES = {
    "game_assembly": "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce",
    "global_metadata": "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e",
    "init_bundle_chunk": "cbc87c7d8f41d90da25af7758cf77ced7321d19c52c067f6f77a75aa5dabc380",
    "device_type_source": "8cde77dfadb6b857ceb1dc5c92eec460cac1d49eb2ccbd948619699c69ed84b5",
    "setting_hub_source": "0ab0fd1fb0fa6aaa52a2acc2544503f7379487d96b47a31bcaf4e3d525f1b761",
    "setting_parameters_source": "0ea7d61931aa014fb7ebca149380da2804fc8d5e07705e941bf6474b74a55ce9",
    "light_cluster_source": "a81ef9843339141a86c910a6915ab96e647f1f43c25631d537fe872ef4ead888",
    "ifix_state": "b9ab981b65caa0b2a16d9603812c18236ad0aa5af255cb06614e7441cdef45d1",
}

TEXT_ASSETS = {
    "SettingFiles": (
        "SettingFiles_pA5D65C734C247CA7.txt",
        "6031cb98e345cd347830658d3661067af0a6b34ca58f92bc5f9ee6f0ed75d14c",
        "0xA5D65C734C247CA7",
    ),
    "HGRenderPipelineSettings": (
        "HGRenderPipelineSettings_p0EA7FF83EAC093AD.txt",
        "05a4fb96d13a4766757c965df6c5c2a478964ab40d8d2df31659a39e6b710abf",
        "0x0EA7FF83EAC093AD",
    ),
    "CommonSettings": (
        "CommonSettings_p2936E10EDCE2C9E4.txt",
        "aed529949a67769c9066ead730aea1f4144cc8f9ecd63d5debf6e59670649049",
        "0x2936E10EDCE2C9E4",
    ),
    "DesktopSettings": (
        "DesktopSettings_p99C7C961A15A8994.txt",
        "a4a0b652162a13e5c5cad39e7c290641dd83116b984d884e246cacf7991f1f10",
        "0x99C7C961A15A8994",
    ),
    "CloudDesktopOverride": (
        "CloudDesktopOverride_p4CDB7A1FBABEC323.txt",
        "439af33ecca9b7b400a6b92b17ca279b488d47652b04296d95d868b85a7be7f4",
        "0x4CDB7A1FBABEC323",
    ),
    "ConsoleSettings": (
        "ConsoleSettings_p6DB117C9F26E1FCE.txt",
        "0d077462addf6478a90abf6584f6e0844c8b3ef0ff929465dc6c04c6b2e3ea69",
        "0x6DB117C9F26E1FCE",
    ),
    "MobileSettings": (
        "MobileSettings_p883CA7EF83FC2F7C.txt",
        "f9f3388bf3ddb6c0dfbecdac952244044589acb4bb6d7231f0e41a968e463a72",
        "0x883CA7EF83FC2F7C",
    ),
    "CinematicSettings": (
        "CinematicSettings_p02A48AAA604195BF.txt",
        "c0cd749dd829222aab2a2761e0ca7e61ed0d72e87dd2d294a3c65e2bc9358c73",
        "0x02A48AAA604195BF",
    ),
}

EXPECTED_SETTING_FILES = [
    "CommonSettings.ini",
    "ConsoleSettings.ini",
    "DesktopSettings.ini",
    "CloudDesktopOverride.ini",
    "MobileSettings.ini",
    "CinematicSettings.ini",
    "HGRenderPipelineSettings.ini",
]

EXPECTED_INCLUDE_ROUTES = {
    "Common": "CommonSettings.ini",
    "Handheld": "MobileSettings.ini",
    "Desktop": "DesktopSettings.ini",
    "Desktop.Cloud": "CloudDesktopOverride.ini",
    "Console": "ConsoleSettings.ini",
    "Cinematic": "CinematicSettings.ini",
}

EXPECTED_CAP_DEFINITIONS = {
    "ConsoleSettings": [256],
    "DesktopSettings": [256],
    "MobileSettings": [32],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(check: str, actual: object, expected: object, source: Path | str) -> None:
    if actual != expected:
        raise AssertionError(
            "Light-cull cap audit failed: "
            f"validator=light_cull_cap; check={check}; source={source}; "
            f"expected={expected!r}; actual={actual!r}"
        )


def verified_hash(name: str, path: Path) -> str:
    require(f"{name}_exists", path.is_file(), True, path)
    actual = sha256(path)
    require(f"{name}_sha256", actual, EXPECTED_HASHES[name], path)
    return actual


def _read_text_assets(
    extracted_root: Path, *, verify_hashes: bool
) -> tuple[dict[str, str], list[dict[str, object]]]:
    texts: dict[str, str] = {}
    records: list[dict[str, object]] = []
    for logical_name, (file_name, expected_hash, path_id_hex) in TEXT_ASSETS.items():
        path = extracted_root / file_name
        require(f"{logical_name}_exists", path.is_file(), True, path)
        actual_hash = sha256(path)
        if verify_hashes:
            require(
                f"{logical_name}_sha256",
                actual_hash,
                expected_hash,
                path,
            )
        texts[logical_name] = path.read_text(encoding="utf-8-sig")
        records.append(
            {
                "name": logical_name,
                "pathIdHex": path_id_hex,
                "fileName": file_name,
                "sizeBytes": path.stat().st_size,
                "sha256": actual_hash,
            }
        )
    return texts, records


def _parse_include_routes(text: str) -> dict[str, str]:
    section = ""
    routes: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"\[IncludeSettings(?:@([^]]+))?\]", line)
        if match:
            section = match.group(1) or "Common"
            continue
        match = re.fullmatch(r"includeSettings\s*=\s*(\S+)", line)
        if match and section:
            routes[section] = match.group(1)
    return routes


def validate_settings_payloads(
    extracted_root: Path, *, verify_hashes: bool = True
) -> tuple[list[dict[str, object]], dict[str, list[int]]]:
    texts, records = _read_text_assets(
        extracted_root, verify_hashes=verify_hashes
    )
    setting_files = [
        line.strip()
        for line in texts["SettingFiles"].splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    require(
        "setting_file_list",
        setting_files,
        EXPECTED_SETTING_FILES,
        extracted_root / TEXT_ASSETS["SettingFiles"][0],
    )
    include_routes = _parse_include_routes(texts["HGRenderPipelineSettings"])
    require(
        "include_routes",
        include_routes,
        EXPECTED_INCLUDE_ROUTES,
        extracted_root / TEXT_ASSETS["HGRenderPipelineSettings"][0],
    )

    cap_pattern = re.compile(
        r"^\s*PunctualLightMaxCount\s*=\s*(-?\d+)\s*$",
        re.MULTILINE,
    )
    cap_definitions = {
        name: [int(value) for value in cap_pattern.findall(text)]
        for name, text in texts.items()
        if cap_pattern.search(text)
    }
    require(
        "cap_definitions",
        cap_definitions,
        EXPECTED_CAP_DEFINITIONS,
        extracted_root,
    )
    return records, cap_definitions


def _require_source_contracts() -> dict[str, str]:
    paths = {
        "device_type_source": DEVICE_TYPE_SOURCE,
        "setting_hub_source": SETTING_HUB_SOURCE,
        "setting_parameters_source": SETTING_PARAMETERS_SOURCE,
        "light_cluster_source": LIGHT_CLUSTER_SOURCE,
    }
    texts = {name: path.read_text(encoding="utf-8-sig") for name, path in paths.items()}
    snippets = {
        "device_type_source": ["Handheld", "Console", "Desktop", "Cinematic"],
        "setting_hub_source": [
            "UnityEngine::SystemInfo::GetDeviceType(0LL)",
            "_currentDeviceType_k__BackingField = overrideDeviceType",
        ],
        "setting_parameters_source": [
            "SettingParameter::Create<int>(",
            "//                                                           256,",
            '(String *)"PunctualLightMaxCount"',
        ],
        "light_cluster_source": [
            "*(_DWORD *)m_Buffer == 2 || !*(_DWORD *)m_Buffer",
            "System::Single::CompareTo((Single *)&this.distance, other.distance",
            "System::Int32::CompareTo((Int32 *)&other.priority, this.priority",
            "if ( v12 < (int)v42 )",
            "this.fields.m_punctualLightCount = v42",
        ],
    }
    for name, required in snippets.items():
        for snippet in required:
            require(
                f"{name}_snippet",
                snippet in texts[name],
                True,
                paths[name],
            )
    return texts


def build_audit(extracted_root: Path) -> dict[str, object]:
    hashes = {
        "game_assembly": verified_hash("game_assembly", GAME_ASSEMBLY),
        "global_metadata": verified_hash("global_metadata", GLOBAL_METADATA),
        "init_bundle_chunk": verified_hash(
            "init_bundle_chunk", INIT_BUNDLE_CHUNK
        ),
        "device_type_source": verified_hash(
            "device_type_source", DEVICE_TYPE_SOURCE
        ),
        "setting_hub_source": verified_hash(
            "setting_hub_source", SETTING_HUB_SOURCE
        ),
        "setting_parameters_source": verified_hash(
            "setting_parameters_source", SETTING_PARAMETERS_SOURCE
        ),
        "light_cluster_source": verified_hash(
            "light_cluster_source", LIGHT_CLUSTER_SOURCE
        ),
        "ifix_state": verified_hash("ifix_state", IFIX_STATE),
    }
    _require_source_contracts()
    asset_records, cap_definitions = validate_settings_payloads(extracted_root)

    ifix = json.loads(IFIX_STATE.read_text(encoding="utf-8"))
    require(
        "ifix_target_count",
        ifix["patch_format"]["target_count"],
        30,
        IFIX_STATE,
    )
    hgrp_targets = [
        f"{row['type']}.{row['method']}"
        for row in ifix["targets"]
        if row["type"].startswith("HG.Rendering.Runtime")
    ]
    require("ifix_hgrp_targets", hgrp_targets, [], IFIX_STATE)

    return {
        "schema": "endfield.recovered-light-cull-cap.v1",
        "status": "installed_windows_desktop_punctual_cap_source_closed",
        "outcome": (
            "The installed Windows desktop route resolves PunctualLightMaxCount "
            "to 256. SetupState accepts only VisibleLight types 0/2, sorts by "
            "priority descending then squared distance ascending, and applies "
            "min(survivorCount, cap). Because HGCullingSystem.CullLights already "
            "receives maxCount=256, the desktop settings cap cannot further "
            "truncate that native result. The target-frame LightCullResult and "
            "unrelated live native lights remain capture-only."
        ),
        "installedInputs": {
            "gameAssembly": {
                "sizeBytes": GAME_ASSEMBLY.stat().st_size,
                "sha256": hashes["game_assembly"],
            },
            "globalMetadata": {
                "sizeBytes": GLOBAL_METADATA.stat().st_size,
                "sha256": hashes["global_metadata"],
            },
            "initBundleChunk": {
                "vfsRelativePath": (
                    "0CE8FA57/19F0903A12BA87C0D43E67E64889B525.chk"
                ),
                "blockType": "InitBundle",
                "sizeBytes": INIT_BUNDLE_CHUNK.stat().st_size,
                "sha256": hashes["init_bundle_chunk"],
                "serializedFileOffset": 157608586,
            },
            "installedIfixState": {
                "path": IFIX_STATE.relative_to(LAB_ROOT).as_posix(),
                "sha256": hashes["ifix_state"],
                "targetCount": 30,
                "hgrpSettingOrLightClusterTargets": [],
            },
        },
        "settingTextAssets": asset_records,
        "settingRoute": {
            "entry": "HGRenderPipelineSettings.ini",
            "settingFiles": EXPECTED_SETTING_FILES,
            "includeRoutes": EXPECTED_INCLUDE_ROUTES,
            "installedPlayer": "Windows desktop",
            "deviceSelection": (
                "HGRenderPipelineSettings.PopulateDeviceInfo uses "
                "UnityEngine.SystemInfo.GetDeviceType when no override is supplied"
            ),
            "desktopCloudInheritance": (
                "CloudDesktopOverride contains no PunctualLightMaxCount and "
                "inherits DesktopSettings"
            ),
        },
        "capDefinitions": cap_definitions,
        "resolvedInstalledDesktopCap": 256,
        "nativeContract": {
            "settingDefault": {
                "method": "HG.Rendering.Runtime.HGSettingParameters..ctor",
                "methodIndex": 288533,
                "virtualAddress": "0x1836590A0",
                "value": 256,
            },
            "setupState": {
                "method": (
                    "HG.Rendering.Runtime.LightClusteringPassConstructor.SetupState"
                ),
                "methodIndex": 285302,
                "virtualAddress": "0x189D09F50",
                "acceptedVisibleLightTypes": [0, 2],
                "sortOrder": [
                    "priority descending",
                    "squared camera distance ascending",
                ],
                "finalCountEquation": "min(punctualSurvivorCount, punctualLightMaxCount)",
            },
            "upstreamCull": {
                "method": "HG.Rendering.Runtime.HGCullingSystem.CullLights",
                "directCaller": "HG.Rendering.Runtime.HGCamera.DoECSCulling",
                "directCallSiteCount": 2,
                "maxCount": 256,
            },
            "desktopNoSecondTruncation": True,
        },
        "sourceFiles": {
            name: {
                "path": path.relative_to(REPO_ROOT).as_posix(),
                "sha256": hashes[name],
            }
            for name, path in {
                "device_type_source": DEVICE_TYPE_SOURCE,
                "setting_hub_source": SETTING_HUB_SOURCE,
                "setting_parameters_source": SETTING_PARAMETERS_SOURCE,
                "light_cluster_source": LIGHT_CLUSTER_SOURCE,
            }.items()
        },
        "evidenceBoundary": {
            "sourceClosed": [
                "installed Windows desktop cap value 256",
                "type 0/2 punctual filter",
                "priority/distance shortlist order",
                "min survivor/cap final-count rule",
                "desktop cap cannot truncate the upstream max-256 cull result",
            ],
            "captureOnly": [
                "target-frame LightCullResult pointer and count",
                "unrelated active native lights",
                "arbitrary/asymmetric final selected-view planes",
                "future or separately delivered IFix/settings payloads",
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--extracted-root",
        type=Path,
        default=DEFAULT_EXTRACTED_ROOT,
        help="AnimeStudio TextAsset output containing the targeted settings files",
    )
    args = parser.parse_args()

    rendered = json.dumps(build_audit(args.extracted_root), indent=2) + "\n"
    if args.check:
        require("generated_output_exists", OUTPUT.is_file(), True, OUTPUT)
        require(
            "generated_output",
            OUTPUT.read_text(encoding="utf-8"),
            rendered,
            OUTPUT,
        )
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered, encoding="utf-8")
    print(
        "Light-cull cap audit passed: desktop cap=256; "
        "sort=priority-desc/distance-asc; second truncation=none."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Verify the pinned SphereOutside HGRP/Lit deferred-recovery evidence.

This intentionally verifies a fail-closed result. Recovered bytecode and native
entry points are evidence, but do not make the current Unity SRP resource and
render-graph contract equivalent to the original HGRP deferred path.
"""

from __future__ import annotations

import hashlib
import json
import re
import base64
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
ASSET_ROOT = LAB_ROOT / "Assets" / "EndfieldGraphShaderLab"
SOURCE_ROOT = (
    ASSET_ROOT / "Generated" / "OriginalData" / "CharInfoPresentation"
)
RECOVERY_PATH = SOURCE_ROOT / "deferred_lighting_recovery.json"
BINDING_CONTRACT_PATH = SOURCE_ROOT / "deferred_resolver_binding_contract.json"
VISIBILITY_RUNTIME_ROOT = (
    ASSET_ROOT / "Resources" / "EndfieldRecoveredVisibilitySH"
)
VISIBILITY_RUNTIME_PATH = (
    VISIBILITY_RUNTIME_ROOT / "visibility_sh_runtime.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text_lf(path: Path) -> str:
    """Hash source text canonically across Git LF/CRLF checkout policy."""
    return hashlib.sha256(
        path.read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()


def repo_path(relative: str) -> Path:
    return REPO_ROOT.joinpath(*relative.split("/"))


def require_hash(path: Path, expected: str) -> None:
    if not path.is_file():
        raise AssertionError(f"missing pinned evidence: {path}")
    actual = sha256(path)
    if actual != expected:
        raise AssertionError(
            f"{path}: SHA-256 {actual} does not match pinned {expected}"
        )


def require_text_hash(path: Path, expected: str) -> None:
    if not path.is_file():
        raise AssertionError(f"missing pinned source text: {path}")
    actual = sha256_text_lf(path)
    if actual != expected:
        raise AssertionError(
            f"{path}: canonical-LF SHA-256 {actual} does not match "
            f"pinned {expected}"
        )


def require_unity_log(
    path: Path,
    expected: str,
    tokens: list[str],
) -> None:
    """Accept only semantically identical reruns of nondeterministic Unity logs."""
    if not path.is_file():
        raise AssertionError(f"missing Unity validation log: {path}")
    actual = sha256(path)
    if actual == expected:
        return
    require_tokens(path, tokens)
    print(
        "Unity validation log hash changed after a successful rerun; "
        f"semantic gate passed for {path} "
        f"(pinned={expected}, actual={actual})."
    )


def require_tokens(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    for token in tokens:
        if token not in text:
            raise AssertionError(f"{path}: missing token {token!r}")


def require_charinfo_v2_path_value(
    source: Path,
    check: str,
    actual: object,
    expected: object,
) -> None:
    if actual != expected:
        raise AssertionError(
            "CharInfo V2 irradiance data-path validator failed: "
            f"check={check}; source={source}; "
            f"expected={expected!r}; actual={actual!r}"
        )


def verify_charinfo_v2_data_path_contract(
    ownership: dict[str, object],
    report: dict[str, object],
    source: Path = BINDING_CONTRACT_PATH,
) -> None:
    selection = report["livePath"]["installedMapPathSelection"]
    shipped = report["shippedIvData"]
    contract_selection = ownership["installed_map_path_selection"]
    contract_shipped = ownership["shipped_iv_data"]
    checks = (
        (
            "installed_map_path_selection.constructor_fields",
            contract_selection["constructor_fields"],
            {
                "m_irradianceDataPathV2": "System.String.Empty",
                "m_exportpathV2": "System.String.Empty",
                "m_gachaDataPathV2": "System.String.Empty",
            },
        ),
        (
            "audit.installed_map_path_selection.constructor_fields",
            selection["constructorFields"],
            contract_selection["constructor_fields"],
        ),
        (
            "installed_map_path_selection.streaming_suffix",
            contract_selection["streaming_suffix"],
            "/aiTest/index.bytes",
        ),
        (
            "audit.installed_map_path_selection.streaming_suffix",
            selection["streamingSuffixLiteral"]["value"],
            contract_selection["streaming_suffix"],
        ),
        (
            "audit.installed_map_path_selection.streaming_literal",
            (
                selection["streamingSuffixLiteral"]["encodedUsage"],
                selection["streamingSuffixLiteral"]["literalIndex"],
                selection["streamingSuffixLiteral"]["utf8ByteCount"],
            ),
            ("0xa0000fdd", 2030, 19),
        ),
        (
            "installed_map_path_selection.matching_shipped_iv_files",
            contract_selection["matching_shipped_iv_files"],
            0,
        ),
        (
            "audit.path_resolution.matching_shipped_files",
            shipped["pathResolution"]["matchingShippedFiles"],
            [],
        ),
        (
            "installed_map_path_selection.direct_managed_call_sites",
            contract_selection["direct_managed_call_sites"],
            {"ReloadIndexFileV2": [], "StreamingInNewMapV2": []},
        ),
        (
            "audit.installed_map_path_selection.direct_managed_call_sites",
            selection["directManagedCallSites"],
            {"0x189d025a0": [], "0x184843fb0": []},
        ),
        (
            "installed_map_path_selection.absolute_method_pointer_sites",
            contract_selection["absolute_method_pointer_sites"],
            {
                "ReloadIndexFileV2": ["0x18eabd458"],
                "StreamingInNewMapV2": ["0x18eabd498"],
            },
        ),
        (
            "audit.installed_map_path_selection.absolute_method_pointer_sites",
            selection["absoluteMethodPointerSites"],
            {
                "0x189d025a0": ["0x18eabd458"],
                "0x184843fb0": ["0x18eabd498"],
            },
        ),
        (
            "installed_map_path_selection.shipped_lua_mentions",
            contract_selection["shipped_lua_mentions"],
            {
                "ReloadIndexFileV2": [],
                "StreamingInNewMapV2": [],
                "HGIrradianceVolumeManagerV2": [],
            },
        ),
        (
            "audit.installed_map_path_selection.shipped_lua_mentions",
            selection["shippedLuaMentions"],
            contract_selection["shipped_lua_mentions"],
        ),
        (
            "installed_map_path_selection.installed_ifix_target_count",
            contract_selection["installed_ifix_target_count"],
            32,
        ),
        (
            "audit.installed_map_path_selection.installed_ifix",
            (
                selection["installedIfix"]["persistentTargetCount"],
                selection["installedIfix"]["matchingTargets"],
                selection["installedIfix"]["currentRoute"],
            ),
            (32, [], "all three recovered non-IFix branches"),
        ),
        (
            "installed_map_path_selection.native_missing_map",
            contract_selection["native_missing_map"],
            {
                "set_map_native_va": "0x18111b690",
                "loader_state_offset": 0x398,
                "loader_handle_offset": 0x3A0,
                "path_offset": 0x3B0,
                "active_resource_flag_offset": 0x4A0,
                "transitions": [
                    "SetMap -> state 4 (clear requested)",
                    "state 4 -> release six clipmaps, active=false, state 0",
                    "state 0 + empty/unresolved path -> state 2",
                    "state 2 -> stable inactive result",
                ],
                "creates_full_size_clipmaps": False,
                "inactive_parameters": {
                    "param0": [0.0, 0.0, 0.0, 0.0],
                    "param1": [0.0, 0.0, 0.0, 0.0],
                    "param2": [0.0, 0.0, 0.0, 0.0],
                    "param3": [0.0, 0.3333333432674408, 0.0, 0.0],
                },
                "textures": (
                    "the same 1x1x1 UnityDefault3D zero texture in all six "
                    "result slots"
                ),
            },
        ),
        (
            "audit.active_clipmap.installed_missing_map",
            report["activeClipmaps"]["installedMissingMapState"],
            {
                "setMapNativeVa": "0x18111b690",
                "loaderStateOffset": 0x398,
                "loaderHandleOffset": 0x3A0,
                "pathOffset": 0x3B0,
                "activeResourceFlagOffset": 0x4A0,
                "transitions": [
                    "SetMap -> state 4 (clear requested)",
                    "state 4 -> release six clipmaps, active=false, state 0",
                    "state 0 + empty/unresolved path -> state 2",
                    "state 2 -> stable inactive result",
                ],
                "createsFullSizeClipmaps": False,
                "parameters": {
                    "param0": [0.0, 0.0, 0.0, 0.0],
                    "param1": [0.0, 0.0, 0.0, 0.0],
                    "param2": [0.0, 0.0, 0.0, 0.0],
                    "param3": [0.0, 0.3333333432674408, 0.0, 0.0],
                },
                "textures": (
                    "the same 1x1x1 UnityDefault3D zero texture in all six "
                    "result slots"
                ),
            },
        ),
        (
            "shipped_iv_data.vfs_index_sha256",
            contract_shipped["vfs_index_sha256"],
            shipped["vfs"]["sha256"],
        ),
        (
            "shipped_iv_data.inventory",
            contract_shipped["inventory"],
            {
                "iv_files": 224,
                "v3_index_files": 85,
                "legacy_index_files": 2,
                "gacha_files": 12,
                "ai_test_index_files": 0,
            },
        ),
        (
            "audit.shipped_iv_data.inventory",
            shipped["vfs"]["counts"],
            {
                "v3Index": 85,
                "legacyIndex": 2,
                "gachaFiles": 12,
                "aiTestIndex": 0,
            },
        ),
        (
            "shipped_iv_data.marker2",
            contract_shipped["index_record_formats"]["marker_0x03000002"],
            {
                "record_stride": 32,
                "length_fields": "one stored/decoded length",
                "tail_record_count": 0,
                "sample_sha256": (
                    "d0ba47a7d92820598ade4039807f9cb5"
                    "fe28b190825205835ccf17b69ba79eb3"
                ),
                "sample_record_count": 24,
            },
        ),
        (
            "audit.shipped_iv_data.marker2",
            {
                key: shipped["indexFormatSamples"]["gachaCharacterMarker2"][key]
                for key in (
                    "marker",
                    "recordStride",
                    "recordCount",
                    "tailRecordCount",
                    "storedPayloadBytes",
                )
            },
            {
                "marker": "0x03000002",
                "recordStride": 32,
                "recordCount": 24,
                "tailRecordCount": 0,
                "storedPayloadBytes": 1399240,
            },
        ),
        (
            "shipped_iv_data.marker3",
            contract_shipped["index_record_formats"]["marker_0x03000003"],
            {
                "record_stride": 36,
                "length_fields": "separate stored and decoded lengths",
                "tail_record_stride": 20,
                "sample_sha256": (
                    "1726f8d11aa7c2706d95e0e4163cb776"
                    "f9bfa2eb54787bb672dd9a7d868a360c"
                ),
                "sample_record_count": 18,
                "sample_tail_record_count": 12,
            },
        ),
        (
            "audit.shipped_iv_data.marker3",
            {
                key: shipped["indexFormatSamples"]["indieDg008Marker3"][key]
                for key in (
                    "marker",
                    "recordStride",
                    "recordCount",
                    "tailRecordStride",
                    "tailRecordCount",
                )
            },
            {
                "marker": "0x03000003",
                "recordStride": 36,
                "recordCount": 18,
                "tailRecordStride": 20,
                "tailRecordCount": 12,
            },
        ),
        (
            "shipped_iv_data.gacha_character_sample",
            contract_shipped["gacha_character_sample"],
            {
                "index_path": (
                    "Data/IrradianceVolume/PC/gacha/character/v3/index.bytes"
                ),
                "payload_path": (
                    "Data/IrradianceVolume/PC/gacha/character/v3/iv_0_0.bytes"
                ),
                "payload_sha256": (
                    "ccba259839d3b91cf9d32c2edce1d672"
                    "eb82f489c7aae33014982aa310b351b4"
                ),
                "payload_bytes": 1399240,
                "covered_exactly_by_index_stored_ranges": True,
                "charinfo_v2_owner": False,
            },
        ),
        (
            "audit.shipped_iv_data.gacha_character_payload",
            {
                key: shipped["gachaCharacterPayload"][key]
                for key in (
                    "sha256",
                    "byteCount",
                    "coveredExactlyByIndexStoredRanges",
                )
            },
            {
                "sha256": (
                    "ccba259839d3b91cf9d32c2edce1d672"
                    "eb82f489c7aae33014982aa310b351b4"
                ),
                "byteCount": 1399240,
                "coveredExactlyByIndexStoredRanges": True,
            },
        ),
    )
    for check, actual, expected in checks:
        require_charinfo_v2_path_value(source, check, actual, expected)


def require_light_binning_value(
    source: Path,
    check: str,
    actual: object,
    expected: object,
) -> None:
    if actual != expected:
        raise AssertionError(
            "CharInfo light-binning validator failed: "
            f"check={check}; source={source}; "
            f"expected={expected!r}; actual={actual!r}"
        )


def verify_light_binning_contract(
    runtime: dict[str, object],
    audit: dict[str, object],
    source: Path = BINDING_CONTRACT_PATH,
) -> None:
    expected_assets = {
        "LightBinningXYCS": {
            "pathId": 4548070058470272991,
            "sourceCab": "CAB-2894b8a1c7ce2e6f58bc1c00db01d58d",
            "serializedSha256": (
                "0817ef60ae7b9e1d5c2b2358e2e8f63a"
                "d3073cc15b3184d74eb7f05e20de2561"
            ),
            "sourceOffset": 7776767,
        },
        "LightBinningZCS": {
            "pathId": -7926954666264468449,
            "sourceCab": "CAB-39f802e0747697a03fa65bb3c7439cab",
            "serializedSha256": (
                "89ca3fbcaf8283edfa6b3bf16b1206733"
                "2b49dc212adde955a97291de9cec2a4"
            ),
            "sourceOffset": 4917612,
        },
    }
    audited_assets = {
        row["name"]: {
            key: row[key]
            for key in (
                "pathId",
                "sourceCab",
                "serializedSha256",
                "sourceOffset",
            )
        }
        for row in audit["assets"]
    }
    expected_programs = [
        (
            "LightBinningXYCS",
            "CSMain",
            "d3d11",
            [8, 8, 1],
            "608523c1a5c42430629885eced9c2cd39dea9b446916f4e02461527b00edce3b",
        ),
        (
            "LightBinningXYCS",
            "CSMainWithTileDrawResult",
            "d3d11",
            [8, 8, 1],
            "608523c1a5c42430629885eced9c2cd39dea9b446916f4e02461527b00edce3b",
        ),
        (
            "LightBinningXYCS",
            "CSClear",
            "d3d11",
            [64, 1, 1],
            "ad570420e19ec470afecd867b0b58bfb626b5c4068d289776a5cb15438ce0574",
        ),
        (
            "LightBinningXYCS",
            "CSMain",
            "vulkan",
            [8, 8, 1],
            "7bc92dd208a2e84a1b1a0041acc9667b145f6f13db9f08790e61957a9fe3f346",
        ),
        (
            "LightBinningXYCS",
            "CSMainWithTileDrawResult",
            "vulkan",
            [8, 8, 1],
            "7bc92dd208a2e84a1b1a0041acc9667b145f6f13db9f08790e61957a9fe3f346",
        ),
        (
            "LightBinningXYCS",
            "CSClear",
            "vulkan",
            [64, 1, 1],
            "99c6691fb03b6a1c6381764b9443b4d3a7b93e8046e92629941fb8b77770b17b",
        ),
        (
            "LightBinningZCS",
            "CSMain",
            "d3d11",
            [64, 1, 1],
            "51c6e5de76f7eb1d5913cf2aa65d75096b2802cfeeb0ebf0e972d165f36ae085",
        ),
        (
            "LightBinningZCS",
            "CSMain",
            "vulkan",
            [64, 1, 1],
            "98567e52ff0479884a822b47e1180499ccac7f86c49c25a40bb72bf9bdbff761",
        ),
    ]
    audited_programs = [
        (
            row["asset"],
            row["kernel"],
            row["rendererName"],
            row["threadGroupSize"],
            row["sha256"],
        )
        for row in audit["programs"]
    ]
    checks = (
        ("contract.published", runtime["published"], False),
        (
            "contract.pass0_consumer_enabled",
            runtime["pass0_consumer_enabled"],
            False,
        ),
        ("audit.schema", audit["schema"], "endfield.charinfo.light-binning.v1"),
        ("audit.valid", audit["valid"], True),
        ("contract.assets", runtime["assets"], expected_assets),
        ("audit.assets", audited_assets, expected_assets),
        ("contract.program_count", runtime["program_count"], 8),
        ("audit.programs", audited_programs, expected_programs),
        (
            "contract.static_constants",
            runtime["static_constants"],
            audit["staticConstants"],
        ),
        (
            "contract.binning_data_layout",
            runtime["binning_data_layout"],
            audit["binningDataLayout"],
        ),
        (
            "contract.light_segment.core",
            runtime["light_segment"],
            {
                key: audit["lightSegment"][key]
                for key in (
                    "tileSize",
                    "sliceZ",
                    "uintCountPerBin",
                    "maxLightMasks",
                    "xyDispatch",
                    "zDispatch",
                )
            },
        ),
        (
            "contract.combined_buffer",
            runtime["combined_buffer"],
            audit["combinedBuffer"],
        ),
        (
            "audit.recovery_boundary.canonical_combined_publication",
            audit["recoveryBoundary"]["canonicalCombinedPublication"],
            False,
        ),
        (
            "audit.recovery_boundary.canonical_combined_capability",
            audit["recoveryBoundary"]["canonicalCombinedCapability"],
            (
                "implemented as a default-off raw ByteAddressBuffer bridge "
                "with exact light words, zero-local-reflection tail, four "
                "installed offsets, and same-frame recovered reflection "
                "oct/global co-publication"
            ),
        ),
        (
            "contract.runtime_port.canonical_combined_publication",
            runtime["runtime_port"]["canonicalCombinedPublication"],
            False,
        ),
    )
    for check, actual, expected in checks:
        require_light_binning_value(source, check, actual, expected)


def verify_canonical_binning_gpu_report(
    transport: dict[str, object],
    report: dict[str, object],
    api: str,
    audit_sha256: str,
    source: Path = BINDING_CONTRACT_PATH,
) -> None:
    fixture = transport["fixture"]
    expected_gates = [
        {
            "gate": "zero_width",
            "input": "width=0, height=2160",
            "requiredDiagnosticToken": "render dimensions must be positive",
            "diagnostic": "render dimensions must be positive",
            "rejected": True,
            "diagnosticMatched": True,
        },
        {
            "gate": "tile_x_overflow",
            "input": "width=8193, height=2160",
            "requiredDiagnosticToken": "exceed the installed 256x128 limit",
            "diagnostic": (
                "tile dimensions 257x68 exceed the installed 256x128 limit"
            ),
            "rejected": True,
            "diagnosticMatched": True,
        },
        {
            "gate": "tile_y_overflow",
            "input": "width=3840, height=4097",
            "requiredDiagnosticToken": "exceed the installed 256x128 limit",
            "diagnostic": (
                "tile dimensions 120x129 exceed the installed 256x128 limit"
            ),
            "rejected": True,
            "diagnosticMatched": True,
        },
    ]
    checks = (
        (
            f"gpu_report.{api}.schema",
            report["schema"],
            "endfield-recovered-canonical-binning-validation-v1",
        ),
        (f"gpu_report.{api}.valid", report["valid"], True),
        (f"gpu_report.{api}.graphics_api", report["graphicsApi"], api),
        (
            f"gpu_report.{api}.canonical_publication_default_off",
            report["canonicalPublicationDefaultOff"],
            True,
        ),
        (
            f"gpu_report.{api}.no_local_reflection_source_closed",
            report["noLocalReflectionSourceClosed"],
            True,
        ),
        (
            f"gpu_report.{api}.source_audit",
            (
                report["sourceAuditSha256"],
                report["expectedSourceAuditSha256"],
                report["sourceAuditHashMatches"],
            ),
            (audit_sha256, audit_sha256, True),
        ),
        (
            f"gpu_report.{api}.fixture",
            {
                "width": report["fixtureWidth"],
                "height": report["fixtureHeight"],
                "tileX": report["tileX"],
                "tileY": report["tileY"],
                "offsets": [
                    report["lightXYOffset"],
                    report["lightZOffset"],
                    report["reflectionXYOffset"],
                    report["reflectionZOffset"],
                ],
                "lightWords": report["lightWordCount"],
                "reflectionZeroWords": report["reflectionWordCount"],
                "totalWords": report["totalWordCount"],
                "totalBytes": report["totalBytes"],
            },
            fixture,
        ),
        (
            f"gpu_report.{api}.readback",
            (
                report["rawGlobalReadbackMatches"],
                report["lightSegmentMatches"],
                report["reflectionSegmentIsZero"],
            ),
            (True, True, True),
        ),
        (
            f"gpu_report.{api}.fail_closed_gates",
            report["failClosedGates"],
            expected_gates,
        ),
        (f"gpu_report.{api}.failures", report["failures"], []),
    )
    for check, actual, expected in checks:
        require_light_binning_value(source, check, actual, expected)


def verify_canonical_reflection_frame_gpu_report(
    resources: dict[str, object],
    report: dict[str, object],
    api: str,
    source: Path = BINDING_CONTRACT_PATH,
) -> None:
    expected_global_words = [
        "0x42F00000",
        "0x42880000",
        "0x45FF0000",
        "0x3D000000",
        "0x44800000",
        "0x3F800000",
        "0x3F800000",
        "0x3F638E39",
        "0x00000000",
        "0x3DEC7B90",
        "0x3D5E9269",
        "0x3D638E39",
        "0xBBF76C62",
        "0x3C476815",
        "0x3EF1C918",
        "0x3F8C53BF",
    ]
    checks = (
        (
            f"gpu_report.{api}.schema",
            report["schema"],
            "endfield-recovered-canonical-reflection-frame-v1",
        ),
        (f"gpu_report.{api}.valid", report["valid"], True),
        (f"gpu_report.{api}.graphics_api", report["graphicsApi"], api),
        (f"gpu_report.{api}.default_off", report["defaultOff"], True),
        (
            f"gpu_report.{api}.source",
            (
                report["sourceCubemapAssetPath"],
                report["sourcePayloadSha256"],
            ),
            (
                resources["source_cubemap_asset_path"],
                resources["source_payload_sha256"],
            ),
        ),
        (
            f"gpu_report.{api}.source_gates",
            (
                report["missingSourceRejected"],
                report["missingSourceDiagnostic"],
                report["wrongSourceRejected"],
                report["wrongSourceDiagnostic"],
            ),
            (
                True,
                "the exact T_hdri_env_char_01 Cubemap is not bound",
                True,
                "the source Cubemap is not the exact T_hdri_env_char_01 asset",
            ),
        ),
        (
            f"gpu_report.{api}.publication_ready",
            (
                report["recoveredPublicationReturnedReady"],
                report["canonicalReadyObserved"],
                report["reflectionReadyObserved"],
            ),
            (True, True, True),
        ),
        (
            f"gpu_report.{api}.canonical_buffer_preserved",
            report["canonicalBufferPreserved"],
            True,
        ),
        (
            f"gpu_report.{api}.canonical_sentinels",
            report["canonicalSentinelWords"],
            [
                "0xA5C31F29",
                "0x27AF0A66",
                "0x00000000",
                "0x00000000",
            ],
        ),
        (
            f"gpu_report.{api}.reflection_global_data",
            (
                report["reflectionGlobalDataMatches"],
                report["expectedGlobalWords"],
                report["actualGlobalWords"],
            ),
            (True, expected_global_words, expected_global_words),
        ),
        (
            f"gpu_report.{api}.oct_texture",
            (
                report["octDimensionsMatch"],
                report["octWidth"],
                report["octHeight"],
                report["octSlices"],
                report["octMipCount"],
                report["octCenterFiniteNonzero"],
                report["octCenterBits"],
            ),
            (
                True,
                576,
                576,
                32,
                10,
                True,
                [
                    "0x3F67A000",
                    "0x3F67A000",
                    "0x3F67A000",
                    "0x00000000",
                ],
            ),
        ),
        (f"gpu_report.{api}.failures", report["failures"], []),
    )
    for check, actual, expected in checks:
        require_light_binning_value(source, check, actual, expected)


def require_visibility_sh_constants_value(
    source: Path,
    check: str,
    actual: object,
    expected: object,
) -> None:
    if actual != expected:
        raise AssertionError(
            "VisibilitySHConstData validator failed: "
            f"check={check}; source={source}; "
            f"expected={expected!r}; actual={actual!r}"
        )


def verify_visibility_sh_constants_audit(
    transport: dict[str, object],
    audit: dict[str, object],
    source: Path = BINDING_CONTRACT_PATH,
) -> None:
    checks = (
        (
            "audit.schema",
            audit["schema"],
            "endfield.charinfo.visibility-sh-constants.v1",
        ),
        ("audit.valid", audit["valid"], True),
        (
            "contract.layout",
            (
                transport["buffer_name"],
                transport["size_bytes"],
                transport["selected_used_byte_ranges"],
            ),
            ("VisibilitySHConstData", 128, [[32, 47], [48, 63]]),
        ),
        (
            "audit.layout",
            audit["layout"],
            {
                "bufferName": "VisibilitySHConstData",
                "sizeBytes": 128,
                "vectorCount": 8,
                "fields": {
                    "logSHParams": 0,
                    "gStarParams": 16,
                    "abParams": 32,
                    "fHatParams": 48,
                    "sphereParams": 64,
                    "tileParam0": 80,
                    "tileParam1": 96,
                    "tileParam2": 112,
                },
            },
        ),
        (
            "audit.native_producer",
            (
                audit["nativeProducer"]["methodIndex"],
                audit["nativeProducer"]["token"],
                audit["nativeProducer"]["va"],
                audit["nativeProducer"]["size"],
                audit["nativeProducer"]["sha256"],
            ),
            (
                285491,
                "0x060009af",
                "0x189d15978",
                4189,
                "8ccfdc128db265d7a80feba1120b60ca"
                "f0bfd0d25d8dfc32ee8657f22f768894",
            ),
        ),
        (
            "audit.full_struct_zero_fill",
            audit["nativeProducer"]["instructionWindows"]
            ["full_struct_zero_fill"]["hex"],
            "41bf80000000458bc733d2488d8c2410020000e8e35662f6",
        ),
        (
            "audit.zero_tail_rows_copy",
            audit["nativeProducer"]["instructionWindows"]
            ["zero_tail_rows_copy"]["hex"],
            (
                "0f288424600200000f298424a0030000"
                "0f288c24700200000f298c24b0030000"
                "0f288424800200000f298424c0030000"
            ),
        ),
        (
            "audit.zero_fill_helper",
            (
                audit["nativeProducer"]["zeroFillHelper"]["va"],
                audit["nativeProducer"]["zeroFillHelper"]["size"],
                audit["nativeProducer"]["zeroFillHelper"]["sha256"],
                audit["nativeProducer"]["zeroFillHelper"]["entryHex"],
            ),
            (
                "0x18033b9d0",
                904,
                "13b97250d2c9f9ef32c2a569239dab8f"
                "b26f3119b30493d0dd1149b4093e3bc7",
                (
                    "488bc14c8bc94c8d152346ccff0fb6d249bb0101010101010101"
                    "4c0fafda66490f6e"
                ),
            ),
        ),
        (
            "audit.ab_params_bits",
            audit["fixedRows"]["abParams"]["wordBits"],
            ["0x3f800000", "0x3ea16095", "0x3f800000", "0x3f800000"],
        ),
        (
            "audit.f_hat_x",
            audit["scalars"]["fHatX"]["bits"],
            "0x3e5b57c6",
        ),
        (
            "audit.retail_defaults",
            audit["retailDefaults"],
            {
                "enabled": True,
                "halfResolution": True,
                "sphereIntervalScaleBits": "0x3f4ccccd",
                "sphereRangeScaleBits": "0x40a00000",
                "dimensionFormula": (
                    "signed truncating width/2 and height/2 for positive "
                    "camera dimensions"
                ),
                "sphereParamsFormula": (
                    "(clamp(interval,0.8,2), clamp(range,0.01,5), "
                    "1/outputWidth, 1/outputHeight)"
                ),
            },
        ),
        (
            "audit.selected_consumer",
            (
                audit["selectedDeferredConsumer"]["usedMembers"],
                audit["selectedDeferredConsumer"]["usedByteRanges"],
            ),
            (
                [
                    "VisibilitySHConstData_ABParams",
                    "VisibilitySHConstData_FHatParams",
                ],
                [[32, 47], [48, 63]],
            ),
        ),
        (
            "audit.full_producer_initialization",
            audit["fullProducerInitialization"],
            {
                "sizeBytes": 128,
                "zeroFillValue": 0,
                "sourceStackRange": "rsp+0x210..rsp+0x28f",
                "uploadStackRange": "rsp+0x350..rsp+0x3cf",
                "overwrittenRows": [0, 1, 2, 3, 4],
                "zeroRows": [5, 6, 7],
                "zeroTailByteRange": [80, 127],
                "sourceClosed": True,
            },
        ),
    )
    for check, actual, expected in checks:
        require_visibility_sh_constants_value(source, check, actual, expected)


def verify_visibility_sh_constants_gpu_report(
    transport: dict[str, object],
    report: dict[str, object],
    api: str,
    source: Path = BINDING_CONTRACT_PATH,
) -> None:
    expected_words = [
        "0x409D41DD", "0x40956445", "0xC09D41DD", "0xC0956445",
        "0x418B5D98", "0x4118E06B", "0xC18B5D98", "0xC118E06B",
        "0x3F800000", "0x3EA16095", "0x3F800000", "0x3F800000",
        "0x3E5B57C6", "0x00000000", "0x44F00000", "0x44870000",
        "0x3F4CCCCD", "0x40A00000", "0x3A088889", "0x3A72B9D6",
    ] + ["0x00000000"] * 12
    expected_gates = [
        {
            "gate": "zero_width",
            "input": "width=0, height=2160",
            "requiredDiagnosticToken": "camera dimensions must be positive",
            "diagnostic": "camera dimensions must be positive",
            "rejected": True,
            "diagnosticMatched": True,
        },
        {
            "gate": "half_width_zero",
            "input": "width=1, height=2160",
            "requiredDiagnosticToken": (
                "half-resolution dimensions must remain positive"
            ),
            "diagnostic": (
                "retail half-resolution dimensions must remain positive"
            ),
            "rejected": True,
            "diagnosticMatched": True,
        },
        {
            "gate": "float_integer_overflow",
            "input": "width=16777216, height=2160",
            "requiredDiagnosticToken": "exceed exact float-integer transport",
            "diagnostic": (
                "camera dimensions exceed exact float-integer transport"
            ),
            "rejected": True,
            "diagnosticMatched": True,
        },
    ]
    checks = (
        (
            f"gpu_report.{api}.schema",
            report["schema"],
            "endfield-recovered-visibility-sh-constants-validation-v2",
        ),
        (f"gpu_report.{api}.valid", report["valid"], True),
        (f"gpu_report.{api}.graphics_api", report["graphicsApi"], api),
        (f"gpu_report.{api}.default_off", report["defaultOff"], True),
        (
            f"gpu_report.{api}.retail_visibility_texture_closed",
            report["retailVisibilityTextureClosed"],
            False,
        ),
        (
            f"gpu_report.{api}.full_constant_buffer_source_closed",
            report["fullConstantBufferSourceClosed"],
            True,
        ),
        (
            f"gpu_report.{api}.source_audit",
            (
                report["sourceAuditSha256"],
                report["expectedSourceAuditSha256"],
                report["sourceAuditHashMatches"],
            ),
            (transport["audit_sha256"], transport["audit_sha256"], True),
        ),
        (
            f"gpu_report.{api}.fixture",
            (
                report["cameraWidth"],
                report["cameraHeight"],
                report["outputWidth"],
                report["outputHeight"],
                report["bufferBytes"],
                report["selectedFirstWord"],
                report["selectedWordCount"],
            ),
            (3840, 2160, 1920, 1080, 128, 8, 8),
        ),
        (
            f"gpu_report.{api}.publication",
            (
                report["publicationReturnedReady"],
                report["readyObserved"],
                report["allPublishedWordsMatch"],
                report["selectedDeferredWordsMatch"],
                report["nativeZeroTailMatch"],
            ),
            (True, True, True, True, True),
        ),
        (
            f"gpu_report.{api}.words",
            (report["expectedWords"], report["actualWords"]),
            (expected_words, expected_words),
        ),
        (
            f"gpu_report.{api}.fail_closed_gates",
            report["failClosedGates"],
            expected_gates,
        ),
        (f"gpu_report.{api}.failures", report["failures"], []),
    )
    for check, actual, expected in checks:
        require_visibility_sh_constants_value(source, check, actual, expected)


def verify_visibility_sh_frame_report(
    transport: dict[str, object],
    report: dict[str, object],
    api: str,
    expected_publication: str,
    source: Path = BINDING_CONTRACT_PATH,
) -> None:
    fixture = transport["fixture"]
    checks = (
        (
            f"frame_report.{api}.{expected_publication}.schema",
            report["schema"],
            "endfield-recovered-visibility-sh-frame-validation-v1",
        ),
        (f"frame_report.{api}.{expected_publication}.valid", report["valid"], True),
        (
            f"frame_report.{api}.{expected_publication}.identity",
            (
                report["graphicsApi"],
                report["defaultOff"],
                report["canonicalProperty"],
                report["canonicalReadyProperty"],
                report["expectedCanonicalPublication"],
                report["pass0ConsumerEnabled"],
            ),
            (
                api,
                True,
                "_VisibilitySHRT",
                "_EndfieldRecoveredVisibilitySHReady",
                expected_publication,
                False,
            ),
        ),
        (
            f"frame_report.{api}.{expected_publication}.capsules",
            report["capsuleFixture"],
            {
                "actor": fixture["actor"],
                "count": fixture["authored_capsules"],
                "stride": 48,
                "order": fixture["survivor_order"],
                "sha256": fixture["capsule_bytes_sha256"],
            },
        ),
        (
            f"frame_report.{api}.{expected_publication}.active",
            (
                report["activeFrame"]["actor"],
                report["activeFrame"]["survivors"],
                report["activeFrame"]["authored"],
                report["activeFrame"]["order"],
                report["activeFrame"]["width"],
                report["activeFrame"]["height"],
                report["activeFrame"]["canonicalPublication"],
            ),
            (
                fixture["actor"],
                fixture["authored_capsules"],
                fixture["authored_capsules"],
                fixture["survivor_order"],
                fixture["readback_width"],
                fixture["readback_height"],
                expected_publication,
            ),
        ),
        (
            f"frame_report.{api}.{expected_publication}.gpu",
            report["gpuReadback"],
            {
                "actor": fixture["actor"],
                "width": fixture["readback_width"],
                "height": fixture["readback_height"],
                "byteCount": fixture["readback_byte_count"],
                "nonzeroPixels": fixture["nonzero_pixels"],
                "sha256": fixture["rgba_half_sha256"],
            },
        ),
        (
            f"frame_report.{api}.{expected_publication}.sources",
            (
                report["sources"]["producer"]["sha256"],
                report["sources"]["pipeline"]["sha256"],
                report["sources"]["nativeAudit"]["sha256"],
            ),
            (
                transport["producer_sha256"],
                transport["pipeline_sha256"],
                transport["native_audit_sha256"],
            ),
        ),
        (
            f"frame_report.{api}.{expected_publication}.beauty",
            (
                report["beautyFrame"]["sha256"],
                report["beautyFrame"]["expectedSha256"],
                report["beautyFrame"]["unchanged"],
            ),
            (
                report["beautyFrame"]["expectedSha256"],
                report["beautyFrame"]["expectedSha256"],
                True,
            ),
        ),
        (f"frame_report.{api}.{expected_publication}.failures", report["failures"], []),
    )
    for check, actual, expected in checks:
        require_visibility_sh_constants_value(source, check, actual, expected)


def require_deferred_gbuffer_frame_value(
    source: Path,
    check: str,
    actual: object,
    expected: object,
) -> None:
    if actual != expected:
        raise AssertionError(
            "Deferred HGBuffer frame validator failed: "
            f"check={check}; source={source}; "
            f"expected={expected!r}; actual={actual!r}"
        )


def verify_deferred_gbuffer_frame_report(
    transport: dict[str, object],
    report: dict[str, object],
    api: str,
    expect_fail_closed: bool = False,
    source: Path = BINDING_CONTRACT_PATH,
) -> None:
    expected_readbacks = transport["readbacks"]
    checks = (
        (
            f"frame_report.{api}.schema",
            report["schema"],
            "endfield-recovered-deferred-gbuffer-frame-validation-v1",
        ),
        (f"frame_report.{api}.valid", report["valid"], True),
        (
            f"frame_report.{api}.identity",
            (
                report["graphicsApi"],
                report["defaultOff"],
                report["expectedFailClosed"],
                report["canonicalPublication"],
                report["pass0ConsumerEnabled"],
            ),
            (api, True, expect_fail_closed, False, False),
        ),
        (
            f"frame_report.{api}.sources",
            (
                report["sources"]["producer"]["sha256"],
                report["sources"]["shader"]["sha256"],
                report["sources"]["pipeline"]["sha256"],
                report["sources"]["materialSource"]["sha256"],
            ),
            (
                transport["sources"]["producer"]["sha256"],
                transport["sources"]["shader"]["sha256"],
                transport["sources"]["pipeline"]["sha256"],
                transport["sources"]["material_source"]["sha256"],
            ),
        ),
        (
            f"frame_report.{api}.beauty",
            (
                report["beautyFrame"]["sha256"],
                report["beautyFrame"]["expectedSha256"],
                report["beautyFrame"]["unchanged"],
            ),
            (
                report["beautyFrame"]["expectedSha256"],
                report["beautyFrame"]["expectedSha256"],
                True,
            ),
        ),
        (f"frame_report.{api}.failures", report["failures"], []),
    )
    for check, actual, expected in checks:
        require_deferred_gbuffer_frame_value(source, check, actual, expected)

    if expect_fail_closed:
        require_deferred_gbuffer_frame_value(
            source,
            f"frame_report.{api}.fail_closed_payload",
            (report["activeFrame"], report["gpuReadbacks"]),
            ({}, {}),
        )
        return

    active = report["activeFrame"]
    require_deferred_gbuffer_frame_value(
        source,
        f"frame_report.{api}.active",
        active,
        {
            "camera": transport["source_camera"]["name"],
            "width": transport["extent"]["width"],
            "height": transport["extent"]["height"],
            "attachments": transport["attachment_signature"],
            "sourceRendererDisabled": True,
            "pass0ConsumerEnabled": False,
        },
    )
    require_deferred_gbuffer_frame_value(
        source,
        f"frame_report.{api}.readbacks",
        report["gpuReadbacks"],
        {
            role: {
                "camera": transport["source_camera"]["name"],
                "width": transport["extent"]["width"],
                "height": transport["extent"]["height"],
                "format": values["format"],
                "byteCount": transport["extent"]["byte_count_per_attachment"],
                "nonzeroBytes": values["nonzero_bytes"],
                "sha256": values["sha256"],
            }
            for role, values in expected_readbacks.items()
        },
    )


def verify_deferred_gbuffer_frame_transport(recovery: dict[str, object]) -> None:
    contract = json.loads(BINDING_CONTRACT_PATH.read_text(encoding="utf-8"))
    transport = recovery["same_camera_hgbuffer_sidecar"]
    require_deferred_gbuffer_frame_value(
        RECOVERY_PATH,
        "contract.transport",
        contract["deferred_gbuffer_frame_transport"],
        transport,
    )
    require_deferred_gbuffer_frame_value(
        RECOVERY_PATH,
        "transport.state",
        (
            transport["default_off"],
            transport["published"],
            transport["pass0_consumer_enabled"],
            transport["source_renderer_disabled"],
        ),
        (True, False, False, True),
    )
    require_deferred_gbuffer_frame_value(
        RECOVERY_PATH,
        "transport.material_state",
        transport["material_state"],
        {
            "_CullMode": 0,
            "_ZTestGBuffer": 4,
            "_ZWriteGBuffer": 1,
            "_StencilRef": 0,
            "_StencilOpGBuffer": 2,
        },
    )

    for entry in transport["sources"].values():
        require_hash(LAB_ROOT / entry["path"], entry["sha256"])
    validation = transport["validation"]
    for entry in (
        validation["validator"],
        validation["tests"],
        validation["wrapper"],
    ):
        require_hash(LAB_ROOT / entry["path"], entry["sha256"])

    reports: dict[str, dict[str, object]] = {}
    for api in ("d3d11", "d3d12"):
        evidence = validation["gpu_reports"][api]
        report_path = LAB_ROOT / evidence["path"]
        log_path = LAB_ROOT / evidence["log_path"]
        require_hash(report_path, evidence["sha256"])
        require_unity_log(
            log_path,
            evidence["log_sha256"],
            [
                f"Forcing GfxDevice: Direct3D {11 if api == 'd3d11' else 12}",
                "Recovered SphereOutside same-frame HGBuffer sidecar active:",
                "Recovered deferred HGBuffer GPU readback: role=SceneColor",
                "Recovered deferred HGBuffer GPU readback: role=GBufferC",
                "Exiting batchmode successfully now!",
            ],
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        verify_deferred_gbuffer_frame_report(transport, report, api)
        reports[api] = report
    require_deferred_gbuffer_frame_value(
        RECOVERY_PATH,
        "transport.cross_api_readbacks",
        reports["d3d11"]["gpuReadbacks"],
        reports["d3d12"]["gpuReadbacks"],
    )

    evidence = validation["fail_closed_d3d12"]
    report_path = LAB_ROOT / evidence["path"]
    log_path = LAB_ROOT / evidence["log_path"]
    require_hash(report_path, evidence["sha256"])
    require_unity_log(
        log_path,
        evidence["log_sha256"],
        [
            "Forcing GfxDevice: Direct3D 12",
            "Recovered SphereOutside same-frame HGBuffer sidecar failed closed: "
            "canonical binning/reflection/VisibilitySHConstData prerequisites "
            "are not ready.",
            "Exiting batchmode successfully now!",
        ],
    )
    fail_report = json.loads(report_path.read_text(encoding="utf-8"))
    verify_deferred_gbuffer_frame_report(
        transport,
        fail_report,
        "d3d12",
        expect_fail_closed=True,
    )

    producer = LAB_ROOT / transport["sources"]["producer"]["path"]
    shader = LAB_ROOT / transport["sources"]["shader"]["path"]
    pipeline = LAB_ROOT / transport["sources"]["pipeline"]["path"]
    require_tokens(
        producer,
        [
            "ENDFIELD_RECOVERED_DEFERRED_GBUFFER_FRAME",
            "RecoveredSphereOutsideHGBufferFrame",
            "GraphicsFormat.B10G11R11_UFloatPack32",
            "GraphicsFormat.A2B10G10R10_UNormPack32",
            "GraphicsFormat.R8G8B8A8_SRGB",
            "GraphicsFormat.D32_SFloat_S8_UInt",
            "command.SetGlobalMatrix(",
            "GpuViewProjectionId,",
            "command.RequestAsyncReadback",
            "command.SetRenderTarget(",
            "canonicalColorTarget,",
            "canonicalDepthTarget);",
            'pass0ConsumerEnabled=false',
        ],
    )
    require_tokens(
        shader,
        [
            'Name "RecoveredSphereOutsideHGBufferFrame"',
            "Cull [_CullMode]",
            "ZTest [_ZTestGBuffer]",
            "ZWrite [_ZWriteGBuffer]",
            "Ref [_StencilRef]",
            "Pass [_StencilOpGBuffer]",
            "float4 sceneColor : SV_Target0;",
            "float4 gBufferC : SV_Target4;",
            "_EndfieldRecoveredDeferredGpuViewProjection",
        ],
    )
    require_tokens(
        pipeline,
        [
            "EndfieldRecoveredDeferredGBufferFrame",
            "recoveredDeferredGBufferFrame.Render(",
            "recoveredCanonicalFrameResourcesReady,",
        ],
    )


def require_deferred_transform_variables_value(
    source: Path,
    check: str,
    actual: object,
    expected: object,
) -> None:
    if actual != expected:
        raise AssertionError(
            "Deferred TransformVariables validator failed: "
            f"check={check}; source={source}; "
            f"expected={expected!r}; actual={actual!r}"
        )


def verify_deferred_transform_variables_gpu_report(
    report: dict[str, object],
    api: str,
    source: Path,
) -> None:
    expected_vectors = [
        0, 1, 2, 3, 4, 5, 6, 7, 24, 25, 26, 27, 44
    ]
    require_deferred_transform_variables_value(
        source,
        f"transform_variables.{api}.identity",
        (
            report["schema"],
            report["valid"],
            report["graphicsApi"],
            report["defaultOff"],
            report["pass0ConsumerEnabled"],
            report["bufferBytes"],
            report["vectorCount"],
            report["d3d11SelectedBytes"],
        ),
        (
            "endfield-recovered-deferred-transform-variables-validation-v1",
            True,
            api,
            True,
            False,
            1312,
            82,
            720,
        ),
    )
    require_deferred_transform_variables_value(
        source,
        f"transform_variables.{api}.selected_vectors",
        report["selectedUsedVectors"],
        expected_vectors,
    )
    require_deferred_transform_variables_value(
        source,
        f"transform_variables.{api}.publication",
        (
            report["publicationReturnedReady"],
            report["readyObserved"],
            report["allPublishedWordsMatch"],
            report["selectedConsumerWordsMatch"],
            report["unresolvedRegistersZero"],
            report["viewInverseRoundTrip"],
            report["worldClipRoundTrip"],
            report["failures"],
        ),
        (True, True, True, True, True, True, True, []),
    )
    require_deferred_transform_variables_value(
        source,
        f"transform_variables.{api}.words",
        report["actualWords"],
        report["expectedWords"],
    )
    require_deferred_transform_variables_value(
        source,
        f"transform_variables.{api}.word_count",
        len(report["actualWords"]),
        328,
    )
    require_deferred_transform_variables_value(
        source,
        f"transform_variables.{api}.fail_closed_gates",
        [
            (row["gate"], row["rejected"], row["diagnosticMatched"])
            for row in report["failClosedGates"]
        ],
        [
            ("destination_size", True, True),
            ("nonfinite_camera", True, True),
            ("singular_view", True, True),
        ],
    )


def verify_deferred_transform_variables_transport(
    recovery: dict[str, object],
) -> None:
    contract = json.loads(BINDING_CONTRACT_PATH.read_text(encoding="utf-8"))
    transport = recovery["selected_deferred_transform_variables_transport"]
    require_deferred_transform_variables_value(
        RECOVERY_PATH,
        "transform_variables.contract_transport",
        contract["selected_deferred_transform_variables_transport"],
        transport,
    )
    require_deferred_transform_variables_value(
        RECOVERY_PATH,
        "transform_variables.state",
        (
            transport["default_off"],
            transport["published_by_default"],
            transport["pass0_consumer_enabled"],
            transport["logical_size_bytes"],
            transport["logical_vector_count"],
            transport["d3d11_bridge_size_bytes"],
            transport["selected_used_vector_count"],
        ),
        (True, False, False, 1312, 82, 720, 13),
    )

    require_hash(
        LAB_ROOT / transport["source_audit"]["path"],
        transport["source_audit"]["sha256"],
    )
    for entry in transport["sources"].values():
        require_hash(LAB_ROOT / entry["path"], entry["sha256"])

    validation = transport["validation"]
    frame_report_path = LAB_ROOT / validation["frame_report"]["path"]
    require_hash(frame_report_path, validation["frame_report"]["sha256"])
    frame_report = json.loads(frame_report_path.read_text(encoding="utf-8"))
    require_deferred_transform_variables_value(
        frame_report_path,
        "transform_variables.frame_summary",
        (
            frame_report["valid"],
            frame_report["defaultOff"],
            frame_report["pass0ConsumerEnabled"],
            frame_report["crossApiWordsBitExact"],
            frame_report["unresolvedRegistersZero"],
            frame_report["beautyUnchanged"],
            frame_report["failClosedWithoutCanonicalPrerequisites"],
        ),
        (True, True, False, True, True, True, True),
    )

    reports: dict[str, dict[str, object]] = {}
    active_token = (
        "Recovered selected deferred _TransformVariables b30 reads are active "
        "for the physical CharInfo camera; pass0=disabled."
    )
    for api in ("d3d11", "d3d12"):
        evidence = validation["gpu_reports"][api]
        report_path = LAB_ROOT / evidence["path"]
        log_path = LAB_ROOT / evidence["log_path"]
        require_hash(report_path, evidence["sha256"])
        require_unity_log(
            log_path,
            evidence["log_sha256"],
            [
                f"Forcing GfxDevice: Direct3D {11 if api == 'd3d11' else 12}",
                "Recovered canonical CharInfo binning + reflection oct/global + exact VisibilitySHConstData frame resources are active",
                active_token,
                "Exiting batchmode successfully now!",
            ],
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        verify_deferred_transform_variables_gpu_report(report, api, report_path)
        reports[api] = report
        beauty = frame_report["evidence"][api]["beauty"]
        require_hash(LAB_ROOT / beauty["path"], evidence["beauty_sha256"])

    require_deferred_transform_variables_value(
        RECOVERY_PATH,
        "transform_variables.cross_api_words",
        reports["d3d11"]["actualWords"],
        reports["d3d12"]["actualWords"],
    )

    fail = validation["fail_closed_d3d12"]
    require_unity_log(
        LAB_ROOT / fail["log_path"],
        fail["log_sha256"],
        [
            "Forcing GfxDevice: Direct3D 12",
            "Recovered selected deferred _TransformVariables failed closed: canonical binning/reflection/VisibilitySHConstData prerequisites are not ready.",
            "Exiting batchmode successfully now!",
        ],
    )
    fail_beauty = frame_report["evidence"]["failClosedD3D12"]["beauty"]
    require_hash(LAB_ROOT / fail_beauty["path"], fail["beauty_sha256"])

    sources = transport["sources"]
    require_tokens(
        LAB_ROOT / sources["contract"]["path"],
        [
            "SizeBytes = 1312",
            "D3D11SelectedSizeBytes = 720",
            "ViewFirstVector = 0",
            "InverseViewFirstVector = 4",
            "InverseViewProjectionFirstVector = 24",
            "CameraPositionVector = 44",
            "GL.GetGPUProjectionMatrix(",
            "Array.Clear(destination, 0, destination.Length)",
            "PackD3DColumnRegisters",
        ],
    )
    require_tokens(
        LAB_ROOT / sources["owner"]["path"],
        [
            "ENDFIELD_RECOVERED_DEFERRED_TRANSFORM_VARIABLES",
            'Shader.PropertyToID("_TransformVariables")',
            'Shader.PropertyToID("EndfieldCB0")',
            '"_EndfieldRecoveredDeferredTransformVariablesReady"',
            '"_EndfieldRecoveredDeferredPass0InputSubsetReady"',
        ],
    )
    require_tokens(
        LAB_ROOT / sources["pipeline"]["path"],
        [
            "EndfieldRecoveredDeferredTransformVariables",
            ".PrepareAndPublish(",
            '"_TransformVariables b30 reads are active "',
            '"VisibilitySHConstData prerequisites are not ready."',
        ],
    )
    require_tokens(
        LAB_ROOT / sources["probe"]["path"],
        [
            "cbuffer _TransformVariables",
            "float4 _EndfieldRecoveredDeferredTransformVectors[82]",
        ],
    )


def require_hdpls_matrix_value(
    source: Path,
    check: str,
    actual: object,
    expected: object,
) -> None:
    if actual != expected:
        raise AssertionError(
            "HDPLS matrix-production validator failed: "
            f"check={check}; source={source}; "
            f"expected={expected!r}; actual={actual!r}"
        )


def verify_hdpls_matrix_formula_contract(
    hdpls_native: dict[str, object],
    hdpls_audit: dict[str, object],
    source: Path = BINDING_CONTRACT_PATH,
) -> None:
    matrix_production = hdpls_audit["matrix_production"]
    checks = (
        (
            "native.matrix_formula_scope",
            hdpls_native["matrix_formula_scope"],
            "installed non-IFix-patched GetShadowParamsFromCharacter id 0x877 "
            "and HGShadowUtils spot-row branches",
        ),
        (
            "native.character_shadow_transform",
            hdpls_native["character_shadow_transform"],
            "radius=length(bounds.extents); direction=bounds.center-lightPosition; "
            "rotation=LookRotation(direction) when distance>1e-5 else "
            "light.localToWorldMatrix.rotation; "
            "localToWorld=TRS(lightPosition,rotation,one)",
        ),
        (
            "native.character_spot_angle",
            hdpls_native["character_spot_angle"],
            "radius<=1e-6 -> 0.1 degrees; radius+1e-5>=distance -> 179.9 "
            "degrees; else clamp(2*asinf(clamp(radius/distance,0,1))*"
            "57.295780181884766,0.1,179.9)",
        ),
        (
            "matrix_production.scope",
            matrix_production["scope"],
            "installed GetShadowParamsFromCharacter non-IFix-patched branch "
            "(IFix patch id 0x877) followed by the installed non-IFix-patched "
            "HGShadowUtils spot-row branch",
        ),
        (
            "matrix_production.character_sphere",
            matrix_production["character_sphere"],
            {
                "center": "bounds.center",
                "radius": "length(bounds.extents)",
                "radius_threshold": 1e-6,
            },
        ),
        (
            "matrix_production.light_direction",
            matrix_production["light_direction"],
            {
                "light_position": "HGSharedLightData.worldPosition",
                "direction": "bounds.center - light_position",
                "distance": "length(direction)",
                "direction_epsilon": 1e-5,
            },
        ),
        (
            "matrix_production.local_to_world",
            matrix_production["local_to_world"],
            {
                "rotation": (
                    "Quaternion.LookRotation(direction) when distance>1e-5; "
                    "otherwise HGSharedLightData.localToWorldMatrix.rotation"
                ),
                "matrix": "Matrix4x4.TRS(light_position, rotation, Vector3.one)",
            },
        ),
        (
            "matrix_production.spot_angle_degrees",
            matrix_production["spot_angle_degrees"],
            {
                "radius_le_threshold": 0.1,
                "radius_plus_epsilon_ge_distance": 179.9,
                "general": (
                    "clamp(2*asinf(clamp(radius/distance,0,1))*"
                    "57.295780181884766,0.1,179.9)"
                ),
            },
        ),
        (
            "matrix_production.shadow_utility_chain.view",
            matrix_production["shadow_utility_chain"]["view"],
            "inverse(derived localToWorld), then negate m20,m21,m22,m23",
        ),
        (
            "matrix_production.shadow_utility_chain.world_to_shadow",
            matrix_production["shadow_utility_chain"]["world_to_shadow"],
            {
                "formula": "B * (P' * V)",
                "reversedZ": (
                    "when UsesReversedZBuffer, P' negates m20,m21,m22,m23"
                ),
                "scaleBiasB": (
                    "diag(0.5,0.5,0.5,1) with translation (0.5,0.5,0.5)"
                ),
                "storedField": "_PunctualLightWorldToShadow[row]",
            },
        ),
        (
            "matrix_production.render_pass_bias",
            matrix_production["render_pass_bias"],
            {
                "depth_bias": "hdplsDepthBias.value -> pass data +0x10",
                "normal_bias": "hdplsNormalBias.value -> pass data +0x14",
            },
        ),
    )
    for check, actual, expected in checks:
        require_hdpls_matrix_value(source, check, actual, expected)


def require_hdpls_resource_value(
    source: Path,
    check: str,
    actual: object,
    expected: object,
) -> None:
    if actual != expected:
        raise AssertionError(
            "HDPLS resource-lifecycle validator failed: "
            f"check={check}; source={source}; "
            f"expected={expected!r}; actual={actual!r}"
        )


def verify_hdpls_resource_lifecycle_contract(
    hdpls_native: dict[str, object],
    hdpls_audit: dict[str, object],
    source: Path = BINDING_CONTRACT_PATH,
) -> None:
    lifecycle = hdpls_audit["resource_lifecycle"]
    atlas = hdpls_audit["frame_derived_formulas"]["atlas"]
    checks = (
        (
            "audit.verdict",
            hdpls_audit["verdict"],
            "INSTALLED_IFIX_AND_RESOURCE_LIFECYCLE_CLOSED_"
            "ACTIVE_PIXELS_CAPTURE_REQUIRED",
        ),
        (
            "installed_ifix_state",
            hdpls_audit["installed_ifix_state"],
            {
                "scope": "hash-pinned files currently installed on this machine",
                "base_ifix_file_count": 0,
                "persistent_ifix_file_count": 1,
                "persistent_target_count": 32,
                "checked_hdpls_signatures": [
                    {
                        "type": (
                            "HG.Rendering.Runtime."
                            "HGHDPLSCharacterShadowManager"
                        ),
                        "method": "GetShadowParamsFromCharacter",
                        "wrapper_gate": "0x877",
                    },
                    {
                        "type": (
                            "HG.Rendering.Runtime."
                            "ScreenSpaceShadowMaskPassConstructor"
                        ),
                        "method": "RenderHDPLSScreenSpaceShadowResolve",
                        "wrapper_gate": "0x890",
                    },
                ],
                "matching_target_count": 0,
                "current_route": "both recovered non-IFix branches",
                "version_boundary": (
                    "future/network, memory-only, or differently installed "
                    "patches remain outside this static snapshot"
                ),
            },
        ),
        (
            "native.texture_roles",
            hdpls_native["texture_roles"],
            {
                "raw_atlas_global": "_HDPLSTex",
                "screen_resolve_global": "_HDPLSScreenSpaceShadowMask",
                "deferred_binding_22": "_HDPLSScreenSpaceShadowMask",
            },
        ),
        (
            "atlas.descriptor",
            atlas["descriptor"],
            {
                "depth_buffer_bits": 16,
                "graphics_format_value": 90,
                "graphics_format": "D16_UNorm",
                "filter_mode_value": 1,
                "filter_mode": "Bilinear",
                "wrap_mode_value": 1,
                "wrap_mode": "Clamp",
                "dimension_value": 2,
                "dimension": "Tex2D",
                "slices": 1,
                "is_shadow_map": False,
                "use_mip_map": False,
                "enable_random_write": False,
                "msaa_samples": 1,
                "clear_buffer": False,
            },
        ),
        (
            "screen_resolve.size",
            lifecycle["screen_resolve"]["size"],
            "camera render size; when reduction is enabled and width>1920 or "
            "height>1080, floor(size*min(1920/width,1080/height)), each axis "
            "clamped to at least 1",
        ),
        (
            "screen_resolve.descriptor",
            lifecycle["screen_resolve"]["descriptor"],
            {
                "graphics_format_value": 8,
                "graphics_format": "R8G8B8A8_UNorm",
                "filter_mode_value": 1,
                "filter_mode": "Bilinear",
                "wrap_mode_value": 1,
                "wrap_mode": "Clamp",
                "dimension": "Tex2D",
                "slices": 1,
                "use_mip_map": False,
                "enable_random_write": False,
                "msaa_samples": 1,
            },
        ),
        (
            "screen_resolve.render_graph",
            lifecycle["screen_resolve"]["render_graph"],
            {
                "allow_pass_culling": False,
                "reads": [
                    "scene depth buffer",
                    "sampleable depth",
                    "s_hdplsAtlas",
                ],
                "writes": "hdplsScreenSpaceShadowTexture",
                "color_attachment": {
                    "index": 0,
                    "load_action_value": 2,
                    "load_action": "DontCare",
                    "store_action_value": 3,
                    "store_action": "DontCare",
                    "explicit_clear": False,
                },
                "depth_attachment": {
                    "resource": "scene depth buffer",
                    "access_value": 1,
                    "access": "Read",
                    "slice": 0,
                },
            },
        ),
        (
            "screen_resolve.shader",
            lifecycle["screen_resolve"]["shader"],
            {
                "material_pass": 2,
                "inputs": [
                    "_CameraDepthTexture",
                    "_PunctualLightShadowTexV2",
                    "_HDPLSTex",
                    "_GBufferTexture1",
                ],
                "output": "four independent HDPLS screen-space channels in RGBA",
                "global_output": "HGShaderIDs._HDPLSScreenSpaceShadowMask",
            },
        ),
        (
            "inactive_fallback",
            lifecycle["inactive_fallback"],
            {
                "constant_buffer": "all 56 selected channel values are zero",
                "_HDPLSTex": "Texture2D.whiteTexture",
                "_HDPLSScreenSpaceShadowMask": "Texture2D.whiteTexture",
                "consumer_result": (
                    "selected deferred resolver takes punctual-atlas fallback"
                ),
            },
        ),
        (
            "logical_global_boundary",
            lifecycle["logical_global_boundary"],
            "_HDPLSTex is the raw D16 atlas input; "
            "_HDPLSScreenSpaceShadowMask is the RGBA8 resolved output consumed "
            "by the deferred HDPLS channel path",
        ),
    )
    for check, actual, expected in checks:
        require_hdpls_resource_value(source, check, actual, expected)


def verify_visibility_sh_unity_replay() -> None:
    payload = json.loads(
        VISIBILITY_RUNTIME_PATH.read_text(encoding="utf-8")
    )
    assert payload["schema"] == "endfield.visibility-sh-runtime.v1"
    assert payload["source"]["sphereMeshPathId"] == (
        "-497958453517564970"
    )
    assert payload["source"]["sphereMeshVertexCount"] == 79
    assert payload["source"]["sphereMeshIndexCount"] == 336
    assert payload["retailDefaults"] == {
        "enabled": True,
        "halfResolution": True,
        "sphereIntervalScale": 0.8,
        "sphereRangeScale": 5.0,
    }
    assert payload["retailCulling"] == {
        "boundsCenter": "worldCenter",
        "boundsExtentFormula": "0.5 * fullHeight * 5.0 on X/Y/Z",
        "survivorOrder": "stable manager query/registration order",
    }
    assert [actor["name"] for actor in payload["actors"]] == [
        "Wulfa",
        "Zhuangfy",
    ]
    assert [len(actor["capsules"]) for actor in payload["actors"]] == [
        10,
        10,
    ]
    assert len(
        base64.b64decode(
            payload["visibilityShLutRgba32Base64"],
            validate=True,
        )
    ) == 1024

    shader = ASSET_ROOT / "Resources" / (
        "EndfieldRecoveredVisibilitySH.shader"
    )
    producer = ASSET_ROOT / "Runtime" / "Rendering" / (
        "EndfieldRecoveredVisibilitySHProducer.cs"
    )
    pipeline = ASSET_ROOT / "Runtime" / "Rendering" / (
        "HGCompatRenderPipeline.cs"
    )
    require_tokens(
        shader,
        [
            'Name "DOWNSAMPLE_DEPTH"',
            "_InputDepthTexture.GatherRed(",
            "return min(min(gathered.x, gathered.y),",
            'Name "CAPSULE_VISIBILITY_SH"',
            "Blend One One, One One",
            "ZTest [_VisibilityZTest]",
            "Cull [_VisibilityCull]",
            "Ref 4",
            "ReadMask 7",
            "Comp NotEqual",
            "StructuredBuffer<CapsuleData> _VisibilityCapsules;",
            "_LogSHLutTex.SampleLevel(",
            "0.282094806432724",
            "-0.488602489233017",
        ],
    )
    require_tokens(
        producer,
        [
            "ENDFIELD_RECOVERED_VISIBILITY_SH",
            "-endfield-recovered-visibility-sh",
            'Shader.PropertyToID("_VisibilitySHRT")',
            'Shader.PropertyToID("_EndfieldRecoveredVisibilitySH")',
            "GraphicsFormat.R16G16B16A16_SFloat",
            "GraphicsFormat.D32_SFloat_S8_UInt",
            "commandBuffer.RequestAsyncReadback(",
            "DrawMeshInstancedProcedural(",
            "float fullHeight = Mathf.Max(",
            "float cullExtent =",
            "0.5f * fullHeight * 5.0f;",
            "GeometryUtility.TestPlanesAABB(",
            "survivorIndices[count - 1] = sourceIndex;",
            "Mathf.Clamp(source.intensity, 0.01f, 2.0f)",
            "commandBuffer.SetRenderTarget(",
            "canonicalColorTarget,",
            "canonicalDepthTarget);",
        ],
    )
    require_tokens(
        pipeline,
        [
            "recoveredVisibilitySHProducer.Requested",
            "recoveredVisibilitySHProducer.Render(",
            "recoveredVisibilitySHProducer.ResetAfterForward(context);",
        ],
    )


def verify_hgbuffer(recovery: dict[str, object]) -> None:
    selected = recovery["selected_hgbuffer"]
    assert selected["shader"] == "HGRP/Lit"
    assert selected["pass"] == "HGBuffer"
    assert selected["keywords"] == ["HG_ENABLE_MV", "SRP_INSTANCING_ON"]

    material_record = selected["material"]
    material_path = SOURCE_ROOT / material_record["path"]
    assert material_path.stat().st_size == material_record["size"]
    require_hash(material_path, material_record["sha256"])

    for stage in ("vertex_dxbc", "fragment_dxbc"):
        record = selected[stage]
        require_hash(SOURCE_ROOT / record["path"], record["sha256"])

    for stage in ("decompiled_vertex", "decompiled_fragment"):
        record = selected[stage]
        require_hash(repo_path(record["repo_path"]), record["sha256"])

    fragment = repo_path(selected["decompiled_fragment"]["repo_path"])
    require_tokens(
        fragment,
        [
            "float4 SV_Target : SV_Target0;",
            "float4 SV_Target_1 : SV_Target1;",
            "float4 SV_Target_2 : SV_Target2;",
            "float4 SV_Target_3 : SV_Target3;",
            "float4 SV_Target_4 : SV_Target4;",
            "SV_Target.w = 0.5f;",
            "SV_Target_3.x = mad(",
            "SV_Target_4.w = 0.0f;",
        ],
    )


def parse_resolver(path: Path) -> tuple[list[str], set[str], int, str]:
    pass_names: list[str] = []
    keywords: set[str] = set()
    d3d11_variants = 0
    text_parts: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            stripped = line.strip()
            if stripped.startswith('Name "'):
                pass_names.append(stripped[6:-1])
            if stripped == 'SubProgram "d3d11 " {':
                d3d11_variants += 1
            if stripped.startswith("Keywords {"):
                keywords.update(re.findall(r'"([^"]+)"', stripped))
            if len(text_parts) < 30:
                text_parts.append(line)
    return pass_names, keywords, d3d11_variants, "".join(text_parts)


def parse_pass_headers(path: Path, count: int) -> list[tuple[str, list[str]]]:
    headers: list[tuple[str, list[str]]] = []
    current_name = ""
    current_lines: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            stripped = line.strip()
            if stripped.startswith('Name "'):
                current_name = stripped[6:-1]
                current_lines = [stripped]
                continue
            if not current_name:
                continue
            if stripped == 'Program "vp" {':
                headers.append((current_name, current_lines))
                current_name = ""
                current_lines = []
                if len(headers) == count:
                    break
                continue
            current_lines.append(stripped)
    return headers


def verify_resolvers(recovery: dict[str, object]) -> None:
    records = recovery["resolver_shader_dumps"]
    by_shader = {record["shader"]: record for record in records}
    assert set(by_shader) == {
        "HGRP/DeferredLighting",
        "HGRP/DeferredLightingPerLight",
        "HGRP/DeferredLightingWriteAlpha",
        "HGRP/Lit",
    }
    for record in records:
        path = repo_path(record["repo_path"])
        assert path.stat().st_size == record["size"], path
        require_hash(path, record["sha256"])

    deferred = repo_path(by_shader["HGRP/DeferredLighting"]["repo_path"])
    pass_names, keywords, d3d11_variants, header = parse_resolver(deferred)
    expected = recovery["deferred_resolver"]
    expected_passes = expected["pass_names"]
    subshader_count = expected["serialized_subshader_count"]
    assert len(pass_names) == len(expected_passes) * subshader_count
    for subshader_index in range(subshader_count):
        start = subshader_index * len(expected_passes)
        assert pass_names[start : start + len(expected_passes)] == expected_passes
    assert keywords == set(expected["keyword_axes"])
    assert d3d11_variants == expected["d3d11_variant_count"] * subshader_count
    for token in (
        "Blend 0 One SrcAlpha, One SrcAlpha",
        "Blend 1 One One, One One",
        "ZTest Greater",
        "ZWrite Off",
        "ReadMask 7",
        "Comp Equal",
    ):
        assert token in header, token

    first_headers = parse_pass_headers(deferred, 3)
    assert [name for name, _ in first_headers] == expected_passes[:3]
    assert "Ref 0" not in first_headers[0][1]
    assert "Ref 1" in first_headers[1][1]
    assert "Ref 2" in first_headers[2][1]
    for _, lines in first_headers:
        assert "ReadMask 7" in lines
        assert "Comp Equal" in lines

    write_alpha = repo_path(
        by_shader["HGRP/DeferredLightingWriteAlpha"]["repo_path"]
    )
    require_tokens(
        write_alpha,
        [
            "ColorMask A 0",
            "ZTest Greater",
            "ZWrite Off",
            "Cull Off",
            "ReadMask 7",
            "Comp Equal",
            "Ref 1",
            "Ref 2",
        ],
    )


def verify_native_map(recovery: dict[str, object]) -> None:
    native = recovery["native_runtime_evidence"]
    metadata_record = native["global_metadata"]
    metadata_path = Path(metadata_record["path_at_recovery"])
    if metadata_path.is_file():
        assert metadata_path.stat().st_size == metadata_record["size"]
        require_hash(metadata_path, metadata_record["sha256"])
    require_hash(
        repo_path(native["targeted_metadata"]["repo_path"]),
        native["targeted_metadata"]["sha256"],
    )
    map_record = native["targeted_native_map"]
    native_path = repo_path(map_record["repo_path"])
    require_hash(native_path, map_record["sha256"])
    payload = json.loads(native_path.read_text(encoding="utf-8"))
    assert payload["summary"]["mappedTargetCount"] == map_record["mapped_targets"]
    assert payload["summary"]["catalogBodyTargetCount"] == map_record["catalog_targets"]
    assert payload["settings"]["codeRegistration"] == native["code_registration"]
    assert payload["codeRegistration"]["va"] == native["code_registration"]

    expected = native["method_indices"]
    expected_vas = native["method_vas"]
    found: dict[str, int] = {}
    found_vas: dict[str, str] = {}
    for method in payload["bodyTargets"]:
        key = f'{method["type"].rsplit(".", 1)[-1]}.{method["method"]}'
        found[key] = method["methodIndex"]
        found_vas[key] = method["methodPointerVa"]
        assert method["mappingStatus"] == "mapped", key
    assert found == expected
    assert found_vas == expected_vas

    init = native["unpatched_init_semantics"]
    assert init["ifix_patch_id"] == "0xbe4"
    assert len(init["ordered_feature_sources"]) == 9
    assert len(init["ordered_result_fields"]) == 9
    assert init["when_is_one_pass_deferred_false_force_off"] == [
        "splitDeferredShadingStage",
        "enableDeferredShadingTileDraw",
    ]
    init_method = next(
        method
        for method in payload["bodyTargets"]
        if method["method"] == "InitDeferredLightingRenderParams"
    )
    enabled_calls = [
        resolved
        for call in init_method["directCalls"]
        for resolved in call.get("resolved", [])
        if resolved["type"].endswith("HGGraphicsFeatureSwitch")
        and resolved["method"] == "get_enabled"
    ]
    assert len(enabled_calls) == 9

    support = native["static_supporting_evidence"]
    for key in (
        "feature_manager_metadata",
        "constructor_metadata",
        "render_graph_metadata",
    ):
        record = support[key]
        require_hash(repo_path(record["repo_path"]), record["sha256"])

    feature_record = support["feature_manager_native_map"]
    feature_path = repo_path(feature_record["repo_path"])
    require_hash(feature_path, feature_record["sha256"])
    feature_map = json.loads(feature_path.read_text(encoding="utf-8"))
    assert feature_map["summary"]["mappedTargetCount"] == feature_record["mapped_targets"]
    assert feature_map["summary"]["catalogBodyTargetCount"] == feature_record["catalog_targets"]
    cctor = next(
        method
        for method in feature_map["bodyTargets"]
        if method["type"].endswith("HGGraphicsFeatureManager")
        and method["method"] == ".cctor"
    )
    assert cctor["methodIndex"] == feature_record["cctor_method_index"]
    assert cctor["methodPointerVa"] == feature_record["cctor_va"]

    constructor_record = support["constructor_native_map"]
    constructor_path = repo_path(constructor_record["repo_path"])
    require_hash(constructor_path, constructor_record["sha256"])
    constructor_map = json.loads(constructor_path.read_text(encoding="utf-8"))
    assert constructor_map["summary"]["mappedTargetCount"] == constructor_record["mapped_targets"]
    assert constructor_map["summary"]["catalogBodyTargetCount"] == constructor_record["catalog_targets"]
    render_lambda = next(
        method
        for method in constructor_map["bodyTargets"]
        if method["method"] == "<.cctor>b__13_0"
    )
    assert render_lambda["methodIndex"] == constructor_record["render_lambda_method_index"]
    assert render_lambda["methodPointerVa"] == constructor_record["render_lambda_va"]
    construct_pass = next(
        method
        for method in constructor_map["bodyTargets"]
        if method["method"] == "ConstructPass"
    )
    prepare_call = next(
        call
        for call in construct_pass["directCalls"]
        if any(
            resolved["method"] == "PrepareDeferredLightingPass"
            for resolved in call.get("resolved", [])
        )
    )
    assert any(
        instruction["text"] == "mov [rsp+0x30], 0x0"
        for instruction in prepare_call["argumentContext"]["nearbyInstructions"]
    )
    init_call = next(
        call
        for call in render_lambda["directCalls"]
        if any(
            resolved["method"] == "InitDeferredLightingRenderParams"
            for resolved in call.get("resolved", [])
        )
    )
    assert init_call["argumentContext"]["argRegisterWrites"]["rdx"]["write"]["value"] == "0"
    write_alpha_call = next(
        call
        for call in render_lambda["directCalls"]
        if any(
            resolved["method"] == "DrawDeferredLightingWriteAlpha"
            for resolved in call.get("resolved", [])
        )
    )
    assert any(
        instruction["text"] == "mov [rsp+0x20], 0x1"
        for instruction in write_alpha_call["argumentContext"]["nearbyInstructions"]
    )

    shader_ids_record = support["shader_ids_metadata"]
    shader_ids_path = repo_path(shader_ids_record["repo_path"])
    require_hash(shader_ids_path, shader_ids_record["sha256"])
    shader_catalog = json.loads(shader_ids_path.read_text(encoding="utf-8"))
    shader_ids_type = next(
        type_row
        for type_row in shader_catalog["matchedTypes"]
        if type_row["fullName"] == "HG.Rendering.Runtime.HGShaderIDs"
    )
    shader_field_names = {field["name"] for field in shader_ids_type["fields"]}
    assert {
        "_GBufferTexture",
        "_CameraDepthTexture",
        "_PreviousSceneColorTexture",
        "_WaterWetnessMaskTexture",
        "_SSRLightingTexture",
        "_SSRFadenessTexture",
        "_IndirectAmbientOcclusionTexture",
        "_FakePlanarReflectionTexture",
    }.issubset(shader_field_names)
    pass_data_type = next(
        type_row
        for type_row in shader_catalog["matchedTypes"]
        if type_row["fullName"].endswith("DeferredLightingPassData")
    )
    pass_data_fields = [field["name"] for field in pass_data_type["fields"]]
    assert pass_data_fields[2:10] == [
        "depthTexture",
        "previousSceneColorTexture",
        "indirectAmbientOcclusionTexture",
        "ssrLightingTexture",
        "ssrFadenessTexture",
        "planarReflectionTexture",
        "fogBakeLutTexture",
        "waterWetnessMaskTexture",
    ]

    render_graph_record = support["render_graph_metadata"]
    render_graph_catalog = json.loads(
        repo_path(render_graph_record["repo_path"]).read_text(encoding="utf-8")
    )
    builder_type = next(
        type_row
        for type_row in render_graph_catalog["matchedTypes"]
        if type_row["fullName"].endswith("HGRenderGraphBuilder")
    )
    builder_methods = {method["index"]: method for method in builder_type["methods"]}
    assert builder_methods[283474]["parameters"][:4] == [
        "input",
        "index",
        "loadAction",
        "storeAction",
    ]
    assert builder_methods[283475]["parameters"] == [
        "input",
        "flags",
        "depthSlice",
    ]
    depth_access_type = next(
        type_row
        for type_row in render_graph_catalog["matchedTypes"]
        if type_row["fullName"].endswith("DepthAccess")
    )
    assert [field["name"] for field in depth_access_type["fields"]] == [
        "value__",
        "Read",
        "Write",
        "ReadWrite",
    ]

    for key in ("unity_texture_defaults_metadata",):
        record = support[key]
        require_hash(repo_path(record["repo_path"]), record["sha256"])
    texture_record = support["unity_texture_defaults_native_map"]
    texture_path = repo_path(texture_record["repo_path"])
    require_hash(texture_path, texture_record["sha256"])
    texture_map = json.loads(texture_path.read_text(encoding="utf-8"))
    assert texture_map["summary"]["mappedTargetCount"] == texture_record["mapped_targets"]
    assert texture_map["summary"]["catalogBodyTargetCount"] == texture_record["catalog_targets"]
    white_texture = next(
        method
        for method in texture_map["bodyTargets"]
        if method["method"] == "get_whiteTexture"
    )
    assert white_texture["methodPointerVa"] == texture_record["white_texture_va"]

    ifix_record = support["installed_ifix_patch_index"]
    ifix_path = repo_path(ifix_record["repo_path"])
    require_hash(ifix_path, ifix_record["sha256"])
    ifix_index = json.loads(ifix_path.read_text(encoding="utf-8"))
    assert ifix_index["blockFilter"] == ifix_record["block"]
    for key in ("file_count", "chunk_count", "byte_count"):
        index_key = "".join(
            [key.split("_")[0]]
            + [part.title() for part in key.split("_")[1:]]
        )
        assert ifix_index["summary"][index_key] == ifix_record[key]
    assert ifix_record["block_version"] == 23167343
    assert ifix_record["target_count"] == 32
    assert ifix_record["character_recovery_locally_replaced"] is False
    state_record = ifix_record["state_report"]
    state_path = repo_path(state_record["repo_path"])
    assert state_path.stat().st_size == state_record["size"]
    require_hash(state_path, state_record["sha256"])
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["patch_format"]["target_count"] == ifix_record["target_count"]
    assert state["character_recovery_target_audit"]["locally_replaced"] is False
    assert not any(
        target["type"].startswith("HG.Rendering.Runtime")
        or target["method"]
        in {
            "PrepareRenderPipelineSettings",
            "get_settingParameters",
            "set_settingParameters",
        }
        for target in state["targets"]
    )

    route = native["offline_unpatched_charinfo_route"]
    assert route["render_lambda_is_one_pass_deferred"] is False
    assert list(route["resolved_render_booleans"].values()) == [
        True,
        True,
        True,
        False,
        False,
        True,
        True,
        True,
        False,
    ]
    assert [draw.get("pass_index") for draw in route["resolver_draws"][:3]] == [0, 1, 2]
    write_alpha_draw = route["resolver_draws"][3]
    assert write_alpha_draw["shader"] == "HGRP/DeferredLightingWriteAlpha"
    assert write_alpha_draw["pass_indices_when_enabled"] == [0, 1, 2]
    assert "HGUtils.RenderWithAlpha" in write_alpha_draw["selection"]
    assert write_alpha_draw["settled_gacha_result"] is False
    assert write_alpha_draw["selected_gacha_draws"] == []
    gbuffer_submission = recovery["default_deferred_gbuffer_submission"]
    assert gbuffer_submission["shader_pass_name"] == "HGBuffer"
    assert gbuffer_submission["renderer_list_light_mode"] == "GBuffer"
    assert gbuffer_submission["color_attachments_in_order"] == [
        "SceneColor",
        "SceneMV when valid",
        "GBufferA",
        "GBufferB",
        "GBufferC",
    ]
    assert gbuffer_submission["depth_attachment"]["access_value"] == 2
    scene_color = gbuffer_submission["scene_color_producer"]
    require_hash(
        repo_path(scene_color["audit_path"]),
        scene_color["audit_sha256"],
    )
    assert scene_color["logical_descriptor_source_closed"] is True
    assert scene_color["graphics_format"] == "B10G11R11_UFloatPack32"
    assert scene_color["graphics_format_enum"] == 74
    assert scene_color["has_alpha_channel"] is False
    assert scene_color["filter_mode"] == "Point"
    assert scene_color["wrap_mode"] == "Clamp"
    assert scene_color["clear_color"] == [0.025, 0.07, 0.19, 0.0]
    assert scene_color["physical_allocation_source_closed"] is False
    resolver_resources = recovery["runtime_resolver_resources"]
    assert resolver_resources["runtime_resources_path_id"] == 5613980184714137857
    assert resolver_resources["deferred"]["path_id"] == 6850169740889141214
    assert resolver_resources["write_alpha"]["path_id"] == 1251403764302302053
    assert resolver_resources["per_light"]["path_id"] == 1386032630407682696
    keyword_state = recovery["selected_resolver_keyword_state"]
    require_hash(
        repo_path(keyword_state["audit_path"]),
        keyword_state["audit_sha256"],
    )
    assert keyword_state["source_closed"] is True
    assert keyword_state["HG_ENABLE_SCREEN_SPACE_SHADOW_MASK"] is True
    assert (
        keyword_state["HG_USE_SUBPASS_INPUT_UNDER_ONE_PASS_DEFERRED"]
        is False
    )
    assert (
        keyword_state["exact_executed_pass0_program_pair_source_closed"]
        is True
    )
    selection = keyword_state["installed_player_fallback_selection"]
    assert selection["source_closed"] is True
    assert selection["variant_pair_count"] == 64
    assert selection["unique_winner"] is True
    assert selection["selected_serialized_order"] == 96
    assert selection["selected_score"] == -15
    assert selection["runner_up_score"] == -16
    assert selection["request_enabled_keywords"] == [
        "HG_ENABLE_SCREEN_SPACE_SHADOW_MASK"
    ]
    assert selection["selected_compiled_keywords"] == [
        "HG_ENABLE_SCREEN_SPACE_SHADOW_MASK",
        "HG_USE_SUBPASS_INPUT_UNDER_ONE_PASS_DEFERRED",
    ]
    require_hash(
        repo_path(selection["fallback_program_audit_path"]),
        selection["fallback_program_audit_sha256"],
    )
    pair = selection["selected_d3d11_pair"]
    for stage in ("vertex", "fragment"):
        require_hash(repo_path(pair[stage]["path"]), pair[stage]["sha256"])
    execution = selection["isolated_original_bytecode_execution"]
    require_hash(
        repo_path(execution["audit_path"]),
        execution["audit_sha256"],
    )
    execution_report = json.loads(
        repo_path(execution["audit_path"]).read_text(encoding="utf-8")
    )
    assert execution_report["verdict"] == "ACTIVATION"
    assert execution_report["production_room_draw_enabled"] is False
    standalone = execution_report["standalone_validation"]
    assert standalone["status"] == "pass"
    assert standalone["graphics_device_type"] == "Direct3D11"
    assert standalone["vertex_swap_count"] == 1
    assert standalone["pixel_swap_count"] == 1
    assert standalone["resource_binding_compatible"] is True
    assert standalone["neutral_fixture_numeric_fidelity"] is False
    write_alpha_port = resolver_resources["unity_write_alpha_port"]
    write_alpha_port_path = LAB_ROOT / write_alpha_port["path"]
    require_hash(write_alpha_port_path, write_alpha_port["sha256"])
    assert write_alpha_port["runtime_enabled"] is False
    assert write_alpha_port["pass_indices"] == [0, 1, 2]
    assert write_alpha_port["stencil_refs"] == [0, 1, 2]
    assert (
        write_alpha_port["vertex_dxbc_sha256"]
        == "81C3531A3981DC2C4367449B4148613912C228572770511BB0AD767363F3E810"
    )
    assert (
        write_alpha_port["fragment_dxbc_sha256"]
        == "E1C62FBCEC8B1ADB4F28717C4A9D5A47D7D517D456F07945B60C1891C4191E32"
    )
    require_tokens(
        write_alpha_port_path,
        [
            'Shader "Hidden/Endfield/HGRPCompat/RecoveredDeferredLightingWriteAlpha"',
            'Name "DefaultLitWriteAlpha"',
            'Name "TwoSidedFoliageWriteAlpha"',
            'Name "SubsurfaceWriteAlpha"',
            "ColorMask A",
            "ZTest Greater",
            "ZWrite Off",
            "Cull Off",
            "ReadMask 7",
            "Comp Equal",
            "Ref 0",
            "Ref 1",
            "Ref 2",
            "float4(0.0, 0.0, 0.0, 1.0)",
        ],
    )
    write_alpha_gpu = write_alpha_port["gpu_validation"]
    write_alpha_report_path = repo_path(write_alpha_gpu["report_path"])
    write_alpha_log_path = repo_path(write_alpha_gpu["log_path"])
    require_hash(write_alpha_report_path, write_alpha_gpu["report_sha256"])
    require_unity_log(
        write_alpha_log_path,
        write_alpha_gpu["log_sha256"],
        [
            "EndfieldGraphShaderLabEditor." +
            "EndfieldDeferredWriteAlphaBatchVerifier.BuildAndValidate",
            "Deferred WriteAlpha diagnostic report:",
            "Application will terminate with return code 0",
        ],
    )
    write_alpha_report = json.loads(
        write_alpha_report_path.read_text(encoding="utf-8")
    )
    assert write_alpha_report["status"] == "pass"
    assert write_alpha_report["graphics_device"] == "Direct3D12"
    assert write_alpha_report["runtime_submitted"] is False
    assert [
        (
            case["pass"],
            case["stencil"],
            case["expected_alpha_written"],
            case["rgba_sha256"],
        )
        for case in write_alpha_report["cases"]
    ] == [
        (0, 0, True, write_alpha_gpu["matching_stencil_rgba_sha256"]),
        (0, 1, False, write_alpha_gpu["mismatching_stencil_rgba_sha256"]),
        (1, 1, True, write_alpha_gpu["matching_stencil_rgba_sha256"]),
        (1, 2, False, write_alpha_gpu["mismatching_stencil_rgba_sha256"]),
        (2, 2, True, write_alpha_gpu["matching_stencil_rgba_sha256"]),
        (2, 0, False, write_alpha_gpu["mismatching_stencil_rgba_sha256"]),
    ]
    bindings = {
        binding["pass_data_field"]: binding
        for binding in route["render_lambda_global_bindings"]
    }
    assert set(bindings) == {
        "gbuffer",
        "depthTexture",
        "previousSceneColorTexture",
        "waterWetnessMaskTexture",
        "fogBakeLutTexture",
        "ssrLightingTexture",
        "ssrFadenessTexture",
        "indirectAmbientOcclusionTexture",
        "planarReflectionTexture",
    }
    assert bindings["waterWetnessMaskTexture"]["condition"].endswith(
        "UnityEngine.Texture2D.whiteTexture"
    )
    attachment_route = route["render_graph_attachment_route"]
    assert attachment_route["change_color_rt"] is False
    assert attachment_route["color"] == {
        "source": "PassInput.sceneColor",
        "input_object_offset": "0x0",
        "attachment_index": 0,
        "load_action": "Load",
        "store_action": "Store",
        "clear_color_argument": "UnityEngine.Color.black (ignored by Load)",
        "depth_slice": 0,
        "builder_overload_method_index": 283474,
    }
    assert attachment_route["depth"]["source"] == "PassInput.sceneDepth"
    assert attachment_route["depth"]["access"] == "Read"
    assert attachment_route["depth"]["access_value"] == 1
    assert attachment_route["depth"]["builder_overload_method_index"] == 283475
    prepare_method = next(
        method
        for method in constructor_map["bodyTargets"]
        if method["method"] == "PrepareDeferredLightingPass"
    )
    color_call = next(
        call
        for call in prepare_method["directCalls"]
        if any(
            resolved["methodIndex"] == 283474
            for resolved in call.get("resolved", [])
        )
    )
    assert color_call["argumentContext"]["argRegisterWrites"]["r9"]["write"]["value"] == "0"
    depth_call = next(
        call
        for call in prepare_method["directCalls"]
        if any(
            resolved["methodIndex"] == 283475
            for resolved in call.get("resolved", [])
        )
    )
    assert depth_call["argumentContext"]["argRegisterWrites"]["r9"]["write"]["value"] == "0x1"
    material = json.loads(
        (SOURCE_ROOT / recovery["selected_hgbuffer"]["material"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    material_floats = {
        row["Key"]: row["Value"]
        for row in material["m_SavedProperties"]["m_Floats"]
    }
    stencil = route["sphere_stencil_contract"]
    assert material_floats["_StencilRef"] == stencil["hgbuffer_material_stencil_ref"]
    assert material_floats["_StencilOpGBuffer"] == stencil["hgbuffer_material_stencil_op_value"]
    assert list(stencil["resolver_pass_refs"].values()) == [0, 1, 2]
    assert stencil["write_alpha_ref"] == 0
    full_screen_calls = [
        call
        for method in payload["bodyTargets"]
        if method["type"].endswith("DeferredLightingPass")
        and method["method"] == "DrawDeferredLighting"
        for call in method["directCalls"]
        if any(resolved["method"] == "DrawFullScreen" for resolved in call.get("resolved", []))
    ]
    pass_args = {
        call["argumentContext"]["argRegisterWrites"]["r9"]["write"]["value"]
        for call in full_screen_calls
    }
    assert {"0", "0x1", "0x2"}.issubset(pass_args)

    assembly_path = Path(native["game_assembly"]["path_at_recovery"])
    if assembly_path.is_file():
        assert assembly_path.stat().st_size == native["game_assembly"]["size"]
        require_hash(assembly_path, native["game_assembly"]["sha256"])


def verify_fail_closed(recovery: dict[str, object]) -> None:
    assert recovery["runtime_ready"] is False
    assert recovery["activation_policy"] == "default-off-fail-closed"
    unresolved = recovery["unresolved_exact_contract"]
    assert len(unresolved) == 5
    assert not any(
        "missing-variant fallback" in blocker or
        "exact executed deferred-resolver D3D11 pass-0 program pair" in blocker
        for blocker in unresolved
    )
    assert any("settled contents" in blocker for blocker in unresolved)

    manifest = json.loads((SOURCE_ROOT / "source_manifest.json").read_text())
    assert manifest["complete"] is False
    outside = manifest["selected_shader_variants"][-1]
    assert outside["shader"] == "HGRP/Lit"
    assert "runtime_deferred_contract_missing" in outside["status"]

    runtime = ASSET_ROOT / "Runtime" / "Rendering" / (
        "EndfieldRecoveredCharInfoPresentation.cs"
    )
    builder = ASSET_ROOT / "Editor" / "CharacterRecovery" / (
        "EndfieldRecoveredCharInfoPresentationBuilder.cs"
    )
    unavailable = ASSET_ROOT / "Shaders" / "Recovered" / (
        "EndfieldCharInfoHGRPLitUnavailable.shader"
    )
    diagnostic = ASSET_ROOT / "Editor" / "CharacterRecovery" / (
        "EndfieldSphereOutsideHGBufferBatchVerifier.cs"
    )
    diagnostic_wrapper = LAB_ROOT / "verify_sphereoutside_hgbuffer_diagnostic.bat"
    require_tokens(
        runtime,
        [
            "public bool exactSourceAssetsReady;",
            "if (!exactSourceAssetsReady)",
            "sourceContent.SetActive(false);",
        ],
    )
    require_tokens(
        builder,
        [
            "controller.enableRecoveredPresentation = false;",
            "controller.exactSourceAssetsReady = manifest.complete &&",
            'Shader.Find("Endfield/Recovered/CharInfo/HGRPLit") != null',
            "content.SetActive(false);",
            "BuildSphereOutsideHGBufferDiagnosticAssets()",
            '"_PorosityFactorX"',
            '"_PorosityFactorY"',
            '"_PorosityFactorZ"',
        ],
    )
    require_tokens(
        unavailable,
        [
            'Shader "Hidden/Endfield/Recovered/CharInfo/HGRPLitUnavailable"',
            "ZWrite Off",
            "ColorMask 0",
            'Name "RecoveredSphereOutsideHGBufferDiagnostic"',
            "ZTest Always",
            "float4 sceneColor : SV_Target0;",
            "float4 gBufferC : SV_Target4;",
            "_PorosityFactorY * roughness",
        ],
    )
    require_tokens(
        diagnostic,
        [
            "ENDFIELD_RECOVERED_SPHERE_OUTSIDE_HGBUFFER",
            "GraphicsFormat.R16G16B16A16_SFloat",
            "GraphicsFormat.A2B10G10R10_UNormPack32",
            "GraphicsFormat.R8G8B8A8_SRGB",
            "GraphicsFormat.D32_SFloat_S8_UInt",
            "Graphics.SetRenderTarget(colors, depthStencil.depthBuffer);",
            "AsyncGPUReadback.Request(texture, 0)",
            "diagnosticOnly = true",
            "defaultOff = true",
        ],
    )
    require_tokens(
        diagnostic_wrapper,
        [
            "EndfieldSphereOutsideHGBufferBatchVerifier.Verify",
            "ENDFIELD_RECOVERED_SPHERE_OUTSIDE_HGBUFFER=1",
            "-force-d3d12",
        ],
    )


def verify_selected_resolver_binding_contract() -> None:
    contract = json.loads(BINDING_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert contract["schema"] == (
        "endfield.charinfo.sphereoutside.deferred-binding-contract.v1"
    )
    assert contract["runtime_ready"] is False
    assert contract["activation_policy"] == "default-off-fail-closed"
    identifier_evidence = contract["installed_texture_identifier_evidence"]
    require_hash(
        LAB_ROOT / identifier_evidence["path"],
        identifier_evidence["sha256"],
    )
    assert identifier_evidence["identifier_count"] == 16
    installed_metadata = Path(identifier_evidence["source"]["path"])
    assert (
        installed_metadata.stat().st_size
        == identifier_evidence["source"]["size"]
    )
    require_hash(
        installed_metadata,
        identifier_evidence["source"]["sha256"],
    )
    light_binning = contract["light_binning_runtime"]
    assert light_binning["status"].startswith("binary-source-closed")
    for path_key, hash_key in (
        ("audit_path", "audit_sha256"),
        ("auditor_path", "auditor_sha256"),
        ("extractor_path", "extractor_sha256"),
        ("program_manifest_path", "program_manifest_sha256"),
    ):
        require_hash(LAB_ROOT / light_binning[path_key], light_binning[hash_key])
    light_binning_audit = json.loads(
        (LAB_ROOT / light_binning["audit_path"]).read_text(encoding="utf-8")
    )
    verify_light_binning_contract(
        light_binning,
        light_binning_audit,
        BINDING_CONTRACT_PATH,
    )
    light_runtime = light_binning["runtime_port"]
    require_hash(
        LAB_ROOT / light_runtime["compute_path"],
        light_runtime["compute_sha256"],
    )
    require_hash(
        LAB_ROOT / light_runtime["owner_path"],
        light_runtime["owner_sha256"],
    )
    require_tokens(
        LAB_ROOT / light_runtime["compute_path"],
        [
            "#pragma kernel BuildXY",
            "#pragma kernel BuildZ",
            "RWStructuredBuffer<uint> _EndfieldRecoveredLightBinningBuffer;",
            "(dispatchThreadID.y * (uint)_NumTilesX + dispatchThreadID.x) * 8u;",
            "(uint)_EndfieldRecoveredLightBinningZOffset + dispatchThreadID.x * 8u;",
        ],
    )
    require_tokens(
        LAB_ROOT / light_runtime["owner_path"],
        [
            "internal sealed class EndfieldRecoveredLightBinning",
            "private const int WordsPerBin = 8;",
            "int tileCountX = (width + TileSize - 1) / TileSize;",
            "(tileCountX + 7) / 8,",
            "(SliceCount + 63) / 64,",
            "ENDFIELD_RECOVERED_CANONICAL_BINNING_BUFFER",
            "_EndfieldRecoveredCanonicalBinningReady",
            "ComputeBufferType.Raw",
            "PublishCanonicalBinning(",
        ],
    )
    canonical_transport = light_binning["canonical_combined_transport"]
    assert canonical_transport["published_by_default"] is False
    assert canonical_transport["environment_selector"] == (
        "ENDFIELD_RECOVERED_CANONICAL_BINNING_BUFFER=1"
    )
    assert canonical_transport["command_line_selector"] == (
        "-endfield-recovered-canonical-binning-buffer"
    )
    assert canonical_transport["ready_property"] == (
        "_EndfieldRecoveredCanonicalBinningReady"
    )
    for path_key, hash_key in (
        ("layout_contract_path", "layout_contract_sha256"),
        ("compute_path", "compute_sha256"),
        ("verifier_path", "verifier_sha256"),
        ("wrapper_path", "wrapper_sha256"),
    ):
        require_hash(
            LAB_ROOT / canonical_transport[path_key],
            canonical_transport[hash_key],
        )
    require_tokens(
        LAB_ROOT / canonical_transport["layout_contract_path"],
        [
            "public const int MaxTileX = 256;",
            "public const int MaxTileY = 128;",
            "public const int LightSliceCount = 2048;",
            "public const int ReflectionSliceCount = 1024;",
            "int totalWordCount = checked(",
        ],
    )
    require_tokens(
        LAB_ROOT / canonical_transport["compute_path"],
        [
            "#pragma kernel BuildCanonicalCombined",
            "#pragma kernel ReadCanonicalGlobal",
            "RWByteAddressBuffer _EndfieldRecoveredCanonicalBinningBuffer;",
            "ByteAddressBuffer _BinningBuffer;",
            "_EndfieldRecoveredCanonicalBinningBuffer.Store(wordIndex * 4u, value);",
            "_BinningBuffer.Load(wordIndex * 4u);",
        ],
    )
    for api, evidence in canonical_transport["gpu_reports"].items():
        report_path = LAB_ROOT / evidence["path"]
        require_hash(report_path, evidence["sha256"])
        report = json.loads(report_path.read_text(encoding="utf-8"))
        verify_canonical_binning_gpu_report(
            canonical_transport,
            report,
            api,
            light_binning["audit_sha256"],
            BINDING_CONTRACT_PATH,
        )
        require_unity_log(
            LAB_ROOT / evidence["log_path"],
            evidence["log_sha256"],
            [
                "Recovered canonical _BinningBuffer validation passed:",
                "raw global readback exact",
                "fail-closed gates=3/3",
                f"api={api}",
                "Exiting batchmode successfully now!",
            ],
        )
    reflection_frame = canonical_transport["same_frame_reflection_resources"]
    assert reflection_frame["reflection_ready_property"] == (
        "_EndfieldRecoveredReflectionProbeFallbackReady"
    )
    for path_key, hash_key in (
        ("runtime_pipeline_path", "runtime_pipeline_sha256"),
        ("reflection_owner_path", "reflection_owner_sha256"),
        ("lighting_volume_path", "lighting_volume_sha256"),
        ("presentation_controller_path", "presentation_controller_sha256"),
        ("scene_setup_path", "scene_setup_sha256"),
        ("cubemap_importer_path", "cubemap_importer_sha256"),
        ("probe_path", "probe_sha256"),
        ("verifier_path", "verifier_sha256"),
        ("wrapper_path", "wrapper_sha256"),
    ):
        require_hash(
            LAB_ROOT / reflection_frame[path_key],
            reflection_frame[hash_key],
        )
    require_tokens(
        LAB_ROOT / reflection_frame["runtime_pipeline_path"],
        [
            "recoveredReflectionProbeFallback.ResetPublication(commandBuffer);",
            "bool recoveredCanonicalBinningReady =",
            ".PrepareAndPublishRecoveredResources(",
            "recoveredLightBinning.DisableCanonicalPublication(",
            "Recovered canonical CharInfo binning + reflection",
        ],
    )
    require_tokens(
        LAB_ROOT / reflection_frame["reflection_owner_path"],
        [
            "public sealed class EndfieldRecoveredReflectionProbeFallback",
            'Shader.PropertyToID("_EndfieldRecoveredReflectionProbeFallbackReady")',
            "public bool PrepareAndPublishRecoveredResources(",
            'source.name,\n                    "T_hdri_env_char_01"',
            "if (publishLegacyZeroBinningBuffer)",
            "commandBuffer.SetGlobalFloat(ReadyId, 1.0f);",
            "internal void ResetPublication(CommandBuffer commandBuffer)",
        ],
    )
    require_tokens(
        LAB_ROOT / reflection_frame["lighting_volume_path"],
        ["public Cubemap environmentReflectionCubemap;"],
    )
    require_tokens(
        LAB_ROOT / reflection_frame["presentation_controller_path"],
        [
            "Cubemap environmentReflectionCubemap =",
            "characterLighting.environmentReflectionCubemap =",
        ],
    )
    require_tokens(
        LAB_ROOT / reflection_frame["scene_setup_path"],
        [
            "volume.environmentReflectionCubemap =",
            "LoadRecoveredEnvironmentReflectionCubemap()",
        ],
    )
    require_tokens(
        LAB_ROOT / reflection_frame["cubemap_importer_path"],
        [
            "BindEnvironmentReflectionIntoGeneratedScenes(imported);",
            "volume.environmentReflectionCubemap = cubemap;",
        ],
    )
    require_tokens(
        LAB_ROOT / reflection_frame["probe_path"],
        [
            "ByteAddressBuffer _BinningBuffer;",
            "Texture2DArray<float4> _ReflectionProbeOctTextureArray;",
            "_EndfieldRecoveredCanonicalBinningReady",
            "_EndfieldRecoveredReflectionProbeFallbackReady",
            "_BinningBuffer.Load(90847u * 4u);",
        ],
    )
    assert reflection_frame["selector_on_off_pixel_oracle"] == {
        "png_sha256": (
            "59902c424de630a496364d57e404a5a72"
            "bcbcc42712bf7ef6935900d7500cac3"
        ),
        "pixel_identical": True,
    }
    for api, evidence in reflection_frame["gpu_reports"].items():
        report_path = LAB_ROOT / evidence["path"]
        require_hash(report_path, evidence["sha256"])
        report = json.loads(report_path.read_text(encoding="utf-8"))
        verify_canonical_reflection_frame_gpu_report(
            reflection_frame,
            report,
            api,
            BINDING_CONTRACT_PATH,
        )
        require_unity_log(
            LAB_ROOT / evidence["log_path"],
            evidence["log_sha256"],
            [
                "Recovered canonical reflection frame validation passed:",
                "canonical sentinels preserved",
                "source gates=2/2",
                f"api={api}",
                "Exiting batchmode successfully now!",
            ],
        )
    reflection_runtime = contract["reflection_probe_runtime"]
    assert reflection_runtime["status"].startswith("binary-source-closed")
    assert reflection_runtime["published"] is False
    assert reflection_runtime["pass0_consumer_enabled"] is False
    assert (
        reflection_runtime["source_cubemap"],
        reflection_runtime["source_cubemap_path_id"],
    ) == ("T_hdri_env_char_01", 2404688955498524548)
    require_hash(
        LAB_ROOT / reflection_runtime["runtime_producer_path"],
        reflection_runtime["runtime_producer_sha256"],
    )
    runtime_producer_source = (
        LAB_ROOT / reflection_runtime["runtime_producer_path"]
    ).read_text(encoding="utf-8")
    for token in (
        "public sealed class EndfieldRecoveredReflectionProbeFallback",
        "private const int TileSize = 32;",
        "private const int LightSliceCount = 2048;",
        "private const int LightWordsPerBin = 8;",
        "private const int ReflectionSliceCount = 1024;",
        "private const int ReflectionWordsPerBin = 1;",
        "private const int OctPhysicalSize =",
        "private const int GlobalBufferBytes = 4160;",
        "public bool PrepareAndPublishRecoveredResources(",
        "if (publishLegacyZeroBinningBuffer)",
        "internal void ResetPublication(CommandBuffer commandBuffer)",
        "float tileHeightAtNear = nearHeight * TileSize / tileY;",
        "ComputeBufferType.Constant",
        "commandBuffer.SetGlobalConstantBuffer(",
        "commandBuffer.SetGlobalBuffer(",
    ):
        assert token in runtime_producer_source
    camera_binning = reflection_runtime["camera_binning"]
    assert camera_binning["tileSize"] == 32
    assert camera_binning["light"] == {
        "sliceZ": 2048,
        "uintCountPerBin": 8,
        "punctualLightsMax": 32,
        "maskUnitDivisor": 4,
    }
    assert camera_binning["reflection"] == {
        "sliceZ": 1024,
        "uintCountPerBin": 1,
        "tileX": "ceil(renderTargetWidth / 32)",
        "tileY": "ceil(renderTargetHeight / 32)",
        "xyOffset": "(tileX * tileY + 2048) * 8",
        "zOffset": (
            "(tileX * tileY + 2048) * 8 + tileX * tileY"
        ),
        "uintCount": "tileX * tileY + 1024",
    }
    assert camera_binning["shaderVariablesGlobalBinningBufferOffsets"] == [
        "light.xyOffset",
        "light.zOffset",
        "reflection.xyOffset",
        "reflection.zOffset",
    ]
    oct_runtime = reflection_runtime["oct_texture_array"]
    assert (
        oct_runtime["format"],
        oct_runtime["width"],
        oct_runtime["height"],
        oct_runtime["slices"],
        oct_runtime["physical_mip_count"],
        oct_runtime["populated_mips"],
        oct_runtime["destination_slice"],
    ) == (
        "R16G16B16A16_SFloat",
        576,
        576,
        32,
        10,
        list(range(8)),
        0,
    )
    assert oct_runtime["gpu_repeat_byte_identical"] is True
    assert oct_runtime["slice0_mip_sha256"] == {
        "0": "51a9f6e8c9cac7cb3b57c2b1f00341ca579f86220c8c6345a819264370d84b68",
        "1": "eba655a4eca3a7e3fa4fab402b914c0a7b42f7877cfe47b46091b0664c9f74dc",
        "2": "2d80cf7c62e528dbccb7fa435af93d58cdd8c938f6a27c78b55f486fc9df51b9",
        "3": "3fa3a63ceae7a23e8f2fdd3d9ef7a4b399016044ecee3de39ab76706b9b8579f",
        "4": "fdbbc8070238c7857417d9f64ab46ab366f4035f3c4fdab2192d7e52913026e5",
        "5": "28e10eea295b226b2d53046dde9c8558d1b53c426863cb87c0c43dfb76d61b24",
        "6": "8957d831c59c97cd1c1c0063df0ed0450d2e0266935598e2740f1888d28574e4",
        "7": "b91f9dca3b9afe7683efe9952ec00845c30a64d57c3d0ae9f80c9c0adfb04ba8",
    }
    for path_key, hash_key in (
        ("diagnostic_report_path", "diagnostic_report_sha256"),
        ("compute_path", "compute_sha256"),
        ("verifier_path", "verifier_sha256"),
    ):
        require_hash(LAB_ROOT / oct_runtime[path_key], oct_runtime[hash_key])
    oct_report = json.loads(
        (LAB_ROOT / oct_runtime["diagnostic_report_path"]).read_text(
            encoding="utf-8"
        )
    )
    assert oct_report["valid"] is True
    assert oct_report["diagnosticOnly"] is True
    assert oct_report["publishedAsReflectionProbeOctTextureArray"] is False
    assert oct_report["pass0ConsumerEnabled"] is False

    reflection_global = reflection_runtime["global_buffer"]
    assert (
        reflection_global["byte_size"],
        reflection_global["header_bytes"],
        reflection_global["reserved_global_record_bytes"],
        reflection_global["local_record_start"],
        reflection_global["local_record_stride"],
        reflection_global["local_record_count"],
        reflection_global["no_local_probe_slice"],
    ) == (4160, 64, 128, 192, 128, 31, 0)
    assert reflection_global["charinfo_param3"] == [
        -0.0075507620349526405,
        0.01217081118375063,
        0.47223734855651855,
        1.0963057279586792,
    ]
    assert reflection_global["gameassembly_va"] == "0x189d10660"
    assert reflection_global["unityplayer_icall_index"] == 423
    assert (
        reflection_global["unityplayer_implementation_va"] == "0x18108a090"
    )
    for path_key, hash_key in (
        ("audit_path", "audit_sha256"),
        ("auditor_path", "auditor_sha256"),
    ):
        require_hash(
            LAB_ROOT / reflection_global[path_key],
            reflection_global[hash_key],
        )
    global_report = json.loads(
        (LAB_ROOT / reflection_global["audit_path"]).read_text(
            encoding="utf-8"
        )
    )
    assert global_report["valid"] is True
    assert (
        global_report["nativeProducer"]["globalBufferLayout"]["byteSize"]
        == 4160
    )
    assert (
        global_report["noLocalProbeFallback"]["serializedCharInfoParam3"]
        == reflection_global["charinfo_param3"]
    )

    disabled_resources = contract["disabled_feature_resource_bindings"]
    assert disabled_resources["published"] is False
    assert disabled_resources["status"].startswith("binary-source-closed")
    for path_key, hash_key in (
        ("audit_path", "audit_sha256"),
        ("auditor_path", "auditor_sha256"),
    ):
        require_hash(
            LAB_ROOT / disabled_resources[path_key],
            disabled_resources[hash_key],
        )
    disabled_report = json.loads(
        (LAB_ROOT / disabled_resources["audit_path"]).read_text(
            encoding="utf-8"
        )
    )
    assert disabled_report["valid"] is True
    wetness_resource = disabled_resources["water_wetness_mask"]
    fog_resource = disabled_resources["integrated_light_scattering"]
    assert wetness_resource == disabled_report["disabledFeatureBindings"][
        "waterWetnessMask"
    ]
    assert fog_resource == disabled_report["disabledFeatureBindings"][
        "integratedLightScattering"
    ]
    assert wetness_resource["invalidHandleFallback"] == (
        "UnityEngine.Texture2D.whiteTexture"
    )
    assert wetness_resource["propertyIdStaticOffset"] == 0xBB8
    assert fog_resource["disabledFallback"] == (
        "HG.Rendering.Runtime.HGVolumetricFogUtils."
        "volumetricBlackTexture3D"
    )
    assert fog_resource["propertyIdStaticOffset"] == 0x440
    fog_texture = fog_resource["fallbackTexture"]
    assert (
        fog_texture["dimension"],
        fog_texture["width"],
        fog_texture["height"],
        fog_texture["depth"],
        fog_texture["textureFormatNumeric"],
        fog_texture["textureFormatUnity2022_3_62f3"],
        fog_texture["mipChain"],
        fog_texture["createUninitialized"],
    ) == ("Texture3D", 1, 1, 1, 48, "ASTC_4x4", False, False)
    assert fog_texture["pixel"] == [0.0, 0.0, 0.0, 1.0]
    assert fog_texture["setPixelCoordinates"] == [0, 0, 0]
    assert fog_texture["applyUpdateMipmaps"] is False
    assert fog_texture["applyMakeNoLongerReadable"] is True
    unity_enum_evidence = fog_texture["unityEnumEvidence"]
    assert unity_enum_evidence["enum"] == "UnityEngine.TextureFormat"
    assert (
        unity_enum_evidence["numericValue"],
        unity_enum_evidence["name"],
    ) == (48, "ASTC_4x4")
    require_hash(
        Path(unity_enum_evidence["assembly"]),
        unity_enum_evidence["assemblySha256"],
    )

    visibility_resource = contract["visibility_sh_resource_binding"]
    assert visibility_resource["published_by_lab"] is True
    assert visibility_resource["published_by_default"] is False
    assert "source-closed" in visibility_resource["status"]
    visibility_constants = visibility_resource["constants_transport"]
    assert visibility_constants["published_by_default"] is False
    assert visibility_constants["canonical_frame_ready_property"] == (
        "_EndfieldRecoveredVisibilitySHConstDataReady"
    )
    for path_key, hash_key in (
        ("audit_path", "audit_sha256"),
        ("auditor_path", "auditor_sha256"),
        ("contract_path", "contract_sha256"),
        ("owner_path", "owner_sha256"),
        ("pipeline_path", "pipeline_sha256"),
        ("probe_path", "probe_sha256"),
        ("verifier_path", "verifier_sha256"),
        ("wrapper_path", "wrapper_sha256"),
    ):
        require_hash(
            LAB_ROOT / visibility_constants[path_key],
            visibility_constants[hash_key],
        )
    visibility_constants_audit = json.loads(
        (LAB_ROOT / visibility_constants["audit_path"]).read_text(
            encoding="utf-8"
        )
    )
    verify_visibility_sh_constants_audit(
        visibility_constants,
        visibility_constants_audit,
        BINDING_CONTRACT_PATH,
    )
    require_tokens(
        LAB_ROOT / visibility_constants["contract_path"],
        [
            "public const int SizeBytes = 128;",
            "public const int SelectedReadFirstVector = 2;",
            "0x3EA16095u",
            "0x3E5B57C6u",
            "1.0f / outputWidth",
            "native 0x80-byte zero-fill",
        ],
    )
    require_tokens(
        LAB_ROOT / visibility_constants["owner_path"],
        [
            'Shader.PropertyToID("VisibilitySHConstData")',
            'Shader.PropertyToID("_EndfieldRecoveredVisibilitySHConstDataReady")',
            "public bool PrepareAndPublish(",
            "commandBuffer.SetGlobalConstantBuffer(",
            "commandBuffer.SetGlobalFloat(ReadyId, 1.0f);",
        ],
    )
    require_tokens(
        LAB_ROOT / visibility_constants["pipeline_path"],
        [
            "recoveredVisibilitySHConstants.ResetPublication(commandBuffer);",
            "recoveredVisibilitySHConstants.PrepareAndPublish(",
            "recoveredReflectionProbeFallback.ResetPublication(",
            "exact VisibilitySHConstData",
        ],
    )
    require_tokens(
        LAB_ROOT / visibility_constants["probe_path"],
        [
            "cbuffer VisibilitySHConstData",
            "_EndfieldRecoveredVisibilitySHConstDataReady",
            "_EndfieldRecoveredVisibilitySHConstantsReadback",
        ],
    )
    for api, evidence in visibility_constants["gpu_reports"].items():
        report_path = LAB_ROOT / evidence["path"]
        require_hash(report_path, evidence["sha256"])
        report = json.loads(report_path.read_text(encoding="utf-8"))
        verify_visibility_sh_constants_gpu_report(
            visibility_constants,
            report,
            api,
            BINDING_CONTRACT_PATH,
        )
        require_unity_log(
            LAB_ROOT / evidence["log_path"],
            evidence["log_sha256"],
            [
                "Recovered VisibilitySHConstData validation passed:",
                "all 32 native words exact",
                "selected words=8/8",
                "fail-closed gates=3/3",
                f"api={api}",
                "Exiting batchmode successfully now!",
            ],
        )
    actual_scene = visibility_constants["actual_scene_oracle"]
    require_hash(LAB_ROOT / actual_scene["png_path"], actual_scene["png_sha256"])
    require_unity_log(
        LAB_ROOT / actual_scene["log_path"],
        actual_scene["log_sha256"],
        [
            "Recovered canonical _BinningBuffer active",
            "exact VisibilitySHConstData frame resources are active",
            "Exiting batchmode successfully now!",
        ],
    )
    visibility_frame = visibility_resource["canonical_frame_transport"]
    assert visibility_frame["published_by_default"] is False
    assert visibility_frame["pass0_consumer_enabled"] is False
    assert visibility_frame["required_same_frame_resources"] == [
        "_BinningBuffer",
        "_ReflectionProbeOctTextureArray",
        "ReflectionProbeGlobalData",
        "VisibilitySHConstData",
    ]
    for path_key, hash_key in (
        ("producer_path", "producer_sha256"),
        ("pipeline_path", "pipeline_sha256"),
        ("shader_path", "shader_sha256"),
        ("payload_path", "payload_sha256"),
        ("native_audit_path", "native_audit_sha256"),
        ("validator_path", "validator_sha256"),
        ("validator_test_path", "validator_test_sha256"),
        ("wrapper_path", "wrapper_sha256"),
    ):
        require_hash(
            LAB_ROOT / visibility_frame[path_key],
            visibility_frame[hash_key],
        )
    require_tokens(
        LAB_ROOT / visibility_frame["producer_path"],
        [
            "bool canonicalFrameResourcesReady)",
            "CanonicalOutputId,",
            "canonicalFrameResourcesReady",
            "? (Texture)resources.color",
            ": Texture2D.blackTexture",
            '"canonicalPublication="',
        ],
    )
    require_tokens(
        LAB_ROOT / visibility_frame["pipeline_path"],
        [
            "bool recoveredCanonicalFrameResourcesReady = false;",
            "recoveredCanonicalFrameResourcesReady = true;",
            "recoveredVisibilitySHProducer.Render(",
            "recoveredCanonicalFrameResourcesReady);",
        ],
    )
    for api, evidence in visibility_frame["gpu_reports"].items():
        report_path = LAB_ROOT / evidence["path"]
        require_hash(report_path, evidence["sha256"])
        report = json.loads(report_path.read_text(encoding="utf-8"))
        verify_visibility_sh_frame_report(
            visibility_frame,
            report,
            api,
            "ready",
            BINDING_CONTRACT_PATH,
        )
        require_hash(LAB_ROOT / evidence["beauty_path"], evidence["beauty_sha256"])
        require_unity_log(
            LAB_ROOT / evidence["log_path"],
            evidence["log_sha256"],
            [
                "exact VisibilitySHConstData frame resources are active",
                "Recovered VisibilitySH CPU capsule fixture: actor=Wulfa, count=10",
                "canonicalPublication=ready",
                "nonzeroPixels=20006",
                visibility_frame["fixture"]["rgba_half_sha256"],
                "Exiting batchmode successfully now!",
            ],
        )
    fail_closed = visibility_frame["fail_closed_report"]
    fail_report_path = LAB_ROOT / fail_closed["path"]
    require_hash(fail_report_path, fail_closed["sha256"])
    fail_report = json.loads(fail_report_path.read_text(encoding="utf-8"))
    verify_visibility_sh_frame_report(
        visibility_frame,
        fail_report,
        "d3d12",
        "fail-closed",
        BINDING_CONTRACT_PATH,
    )
    fail_log_path = LAB_ROOT / fail_closed["log_path"]
    require_unity_log(
        fail_log_path,
        fail_closed["log_sha256"],
        [
            "Recovered VisibilitySH CPU capsule fixture: actor=Wulfa, count=10",
            "canonicalPublication=fail-closed",
            "nonzeroPixels=20006",
            visibility_frame["fixture"]["rgba_half_sha256"],
            "Exiting batchmode successfully now!",
        ],
    )
    if "exact VisibilitySHConstData frame resources are active" in (
        fail_log_path.read_text(encoding="utf-8", errors="replace")
    ):
        raise AssertionError(
            "VisibilitySH frame validator failed: "
            "check=fail_closed_upstream_absent; "
            f"source={fail_log_path}; expected=False; actual=True"
        )
    require_hash(
        LAB_ROOT / visibility_resource["audit_path"],
        visibility_resource["audit_sha256"],
    )
    visibility_report = disabled_report["visibilitySHBinding"]
    assert visibility_resource["properties"] == visibility_report["properties"]
    assert (
        visibility_resource["properties"]["logSHLut"]["property"],
        visibility_resource["properties"]["abLut"]["property"],
        visibility_resource["properties"]["visibilitySH"]["property"],
    ) == ("_LogSHLutTex", "_ABLutTex", "_VisibilitySHRT")
    visibility_target = visibility_resource["active_render_target"]
    assert visibility_target == visibility_report["activeRenderTarget"]
    assert (
        visibility_target["colorFormatNumeric"],
        visibility_target["colorFormatUnity2022_3_62f3"],
        visibility_target["filterModeNumeric"],
        visibility_target["filterModeUnity2022_3_62f3"],
        visibility_target["wrapModeNumeric"],
        visibility_target["wrapModeUnity2022_3_62f3"],
        visibility_target["enableRandomWrite"],
        visibility_target["useMipMap"],
    ) == (
        48,
        "R16G16B16A16_SFloat",
        1,
        "Bilinear",
        1,
        "Clamp",
        False,
        False,
    )
    visibility_fallback = visibility_resource[
        "empty_or_disabled_fallback"
    ]
    assert visibility_fallback == visibility_report[
        "emptyOrDisabledFallback"
    ]
    assert visibility_fallback["texture"] == (
        "UnityEngine.Texture2D.blackTexture"
    )
    assert visibility_fallback["publishedByEmptyRenderFunction"] is True
    assert len(visibility_fallback["constructorBranches"]) == 2
    for path_key, hash_key in (
        ("lut_manifest_path", "lut_manifest_sha256"),
        ("lut_auditor_path", "lut_auditor_sha256"),
    ):
        require_hash(
            LAB_ROOT / visibility_resource[path_key],
            visibility_resource[hash_key],
        )
    visibility_lut_manifest = json.loads(
        (LAB_ROOT / visibility_resource["lut_manifest_path"]).read_text(
            encoding="utf-8"
        )
    )
    assert visibility_lut_manifest["schema"] == (
        "endfield.charinfo.visibility-luts.v1"
    )
    assert visibility_lut_manifest["valid"] is True
    assert visibility_resource["lut_runtime_resources"] == (
        visibility_lut_manifest["runtimeResources"]
    )
    runtime_resources = visibility_resource["lut_runtime_resources"]
    assert runtime_resources["pathId"] == 5613980184714137857
    require_hash(
        Path(runtime_resources["path"]),
        runtime_resources["sha256"],
    )
    visibility_lut_descriptor = {
        "width": 256,
        "height": 1,
        "textureFormatNumeric": 4,
        "textureFormatUnity2022_3_62f3": "RGBA32",
        "mipCount": 1,
        "textureDimensionNumeric": 2,
        "textureDimensionUnity2022_3_62f3": "Tex2D",
        "filterModeNumeric": 1,
        "filterModeUnity2022_3_62f3": "Bilinear",
        "wrapModeNumeric": 1,
        "wrapModeUnity2022_3_62f3": "Clamp",
        "colorSpaceNumeric": 0,
        "colorSpaceUnity2022_3_62f3": "Gamma",
        "aniso": 1,
        "mipBias": 0.0,
    }
    expected_visibility_luts = {
        "VisibilityABLut": (
            2892350180982884757,
            "ca1a648d1a19434b41a9dbbe9f6ad0191c4c4e7f088341761725895748f33ed0",
        ),
        "VisibilitySHLut": (
            8323377478838034894,
            "3e5d7d50ed14ab927676cb638eebcedfb8e02766b8e0d01164105d519d925bf3",
        ),
    }
    assert visibility_resource["lookup_textures"] == (
        visibility_lut_manifest["textures"]
    )
    for name, (expected_path_id, expected_raw_sha) in (
        expected_visibility_luts.items()
    ):
        lut = visibility_resource["lookup_textures"][name]
        assert lut["pathId"] == expected_path_id
        assert lut["serializedDescriptor"] == visibility_lut_descriptor
        assert lut["rawRgba32"]["byteLength"] == 1024
        assert lut["rawRgba32"]["sha256"] == expected_raw_sha
        require_hash(
            LAB_ROOT / lut["rawRgba32"]["path"],
            lut["rawRgba32"]["sha256"],
        )
        require_hash(
            Path(lut["sourcePng"]["path"]),
            lut["sourcePng"]["sha256"],
        )
        require_hash(
            Path(lut["persistentPng"]["path"]),
            lut["persistentPng"]["sha256"],
        )
        require_hash(
            Path(lut["descriptorJson"]["path"]),
            lut["descriptorJson"]["sha256"],
        )

    for path_key, hash_key in (
        ("capsule_runtime_audit_path", "capsule_runtime_audit_sha256"),
        ("capsule_runtime_auditor_path", "capsule_runtime_auditor_sha256"),
    ):
        require_hash(
            LAB_ROOT / visibility_resource[path_key],
            visibility_resource[hash_key],
        )
    capsule_report = json.loads(
        (
            LAB_ROOT / visibility_resource["capsule_runtime_audit_path"]
        ).read_text(encoding="utf-8")
    )
    assert capsule_report["valid"] is True
    capsule_runtime = visibility_resource["capsule_runtime"]
    assert capsule_runtime["managed_activation"] == capsule_report[
        "managed_activation"
    ]
    assert capsule_runtime["actors"] == capsule_report["actors"]
    assert capsule_runtime["isolated_unity_pose_fixtures"] == capsule_report[
        "isolated_unity_pose_fixtures"
    ]
    assert capsule_runtime["native_manager"] == capsule_report[
        "native_manager"
    ]
    assert capsule_runtime["component_native_packing"] == capsule_report[
        "component_native_packing"
    ]
    assert capsule_runtime["producer_pass"] == capsule_report["producer_pass"]
    assert capsule_runtime["source_closed"] == capsule_report["source_closed"]
    assert capsule_runtime["still_open"] == capsule_report["still_open"]
    for source_path, source in capsule_report["sources"].items():
        path = Path(source_path)
        assert path.stat().st_size == source["size"]
        require_hash(path, source["sha256"])

    actors = capsule_runtime["actors"]
    assert [actor["label"] for actor in actors] == ["Wulfa", "Zhuang"]
    assert [actor["helper_path_id"] for actor in actors] == [
        2213601665269696176,
        -8130124107266882278,
    ]
    assert all(
        actor["serialized_enabled"] == 1
        and actor["authored_candidate_count"] == 10
        and actor["all_candidates_serialized_enabled"] is True
        and actor["interaction_only"] == 0
        for actor in actors
    )
    isolated_fixtures = capsule_runtime["isolated_unity_pose_fixtures"]
    assert isolated_fixtures["Wulfa"]["record_sha256"] == (
        "0e418fd299cfaa88e8de5ef0388bb532"
        "8e326c5afd0b4c69cf2cf47b4a440a08"
    )
    assert isolated_fixtures["Zhuangfy"]["record_sha256"] == (
        "1f72039bdd39a1ae073dd2629f0e1245"
        "145a852e78dd4114778204ddde654264"
    )
    assert all(
        fixture["repeat_exact"]
        and fixture["count"] == 10
        and fixture["stride"] == 48
        and fixture["order"] == list(range(10))
        and len(fixture["records"]) == 10
        for fixture in isolated_fixtures.values()
    )
    native_manager = capsule_runtime["native_manager"]
    assert (
        native_manager["max_render_capsules"],
        native_manager["internal_record_stride"],
        native_manager["output_record_stride"],
    ) == (128, 52, 48)
    assert native_manager["output_record"] == [
        {"name": "pa", "offset": 0, "size": 16},
        {"name": "pb", "offset": 16, "size": 16},
        {"name": "dir", "offset": 32, "size": 16},
    ]
    component_packing = capsule_runtime["component_native_packing"]
    assert component_packing["internal_record_writes"] == {
        "valid": 1,
        "pa": 4,
        "pb": 20,
        "dir": 36,
        "stride": 52,
    }
    assert component_packing["constants"] == {
        "degrees_to_radians": 0.01745329238474369,
        "half": 0.5,
        "culling_range": 5.0,
        "intensity_min": 0.009999999776482582,
        "intensity_max": 2.0,
    }
    assert component_packing["culling_bounds"] == {
        "native_aabb_test_va": "0x180411410",
        "center": "world_center",
        "extent": (
            "float3(0.5 * full_height * 5.0); the same "
            "conservative extent is written on X, Y, and Z"
        ),
        "plane_test": (
            "center dot plane.xyz + plane.w <= "
            "dot(abs(plane.xyz), extent)"
        ),
        "ordering": (
            "manager query/chunk order is retained; records that fail "
            "the plane test are skipped without re-sorting survivors"
        ),
    }
    assert component_packing["record_formula"]["full_height"] == (
        "max(capsuleHeight, 2 * capsuleRadius)"
    )
    assert component_packing["record_formula"]["half_segment"] == (
        "0.5 * full_height - capsuleRadius"
    )
    assert component_packing["record_formula"]["pa"].startswith(
        "float4(world_center - world_direction"
    )
    assert component_packing["record_formula"]["pb"].startswith(
        "float4(world_center + world_direction"
    )
    assert component_packing["record_formula"]["dir"].startswith(
        "float4(world_direction"
    )
    producer = capsule_runtime["producer_pass"]
    assert (
        producer["shader"],
        producer["path_id"],
        producer["selected_pass_index"],
        producer["draw_method"],
        producer["resources"]["capsule_capacity"],
        producer["resources"]["capsule_stride"],
        producer["resources"]["VisibilityCapsuleData_size"],
    ) == (
        "HGRP/VisibilitySH",
        -4362943401419010014,
        2,
        "CommandBuffer.HGDrawMeshInstanced",
        128,
        48,
        6160,
    )
    assert producer["render_state"] == {
        "blend": "One One, One One",
        "z_test": "Greater",
        "z_write": "Off",
        "cull": "Front",
        "stencil_ref": 4,
        "stencil_read_mask": 7,
        "stencil_compare": "NotEqual",
    }
    settings_lifecycle = producer["settings_lifecycle"]
    assert settings_lifecycle["prepare_method_va"] == "0x183948e30"
    assert settings_lifecycle["prepare_direct_call_sites"] == [
        "0x183947fd5"
    ]
    assert settings_lifecycle["constructor_direct_call_sites"] == [
        "0x183948e78"
    ]
    assert settings_lifecycle["pipeline_storage_offset"] == 0x160
    assert settings_lifecycle["setter_va"] == "0x186b8b288"
    assert settings_lifecycle["setter_direct_call_sites"] == []
    assert settings_lifecycle["visibility_feature_key_offset"] == 0x68
    assert settings_lifecycle["registered_callback_key_offsets"] == [
        0x60,
        0x70,
        0x00,
        0xC0,
        0xB8,
        0x20,
        0xF8,
        0x100,
    ]
    assert settings_lifecycle["visibility_callback_registered"] is False
    assert settings_lifecycle["ifix_patch_id_checked"] == 0x1D8
    assert settings_lifecycle["base_ifix_patch_block"] == {
        "name": "IFixPatchOut",
        "file_count": 0,
        "chunk_count": 0,
        "byte_count": 0,
    }
    assert settings_lifecycle["persistent_ifix_patch_overlay"] == {
        "name": "IFixPatchOut",
        "block_version": 23167343,
        "file_count": 1,
        "chunk_count": 1,
        "byte_count": 86926,
        "target_count": 32,
        "render_pipeline_settings_target_count": 0,
        "state_report": (
            "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/"
            "Generated/OriginalData/CharInfoPresentation/"
            "installed_ifix_patch_state.json"
        ),
    }
    assert producer["constructor_constants"]["g_star_params"] == [
        17.420700073242188,
        9.554789543151855,
        -17.420700073242188,
        -9.554789543151855,
    ]
    assert producer["constructor_constants"][
        "sphere_interval_scale_clamp"
    ] == [0.8, 2.0]
    assert producer["constructor_constants"]["sphere_range_scale_clamp"] == [
        0.01,
        5.0,
    ]

    irradiance_ownership = contract[
        "charinfo_irradiance_volume_ownership"
    ]
    assert irradiance_ownership["active_owner"] == "m_defaultIV"
    assert irradiance_ownership["active_manager"] == (
        "HG.Rendering.Runtime.HGIrradianceVolumeManagerV2"
    )
    assert irradiance_ownership["creates_gacha_override"] is False
    assert irradiance_ownership["calls_old_gacha_lifecycle"] is False
    assert irradiance_ownership[
        "api_symbol_owners_across_decoded_lua"
    ] == {
        "CreateGachaIV": [
            "Data/LuaScripts/LuaSystem/GachaSystem.lua"
        ],
        "UpdateGachaIV": [],
        "DestroyGachaIV": [
            "Data/LuaScripts/LuaSystem/GachaSystem.lua"
        ],
    }
    for path_key, hash_key in (
        ("audit_path", "audit_sha256"),
        ("auditor_path", "auditor_sha256"),
        ("v2_audit_path", "v2_audit_sha256"),
        ("v2_auditor_path", "v2_auditor_sha256"),
    ):
        require_hash(
            LAB_ROOT / irradiance_ownership[path_key],
            irradiance_ownership[hash_key],
        )
    ownership_report = json.loads(
        (LAB_ROOT / irradiance_ownership["audit_path"]).read_text(
            encoding="utf-8"
        )
    )
    assert ownership_report["result"][
        "charinfo_creates_gacha_irradiance_volume"
    ] is False
    assert ownership_report["result"][
        "charinfo_calls_old_gacha_iv_lifecycle"
    ] is False
    assert ownership_report["evidence"]["index"][
        "indexed_file_count"
    ] == 1291
    assert ownership_report["evidence"]["index"][
        "decoded_file_count"
    ] == 1290
    v2_report = json.loads(
        (LAB_ROOT / irradiance_ownership["v2_audit_path"]).read_text(
            encoding="utf-8"
        )
    )
    verify_charinfo_v2_data_path_contract(
        irradiance_ownership,
        v2_report,
        BINDING_CONTRACT_PATH,
    )
    assert v2_report["valid"] is True
    assert v2_report["livePath"]["manager"] == (
        "HG.Rendering.Runtime.HGIrradianceVolumeManagerV2"
    )
    assert v2_report["livePath"]["selection"]["behavior"] == (
        "V2 PipelineUpdate always passes m_defaultIV to the native renderer"
    )
    legacy_boundary = v2_report["livePath"]["legacyBoundary"]
    assert "separate older HGIrradianceVolumeManager" in legacy_boundary
    assert "m_gachaIV-or-m_defaultIV selector" in legacy_boundary
    assert (
        "independently calls HGIrradianceVolumeManagerV2.PipelineUpdateV2"
        in legacy_boundary
    )
    assert v2_report["activeClipmaps"]["resultOrder"] == [
        "clipmapTextureALod0",
        "clipmapTextureBLod0",
        "clipmapTextureALod1",
        "clipmapTextureBLod1",
        "clipmapTextureALod3",
        "clipmapTextureBLod3",
    ]
    assert [
        (row["dimensions"], row["graphicsFormatNumeric"])
        for row in v2_report["activeClipmaps"]["descriptors"]
    ] == [
        ([128, 64, 128], 74),
        ([128, 64, 384], 8),
        ([128, 64, 128], 74),
        ([128, 64, 384], 8),
        ([128, 64, 128], 74),
        ([128, 64, 384], 8),
    ]
    assert v2_report["activeClipmaps"]["missingObjectFallback"][
        "sameResourcePublishedToAllSixSlots"
    ] is True
    assert v2_report["shaderPublication"][
        "textureResultPayloadOffsets"
    ] == [0x40, 0x48, 0x50, 0x58, 0x60, 0x68]

    selected = contract["selected_original_program"]
    assert selected["pass_index"] == 0
    assert selected["pass_name"] == "Default Lit - Full Lighting"
    assert selected["program_payload"] == "fragment snippet 1"
    assert selected["keywords"] == [
        "HG_ENABLE_SCREEN_SPACE_SHADOW_MASK",
        "HG_USE_SUBPASS_INPUT_UNDER_ONE_PASS_DEFERRED",
    ]
    for path_key, hash_key in (
        ("spirv_path", "spirv_sha256"),
        ("source_metadata_path", "source_metadata_sha256"),
        ("enriched_metadata_path", "enriched_metadata_sha256"),
        ("decompiled_hlsl_path", "decompiled_hlsl_sha256"),
        ("dxbc_path", "dxbc_sha256"),
        ("dxbc_metadata_path", "dxbc_metadata_sha256"),
        ("decompiled_dxbc_hlsl_path", "decompiled_dxbc_hlsl_sha256"),
    ):
        require_hash(
            LAB_ROOT / selected[path_key],
            selected[hash_key],
        )
    installed_selection = selected["installed_d3d11_selection"]
    assert installed_selection["source_closed"] is True
    assert installed_selection["variant_pair_count"] == 64
    assert installed_selection["selected_serialized_order"] == 96
    assert installed_selection["selected_score"] == -15
    assert installed_selection["runner_up_score"] == -16
    assert installed_selection["unique_winner"] is True
    assert installed_selection["global_keywords"] == {
        "HG_ENABLE_SCREEN_SPACE_SHADOW_MASK": True,
        "HG_USE_SUBPASS_INPUT_UNDER_ONE_PASS_DEFERRED": False,
    }
    for path_key, hash_key in (
        ("keyword_state_audit_path", "keyword_state_audit_sha256"),
        ("fallback_program_audit_path", "fallback_program_audit_sha256"),
        ("isolated_execution_audit_path", "isolated_execution_audit_sha256"),
    ):
        require_hash(
            repo_path(installed_selection[path_key]),
            installed_selection[hash_key],
        )
    selected_pair = installed_selection["selected_pair"]
    require_hash(
        repo_path(selected_pair["vertex_path"]),
        selected_pair["vertex_sha256"],
    )
    require_hash(
        repo_path(selected_pair["fragment_path"]),
        selected_pair["fragment_sha256"],
    )
    assert selected_pair["fragment_sha256"] == selected["dxbc_sha256"]
    assert installed_selection["isolated_execution_scope"] == (
        "standalone_d3d11_isolated_diagnostic"
    )
    assert installed_selection["resource_binding_compatible"] is True
    assert installed_selection["numeric_render_fidelity_proven"] is False

    named = {
        row["name"]: (row["set"], row["binding"], row["size"])
        for row in contract["named_constant_buffers"]
    }
    assert named == {
        "_TransformVariables": (3, 30, 1312),
        "_LightDataBuffer": (3, 31, 32864),
        "VisibilitySHConstData": (3, 33, 128),
        "ShaderVariablesGlobal": (3, 35, 3200),
        "ReflectionProbeGlobalData": (3, 36, 4160),
    }
    visibility_named = next(
        row
        for row in contract["named_constant_buffers"]
        if row["name"] == "VisibilitySHConstData"
    )
    assert visibility_named["partial"] is False
    assert visibility_named["full_producer_closed"] is True
    assert visibility_named["selected_consumer_closed"] is True
    unnamed = {
        (row["set"], row["binding"])
        for row in contract["unnamed_constant_buffers"]
    }
    assert unnamed == {(3, 32), (3, 34), (3, 37), (3, 38)}
    identified = contract["identified_unnamed_constant_buffer_roles"]
    assert len(identified) == 4
    assert (
        identified[0]["role"],
        identified[0]["symbol"],
        identified[0]["set"],
        identified[0]["binding"],
        identified[0]["size"],
    ) == ("_LightBinningConstants", "_28_29", 3, 32, 48)
    assert identified[0]["status"].startswith("binary-role-identified")
    light_binning_native = identified[0]["native_producer"]
    require_hash(
        repo_path(light_binning_native["audit_path"]),
        light_binning_native["audit_sha256"],
    )
    assert light_binning_native["owner"] == "LightCulling+0x60"
    assert light_binning_native["upload_size_bytes"] == 48
    assert light_binning_native["light_cap"] == 32
    assert light_binning_native["layout"] == [
        "int lightCount@0",
        "int numTiles@4",
        "int actualWidth@8",
        "int actualHeight@12",
        "float tileSize@16",
        "float numTilesX@20",
        "float numTilesY@24",
        "float numSliceZ@28",
        "float nearClipPlane@32",
        "float farClipPlane@36",
        "float zBinSlice@40",
        "float invZBinSlice@44",
    ]
    # The authored-room subset was expanded by the refreshed source audit. Keep
    # this gate tied to the durable open boundary rather than a superseded
    # intermediate row count.
    assert "runtime/custom carry-in" in light_binning_native["remaining_boundary"]
    assert "final lightCount remain native live state" in (
        light_binning_native["remaining_boundary"]
    )
    light_cull_audit_path = repo_path(
        light_binning_native["light_cull_result_audit_path"]
    )
    require_hash(
        light_cull_audit_path,
        light_binning_native["light_cull_result_audit_sha256"],
    )
    light_cull_audit = json.loads(
        light_cull_audit_path.read_text(encoding="utf-8")
    )
    assert light_cull_audit["schema"] == (
        "endfield.gacha-light-cull-result-audit.v1"
    )
    assert light_cull_audit["verdict"] == "CAPTURE_REQUIRED"
    assert light_cull_audit["productionPatch"] is False
    for pin in light_cull_audit["sourcePins"].values():
        require_hash(repo_path(pin["path"]), pin["sha256"])
    assert light_cull_audit["nativeResult"]["fields"] == [
        "IntPtr visibleLightsPtr",
        "int visibleLightCount",
    ]
    cull_producer = light_cull_audit["producer"]
    assert cull_producer["method"] == (
        "UnityEngine.HyperGryph.HGCullingSystem.CullLights"
    )
    assert cull_producer["allDirectGameAssemblyCallersClosed"] is True
    assert cull_producer["directCallCount"] == 2
    assert cull_producer["onlyCaller"] == (
        "HG.Rendering.Runtime.HGCamera.DoECSCulling"
    )
    assert cull_producer["exactMaxCountAtBothSites"] == 256
    assert [row["offset"] for row in cull_producer["callSites"]] == [
        "0x63e",
        "0x7e4",
    ]
    assert all(row["maxCount"] == 256 for row in cull_producer["callSites"])
    assert light_cull_audit["consumer"]["method"] == (
        "HG.Rendering.Runtime.LightClusteringPassConstructor.SetupState"
    )
    assert "no process attachment or injection was performed" in (
        light_cull_audit["nextCaptureBoundary"]["safety"]
    )

    light_binning_transport = identified[0]["unity_transport"]
    assert light_binning_transport["activation_policy"] == (
        "default-off-fail-closed"
    )
    assert light_binning_transport["environment_variable"] == (
        "ENDFIELD_RECOVERED_LIGHT_BINNING_CONSTANTS"
    )
    assert light_binning_transport["command_line_argument"] == (
        "-endfield-recovered-light-binning-constants"
    )
    assert light_binning_transport["ready_property"] == (
        "_EndfieldRecoveredLightBinningConstantsReady"
    )
    for path_key, hash_key in (
        ("contract_path", "contract_sha256"),
        ("runtime_path", "runtime_sha256"),
        ("probe_path", "probe_sha256"),
        ("verifier_path", "verifier_sha256"),
    ):
        require_text_hash(
            repo_path(light_binning_transport[path_key]),
            light_binning_transport[hash_key],
        )

    light_binning_gpu = light_binning_transport["gpu_validation"]
    for api in ("d3d11", "d3d12"):
        report_path = repo_path(
            light_binning_gpu[f"{api}_report_path"]
        )
        require_hash(
            report_path,
            light_binning_gpu[f"{api}_report_sha256"],
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["schema"] == (
            "endfield-recovered-light-binning-constants-validation-v1"
        )
        assert report["valid"] is True
        assert report["graphicsApi"] == api
        assert report["canonicalBindingDefaultOff"] is True
        assert report["retailWholeSceneLightListClosed"] is False
        assert report["sourceAuditHashMatches"] is True
        assert report["managedSizeBytes"] == 48
        assert report["globalConstantBufferGpuReadbackMatches"] is True
        assert report["fixtureLightCount"] == 8
        assert report["fixtureNumTiles"] == 8160
        assert len(report["fields"]) == 12
        assert all(field["matches"] for field in report["fields"])
        assert len(report["failClosedGates"]) == 5
        assert all(
            gate["rejected"] and gate["diagnosticMatched"]
            for gate in report["failClosedGates"]
        )
        assert report["failures"] == []
        require_unity_log(
            repo_path(light_binning_gpu[f"{api}_log_path"]),
            light_binning_gpu[f"{api}_log_sha256"],
            [
                "Recovered LightBinningConstants validation passed:",
                "size=48",
                "GPU words=12/12",
                "fail-closed gates=5/5",
                f"api={api}",
                "Retail whole-scene light list remains open.",
            ],
        )
    assert (
        identified[1]["role"],
        identified[1]["symbol"],
        identified[1]["set"],
        identified[1]["binding"],
        identified[1]["size"],
    ) == ("ShadowData", "_32_33", 3, 34, 11440)
    assert identified[1]["status"].startswith("source-closed")
    require_hash(
        LAB_ROOT / identified[1]["source_metadata_path"],
        identified[1]["source_metadata_sha256"],
    )
    shadow_native = identified[1]["native_producer"]
    assert shadow_native["owner"] == (
        "HG.Rendering.Runtime.HGShadowConstantBufferUtils"
    )
    assert shadow_native["size_bytes"] == 11440
    assert shadow_native["punctual_section_offset_bytes"] == 1024
    assert shadow_native["punctual_section_size_bytes"] == 6144
    assert shadow_native["selected_read_span"] == "bytes 1024..6415"
    assert shadow_native["publication_policy"].startswith("fail closed")
    require_hash(
        repo_path(shadow_native["audit_path"]),
        shadow_native["audit_sha256"],
    )
    require_text_hash(
        repo_path(shadow_native["auditor_path"]),
        shadow_native["auditor_sha256"],
    )
    require_text_hash(
        repo_path(shadow_native["disassembler_path"]),
        shadow_native["disassembler_sha256"],
    )
    require_hash(
        repo_path(shadow_native["native_disassembly_path"]),
        shadow_native["native_disassembly_sha256"],
    )
    require_hash(
        repo_path(shadow_native["metadata_path"]),
        shadow_native["metadata_sha256"],
    )
    shadow_audit = json.loads(
        repo_path(shadow_native["audit_path"]).read_text(encoding="utf-8")
    )
    assert shadow_audit["schema"] == "endfield.shadow-data-audit.v1"
    assert shadow_audit["verdict"] == (
        "PUNCTUAL_SECTION_NATIVE_TRANSPORT_CLOSED_"
        "SETTLED_VALUES_CAPTURE_REQUIRED"
    )
    assert shadow_audit["publication_allowed"] is False
    assert shadow_audit["layout"]["size_bytes"] == 11440
    assert shadow_audit["layout"]["sections"] == [
        {"name": "CSM", "enum": 0, "offset": 0, "size": 1024},
        {
            "name": "PunctualLight",
            "enum": 1,
            "offset": 1024,
            "size": 6144,
        },
        {"name": "Character", "enum": 2, "offset": 7168, "size": 2048},
        {"name": "ASM", "enum": 3, "offset": 9216, "size": 2224},
    ]
    assert shadow_audit["layout"]["selected_read_span"] == (
        "bytes 1024..6415"
    )
    assert shadow_audit["layout"]["punctual_padding_not_read"] == (
        "bytes 6416..7167"
    )
    assert shadow_audit["capture_boundary"]["recommended_hook"].endswith(
        "PunctualLight (enum 1)"
    )
    assert shadow_native["frame_writer_owner"] == (
        "HG.Rendering.Runtime.HGPunctualLightShadowManagerV2"
    )
    assert shadow_native["max_shadow_caster_count"] == 56
    assert "all 56 matrix/params/params2 rows" in shadow_native["enabled_writer"]
    assert "does not write or publish ShadowData" in shadow_native[
        "disabled_writer"
    ]
    require_hash(
        repo_path(shadow_native["frame_writer_audit_path"]),
        shadow_native["frame_writer_audit_sha256"],
    )
    require_text_hash(
        repo_path(shadow_native["frame_writer_auditor_path"]),
        shadow_native["frame_writer_auditor_sha256"],
    )
    require_text_hash(
        repo_path(shadow_native["frame_writer_disassembler_path"]),
        shadow_native["frame_writer_disassembler_sha256"],
    )
    require_hash(
        repo_path(shadow_native["frame_writer_disassembly_path"]),
        shadow_native["frame_writer_disassembly_sha256"],
    )
    require_hash(
        repo_path(shadow_native["frame_writer_metadata_path"]),
        shadow_native["frame_writer_metadata_sha256"],
    )
    require_hash(
        repo_path(shadow_native["frame_writer_native_map_path"]),
        shadow_native["frame_writer_native_map_sha256"],
    )
    punctual_writer_audit = json.loads(
        repo_path(shadow_native["frame_writer_audit_path"]).read_text(
            encoding="utf-8"
        )
    )
    assert punctual_writer_audit["schema"] == (
        "endfield.punctual-shadow-writer-audit.v1"
    )
    assert punctual_writer_audit["verdict"] == (
        "ACTIVE_WRITER_CLOSED_SETTLED_FRAME_CAPTURE_REQUIRED"
    )
    assert punctual_writer_audit["publication_allowed"] is False
    assert punctual_writer_audit["manager"]["max_shadow_caster_count"] == 56
    assert punctual_writer_audit["enabled_frame_writer"]["regions"] == [
        {
            "field": "_PunctualLightWorldToShadow[56]",
            "offset": 1024,
            "size": 3584,
        },
        {
            "field": "_PunctualLightShadowParams[56]",
            "offset": 4608,
            "size": 896,
        },
        {
            "field": "_PunctualLightShadowParams2[56]",
            "offset": 5504,
            "size": 896,
        },
        {
            "field": "_PunctualLightShadowTexelSize",
            "offset": 6400,
            "size": 16,
        },
    ]
    assert punctual_writer_audit["enabled_frame_writer"]["publication"] == (
        "SetGlobalConstantBuffer(PunctualLight enum 1), then SetGlobalTexture"
    )
    assert punctual_writer_audit["disabled_frame"][
        "shadow_data_publication"
    ] is False
    assert punctual_writer_audit["disabled_frame"][
        "neutral_fixture_proven"
    ] is False
    assert punctual_writer_audit["capture_boundary"]["recommended_hook"].endswith(
        "VA 0x189b57155"
    )
    assert shadow_native["atlas_name"] == "Punctual Shadowmap"
    assert shadow_native["atlas_size"].startswith(
        "N == 0 ? 4*T x 4*T : (ceil(N*0.25)+4)*T x 4*T"
    )
    assert "T=512" in shadow_native["setting_defaults"]
    assert "N=8" in shadow_native["setting_defaults"]
    assert "3072x2048" in shadow_native["setting_defaults"]
    assert "Depth16" in shadow_native["atlas_descriptor"]
    assert "D16_UNorm" in shadow_native[
        "pinned_d3d12_physical_resolution"
    ]
    assert "_PunctualLightShadowTexV2" in shadow_native[
        "atlas_enabled_binding"
    ]
    assert "defaultShadowTexture" in shadow_native["atlas_disabled_binding"]
    require_hash(
        repo_path(shadow_native["atlas_audit_path"]),
        shadow_native["atlas_audit_sha256"],
    )
    require_text_hash(
        repo_path(shadow_native["atlas_auditor_path"]),
        shadow_native["atlas_auditor_sha256"],
    )
    require_hash(
        repo_path(shadow_native["atlas_descriptor_probe_path"]),
        shadow_native["atlas_descriptor_probe_sha256"],
    )
    require_text_hash(
        repo_path(shadow_native["atlas_descriptor_probe_source_path"]),
        shadow_native["atlas_descriptor_probe_source_sha256"],
    )
    punctual_atlas_audit = json.loads(
        repo_path(shadow_native["atlas_audit_path"]).read_text(encoding="utf-8")
    )
    assert punctual_atlas_audit["schema"] == (
        "endfield.punctual-shadow-atlas-audit.v1"
    )
    assert punctual_atlas_audit["verdict"] == (
        "ALLOCATION_BINDING_AND_PINNED_D3D12_FORMAT_CLOSED_"
        "TARGET_FRAME_CAPTURE_REQUIRED"
    )
    assert punctual_atlas_audit["publication_allowed"] is False
    assert punctual_atlas_audit["allocation"]["name"] == "Punctual Shadowmap"
    assert punctual_atlas_audit["allocation"]["width_formula"] == (
        "N == 0 ? 4*T : (ceil(N*0.25)+4)*T"
    )
    assert punctual_atlas_audit["allocation"]["height_formula"] == "4*T"
    assert punctual_atlas_audit["allocation"]["descriptor"] == {
        "slices": 1,
        "depthBufferBits": "DepthBits.Depth16 (16)",
        "colorFormat": "GraphicsFormat.R8G8B8A8_SRGB (4)",
        "filterMode": "FilterMode.Point (0)",
        "wrapMode": "TextureWrapMode.Clamp (1)",
        "dimension": "TextureDimension.Tex2D (2)",
        "enableRandomWrite": False,
        "useMipMap": False,
        "autoGenerateMips": False,
        "isShadowMap": True,
        "anisoLevel": 1,
        "mipMapBias": 0.0,
        "msaaSamples": "MSAASamples.None (1)",
        "bindTextureMS": False,
        "memoryless": 0,
    }
    punctual_defaults = punctual_atlas_audit["setting_defaults"]
    assert punctual_defaults["punctualLightShadowEnabled"] is True
    assert punctual_defaults["punctualLightTileMaxSize"] == 512
    assert punctual_defaults["punctualLightForceCullDistance"] == 200.0
    assert punctual_defaults["punctualLightEnvDynamicCasterCount"] == 6
    assert punctual_defaults["punctualLightMovableDynamicCasterCount"] == 2
    assert 0.0009999999 < punctual_defaults[
        "punctualLightShadowScreenSizeMin"
    ] < 0.0010000002
    assert punctual_defaults["derivedDynamicCasterCount"] == 8
    assert punctual_defaults["derivedAtlasWidth"] == 3072
    assert punctual_defaults["derivedAtlasHeight"] == 2048
    punctual_physical = punctual_atlas_audit["pinned_d3d12_resolution"]
    assert punctual_physical["unityVersion"] == "2022.3.62f3"
    assert punctual_physical["graphicsDeviceType"] == "Direct3D12"
    assert punctual_physical["actualGraphicsFormat"] == "R8G8B8A8_UNorm"
    assert punctual_physical["actualDepthStencilFormat"] == "D16_UNorm"
    assert punctual_physical["usesReversedZBuffer"] is True
    assert punctual_physical[
        "rawDepthAndComparisonSamplingExecuted"
    ] is True
    assert punctual_physical["d16QuantizationMatches"] is True
    assert punctual_physical["genericSampleSupportQuery"] is False
    punctual_probe = json.loads(
        repo_path(shadow_native["atlas_descriptor_probe_path"])
        .read_text(encoding="utf-8")
    )
    assert punctual_probe["actualDepthStencilFormat"] == "D16_UNorm"
    assert punctual_probe["descriptorMatches"] is True
    assert punctual_probe["depthSubElementSamplingExecuted"] is True
    assert punctual_probe["reversedZEndpointsMatch"] is True
    assert punctual_probe["d16QuantizationMatches"] is True
    assert punctual_atlas_audit["enabled_path"]["shader_property"] == (
        "_PunctualLightShadowTexV2"
    )
    assert punctual_atlas_audit["disabled_path"]["resource"] == (
        "HGRenderGraphDefaultResources.defaultShadowTexture"
    )
    assert punctual_atlas_audit["physical_boundary"][
        "recommended_hook"
    ].endswith("VA 0x189b57155")
    assert shadow_native["static_cache_layout"].startswith("40 slots")
    assert "40+i" in shadow_native["dynamic_slot_layout"]
    assert "indices 0..5" in shadow_native["caster_face_mapping"]
    assert "one request per frame" in shadow_native["cache_redraw_policy"]
    for path_key, hash_key, text_file in [
        ("cache_audit_path", "cache_audit_sha256", False),
        ("cache_auditor_path", "cache_auditor_sha256", True),
        ("cache_disassembler_path", "cache_disassembler_sha256", True),
        ("cache_disassembly_path", "cache_disassembly_sha256", False),
        ("cache_metadata_path", "cache_metadata_sha256", False),
        ("cache_native_map_path", "cache_native_map_sha256", False),
    ]:
        verifier = require_text_hash if text_file else require_hash
        verifier(
            repo_path(shadow_native[path_key]),
            shadow_native[hash_key],
        )
    punctual_cache_audit = json.loads(
        repo_path(shadow_native["cache_audit_path"]).read_text(
            encoding="utf-8"
        )
    )
    assert punctual_cache_audit["schema"] == (
        "endfield.punctual-shadow-cache-audit.v1"
    )
    assert punctual_cache_audit["verdict"] == (
        "CACHE_SLOT_AND_REDRAW_SCHEDULING_CLOSED_"
        "TARGET_FRAME_CAPTURE_REQUIRED"
    )
    assert punctual_cache_audit["publication_allowed"] is False
    static_cache = punctual_cache_audit["staticAllocator"]
    assert static_cache["levelCount"] == 3
    assert static_cache["slotCount"] == 40
    assert static_cache["levels"] == [
        {
            "level": 0,
            "absoluteSlots": [0, 11],
            "slotCount": 12,
            "cellSizeT": 1.0,
            "baseOffsetT": 0.0,
        },
        {
            "level": 1,
            "absoluteSlots": [12, 23],
            "slotCount": 12,
            "cellSizeT": 0.5,
            "baseOffsetT": 2.0,
        },
        {
            "level": 2,
            "absoluteSlots": [24, 39],
            "slotCount": 16,
            "cellSizeT": 0.25,
            "baseOffsetT": 3.0,
        },
    ]
    assert static_cache["rectOffsets"] == [
        [0, 0], [1, 0], [2, 0], [3, 0],
        [0, 1], [1, 1], [2, 1], [3, 1],
        [0, 2], [1, 2], [0, 3], [1, 3],
        [2, 2], [3, 2], [2, 3], [3, 3],
    ]
    dynamic_cache = punctual_cache_audit["dynamicRegion"]
    assert dynamic_cache["globalSlotFormula"] == "40+i"
    assert dynamic_cache["rectFormula"] == (
        "x=(4+floor(i/4))*T; y=(i mod 4)*T; width=height=T"
    )
    assert dynamic_cache["defaultCasterCount"] == 8
    assert dynamic_cache["defaultGlobalSlots"] == [40, 47]
    assert "every frame" in dynamic_cache["renderPolicy"]
    assert punctual_cache_audit["lightCaster"]["faceMapping"] == (
        "point lights construct six casters with index 0..5; "
        "spot-like lights construct index 0 only"
    )
    cache_schedule = punctual_cache_audit["staticCacheScheduling"]
    assert cache_schedule["requestTypes"] == {
        "None": 0,
        "AllocNewChunk": 1,
        "SmallChunkToLargeChunk": 2,
        "LargeChunkToSmallChunk": 3,
    }
    assert cache_schedule["singleRequestPerFrame"] is True
    assert cache_schedule["priority"] == [
        "LargeChunkToSmallChunk",
        "SmallChunkToLargeChunk",
        "AllocNewChunk",
    ]
    assert "lastVisitedTime" in punctual_cache_audit[
        "invalidationAndEviction"
    ]["allocationFailure"]
    assert "56-row ShadowData" in punctual_cache_audit[
        "captureBoundary"
    ]["open"]
    assert "PCF_3x3" in shadow_native["row_production"]
    assert "1.5*q" in shadow_native["row_production"]
    assert "saturate" in shadow_native["strength_fade"]
    assert "non-IFix-patched" in shadow_native["native_branch_boundary"]
    for path_key, hash_key, text_file in [
        ("row_audit_path", "row_audit_sha256", False),
        ("row_auditor_path", "row_auditor_sha256", True),
        ("row_disassembler_path", "row_disassembler_sha256", True),
        ("row_disassembly_path", "row_disassembly_sha256", False),
        ("row_metadata_path", "row_metadata_sha256", False),
        ("row_native_map_path", "row_native_map_sha256", False),
        ("row_cctor_metadata_path", "row_cctor_metadata_sha256", False),
        ("row_cctor_native_map_path", "row_cctor_native_map_sha256", False),
    ]:
        verifier = require_text_hash if text_file else require_hash
        verifier(
            repo_path(shadow_native[path_key]),
            shadow_native[hash_key],
        )
    punctual_row_audit = json.loads(
        repo_path(shadow_native["row_audit_path"]).read_text(
            encoding="utf-8"
        )
    )
    assert punctual_row_audit["schema"] == (
        "endfield.punctual-shadow-row-audit.v1"
    )
    assert punctual_row_audit["verdict"] == (
        "UNPATCHED_ROW_PRODUCTION_CLOSED_TARGET_FRAME_VALUES_"
        "CAPTURE_REQUIRED"
    )
    assert punctual_row_audit["publication_allowed"] is False
    assert punctual_row_audit["rowAssignment"] == {
        "static": "cache slot 0..39 writes the same ShadowData row",
        "dynamic": "dynamic caster i writes row 40+i",
        "finalSerialization": "all 56 rows are serialized every enabled frame",
    }
    assert punctual_row_audit["projection"] == {
        "near": "n=max(light.shadowNearPlane, 0.0001)",
        "far": "f=clamp(light.shadowFarPlane, n, 10000000*n)",
        "spotHalfAngleRadians": (
            "0.5*pi/180*clamp(spotAngle+guardAngle, 0, 179.9)"
        ),
        "pointHalfAngleRadians": (
            "0.5*pi/180*clamp(90+2, 0, 179.9)"
        ),
        "matrix": (
            "m00=m11=cot(halfAngle); m22=-(f+n)/(f-n); "
            "m23=-2*f*n/(f-n); m32=-1; other entries zero"
        ),
        "pointGuardAngleDegrees": 2.0,
        "spotGuardAngle": "light.shadowGuardAngle",
    }
    punctual_view = punctual_row_audit["view"]
    assert punctual_view["spot"] == (
        "inverse(light.localToWorldMatrix), then negate m20,m21,m22,m23"
    )
    assert punctual_view["pointFaceBasis"] == [
        [[0, 0, -1], [0, -1, 0], [-1, 0, 0]],
        [[0, 0, 1], [0, -1, 0], [1, 0, 0]],
        [[1, 0, 0], [0, 0, 1], [0, -1, 0]],
        [[1, 0, 0], [0, 0, -1], [0, 1, 0]],
        [[1, 0, 0], [0, -1, 0], [0, 0, -1]],
        [[-1, 0, 0], [0, -1, 0], [0, 0, 1]],
    ]
    punctual_world_to_shadow = punctual_row_audit["worldToShadow"]
    assert punctual_world_to_shadow["formula"] == "B * (P' * V)"
    assert "m20,m21,m22,m23" in punctual_world_to_shadow["reversedZ"]
    assert punctual_world_to_shadow["scaleBiasB"] == (
        "diag(0.5,0.5,0.5,1) with translation (0.5,0.5,0.5)"
    )
    punctual_params = punctual_row_audit["params"]
    assert punctual_params["baseTexelWorldSize"] == (
        "q=2/(projection.m00*shadowResolution)"
    )
    assert punctual_params["sampleMode"] == (
        "PCF_3x3 enum value 2; bias multiplier 1.5"
    )
    assert punctual_params["storedFormula"] == (
        "(0, 1.5*q*light.shadowNormalBias, q, fadedStrength)"
    )
    assert punctual_params["staticResolution"] == (
        "the selected cache slot width (T, T/2, or T/4)"
    )
    assert punctual_params["dynamicResolution"] == "T"
    punctual_strength = punctual_params["strength"]
    assert punctual_strength["formula"] == (
        "lerp(0, light.shadowStrength, saturate(t))"
    )
    assert punctual_strength["ratio"] == (
        "t=(c-d)/(c-light.shadowFadeRatio*c)"
    )
    assert punctual_row_audit["params2"]["storedFormula"] == (
        "(rect.xMin/atlasWidth, rect.yMin/atlasHeight, "
        "rect.xMax/atlasWidth, rect.yMax/atlasHeight)"
    )
    assert punctual_row_audit["texelSize"]["storedFormula"] == (
        "(1/atlasWidth, 1/atlasHeight, atlasWidth, atlasHeight)"
    )
    assert punctual_row_audit["nativeBranchBoundary"]["scope"] == (
        "the installed non-IFix-patched native branches"
    )
    assert "IFix patch state" in punctual_row_audit["captureBoundary"][
        "required"
    ]
    assert (
        identified[2]["role"],
        identified[2]["symbol"],
        identified[2]["set"],
        identified[2]["binding"],
        identified[2]["size"],
    ) == ("LightCookieData", "_44_45", 3, 37, 2560)
    assert identified[2]["status"].startswith("binary-source-closed")
    light_cookie_native = identified[2]["native_producer"]
    require_hash(
        repo_path(light_cookie_native["audit_path"]),
        light_cookie_native["audit_sha256"],
    )
    require_text_hash(
        repo_path(light_cookie_native["auditor_path"]),
        light_cookie_native["auditor_sha256"],
    )
    require_text_hash(
        repo_path(light_cookie_native["disassembler_path"]),
        light_cookie_native["disassembler_sha256"],
    )
    assert light_cookie_native["owner"] == (
        "HG.Rendering.Runtime.HGLightCookieManager"
    )
    assert light_cookie_native["upload_size_bytes"] == 2560
    assert light_cookie_native["light_cap"] == 32
    assert light_cookie_native["missing_cookie_index"] == -1

    light_cookie_audit = json.loads(
        repo_path(light_cookie_native["audit_path"]).read_text(encoding="utf-8")
    )
    assert light_cookie_audit["schema"] == "endfield.light-cookie-data-audit.v1"
    assert light_cookie_audit["decision"]["verdict"] == (
        "ISOLATED_ZERO_COOKIE_TRANSPORT_ALLOWED"
    )
    for pin in light_cookie_audit["inputs"].values():
        require_hash(repo_path(pin["path"]), pin["sha256"])
    assert light_cookie_audit["layout"] == {
        "atlasScaleOffset": {
            "count": 32,
            "offsetBytes": 0,
            "sizeBytes": 512,
            "strideBytes": 16,
        },
        "constantBufferSizeBytes": 2560,
        "maxCookieCount": 32,
        "worldOrDirectionToCookie": {
            "count": 32,
            "offsetBytes": 512,
            "sizeBytes": 2048,
            "strideBytes": 64,
        },
    }
    assert light_cookie_audit["producer"]["noCookieIndex"] == -1
    assert light_cookie_audit["consumer"]["guard"] == (
        "both punctual-light paths sample only when packed cookieIndex >= 0"
    )

    light_cookie_transport = identified[2]["unity_transport"]
    assert light_cookie_transport["activation_policy"] == (
        "default-off-fail-closed"
    )
    assert light_cookie_transport["environment_variable"] == (
        "ENDFIELD_RECOVERED_LIGHT_COOKIE_DATA"
    )
    assert light_cookie_transport["command_line_argument"] == (
        "-endfield-recovered-light-cookie-data"
    )
    assert light_cookie_transport["ready_property"] == (
        "_EndfieldRecoveredLightCookieDataReady"
    )
    assert light_cookie_transport["constant_buffer_property"] == (
        "_LightCookieData"
    )
    assert light_cookie_transport["texture_property"] == "_LightCookie"
    for path_key, hash_key in (
        ("contract_path", "contract_sha256"),
        ("runtime_path", "runtime_sha256"),
        ("probe_path", "probe_sha256"),
        ("verifier_path", "verifier_sha256"),
    ):
        require_text_hash(
            repo_path(light_cookie_transport[path_key]),
            light_cookie_transport[hash_key],
        )

    light_cookie_gpu = light_cookie_transport["gpu_validation"]
    assert light_cookie_gpu["fixture_sha256"] == (
        "e6cd3da342352c5b26a08d49f7d25589c7bb64c347c9cabb5224f09d3ee5bd89"
    )
    for api, device in (
        ("d3d11", "Direct3D11"),
        ("d3d12", "Direct3D12"),
    ):
        report_path = repo_path(light_cookie_gpu[f"{api}_report_path"])
        require_hash(
            report_path,
            light_cookie_gpu[f"{api}_report_sha256"],
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["schema"] == (
            "endfield.recovered-light-cookie-data-gpu-validation.v1"
        )
        assert report["graphicsDeviceType"] == device
        assert report["sizeBytes"] == 2560
        assert report["atlasBytes"] == 512
        assert report["matrixBytes"] == 2048
        assert report["vectorCount"] == 160
        assert report["wordCount"] == 640
        assert report["fixtureSha256"] == light_cookie_gpu["fixture_sha256"]
        assert report["gpuReadbackSha256"] == report["fixtureSha256"]
        assert report["gpuReadbackMatches"] is True
        assert report["zeroCookieFrameAccepted"] is True
        assert len(report["failClosedGates"]) == 3
        assert all(row["rejected"] for row in report["failClosedGates"])
        assert all(row["diagnostic"] for row in report["failClosedGates"])
        assert report["failures"] == []
        require_unity_log(
            repo_path(light_cookie_gpu[f"{api}_log_path"]),
            light_cookie_gpu[f"{api}_log_sha256"],
            [
                "Recovered LightCookieData validation passed:",
                "exact 2,560-byte layout",
                "640/640 GPU words",
                f"API={api}",
                "Non-empty retail cookie atlases remain open.",
            ],
        )
    assert (
        identified[3]["role"],
        identified[3]["symbol"],
        identified[3]["set"],
        identified[3]["binding"],
        identified[3]["size"],
    ) == (
        "HDPunctualLightCharacterShadowData",
        "_34_35",
        3,
        38,
        3568,
    )
    assert identified[3]["status"].startswith("source-closed")
    require_hash(
        LAB_ROOT / identified[3]["source_metadata_path"],
        identified[3]["source_metadata_sha256"],
    )
    hdpls_native = identified[3]["native_producer"]
    assert hdpls_native["owner"] == (
        "HG.Rendering.Runtime.HGHDPLSCharacterShadowManager"
    )
    assert hdpls_native["upload_callback"] == (
        "HGHDPLSCharacterShadowManager+<>c.<.cctor>b__33_1"
    )
    assert hdpls_native["reflected_size_bytes"] == 3568
    assert hdpls_native["native_requested_size_bytes"] == 3552
    assert hdpls_native["cbhandle_size_bytes"] == 3552
    assert hdpls_native["ring_start_alignment_bytes"] == 256
    assert hdpls_native["next_allocation_start_delta"] == 3584
    assert hdpls_native["cpu_tail_write_end_bytes"] == 3568
    assert hdpls_native["target_graphics_api"] == "Direct3D 11"
    assert hdpls_native["d3d11_num_constants_before_alignment"] == 222
    assert hdpls_native["d3d11_num_constants"] == 224
    assert hdpls_native["d3d11_visible_size_bytes"] == 3584
    assert hdpls_native["setting_defaults"] == (
        "hdpls enabled; atlas height=2048; screen-space reduce-resolution "
        "enabled; depth bias=0; normal bias=0; softness=0"
    )
    assert hdpls_native["default_atlas"] == (
        "4096x2048; 4x2 grid for requestCount<=8, 8x4 grid for requestCount>8"
    )
    assert hdpls_native["publication_policy"].startswith("fail closed")
    assert hdpls_native["texture_roles"] == {
        "raw_atlas_global": "_HDPLSTex",
        "screen_resolve_global": "_HDPLSScreenSpaceShadowMask",
        "deferred_binding_22": "_HDPLSScreenSpaceShadowMask",
    }
    assert hdpls_native["installed_ifix_state"] == {
        "base_file_count": 0,
        "persistent_file_count": 1,
        "persistent_target_count": 32,
        "hdpls_target_count": 0,
        "current_route": "both recovered non-IFix branches",
        "future_patch_boundary": True,
    }
    require_hash(
        repo_path(hdpls_native["installed_ifix_state_path"]),
        hdpls_native["installed_ifix_state_sha256"],
    )
    require_hash(
        repo_path(hdpls_native["audit_path"]),
        hdpls_native["audit_sha256"],
    )
    require_text_hash(
        repo_path(hdpls_native["auditor_path"]),
        hdpls_native["auditor_sha256"],
    )
    require_text_hash(
        repo_path(hdpls_native["disassembler_path"]),
        hdpls_native["disassembler_sha256"],
    )
    require_hash(
        repo_path(hdpls_native["native_disassembly_path"]),
        hdpls_native["native_disassembly_sha256"],
    )
    require_hash(
        repo_path(hdpls_native["metadata_path"]),
        hdpls_native["metadata_sha256"],
    )
    for path_key, hash_key in (
        ("native_map_path", "native_map_sha256"),
        ("setting_parameters_metadata_path", "setting_parameters_metadata_sha256"),
        ("setting_parameters_native_path", "setting_parameters_native_sha256"),
        ("setting_getters_metadata_path", "setting_getters_metadata_sha256"),
        ("setting_getters_native_path", "setting_getters_native_sha256"),
        ("punctual_row_audit_path", "punctual_row_audit_sha256"),
    ):
        require_hash(
            repo_path(hdpls_native[path_key]),
            hdpls_native[hash_key],
        )
    require_hash(
        repo_path(hdpls_native["constant_buffer_audit_path"]),
        hdpls_native["constant_buffer_audit_sha256"],
    )
    require_text_hash(
        repo_path(hdpls_native["constant_buffer_auditor_path"]),
        hdpls_native["constant_buffer_auditor_sha256"],
    )
    require_text_hash(
        repo_path(hdpls_native["unityplayer_disassembler_path"]),
        hdpls_native["unityplayer_disassembler_sha256"],
    )
    require_hash(
        repo_path(hdpls_native["unityplayer_disassembly_path"]),
        hdpls_native["unityplayer_disassembly_sha256"],
    )
    require_text_hash(
        repo_path(hdpls_native["target_player_log_excerpt_path"]),
        hdpls_native["target_player_log_excerpt_sha256"],
    )

    hdpls_constant_buffer = json.loads(
        repo_path(hdpls_native["constant_buffer_audit_path"]).read_text(
            encoding="utf-8"
        )
    )
    assert hdpls_constant_buffer["schema"] == (
        "endfield.hdpls-constant-buffer-audit.v1"
    )
    assert hdpls_constant_buffer["verdict"] == (
        "TARGET_D3D11_CPU_AND_GPU_TAIL_CLOSED"
    )
    assert hdpls_constant_buffer["allocation"] == {
        "requested_bytes": 3552,
        "cbhandle_size_bytes": 3552,
        "ring_rounded_bytes": 3552,
        "start_alignment_bytes": 256,
        "next_aligned_start_delta": 3584,
        "reflected_write_end_bytes": 3568,
        "padding_remaining_after_tail_bytes": 16,
        "next_allocation_overlap": False,
    }
    assert hdpls_constant_buffer["binding"]["serialized_size_bytes"] == 3552
    assert hdpls_constant_buffer["binding"]["global_state_size_bytes"] == 3552
    assert hdpls_constant_buffer["binding"]["target_graphics_api"] == (
        "Direct3D 11"
    )
    assert hdpls_constant_buffer["binding"]["d3d11_num_constants"] == 224
    assert hdpls_constant_buffer["binding"]["d3d11_visible_bytes"] == 3584
    assert hdpls_constant_buffer["binding"]["tail_gpu_visibility"] is True
    assert hdpls_constant_buffer["sources"]["unityplayer_sha256"] == (
        hdpls_native["unityplayer_sha256"]
    )

    hdpls_audit = json.loads(
        repo_path(hdpls_native["audit_path"]).read_text(encoding="utf-8")
    )
    assert hdpls_audit["schema"] == (
        "endfield.hdpls-character-shadow-data-audit.v1"
    )
    assert hdpls_audit["verdict"] == (
        "INSTALLED_IFIX_AND_RESOURCE_LIFECYCLE_CLOSED_"
        "ACTIVE_PIXELS_CAPTURE_REQUIRED"
    )
    assert hdpls_audit["publication_allowed"] is False
    assert hdpls_audit["layout"]["reflected_size_bytes"] == 3568
    assert hdpls_audit["layout"]["native_requested_size_bytes"] == 3552
    assert hdpls_audit["layout"]["selected_read_region"] == (
        "uint4[56] at bytes 2560..3455; only .y is read"
    )
    assert hdpls_audit["frame_lifecycle"]["screen_space_shadow_indices"] == (
        "4 entries reset to -1"
    )
    assert hdpls_audit["frame_lifecycle"]["character_indices"] == (
        "56 entries reset to 0"
    )
    assert hdpls_audit["frame_lifecycle"]["screen_space_channels"] == (
        "56 entries reset to 0"
    )
    assert hdpls_audit["frame_lifecycle"]["matrix_and_params"] == {
        "active_rows": (
            "overwritten from the binary-closed unpatched matrix and "
            "atlas-rect formulas"
        ),
        "unused_rows": "persistent static storage; not reset each frame",
    }
    hdpls_formulas = hdpls_audit["frame_derived_formulas"]
    assert hdpls_formulas["setting_field_offsets"] == {
        "hdplsCharacterShadowEnabled": "0x368",
        "hdplsAtlasHeight": "0x370",
        "hdplsScreenSpaceReduceResolution": "0x378",
        "hdplsDepthBias": "0x380",
        "hdplsNormalBias": "0x388",
        "hdplsSoftness": "0x390",
    }
    assert hdpls_formulas["constructor_defaults"] == {
        "hdplsCharacterShadowEnabled": True,
        "hdplsAtlasHeight": 2048,
        "hdplsScreenSpaceReduceResolution": True,
        "hdplsDepthBias": 0.0,
        "hdplsNormalBias": 0.0,
        "hdplsSoftness": 0.0,
    }
    assert hdpls_formulas["atlas"]["default_dimensions"] == [4096, 2048]
    assert hdpls_formulas["atlas"]["default_grid_le_8"] == [4, 2]
    assert hdpls_formulas["atlas"]["default_grid_gt_8"] == [8, 4]
    assert hdpls_formulas["atlas_texel_size"] == "(1/(2*S),1/S,2*S,S)"
    assert hdpls_formulas["global_params"] == "(hdplsSoftness.value,0,0,0)"
    assert hdpls_formulas["screen_space_light_positions"] == (
        "screenSlot stores float4(HGSharedLightData.worldPosition.xyz,0)"
    )
    assert hdpls_formulas["selector_publication"] == {
        "screen_space_shadow_index": (
            "screenSpaceShadowIndices[screenSlot] = punctualLightShadowIndex"
        ),
        "screen_space": (
            "punctualLightShadowSSChannel[punctualLightShadowIndex] = "
            "screenSlot + 1"
        ),
        "hdpls_atlas": (
            "punctualLightShadowHDCharacterIndices[punctualLightShadowIndex] "
            "sets bit (requestIndex & 31)"
        ),
    }
    verify_hdpls_matrix_formula_contract(
        hdpls_native,
        hdpls_audit,
        BINDING_CONTRACT_PATH,
    )
    verify_hdpls_resource_lifecycle_contract(
        hdpls_native,
        hdpls_audit,
        BINDING_CONTRACT_PATH,
    )
    assert len(hdpls_audit["capture_boundary"]["required"]) == 3
    assert len(hdpls_audit["capture_boundary"]["offline_closed"]) == 13
    for path_key, hash_key in (
        ("disassembly_path", "disassembly_sha256"),
        ("metadata_path", "metadata_sha256"),
        ("native_map_path", "native_map_sha256"),
        ("setting_parameters_metadata_path", "setting_parameters_metadata_sha256"),
        ("setting_parameters_native_path", "setting_parameters_native_sha256"),
        ("setting_getters_metadata_path", "setting_getters_metadata_sha256"),
        ("setting_getters_native_path", "setting_getters_native_sha256"),
        ("punctual_row_audit_path", "punctual_row_audit_sha256"),
        ("resource_metadata_path", "resource_metadata_sha256"),
        ("resolve_shader_path", "resolve_shader_sha256"),
        ("resolve_dxbc_sidecar_path", "resolve_dxbc_sidecar_sha256"),
        ("installed_ifix_state_path", "installed_ifix_state_sha256"),
        ("selected_shader_path", "selected_shader_sha256"),
        ("source_sidecar_path", "source_sidecar_sha256"),
        ("constant_buffer_audit_path", "constant_buffer_audit_sha256"),
    ):
        require_hash(
            repo_path(hdpls_audit["sources"][path_key]),
            hdpls_audit["sources"][hash_key],
        )

    roles = {
        row["role"]: (row["symbol"], row["set"], row["binding"])
        for row in contract["core_texture_roles"]
    }
    assert roles == {
        "_CameraDepthTexture": ("_18", 3, 27),
        "_GBufferTexture[0] / GBuffer A": ("_60", 3, 25),
        "_GBufferTexture[1] / GBuffer B": ("_61", 3, 24),
        "_GBufferTexture[2] / GBuffer C": ("_62", 3, 23),
        "_ScreenSpaceShadowMask": ("_42", 3, 26),
        "_WaterWetnessMaskTexture": ("_59", 3, 5),
        "_SSRLightingTexture": ("_19", 3, 8),
        "_SSRFadenessTexture": ("_20", 3, 9),
        "_IndirectAmbientOcclusionTexture": ("_21", 3, 21),
        "_LowResDirectionalShadow": ("_37", 3, 7),
        "_CSMShadowRampTex": ("_39", 3, 28),
        "_HDPLSScreenSpaceShadowMask": ("_38", 3, 22),
        "_PunctualLightShadowTexV2": ("_36", 3, 11),
        "_LightCookie": ("_43", 3, 13),
        "_MultiscatteringLUT": ("_41", 3, 12),
        "_IrradianceVolumeClipmapTextureALod0": ("_53", 3, 19),
        "_IrradianceVolumeClipmapTextureBLod0": ("_54", 3, 16),
        "_IrradianceVolumeClipmapTextureALod1": ("_55", 3, 18),
        "_IrradianceVolumeClipmapTextureBLod1": ("_56", 3, 15),
        "_IrradianceVolumeClipmapTextureALod3": ("_57", 3, 17),
        "_IrradianceVolumeClipmapTextureBLod3": ("_58", 3, 14),
        "_VisibilitySHRT": ("_52", 3, 6),
        "_LogSHLutTex": ("_51", 3, 29),
        "_ReflectionProbeOctTextureArray": ("_22", 3, 10),
        "_IntegratedLightScattering": ("_48", 3, 20),
    }
    scene_state = contract["charinfo_scene_resource_state"]
    assert scene_state["status"].startswith("serialized-source-closed")
    assert len(scene_state["sources"]) == 11
    for source in scene_state["sources"]:
        source_path = LAB_ROOT / source["path"]
        require_hash(source_path, source["sha256"])
        source_json = json.loads(source_path.read_text(encoding="utf-8"))
        assert (
            source_json.get("$animestudio", {}).get("rawDataSha256", "")
            == source["raw_data_sha256"]
        )
    routing = scene_state["volume_routing"]
    assert routing["controller_keys"] == {
        "charOverrideVolume": -5307430246267656445,
        "overrideVolume": -5307430246267656445,
    }
    assert routing["char_override_volume"] == {
        "enabled": True,
        "global": True,
        "priority": 30001.0,
        "weight": 1.0,
        "profile_path_id": 2267877729828506461,
        "profile_components": ["HGCharacterVolume"],
    }
    assert routing["global_volume"]["priority"] == 30000.0
    assert routing["global_volume"]["profile_path_id"] == -8401698007244884640
    assert routing["global_volume"]["profile_component_count"] == 12
    assert routing["global_environment_volume"] == {
        "enabled": True,
        "priority": 600,
        "manual_blend_factor": 1.0,
        "environment_phase_path_id": 1201129019072041203,
    }
    disabled = scene_state["disabled_or_overridden_features"]
    assert disabled["rain_wetness"]["enabled"] is False
    assert disabled["rain_wetness"]["disabled_shader_value"] == [1.0, 1.0]
    assert (
        disabled["rain_wetness"]["native_invalid_handle_fallback"]
        == "UnityEngine.Texture2D.whiteTexture"
    )
    assert disabled["rain_wetness"]["binding_evidence"] == wetness_resource
    assert disabled["volumetric_fog"]["fog_enabled"] is False
    assert disabled["volumetric_fog"]["height_fog_enabled"] is False
    assert disabled["volumetric_fog"]["volumetric_fog_enabled"] is False
    assert disabled["volumetric_fog"]["binding_evidence"] == fog_resource
    assert disabled["cloud_shadow"] == {
        "enabled": False,
        "texture_path_id": 0,
    }
    assert disabled["asm"] == {"disabled": True, "source_value": 1}
    assert disabled["directional_shadow"]["disabled"] is True
    assert disabled["directional_shadow"]["disable_override"] == 1.0
    assert disabled["directional_shadow"]["environment_csm_enabled"] is True
    assert disabled["directional_shadow"]["csm_ramp_texture"] == "null"
    assert (
        disabled["directional_shadow"]["csm_ramp_binding"]
        == "UnityEngine.Texture2D.blackTexture"
    )
    screen_shadow_contract_path = (
        LAB_ROOT
        / disabled["directional_shadow"]["screen_shadow_contract_path"]
    )
    require_hash(
        screen_shadow_contract_path,
        disabled["directional_shadow"]["screen_shadow_contract_sha256"],
    )
    assert (
        disabled["directional_shadow"][
            "character_ignores_main_light_shadow"
        ]
        is True
    )
    texture_relevance = scene_state["texture_relevance"]
    assert "canonical publication" in texture_relevance[
        "_LowResDirectionalShadow"
    ]
    assert texture_relevance["_CSMShadowRampTex"] == (
        "source-closed as UnityEngine.Texture2D.blackTexture for the "
        "installed CharInfo null csmRampTexture"
    )
    live = scene_state["live_environment_resources"]
    character_cubemap = live["character_max_cubemap"]
    assert character_cubemap["path_id"] == -8084913603968714749
    assert (
        character_cubemap["name"],
        character_cubemap["format"],
        character_cubemap["width"],
        character_cubemap["height"],
        character_cubemap["mip_count"],
        character_cubemap["face_count"],
    ) == ("T_hdri_reflection_char_01", "BC6H", 128, 128, 8, 6)
    require_hash(
        LAB_ROOT / character_cubemap["payload_path"],
        character_cubemap["payload_sha256"],
    )
    require_hash(
        LAB_ROOT / character_cubemap["manifest_path"],
        character_cubemap["manifest_sha256"],
    )
    assert live["environment_reflection"]["reflection_type"] == 1
    assert (
        live["environment_reflection"]["reflection_map_path_id"]
        == 2404688955498524548
    )
    assert (
        live["environment_reflection"]["skybox_cubemap_path_id"]
        == -5544960624411894816
    )
    reflection_cubemap = live["environment_reflection"][
        "reflection_map_cubemap"
    ]
    assert (
        reflection_cubemap["name"],
        reflection_cubemap["path_id"],
        reflection_cubemap["format"],
        reflection_cubemap["width"],
        reflection_cubemap["height"],
        reflection_cubemap["mip_count"],
        reflection_cubemap["face_count"],
    ) == (
        "T_hdri_env_char_01",
        2404688955498524548,
        "BC6H",
        128,
        128,
        8,
        6,
    )
    assert (
        reflection_cubemap["source_file"]
        == "CAB-7e9fb62841465607699a223e58b64af8"
    )
    assert reflection_cubemap["source_offset"] == 1026030945
    require_hash(
        LAB_ROOT / reflection_cubemap["payload_path"],
        reflection_cubemap["payload_sha256"],
    )
    require_hash(
        LAB_ROOT / reflection_cubemap["manifest_path"],
        reflection_cubemap["manifest_sha256"],
    )
    require_hash(
        LAB_ROOT / reflection_cubemap["recovery_filter_path"],
        reflection_cubemap["recovery_filter_sha256"],
    )
    assert (
        "_ReflectionProbeOctTextureArray publication remains deliberately "
        "default-off"
        in reflection_cubemap["runtime_binding_status"]
    )
    sky_cubemap = live["environment_reflection"]["skybox_cubemap"]
    assert (
        sky_cubemap["name"],
        sky_cubemap["format"],
        sky_cubemap["width"],
        sky_cubemap["height"],
        sky_cubemap["mip_count"],
        sky_cubemap["face_count"],
    ) == ("T_hdri_006", "BC6H", 128, 128, 8, 6)
    require_hash(
        LAB_ROOT / sky_cubemap["payload_path"],
        sky_cubemap["payload_sha256"],
    )
    require_hash(
        LAB_ROOT / sky_cubemap["manifest_path"],
        sky_cubemap["manifest_sha256"],
    )
    assert live["irradiance_volume"]["use_custom_default_sh"] is False
    assert live["irradiance_volume"]["charinfo_active_owner"] == "m_defaultIV"
    irradiance_selector = live["irradiance_volume"]["active_selector"]
    assert (
        irradiance_selector["renderedField"],
        irradiance_selector["renderedFieldOffset"],
        irradiance_selector["gachaFieldOffset"],
        irradiance_selector["behavior"],
    ) == (
        "m_defaultIV",
        0x10,
        0x30,
        "V2 PipelineUpdate always passes m_defaultIV to the native renderer",
    )
    assert "six A/B clipmap descriptors/order" in (
        live["irradiance_volume"]["status"]
    )
    assert live["irradiance_volume"]["active_clipmaps"][
        "resultOrder"
    ] == v2_report["activeClipmaps"]["resultOrder"]
    assert live["irradiance_volume"]["shader_publication"][
        "resultStoredAtObjectOffset"
    ] == 0x210
    assert live["visibility_sh"]["binding"] == visibility_report
    assert live["visibility_sh"]["lookup_textures"] == (
        visibility_lut_manifest["textures"]
    )
    assert "numeric pa/pb/dir fixtures" in live["visibility_sh"]["status"]
    assert "retail settled posed records" in live["visibility_sh"]["status"]
    assert "current installed settings lifecycle" in live[
        "visibility_sh"
    ]["status"]
    assert "enabled/0.8/5.0/half-resolution" in (
        live["visibility_sh"]["status"]
    )
    assert "256x1 RGBA32 Gamma LUT payloads" in (
        live["visibility_sh"]["status"]
    )
    buffers = contract["core_buffer_roles"]
    assert len(buffers) == 1
    assert (
        buffers[0]["role"],
        buffers[0]["symbol"],
        buffers[0]["kind"],
        buffers[0]["set"],
        buffers[0]["binding"],
    ) == ("_BinningBuffer", "_24", "ByteAddressBuffer", 3, 39)
    observations = contract["binary_observations"]
    assert observations["named_constant_buffer_count"] == 5
    assert observations["unnamed_constant_buffer_count"] == 4
    assert observations["texture_count"] == 25
    assert observations["buffer_count"] == 1
    assert observations["sampler_count"] == 5
    assert len(contract["remaining_blockers"]) == 4


def main() -> int:
    recovery = json.loads(RECOVERY_PATH.read_text(encoding="utf-8"))
    assert recovery["schema"] == (
        "endfield.charinfo.sphereoutside.deferred-lighting-recovery.v1"
    )
    verify_hgbuffer(recovery)
    verify_resolvers(recovery)
    verify_native_map(recovery)
    verify_selected_resolver_binding_contract()
    verify_deferred_gbuffer_frame_transport(recovery)
    verify_deferred_transform_variables_transport(recovery)
    verify_fail_closed(recovery)
    verify_visibility_sh_unity_replay()
    print(
        "SphereOutside deferred recovery verification passed: exact HGBuffer "
        "stages, 4 original shader dumps, one populated serialized subshader "
        "with 14 resolver passes / 640 D3D11 variants plus 3 empty LOD "
        "fallback subshaders, 7 native draw targets, the "
        "installed patch-audited passes 0/1/2 plus conditional WriteAlpha route, "
        "the installed UnityPlayer fallback scorer and unique serialized pass-0 "
        "D3D11 pair 96, with both original stages executed once in a fail-closed "
        "standalone D3D11 diagnostic, "
        "the exact DefaultDeferred GBuffer LightMode/five-color-target topology, "
        "runtime resolver shader/Material chain, and global-texture "
        "plus scene-color/depth attachment, ref-0 sphere stencil provenance, "
        "and the exact selected Vulkan fragment's 5 named / 4 debug-anonymous "
        "constant buffers (including b32 _LightBinningConstants with its "
        "exact native 48-byte producer layout and D3D11/D3D12-verified "
        "default-off isolated-count transport, plus the unique native "
        "CullLights producer, both HGCamera call sites and 256-candidate "
        "handoff before the still-open target-frame array, exact b34 ShadowData identity, "
        "11,440-byte four-section native transport, selected punctual-only read span, "
        "exact 56-row punctual frame writer, enabled section-1 push callback, disabled "
        "texture-only path, pinned D3D12 D16_UNorm resolution/reversed-Z/quantization, "
        "exact 40-static/40+i-dynamic cache slots and single-static-redraw scheduling, "
        "exact unpatched point/spot matrix, PCF bias, strength-fade, rect, and texel-size row production, "
        "and fail-closed pre-push capture boundary, plus b37 "
        "LightCookieData native layout/upload plus D3D11/D3D12-verified default-off "
        "zero-cookie isolated transport, plus exact b38 "
        "HDPunctualLightCharacterShadowData identity, native reset/push owner, "
        "selected .y-only read path, exact 0xDE0 CBHandle/command size, "
        "0x100-aligned CPU tail-write safety, target-D3D11 224-constant c222 visibility, "
        "exact HDPLS setting/default, atlas/rect/texel/global/world-position/selector formulas, "
        "exact installed-unpatched Bounds/light-to-TRS/spot-angle/reversed-Z matrix chain, "
        "and fail-closed active-frame boundary), "
        "all 25 sampled texture "
        "roles, exact installed CharInfo Volume/Environment state that gates "
        "wetness and volumetric-fog sampling while retaining live reflection, "
        "the deferred binder's white wetness fallback and exact 1x1x1 black "
        "ASTC_4x4 volumetric Texture3D fallback, "
        "the bilinear/clamp RGBAHalf VisibilitySH output descriptor and its "
        "exact black empty/disabled fallback, plus both exact shipped 256x1 "
        "RGBA32 Gamma VisibilitySH lookup payloads, the native 128-entry "
        "48-byte pa/pb/dir output ABI and culler, the exact native posed "
        "transform-to-record formula, Wulfa/Zhuang's ten enabled authored "
        "candidates, the exact selected additive pass-2 producer, and its "
        "default-off Unity half-depth/procedural-instance replay, "
        "the installed live V2 irradiance manager proving it always renders "
        "m_defaultIV, its six exact A/B clipmap descriptors/order and shared "
        "zero fallback, installed /aiTest path construction with no shipped IV "
        "match, marker-2/marker-3 index record formats and exact gacha sample "
        "payload span, plus the shipped Lua old-gacha ownership boundary, "
        "the exact reflection Cubemap's binary-derived 576x576x32 RGBAHalf "
        "slice-0 oct producer, the 4,160-byte global-buffer producer and "
        "serialized CharInfo SH-luminance fallback, plus the default-off "
        "D3D11/D3D12 bit-exact canonical light/zero-reflection binning, "
        "same-frame reflection resources, the full exact 128-byte b33 "
        "constant transport, and the D3D11/D3D12-identical nonzero canonical "
        "VisibilitySH frame publication, plus the source-camera 640x720 exact "
        "five-MRT SphereOutside HGBuffer sidecar with D32S8 depth and "
        "D3D11/D3D12-identical readbacks, and the selected b30 view/inverse-view/"
        "inverse-GPU-view-projection/camera-position words with zeroed unclosed "
        "rows are pinned; canonical publication and "
        "pass-0 presentation remain default-off because the CharInfo-frame "
        "runtime contract is not closed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Current VFS gate for anonymous BuffData union tag 0x1B.

This joins authenticated BuffData bytes, the maintained structural reader,
and the selected exact-build native union route. It does not promote action
field names, runtime behavior, provider selection, or whole-BuffData EOF.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mmap
import os
import re
import struct
import subprocess
from pathlib import Path
from typing import Any, Mapping

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs

from scripts.game_data.memorypack import buff_corpus, corpus_gate as vfs


TAG = 0x1B
FORMAT = "animestudio-buffdata-1b-current-vfs-corpus"
BOUNDARY = (
    "The current VFS census authenticates BuffData logical bytes and frames "
    "root-continuation action records structurally. Exact candidate files are "
    "streamed again to verify the 0x1B tag byte against their ledger MD5 and "
    "logical SHA-256. The exact-build AbilityActionData route and selected "
    "BlowOffAction_Data reader order are independently pinned. This does not "
    "establish that the continuation starts at a schema-authenticated root field, "
    "runtime provider selection, action field meanings, suffix ownership, or "
    "whole-BuffData EOF. A later unsupported continuation does not enlarge or "
    "invalidate an individually exact-closed earlier union range."
)

from scripts.repo_paths import REPO_ROOT
from scripts.common import canonical_json_sha256

REPO_ROOT = REPO_ROOT
GAME_DATA_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NATIVE_REPORT = REPO_ROOT / "reports/animestudio/il2cpp_context_current_latest.json"
DEFAULT_NATIVE_CONTRACT = GAME_DATA_ROOT / "buff_1b_native.json"
DEFAULT_ROOT_SIXTH_CONTRACT = GAME_DATA_ROOT / "buff_root_sixth_native.json"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "reports/animestudio/buff_1b_current_latest.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "reports/animestudio/buff_1b_current_latest.md"
NATIVE_SOURCE_PATHS = (
    GAME_DATA_ROOT / "il2cpp_context_audit.py",
    GAME_DATA_ROOT / "il2cpp_context.py",
    REPO_ROOT / "scripts/common.py",
    GAME_DATA_ROOT / "memorypack/buff_actions.py",
    GAME_DATA_ROOT / "buff_1b_native.json",
    GAME_DATA_ROOT / "buff_root_sixth_native.json",
)
SEQUENCE_TYPE = (
    "Beyond.MemoryPack."
    "Beyond_Gameplay_Core_SequenceActionDataForMemoryPack"
)


def _path_key(path: str | Path) -> str:
    return os.path.normcase(str(Path(path).resolve()))


def _guard_output_paths(outputs: tuple[Path, ...], protected_paths: list[Path]) -> None:
    paths = tuple(Path(path) for path in outputs)
    protected = [Path(__file__), *NATIVE_SOURCE_PATHS, *protected_paths]
    for output in paths:
        vfs._guard_output_path(output, protected + [other for other in paths if other != output])
    resolved = [_path_key(path) for path in paths]
    if len(set(resolved)) != len(resolved):
        vfs._fail("duplicate-output", source="BuffData 0x1B outputs", actual=resolved)


def _json_property(data: mmap.mmap, name: str, *, limit: int = 4 * 1024 * 1024) -> Any:
    marker = f'"{name}":'.encode("ascii")
    start = data.find(marker)
    if start < 0:
        vfs._fail("native-audit-property-missing", source=name)
    start += len(marker)
    while start < len(data) and data[start] in b" \t\r\n":
        start += 1
    stop = min(len(data), start + limit)
    try:
        return json.JSONDecoder().raw_decode(data[start:stop].decode("utf-8"))[0]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        vfs._fail(
            "native-audit-property-invalid",
            source=name,
            expected="complete JSON property value within the bounded report window",
            actual=str(exc),
        )


def _read_pe_image_base(path: Path) -> int:
    """Read and validate the AMD64 PE32+ ImageBase without loading the DLL."""
    path = Path(path)
    try:
        size = path.stat().st_size
        with path.open("rb") as stream:
            dos = stream.read(64)
            if len(dos) < 64 or dos[:2] != b"MZ":
                vfs._fail(
                    "native-gameassembly-dos-header-invalid",
                    source=str(path),
                    expected="64-byte DOS header beginning MZ",
                    actual={"length": len(dos), "signature": dos[:2].hex().upper()},
                )
            pe_offset = struct.unpack_from("<I", dos, 0x3C)[0]
            if pe_offset < 64:
                vfs._fail(
                    "native-gameassembly-pe-offset-before-header",
                    source=str(path),
                    offset=0x3C,
                    expected="e_lfanew >= 64",
                    actual=pe_offset,
                )
            if pe_offset > size - 24:
                vfs._fail(
                    "native-gameassembly-pe-offset-out-of-bounds",
                    source=str(path),
                    expected=f"PE header offset <= {max(-1, size - 24)}",
                    actual=pe_offset,
                )
            stream.seek(pe_offset)
            coff = stream.read(24)
            if len(coff) != 24 or coff[:4] != b"PE\0\0":
                vfs._fail(
                    "native-gameassembly-pe-header-invalid",
                    source=str(path),
                    offset=pe_offset,
                    expected="PE\0\0 signature and complete COFF header",
                    actual={"length": len(coff), "signature": coff[:4].hex().upper()},
                )
            machine, _sections, _stamp, _symbols, _symbol_count, optional_size, _flags = (
                struct.unpack_from("<HHIIIHH", coff, 4)
            )
            optional_offset = pe_offset + 24
            if (
                machine != 0x8664
                or optional_size < 32
                or optional_offset > size - optional_size
            ):
                vfs._fail(
                    "native-gameassembly-optional-header-invalid",
                    source=str(path),
                    offset=optional_offset,
                    expected={"machine": "AMD64 (0x8664)", "optionalHeaderSizeAtLeast": 32,
                              "optionalHeaderWithinFile": True},
                    actual={"machine": f"0x{machine:04X}", "optionalHeaderSize": optional_size,
                            "fileLength": size},
                )
            optional = stream.read(32)
            if len(optional) != 32 or struct.unpack_from("<H", optional, 0)[0] != 0x20B:
                vfs._fail(
                    "native-gameassembly-optional-magic-invalid",
                    source=str(path),
                    offset=optional_offset,
                    expected="PE32+ optional header (0x20B)",
                    actual=optional[:2].hex().upper(),
                )
            image_base = struct.unpack_from("<Q", optional, 24)[0]
            if image_base == 0:
                vfs._fail(
                    "native-gameassembly-image-base-invalid",
                    source=str(path),
                    offset=optional_offset + 24,
                    expected="nonzero 64-bit ImageBase",
                    actual=image_base,
                )
            return image_base
    except OSError as exc:
        vfs._fail("native-gameassembly-read-failed", source=str(path), actual=str(exc))


def _read_native_projection(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    fingerprint = vfs._fingerprint(path)
    if fingerprint["length"] <= 0:
        vfs._fail("native-audit-empty", source=str(path))
    try:
        with path.open("rb") as handle, mmap.mmap(
            handle.fileno(), 0, access=mmap.ACCESS_READ
        ) as data:
            projection = {
                "schemaVersion": _json_property(data, "schemaVersion"),
                "status": _json_property(data, "status"),
                "inputSetSha256": _json_property(data, "inputSetSha256"),
                "sourceHashes": _json_property(data, "sourceHashes"),
                "nativeInputs": _json_property(data, "nativeInputs"),
                "selectedBuffUnionRoutes": _json_property(data, "selectedBuffUnionRoutes"),
                "selectedBuff1BReadOrder": _json_property(data, "selectedBuff1BReadOrder"),
                "selectedBuffRootSixthReadOrder": _json_property(
                    data, "selectedBuffRootSixthReadOrder"
                ),
                "selectedBuffSequenceReadOrder": _json_property(
                    data, "selectedBuffSequenceReadOrder"
                ),
            }
    except OSError as exc:
        vfs._fail("native-audit-read-failed", source=str(path), actual=str(exc))
    return projection, fingerprint


def _live_native_sources(source_hashes: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(source_hashes, Mapping):
        vfs._fail("native-source-hashes-invalid", source="native audit sourceHashes")
    indexed: dict[str, str] = {}
    for source, digest in source_hashes.items():
        if isinstance(source, str) and isinstance(digest, str):
            indexed[_path_key(source)] = digest.upper()
    checked = []
    for source in NATIVE_SOURCE_PATHS:
        key = _path_key(source)
        expected = indexed.get(key)
        if expected is None:
            vfs._fail(
                "native-source-fingerprint-missing",
                source=str(source),
                expected="source hash in current native audit",
            )
        current = vfs._fingerprint(source)
        if current["sha256"] != expected:
            vfs._fail(
                "native-source-fingerprint-mismatch",
                source=str(source),
                expected=expected,
                actual=current["sha256"],
            )
        checked.append(current)
    return checked


def validate_native_selection(
    native: Mapping[str, Any],
    contract: Mapping[str, Any],
    root_contract: Mapping[str, Any],
    *,
    expected_input_set_sha256: str,
    expected_gameassembly_image_base: int | None = None,
) -> dict[str, Any]:
    """Join one exact current AbilityActionData route to its selected reader."""
    if not isinstance(native, Mapping):
        vfs._fail("native-audit-projection-invalid", source="IL2CPP native audit")
    if not isinstance(contract, Mapping) or not isinstance(root_contract, Mapping):
        vfs._fail("native-contract-invalid", source="BuffData native contracts")
    if not isinstance(expected_input_set_sha256, str):
        vfs._fail(
            "invalid-expected-input-set",
            source="native selection argument",
            expected="64 hexadecimal characters",
            actual=type(expected_input_set_sha256).__name__,
        )
    if expected_gameassembly_image_base is not None and (
        type(expected_gameassembly_image_base) is not int
        or expected_gameassembly_image_base <= 0
    ):
        vfs._fail(
            "native-gameassembly-image-base-argument-invalid",
            source="selected GameAssembly PE ImageBase",
            expected="positive integer",
            actual=expected_gameassembly_image_base,
        )
    expected_input = expected_input_set_sha256.upper()
    if native.get("schemaVersion") != 1 or native.get("status") != "structural-only":
        vfs._fail(
            "native-audit-not-structural-current-report",
            source="IL2CPP native audit",
            expected={"schemaVersion": 1, "status": "structural-only"},
            actual={"schemaVersion": native.get("schemaVersion"), "status": native.get("status")},
        )
    if native.get("inputSetSha256") != expected_input:
        vfs._fail(
            "native-audit-input-set-mismatch",
            source="IL2CPP native audit",
            expected=expected_input,
            actual=native.get("inputSetSha256"),
        )
    if contract.get("schemaVersion") != 1 or root_contract.get("schemaVersion") != 1:
        vfs._fail("native-contract-schema-mismatch", source="BuffData native contracts")

    route_contract = contract.get("unionRoute")
    native_contract_inputs = contract.get("nativeInputs")
    if not isinstance(route_contract, Mapping) or not isinstance(native_contract_inputs, Mapping):
        vfs._fail(
            "native-buff-1b-route-contract-missing",
            source="buff_1b_native.json",
            expected="pinned unionRoute and nativeInputs objects",
        )
    expected_native_hashes = {
        "gameassemblySha256": native_contract_inputs.get("gameassemblySha256"),
        "metadataSha256": native_contract_inputs.get("metadataSha256"),
    }
    for name, digest in expected_native_hashes.items():
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9A-Fa-f]{64}", digest):
            vfs._fail(
                "native-buff-1b-input-contract-invalid",
                source=f"buff_1b_native.json.nativeInputs.{name}",
                expected="64 hexadecimal characters",
                actual=digest,
            )
    reported_native_inputs = native.get("nativeInputs")
    if not isinstance(reported_native_inputs, Mapping):
        vfs._fail("native-inputs-missing", source="IL2CPP native audit")
    for name, expected_hash in expected_native_hashes.items():
        actual_hash = reported_native_inputs.get(name)
        if not isinstance(actual_hash, str) or actual_hash.upper() != expected_hash.upper():
            vfs._fail(
                "native-input-contract-mismatch",
                source=f"IL2CPP native audit.nativeInputs.{name}",
                expected=expected_hash.upper(),
                actual=actual_hash,
            )

    expected_route = {
        "tag": route_contract.get("tag"),
        "switchTargetRva": route_contract.get("switchTargetRva"),
        "typeDefinition": route_contract.get("typeDefinition"),
        "wrapperName": route_contract.get("wrapperName"),
    }
    if (
        type(expected_route["tag"]) is not int
        or expected_route["tag"] != TAG
        or type(expected_route["switchTargetRva"]) is not int
        or expected_route["switchTargetRva"] < 0
        or type(expected_route["typeDefinition"]) is not int
        or expected_route["typeDefinition"] < 0
        or not isinstance(expected_route["wrapperName"], str)
    ):
        vfs._fail(
            "native-buff-1b-route-contract-invalid",
            source="buff_1b_native.json.unionRoute",
            expected={"tag": TAG, "switchTargetRva": "nonnegative int",
                      "typeDefinition": "nonnegative int", "wrapperName": "string"},
            actual=expected_route,
        )
    expected_operands = route_contract.get("operands")
    if (
        not isinstance(expected_operands, list)
        or len(expected_operands) != 1
        or not isinstance(expected_operands[0], Mapping)
        or type(expected_operands[0].get("instructionRva")) is not int
        or type(expected_operands[0].get("usageTag")) is not int
        or type(expected_operands[0].get("registeredTypeIndex")) is not int
    ):
        vfs._fail(
            "native-buff-1b-route-operands-contract-invalid",
            source="buff_1b_native.json.unionRoute.operands",
            expected="one pinned instruction/usageTag/registeredTypeIndex tuple",
            actual=expected_operands,
        )
    expected_data_method_index = route_contract.get("dataReaderMethodIndex")
    if type(expected_data_method_index) is not int or expected_data_method_index < 0:
        vfs._fail(
            "native-buff-1b-data-method-contract-invalid",
            source="buff_1b_native.json.unionRoute.dataReaderMethodIndex",
            expected="nonnegative method index",
            actual=expected_data_method_index,
        )

    routes = native.get("selectedBuffUnionRoutes")
    route_rows = routes.get("rows") if isinstance(routes, Mapping) else None
    if not isinstance(route_rows, list):
        vfs._fail("native-union-routes-missing", source="selectedBuffUnionRoutes.rows")
    matching_routes = [row for row in route_rows if isinstance(row, Mapping) and row.get("tag") == TAG]
    if len(matching_routes) != 1:
        vfs._fail(
            "native-union-route-not-unique",
            source="selectedBuffUnionRoutes",
            expected=1,
            actual=len(matching_routes),
        )
    route = dict(matching_routes[0])
    if (
        type(route.get("switchTargetRva")) is not int
        or route["switchTargetRva"] < 0
        or type(route.get("typeDefinition")) is not int
        or route["typeDefinition"] < 0
        or not isinstance(route.get("wrapperName"), str)
        or not isinstance(route.get("operands"), list)
        or not route["operands"]
    ):
        vfs._fail(
            "native-union-route-incomplete",
            source="selectedBuffUnionRoutes.tag27",
            expected="switch target, registered wrapper, type definition, and operands",
            actual=route,
        )
    actual_route = {key: route.get(key) for key in expected_route}
    actual_route_operands = route.get("operands")
    actual_operand_projection = None
    if isinstance(actual_route_operands, list):
        actual_operand_projection = [
            {
                "instructionRva": operand.get("instructionRva"),
                "usageTag": operand.get("usageTag"),
                "registeredTypeIndex": operand.get("registeredTypeIndex"),
            }
            if isinstance(operand, Mapping)
            else operand
            for operand in actual_route_operands
        ]
    expected_operand_projection = [
        {
            "instructionRva": expected_operands[0]["instructionRva"],
            "usageTag": expected_operands[0]["usageTag"],
            "registeredTypeIndex": expected_operands[0]["registeredTypeIndex"],
        }
    ]
    if actual_route != expected_route or actual_operand_projection != expected_operand_projection:
        vfs._fail(
            "native-buff-1b-route-contract-mismatch",
            source="selectedBuffUnionRoutes.tag27",
            expected={**expected_route, "operands": expected_operand_projection},
            actual={**actual_route, "operands": actual_operand_projection},
        )

    reader = native.get("selectedBuff1BReadOrder")
    if not isinstance(reader, Mapping):
        vfs._fail("native-buff-1b-reader-missing", source="selectedBuff1BReadOrder")
    if reader.get("anonymousReadOrder") != contract.get("anonymousReadOrder"):
        vfs._fail(
            "native-buff-1b-read-order-mismatch",
            source="selectedBuff1BReadOrder",
            expected=contract.get("anonymousReadOrder"),
            actual=reader.get("anonymousReadOrder"),
        )
    if (
        reader.get("codeWindows") != contract.get("codeWindows")
        or reader.get("nestedContexts") != contract.get("nestedContexts")
    ):
        vfs._fail(
            "native-buff-1b-contract-mismatch",
            source="selectedBuff1BReadOrder",
            expected="pinned code windows and nested contexts from buff_1b_native.json",
        )
    contract_sha = reader.get("contractSha256")
    if not isinstance(contract_sha, str) or not re.fullmatch(r"[0-9A-Fa-f]{64}", contract_sha):
        vfs._fail(
            "native-buff-1b-contract-hash-invalid",
            source="selectedBuff1BReadOrder.contractSha256",
            expected="64 hexadecimal characters",
            actual=contract_sha,
        )

    contract_methods = contract.get("methods")
    selected_methods = reader.get("methods")
    if not isinstance(contract_methods, list) or not isinstance(selected_methods, list):
        vfs._fail("native-buff-1b-methods-invalid", source="selectedBuff1BReadOrder.methods")
    method_links = []
    image_bases = set()
    for expected in contract_methods:
        if not isinstance(expected, list) or len(expected) != 4:
            vfs._fail("buff-1b-contract-method-invalid", source="buff_1b_native.json", actual=expected)
        method_index, declaring_type, method_name, method_rva = expected
        matches = [
            row for row in selected_methods
            if isinstance(row, Mapping)
            and row.get("methodIndex") == method_index
            and row.get("declaringType") == declaring_type
            and row.get("name") == method_name
        ]
        if len(matches) != 1:
            vfs._fail(
                "native-buff-1b-method-not-unique",
                source="selectedBuff1BReadOrder.methods",
                offset=method_index,
                expected=1,
                actual=len(matches),
            )
        method = dict(matches[0])
        pointer = method.get("pointerVa")
        if (
            method.get("image") != "MemoryPack.Beyond.dll"
            or type(pointer) is not int
            or type(method_rva) is not int
            or pointer < method_rva
        ):
            vfs._fail(
                "native-buff-1b-method-invalid",
                source="selectedBuff1BReadOrder.methods",
                offset=method_index,
                expected="MemoryPack.Beyond method with a valid pointer and RVA",
                actual=method,
            )
        image_bases.add(pointer - method_rva)
        method_links.append(method)
    if len(image_bases) != 1:
        vfs._fail(
            "native-buff-1b-method-image-base-mismatch",
            source="selectedBuff1BReadOrder.methods",
            expected="one common GameAssembly image base",
            actual=sorted(image_bases),
        )
    if (
        expected_gameassembly_image_base is not None
        and image_bases != {expected_gameassembly_image_base}
    ):
        vfs._fail(
            "native-buff-1b-method-pe-image-base-mismatch",
            source="selectedBuff1BReadOrder.methods",
            expected=expected_gameassembly_image_base,
            actual=sorted(image_bases),
        )
    expected_data_methods = [
        row for row in contract_methods
        if isinstance(row, list)
        and len(row) == 4
        and row[0] == expected_data_method_index
        and row[1] == expected_route["wrapperName"]
        and row[2] == "Deserialize"
    ]
    if len(expected_data_methods) != 1:
        vfs._fail(
            "native-buff-1b-data-method-not-unique-in-contract",
            source="buff_1b_native.json.methods",
            expected={"methodIndex": expected_data_method_index,
                      "declaringType": expected_route["wrapperName"],
                      "name": "Deserialize"},
            actual=len(expected_data_methods),
        )
    data_type_methods = [
        row for row in method_links
        if row.get("methodIndex") == expected_data_method_index
        and row.get("declaringType") == expected_route["wrapperName"]
        and row.get("name") == "Deserialize"
    ]
    if len(data_type_methods) != 1:
        vfs._fail(
            "native-union-reader-route-mismatch",
            source="tag 0x1B to BlowOffAction_Data",
            expected={"methodIndex": expected_data_method_index,
                      "declaringType": expected_route["wrapperName"]},
            actual=[{"methodIndex": row.get("methodIndex"),
                     "declaringType": row.get("declaringType")} for row in method_links],
        )

    root_reader = native.get("selectedBuffRootSixthReadOrder")
    if not isinstance(root_reader, Mapping):
        vfs._fail("native-root-sixth-reader-missing", source="selectedBuffRootSixthReadOrder")
    if (
        root_reader.get("anonymousReadOrder") != root_contract.get("anonymousReadOrder")
        or root_reader.get("codeWindows") != root_contract.get("codeWindows")
        or root_reader.get("nestedContexts") != root_contract.get("nestedContexts")
    ):
        vfs._fail(
            "native-root-sixth-contract-mismatch",
            source="selectedBuffRootSixthReadOrder",
            expected="pinned root-member-six contract",
        )
    root_contract_methods = root_contract.get("methods")
    root_selected_methods = root_reader.get("methods")
    if not isinstance(root_contract_methods, list) or not isinstance(root_selected_methods, list):
        vfs._fail(
            "native-root-sixth-methods-invalid",
            source="selectedBuffRootSixthReadOrder.methods",
            expected="method arrays in native projection and contract",
            actual={"contract": type(root_contract_methods).__name__,
                    "selected": type(root_selected_methods).__name__},
        )
    root_method_links = []
    root_image_bases = set()
    for expected in root_contract_methods:
        if not isinstance(expected, list) or len(expected) != 4:
            vfs._fail(
                "buff-root-sixth-contract-method-invalid",
                source="buff_root_sixth_native.json.methods",
                actual=expected,
            )
        method_index, declaring_type, method_name, method_rva = expected
        matches = [
            row for row in root_selected_methods
            if isinstance(row, Mapping)
            and row.get("methodIndex") == method_index
            and row.get("declaringType") == declaring_type
            and row.get("name") == method_name
        ]
        if len(matches) != 1:
            vfs._fail(
                "native-root-sixth-method-not-unique",
                source="selectedBuffRootSixthReadOrder.methods",
                offset=method_index if type(method_index) is int else None,
                expected=1,
                actual=len(matches),
            )
        method = dict(matches[0])
        pointer = method.get("pointerVa")
        if (
            method.get("image") != "MemoryPack.Beyond.dll"
            or type(pointer) is not int
            or type(method_rva) is not int
            or method_rva < 0
            or pointer < method_rva
        ):
            vfs._fail(
                "native-root-sixth-method-invalid",
                source="selectedBuffRootSixthReadOrder.methods",
                offset=method_index if type(method_index) is int else None,
                expected="MemoryPack.Beyond method with a valid pointer and RVA",
                actual=method,
            )
        root_image_bases.add(pointer - method_rva)
        root_method_links.append(method)
    if len(root_method_links) != len(root_selected_methods) or len(root_image_bases) != 1:
        vfs._fail(
            "native-root-sixth-method-set-or-base-mismatch",
            source="selectedBuffRootSixthReadOrder.methods",
            expected={"methods": len(root_contract_methods), "imageBaseCount": 1},
            actual={"methods": len(root_selected_methods),
                    "imageBases": sorted(root_image_bases)},
        )
    if root_image_bases != image_bases:
        vfs._fail(
            "native-root-sixth-image-base-differs-from-data-reader",
            source="selectedBuffRootSixthReadOrder.methods",
            expected=sorted(image_bases),
            actual=sorted(root_image_bases),
        )
    if (
        expected_gameassembly_image_base is not None
        and root_image_bases != {expected_gameassembly_image_base}
    ):
        vfs._fail(
            "native-root-sixth-pe-image-base-mismatch",
            source="selectedBuffRootSixthReadOrder.methods",
            expected=expected_gameassembly_image_base,
            actual=sorted(root_image_bases),
        )

    root_contract_sha = root_reader.get("contractSha256")
    if not isinstance(root_contract_sha, str) or not re.fullmatch(
        r"[0-9A-Fa-f]{64}", root_contract_sha
    ):
        vfs._fail(
            "native-root-sixth-contract-hash-invalid",
            source="selectedBuffRootSixthReadOrder.contractSha256",
            expected="64 hexadecimal characters",
            actual=root_contract_sha,
        )

    sequence_reader = native.get("selectedBuffSequenceReadOrder")
    if not isinstance(sequence_reader, Mapping):
        vfs._fail("native-sequence-reader-missing", source="selectedBuffSequenceReadOrder")
    sequence_methods = sequence_reader.get("methods")
    if not isinstance(sequence_methods, list):
        vfs._fail(
            "native-sequence-methods-invalid",
            source="selectedBuffSequenceReadOrder.methods",
            expected="array",
            actual=type(sequence_methods).__name__,
        )
    sequence_method = [
        row for row in sequence_methods
        if isinstance(row, Mapping)
        and row.get("declaringType") == SEQUENCE_TYPE
        and row.get("name") == "Deserialize"
        and row.get("image") == "MemoryPack.Beyond.dll"
    ]
    if len(sequence_method) != 1:
        vfs._fail(
            "native-sequence-reader-not-unique",
            source="selectedBuffSequenceReadOrder.methods",
            expected=1,
            actual=len(sequence_method),
        )

    return {
        "unionRoute": route,
        "readerContractPath": reader.get("contractPath"),
        "readerContractSha256": str(reader.get("contractSha256")).upper(),
        "readerMethods": method_links,
        "readerCodeWindows": reader.get("codeWindows"),
        "readerNestedContexts": reader.get("nestedContexts"),
        "anonymousReadOrder": reader.get("anonymousReadOrder"),
        "rootMemberSix": {
            "contractPath": root_reader.get("contractPath"),
            "contractSha256": root_reader.get("contractSha256"),
            "methods": root_method_links,
            "gameAssemblyImageBase": next(iter(root_image_bases)),
            "anonymousReadOrder": root_reader.get("anonymousReadOrder"),
            "boundary": root_reader.get("boundary"),
        },
        "sequenceReader": {
            "method": dict(sequence_method[0]),
            "rootCodeWindow": sequence_reader.get("rootCodeWindow"),
            "boundary": sequence_reader.get("boundary"),
        },
        "boundary": (
            "The exact-build route maps tag 0x1B to the selected BlowOffAction_Data "
            "Deserialize method and its pinned member17 order. Root member6 contains "
            "BuffActionMap elements with SequenceActionData arrays. The SequenceActionData "
            "element provider remains conditional; this static route does not prove the "
            "runtime provider or formatter choice."
        ),
    }


def _verify_native_report(
    report_path: Path,
    contract_path: Path,
    root_contract_path: Path,
    *,
    expected_input_set_sha256: str,
) -> dict[str, Any]:
    native, fingerprint = _read_native_projection(report_path)
    try:
        contract = json.loads(contract_path.read_bytes())
        root_contract = json.loads(root_contract_path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        vfs._fail("native-contract-read-failed", source=str(contract_path), actual=str(exc))
    if not isinstance(contract, Mapping) or not isinstance(root_contract, Mapping):
        vfs._fail("native-contract-invalid", source="BuffData native contracts")
    selected_reader = native.get("selectedBuff1BReadOrder")
    selected_root_reader = native.get("selectedBuffRootSixthReadOrder")
    if not isinstance(selected_reader, Mapping):
        vfs._fail("native-buff-1b-reader-missing", source="selectedBuff1BReadOrder")
    if not isinstance(selected_root_reader, Mapping):
        vfs._fail("native-root-sixth-reader-missing", source="selectedBuffRootSixthReadOrder")
    if _path_key(str(selected_reader.get("contractPath", ""))) != _path_key(contract_path):
        vfs._fail(
            "native-buff-1b-contract-path-mismatch",
            source="selectedBuff1BReadOrder.contractPath",
            expected=str(contract_path.resolve()),
            actual=selected_reader.get("contractPath"),
        )
    reader_hash = selected_reader.get("contractSha256")
    if not isinstance(reader_hash, str) or reader_hash.upper() != vfs._fingerprint(contract_path)["sha256"]:
        vfs._fail("native-buff-1b-contract-hash-mismatch", source=str(contract_path))
    if _path_key(str(selected_root_reader.get("contractPath", ""))) != _path_key(root_contract_path):
        vfs._fail(
            "native-root-sixth-contract-path-mismatch",
            source="selectedBuffRootSixthReadOrder.contractPath",
            expected=str(root_contract_path.resolve()),
            actual=selected_root_reader.get("contractPath"),
        )
    root_reader_hash = selected_root_reader.get("contractSha256")
    if not isinstance(root_reader_hash, str) or root_reader_hash.upper() != vfs._fingerprint(root_contract_path)["sha256"]:
        vfs._fail("native-root-sixth-contract-hash-mismatch", source=str(root_contract_path))

    checked_sources = _live_native_sources(native.get("sourceHashes"))
    native_inputs = native.get("nativeInputs")
    if not isinstance(native_inputs, Mapping):
        vfs._fail("native-inputs-missing", source="IL2CPP native audit")
    native_contract_inputs = contract.get("nativeInputs")
    if not isinstance(native_contract_inputs, Mapping):
        vfs._fail("native-input-contract-missing", source="buff_1b_native.json")
    native_gate = check_installed_native_inputs(
        expected_gameassembly_sha256=str(native_contract_inputs.get("gameassemblySha256") or ""),
        expected_metadata_sha256=str(native_contract_inputs.get("metadataSha256") or ""),
        gameassembly=Path(str(native_inputs.get("gameassembly") or "")),
        metadata=Path(str(native_inputs.get("metadata") or "")),
        require_metadata=True,
    )
    if native_gate.status != NATIVE_EVIDENCE_VALIDATED:
        vfs._fail(
            "native-input-gate-failed",
            source="explicit GameAssembly.dll/global-metadata.dat",
            expected=NATIVE_EVIDENCE_VALIDATED,
            actual={
                "status": native_gate.status,
                "detail": native_gate.detail,
                "gameassembly": str(native_gate.gameassembly),
                "metadata": str(native_gate.metadata),
            },
        )
    gameassembly_image_base = _read_pe_image_base(native_gate.gameassembly)
    route_evidence = validate_native_selection(
        native,
        contract,
        root_contract,
        expected_input_set_sha256=expected_input_set_sha256,
        expected_gameassembly_image_base=gameassembly_image_base,
    )
    return {
        "path": str(report_path.resolve()),
        "length": fingerprint["length"],
        "sha256": fingerprint["sha256"],
        "inputSetSha256": native["inputSetSha256"],
        "sourceFingerprints": checked_sources,
        "nativeInputs": {
            "gameassembly": str(native_gate.gameassembly.resolve()),
            "gameassemblySha256": native_gate.gameassembly_sha256,
            "gameassemblyImageBase": gameassembly_image_base,
            "metadata": str(native_gate.metadata.resolve()),
            "metadataSha256": native_gate.metadata_sha256,
        },
        "selectedRoute": route_evidence,
    }


def select_root_tag_records(
    census: Mapping[str, Any],
    *,
    expected_input_set_sha256: str,
) -> list[dict[str, Any]]:
    if not isinstance(census, Mapping):
        vfs._fail("buff-census-invalid", source="BuffData current census")
    if not isinstance(expected_input_set_sha256, str):
        vfs._fail(
            "invalid-expected-input-set",
            source="BuffData record selection argument",
            expected="64 hexadecimal characters",
            actual=type(expected_input_set_sha256).__name__,
        )
    expected_input = expected_input_set_sha256.upper()
    if (
        census.get("format") != "animestudio-buffdata-current-vfs-corpus"
        or census.get("schemaVersion") != 1
        or census.get("status") != "complete"
        or census.get("publicationEligible") is not True
        or census.get("inputSetSha256") != expected_input
    ):
        vfs._fail(
            "buff-census-not-current-complete",
            source="BuffData current census",
            expected={"status": "complete", "inputSetSha256": expected_input},
            actual={
                "format": census.get("format"),
                "schemaVersion": census.get("schemaVersion"),
                "status": census.get("status"),
                "inputSetSha256": census.get("inputSetSha256"),
            },
        )
    rows = census.get("files")
    if not isinstance(rows, list):
        vfs._fail("buff-census-files-missing", source="BuffData current census")

    selected = []
    for file_index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            vfs._fail("buff-census-row-invalid", source=f"files[{file_index}]")
        identity = row.get("identity")
        if not isinstance(identity, Mapping):
            vfs._fail("buff-census-identity-missing", source=f"files[{file_index}]")
        path = identity.get("virtualPath")
        logical_sha = row.get("logicalSha256")
        if not isinstance(path, str) or identity.get("inputSetSha256") != expected_input:
            vfs._fail(
                "buff-census-identity-invalid",
                source=f"files[{file_index}]",
                expected={"virtualPath": "string", "inputSetSha256": expected_input},
                actual={"virtualPath": path, "inputSetSha256": identity.get("inputSetSha256")},
            )
        if not isinstance(logical_sha, str) or not re.fullmatch(r"[0-9A-F]{64}", logical_sha):
            vfs._fail("buff-census-logical-sha-invalid", source=path, actual=logical_sha)
        candidates = row.get("candidates")
        if not isinstance(candidates, list):
            vfs._fail("buff-census-candidates-invalid", source=path)
        for candidate_index, candidate in enumerate(candidates):
            if not isinstance(candidate, Mapping):
                vfs._fail(
                    "buff-census-candidate-invalid",
                    source=path,
                    offset=candidate_index,
                )
            profile = candidate.get("currentRootContinuation")
            if not isinstance(profile, Mapping):
                continue
            completed = profile.get("completedRecords")
            if not isinstance(completed, list):
                vfs._fail("buff-tag27-records-invalid", source=path + ".currentRootContinuation")
            for record_index, record in enumerate(completed):
                if (
                    not isinstance(record, Mapping)
                    or record.get("kind") != "union"
                    or record.get("tag") != TAG
                ):
                    continue
                record_source = f"{path}.tag27.record[{record_index}]"
                start = vfs._require_int(record.get("start"), source=record_source + ".start", minimum=0)
                end = vfs._require_int(record.get("end"), source=record_source + ".end", minimum=1)
                hard_limit = vfs._require_int(
                    candidate.get("hardLimit"), source=record_source + ".candidateHardLimit", minimum=1
                )
                anchor_offset = vfs._require_int(
                    candidate.get("anchorOffset"), source=record_source + ".anchorOffset", minimum=1
                )
                candidate_start = vfs._require_int(
                    candidate.get("startOffset"), source=record_source + ".candidateStart", minimum=0
                )
                profile_start = vfs._require_int(
                    profile.get("startOffset"), source=record_source + ".profileStart", minimum=0
                )
                profile_limit = vfs._require_int(
                    profile.get("readLimit"), source=record_source + ".profileReadLimit", minimum=1
                )
                profile_hard_limit = vfs._require_int(
                    profile.get("hardLimit"), source=record_source + ".profileHardLimit", minimum=1
                )
                parser_cursor = vfs._require_int(
                    profile.get("parserCursor"), source=record_source + ".parserCursor", minimum=1
                )
                event_profile = candidate.get("currentEventPrefix")
                if not isinstance(event_profile, Mapping):
                    vfs._fail("buff-tag27-parent-prefix-missing", source=path, offset=start)
                if event_profile.get("status") != "supported-prefix":
                    vfs._fail(
                        "buff-tag27-parent-prefix-not-supported",
                        source=path,
                        offset=start,
                        expected="supported-prefix",
                        actual=event_profile.get("status"),
                    )
                event_end = vfs._require_int(
                    event_profile.get("consumedEnd"), source=record_source + ".eventPrefixEnd", minimum=0
                )
                event_cursor = vfs._require_int(
                    event_profile.get("parserCursor"), source=record_source + ".eventParserCursor", minimum=0
                )
                event_limit = vfs._require_int(
                    event_profile.get("readLimit"), source=record_source + ".eventReadLimit", minimum=1
                )
                event_hard_limit = vfs._require_int(
                    event_profile.get("hardLimit"), source=record_source + ".eventHardLimit", minimum=1
                )
                if (
                    anchor_offset != hard_limit
                    or candidate_start != event_end
                    or event_cursor != event_end
                    or event_limit != hard_limit
                    or event_hard_limit != hard_limit
                    or profile_start != candidate_start
                    or profile_limit != hard_limit
                    or profile_hard_limit != hard_limit
                    or not candidate_start < hard_limit
                ):
                    vfs._fail(
                        "buff-tag27-continuation-boundary-mismatch",
                        source=path,
                        offset=start,
                        expected={"anchorOffset": hard_limit, "candidateStart": event_end,
                                  "eventParserCursor": event_end, "eventReadLimit": hard_limit,
                                  "eventHardLimit": hard_limit, "profileStart": candidate_start,
                                  "profileReadLimit": hard_limit, "profileHardLimit": hard_limit},
                        actual={"anchorOffset": anchor_offset, "candidateStart": candidate_start,
                                "eventParserCursor": event_cursor, "eventReadLimit": event_limit,
                                "eventHardLimit": event_hard_limit, "profileStart": profile_start,
                                "profileReadLimit": profile_limit, "profileHardLimit": profile_hard_limit},
                    )
                continuation_status = profile.get("status")
                expected_boundary_class = {
                    "supported-prefix": "structural-prefix",
                    "unsupported": "unsupported",
                }.get(continuation_status)
                if (
                    expected_boundary_class is None
                    or profile.get("boundaryClass") != expected_boundary_class
                ):
                    vfs._fail(
                        "buff-tag27-continuation-status-invalid",
                        source=path,
                        offset=start,
                        expected={"status": "supported-prefix or unsupported",
                                  "boundaryClass": expected_boundary_class},
                        actual={"status": continuation_status,
                                "boundaryClass": profile.get("boundaryClass")},
                    )
                if not start < end <= parser_cursor <= profile_limit:
                    vfs._fail(
                        "buff-tag27-range-out-of-bounds",
                        source=path,
                        offset=start,
                        expected=f"start < end <= parser cursor <= hard limit ({hard_limit})",
                        actual={"start": start, "end": end, "parserCursor": parser_cursor},
                    )
                if record.get("boundaryClass") != "exact-closed" or record.get("hardLimit") != hard_limit:
                    vfs._fail(
                        "buff-tag27-record-not-exact-closed",
                        source=path,
                        offset=start,
                        expected={"boundaryClass": "exact-closed", "hardLimit": hard_limit},
                        actual={
                            "boundaryClass": record.get("boundaryClass"),
                            "hardLimit": record.get("hardLimit"),
                        },
                    )
                context = {
                    "inputSetSha256": expected_input,
                    "logicalFileIdentity": path,
                    "logicalSha256": logical_sha,
                    "startOffset": candidate_start,
                    "hardLimit": hard_limit,
                }
                expected_record_context = {**context, "recordRange": [start, end]}
                if (
                    candidate.get("boundaryContext") != context
                    or event_profile.get("boundaryContext") != context
                    or profile.get("boundaryContext") != context
                    or record.get("boundaryContext") != expected_record_context
                ):
                    vfs._fail(
                        "buff-tag27-boundary-context-mismatch",
                        source=path,
                        offset=start,
                        expected={"candidateContext": context, "recordRange": [start, end]},
                        actual={
                            "candidateContext": candidate.get("boundaryContext"),
                            "eventProfileContext": event_profile.get("boundaryContext"),
                            "profileContext": profile.get("boundaryContext"),
                            "recordContext": record.get("boundaryContext"),
                        },
                    )
                if not candidate.get("readerAcceptedThroughEof"):
                    vfs._fail(
                        "buff-tag27-without-accepted-candidate",
                        source=path,
                        offset=start,
                        expected=True,
                        actual=candidate.get("readerAcceptedThroughEof"),
                    )
                coverage = row.get("coverageStatus")
                if coverage not in {"unique", "ambiguous"}:
                    vfs._fail(
                        "buff-tag27-candidate-coverage-invalid",
                        source=path,
                        offset=start,
                        expected="unique or ambiguous",
                        actual=coverage,
                    )
                selected.append(
                    {
                        "logicalFileIdentity": path,
                        "logicalSha256": logical_sha,
                        "ledgerIdentity": dict(identity),
                        "candidateIndex": candidate_index,
                        "anchorOffset": anchor_offset,
                        "hardLimit": hard_limit,
                        "fileCoverageStatus": coverage,
                        "rootContinuationStatus": row.get("rootContinuationStatus"),
                        "continuationStatus": continuation_status,
                        "parserCursor": parser_cursor,
                        "recordRange": [start, end],
                        "tag": TAG,
                        "uniqueCandidate": coverage == "unique",
                        "tagByteRange": None,
                    }
                )
    return selected


def _stream_exact_files(
    cli_path: Path,
    outer: Mapping[str, Any],
    identities: Mapping[str, Mapping[str, Any]],
) -> dict[str, bytes]:
    if not identities:
        return {}
    pattern = "^(?:" + "|".join(re.escape(path) for path in sorted(identities)) + ")$"
    command = [
        str(cli_path.resolve()),
        "stream",
        "--streaming-assets",
        str(outer["primaryAssets"]),
        "--fallback-assets",
        str(outer["fallbackAssets"]),
        "--block-type",
        "json-data",
        "--verify-md5",
        "--file-regex",
        pattern,
    ]
    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if process.returncode != 0:
        vfs._fail(
            "buff-tag27-stream-failed",
            source=str(cli_path),
            expected=0,
            actual={"returnCode": process.returncode, "stderr": process.stderr[-4000:]},
        )
    rows = []
    for line_number, line in enumerate(process.stdout.splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            vfs._fail(
                "buff-tag27-stream-json-invalid",
                source="AnimeStudio stream stdout",
                offset=line_number,
                actual=str(exc),
            )
        if not isinstance(row, dict):
            vfs._fail(
                "buff-tag27-stream-row-invalid",
                source="AnimeStudio stream stdout",
                offset=line_number,
                actual=type(row).__name__,
            )
        rows.append(row)
    terminal = re.findall(r"(?m)^Streamed ([0-9]+) files\s*$", process.stderr)
    if len(terminal) != 1 or int(terminal[0]) != len(rows) or len(rows) != len(identities):
        vfs._fail(
            "buff-tag27-stream-terminal-count-mismatch",
            source="AnimeStudio stream",
            expected={"rows": len(identities), "terminal": len(identities)},
            actual={"rows": len(rows), "terminal": terminal},
        )

    data_by_path: dict[str, bytes] = {}
    for index, row in enumerate(rows):
        path = row.get("fileName")
        if not isinstance(path, str) or path not in identities or path in data_by_path:
            vfs._fail(
                "buff-tag27-stream-identity-mismatch",
                source=f"AnimeStudio stream row {index}",
                expected="one unique selected BuffData identity",
                actual=path,
            )
        selected = identities[path]
        identity = selected.get("ledgerIdentity", selected)
        if (row.get("blockType"), row.get("blockTypeValue")) != ("JsonData", 19):
            vfs._fail("buff-tag27-stream-block-mismatch", source=path)
        encoded = row.get("dataBase64")
        if not isinstance(encoded, str):
            vfs._fail("buff-tag27-stream-data-missing", source=path)
        try:
            data = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            vfs._fail("buff-tag27-stream-base64-invalid", source=path, actual=str(exc))
        length = vfs._require_int(row.get("length"), source=path + ".length", minimum=1)
        if length != len(data) or length != identity.get("length"):
            vfs._fail(
                "buff-tag27-stream-length-mismatch",
                source=path,
                expected=identity.get("length"),
                actual=[length, len(data)],
            )
        md5 = hashlib.md5(data).hexdigest().upper()
        if md5 != str(identity.get("recomputedFileDataMd5") or "").upper():
            vfs._fail(
                "buff-tag27-stream-md5-mismatch",
                source=path,
                expected=identity.get("recomputedFileDataMd5"),
                actual=md5,
            )
        data_sha = hashlib.sha256(data).hexdigest().upper()
        expected_logical_sha = selected.get("logicalSha256") or identity.get("logicalSha256")
        if data_sha != expected_logical_sha:
            vfs._fail(
                "buff-tag27-stream-logical-sha-mismatch",
                source=path,
                expected=expected_logical_sha,
                actual=data_sha,
            )
        data_by_path[path] = data
    if set(data_by_path) != set(identities):
        vfs._fail(
            "buff-tag27-stream-selected-set-mismatch",
            source="AnimeStudio stream",
            expected=sorted(identities),
            actual=sorted(data_by_path),
        )
    return data_by_path


def bind_tag_bytes(records: list[dict[str, Any]], data_by_path: Mapping[str, bytes]) -> None:
    """Prove that each selected parser record begins with the literal 0x1B byte."""
    for record in records:
        path = record["logicalFileIdentity"]
        data = data_by_path.get(path)
        if data is None:
            vfs._fail("buff-tag27-bytes-missing", source=path)
        start, end = record["recordRange"]
        if end > len(data):
            vfs._fail(
                "buff-tag27-record-range-out-of-file",
                source=path,
                offset=start,
                expected=f"end <= {len(data)}",
                actual=end,
            )
        profile_ranges = record.pop("_profileRanges", None)
        if not isinstance(profile_ranges, list):
            vfs._fail("buff-tag27-parser-ranges-missing", source=path, offset=start)
        tag_spans = [
            span
            for span in profile_ranges
            if isinstance(span, Mapping)
            and span.get("kind") == "union-tag"
            and span.get("start") == start
        ]
        if len(tag_spans) != 1:
            vfs._fail(
                "buff-tag27-tag-span-not-unique",
                source=path,
                offset=start,
                expected=1,
                actual=len(tag_spans),
            )
        span = tag_spans[0]
        if span.get("end") != start + 1 or data[start : start + 1] != bytes([TAG]):
            vfs._fail(
                "buff-tag27-byte-mismatch",
                source=path,
                offset=start,
                expected={"tag": TAG, "bytes": "1B", "end": start + 1},
                actual={"bytes": data[start : min(end, start + 3)].hex().upper(), "span": dict(span)},
            )
        record["tagByteRange"] = [start, start + 1]
        record["tagByteHex"] = data[start : start + 1].hex().upper()


def build_current_census(
    *,
    outer_path: Path,
    ledger_path: Path,
    cli_path: Path,
    native_report_path: Path,
    native_contract_path: Path,
    root_sixth_contract_path: Path,
    expected_input_set_sha256: str,
    outputs: tuple[Path, ...] = (),
) -> dict[str, Any]:
    if not isinstance(expected_input_set_sha256, str):
        vfs._fail(
            "invalid-expected-input-set",
            source="argument",
            expected="64 uppercase hex",
            actual=type(expected_input_set_sha256).__name__,
        )
    expected_input = expected_input_set_sha256.upper()
    if not re.fullmatch(r"[0-9A-F]{64}", expected_input):
        vfs._fail(
            "invalid-expected-input-set",
            source="argument",
            expected="64 uppercase hex",
            actual=expected_input_set_sha256,
        )
    native_before = _verify_native_report(
        native_report_path,
        native_contract_path,
        root_sixth_contract_path,
        expected_input_set_sha256=expected_input,
    )
    gate_source_before = vfs._fingerprint(Path(__file__))
    try:
        outer = json.loads(outer_path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        vfs._fail("outer-report-read-failed", source=str(outer_path), actual=str(exc))
    if not isinstance(outer, Mapping):
        vfs._fail("outer-report-invalid", source=str(outer_path), expected="JSON object", actual=type(outer).__name__)
    if outer.get("inputSetSha256") != expected_input:
        vfs._fail(
            "outer-input-set-mismatch",
            source=str(outer_path),
            expected=expected_input,
            actual=outer.get("inputSetSha256"),
        )

    protected = [
        Path(__file__),
        outer_path,
        ledger_path,
        native_report_path,
        native_contract_path,
        root_sixth_contract_path,
        Path(str(outer.get("primaryAssets") or "")),
        Path(str(outer.get("fallbackAssets") or "")),
        Path(native_before["nativeInputs"]["gameassembly"]),
        Path(native_before["nativeInputs"]["metadata"]),
    ]
    _guard_output_paths(outputs, protected)

    census = buff_corpus.build_current_census(
        outer_path=outer_path,
        ledger_path=ledger_path,
        cli_path=cli_path,
        expected_input_set_sha256=expected_input,
        outputs=outputs,
    )
    selected = select_root_tag_records(
        census,
        expected_input_set_sha256=expected_input,
    )
    identities: dict[str, Mapping[str, Any]] = {}
    for record in selected:
        path = record["logicalFileIdentity"]
        identity = record["ledgerIdentity"]
        prior = identities.get(path)
        if prior is not None and prior.get("ledgerIdentity") != identity:
            vfs._fail(
                "buff-tag27-duplicate-ledger-identity",
                source=path,
                expected=dict(prior["ledgerIdentity"]),
                actual=dict(identity),
            )
        identities[path] = {
            "ledgerIdentity": dict(identity),
            "logicalSha256": record["logicalSha256"],
        }
    data_by_path = _stream_exact_files(cli_path, outer, identities)

    for record in selected:
        profile = None
        for row in census["files"]:
            if row["identity"]["virtualPath"] != record["logicalFileIdentity"]:
                continue
            candidate = row["candidates"][record["candidateIndex"]]
            profile = candidate.get("currentRootContinuation")
            break
        if not isinstance(profile, Mapping):
            vfs._fail(
                "buff-tag27-profile-disappeared",
                source=record["logicalFileIdentity"],
                offset=record["recordRange"][0],
            )
        record["_profileRanges"] = profile.get("ranges")
    bind_tag_bytes(selected, data_by_path)

    vfs.verify_current_report_inputs(
        census,
        expected_format="animestudio-buffdata-current-vfs-corpus",
        label="BuffData",
    )
    native_after = _verify_native_report(
        native_report_path,
        native_contract_path,
        root_sixth_contract_path,
        expected_input_set_sha256=expected_input,
    )
    if native_before != native_after:
        vfs._fail(
            "buff-1b-native-evidence-drift",
            source=str(native_report_path),
            expected=canonical_json_sha256(native_before),
            actual=canonical_json_sha256(native_after),
        )
    gate_source_after = vfs._fingerprint(Path(__file__))
    if gate_source_before != gate_source_after:
        vfs._fail(
            "buff-1b-gate-source-drift",
            source=str(Path(__file__)),
            expected=gate_source_before,
            actual=gate_source_after,
        )

    unique = [row for row in selected if row["uniqueCandidate"]]
    status = (
        "success"
        if selected and len(unique) == len(selected)
        else "ambiguous"
        if selected
        else "unsupported"
    )
    summary = {
        "selectedBuffDataFiles": census["summary"]["filesSelected"],
        "uniqueTag27Records": len(unique),
        "ambiguousTag27Records": len(selected) - len(unique),
        "tag27LogicalFiles": len(data_by_path),
        "wholeSchemaExact": False,
    }
    return {
        "format": FORMAT,
        "schemaVersion": 1,
        "inputSetSha256": expected_input,
        "status": status,
        "publicationEligible": True,
        "wholeSchemaExact": False,
        "summary": summary,
        "buffDataCensus": {
            "identitySetSha256": census["identitySetSha256"],
            "summary": census["summary"],
            "provenance": census["provenance"],
        },
        "nativeAudit": native_after,
        "gateSource": gate_source_after,
        "records": selected,
        "evidenceBoundary": BOUNDARY,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-summary", type=Path, default=vfs.DEFAULT_OUTER)
    parser.add_argument("--outer-ledger", type=Path, default=vfs.DEFAULT_LEDGER)
    parser.add_argument("--cli", type=Path, default=vfs.DEFAULT_CLI)
    parser.add_argument("--native-report", type=Path, default=DEFAULT_NATIVE_REPORT)
    parser.add_argument("--native-contract", type=Path, default=DEFAULT_NATIVE_CONTRACT)
    parser.add_argument(
        "--root-sixth-contract",
        type=Path,
        default=DEFAULT_ROOT_SIXTH_CONTRACT,
    )
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args(argv)
    try:
        report = build_current_census(
            outer_path=args.outer_summary,
            ledger_path=args.outer_ledger,
            cli_path=args.cli,
            native_report_path=args.native_report,
            native_contract_path=args.native_contract,
            root_sixth_contract_path=args.root_sixth_contract,
            expected_input_set_sha256=args.expected_input_set_sha256,
            outputs=(args.output_json, args.output_md),
        )
    except vfs.CensusGateError as exc:
        print(json.dumps({"status": "failed", "diagnostic": exc.diagnostic}))
        return 1
    vfs._atomic_write_json(args.output_json, report)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(
        "# Current BuffData 0x1B reader gate\n\n"
        + report["inputSetSha256"]
        + "\n\n"
        + json.dumps(report["summary"], ensure_ascii=False)
        + "\n\n"
        + BOUNDARY
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": report["status"], "summary": report["summary"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

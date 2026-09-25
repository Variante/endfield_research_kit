"""Join IFix external declarations to unique selected IL2CPP method definitions.

This matches complete parameter types after substituting constructed owner and
method generic arguments. It does not observe reflection selection or runtime
execution. Patch bytes are caller supplied; the native pair is explicit and
must match the reviewed IFix VM contract before any row is projected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.ifix_patch import ordered_signature_parameters, parse_ifix_patch
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.protocol import runtime_type_name


DEFAULT_CONTRACT = CONTRACTS_DIR / "ifix_vm_operands_native.json"
REPORT_SCHEMA = "endfield-ifix-external-signature-audit-v1"

_PRIMITIVE_NAMES = {
    "System.Boolean": "bool", "System.Byte": "byte", "System.Char": "char",
    "System.Double": "double", "System.Int16": "short", "System.Int32": "int",
    "System.Int64": "long", "System.IntPtr": "nint", "System.Object": "object",
    "System.SByte": "sbyte", "System.Single": "float", "System.String": "string",
    "System.UInt16": "ushort", "System.UInt32": "uint", "System.UInt64": "ulong",
    "System.UIntPtr": "nuint", "System.Void": "void",
}
_GENERIC_VARIABLE = re.compile(r"(M?VAR)\[(\d+)\]")


class IFixSignatureEvidenceError(ValueError):
    """The selected build, file signature, or metadata join did not validate."""


def _unqualified_type_spec(assembly_qualified_name: str) -> str:
    depth = 0
    for index, char in enumerate(assembly_qualified_name):
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth < 0:
                raise IFixSignatureEvidenceError("unbalanced assembly-qualified type brackets")
        elif char == "," and depth == 0:
            return assembly_qualified_name[:index]
    if depth:
        raise IFixSignatureEvidenceError("unbalanced assembly-qualified type brackets")
    return assembly_qualified_name


def _constructed_arguments(type_spec: str) -> tuple[str, list[str]]:
    position = type_spec.find("[[")
    if position < 0:
        return type_spec, []
    base = type_spec[:position]
    index = position + 1
    arguments: list[str] = []
    while index < len(type_spec) and type_spec[index] == "[":
        depth = 1
        begin = index + 1
        cursor = begin
        while cursor < len(type_spec) and depth:
            if type_spec[cursor] == "[":
                depth += 1
            elif type_spec[cursor] == "]":
                depth -= 1
            cursor += 1
        if depth:
            raise IFixSignatureEvidenceError(f"unbalanced generic argument: {type_spec}")
        arguments.append(type_spec[begin:cursor - 1])
        index = cursor
        if index < len(type_spec) and type_spec[index] == ",":
            index += 1
        else:
            break
    if type_spec[index:] != "]" or not arguments:
        raise IFixSignatureEvidenceError(f"unconsumed generic argument suffix: {type_spec}")
    return base, arguments


def canonical_type_name(assembly_qualified_name: str) -> str:
    """Canonicalize the file's CLR type spelling to the native type reader's form."""
    name = _unqualified_type_spec(assembly_qualified_name)
    if name.endswith("&"):
        return canonical_type_name(name[:-1]) + "&"
    if name.endswith("[]"):
        return canonical_type_name(name[:-2]) + "[]"
    base, arguments = _constructed_arguments(name)
    if arguments:
        return base + "<" + ",".join(canonical_type_name(arg) for arg in arguments) + ">"
    return _PRIMITIVE_NAMES.get(base, base)


def _generic_parameter_indices(
    metadata: Any, container_index: int, owner_index: int, *, is_method: bool
) -> list[int]:
    if container_index < 0:
        return []
    containers = metadata.sections["genericContainers"]
    parameters = metadata.sections["genericParameters"]
    if containers.size % 16 or parameters.size % 16 or container_index >= containers.size // 16:
        raise IFixSignatureEvidenceError("generic container framing or index is invalid")
    owner, count, method_flag, start = struct.unpack_from(
        "<iiii", metadata.buf, containers.offset + container_index * 16
    )
    if (
        owner != owner_index or method_flag != int(is_method)
        or count < 0 or start < 0 or start + count > parameters.size // 16
    ):
        raise IFixSignatureEvidenceError(
            f"generic container {container_index}: owner, kind, or parameter span differs"
        )
    return list(range(start, start + count))


def _native_type_name(
    image: Any, type_index: int, bindings: dict[tuple[str, int], str]
) -> str:
    pointer_table = int(image.registration["types"], 16)
    type_pointer = image.pe.u64_at_va(pointer_table + type_index * 8)
    raw = image.pe.bytes_at_va(type_pointer, 16)
    name = runtime_type_name(image.pe, image.metadata, type_pointer)
    name = _GENERIC_VARIABLE.sub(
        lambda match: bindings.get((match.group(1), int(match.group(2))), match.group(0)),
        name,
    )
    # Il2CppType's byref bit is 0x20 in byte 11 for the selected v29 layout.
    return name + ("&" if raw[11] & 0x20 else "")


def _file_parameters(row: dict[str, Any], type_names: list[str]) -> list[str]:
    arguments = [type_names[index] for index in row["genericTypeIndices"]]
    values = []
    for parameter in ordered_signature_parameters(row):
        if parameter["kind"] == "extern-type-index":
            values.append(type_names[parameter["typeIndex"]])
            continue
        name = parameter["name"]
        if not re.fullmatch(r"!!\d+", name):
            raise IFixSignatureEvidenceError(f"unsupported IFix method generic parameter {name!r}")
        ordinal = int(name[2:])
        if ordinal >= len(arguments):
            raise IFixSignatureEvidenceError(
                f"generic parameter {name} outside {len(arguments)} method arguments"
            )
        values.append(arguments[ordinal])
    return values


def project_external_signatures(image: Any, data: bytes, *, source: str) -> dict[str, Any]:
    """Require complete parameter equality before naming a metadata definition."""
    parsed = parse_ifix_patch(data, source=source)
    metadata = image.metadata
    types = {metadata.type_full_name(row): row for row in metadata.types}
    file_types = [canonical_type_name(row["value"]) for row in parsed["externTypes"]["records"]]
    rows = []
    for file_index, record in enumerate(parsed["externMethods"]["records"]):
        owner_raw = parsed["externTypes"]["records"][record["declaringTypeIndex"]]["value"]
        owner_spec = _unqualified_type_spec(owner_raw)
        owner_base, owner_argument_raw = _constructed_arguments(owner_spec)
        owner_arguments = [canonical_type_name(arg) for arg in owner_argument_raw]
        file_parameters = _file_parameters(record, file_types)
        method_arguments = [file_types[index] for index in record["genericTypeIndices"]]
        result: dict[str, Any] = {
            "fileRowIndex": file_index,
            "recordOffset": record["offset"],
            "declaringType": file_types[record["declaringTypeIndex"]],
            "methodName": record["name"]["value"],
            "ownerGenericArguments": owner_arguments,
            "methodGenericArguments": method_arguments,
            "parameterTypes": file_parameters,
            "parameterGenericFlags": record["parameterGenericFlags"],
            "metadataDefinition": None,
            "evidenceBoundary": "unresolved",
            "runtimeMethodInfoSelection": "unobserved",
        }
        owner = types.get(owner_base)
        if owner is None:
            result["status"] = "owner-definition-missing"
            rows.append(result)
            continue
        owner_vars = _generic_parameter_indices(
            metadata, owner.generic_container_index, owner.index, is_method=False
        )
        if len(owner_vars) != len(owner_arguments):
            result["status"] = "owner-generic-arity-mismatch"
            rows.append(result)
            continue
        candidates = [
            method for method in metadata.methods_for(owner)
            if metadata.string(method.name_index) == record["name"]["value"]
            and method.parameter_count == len(file_parameters)
        ]
        matches = []
        for method in candidates:
            method_vars = _generic_parameter_indices(
                metadata, method.generic_container_index, method.index, is_method=True
            )
            if len(method_vars) != len(method_arguments):
                continue
            bindings = {
                **{("VAR", key): value for key, value in zip(owner_vars, owner_arguments)},
                **{("MVAR", key): value for key, value in zip(method_vars, method_arguments)},
            }
            native_parameters = [
                _native_type_name(image, parameter.type_index, bindings)
                for parameter in metadata.parameters_for(method)
            ]
            if native_parameters != file_parameters:
                continue
            matches.append({
                "methodIndex": method.index,
                "token": f"0x{method.token:08x}",
                "parameterTypes": native_parameters,
                "returnType": _native_type_name(image, method.return_type, bindings),
                "isStatic": bool(method.flags & 0x10),
                "isGenericDefinition": method.generic_container_index >= 0,
            })
        result["candidateCountAfterNameAndArity"] = len(candidates)
        result["exactSignatureMatchCount"] = len(matches)
        if len(matches) == 1:
            result["status"] = "direct-unique-metadata-definition"
            result["evidenceBoundary"] = "direct"
            result["metadataDefinition"] = matches[0]
        else:
            result["status"] = "no-exact-signature" if not matches else "ambiguous-exact-signature"
            result["boundedMatches"] = matches[:8]
        rows.append(result)
    return {
        "source": source,
        "input": parsed["input"],
        "sourceSelection": "caller-supplied-patch-file",
        "externalMethodCount": len(rows),
        "exactMatchCount": sum(row["evidenceBoundary"] == "direct" for row in rows),
        "unresolvedCount": sum(row["evidenceBoundary"] != "direct" for row in rows),
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        raw_contract = args.contract.read_bytes()
        contract = json.loads(raw_contract)
        if not isinstance(contract, dict) or contract.get("status") != "validated":
            raise IFixSignatureEvidenceError("reviewed IFix native contract is missing or unvalidated")
        native_inputs = contract["nativeInputs"]
        gate = check_installed_native_inputs(
            native_inputs["gameAssemblySha256"],
            native_inputs["globalMetadataSha256"],
            gameassembly=args.gameassembly,
            metadata=args.metadata,
        )
        if gate.status != NATIVE_EVIDENCE_VALIDATED:
            raise IFixSignatureEvidenceError(f"installed_native_inputs:{gate.status}:{gate.detail}")
        image = open_native_image(args.gameassembly, args.metadata)
        files = [
            project_external_signatures(image, path.read_bytes(), source=str(path))
            for path in args.input
        ]
    except (IFixSignatureEvidenceError, OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print(f"ifix-external-signatures: {error}", file=sys.stderr)
        return 1
    report = {
        "schema": REPORT_SCHEMA,
        "status": "validated-selected-native-signatures",
        "audit": {
            "contractFile": str(args.contract),
            "contractSha256": hashlib.sha256(raw_contract).hexdigest().upper(),
            "nativeInputs": {
                "gameAssemblySha256": gate.gameassembly_sha256.upper(),
                "globalMetadataSha256": gate.metadata_sha256.upper(),
            },
            "runtimeMethodInfoSelection": "unobserved",
        },
        "files": files,
        "fileCount": len(files),
        "externalMethodCount": sum(row["externalMethodCount"] for row in files),
        "exactMatchCount": sum(row["exactMatchCount"] for row in files),
        "unresolvedCount": sum(row["unresolvedCount"] for row in files),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"matched {report['exactMatchCount']}/{report['externalMethodCount']} "
        f"IFix external method rows in {len(files)} patch files"
    )
    return 0 if report["unresolvedCount"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

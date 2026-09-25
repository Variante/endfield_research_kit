"""Name IFix VM instruction opcodes from the selected installed IL2CPP build.

The file parser in ``ifix_patch`` establishes each eight-byte instruction
boundary.  The selected build's ``IFix.Core.Instruction`` layout establishes
two 32-bit fields, and ``IFix.Core.Code`` names the first one.  This module
does not interpret the operand or claim that a patch executed.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.ifix_patch import INSTRUCTION_WORD_SIZE, parse_ifix_patch
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.protocol import (
    enum_members,
    field_defaults,
    runtime_type_field_offsets,
)


class InstructionLayoutError(ValueError):
    """The selected build or patch does not support this exact opcode view."""


def _unique_type(metadata: Any, name: str) -> Any:
    matches = [row for row in metadata.types if metadata.type_full_name(row) == name]
    if len(matches) != 1:
        raise InstructionLayoutError(f"{name}: expected one type, found {len(matches)}")
    return matches[0]


def _type_sizes(image: Any, type_index: int) -> tuple[int, int]:
    registration = image.registration
    count = int(registration["typeDefinitionsSizesCount"])
    if not 0 <= type_index < count:
        raise InstructionLayoutError(f"type {type_index}: outside size table of {count}")
    table = int(registration["typeDefinitionsSizes"], 16)
    pointer = image.pe.u64_at_va(table + type_index * 8)
    if not pointer:
        raise InstructionLayoutError(f"type {type_index}: null size row")
    instance_size, native_size, _static_size, _thread_static_size = struct.unpack(
        "<IIII", image.pe.bytes_at_va(pointer, 16)
    )
    return instance_size, native_size


def selected_opcode_layout(gameassembly: Path, metadata_path: Path) -> dict[str, Any]:
    """Derive the format and enum from one explicit native pair, or fail closed."""
    gate = check_installed_native_inputs(
        gameassembly=Path(gameassembly), metadata=Path(metadata_path)
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise InstructionLayoutError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    image = open_native_image(Path(gameassembly), Path(metadata_path))
    metadata = image.metadata
    instruction = _unique_type(metadata, "IFix.Core.Instruction")
    code = _unique_type(metadata, "IFix.Core.Code")
    instruction_offsets = runtime_type_field_offsets(
        metadata, image.pe, image.registration, instruction.index
    )
    code_offsets = runtime_type_field_offsets(
        metadata, image.pe, image.registration, code.index
    )
    instruction_sizes = _type_sizes(image, instruction.index)
    code_sizes = _type_sizes(image, code.index)
    # IL2CPP reports value-type fields with the managed object-header offset.
    # Subtracting that 16-byte header gives file word offsets 0 and 4.
    if (
        instruction_offsets != {"Code": 16, "Operand": 20}
        or instruction_sizes != (24, INSTRUCTION_WORD_SIZE)
        or code_offsets.get("value__") != 16
        or code_sizes != (20, 4)
    ):
        raise InstructionLayoutError(
            "IFix instruction layout differs: "
            f"instructionOffsets={instruction_offsets} instructionSizes={instruction_sizes} "
            f"codeValueOffset={code_offsets.get('value__')} codeSizes={code_sizes}"
        )
    members = enum_members(metadata, field_defaults(metadata), "IFix.Core.Code")
    ids = [int(row["id"]) for row in members]
    if not members or len(ids) != len(set(ids)) or any(not 0 <= value <= 0xFFFFFFFF for value in ids):
        raise InstructionLayoutError("IFix.Core.Code has missing, duplicate, or invalid values")
    return {
        "nativeInputs": {
            "gameAssemblySha256": gate.gameassembly_sha256.upper(),
            "globalMetadataSha256": gate.metadata_sha256.upper(),
        },
        "instruction": {
            "typeName": "IFix.Core.Instruction",
            "nativeSize": instruction_sizes[1],
            "fieldOffsets": instruction_offsets,
        },
        "opcodeEnum": {
            "typeName": "IFix.Core.Code",
            "nativeSize": code_sizes[1],
            "members": [{"id": int(row["id"]), "name": row["name"]} for row in members],
        },
        "evidenceBoundary": "direct",
    }


def decode_patch_opcodes(data: bytes, layout: dict[str, Any], *, source: str) -> dict[str, Any]:
    """Decode only code names and raw operands inside exact parsed method spans."""
    parsed = parse_ifix_patch(data, source=source)
    members = layout["opcodeEnum"]["members"]
    names = {int(row["id"]): str(row["name"]) for row in members}
    if len(names) != len(members):
        raise InstructionLayoutError("opcode map contains duplicate values")
    methods = []
    for body in parsed["methods"]["records"]:
        start, end = body["codeOffset"], body["codeEndOffset"]
        raw = data[start:end]
        if len(raw) != body["codeSize"] * INSTRUCTION_WORD_SIZE:
            raise InstructionLayoutError(f"{source}: method {body['index']} code span changed")
        instructions = []
        for index, (code, operand) in enumerate(struct.iter_unpack("<II", raw)):
            if code not in names:
                raise InstructionLayoutError(
                    f"{source}: method {body['index']} instruction {index} "
                    f"at {start + index * INSTRUCTION_WORD_SIZE}: unknown opcode {code}"
                )
            instructions.append({
                "index": index,
                "offset": start + index * INSTRUCTION_WORD_SIZE,
                "opcode": code,
                "name": names[code],
                "operandUnsigned": operand,
                "operandSigned": operand if operand < 0x80000000 else operand - 0x100000000,
            })
        methods.append({
            "index": body["index"],
            "codeOffset": start,
            "instructionCount": len(instructions),
            "instructions": instructions,
        })
    return {
        "source": source,
        "input": parsed["input"],
        "consumedBytes": parsed["consumedBytes"],
        "fixRecords": parsed["fixRecords"],
        "methods": methods,
        "instructionCount": sum(row["instructionCount"] for row in methods),
        "sourceSelection": "caller-supplied-patch-file",
        "evidenceBoundary": "opcode-named-operand-raw",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        layout = selected_opcode_layout(args.gameassembly, args.metadata)
        files = [
            decode_patch_opcodes(path.read_bytes(), layout, source=str(path))
            for path in args.input
        ]
    except (InstructionLayoutError, OSError, ValueError, KeyError, RuntimeError) as error:
        print(f"ifix-vm-opcode-audit: {error}", file=sys.stderr)
        return 1
    report = {
        "schema": "endfield-ifix-vm-opcode-audit-v1",
        "status": "opcode_layout_validated",
        "layout": layout,
        "files": files,
        "fileCount": len(files),
        "instructionCount": sum(row["instructionCount"] for row in files),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"validated {len(files)} patch files, {report['instructionCount']} opcode names")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

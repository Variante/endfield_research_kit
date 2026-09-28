"""Test whether one authenticated Init descriptor ID can be a component bit index.

This is a counterexample gate, not a descriptor-name decoder. It authenticates
one VFS logical file and the selected native/metadata consumer before comparing
the stored ID range with the selected StreamingComponentType enum's bit range.

``StreamingComponentType`` is a ulong one-hot mask (``Transform`` = 1 up to
bit 42), and ``GetComponentIndexFromType`` returns the first set bit. A
stored descriptor ID above 42 (44 in the selected witness) would be bit 44
of the anonymous 128-bit mask that ``descriptor_mask_native`` builds, so
descriptor IDs and enum bit indices are distinct namespaces and even an ID
inside the enum's range is not labelled by numeric equality. A separate
ID-to-component lookup is not excluded.

Decode enum defaults at their declared width and encoding
(``_enum_index_range``). An earlier one-byte-per-entry read gave
StreamingComponentType a bogus "non-sequential, maximum 128" that wrongly
excluded it from the chunk readings, and gave flag enums incoherent
sequences; it only looked right for small sequential enums
(``StreamingLayer`` 0..10, ``ECSEntityType`` 0..13, ``ProxyEntityType``
0..10). A wrong read that returns a small tidy value is the dangerous kind.

Pass ``--game-root`` (the installed ``Endfield_Data``), ``--witness-path``
(one exact ``Data/Streaming/PC/.../InitChunkData_...bytes`` logical path) and
the VFS audit's ``--expected-input-set-sha256``. The witness is checked
against the current ledger and the selected first-root and descriptor-mask
native contracts. The gate writes
``reports/chunk_data/descriptor_component_index_boundary.json`` only when a
stored descriptor ID has a checked mask position but exceeds the named enum's
bit index range; that counterexample rules out direct ordinal identification
and does not label the descriptor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import field_defaults, runtime_type_name
from scripts.game_data.streaming.corpus import RAW_DATA_EXCEPTIONS
from scripts.game_data.streaming.descriptor_name_corpus import (
    DEFAULT_AUDIT, DEFAULT_LEDGER, _selected_rows,
)
from scripts.game_data.streaming.descriptor_names import _table_vector
from scripts.game_data.streaming.framing import (
    _bounded_vector, _decode_compressed, _root_layout, parse_streaming_file,
)
from scripts.game_data.streaming.native import validate_streaming_field2_native_contract
from scripts.game_data.streaming.descriptor_mask_native import validate_descriptor_mask_native
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.streaming-descriptor-component-index-boundary.v2"
DEFAULT_OUTPUT = REPO_ROOT / "reports/chunk_data/descriptor_component_index_boundary.json"
ENUM_TYPE = "UnityEngine.HyperGryph.Streaming.StreamingComponentType"
INDEX_ICALL = "UnityEngine.HyperGryph.Streaming.PropertySerializeId::GetComponentIndexFromType"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _enum_index_range(image: NativeImage) -> dict[str, Any]:
    """Decode selected ulong enum defaults, excluding its Count sentinel."""
    md = image.metadata
    owners = [row for row in md.types if md.type_full_name(row) == ENUM_TYPE]
    if len(owners) != 1:
        raise ValueError(f"enum:type-identity={len(owners)}")
    fields = list(md.fields_for(owners[0]))
    backing = [row for row in fields if md.string(row.name_index) == "value__"]
    if len(backing) != 1:
        raise ValueError("enum:backing-field")
    type_table = int(image.registration["types"], 16)

    def field_type(type_index: int) -> str:
        type_va = image.pe.u64_at_va(type_table + type_index * 8)
        if not type_va:
            raise ValueError(f"enum:missing-field-type={type_index}")
        return runtime_type_name(image.pe, md, type_va)

    if field_type(backing[0].type_index) != "ulong":
        raise ValueError("enum:expected-ulong-backing")
    defaults = field_defaults(md)
    blob = md.sections["fieldAndParameterDefaultValueData"]
    members: list[dict[str, Any]] = []
    sentinel: int | None = None
    for field in fields:
        name = md.string(field.name_index)
        if name == "value__":
            continue
        default = defaults.get(field.index)
        if default is None or field_type(default[0]) != "ulong":
            raise ValueError(f"enum:{name}:missing-ulong-default")
        offset = blob.offset + default[1]
        if not blob.offset <= offset <= blob.offset + blob.size - 8:
            raise ValueError(f"enum:{name}:default-outside-blob")
        value = struct.unpack_from("<Q", md.buf, offset)[0]
        if name == "Count":
            sentinel = value
        elif name != "None":
            if not value or value.bit_count() != 1:
                raise ValueError(f"enum:{name}:not-one-hot={value:#x}")
            members.append({"name": name, "index": value.bit_length() - 1})
        elif value != 0:
            raise ValueError("enum:None-is-nonzero")
    indexes = [row["index"] for row in members]
    if len(indexes) != len(set(indexes)) or not indexes:
        raise ValueError("enum:duplicate-or-empty-bit-index")
    max_bit = max(indexes)
    if sentinel != max_bit + 1:
        raise ValueError(f"enum:Count={sentinel},max-bit={max_bit}")
    return {"type": ENUM_TYPE, "memberCount": len(members),
            "maxBitIndex": max_bit, "countSentinel": sentinel}


def _icall_bit_index(image: NativeImage, native_report: dict[str, Any], unityplayer: Path) -> str:
    candidate = native_report["groupComponentNameCandidate"]
    bindings = [row for row in candidate["icallBindings"] if row["name"] == INDEX_ICALL]
    if len(bindings) != 1:
        raise ValueError("index-icall:binding-identity")
    unity = image.mapper.PeImage(unityplayer)
    rva = int(bindings[0]["functionRva"], 0)
    # The selected reviewed native contract also hashes this five-byte body.
    if unity.bytes_at_va(unity.image_base + rva, 5) != b"\x48\x0f\xbc\xc1\xc3":
        raise ValueError("index-icall:expected-bsf-rax-rcx-ret")
    return bindings[0]["name"]


def _authenticated_decoded_file(source: dict[str, Any], virtual_path: str) -> tuple[bytes, str, str]:
    with Path(source["physicalChunkPath"]).open("rb") as chunk:
        chunk.seek(source["offset"])
        packed = chunk.read(source["length"])
    if len(packed) != source["length"]:
        raise ValueError(f"source:short-physical-read={len(packed)}/{source['length']}")
    packed_md5 = hashlib.md5(packed).hexdigest().upper()
    if packed_md5 != source["recomputedFileDataMd5"]:
        raise ValueError("source:physical-MD5-mismatch")
    parsed = parse_streaming_file("init", packed, allow_raw=virtual_path in RAW_DATA_EXCEPTIONS)
    if parsed["encoding"] == "inverted_lz4":
        decoded = _decode_compressed(packed)
    elif parsed["encoding"] == "raw_flatbuffer" and virtual_path in RAW_DATA_EXCEPTIONS:
        decoded = packed
    else:
        raise ValueError(f"source:unsupported-encoding={parsed['encoding']}")
    return decoded, packed_md5, hashlib.sha256(decoded).hexdigest().upper()


def _first_out_of_range_descriptor(decoded: bytes, max_bit: int) -> dict[str, int] | None:
    root = _root_layout(decoded)
    root["tableOffset"] = root["rootOffset"]
    groups = _table_vector(decoded, root, 7, "root field 7 groups")
    for group_index, group in enumerate(groups):
        start, count, _end = _bounded_vector(decoded, group, 3, 8, "group descriptors")
        for descriptor_index in range(count):
            descriptor_id, stride, reserved = struct.unpack_from(
                "<HHI", decoded, start + 4 + descriptor_index * 8
            )
            if reserved or stride == 0:
                raise ValueError(f"group {group_index} descriptor {descriptor_index}:invalid-framing")
            if descriptor_id > max_bit:
                return {"groupIndex": group_index, "descriptorIndex": descriptor_index,
                        "descriptorId": descriptor_id, "stride": stride}
    return None


def audit_descriptor_component_index(
    *, game_root: Path, witness_path: str, expected_input_set_sha256: str,
    audit_path: Path = DEFAULT_AUDIT, ledger_path: Path = DEFAULT_LEDGER,
) -> dict[str, Any]:
    """Return one checked counterexample, withholding it on any gate failure."""
    result: dict[str, Any] = {"schema": SCHEMA, "status": "validation_failed", "witness": None}
    native = validate_streaming_field2_native_contract(game_root=game_root)
    if native["status"] != "validated":
        result["reason"] = {"nativeStatus": native["status"],
                            "validationFailures": native.get("validationFailures", [])[:5]}
        return result
    mask_native = validate_descriptor_mask_native(game_root=game_root)
    if mask_native["status"] != "validated":
        result["reason"] = {"maskNativeStatus": mask_native["status"],
                            "detail": mask_native.get("reason", "")}
        return result
    try:
        root = Path(game_root)
        image = NativeImage(root.parent / "GameAssembly.dll",
                            root / "il2cpp_data/Metadata/global-metadata.dat",
                            label="streaming-descriptor-index")
        enum = _enum_index_range(image)
        icall = _icall_bit_index(image, native, root.parent / "UnityPlayer.dll")
        audit = json.loads(Path(audit_path).read_text(encoding="utf-8-sig"))
        input_set = audit.get("inputSetSha256")
        if (not audit.get("summary", {}).get("fullAuditPassed")
                or not isinstance(input_set, str) or len(input_set) != 64):
            raise ValueError("vfs-audit:not-current-complete")
        if expected_input_set_sha256.upper() != input_set:
            raise ValueError("vfs-audit:expected-input-set-mismatch")
        sources = _selected_rows(Path(ledger_path), input_set)
        source = sources.get(witness_path)
        if source is None:
            raise ValueError("source:witness-path-absent-from-current-ledger")
        decoded, packed_md5, decoded_sha = _authenticated_decoded_file(source, witness_path)
        witness = _first_out_of_range_descriptor(decoded, enum["maxBitIndex"])
        if witness is None:
            raise ValueError("source:no-descriptor-outside-enum-bit-range")
        descriptor_id = witness["descriptorId"]
        if descriptor_id >= 128:
            raise ValueError(f"source:descriptor-id-outside-checked-mask={descriptor_id}")
    except (OSError, ValueError, KeyError, TypeError, IndexError, struct.error, RuntimeError) as error:
        result["reason"] = str(error)
        return result
    return {"schema": SCHEMA, "status": "validated-counterexample",
            "inputSetSha256": input_set, "vfsAuditSha256": _sha256_file(Path(audit_path)),
            "vfsLedgerSha256": _sha256_file(Path(ledger_path)),
            "nativeContractSha256": native["contractSha256"],
            "maskNativeContractSha256": mask_native["contractSha256"],
            "nativeInputs": {key: native[key] for key in (
                "gameAssemblySha256", "metadataSha256", "unityPlayerSha256")},
            "componentIndexIcall": icall, "enum": enum,
            "witness": {"virtualPath": witness_path, "packedMd5": packed_md5,
                        "decodedSha256": decoded_sha, **witness},
            "anonymousMaskPosition": {"wordIndex": descriptor_id // 64,
                                      "bitInWord": descriptor_id % 64,
                                      "bitIndex": descriptor_id},
            "evidenceBoundary": (
                "The selected native setup sets each signed descriptor ID as a bit in an "
                "anonymous two-QWORD packed-column mask. Under that selected static "
                "branch, this authenticated positive ID has a checked position in the "
                "mask, yet exceeds every bit index in the "
                "selected StreamingComponentType enum returned by the named bsf icall. "
                "The two index namespaces therefore cannot be equated generally. This "
                "does not name the descriptor or exclude a separate lookup mapping."
            )}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--witness-path", required=True, help="Exact InitChunkData VFS logical path")
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if (REPO_ROOT / "reports").resolve() not in output.parents:
        parser.error("--output must be under reports/")
    report = audit_descriptor_component_index(
        game_root=args.game_root, witness_path=args.witness_path,
        expected_input_set_sha256=args.expected_input_set_sha256,
        audit_path=args.audit, ledger_path=args.ledger,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Streaming descriptor/component index boundary: {report['status']}")
    if report["status"] != "validated-counterexample":
        print(report.get("reason", ""))
    return 0 if report["status"] == "validated-counterexample" else 1


if __name__ == "__main__":
    raise SystemExit(main())

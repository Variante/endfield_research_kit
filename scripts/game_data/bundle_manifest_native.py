"""Gate the installed native reader's bindings to manifest file sections.

The contract authenticates the selected initializer, array and dictionary
accessors, writers, and UTF-16 hash paths. A supplied ``manifest.hgmmap`` is
framed independently by ``bundle_manifest``. Its table offsets are projected
through the authenticated pointer and field reads. The supplied file then
replays both split dictionaries, their Bundle joins, every Brotli UTF-16 asset
path hash, and every Bundle version hash. Live gameplay use remains separate.

What the selected build establishes (``exact`` for the pinned inputs plus the
supplied file; the RVAs and field offsets live in
``contracts/bundle_manifest_native.json``):

* ``ManifestDataBinary.InitBinary`` maps the three fixed sections to
  ``assetInfoDictionary``, ``bundleInfoDictionary`` and ``bundles``. The
  nominal 32- and 56-byte section widths are a capacity accounting unit, not
  interleaved records: each dictionary section is a capacity word, that many
  eight-byte ``(relativeOffset, count)`` hash slots, then the same number of
  24-byte ``AssetInfo`` or 48-byte ``Bundle`` values. The array helper points
  straight at the 48-byte rows and ``TryGetBundleByIndex`` copies a whole row.
* The asset lookup reads ``AssetInfo.pathHashHead`` and advances by 24; the
  bundle validation lookup reads ``Bundle.hashName`` and advances by 48; both
  pick a slot by unsigned comparer hash modulo capacity. Every slot range
  lands on its value stride, the ranges cover each value once, and every
  stored key maps back to its own slot.
* ``Bundle`` fields, in order: ``bundleIndex``, ``name``, ``dependencies``,
  ``directReverseDependencies``, ``directDependencies``, ``bundleFlags``,
  ``hashName``, ``hashVersion``, ``category``. Dictionary values store
  ``bundleIndex`` zero while the indexed array stores the ordinal; both join
  on name, lists, flags, hash and category. ``AssetInfo`` holds
  ``pathHashHead``, ``path``, ``bundleIndex`` and ``assetSize``, and every
  asset ``bundleIndex`` is inside the indexed array.
* The ``Bundle.Convert`` writer binds the counted lists to source ``deps``,
  ``directReverseDeps`` and ``directDeps``, sets ``hashVersion`` from
  ``hashName`` and XORs in a fixed multiple of each dependency's native name
  hash; the dependency string wrapper hashes raw UTF-16 code units with no
  case conversion. Replaying that fold reproduces every stored
  ``hashVersion``, and because the folded ``deps`` list is the transitive
  closure (``bundle_cab_dependency_corpus``) the version hash covers every
  reachable dependency name.
* ``AssetInfo.path`` offsets tile the terminal suffix as length-prefixed
  Brotli records with two zero terminator bytes; each decodes to strict
  UTF-16LE through ``RefCompressString``. The asset writer hashes its source
  path after ``ToLow``, and the replayed recurrence reproduces every
  ``pathHashHead``. Repeated decoded paths repeat hash, bundle index and size
  at different raw offsets, so repetition adds no bundle association.
* Both ``BundleLoader+Manager`` proxy loaders call
  ``RuntimeManifestBinary.TryGetBundleDirectDeps``, read a loop element later
  in the body and recurse into the same loader: a direct static consumer of
  the stored direct list, without a live branch or ref/out capture.

Not established: case handling for unseen names (current paths carry no ASCII
uppercase witness), the Burst hash path, runtime comparisons, which loader
branch runs, and Unity object ownership. Unresolved stream and ref/out
carriers still block a safe live lookup capture.

Pass the same dumped ``manifest.hgmmap`` the corpus gate reads; ``--output
reports/animestudio/bundle_manifest_native_latest.json`` saves the report.
"""

from __future__ import annotations

if __name__ == "__main__" and not __package__:
    raise SystemExit("Run as: python -m scripts.game_data.bundle_manifest_native")

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file
from scripts.game_data.bundle_manifest import parse_decompressed_bundle_manifest
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets, runtime_type_name


CONTRACT = CONTRACTS_DIR / "bundle_manifest_native.json"
SCHEMA = "endfield.bundle-manifest-native-contract.v4"


def _require(condition: bool, check: str) -> None:
    if not condition:
        raise ValueError(f"bundle-manifest-native:{check}")


def _field_offsets(image: Any, spec: dict[str, Any]) -> dict[str, int]:
    definition = spec["index"]
    _require(image.type_name(definition) == spec["name"], "type-identity")
    offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, definition)
    for name, expected in spec["fieldOffsets"].items():
        _require(offsets.get(name) == expected, f"field-offset:{spec['name']}.{name}")
    return offsets


def _check_field_types(image: Any, spec: dict[str, Any]) -> None:
    definition = image.metadata.types[spec["index"]]
    fields = list(image.metadata.fields_for(definition))
    for name, expected_type in spec.get("fieldTypes", {}).items():
        matching = [field for field in fields if image.metadata.string(field.name_index) == name]
        _require(len(matching) == 1, f"field-selection:{spec['name']}.{name}")
        type_va = image.pe.u64_at_va(int(image.registration["types"], 16) + matching[0].type_index * 8)
        _require(runtime_type_name(image.pe, image.metadata, type_va) == expected_type,
                 f"field-type:{spec['name']}.{name}")


def _method_rva(contract: dict[str, Any], name: str, type_name: str | None = None) -> int:
    matches = [row[3] for row in contract["methods"]
               if row[2] == name and (type_name is None or row[1] == type_name)]
    _require(len(matches) == 1, f"method-selection:{type_name or '*'}:{name}")
    return matches[0]


def _read(image: Any, rva: int, size: int) -> bytes:
    return image.pe.bytes_at_va(image.pe.image_base + rva, size)


def _check_field_instruction(image: Any, rva: int, *, opcode: bytes, expected_offset: int, label: str) -> None:
    raw = _read(image, rva, len(opcode) + 4)
    _require(raw.startswith(opcode), f"{label}:opcode")
    _require(struct.unpack_from("<I", raw, len(opcode))[0] == expected_offset, f"{label}:offset")


def _check_lea(image: Any, rva: int, offset: int, *, label: str) -> None:
    _require(_read(image, rva, 4) == b"\x48\x8d\x4f" + bytes([offset]), f"{label}:destination")


def _call_target(image: Any, rva: int) -> int:
    raw = _read(image, rva, 5)
    _require(raw[0] == 0xE8, f"call-opcode:{rva:#x}")
    return rva + 5 + struct.unpack_from("<i", raw, 1)[0]


def _jump_target(image: Any, rva: int) -> int:
    raw = _read(image, rva, 5)
    _require(raw[0] == 0xE9, f"jump-opcode:{rva:#x}")
    return rva + 5 + struct.unpack_from("<i", raw, 1)[0]


def _check_dependency_string_hash(image: Any, contract: dict[str, Any], windows: dict[str, Any]) -> dict[str, Any]:
    spec = contract["dependencyStringHash"]
    wrapper = windows[spec["wrapperRole"]]
    burst = windows[spec["burstInvokeRole"]]
    fallback = windows[spec["managedFallbackRole"]]
    _require(wrapper["startRva"] == contract["writer"]["versionFold"]["dependencyNameHashCalleeRva"],
             "utf16-wrapper-entry")
    _require(_read(image, spec["wrapperCharDataLeaRva"], 4)
             == b"\x48\x8d\x59" + bytes([spec["stringCharDataOffset"]]),
             "utf16-wrapper-char-pointer")
    _require(_jump_target(image, spec["wrapperBurstJumpRva"]) == burst["startRva"],
             "utf16-burst-call-route")
    _require(fallback["startRva"] == _method_rva(contract, "HashCodeEx4UTF16$BurstManaged"),
             "utf16-fallback-method")
    _require(_read(image, spec["seedRva"], 5) == b"\xba" + struct.pack("<I", spec["seed"]),
             "utf16-seed")
    _require(_read(image, spec["laneMultiplyRva"], 4)
             == b"\x48\x6b\xc2" + bytes([spec["laneMultiplier"]]),
             "utf16-lane-multiplier")
    _require(_read(image, spec["finalMultiplyRva"], 7)
             == b"\x49\x69\xc0" + struct.pack("<I", spec["finalMultiplier"]),
             "utf16-final-multiplier")
    mask = int(spec["resultMaskHex"], 16)
    _require(_read(image, spec["resultMaskRva"], 10) == b"\x49\xba" + struct.pack("<Q", mask),
             "utf16-result-mask")
    _require(mask > 0 and (mask & (mask + 1)) == 0, "utf16-mask-shape")
    _require(spec["emptyStringResult"] == 0, "utf16-empty-result")
    return {
        "sourceField": spec["sourceField"],
        "inputNormalization": spec["inputNormalization"],
        "seed": spec["seed"],
        "laneMultiplier": spec["laneMultiplier"],
        "finalMultiplier": spec["finalMultiplier"],
        "resultMaskHex": spec["resultMaskHex"],
        "emptyStringResult": spec["emptyStringResult"],
        "evidenceBoundary": spec["evidenceBoundary"],
    }


def _check_writer(image: Any, contract: dict[str, Any], bundle: dict[str, int]) -> dict[str, Any]:
    raw = _field_offsets(image, contract["rawBundleType"])
    header = contract["bundleType"]["boxedValueHeaderBytes"]
    writer = contract["writer"]
    name_hash = writer["nameHash"]
    source_name = raw[name_hash["sourceField"]]
    target_hash = bundle[name_hash["targetField"]] - header
    _require(_read(image, name_hash["sourceReadRva"], 4) == b"\x48\x8b\x5e" + bytes([source_name]),
             "writer:name-read")
    _require(_call_target(image, name_hash["hashCallRva"]) == name_hash["hashCalleeRva"],
             "writer:name-hash-call")
    _require(_read(image, name_hash["targetStoreRva"], 4) == b"\x48\x89\x47" + bytes([target_hash]),
             "writer:name-hash-store")

    list_bindings: list[dict[str, Any]] = []
    for binding in writer["listBindings"]:
        source_offset = raw[binding["sourceField"]]
        target_offset = bundle[binding["targetField"]] - header
        _require(_read(image, binding["sourceReadRva"], 4) == b"\x4c\x8b\x6e" + bytes([source_offset]),
                 f"writer:{binding['sourceField']}:source-read")
        _require(_read(image, binding["targetStoreRva"], 3) == b"\x89\x47" + bytes([target_offset]),
                 f"writer:{binding['targetField']}:target-store")
        list_bindings.append({"sourceField": binding["sourceField"], "bundleField": binding["targetField"],
                              "bundleRowOffset": target_offset})

    fold = writer["versionFold"]
    initial_offset = bundle[fold["initialField"]] - header
    target_offset = bundle[fold["targetField"]] - header
    source_offset = raw[fold["sourceField"]]
    _require(_read(image, fold["sourceReadRva"], 4) == b"\x4c\x8b\x67" + bytes([initial_offset]),
             "writer:fold-initial-read")
    _require(_read(image, fold["arrayReadRva"], 4) == b"\x48\x8b\x76" + bytes([source_offset]),
             "writer:fold-dependencies-read")
    _require(_read(image, fold["dependencyNameReadRva"], 4) == b"\x48\x8b\x49" + bytes([raw[name_hash["sourceField"]]]),
             "writer:dependency-name-read")
    _require(_call_target(image, fold["dependencyNameHashCallRva"]) == fold["dependencyNameHashCalleeRva"],
             "writer:dependency-name-hash-call")
    multiply = _read(image, fold["multiplyRva"], 4)
    _require(multiply[:3] == b"\x48\x6b\xc8" and multiply[3] == fold["multiplier"],
             "writer:fold-multiplier")
    _require(_read(image, fold["xorRva"], 3) == b"\x4c\x33\xe1", "writer:fold-xor")
    _require(_read(image, fold["targetStoreRva"], 4) == b"\x4c\x89\x67" + bytes([target_offset]),
             "writer:fold-store")
    return {
        "nameHashSourceField": name_hash["sourceField"],
        "nameHashBundleField": name_hash["targetField"],
        "listBindings": list_bindings,
        "hashVersionFold": {
            "initialBundleField": fold["initialField"],
            "dependencyIndexSourceField": fold["sourceField"],
            "dependencyNameSourceField": name_hash["sourceField"],
            "dependencyNameHashCalleeRva": fold["dependencyNameHashCalleeRva"],
            "multiplier": fold["multiplier"],
            "combine": "xor",
            "targetBundleField": fold["targetField"],
            "evidenceBoundary": fold["boundary"],
        },
    }


def _check_dictionary_native(
    image: Any, contract: dict[str, Any], owner: dict[str, int], bundle: dict[str, int],
    windows: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    asset_spec = contract["assetInfoType"]
    asset = _field_offsets(image, asset_spec)
    raw_asset = _field_offsets(image, contract["rawAssetInfoBinaryType"])
    ref_string_spec = contract["refCompressStringType"]
    ref_string = _field_offsets(image, ref_string_spec)
    _check_field_types(image, asset_spec)
    asset_fields = {name: offset - asset_spec["boxedValueHeaderBytes"]
                    for name, offset in asset.items() if name in asset_spec["fieldOffsets"]}
    bundle_fields = {name: offset - contract["bundleType"]["boxedValueHeaderBytes"]
                     for name, offset in bundle.items() if name in contract["bundleType"]["fieldOffsets"]}
    _require(all(0 <= offset < asset_spec["valueBytes"] for offset in asset_fields.values()),
             "asset-value-field-bounds")
    sections = []
    by_table = {binding["table"]: binding for binding in contract["sectionBindings"]}
    for spec in contract["dictionarySections"]:
        type_spec = contract[spec["valueType"]]
        expected_value_bytes = type_spec.get("valueBytes", type_spec.get("rowBytes"))
        _require(spec["valueBytes"] == expected_value_bytes, f"{spec['table']}:value-width")
        _require(spec["destinationField"] == by_table[spec["table"]]["destinationField"],
                 f"{spec['table']}:owner-field")
        fields = asset_fields if spec["valueType"] == "assetInfoType" else bundle_fields
        _require(spec["keyField"] in fields, f"{spec['table']}:key-field")
        _require(fields[spec["keyField"]] + 8 <= spec["valueBytes"], f"{spec['table']}:key-bounds")
        sections.append({
            "table": spec["table"], "destinationField": spec["destinationField"],
            "slotBytes": spec["slotBytes"], "valueBytes": spec["valueBytes"],
            "valueType": type_spec["name"], "valueFieldOffsets": fields,
            "keyField": spec["keyField"], "keyOffset": fields[spec["keyField"]],
            "evidenceBoundary": spec["evidenceBoundary"],
        })
    _require({row["table"] for row in sections} == {"fixed-width-32", "fixed-width-56"},
             "dictionary-section-set")
    by_section = {spec["table"]: spec for spec in contract["dictionarySections"]}
    _require(len(by_section) == len(contract["dictionarySections"]), "dictionary-section-unique")
    asset_section = by_section["fixed-width-32"]
    bundle_section = by_section["fixed-width-56"]
    _require(asset_section["paddingBytes"] == asset_section["valueBytes"] - asset_fields["assetSize"] - 4,
             "asset-value:padding-width")

    writer = contract["assetValueWriter"]
    _require(writer["sourceType"] == "rawAssetInfoBinaryType"
             and windows["assetInfoWriter"]["startRva"] == _method_rva(contract, "Convert", asset_spec["name"]),
             "asset-writer:method")
    _require(_read(image, writer["sourcePathReadRva"], 4)
             == b"\x48\x8b\x4f" + bytes([raw_asset[writer["sourcePathField"]]]),
             "asset-writer:path-read")
    _require(_call_target(image, writer["toLowCallRva"]) == _method_rva(contract, "ToLow"),
             "asset-writer:to-low")
    _require(_call_target(image, writer["hashCallRva"]) == writer["hashCalleeRva"]
             == windows[contract["dependencyStringHash"]["wrapperRole"]]["startRva"],
             "asset-writer:hash-call")
    _require(asset_fields[writer["targetPathHashField"]] == 0
             and _read(image, writer["hashStoreRva"], 3) == b"\x48\x89\x03",
             "asset-writer:hash-store")
    _require(_read(image, writer["pathStoreRva"], 3)
             == b"\x89\x43" + bytes([asset_fields[writer["targetPathField"]]]),
             "asset-writer:path-store")
    for field in writer["integerFields"]:
        _require(_read(image, field["sourceReadRva"], 3)
                 == b"\x8b\x47" + bytes([raw_asset[field["sourceField"]]]),
                 f"asset-writer:{field['sourceField']}:read")
        _require(_read(image, field["targetStoreRva"], 3)
                 == b"\x89\x43" + bytes([asset_fields[field["targetField"]]]),
                 f"asset-writer:{field['targetField']}:store")

    a = contract["dictionaryReaders"]["asset"]
    _require(windows[a["pathLookupRole"]]["startRva"] == _method_rva(contract, "TryGetValue"),
             "asset-lookup:method")
    _require(_read(image, a["ownerLeaRva"], 4)
             == b"\x48\x8d\x4b" + bytes([owner[a["ownerField"]]]), "asset-lookup:owner")
    _require(_call_target(image, a["slotCallRva"]) == windows[a["slotSelectorRole"]]["startRva"],
             "asset-lookup:slot-selector")
    _require(_call_target(image, a["valueCallRva"]) == windows[a["valueLookupRole"]]["startRva"],
             "asset-lookup:value-reader")
    _require(_read(image, a["slotSelectorDivRva"], 3) == b"\x48\xf7\xf1", "asset-slot:modulo")
    _require(_read(image, a["slotSelectorShiftRva"], 3)
             == b"\xc1\xe2" + bytes([asset_section["slotBytes"].bit_length() - 1]),
             "asset-slot:width")
    _require(_read(image, a["slotSelectorBaseRva"], 4) == b"\x48\x03\x43\x10", "asset-slot:base")
    _require(_read(image, a["valueCountReadRva"], 4) == b"\x44\x3b\x52\x04", "asset-value:slot-count")
    _require(_read(image, a["valueOffsetReadRva"], 3) == b"\x48\x63\x02", "asset-value:slot-offset")
    _require(_read(image, a["valueBaseReadRva"], 7)
             == b"\x48\x03\x81" + struct.pack("<I", owner[a["ownerDataField"]]),
             "asset-value:section-base")
    _require(asset_fields[asset_section["keyField"]] == 0
             and _read(image, a["keyCompareRva"], 3) == b"\x4c\x39\x00",
             "asset-value:key-compare")
    _require(_read(image, a["valueStrideRva"], 4)
             == b"\x49\x83\xc3" + bytes([asset_spec["valueBytes"]]), "asset-value:stride")

    b = contract["dictionaryReaders"]["bundle"]
    _require(windows[b["callerRole"]]["startRva"] == _method_rva(contract, "ValidCheck"),
             "bundle-lookup:caller")
    _check_lea(image, b["ownerLeaRva"], owner[b["ownerField"]], label="bundle-lookup")
    _require(_read(image, b["arrayKeyLoadRva"], 5)
             == b"\x48\x8b\x54\x13" + bytes([bundle_fields["hashName"]]),
             "bundle-lookup:array-key")
    _require(_read(image, b["keyFieldOffsetSetRva"], 6)
             == b"\x41\xb9" + struct.pack("<I", bundle_fields["hashName"]),
             "bundle-lookup:key-offset")
    _require(_call_target(image, b["lookupCallRva"]) == windows[b["valueLookupRole"]]["startRva"],
             "bundle-lookup:call")
    for label, rva, expected in (
        ("capacity", b["capacityReadRva"], b"\x49\x63\x0e"),
        ("modulo", b["slotDivRva"], b"\x48\xf7\xf1"),
        ("slot-base", b["slotBaseRva"], b"\x4d\x03\x7e\x10"),
        ("slot-count", b["slotCountReadRva"], b"\x41\x3b\x47\x04"),
        ("value-base", b["valueBaseReadRva"], b"\x4d\x8b\x66\x08"),
        ("value-offset", b["valueOffsetReadRva"], b"\x4d\x63\x2f"),
        ("key-offset", b["keyFieldOffsetReadRva"], b"\x48\x63\x44\x24\x68"),
        ("key-compare", b["keyCompareRva"], b"\x48\x39\x1c\x08"),
    ):
        _require(_read(image, rva, len(expected)) == expected, f"bundle-value:{label}")
    _require(_read(image, b["slotShiftRva"], 3)
             == b"\xc1\xe2" + bytes([bundle_section["slotBytes"].bit_length() - 1]),
             "bundle-value:slot-width")
    _require(_read(image, b["valueStrideRva"], 4)
             == b"\x48\x83\xc7" + bytes([contract["bundleType"]["rowBytes"]]),
             "bundle-value:stride")
    _require(image.window_bytes(windows["longKeyComparer"]) == b"\x48\x8b\xc2\xc3",
             "bundle-value:comparer")

    path = contract["assetPathPayload"]
    _require(windows[path["initRole"]]["startRva"] == _method_rva(contract, "Init")
             and windows[path["toStringRole"]]["startRva"] == _method_rva(contract, "ToString"),
             "asset-path:reader-methods")
    _require(ref_string["length"] - ref_string_spec["boxedValueHeaderBytes"] == 0
             and ref_string["head"] - ref_string_spec["boxedValueHeaderBytes"] == path["lengthBytes"],
             "asset-path:ref-layout")
    _require(_read(image, path["initLengthReadRva"], 2) == b"\x8b\x03", "asset-path:length-read")
    _require(_read(image, path["initBodyLeaRva"], 4)
             == b"\x48\x83\xc3" + bytes([path["lengthBytes"]]), "asset-path:body-pointer")
    _require(_read(image, path["initBodyStoreRva"], 4)
             == b"\x48\x89\x5f" + bytes([path["lengthBytes"]]), "asset-path:body-store")
    _require(_call_target(image, path["decompressCallRva"]) == _method_rva(contract, "DecompressBrotli"),
             "asset-path:brotli-reader")
    return sections, asset_fields


def _check_native(image: Any, contract: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, int]]:
    owner = _field_offsets(image, contract["ownerType"])
    bundle = _field_offsets(image, contract["bundleType"])
    for row in contract["methods"]:
        image.validate_method_row(row, label="bundle-manifest-native")
    windows = {row["role"]: row for row in contract["codeWindows"]}
    image.check_windows(list(windows.values()), label="bundle-manifest-native")

    bundle_spec = contract["bundleType"]
    header_bytes = bundle_spec["boxedValueHeaderBytes"]
    _require(bundle_spec["rowBytes"] == contract["bundleCopy"]["rowBytes"], "bundle-row-width")
    projected_fields = {
        name: offset - header_bytes for name, offset in bundle.items()
        if name in bundle_spec["fieldOffsets"]
    }
    _require(all(0 <= offset < bundle_spec["rowBytes"] for offset in projected_fields.values()), "bundle-field-bounds")
    _check_field_types(image, bundle_spec)

    stride = contract["bundleCopy"]["strideRva"]
    stride_bytes = _read(image, stride, 6)
    _require(stride_bytes[:5] == b"\x8d\x04\x5b\xc1\xe0", "bundle-stride-instruction")
    _require(3 * (1 << stride_bytes[5]) == bundle_spec["rowBytes"], "bundle-stride-width")
    _require(_read(image, contract["bundleCopy"]["sourceLoadRva"], 4)
             == b"\x48\x8b\x47" + bytes([
                 owner[contract["bundleCopy"]["sourceField"]]
                 + contract["bundleCopy"]["sourcePointerBias"]
             ]),
             "bundle-copy-source")

    bindings: list[dict[str, Any]] = []
    for binding in contract["sectionBindings"]:
        source = binding["sourceAddressField"]
        destination = binding["destinationField"]
        _check_field_instruction(image, binding["sourceStoreRva"], opcode=b"\x48\x89\x9f",
                                 expected_offset=owner[source], label=f"{binding['table']}:source-store")
        _check_field_instruction(image, binding["sourceLoadRva"], opcode=b"\x48\x8b\x97",
                                 expected_offset=owner[source], label=f"{binding['table']}:source-load")
        _check_lea(image, binding["destinationLeaRva"], owner[destination], label=binding["table"])
        _require(_call_target(image, binding["helperCallRva"]) == windows[binding["helperRole"]]["startRva"],
                 f"{binding['table']}:helper-call")
        helper = windows[binding["helperRole"]]
        helper_bytes = image.window_bytes(helper)
        bias_instruction = helper_bytes.find(b"\x48\x83\xc7")
        _require(b"\x8b\x07" in helper_bytes and 0 <= bias_instruction < len(helper_bytes) - 3,
                 f"{binding['table']}:count-and-row-bias")
        _require(binding["rowDataBias"] == helper_bytes[bias_instruction + 3],
                 f"{binding['table']}:row-data-bias")
        bindings.append({
            "table": binding["table"],
            "sourceAddressField": source,
            "destinationField": destination,
            "rowDataBias": binding["rowDataBias"],
            "evidenceBoundary": binding["boundary"],
        })
    _require({row["table"] for row in bindings} == {"fixed-width-32", "fixed-width-56", "fixed-width-48"},
             "section-binding-set")
    writer = _check_writer(image, contract, bundle)
    string_hash = _check_dependency_string_hash(image, contract, windows)
    _require(string_hash["sourceField"] == writer["hashVersionFold"]["dependencyNameSourceField"],
             "utf16-source-field")
    dictionaries, asset_fields = _check_dictionary_native(image, contract, owner, bundle, windows)
    return bindings, writer, string_hash, dictionaries, asset_fields


def _check_runtime_dependency_consumers(image: Any, contract: dict[str, Any]) -> dict[str, Any]:
    """Authenticate both proxy loaders' accessor call and later recursive loop."""

    spec = contract["runtimeDependencyConsumers"]
    accessor = _method_rva(contract, spec["accessorMethod"], spec["accessorType"])
    extents = image.mapper.pdata_function_extents(image.pe)
    rows = []
    _require(len(spec["loaders"]) == 2, "runtime-consumer-count")
    for row in spec["loaders"]:
        start = _method_rva(contract, row["method"], row["type"])
        end_va = extents.get(image.pe.image_base + start)
        _require(end_va is not None, f"runtime-consumer-extent:{row['method']}")
        end = end_va - image.pe.image_base
        read = row["directDepsCallRva"]
        element = row["loopElementLoadRva"]
        recurse = row["recursiveCallRva"]
        _require(start <= read < element < recurse < end,
                 f"runtime-consumer-order:{row['method']}")
        _require(_call_target(image, read) == accessor,
                 f"runtime-consumer-accessor:{row['method']}")
        element_hex = bytes.fromhex(row["loopElementLoadHex"])
        _require(_read(image, element, len(element_hex)) == element_hex,
                 f"runtime-consumer-loop-element:{row['method']}")
        _require(_call_target(image, recurse) == start,
                 f"runtime-consumer-recursion:{row['method']}")
        rows.append({
            "type": row["type"], "method": row["method"],
            "calls": spec["accessorType"] + "." + spec["accessorMethod"],
            "loopElementReadThenSelfRecursion": True,
            "evidenceBoundary": spec["evidenceBoundary"],
        })
    return {"loaders": rows, "semanticLimit": spec["semanticLimit"]}


def _hash_utf16_component(payload: memoryview, offset: int, spec: dict[str, Any]) -> int:
    byte_length = struct.unpack_from("<I", payload, offset)[0]
    if byte_length == 0:
        return spec["emptyStringResult"]
    cursor = offset + 4
    end = cursor + byte_length
    mask = int(spec["resultMaskHex"], 16)
    first_lane = second_lane = spec["seed"]
    while cursor < end:
        first = struct.unpack_from("<h", payload, cursor)[0]
        if first == 0:
            break
        first_lane = ((first_lane * spec["laneMultiplier"]) ^ (first & mask)) & mask
        cursor += 2
        if cursor >= end:
            break
        second = struct.unpack_from("<h", payload, cursor)[0]
        if second == 0:
            break
        second_lane = ((second_lane * spec["laneMultiplier"]) ^ (second & mask)) & mask
        cursor += 2
    return (second_lane * spec["finalMultiplier"] + first_lane) & mask


def _replay_hash_version(decoded: bytes, parsed: Any, contract: dict[str, Any], fields: dict[str, int]) -> dict[str, Any]:
    table = next(table for table in parsed.tables if table.name == "fixed-width-48")
    payload = memoryview(decoded)[parsed.variable_region.payload_offset:parsed.variable_region.footer_offset]
    rows: list[tuple[int, int, int, tuple[int, ...]]] = []
    referenced: set[int] = set()
    for index in range(table.row_count):
        row_offset = table.offset + index * table.row_size
        name_offset = struct.unpack_from("<I", decoded, row_offset + fields["name"])[0]
        dependencies_offset = struct.unpack_from("<I", decoded, row_offset + fields["dependencies"])[0]
        name_hash = struct.unpack_from("<Q", decoded, row_offset + fields["hashName"])[0]
        version_hash = struct.unpack_from("<Q", decoded, row_offset + fields["hashVersion"])[0]
        count = struct.unpack_from("<I", payload, dependencies_offset)[0]
        dependencies = struct.unpack_from(f"<{count}I", payload, dependencies_offset + 4) if count else ()
        rows.append((name_offset, name_hash, version_hash, dependencies))
        referenced.update(dependencies)
    _require(all(0 <= index < table.row_count for index in referenced), "dependency-index-bounds")
    string_spec = contract["dependencyStringHash"]
    hashes: dict[int, int] = {}
    uppercase_names = 0
    for index in referenced:
        name_offset = rows[index][0]
        hashes[index] = _hash_utf16_component(payload, name_offset, string_spec)
        byte_length = struct.unpack_from("<I", payload, name_offset)[0]
        uppercase_names += any(
            65 <= struct.unpack_from("<H", payload, name_offset + 4 + byte_offset)[0] <= 90
            for byte_offset in range(0, byte_length, 2)
        )
    fold_multiplier = contract["writer"]["versionFold"]["multiplier"]
    reproduced = 0
    zero_deps = 0
    for index, (_name_offset, name_hash, version_hash, dependencies) in enumerate(rows):
        predicted = name_hash
        zero_deps += not dependencies
        for dependency in dependencies:
            predicted ^= fold_multiplier * hashes[dependency] & ((1 << 64) - 1)
        if predicted != version_hash:
            raise ValueError(
                f"bundle-manifest-native:version-replay:row={index} "
                f"expected={version_hash:016X} actual={predicted:016X} "
                f"decompressedSha256={parsed.decompressed_sha256.upper()}"
            )
        reproduced += 1
    return {
        "rowCount": table.row_count,
        "referencedDependencyNameCount": len(referenced),
        "referencedDependencyNamesWithAsciiUppercase": uppercase_names,
        "zeroDependencyRows": zero_deps,
        "hashVersionReproduced": reproduced,
        "evidenceBoundary": "conditional",
    }


def _checked_u32(buffer: memoryview, offset: int, end: int, label: str) -> int:
    _require(0 <= offset <= end - 4, f"{label}:u32-bounds")
    return struct.unpack_from("<I", buffer, offset)[0]


def _bundle_record(
    payload: memoryview, row: memoryview, fields: dict[str, int], limit: int, label: str,
) -> tuple[str, tuple[tuple[int, ...], ...], int]:
    start = struct.unpack_from("<I", row, fields["name"])[0]
    length = _checked_u32(payload, start, limit, f"{label}:name-length")
    _require(length > 0 and length % 2 == 0 and start + 4 + length + 2 <= limit,
             f"{label}:name-bounds")
    name = payload[start + 4:start + 4 + length].tobytes().decode("utf-16-le", errors="strict")
    cursor = start + 4 + length
    _require(payload[cursor:cursor + 2].tobytes() == b"\x00\x00", f"{label}:name-terminator")
    cursor += 2
    lists: list[tuple[int, ...]] = []
    for field in ("dependencies", "directReverseDependencies", "directDependencies"):
        pointer = struct.unpack_from("<I", row, fields[field])[0]
        _require(pointer == cursor, f"{label}:{field}:pointer")
        count = _checked_u32(payload, pointer, limit, f"{label}:{field}:count")
        _require(count <= (limit - pointer - 6) // 4, f"{label}:{field}:bounds")
        lists.append(struct.unpack_from(f"<{count}I", payload, pointer + 4) if count else ())
        cursor = pointer + 4 + count * 4
        _require(payload[cursor:cursor + 2].tobytes() == b"\x00\x00", f"{label}:{field}:terminator")
        cursor += 2
    return name, tuple(lists), cursor


def _replay_dictionary_sections(
    decoded: bytes, parsed: Any, contract: dict[str, Any],
    bundle_fields: dict[str, int], asset_fields: dict[str, int],
) -> dict[str, Any]:
    table_by_name = {table.name: table for table in parsed.tables}
    data = memoryview(decoded)
    payload = data[parsed.variable_region.payload_offset:parsed.variable_region.footer_offset]
    layouts: dict[str, dict[str, Any]] = {}
    by_section = {spec["table"]: spec for spec in contract["dictionarySections"]}
    _require(len(by_section) == len(contract["dictionarySections"]), "dictionary-section-unique")
    for spec in contract["dictionarySections"]:
        table = table_by_name[spec["table"]]
        capacity = table.row_count
        slot_bytes = spec["slotBytes"]
        value_bytes = spec["valueBytes"]
        _require(capacity > 0 and slot_bytes == 8 and table.row_size == slot_bytes + value_bytes,
                 f"{table.name}:split-width")
        base = table.section_offset + 4
        _require(struct.unpack_from("<I", decoded, base)[0] == capacity, f"{table.name}:capacity")
        slots_start = table.offset
        values_start = slots_start + capacity * slot_bytes
        values_end = values_start + capacity * value_bytes
        _require(values_end == table.offset + table.byte_length, f"{table.name}:split-end")
        fields = asset_fields if spec["valueType"] == "assetInfoType" else bundle_fields
        key_offset = fields[spec["keyField"]]
        _require(key_offset + 8 <= value_bytes, f"{table.name}:key-bounds")
        seen = bytearray(capacity)
        occupied = max_count = 0
        for slot_index in range(capacity):
            relative_offset, count = struct.unpack_from("<II", data, slots_start + slot_index * slot_bytes)
            if count == 0:
                _require(relative_offset == 0, f"{table.name}:empty-slot:{slot_index}")
                continue
            occupied += 1
            max_count = max(max_count, count)
            first = base + relative_offset
            _require(values_start <= first < values_end and (first - values_start) % value_bytes == 0
                     and count <= (values_end - first) // value_bytes,
                     f"{table.name}:slot-range:{slot_index}")
            value_index = (first - values_start) // value_bytes
            for index in range(value_index, value_index + count):
                _require(not seen[index], f"{table.name}:overlap:{slot_index}:{index}")
                seen[index] = 1
                hash_key = struct.unpack_from("<Q", data, values_start + index * value_bytes + key_offset)[0]
                _require(hash_key % capacity == slot_index,
                         f"{table.name}:key-modulo:{slot_index}:{index}")
        _require(sum(seen) == capacity, f"{table.name}:unreferenced-values")
        layouts[table.name] = {
            "capacity": capacity, "slotBytes": slot_bytes, "valueBytes": value_bytes,
            "slotStart": slots_start, "valueStart": values_start, "valueEnd": values_end,
            "occupiedSlots": occupied, "emptySlots": capacity - occupied,
            "maxSlotValueCount": max_count, "coveredValues": sum(seen),
            "hashModuloMatches": capacity,
        }

    array_table = table_by_name["fixed-width-48"]
    bundle_layout = layouts["fixed-width-56"]
    asset_layout = layouts["fixed-width-32"]
    asset_section = by_section["fixed-width-32"]
    indexed_end = parsed.variable_region.opaque_suffix_offset
    array_by_name: dict[str, int] = {}
    for index in range(array_table.row_count):
        offset = array_table.offset + index * array_table.row_size
        row = data[offset:offset + array_table.row_size]
        _require(struct.unpack_from("<I", row, bundle_fields["bundleIndex"])[0] == index,
                 f"bundle-array:index:{index}")
        name, _, _ = _bundle_record(payload, row, bundle_fields, indexed_end, f"bundle-array:{index}")
        _require(name not in array_by_name, f"bundle-array:duplicate-name:{index}")
        array_by_name[name] = index
    _require(len(array_by_name) == bundle_layout["capacity"], "bundle-array:name-count")

    sequential_cursor = 0
    joined_names: set[str] = set()
    for index in range(bundle_layout["capacity"]):
        offset = bundle_layout["valueStart"] + index * bundle_layout["valueBytes"]
        row = data[offset:offset + bundle_layout["valueBytes"]]
        _require(struct.unpack_from("<I", row, bundle_fields["name"])[0] == sequential_cursor,
                 f"bundle-dictionary:sequential-pointer:{index}")
        name, lists, sequential_cursor = _bundle_record(
            payload, row, bundle_fields, parsed.variable_region.indexed_region_offset,
            f"bundle-dictionary:{index}",
        )
        array_index = array_by_name.get(name)
        _require(array_index is not None, f"bundle-dictionary:name-join:{index}")
        _require(name not in joined_names, f"bundle-dictionary:duplicate-name:{index}")
        joined_names.add(name)
        array_offset = array_table.offset + array_index * array_table.row_size
        array_row = data[array_offset:array_offset + array_table.row_size]
        _, array_lists, _ = _bundle_record(payload, array_row, bundle_fields, indexed_end,
                                           f"bundle-array-join:{array_index}")
        _require(lists == array_lists, f"bundle-dictionary:list-join:{index}")
        _require(row[bundle_fields["bundleFlags"]:].tobytes()
                 == array_row[bundle_fields["bundleFlags"]:].tobytes(),
                 f"bundle-dictionary:scalar-join:{index}")
        _require(struct.unpack_from("<I", row, bundle_fields["bundleIndex"])[0] == 0,
                 f"bundle-dictionary:index:{index}")
    _require(sequential_cursor == parsed.variable_region.indexed_region_offset,
             "bundle-dictionary:sequential-end")
    _require(len(joined_names) == array_table.row_count, "bundle-dictionary:complete-name-join")

    path_spec = contract["assetPathPayload"]
    _require(path_spec["codec"] == "brotli" and path_spec["decodedEncoding"] == "utf-16-le",
             "asset-path:codec-contract")
    terminator = bytes.fromhex(path_spec["terminatorHex"])
    _require(path_spec["lengthBytes"] == 4 and len(terminator) == 2, "asset-path:record-shape")
    suffix_start = parsed.variable_region.opaque_suffix_offset
    suffix_end = len(payload)
    path_rows = []
    for index in range(asset_layout["capacity"]):
        offset = asset_layout["valueStart"] + index * asset_layout["valueBytes"]
        row = data[offset:offset + asset_layout["valueBytes"]]
        path_offset = struct.unpack_from("<I", row, asset_fields[path_spec["referenceField"]])[0]
        bundle_index = struct.unpack_from("<I", row, asset_fields["bundleIndex"])[0]
        _require(bundle_index < array_table.row_count, f"asset-value:bundle-index:{index}")
        padding_bytes = asset_section["paddingBytes"]
        _require(row[-padding_bytes:].tobytes() == bytes(padding_bytes),
                 f"asset-value:padding:{index}")
        _require(suffix_start <= path_offset < suffix_end, f"asset-value:path-pointer:{index}")
        path_rows.append((path_offset, index, offset))
    path_rows.sort()
    _require(len({row[0] for row in path_rows}) == len(path_rows), "asset-path:duplicate-offset")
    _require(path_rows[0][0] == suffix_start, "asset-path:suffix-start")
    import brotli

    unique_paths: set[str] = set()
    uppercase_paths = 0
    decoded_bytes = 0
    for order, (path_offset, index, value_offset) in enumerate(path_rows):
        length = _checked_u32(payload, path_offset, suffix_end, f"asset-path:{index}:length")
        record_end = path_offset + path_spec["lengthBytes"] + length + len(terminator)
        expected_end = path_rows[order + 1][0] if order + 1 < len(path_rows) else suffix_end
        _require(record_end == expected_end, f"asset-path:tiling:{index}")
        _require(payload[record_end - len(terminator):record_end].tobytes() == terminator,
                 f"asset-path:terminator:{index}")
        compressed = payload[path_offset + path_spec["lengthBytes"]:record_end - len(terminator)]
        decoded_path = brotli.decompress(compressed)
        _require(len(decoded_path) > 0 and len(decoded_path) % 2 == 0,
                 f"asset-path:utf16-width:{index}")
        path = decoded_path.decode(path_spec["decodedEncoding"], errors="strict")
        _require("\x00" not in path, f"asset-path:nul:{index}")
        uppercase_paths += any("A" <= char <= "Z" for char in path)
        unique_paths.add(path)
        decoded_bytes += len(decoded_path)
        expected_hash = struct.unpack_from("<Q", data, value_offset + asset_fields["pathHashHead"])[0]
        actual_hash = _hash_utf16_component(
            memoryview(struct.pack("<I", len(decoded_path)) + decoded_path), 0,
            contract["dependencyStringHash"],
        )
        _require(actual_hash == expected_hash, f"asset-path:hash:{index}:expected={expected_hash:016X}:actual={actual_hash:016X}")
    return {
        "sections": layouts,
        "bundleValueNameAndFieldJoins": bundle_layout["capacity"],
        "dictionaryBundleIndexZeroCount": bundle_layout["capacity"],
        "assetBundleIndexInBounds": asset_layout["capacity"],
        "assetPathRecords": asset_layout["capacity"],
        "assetPathUniqueNames": len(unique_paths),
        "assetPathDecodedUtf16Bytes": decoded_bytes,
        "assetPathHashesReproduced": asset_layout["capacity"],
        "assetPathsWithAsciiUppercase": uppercase_paths,
        "assetPathSuffixConsumed": suffix_end - suffix_start,
        "evidenceBoundary": "conditional",
    }


def audit_bundle_manifest_native(
    *,
    manifest: Path | None = None,
    contract_path: Path = CONTRACT,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    contract, contract_sha = read_reviewed_contract(
        contract_path, schema=SCHEMA, label="bundle-manifest-native", status="validated"
    )
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["globalMetadataSha256"],
        gameassembly=gameassembly, metadata=metadata,
    )
    report: dict[str, Any] = {
        "schema": "endfield.bundle-manifest-native-audit.v4",
        "status": gate.status,
        "detail": gate.detail,
        "contractSha256": contract_sha,
        "nativeInputs": {
            "gameAssemblySha256": gate.gameassembly_sha256,
            "globalMetadataSha256": gate.metadata_sha256,
        },
    }
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return report
    unity = gate.gameassembly.with_name("UnityPlayer.dll")
    if not unity.is_file():
        report.update(status="missing", detail=f"UnityPlayer.dll missing at {unity}")
        return report
    unity_sha = sha256_file(unity).upper()
    report["nativeInputs"]["unityPlayerSha256"] = unity_sha
    if unity_sha != inputs["unityPlayerSha256"].upper():
        report.update(status="mismatched", detail="UnityPlayer.dll hash differs from reviewed contract")
        return report

    try:
        image = open_native_image(gate.gameassembly, gate.metadata)
        bindings, writer, string_hash, dictionary_sections, asset_fields = _check_native(image, contract)
        runtime_consumers = _check_runtime_dependency_consumers(image, contract)
    except (ValueError, RuntimeError, KeyError, IndexError) as error:
        report.update(status="mismatched", detail=f"native proof failed: {error}")
        return report
    header = contract["bundleType"]["boxedValueHeaderBytes"]
    fields = {
        name: offset - header
        for name, offset in contract["bundleType"]["fieldOffsets"].items()
    }
    manifest_report = None
    if manifest is not None:
        try:
            import brotli

            manifest = Path(manifest)
            source = manifest.read_bytes()
            decoded = brotli.decompress(source)
            parsed = parse_decompressed_bundle_manifest(decoded, source=str(manifest))
            table_by_name = {table.name: table for table in parsed.tables}
            for binding in bindings:
                table = table_by_name[binding["table"]]
                _require(table.offset == table.section_offset + 4 + binding["rowDataBias"],
                         f"{binding['table']}:section-offset")
                binding["countWordOffset"] = table.section_offset + 4
                binding["firstRowOffset"] = table.offset
                binding["rowCount"] = table.row_count
                binding["rowBytes"] = table.row_size
            _require(table_by_name["fixed-width-48"].row_size == contract["bundleType"]["rowBytes"],
                     "bundle-file-width")
            replay = _replay_hash_version(decoded, parsed, contract, fields)
            dictionary_replay = _replay_dictionary_sections(decoded, parsed, contract, fields, asset_fields)
            manifest_report = {
                "source": str(manifest),
                "sourceKind": "supplied file; verify current install with bundle_manifest_corpus",
                "compressedLength": len(source),
                "compressedSha256": hashlib.sha256(source).hexdigest().upper(),
                "decompressedSha256": parsed.decompressed_sha256.upper(),
                "versionHashReplay": replay,
                "dictionaryReplay": dictionary_replay,
            }
        except Exception as error:
            report.update(status="invalid-manifest", detail=f"manifest proof failed: {error}")
            return report
    report.update(
        status="validated",
        evidenceBoundary="direct",
        bindings=bindings,
        bundleRowBytes=contract["bundleType"]["rowBytes"],
        bundleRowFieldOffsets=fields,
        writer=writer,
        dependencyStringHash=string_hash,
        dictionarySections=dictionary_sections,
        runtimeDependencyConsumers=runtime_consumers,
        semanticLimits=contract["evidenceNotes"],
    )
    if manifest_report is not None:
        report["manifest"] = manifest_report
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, help="supplied compressed manifest.hgmmap")
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_bundle_manifest_native(
        manifest=args.manifest,
        contract_path=args.contract,
        gameassembly=args.gameassembly,
        metadata=args.metadata,
    )
    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())

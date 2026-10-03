"""Authenticate conditional decoder-owner-source transport into provider setup.

Only explicit selected native files are accepted. Full unwind groups and typed
field/branch bindings prove a static preparation route; indirect provider slot
identity in a live request, codec identity, allocation lifetime and playback stay open.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NativeImage, read_reviewed_contract
from scripts.game_data import wwise_source_native as source_native
from scripts.game_data import wwise_owner_carrier_native as carrier_native
from scripts.game_data.wwise_source_native import SourceContractError, _collect_source_image
from scripts.game_data.wwise_source_queue_native import (
    _digest, _hex, _rva, validate_native_group_windows, validate_opened_managed_inputs,
)

CONTRACT_PATH = CONTRACTS_DIR / "wwise_decoder_provider_native.json"
SCHEMA = "endfield.wwise-decoder-provider-native.v1"
GROUP_NAMES = {"anonymousDecoderProviderPreparation", "anonymousDecoderPrepareCaller", "anonymousDecoderRetryCaller"}
LAYOUT_FIELDS = {
    "decoder": {"primaryOwnerPointer", "providerOutputPointer"},
    "primaryOwner": {"sourcePointer", "alternatePointer", "alternateWord"},
    "source": {"flagsWord", "dataPointer", "storedWord", "argumentHighWord"},
    "frame": {"descriptorPointer", "descriptorWord", "flagsDescriptorPointer", "directDataFlag", "argumentHighWord", "flagsDescriptor", "options", "outputArgument"},
    "providerVtable": {"alternateSlot", "ordinarySlot"},
}
CONSTANT_NAMES = {"sourceKindMask", "alternateKind", "directDataBit", "pointerDescriptorBit"}


def _fail(check: str, subject: str, expected: Any, actual: Any) -> None:
    raise SourceContractError(check, subject, expected, actual)


def _rows(value: Any, subject: str, maximum: int) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not 1 <= len(value) <= maximum or any(not isinstance(row, dict) for row in value):
        _fail("providerDeclarationRows", subject, f"1..{maximum} objects", type(value).__name__)
    return value


def load_decoder_provider_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract, _ = read_reviewed_contract(path, schema=SCHEMA, status="reviewedCurrentBuild", label="wwise-decoder-provider")
    return contract


def validate_provider_declarations(contract: dict[str, Any]) -> None:
    """Bound every read and bind field/constant/branch declarations to bytes."""
    if contract.get("schema") != SCHEMA or contract.get("status") != "reviewedCurrentBuild":
        _fail("providerSchema", "contract", SCHEMA, contract.get("schema"))
    groups = _rows(contract.get("nativeGroups"), "nativeGroups", 3)
    if len(groups) != len(GROUP_NAMES) or {g.get("key") for g in groups} != GROUP_NAMES:
        _fail("providerGroupCoverage", "nativeGroups", sorted(GROUP_NAMES), [g.get("key") for g in groups])
    inputs = contract["nativeInputs"]
    for name in ("gameAssemblySha256", "globalMetadataSha256", "akSoundEngineSha256"):
        _digest(inputs[name], name)
    if type(inputs["akSoundEngineFileSize"]) is not int or not 0 < inputs["akSoundEngineFileSize"] <= 256 * 1024 * 1024:
        _fail("providerInputSize", "akSoundEngineFileSize", "bounded positive integer", inputs["akSoundEngineFileSize"])
    witnesses = {}
    for group in groups:
        entry = _rva(group["entryRva"], group["key"])
        windows = _rows(group.get("windows"), group["key"], 16)
        starts = set()
        for window in windows:
            start = _rva(window["rva"], group["key"])
            length = window["bodyLength"]
            if start in starts or type(length) is not int or not 1 <= length <= 65536:
                _fail("providerWindowExtent", group["key"], "unique bounded window", window["rva"])
            starts.add(start)
            _digest(window["bodySha256"], group["key"])
            _rva(window["unwindRva"], group["key"])
            _hex(window["unwindInfoHex"], group["key"], 256)
        if entry not in starts:
            _fail("providerEntryExtent", group["key"], "entry is a window start", group["entryRva"])
        local = carrier_native._witnesses(group)
        for role, witness in local.items():
            address = _rva(witness["rva"], role)
            encoded = _hex(witness["instructionHex"], role, 15)
            if not any(int(w["rva"], 16) <= address and address + len(encoded) <= int(w["rva"], 16) + w["bodyLength"] for w in windows):
                _fail("providerWitnessExtent", role, "inside declared window", witness["rva"])
            if group["key"] == "anonymousDecoderProviderPreparation":
                witnesses[role] = witness
    layouts = contract["layouts"]
    if set(layouts) != set(LAYOUT_FIELDS):
        _fail("providerLayoutCoverage", "layouts", sorted(LAYOUT_FIELDS), sorted(layouts))
    for name, fields in LAYOUT_FIELDS.items():
        if set(layouts[name]) != fields:
            _fail("providerFieldCoverage", name, sorted(fields), sorted(layouts[name]))
        for field, offset in layouts[name].items():
            if type(offset) is not int or not 0 <= offset <= 4096:
                _fail("providerFieldOffset", f"{name}.{field}", "bounded nonnegative integer", offset)
    constants = contract["constants"]
    if set(constants) != CONSTANT_NAMES or any(type(v) is not int or not 0 <= v <= 255 for v in constants.values()):
        _fail("providerConstantCoverage", "constants", sorted(CONSTANT_NAMES), constants)
    bound_fields = set()
    for row in _rows(contract["fieldBindings"], "fieldBindings", 64):
        subject = f"{row['layout']}.{row['field']}"
        value = layouts[row["layout"]][row["field"]]
        width = row["displacementBytes"]
        if type(width) is not int or width not in (1, 4) or value >= 1 << (width * 8 - 1):
            _fail("providerDisplacementWidth", subject, "positive signed displacement width", width)
        expected = _hex(row["prefixHex"], subject, 10) + value.to_bytes(width, "little")
        actual = bytes.fromhex(witnesses[row["witness"]]["instructionHex"])
        if actual != expected:
            _fail("providerFieldBinding", subject, expected.hex(), actual.hex())
        bound_fields.add((row["layout"], row["field"]))
    required_fields = {(name, field) for name, fields in LAYOUT_FIELDS.items() for field in fields}
    if bound_fields != required_fields:
        _fail("providerFieldBindingCoverage", "fieldBindings", sorted(required_fields), sorted(bound_fields))
    bound_constants = set()
    for row in _rows(contract["constantBindings"], "constantBindings", 16):
        name = row["constant"]
        expected = _hex(row["prefixHex"], name, 10) + bytes([constants[name]])
        actual = bytes.fromhex(witnesses[row["witness"]]["instructionHex"])
        if expected != actual:
            _fail("providerConstantBinding", name, expected.hex(), actual.hex())
        bound_constants.add(name)
    if bound_constants != CONSTANT_NAMES:
        _fail("providerConstantBindingCoverage", "constantBindings", sorted(CONSTANT_NAMES), sorted(bound_constants))
    branches = _rows(contract["branchBindings"], "branchBindings", 4)
    if len(branches) != 4 or {r.get("witness") for r in branches} != {"branchOrdinaryKind", "branchAlternatePointer", "branchNumericDescriptor", "jumpProviderCall"}:
        _fail("providerBranchCoverage", "branchBindings", "four reviewed branch edges", [r.get("witness") for r in branches])
    for row in branches:
        witness, target = witnesses[row["witness"]], witnesses[row["targetWitness"]]
        encoded = bytes.fromhex(witness["instructionHex"])
        opcode = _hex(row["opcodeHex"], row["witness"], 1)
        if len(encoded) != 2 or encoded[:1] != opcode:
            _fail("providerBranchEncoding", row["witness"], "reviewed short branch", encoded.hex())
        actual = int(witness["rva"], 16) + 2 + struct.unpack("<b", encoded[1:])[0]
        if actual != int(target["rva"], 16):
            _fail("providerBranchTarget", row["witness"], target["rva"], hex(actual))
    globals_seen = set()
    globals_rows = _rows(contract["globalBindings"], "globalBindings", 2)
    if len(globals_rows) != 2 or {r.get("witness") for r in globals_rows} != {"loadAlternateProvider", "loadOrdinaryProvider"}:
        _fail("providerGlobalCoverage", "globalBindings", "both provider loads", [r.get("witness") for r in globals_rows])
    for row in globals_rows:
        witness = witnesses[row["witness"]]
        encoded = bytes.fromhex(witness["instructionHex"])
        prefix = _hex(row["prefixHex"], row["witness"], 3)
        target = _rva(row["targetRva"], row["witness"])
        if len(encoded) != 7 or encoded[:3] != prefix or int(witness["rva"], 16) + 7 + struct.unpack_from("<i", encoded, 3)[0] != target:
            _fail("providerGlobalBinding", row["witness"], row["targetRva"], encoded.hex())
        globals_seen.add(target)
    if len(globals_seen) != 1:
        _fail("providerSingletonContinuity", "globalBindings", "same singleton slot", sorted(globals_seen))
    preparation = next(g for g in groups if g["key"] == "anonymousDecoderProviderPreparation")
    callers = contract["callerGroups"]
    if not isinstance(callers, list) or len(callers) != 2 or set(callers) != GROUP_NAMES - {preparation["key"]}:
        _fail("providerCallerCoverage", "callerGroups", "two reviewed distinct callers", callers)
    for group in groups:
        if group["key"] not in callers:
            continue
        call = next(w for w in group["instructionWitnesses"] if w["role"] == "callPreparation")
        encoded = bytes.fromhex(call["instructionHex"])
        if len(encoded) != 5 or encoded[0] != 0xe8 or int(call["rva"], 16) + 5 + struct.unpack_from("<i", encoded, 1)[0] != int(preparation["entryRva"], 16):
            _fail("providerCallerTarget", group["key"], preparation["entryRva"], encoded.hex())


def validate_provider_dependencies(contract: dict[str, Any], source: dict[str, Any], carrier: dict[str, Any]) -> None:
    """Check layout agreement, without claiming dynamic class/object identity."""
    if source["nativeInputs"] != contract["nativeInputs"] or carrier["nativeInputs"] != contract["nativeInputs"]:
        _fail("providerSelectedDependencies", "source/carrier", contract["nativeInputs"], {"source": source["nativeInputs"], "carrier": carrier["nativeInputs"]})
    expected_owner = source["ownerTransports"][0]["primarySourcePointerOffset"]
    expected_decoder = carrier["layouts"]["decoder"]["primaryOwnerPointer"]["offset"]
    for name, expected, actual in (
        ("primaryOwner.sourcePointer", expected_owner, contract["layouts"]["primaryOwner"]["sourcePointer"]),
        ("decoder.primaryOwnerPointer", expected_decoder, contract["layouts"]["decoder"]["primaryOwnerPointer"]),
    ):
        if expected != actual:
            _fail("providerDependencyField", name, expected, actual)
    fields = {f["name"]: f for f in source["structures"]["source"]["fields"]}
    for name, dependency_name, delta in (("flagsWord", "sourceFlagsWord", 0), ("dataPointer", "sourceDataPointer", 0), ("storedWord", "sourceStoredWord4", 0), ("argumentHighWord", "sourceArgumentWord24", 2)):
        expected = fields[dependency_name]["offset"] + delta
        if contract["layouts"]["source"][name] != expected:
            _fail("providerSourceField", name, expected, contract["layouts"]["source"][name])


def load_validated_decoder_provider_contract(*, gameassembly: Path, metadata: Path, ak_sound_engine: Path, contract_path: Path = CONTRACT_PATH, include_storage: bool = False, include_dispatch: bool = False, include_package: bool = False, include_retention: bool = False, include_result: bool = False, include_read: bool = False) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if include_read:
        include_result = True
    if include_result:
        include_storage = include_package = True
    audit: dict[str, Any] = {"status": "missing", "contractPath": str(contract_path), "detail": ""}
    if any(path is None for path in (gameassembly, metadata, ak_sound_engine)):
        audit.update(detail="three explicit selected native paths are required", diagnostic={"failedCheck": "selectedInputs", "actual": "missing path"})
        return None, audit
    try:
        contract = load_decoder_provider_contract(contract_path)
        validate_provider_declarations(contract)
        inputs = contract["nativeInputs"]
        gate = check_installed_native_inputs(inputs["gameAssemblySha256"], inputs["globalMetadataSha256"], gameassembly=gameassembly, metadata=metadata, require_metadata=True)
        audit.update(status=gate.status, detail=gate.detail)
        if gate.status != "validated":
            return None, audit
        if not ak_sound_engine.is_file():
            audit.update(status="missing", detail=f"selected AkSoundEngine.dll not found: {ak_sound_engine}")
            return None, audit
        digest, size = sha256_file(ak_sound_engine), ak_sound_engine.stat().st_size
        if digest.casefold() != inputs["akSoundEngineSha256"].casefold() or size != inputs["akSoundEngineFileSize"]:
            _fail("providerAkSoundEngineInput", str(ak_sound_engine), f"{inputs['akSoundEngineFileSize']}/{inputs['akSoundEngineSha256']}", f"{size}/{digest}")
        managed = NativeImage(gameassembly, metadata, label="wwise-decoder-provider")
        validate_opened_managed_inputs(contract, managed)
        image, bodies, records = _collect_source_image(ak_sound_engine, managed.mapper)
        if hashlib.sha256(image.buf).hexdigest() != inputs["akSoundEngineSha256"].casefold():
            _fail("providerOpenedInput", str(ak_sound_engine), inputs["akSoundEngineSha256"], hashlib.sha256(image.buf).hexdigest())
        source = source_native.load_source_contract()
        source_native.validate_source_contract(source)
        source_native.validate_source_bodies(source, bodies)
        source_native.validate_source_consumers(source, image, records)
        source_native.validate_source_transports(source, image, bodies)
        carrier = carrier_native.load_owner_carrier_contract()
        carrier_native.validate_owner_carrier_bytes(carrier, image, bodies, records, source)
        validate_provider_dependencies(contract, source, carrier)
        validate_native_group_windows(contract["nativeGroups"], image, bodies, records)
        audit.update(status="validated", detail="selected decoder-owner-source reads and conditional provider descriptor transport validated", evidenceBoundary=contract["evidenceBoundary"])
        if include_storage:
            # Optional downstream facts reuse these selected, authenticated images.
            # A downstream failure withholds those facts, preserving preparation.
            audit["providerStorageGate"] = validate_optional_storage(image, bodies, records, contract)
        if include_dispatch:
            storage = audit.get("providerStorageGate", {})
            if storage.get("status") == "validated":
                audit["sourceDispatchGate"] = validate_optional_dispatch(image, bodies, records, contract, storage["contract"])
            else:
                audit["sourceDispatchGate"] = {"status": "missing", "detail": "validated storage dependency required"}
        if include_package:
            audit["externalPackageGate"] = validate_optional_package(image, bodies, records, contract)
        if include_retention:
            storage = audit.get("providerStorageGate", {})
            audit["providerRetentionGate"] = validate_optional_retention(image, bodies, records, contract, storage["contract"]) if storage.get("status") == "validated" else {"status":"missing","detail":"validated storage dependency required"}
        if include_result:
            storage, package = audit.get("providerStorageGate", {}), audit.get("externalPackageGate", {})
            audit["packageResultGate"] = validate_optional_result(image, bodies, records, contract, storage["contract"], package["contract"]) if storage.get("status") == package.get("status") == "validated" else {"status":"missing", "detail":"validated storage and external-package dependencies required"}
        if include_read:
            result = audit.get('packageResultGate', {})
            audit['packageReadGate'] = validate_optional_read(image,bodies,records,contract,package['contract'],result['contract']) if result.get('status')=='validated' else {'status':'missing','detail':'validated package result dependency required'}
        return contract, audit
    except SourceContractError as error:
        audit.update(status="mismatched", detail=str(error)[:320], diagnostic=error.diagnostic)
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError, StopIteration) as error:
        audit.update(status="mismatched", detail=str(error)[:320], diagnostic={"failedCheck": "decoderProviderContract", "actual": str(error)[:160]})
    return None, audit


def validate_optional_read(image, bodies, records, parent, package, result):
    from scripts.game_data import wwise_package_read_native as read
    try:
        contract=read.load_read_contract()
        read.validate_read_bytes(contract,image,bodies,records,parent,package,result)
        report = {'status':'validated','detail':'default package read/completion and bounded pre-transform entry validated',
                'contract':contract,'observerSpec':read.observer_spec(contract,package),'evidenceBoundary':contract['evidenceBoundary']}
        report['packageTransformGate']=validate_optional_transform(image,bodies,records,contract,result)
        return report
    except SourceContractError as error:
        return {'status':'mismatched','detail':str(error)[:320],'diagnostic':error.diagnostic}
    except FileNotFoundError as error:
        return {'status':'missing','detail':str(error)[:320]}
    except (OSError,ValueError,KeyError,TypeError,IndexError,AttributeError,OverflowError,StopIteration) as error:
        return {'status':'mismatched','detail':str(error)[:320],'diagnostic':{'failedCheck':'packageRead','actual':str(error)[:160]}}


def validate_optional_transform(image,bodies,records,read,result=None):
    from scripts.game_data import wwise_package_transform_native as transform
    try:
        contract=transform.load_transform_contract()
        if result is None:return {'status':'missing','detail':'validated package result dependency required for transfer receiver proof'}
        transform.validate_transform_bytes(contract,image,bodies,records,read,result)
        return {'status':'validated','detail':'aligned native XOR, embedded transfer/back-pointer, producer calls and conditional primary-provider/queued-receiver interfaces validated',
                'contract':contract,'evidenceBoundary':contract['evidenceBoundary']}
    except SourceContractError as error:
        return {'status':'mismatched','detail':str(error)[:320],'diagnostic':error.diagnostic}
    except FileNotFoundError as error:
        return {'status':'missing','detail':str(error)[:320]}
    except (OSError,ValueError,KeyError,TypeError,IndexError,AttributeError,OverflowError,StopIteration) as error:
        return {'status':'mismatched','detail':str(error)[:320],'diagnostic':{'failedCheck':'packageTransform','actual':str(error)[:160]}}


def validate_optional_result(image: Any, bodies: dict, records: dict, parent: dict, storage: dict, package: dict) -> dict:
    from scripts.game_data import wwise_package_result_native as result

    try:
        contract = result.load_result_contract()
        result.validate_result_bytes(contract, image, bodies, records, parent, storage, package)
        return {"status":"validated", "detail":"package result descriptor writes and primary completion entry validated", "contract":contract, "observerSpec":result.observer_spec(contract), "evidenceBoundary":contract["evidenceBoundary"]}
    except SourceContractError as error:
        return {"status":"mismatched", "detail":str(error)[:320], "diagnostic":error.diagnostic}
    except FileNotFoundError as error:
        return {"status":"missing", "detail":str(error)[:320]}
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError, StopIteration) as error:
        return {"status":"mismatched", "detail":str(error)[:320], "diagnostic":{"failedCheck":"packageResult","actual":str(error)[:160]}}


def validate_optional_retention(image: Any, bodies: dict, records: dict, parent: dict, storage: dict) -> dict:
    from scripts.game_data import wwise_provider_retention_native as retention

    try:
        contract = retention.load_retention_contract()
        retention.validate_retention_bytes(contract, image, bodies, records, parent, storage)
        return {"status":"validated", "detail":"retained provider descriptor and device I/O entry reads validated", "contract":contract, "evidenceBoundary":contract["evidenceBoundary"]}
    except SourceContractError as error:
        return {"status":"mismatched", "detail":str(error)[:320], "diagnostic":error.diagnostic}
    except FileNotFoundError as error:
        return {"status":"missing", "detail":str(error)[:320]}
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError, StopIteration) as error:
        return {"status":"mismatched", "detail":str(error)[:320], "diagnostic":{"failedCheck":"providerRetention","actual":str(error)[:160]}}


def validate_optional_package(image: Any, bodies: dict, records: dict, parent: dict) -> dict:
    from scripts.game_data import wwise_external_package_native as package

    try:
        contract = package.load_package_contract()
        package.validate_package_bytes(contract, image, bodies, records, parent)
        return {"status": "validated", "detail": "conditional external-package path hash and keyed lookup validated",
                "contract": contract, "observerSpec": package.observer_spec(contract), "evidenceBoundary": contract["evidenceBoundary"]}
    except SourceContractError as error:
        return {"status": "mismatched", "detail": str(error)[:320], "diagnostic": error.diagnostic}
    except FileNotFoundError as error:
        return {"status": "missing", "detail": str(error)[:320]}
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError, StopIteration) as error:
        return {"status": "mismatched", "detail": str(error)[:320], "diagnostic": {"failedCheck": "externalPackage", "actual": str(error)[:160]}}


def validate_optional_dispatch(image: Any, bodies: dict, records: dict, parent: dict, storage: dict) -> dict:
    from scripts.game_data import wwise_source_provider_dispatch_native as dispatch

    try:
        contract = dispatch.load_dispatch_contract()
        dispatch.validate_dispatch_bytes(contract, image, bodies, records, parent, storage)
        return {"status": "validated", "detail": "source-based provider dispatch and storage-wrapper callsites validated",
                "observerSpec": dispatch.observer_spec(contract, parent, storage), "evidenceBoundary": contract["evidenceBoundary"]}
    except SourceContractError as error:
        return {"status": "mismatched", "detail": str(error)[:320], "diagnostic": error.diagnostic}
    except FileNotFoundError as error:
        return {"status": "missing", "detail": str(error)[:320]}
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError, StopIteration) as error:
        return {"status": "mismatched", "detail": str(error)[:320], "diagnostic": {"failedCheck": "sourceProviderDispatch", "actual": str(error)[:160]}}


def validate_optional_storage(image: Any, bodies: dict, records: dict, parent: dict) -> dict[str, Any]:
    from scripts.game_data import wwise_provider_storage_native as storage

    try:
        contract = storage.load_storage_contract()
        storage.validate_storage_bytes(contract, image, bodies, records, parent)
        return {"status": "validated", "detail": "conditional provider slots and owned UTF-16 storage validated", "evidenceBoundary": contract["evidenceBoundary"], "contract": contract}
    except SourceContractError as error:
        return {"status": "mismatched", "detail": str(error)[:320], "diagnostic": error.diagnostic}
    except FileNotFoundError as error:
        return {"status": "missing", "detail": str(error)[:320]}
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError, StopIteration) as error:
        return {"status": "mismatched", "detail": str(error)[:320], "diagnostic": {"failedCheck": "providerStorageContract", "actual": str(error)[:160]}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--ak-sound-engine", required=True, type=Path)
    parser.add_argument("--include-storage", action="store_true")
    parser.add_argument("--include-dispatch", action="store_true", help="Also validate source-based provider dispatch on the same selected images; implies storage.")
    parser.add_argument("--include-package", action="store_true", help="Also validate conditional external-package hashing and table lookup on the same images.")
    parser.add_argument("--include-retention", action="store_true", help="Also validate retained provider/device reads; implies storage.")
    parser.add_argument("--include-result", action="store_true", help="Also validate package descriptor completion; implies storage and package.")
    parser.add_argument('--include-read',action='store_true',help='Also validate package read/completion and pre-transform entries; implies result.')
    args = parser.parse_args()
    _, audit = load_validated_decoder_provider_contract(gameassembly=args.gameassembly, metadata=args.metadata, ak_sound_engine=args.ak_sound_engine,
        include_storage=args.include_storage or args.include_dispatch or args.include_retention, include_dispatch=args.include_dispatch, include_package=args.include_package, include_retention=args.include_retention, include_result=args.include_result, include_read=args.include_read)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0 if audit["status"] == "validated" and all(audit.get(key, {}).get("status", "validated") == "validated"
        for key in ("providerStorageGate", "sourceDispatchGate", "externalPackageGate", "providerRetentionGate", "packageResultGate", "packageReadGate")) else 1


if __name__ == "__main__":
    raise SystemExit(main())

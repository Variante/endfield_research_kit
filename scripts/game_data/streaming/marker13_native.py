"""Fail-closed validator for the selected marker13 read-window evidence."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.game_data.streaming import marker17_native as dependency
from scripts.game_data.streaming import native as base
from scripts.game_data.contracts import CONTRACTS_DIR


SCHEMA = "endfield.streaming-marker13-native-contract.v2"
DEFAULT_CONTRACT = CONTRACTS_DIR / "streaming_marker13_native.json"
EXPECTED_WHOLE = {
    "selector9Slot4Reader": (14940784, 195),
    "selector9Slot5Reader": (14941152, 195),
    "slot4LocalFourDwordConsumer": (2180112, 744),
    "slot5LocalFourDwordConsumer": (2180864, 510),
}
EXPECTED_SLOTS = {
    4: (14940784, "selector9Slot4Reader", "slot4LocalFourDwordConsumer"),
    5: (14941152, "selector9Slot5Reader", "slot5LocalFourDwordConsumer"),
}
EXPECTED_PROFILE = {
    "family": "streaming", "rootMarker": 2, "rawSelector": 9,
    "key": [255, 0, 0], "packedKey": 0xFF000000, "marker": 13,
    "readWidth": 16, "dwordOffsets": [0, 4, 8, 12],
    "allocatedSizeStatus": "not-proven-by-native",
    "markerBinding": "external authenticated same-element corpus join; native reader does not inspect marker13",
    "extentStatus": "read-window-only; record extent and EOF unresolved",
    "evidenceLevel": "structural-only",
}
EXPECTED_ABSENCE_RANGES = {
    "slot5DispatchWholeHotBodyThroughFinalBackedge": (449296, 276),
    "slot5DispatchColdIndirectBranchAndReturnEdge": (15417332, 11),
    "slot5SelectedMarker2EntryWholeBody": (1817808, 61),
    "slot5ScopeWholeBody": (1817440, 366),
    "slot5Marker2DispatchPointer": (27075480, 8),
    "selector0DescriptorConstructorArgumentsAndCall": (3687547, 14),
    "selector0Slot5Registration": (3687833, 56),
    "selector0PublicationArgumentsAndCall": (3688105, 18),
}
EXPECTED_ABSENCE_REUSE = {
    ("base", "parallelScopeCallbackBridgeA"): (1820368, 92),
    ("base", "descriptorConstructor"): (3671376, 110),
    ("base", "callbackAssignment"): (3681056, 401),
    ("base", "inlineCallbackMove"): (3681472, 108),
    ("base", "callbackReset"): (3681616, 73),
    ("base", "publishTenCallbacks"): (16070512, 95),
    ("marker17", "indexedCallbackAssignment"): (3680944, 72),
    ("self", "selector9Slot5Reader"): (14941152, 195),
    ("self", "slot5LocalFourDwordConsumer"): (2180864, 510),
    ("self", "keyLiteralRange"): (27951384, 12),
}
EXPECTED_ABSENT_WITNESS = {
    "family": "streaming", "rootMarker": 2, "rawSelector": None,
    "serializedSelectorState": "absent", "nativeAccessorDefault": 0,
    "phaseSlot": 5, "packedKey": 0xFF000000, "marker": 13, "readWidth": 16,
    "readerRangeRole": "selector9Slot5Reader",
    "classification": "conditional-native-accessor-default-not-serialized-value",
    "runtimeReceipt": "unresolved", "targetOwnedBytes": 0,
    "extentStatus": "read-window-only; record extent and EOF unresolved",
    "runtimeSelectionCondition": "conditional new-key Init marker2 and default slot5; existing-key history unresolved",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def validate_marker13_native_contract(
    *, game_root: Path, contract_path: Path = DEFAULT_CONTRACT,
) -> dict[str, Any]:
    """Validate only explicit selected-build inputs; never infer a game root."""
    failures: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "status": "validation_failed", "profile": None,
        "consumerReview": None, "absentSelectorContextWitness": None,
        "validationFailures": failures,
    }

    def require(gate: str, expected: Any, actual: Any) -> None:
        if expected != actual:
            failures.append({"gate": gate, "expected": expected, "actual": actual})

    try:
        raw = Path(contract_path).read_bytes()
        contract_sha = sha256(raw)
        result["contractSha256"] = contract_sha
        contract = json.loads(raw)
        require("schema", SCHEMA, contract.get("schema"))
        require("contract_status", "validated-conditional-static", contract.get("status"))
        dep = contract["dependency"]
        dep_document = json.loads(dependency.DEFAULT_CONTRACT.read_bytes())
        require("dependency_schema", dep["schema"], dep_document.get("schema"))
        roles = {row["role"] for row in dep_document["unityPlayerRanges"]}
        require("dependency_required_roles", [], sorted(set(dep["requiredUnityPlayerRoles"]) - roles))
        reused = dep["requiredDefaultRegistration"]
        require("dependency_registration_selector", 9, reused.get("selector"))
        require("dependency_registration_slot", 3, reused.get("slot"))
        selector9 = [row for row in dep_document["selectedDefaultSlot3"] if row.get("selector") == 9]
        require("dependency_selector9_count", 1, len(selector9))
        if len(selector9) == 1:
            require("dependency_reused_registration_evidence", [],
                    sorted(set(reused["reusedEvidence"]) - selector9[0].keys()))
        if failures:
            return result

        selected = dependency.validate_marker17_native_contract(game_root=Path(game_root))
        require("dependency_native_gate", "validated", selected.get("status"))
        if failures:
            result["dependencyValidationFailures"] = selected.get("validationFailures", [])
            return result
        selected_inputs = selected.get("nativeInputs") or {}
        expected_inputs = contract.get("nativeInputs") or {}
        for key, expected in expected_inputs.items():
            require(f"dependency_native_input:{key}", expected, selected_inputs.get(key))

        image_path = Path(game_root).parent / "UnityPlayer.dll"
        image = image_path.read_bytes()
        require("unity_image_read_sha256", expected_inputs.get("unityPlayerSha256"), sha256(image))
        if failures:
            return result
        result["dependencyContractSha256"] = selected["contractSha256"]
        result["nativeInputs"] = dict(selected_inputs)

        rows = contract["unityPlayerRanges"]
        require("whole_range_roles", sorted(EXPECTED_WHOLE), sorted(row["role"] for row in rows))
        require("whole_range_unique_rva_size", len(rows), len({(row["rva"], row["size"]) for row in rows}))
        for row in rows:
            role = row["role"]
            expected_identity = EXPECTED_WHOLE.get(role)
            require(f"{role}.identity", expected_identity,
                    (row["rva"], row["size"]) if expected_identity is not None else None)
            try:
                offset, body = base._bounded_pe_range(image, row["rva"], row["size"])
                require(f"{role}.file_offset", row["fileOffset"], offset)
                require(f"{role}.body_sha256", row["bodySha256"], sha256(body))
                entry = bytes.fromhex(row["entryBytesHex"])
                require(f"{role}.entry_bytes", entry.hex().upper(), body[:len(entry)].hex().upper())
            except (TypeError, ValueError) as exc:
                failures.append({"gate": f"{role}.bounded_range", "expected": "bounded PE range", "actual": str(exc)})

        literal = contract["keyLiteralRange"]
        require("key_literal_words", [255, 0, 0], literal.get("key"))
        require("key_literal_bytes", struct.pack("<3I", 255, 0, 0).hex().upper(), literal.get("bytesHex"))
        try:
            expected = bytes.fromhex(literal["bytesHex"])
            offset, actual = base._bounded_pe_range(image, literal["rva"], len(expected))
            require("key_literal.file_offset", literal["fileOffset"], offset)
            require("key_literal.exact_bytes", expected.hex().upper(), actual.hex().upper())
        except (TypeError, ValueError) as exc:
            failures.append({"gate": "key_literal.bounded_range", "expected": "bounded exact PE bytes", "actual": str(exc)})

        slots = contract["selectedDefaultSlots"]
        require("selected_slots", sorted(EXPECTED_SLOTS), sorted(row["slot"] for row in slots))
        for row in slots:
            slot = row["slot"]
            expected_slot = EXPECTED_SLOTS.get(slot)
            require(f"slot{slot}.identity", expected_slot,
                    (row.get("readerRva"), row.get("readerRangeRole"), row.get("downstreamRangeRole")))
            require(f"slot{slot}.selector", 9, row.get("selector"))
            require(f"slot{slot}.key", [255, 0, 0], row.get("key"))
            span = row["registrationSpan"]
            try:
                expected = bytes.fromhex(span["bytesHex"])
                offset, actual = base._bounded_pe_range(image, span["rva"], len(expected))
                require(f"slot{slot}.registration.file_offset", span["fileOffset"], offset)
                require(f"slot{slot}.registration.exact_bytes", expected.hex().upper(), actual.hex().upper())
            except (TypeError, ValueError) as exc:
                failures.append({"gate": f"slot{slot}.registration.bounded_range",
                                 "expected": "bounded exact PE bytes", "actual": str(exc)})

        require("profile", EXPECTED_PROFILE, contract["profile"])
        additions = contract["additionalUnityPlayerRanges"]
        require("absence_range_roles", sorted(EXPECTED_ABSENCE_RANGES),
                sorted(row["role"] for row in additions))
        require("absence_range_unique_rva_size", len(additions),
                len({(row["rva"], row["size"]) for row in additions}))
        for row in additions:
            role = row["role"]
            require(f"absence:{role}.identity", EXPECTED_ABSENCE_RANGES.get(role),
                    (row["rva"], row["size"]))
            try:
                offset, body = base._bounded_pe_range(image, row["rva"], row["size"])
                require(f"absence:{role}.file_offset", row["fileOffset"], offset)
                require(f"absence:{role}.body_sha256", row["bodySha256"], sha256(body))
                entry = bytes.fromhex(row["entryBytesHex"])
                require(f"absence:{role}.entry_bytes", entry.hex().upper(), body[:len(entry)].hex().upper())
            except (TypeError, ValueError) as exc:
                failures.append({"gate": f"absence:{role}.bounded_range",
                                 "expected": f"bounded PE range RVA {row['rva']} size {row['size']}",
                                 "actual": str(exc)})

        base_document = json.loads(base.DEFAULT_CONTRACT.read_bytes())
        catalogs = {
            "base": {row["role"]: (row["rva"], row["size"])
                     for row in base_document["unityPlayerRanges"]},
            "marker17": {row["role"]: (row["rva"], row["size"])
                         for row in dep_document["unityPlayerRanges"]},
            "self": {row["role"]: (row["rva"], row["size"]) for row in rows},
        }
        catalogs["self"]["keyLiteralRange"] = (literal["rva"], len(bytes.fromhex(literal["bytesHex"])))
        reuse = contract["absencePathReusedRanges"]
        require("absence_reuse_roles", sorted(EXPECTED_ABSENCE_REUSE),
                sorted((row["contract"], row["role"]) for row in reuse))
        for row in reuse:
            key = (row["contract"], row["role"])
            identity = (row["rva"], row["size"])
            require(f"absence_reuse:{key}.identity", EXPECTED_ABSENCE_REUSE.get(key), identity)
            require(f"absence_reuse:{key}.catalog", identity,
                    catalogs.get(key[0], {}).get(key[1]))
        require("absent_selector_witness", EXPECTED_ABSENT_WITNESS,
                contract["absentSelectorContextWitness"])
        if not failures:
            result.update(
                status="validated", nativeMappingId=contract["nativeMappingId"],
                profile=contract["profile"], consumerReview=contract["consumerReview"],
                evidenceBoundary=contract["evidenceBoundary"],
                absentSelectorContextWitness=contract["absentSelectorContextWitness"],
                absentSelectorEvidence=contract["absentSelectorEvidence"],
            )
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        failures.append({"gate": "marker13_contract_inputs",
                         "expected": "readable, well-formed pinned evidence",
                         "actual": f"{type(exc).__name__}: {exc}"})
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    args = parser.parse_args()
    print(json.dumps(validate_marker13_native_contract(game_root=args.game_root,
                                                        contract_path=args.contract), indent=2))

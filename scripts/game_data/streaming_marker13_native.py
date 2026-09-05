"""Fail-closed validator for the selected marker13 read-window evidence."""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.game_data import streaming_marker17_native as dependency
from scripts.game_data import streaming_native as base


SCHEMA = "endfield.streaming-marker13-native-contract.v1"
DEFAULT_CONTRACT = Path(__file__).with_name("streaming_marker13_native.json")
CONTRACT_SHA256 = "E7A3871AD1901484B5FB8230AAC7F2B8E22222CA739B375E4AFFB2578DA35CC1"
DEPENDENCY_SHA256 = "34E915707F363B55F572D867C1CC3C1B28A76D66D132EB0E212377A730DD2891"
EXPECTED_INPUTS = {
    "gameAssemblySha256": "C24495E51B406F03B03890C4788EE618AE022C991405BE5D5B8B787CB775AE89",
    "metadataSha256": "0076743397ACADF03D3B0064343A963C7C88863B8160526D397E4B3EFB96F02E",
    "unityPlayerSha256": "BEE7BE52370ADDDD67BA61E4937CA51B7F272656841D187E95E505496DA798D1",
}
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


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def validate_marker13_native_contract(
    *, game_root: Path, contract_path: Path = DEFAULT_CONTRACT,
) -> dict[str, Any]:
    """Validate only explicit selected-build inputs; never infer a game root."""
    failures: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "status": "validation_failed", "profile": None,
        "consumerReview": None, "validationFailures": failures,
    }

    def require(gate: str, expected: Any, actual: Any) -> None:
        if expected != actual:
            failures.append({"gate": gate, "expected": expected, "actual": actual})

    try:
        raw = Path(contract_path).read_bytes()
        contract_sha = sha256(raw)
        result["contractSha256"] = contract_sha
        require("contract_sha256", CONTRACT_SHA256, contract_sha)
        if failures:
            return result
        contract = json.loads(raw)
        require("schema", SCHEMA, contract.get("schema"))
        require("contract_status", "validated-conditional-static", contract.get("status"))
        dep = contract["dependency"]
        require("dependency_sha256_constant", DEPENDENCY_SHA256, dep.get("sha256"))
        dep_raw = dependency.DEFAULT_CONTRACT.read_bytes()
        dep_document = json.loads(dep_raw)
        require("dependency_sha256", dep["sha256"], sha256(dep_raw))
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
        require("dependency_validated_contract", dep["sha256"], selected.get("contractSha256"))
        if failures:
            result["dependencyValidationFailures"] = selected.get("validationFailures", [])
            return result
        selected_inputs = selected.get("nativeInputs") or {}
        require("contract_native_inputs", EXPECTED_INPUTS, contract.get("nativeInputs"))
        for key, expected in EXPECTED_INPUTS.items():
            require(f"dependency_native_input:{key}", expected, selected_inputs.get(key))

        image_path = Path(game_root).parent / "UnityPlayer.dll"
        image = image_path.read_bytes()
        require("unity_image_read_sha256", EXPECTED_INPUTS["unityPlayerSha256"], sha256(image))
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
        if not failures:
            result.update(
                status="validated", nativeMappingId=contract["nativeMappingId"],
                profile=contract["profile"], consumerReview=contract["consumerReview"],
                evidenceBoundary=contract["evidenceBoundary"],
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

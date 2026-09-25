"""Validate the selected PlaySound string-to-hash default native routes.

The reviewed contract pins method identities and bytes for one installed
GameAssembly/metadata pair. The dynamic witnesses below also require the
serialized ``_soundEvent`` field to reach ``Compute(string)`` through the
checked object and position branches. iFix replacement and runtime execution
are outside this static proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import Body, BodyIndex
from scripts.game_data.il2cpp.native_image import NativeImage, read_reviewed_contract
from scripts.repo_paths import REPO_ROOT
from scripts.webui.audio.semantics.identifiers import audio_hash_generator_compute


CONTRACT_PATH = CONTRACTS_DIR / "audio_play_sound_string_native.json"
SCHEMA = "endfield.audio-play-sound-string-native.v1"
DEFAULT_OUTPUT = REPO_ROOT / "reports/audio/play_sound_string_native.json"


class NativeProofError(ValueError):
    """One named field, body, or direct dataflow witness changed."""


def _require_ordered(rows: list[dict[str, Any]], steps: list[str], *, check: str) -> None:
    """Require the exact selected instruction chain in one decoded body."""
    position = 0
    texts = [str(row.get("text") or "") for row in rows]
    for step in steps:
        try:
            position = texts.index(step, position) + 1
        except ValueError as error:
            raise NativeProofError(f"{check}:missing-or-reordered={step}") from error


def _checked_body(
    index: BodyIndex, image: NativeImage, key: str, spec: dict[str, Any]
) -> Body:
    body = index.body(
        spec["type"], spec["method"], parameters=spec.get("parameters")
    )
    expected_pointer = image.pe.image_base + int(spec["rva"])
    if body.pointer != expected_pointer:
        raise NativeProofError(
            f"{key}:pointer=0x{body.pointer:x};expected=0x{expected_pointer:x}"
        )
    if body.token.lower() != str(spec["token"]).lower():
        raise NativeProofError(f"{key}:token={body.token};expected={spec['token']}")
    if body.size != spec["bodyLength"]:
        raise NativeProofError(
            f"{key}:body-length={body.size};expected={spec['bodyLength']}"
        )
    digest = hashlib.sha256(image.pe.bytes_at_va(body.pointer, body.size)).hexdigest()
    if digest.lower() != spec["bodySha256"].lower():
        raise NativeProofError(f"{key}:body-sha256={digest};expected={spec['bodySha256']}")
    return body


def _checked_helper(
    index: BodyIndex, image: NativeImage, spec: dict[str, Any]
) -> tuple[int, list[dict[str, Any]]]:
    pointer = image.pe.image_base + int(spec["rva"])
    length = int(spec["bodyLength"])
    if index.extents.get(pointer) != pointer + length:
        raise NativeProofError(f"anonymous-post-helper:pdata-extent=0x{pointer:x}")
    digest = hashlib.sha256(image.pe.bytes_at_va(pointer, length)).hexdigest()
    if digest.lower() != spec["bodySha256"].lower():
        raise NativeProofError(
            f"anonymous-post-helper:body-sha256={digest};expected={spec['bodySha256']}"
        )
    if index.names_of(pointer):
        raise NativeProofError(f"anonymous-post-helper:unexpected-names={index.names_of(pointer)}")
    return pointer, index._decode(pointer, length)


def _unique_pointer(index: BodyIndex, symbol: str) -> int:
    pointers = index.pointers_by_name.get(symbol) or set()
    if len(pointers) != 1:
        raise NativeProofError(f"{symbol}:resolved-pointers={len(pointers)}")
    return next(iter(pointers))


def _prove_routes(
    index: BodyIndex, image: NativeImage, contract: dict[str, Any]
) -> dict[str, Any]:
    field = contract["fieldContract"]
    sound_offset = index.field_offset(field["soundEvent"])
    if sound_offset != field["soundEventOffset"]:
        raise NativeProofError(
            f"sound-event-field:offset={sound_offset};expected={field['soundEventOffset']}"
        )
    data_offset = int(field["actionDataPointerOffset"])
    bodies = {
        key: _checked_body(index, image, key, spec)
        for key, spec in contract["methods"].items()
    }
    helper_pointer, helper_rows = _checked_helper(
        index, image, contract["anonymousPostHelper"]
    )
    post_pointer = _unique_pointer(index, "Beyond.Audio.AudioAdapter._PostEvent")
    pos_uint = index.body(
        "Beyond.Gameplay.Audio.AudioBattleUtil",
        "PostEventAtPositionWithMixingType",
        parameters=["System.UInt32", "System.Boolean", "UnityEngine.Vector3"],
    )
    _require_ordered(
        bodies["doPlaySound"].rows,
        [f"call 0x{bodies['doPostEvent'].pointer:x}"],
        check="do-play-sound:object-post",
    )
    _require_ordered(
        bodies["doPlaySound"].rows,
        [f"call 0x{bodies['doPostEventAtPosition'].pointer:x}"],
        check="do-play-sound:position-post",
    )
    _require_ordered(
        bodies["doPostEvent"].rows,
        [
            f"mov rax, [rbx+0x{data_offset:x}]",
            f"mov rsi, [rax+0x{sound_offset:x}]",
            "mov rdx, rbp",
            "mov rcx, rsi",
            f"call 0x{helper_pointer:x}",
        ],
        check="object-post:raw-sound-event-to-helper",
    )
    _require_ordered(
        helper_rows,
        [
            "mov rbx, rcx",
            "cmp [rbx+0x10], esi",
            "mov rcx, rbx",
            f"call 0x{bodies['computeString'].pointer:x}",
            "mov ecx, eax",
            f"call 0x{post_pointer:x}",
        ],
        check="object-post-helper:full-string-compute-and-post",
    )
    _require_ordered(
        bodies["doPostEventAtPosition"].rows,
        [
            f"mov rax, [rdi+0x{data_offset:x}]",
            f"mov rbx, [rax+0x{sound_offset:x}]",
            "mov rcx, rbx",
            f"call 0x{bodies['postAtPositionString'].pointer:x}",
        ],
        check="position-post:raw-sound-event-to-string-overload",
    )
    _require_ordered(
        bodies["postAtPositionString"].rows,
        [
            "mov rbx, rcx",
            "cmp [rbx+0x10], 0x0",
            "mov rcx, rbx",
            f"call 0x{bodies['computeString'].pointer:x}",
            "mov ecx, eax",
            f"call 0x{pos_uint.pointer:x}",
        ],
        check="position-string-overload:full-string-compute-and-post",
    )
    _require_ordered(
        bodies["computeString"].rows,
        [
            "mov rbx, rcx",
            "lea rax, [rbx+0x14]",
            "mov eax, [rbx+0x10]",
            "movzx edx, [r8]",
            "lea rax, [rdx-0x41]",
            "cmp eax, 0x19",
            "add r8, 0x2",
            "cmp ecx, r9d",
        ],
        check="compute-string:whole-utf16-loop-and-ascii-fold",
    )
    return {
        "methodCount": len(bodies),
        "methods": {
            key: {"type": spec["type"], "method": spec["method"],
                  "rva": spec["rva"], "bodySha256": spec["bodySha256"]}
            for key, spec in contract["methods"].items()
        },
        "actionDataPointerOffset": data_offset,
        "soundEventFieldOffset": sound_offset,
        "anonymousPostHelperRva": contract["anonymousPostHelper"]["rva"],
        "checkedRoutes": ["objectPostDefaultBody", "positionPostDefaultBody"],
        "patchBoundary": "iFix IsPatched prologues; replacement path not checked",
    }


def _hirc_membership(path: Path, raw_hash: int, stripped_hash: int) -> dict[str, Any]:
    raw = path.read_bytes()
    source = json.loads(raw)
    inventory = source.get("wwiseEventInventory")
    counts = source.get("counts") or {}
    if not isinstance(inventory, list) or len(inventory) != counts.get("wwiseEventObjectOccurrences"):
        raise NativeProofError("audio-source-index:hirc-occurrence-count-mismatch")
    if any(
        not isinstance(row, dict) or not isinstance(row.get("eventHash"), int)
        for row in inventory
    ):
        raise NativeProofError("audio-source-index:malformed-hirc-event-hash")
    matching = [
        {"eventHash": row.get("eventHash"), "eventId": row.get("eventId"),
         "bank": row.get("bank")}
        for row in inventory
        if isinstance(row, dict) and row.get("eventHash") in {raw_hash, stripped_hash}
    ]
    return {
        "sourcePath": str(path),
        "sourceSha256": hashlib.sha256(raw).hexdigest(),
        "eventEvidenceSchemaVersion": source.get("eventEvidenceSchemaVersion"),
        "auditedHircEventOccurrences": len(inventory),
        "rawLiteralEventObjectCount": sum(row["eventHash"] == raw_hash for row in matching),
        "hypotheticalTrimmedEventObjectCount": sum(
            row["eventHash"] == stripped_hash for row in matching
        ),
        "matchingObjects": matching,
        "evidenceBoundary": "Membership in this generated scanned-bank HIRC inventory only; bank loading and runtime posting outcome unresolved.",
    }


def audit(
    *, gameassembly: Path, metadata: Path,
    event_literal: str | None = None,
    audio_source_index: Path | None = None,
    contract_path: Path = CONTRACT_PATH,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "endfield.audio-play-sound-string-native-audit.v1",
        "status": "validation_failed",
        "contractPath": str(contract_path),
    }
    try:
        contract, _digest = read_reviewed_contract(
            contract_path, schema=SCHEMA, label="audio-play-sound-string",
            status="exact-pinned-build",
        )
        expected = contract["nativeInputs"]
        expected_gameassembly = expected["GameAssembly.dll"]
        expected_metadata = expected["global-metadata.dat"]
    except (OSError, ValueError, TypeError, KeyError) as error:
        result["detail"] = f"contract:{type(error).__name__}:{error}"[:500]
        return result
    gate = check_installed_native_inputs(
        expected_gameassembly,
        expected_metadata,
        gameassembly=gameassembly, metadata=metadata,
    )
    result.update({
        "status": gate.status,
        "nativeInputs": {
            "GameAssembly.dll": gate.gameassembly_sha256,
            "global-metadata.dat": gate.metadata_sha256,
        },
    })
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        result["detail"] = gate.detail
        return result
    try:
        image = NativeImage(gameassembly, metadata, label="audio-play-sound-string")
        result["routeProof"] = _prove_routes(BodyIndex(image), image, contract)
        if event_literal is not None:
            stripped = event_literal.strip()
            raw_hash = audio_hash_generator_compute(event_literal)
            stripped_hash = audio_hash_generator_compute(stripped)
            result["literalQuery"] = {
                "rawLiteral": event_literal,
                "rawHash": raw_hash,
                "rawHashHex": f"0x{raw_hash:08x}",
                "hypotheticalTrimmedLiteral": stripped,
                "hypotheticalTrimmedHash": stripped_hash,
                "hypotheticalTrimmedHashHex": f"0x{stripped_hash:08x}",
                "nativeDefaultRouteUses": "rawHash",
            }
            if audio_source_index is not None:
                result["hircMembership"] = _hirc_membership(
                    audio_source_index, raw_hash, stripped_hash
                )
        result["evidenceBoundary"] = contract["evidenceBoundary"]
        result["status"] = "validated"
    except (ValueError, RuntimeError, OSError, KeyError, IndexError, TypeError) as error:
        result["status"] = "validation_failed"
        result["detail"] = str(error)[:500]
        result.pop("routeProof", None)
        result.pop("literalQuery", None)
        result.pop("hircMembership", None)
        result.pop("evidenceBoundary", None)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--event-literal")
    parser.add_argument("--audio-source-index", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    if args.audio_source_index and args.event_literal is None:
        parser.error("--audio-source-index requires --event-literal")
    result = audit(
        gameassembly=args.gameassembly, metadata=args.metadata,
        event_literal=args.event_literal,
        audio_source_index=args.audio_source_index,
    )
    print(f"play-sound-string-native: {result['status']}: {result.get('detail', 'checked default routes')}")
    if result["status"] == "validated":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        return 0
    return 1 if result["status"] == "validation_failed" else 0


if __name__ == "__main__":
    sys.exit(main())

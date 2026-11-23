"""Validate the selected PlaySound string-to-hash default native routes.

The reviewed contract pins method identities and bytes for one installed
GameAssembly/metadata pair. The dynamic witnesses below also require the
serialized ``_soundEvent`` field to reach one anonymous string-hash body
through the checked object and position branches. iFix replacement and
runtime execution are outside this static proof.

The audit covers the unpatched PlaySound object and position routes from the
serialized sound string to the posted integer, fails closed on a different
native pair, and writes ``reports/audio/play_sound_string_native.json``. The
optional ``--event-literal`` and ``--audio-source-index`` compare the raw and
hypothetically trimmed hashes with one scanned HIRC inventory; that comparison
does not observe live posting.

The checked routes, both reached from ``PlaySoundAction._DoPlaySound``:

* object branch: reads ``PlaySoundActionData._soundEvent`` and passes that
  pointer to an anonymous post helper, which calls the string hash and sends
  the integer to ``AudioAdapter._PostEvent``;
* position branch: passes the same field to
  ``AudioBattleUtil.PostEventAtPositionWithMixingType(string, ...)``, which
  calls the same string hash and forwards the integer to its UInt32
  position-post overload.

Since the build that moved strings into the JsonData StringPool, neither
route calls ``AudioHashGenerator.Compute(string)``; both call one unnamed
body (``anonymousStringHash``). Its byte witnesses (FNV-1 offset basis and
prime, ``A``-``Z`` range test, ``+0x20`` fold) and ordered rows prove it
returns 0 for a null or empty string and otherwise hashes every UTF-16 unit
with ASCII uppercase folded and nothing trimmed -- the same semantics as
``Compute``. So these default bodies keep a trailing space through hashing.
The ``SkillData/eny_0080_reaper_skill_left`` sound string ends in a space:
raw and trimmed spellings hash differently and, in the scanned CN HIRC set,
only the trimmed id is an Event object. That is a counterexample to silently
trimming authored strings, not proof of which branch ran or what Wwise did
with a post.

``_DoPostEvent`` also has a conditional pre-branch that posts an
``AudioGlobalConfig`` Event id before the checked call; it is listed as
unresolved in the contract and not validated here.

Both methods test iFix patch state before their default bodies. A
MD5-verified dump of the installed ``IFixPatchOut`` set declares no
replacement target for the named methods (see
``memory/game_data/ifix_patch.md``); that narrows the shipped-patch
alternative without observing runtime patch state or ruling out another patch
source. Other PlaySound routes are not covered, and neither finding promotes
the trimmed spelling to a runtime Event identity.
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
SCHEMA = "endfield.audio-play-sound-string-native.v2"
DEFAULT_OUTPUT = REPO_ROOT / "reports/audio/play_sound_string_native.json"


# Byte witnesses for the hash loop. The FNV prime multiply and the 16-bit
# A-Z range compare decode as raw bytes in the instruction index, so they are
# matched on the selected body bytes instead.
HASH_BYTE_WITNESSES = (
    ("fnv1-offset-basis", "41b8c59d1c81"),          # mov r8d, 0x811c9dc5
    ("ascii-upper-range", "418d51bf6683fa19"),      # lea edx,[r9-0x41]; cmp dx,0x19
    ("fnv1-prime-multiply", "4569c093010001"),      # imul r8d, r8d, 0x01000193
    ("fnv1-xor-char", "4533c1"),                    # xor r8d, r9d
    ("ascii-fold-add", "4183c120"),                 # add r9d, 0x20
)


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
    hash_pointer, hash_rows = _checked_helper(
        index, image, contract["anonymousStringHash"]
    )
    hash_bytes = image.pe.bytes_at_va(hash_pointer, int(contract["anonymousStringHash"]["bodyLength"]))
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
            f"mov rax, [rdi+0x{data_offset:x}]",
            f"mov rbx, [rax+0x{sound_offset:x}]",
            "mov rdx, rbp",
            "mov rcx, rbx",
            f"call 0x{helper_pointer:x}",
        ],
        check="object-post:raw-sound-event-to-helper",
    )
    _require_ordered(
        helper_rows,
        [
            "mov rdi, rcx",
            "mov rcx, rdi",
            f"call 0x{hash_pointer:x}",
            "mov ecx, eax",
            f"call 0x{post_pointer:x}",
        ],
        check="object-post-helper:full-string-hash-and-post",
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
            "mov rsi, rcx",
            "mov rcx, rsi",
            f"call 0x{hash_pointer:x}",
            "mov ecx, eax",
            f"call 0x{pos_uint.pointer:x}",
        ],
        check="position-string-overload:full-string-hash-and-post",
    )
    _require_ordered(
        hash_rows,
        [
            "mov rbx, rcx",
            "test rcx, rcx",
            "cmp [rcx+0x10], 0x0",
            "mov r10d, [rbx+0x10]",
            "lea rax, [rbx+0x14]",
            "mov r8d, 0x811c9dc5",
            "movzx r9d, [rax]",
            "lea rdx, [r9-0x41]",
            "add rax, 0x2",
            "xor r8d, r9d",
            "cmp ecx, r10d",
            "mov eax, r8d",
            "add r9d, 0x20",
        ],
        check="string-hash:whole-utf16-fnv1-loop-and-ascii-fold",
    )
    for label, encoded in HASH_BYTE_WITNESSES:
        if hash_bytes.count(bytes.fromhex(encoded)) != 1:
            raise NativeProofError(f"string-hash:byte-witness-missing={label}")
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
        "anonymousStringHashRva": contract["anonymousStringHash"]["rva"],
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
        "schema": "endfield.audio-play-sound-string-native-audit.v2",
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

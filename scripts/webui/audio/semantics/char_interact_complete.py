"""Project whole-current CharInteract actions inside an authenticated batch.

The complete public reader proves the root, selected union routes and each
concrete AudioEventActData child. Projection grants no authority by itself;
retain its rows only after native/source/pool exit and source-ledger checks.
Authored actions do not prove runtime activation, actor selection or playback.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Callable

from scripts.game_data.char_interact_perform_binary import complete_perform_reader
from scripts.game_data.jsondata_source_provenance import authenticate_current_jsondata_source_inventory
from scripts.game_data.string_pool import export_string_pool
from scripts.source_paths import ExportLayout

AUDIO_TYPE = "Beyond.Gameplay.Core.CharInteractPerform.AudioEventActData"
ACTION_TYPE = "Beyond.Gameplay.Core.CharInteractPerform.CharInteractPerformActionData"


def require(condition, message):
    if not condition:
        raise ValueError("CharInteract Audio: " + message)


def fresh_sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_audio_actions(frame):
    """Pure projection of concrete actions from a complete reader result."""
    require(frame.get("wholeSchemaExact") is True and frame.get("physicalEOF") is True
            and frame.get("serializedMemberCount") == 28 and len(frame.get("fields", [])) == 28,
            "whole current root and physical EOF required")
    records = frame.get("records")
    require(isinstance(records, list), "complete nested records required")
    expected = {(r["start"], r["end"]) for r in records
                if r.get("typeName") == AUDIO_TYPE and r.get("isNull") is False}
    found = set()
    output = []
    for container in records:
        elements = container.get("elements")
        if not isinstance(elements, list):
            continue
        for index, union in enumerate(elements):
            if not isinstance(union, dict) or union.get("isNull") is True:
                continue
            child = union.get("child")
            if not isinstance(child, dict) or child.get("typeName") != AUDIO_TYPE or child.get("isNull") is True:
                continue
            require(union.get("typeName") == ACTION_TYPE and type(union.get("tag")) is int,
                    "AudioEvent child must belong to a proved action union")
            start, end = child["start"], child["end"]
            require(0 <= union["start"] < start < end == union["end"] <= frame["bytesConsumed"],
                    "action byte range is outside its owner")
            require((start, end) in expected and (start, end) not in found, "duplicate or unowned concrete action")
            root_fields = [f for f in frame["fields"] if f["start"] <= union["start"] and end <= f["end"]]
            require(len(root_fields) == 1, "action must have one exact root-field placement")
            fields = child.get("fields", [])
            require(len(fields) == 20 and len({f.get("fieldName") for f in fields}) == 20,
                    "complete twenty-field AudioEventActData required")
            named = {f["fieldName"]: f for f in fields}
            require({"audioEvent", "logicId", "delay", "duration", "devOnly", "useEvent", "eventId",
                     "attachedActorType", "charIndex", "endStop", "is2D"} <= set(named),
                    "required native AudioEvent fields are missing")
            def raw(name, kind, size):
                field = named[name]
                require(field.get("kind") == kind and start < field["start"] < field["end"] <= end
                        and field["end"] - field["start"] == size, "invalid native field range: " + name)
                encoded = field.get("rawHex", "")
                require(isinstance(encoded, str) and len(encoded) == size * 2, "invalid raw field: " + name)
                value = bytes.fromhex(encoded)
                require(len(value) == size, "invalid raw field width: " + name)
                return value
            def number(name, signed=False):
                return int.from_bytes(raw(name, "scalar32", 4), "little", signed=signed)
            def flag(name):
                return raw(name, "bool-byte", 1)[0] != 0
            def floating(name):
                value = struct.unpack("<f", raw(name, "float32-bits", 4))[0]
                return value if math.isfinite(value) else None
            event = named["eventId"]
            require(event.get("kind") == "byte-payload" and (event.get("value") is None or isinstance(event.get("value"), str)),
                    "native pooled eventId required")
            output.append(dict(
                placement=root_fields[0]["fieldName"], actionIndex=index,
                audioEvent=int.from_bytes(raw("audioEvent", "audio-id-raw4", 4), "little"),
                logicId=number("logicId"), delay=floating("delay"), duration=floating("duration"),
                devOnly=flag("devOnly"), useEvent=flag("useEvent"), eventId=event.get("value"),
                attachedActorType=number("attachedActorType"), charIndex=number("charIndex", signed=True),
                endStop=flag("endStop"), is2D=flag("is2D"),
                sourceOffset=union["start"], endOffset=end, unionTag=union["tag"],
                unionTagHex=f"0x{union['tag']:04x}", memberCount=20,
                schemaMappingId=frame.get("schemaMappingId"), unionMappingId=union.get("kind"),
                schemaStatus="named_exact", storedFields=fields,
            ))
            found.add((start, end))
    require(found == expected, "an AudioEvent record lacks a proved containing action-list route")
    return output


def collect_complete(export_root, *, gameassembly, metadata, collector: Callable):
    require(gameassembly is not None and metadata is not None, "explicit GameAssembly and metadata paths required")
    layout = ExportLayout(Path(export_root).resolve()).require()
    summary_path = layout.evidence_dir / "animestudio/jsondata_source_current.json"
    ledger_path = layout.evidence_dir / "animestudio/jsondata_source_files_current.jsonl.gz"
    summary_raw = summary_path.read_bytes()
    summary = json.loads(summary_raw)
    require(Path(summary.get("exportRoot", "")).resolve() == layout.root.resolve()
            and Path(summary.get("jsonRoot", "")).resolve() == layout.json_dir.resolve(),
            "source inventory must belong to the selected export")
    ledger_sha = fresh_sha(ledger_path)
    expected = {}
    prefix = "CharInteractPerformCfgs/"
    with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            key = row.get("exportRelativePath", "")
            if not key.startswith(prefix):
                continue
            name = key[len(prefix):]
            require(name and Path(name).name == name and name not in expected,
                    "duplicate or invalid selected owner identity")
            require(row.get("family") == "CharInteractPerformCfgs" and row.get("status") == "source-bytes-verified",
                    "unverified selected source owner")
            digest = row.get("logicalSha256", "").lower()
            require(len(digest) == 64 and all(c in "0123456789abcdef" for c in digest), "invalid source digest")
            expected[name] = digest
    require(bool(expected) and len(expected) == summary.get("summary", {}).get("familyCounts", {}).get("CharInteractPerformCfgs"),
            "complete nonempty selected CharInteract universe required")
    directory = layout.json_dir / "CharInteractPerformCfgs"
    def roster():
        return {p.name: fresh_sha(p) for p in directory.glob("*.json") if p.is_file()}
    require(roster() == expected, "selected physical source roster or bytes differ from the ledger")
    with complete_perform_reader(gameassembly=Path(gameassembly), metadata=Path(metadata),
                                 strings=export_string_pool(layout.json_dir)) as read:
        result = collector(lambda data: project_audio_actions(read(data)), expected)
        stats = result.get("stats", {})
        require(stats.get("status") == "complete" and stats.get("decodedOwners") == len(expected)
                and stats.get("candidateOwners") == len(expected) and not stats.get("failureSamples"),
                "complete decoding failed: " + json.dumps(stats.get("failureSamples", [])[:3]))
    receipt = read.receipt
    require(receipt.get("status") == "validated-current-raw-animation-operation"
            and receipt.get("wholeCharInteractAdmitted") is True
            and receipt.get("nativeSourcePoolExitBookendsPassed") is True, "complete native exit receipt required")
    require(roster() == expected and summary_path.read_bytes() == summary_raw and fresh_sha(ledger_path) == ledger_sha,
            "source inputs changed during complete decoding")
    authentication = dict(
        summary_path=summary_path, ledger_path=ledger_path,
        expected_summary_sha256=hashlib.sha256(summary_raw).hexdigest().upper(),
        native_sources={"GameAssembly.dll": str(Path(gameassembly).resolve()),
                        "global-metadata.dat": str(Path(metadata).resolve())},
        native_inputs=receipt["nativeInputs"],
    )
    inventory = authenticate_current_jsondata_source_inventory(**authentication)
    require(inventory.get("sourceInventoryAuthenticated") is True and summary_path.read_bytes() == summary_raw
            and fresh_sha(ledger_path) == ledger_sha and roster() == expected, "final selected source authentication failed")
    confirmed = authenticate_current_jsondata_source_inventory(**authentication)
    require(confirmed == inventory and summary_path.read_bytes() == summary_raw
            and fresh_sha(ledger_path) == ledger_sha and roster() == expected,
            "selected source authentication changed before publication")
    result["stats"].update(completeNativeReader=True, nativeOperationReceipt=receipt,
        sourceInventoryAuthenticated=True, selectedOwnerRosterComplete=True,
        sourceInventorySummarySha256=hashlib.sha256(summary_raw).hexdigest(),
        wholeOwnerEOFVerified=len(expected))
    return result

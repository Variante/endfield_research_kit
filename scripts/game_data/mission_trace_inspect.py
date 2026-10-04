"""Verify and decode a retained EndfieldCapture mission package without a game.

Run as ``python -m scripts.game_data.mission_trace_inspect --session PATH
--output-dir reports/runtime_capture/inspection``. Optional ``--join-sources``
adds explicit archived questDic-to-missionId assignments, never causal joins.
Package hashes authenticate consistency with its retained inventory, not its
origin, native ABI, hook execution, or the correctness of server behavior.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import struct
from typing import Any

from scripts.repo_paths import REPO_ROOT


class InspectionError(ValueError):
    """Retained data is unsafe, inconsistent, malformed, or exceeds a bound."""


@dataclass(frozen=True)
class Limits:
    artifacts: int = 20000
    artifact_bytes: int = 16 * 1024**3
    package_bytes: int = 32 * 1024**3
    json_bytes: int = 32 * 1024**2
    journal_bytes: int = 8 * 1024**3
    rows: int = 1000000
    input_line_bytes: int = 16 * 1024
    output_line_bytes: int = 64 * 1024
    output_bytes: int = 2 * 1024**3
    identifiers: int = 65536


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise InspectionError(detail)


def integer(value: Any, label: str, maximum: int = (1 << 64) - 1) -> int:
    require(type(value) is int and 0 <= value <= maximum, f"invalid unsigned integer: {label}")
    return value


def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in items:
        require(key not in result, f"duplicate JSON key: {key[:100]}")
        result[key] = value
    return result


def parse_json(data: bytes, label: str) -> Any:
    def finite_float(text: str) -> float:
        value = float(text)
        require(math.isfinite(value), "nonfinite JSON number")
        return value

    try:
        return json.loads(data, object_pairs_hook=pairs,
                          parse_float=finite_float,
                          parse_constant=lambda value: require(False, f"nonfinite JSON number: {value}"))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise InspectionError(f"invalid JSON: {label}: {str(exc)[:512]}") from exc


def safe_path(root: Path, name: Any, *, existing: bool = True) -> Path:
    require(isinstance(name, str) and 0 < len(name) <= 512, "invalid artifact path")
    parts = name.split("/")
    require(not PurePosixPath(name).is_absolute() and all(part not in ("", ".", "..") for part in parts),
            f"unsafe artifact path: {name}")
    require(not any(char in name for char in '\\:< >"|?*\0'.replace(" ", "")), f"unsafe artifact path: {name}")
    require(all(not part.endswith((".", " ")) and not re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part)
                for part in parts), f"unsafe Windows artifact path: {name}")
    candidate = root.joinpath(*parts)
    resolved = candidate.resolve(strict=existing)
    require(resolved.is_relative_to(root) and resolved != root, f"artifact escaped package: {name}")
    if existing:
        require(resolved.is_file(), f"artifact is not a file: {name}")
    return resolved


def read_bytes(path: Path, limit: int) -> bytes:
    require(path.stat().st_size <= limit, f"input byte budget exceeded: {path.name}")
    with path.open("rb") as source:
        data = source.read(limit + 1)
    require(len(data) <= limit, f"input grew past byte budget: {path.name}")
    return data


def read_object(path: Path, limit: int) -> dict[str, Any]:
    value = parse_json(read_bytes(path, limit), path.name)
    require(isinstance(value, dict), f"expected JSON object: {path.name}")
    return value


def verify_inventory(session: Path, limits: Limits) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    inventory_path = safe_path(session, "collected/inventory.json")
    inventory = read_object(inventory_path, limits.json_bytes)
    require(inventory.get("schema") == "endfieldCapture.collection.v1", "unsupported collection inventory schema")
    require(isinstance(inventory.get("session"), str) and 0 < len(inventory["session"]) <= 127, "invalid inventory session identity")
    artifacts = inventory.get("artifacts")
    require(isinstance(artifacts, list) and 0 < len(artifacts) <= limits.artifacts, "artifact count budget exceeded")
    require(inventory.get("files") == len(artifacts), "inventory file count mismatch")
    result, targets, total = {}, set(), 0
    for row in artifacts:
        require(isinstance(row, dict), "invalid inventory row")
        name = row.get("path")
        path = safe_path(session, name)
        target = str(path).casefold()
        require(name not in result and target not in targets, f"duplicate artifact path or alias: {name}")
        targets.add(target)
        size = integer(row.get("bytes"), f"artifact bytes: {name}", limits.artifact_bytes)
        digest = row.get("sha256")
        require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
                f"invalid artifact SHA256: {name}")
        total += size
        require(total <= limits.package_bytes, "package hash byte budget exceeded")
        before = path.stat()
        require(before.st_size == size, f"artifact size mismatch: {name}")
        actual, length = hashlib.sha256(), 0
        with path.open("rb") as source:
            while block := source.read(1024 * 1024):
                length += len(block)
                require(length <= size, f"artifact grew while hashing: {name}")
                actual.update(block)
        after = path.stat()
        require(length == size and (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
                f"artifact changed while hashing: {name}")
        require(actual.hexdigest() == digest, f"artifact SHA256 mismatch: {name}")
        result[name] = {"path": path, "bytes": size, "sha256": digest}
    require(inventory.get("bytes") == total, "inventory total bytes mismatch")
    return result, {"artifacts": len(result), "bytes": total,
                    "sessionId": inventory["session"],
                    "inventorySha256": hashlib.sha256(read_bytes(inventory_path, limits.json_bytes)).hexdigest(),
                    "verifiedAgainstRetainedInventory": True, "inventoryOriginAuthenticated": False}


def bound_object(artifacts: dict[str, dict[str, Any]], name: str, limits: Limits) -> dict[str, Any]:
    require(name in artifacts, f"required artifact is not collection-bound: {name}")
    value = parse_json(bound_bytes(artifacts, name, limits.json_bytes), name)
    require(isinstance(value, dict), f"expected JSON object: {name}")
    return value


def bound_bytes(artifacts: dict[str, dict[str, Any]], name: str, limit: int) -> bytes:
    require(name in artifacts, f"required artifact is not collection-bound: {name}")
    row = artifacts[name]
    data = read_bytes(row["path"], limit)
    require(len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"],
            f"bound artifact changed before decoding: {name}")
    return data


def program(hook: dict[str, Any]) -> list[list[int]]:
    text = hook.get("readProgram")
    require(isinstance(text, str) and len(text) <= 512 and (not text or text.endswith(";")), "invalid readProgram")
    result = []
    for item in text.rstrip(";").split(";") if text else []:
        require(re.fullmatch(r"\d+,\d+,\d+,\d+,\d+", item) is not None, "invalid readProgram row")
        arg, kind, offset, chain0, chain1 = map(int, item.split(","))
        require(arg <= 7 and 1 <= kind <= 5 and offset <= 4096 and chain0 <= 4097 and chain1 <= 4097,
                "readProgram bounds exceeded")
        require(chain0 != 4097 or chain1 == 4097, "readProgram second chain lacks first chain")
        require(kind != 4 or (offset == 0 and chain0 == chain1 == 4097), "scalar readProgram has memory path")
        result.append([arg, kind, offset, chain0, chain1])
    require(len(result) <= 8, "readProgram field count exceeded")
    return result


def bindings(artifacts: dict[str, dict[str, Any]], limits: Limits) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    profile = bound_object(artifacts, "private/mission-trace-build-manifest.json", limits)
    summary = bound_object(artifacts, "mission-trace/summary.json", limits)
    session = bound_object(artifacts, "session.json", limits)
    require(profile.get("schema") == "endfieldCapture.missionTraceBuild.v1", "unsupported retained profile schema")
    require(summary.get("schema") in ("endfieldCapture.missionTraceSummary.v1", "endfieldCapture.missionTraceSummary.v2"),
            "unsupported provider summary schema")
    require(session.get("schema") == "endfieldCapture.session.v1" and profile.get("profile") == "mission-trace" and
            session.get("providers") == 128 and session.get("gameBuild") == profile.get("gameBuild"), "session/profile binding mismatch")
    hooks, summary_hooks = profile.get("missionTraceHooks"), summary.get("hooks")
    require(isinstance(hooks, list) and 0 < len(hooks) <= 96 and isinstance(summary_hooks, list), "hook count bounds exceeded")
    require(len(hooks) == len(summary_hooks) == summary.get("hookCount"), "profile/summary hook count mismatch")
    files = profile.get("files", {})
    require(isinstance(files, dict) and all(isinstance(files.get(key), dict) for key in ("gameAssembly", "metadata")),
            "invalid profile native inputs")
    hashes = []
    for key, receipt in (("gameAssembly", "gameAssemblySha256"), ("metadata", "metadataSha256")):
        digest = files.get(key, {}).get("sha256")
        require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None and summary.get(receipt) == digest,
                f"profile/summary native input binding mismatch: {key}")
        hashes.append(digest)
    activation = ("schema=missionRuntimeTrace.activation.v1\ngame_assembly_sha256=" + hashes[0] +
                  "\nmetadata_sha256=" + hashes[1] + "\nhook_count=" + str(len(hooks)) + "\n")
    names, rvas = set(), set()
    for index, (hook, receipt) in enumerate(zip(hooks, summary_hooks)):
        require(isinstance(hook, dict) and isinstance(receipt, dict), "invalid hook descriptor")
        name = hook.get("name")
        require(isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_.$<>+`-]{1,127}", name) is not None and name not in names, "invalid or repeated hook name")
        names.add(name)
        try:
            rva = int(hook["rva"], 16) if isinstance(hook.get("rva"), str) else integer(hook.get("rva"), "hook RVA")
        except (ValueError, KeyError) as exc:
            raise InspectionError("invalid hook RVA") from exc
        require(0 < rva < 1 << 32 and rva not in rvas, "invalid or repeated hook RVA")
        rvas.add(rva)
        require(hook.get("module") == "GameAssembly.dll" and hook.get("abiId") == "win64.transparent_entry_snapshot.v1", "unsupported hook ABI/module")
        expected = hook.get("expectedBytes")
        require(isinstance(expected, str) and re.fullmatch(r"(?:[0-9a-f]{2}){16,256}", expected) is not None, "invalid native prefix")
        reads = program(hook)
        fields = hook.get("fields")
        require(isinstance(fields, list) and len(fields) == len(reads), "retained typed field metadata missing")
        labels = set()
        for field, read in zip(fields, reads):
            require(isinstance(field, dict) and isinstance(field.get("label"), str) and 0 < len(field["label"]) <= 127,
                    "invalid field label")
            require(field["label"] not in labels, "repeated field label")
            labels.add(field["label"])
            require([field.get(key) for key in ("arg", "kind", "offset", "chain0", "chain1")] == read, "field/readProgram binding mismatch")
            require(isinstance(field.get("type"), str) and len(field["type"]) <= 256, "invalid field type")
            require(field.get("valueBits") in (None, 8, 16, 32, 64), "unsupported field width")
            representation = field.get("valueRepresentation")
            require(representation in (None, "referenceIdentity"), "unsupported value representation")
            if representation == "referenceIdentity":
                require(profile.get("recipeSchema") == "endfield.mission-trace-capture-recipe.v4"
                        and field.get("valueBits") == 64 and field.get("kind") in (1, 4)
                        and field.get("storageType") == "ulong" and field.get("signed") is False,
                        "invalid reference identity binding")
            path = field.get("fieldPath", [])
            require(isinstance(path, list) and len(path) <= 8 and all(isinstance(part, dict) and
                    isinstance(part.get("field"), str) and len(part["field"]) <= 512 for part in path), "invalid typed field path")
        require(receipt.get("index") == index and receipt.get("name") == name and receipt.get("rva") == rva and receipt.get("reads") == reads,
                "profile/summary hook binding mismatch")
        integer(receipt.get("calls"), "hook calls")
        activation += f"hook={name}|{rva:x}|{hook['abiId']}|{expected}|{hook['readProgram']}\n"
    activation_name = "private/mission-trace.activation"
    require(activation_name in artifacts and bound_bytes(artifacts, activation_name, 128 * 1024) == activation.encode("ascii"),
            "activation/profile binding mismatch")
    config_name = "private/runtime.conf"
    require(config_name in artifacts, "runtime config is not collection-bound")
    config = {}
    for line in bound_bytes(artifacts, config_name, 64 * 1024).decode("utf-8").splitlines():
        require("=" in line, "malformed runtime config")
        key, value = line.split("=", 1)
        require(key not in config, "duplicate runtime config key")
        config[key] = value
    require(config.get("schema") == "endfieldCapture.runtime.v1" and config.get("provider_mask") == "128", "runtime provider binding mismatch")
    portable = lambda value: re.sub(r"/+", "/", value.replace("\\", "/")).rstrip("/").casefold()
    require("session_root" in config and portable(config.get("mission_activation_manifest", "")) ==
            portable(config["session_root"] + "/private/mission-trace.activation"), "runtime activation path binding mismatch")
    if "session_name" in config:
        require(config["session_name"] == session.get("sessionId"), "runtime session name mismatch")
    if "session_id" in config:
        require(config["session_id"] == str(session.get("numericSessionId")), "runtime numeric session ID mismatch")
    dll = artifacts.get("private/EndfieldCapture.dll")
    if dll and "runtimeSha256" in session:
        require(session["runtimeSha256"] == dll["sha256"] and session.get("runtimeBytes") == dll["bytes"], "staged runtime identity mismatch")
    return profile, summary, hooks


PRIMITIVES = {"bool": (8, False), "byte": (8, False), "sbyte": (8, True), "short": (16, True),
              "ushort": (16, False), "int": (32, True), "uint": (32, False), "long": (64, True), "ulong": (64, False)}


def decode_field(field: dict[str, Any], observed: dict[str, Any], enums: dict[str, Any]) -> dict[str, Any]:
    state = integer(observed.get("state"), "field state", 4)
    require(state > 0, "uninitialized observed field")
    raw = integer(observed.get("value"), "raw field value")
    kind = field["kind"]
    if state == 1:
        require(kind != 2 or raw <= 0xFFFFFFFF, "memory u32 observation exceeds physical read width")
        require(kind != 5 or raw <= 0xFF, "memory u8 observation exceeds physical read width")
    decoded = {"label": field["label"], "type": field["type"], "state": state,
               "stateName": {1: "exact", 2: "unreadable", 3: "truncated", 4: "observedNull"}[state], "raw64": raw,
               "read": {key: field[key] for key in ("arg", "kind", "offset", "chain0", "chain1")},
               "fieldPath": field.get("fieldPath", [])}
    for key in ("storageType", "signed", "argumentName", "role", "observation", "argumentRepresentation", "valueRepresentation"):
        if key in field:
            decoded[key] = field[key]
    if state == 4:
        require(raw == 0 and "text" not in observed and (kind == 3 or field["chain0"] != 4097), "invalid observed null")
        decoded.update(value=None, interpretation="Observed null string or absent carrier; ownership remains unresolved.")
        return decoded
    if kind == 3:
        text = observed.get("text")
        require(isinstance(text, str), "string observation lacks bounded text")
        units = len(text.encode("utf-16-le", errors="surrogatepass")) // 2
        require(units <= 160, "string observation exceeds UTF16 bound")
        require(raw <= 1024 * 1024, "string length exceeds native sampler bound")
        if state == 1:
            require(units == raw, "exact string length mismatch")
        elif state == 3:
            require(raw > 160 and units == 160, "truncated string length mismatch")
        decoded.update(utf16Length=raw, text=text, value=text if state == 1 else None)
        return decoded
    require("text" not in observed and state != 3, "invalid scalar observation")
    if state == 2:
        decoded.update(value=None)
        return decoded
    name, bits = field["type"], field.get("valueBits")
    definition = enums.get(name)
    primitive = PRIMITIVES.get(name)
    if bits is None:
        decoded.update(value=None, interpretation="No retained scalar width; raw value only.")
        return decoded
    require(bits in (8, 16, 32, 64), "unsupported scalar width")
    masked = raw & ((1 << bits) - 1)
    decoded.update(valueBits=bits, maskedUnsigned=masked)
    if name == "float":
        if kind == 2 and bits == 32:
            value = struct.unpack("<f", masked.to_bytes(4, "little"))[0]
            decoded.update(value=value if math.isfinite(value) else None, floatBits=f"0x{masked:08x}",
                           floatClass="finite" if math.isfinite(value) else ("nan" if math.isnan(value) else "infinity"))
        else:
            decoded.update(value=None, interpretation="Unsupported float carrier; GP values are not XMM arguments.")
        return decoded
    if definition is not None:
        require(isinstance(definition, dict) and definition.get("valueBits") == bits and type(definition.get("signed")) is bool,
                "invalid retained enum definition")
        signed = definition["signed"]
    elif primitive is not None:
        require(primitive[0] == bits, "primitive width mismatch")
        signed = primitive[1]
    else:
        signed = field.get("signed") if type(field.get("signed")) is bool else None
    value = masked - (1 << bits) if signed and masked & (1 << (bits - 1)) else masked
    decoded.update(value=value, signed=signed)
    if field.get("valueRepresentation") == "referenceIdentity":
        require(bits == 64 and signed is False, "invalid reference identity width/signedness")
        decoded.update(rawPointer=masked, nullReference=masked == 0,
                       interpretation="Same-process managed reference identity only; no pointee fields, stable cross-session identity or ownership inferred.")
    elif name == "bool":
        decoded.update(value=bool(masked), canonicalBool=masked in (0, 1))
    elif definition is not None:
        members = definition.get("members")
        require(isinstance(members, list) and len(members) <= 1024, "enum member budget exceeded")
        require(all(isinstance(member, dict) and type(member.get("value")) is int and isinstance(member.get("name"), str)
                    and len(member["name"]) <= 256 for member in members), "invalid enum members")
        decoded["enumNames"] = [member["name"] for member in members if member["value"] == value]
        decoded["enumSource"] = "retained profile enumDefinitions"
    elif primitive is None:
        decoded["interpretation"] = "Retained width only; enum names or storage signedness may be unavailable."
    return decoded


def source_bindings(session: Path, artifacts: dict[str, dict[str, Any]], limits: Limits, join: bool) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    inventory_name = "static-sources/inventory.json"
    path = session / inventory_name
    result = {"inventoryCollectionBound": inventory_name in artifacts, "copiedEntriesVerified": 0,
              "questAssignmentsRequested": join, "questAssignments": 0,
              "nativeSourceValidationReproved": False, "gaps": []}
    assignments: dict[str, list[dict[str, Any]]] = {}
    if not path.exists():
        result["gaps"].append("No retained static source inventory; source joins remain unresolved.")
        return result, assignments
    inventory = (bound_object(artifacts, inventory_name, limits) if inventory_name in artifacts else
                 read_object(safe_path(session, inventory_name), limits.json_bytes))
    require(inventory.get("schema") == "endfield.mission-source-archive.v1", "unsupported static source inventory")
    if inventory_name not in artifacts:
        result["gaps"].append("Static source inventory is not collection-hashed; its declarations are advisory. Source bytes are checked against collection hashes independently.")
    rows = inventory.get("files")
    require(isinstance(rows, list) and len(rows) <= limits.artifacts, "static source row budget exceeded")
    seen = set()
    for row in rows:
        require(isinstance(row, dict), "invalid source inventory row")
        source_name = row.get("sourceRelativePath")
        safe_path(session, source_name, existing=False)
        require(source_name not in seen, "repeated source inventory path")
        seen.add(source_name)
        if row.get("copied") is not True:
            continue
        name = "static-sources/" + str(row.get("archivedRelativePath", ""))
        safe_path(session, name)
        require(name == "static-sources/files/" + source_name and name in artifacts,
                f"source file is not collection-bound: {source_name}")
        bound = artifacts[name]
        require(row.get("sha256") == bound["sha256"] and row.get("bytes") == bound["bytes"],
                f"source inventory binding mismatch: {source_name}")
        result["copiedEntriesVerified"] += 1
        if not join or not source_name.startswith("game/Json/MissionRuntimeAsset/") or source_name.endswith("_meta.json"):
            continue
        data = bound_object(artifacts, name, limits)
        mission_id, quests = data.get("missionId"), data.get("questDic")
        require(isinstance(mission_id, str) and 0 < len(mission_id) <= 160 and isinstance(quests, dict), "invalid archived mission definition")
        for quest_id, quest in quests.items():
            require(isinstance(quest_id, str) and 0 < len(quest_id) <= 160 and isinstance(quest, dict) and quest.get("questId") == quest_id,
                    "archived quest key/identity mismatch")
            require(result["questAssignments"] < limits.identifiers, "quest assignment budget exceeded")
            assignments.setdefault(quest_id, []).append({"missionId": mission_id, "source": name, "sourceSha256": bound["sha256"],
                                                        "boundary": "explicit archived questDic membership; structuralOnly"})
            result["questAssignments"] += 1
    return result, assignments


def strict_receipt_consistent(receipt: Any, hooks: int) -> bool:
    if not isinstance(receipt, dict):
        return False
    return (all(type(receipt.get(key)) is int and receipt[key] == 0 for key in
                ("status", "failureStage", "rollbackFailureStage", "cleanupFailureStage", "windowsError", "rollbackWindowsError", "cleanupWindowsError",
                 "threadId", "rollbackThreadId", "cleanupThreadId"))
            and receipt.get("hookIndex") == receipt.get("rollbackHookIndex") == (1 << 32) - 1
            and receipt.get("rollbackAttempted") is False and receipt.get("cleanupSucceeded") is True
            and receipt.get("rollbackSucceeded") is True
            and receipt.get("pendingRecovery") is False
            and type(receipt.get("threadsSuspended")) is int and receipt["threadsSuspended"] >= 0
            and receipt.get("threadsResumed") == receipt.get("threadsEnumerated") == receipt["threadsSuspended"]
            and type(receipt.get("contextsChanged")) is int and 0 <= receipt["contextsChanged"] <= receipt["threadsSuspended"]
            and receipt.get("patchesChanged") == hooks)


def strict_preparation_retry_consistent(receipt: Any) -> bool:
    """Only a fully cleaned OpenThread/87 refusal before any suspension is retryable."""
    if not isinstance(receipt, dict):
        return False
    expected = {"status": 13, "failureStage": 3, "windowsError": 87,
                "hookIndex": (1 << 32) - 1, "rollbackHookIndex": (1 << 32) - 1}
    expected.update(dict.fromkeys(("rollbackFailureStage", "rollbackThreadId", "rollbackWindowsError",
                                  "cleanupFailureStage", "cleanupThreadId", "cleanupWindowsError",
                                  "threadsSuspended", "threadsResumed", "contextsChanged", "patchesChanged"), 0))
    return (all(type(receipt.get(key)) is int and receipt[key] == value for key, value in expected.items())
            and all(type(receipt.get(key)) is int and 0 < receipt[key] <= (1 << 32) - 1
                    for key in ("threadId", "threadsEnumerated"))
            and receipt.get("rollbackAttempted") is False and receipt.get("rollbackSucceeded") is True
            and receipt.get("cleanupSucceeded") is True and receipt.get("pendingRecovery") is False)


def strict_enable_history_consistent(summary: dict[str, Any], hooks: int) -> bool:
    if summary.get("schema") == "endfieldCapture.missionTraceSummary.v1":
        return "strictEnableHistory" not in summary and "strictEnableAttempts" not in summary
    attempts, history, final = summary.get("strictEnableAttempts"), summary.get("strictEnableHistory"), summary.get("strictEnable")
    return (type(attempts) is int and 1 <= attempts <= 3 and isinstance(history, list) and len(history) == attempts
            and all(strict_preparation_retry_consistent(receipt) for receipt in history[:-1])
            and isinstance(final, dict) and isinstance(history[-1], dict) and history[-1] == final
            and all(type(history[-1][key]) is type(final[key]) for key in final)
            and strict_receipt_consistent(history[-1], hooks))


def inspect_session(session: Path, output_dir: Path, *, join_sources: bool = False, limits: Limits = Limits()) -> dict[str, Any]:
    session, output_dir = Path(session).resolve(strict=True), Path(output_dir).resolve()
    require(session.is_dir(), "session is not a directory")
    require(any(output_dir.is_relative_to((REPO_ROOT / folder).resolve()) for folder in ("reports", "scratch", "tmp")),
            "output must be under ignored reports/, scratch/, or tmp/")
    require(not output_dir.is_relative_to(session) and not session.is_relative_to(output_dir), "output must be outside original package")
    require(not output_dir.exists() or (output_dir.is_dir() and not any(output_dir.iterdir())), "output directory must be new or empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"schema": "endfield.mission-trace-inspection.v1", "status": "failed", "session": str(session),
                             "budgets": asdict(limits), "nativeValidationReproved": False, "strictTransitionsReexecuted": False,
                             "boundary": "Entry observations and explicit retained metadata only; no success/return, causal ownership, file execution order, or server criteria inferred.",
                             "gaps": [], "decodedRows": 0}
    partial = output_dir / "decoded.events.partial.jsonl"
    try:
        artifacts, report["inventory"] = verify_inventory(session, limits)
        retained_session = bound_object(artifacts, "session.json", limits)
        require(retained_session.get("sessionId") == report["inventory"]["sessionId"], "collection/session identity mismatch")
        profile, summary, hooks = bindings(artifacts, limits)
        report["profileSha256"] = artifacts["private/mission-trace-build-manifest.json"]["sha256"]
        report["providerSummarySha256"] = artifacts["mission-trace/summary.json"]["sha256"]
        report["sources"], assignments = source_bindings(session, artifacts, limits, join_sources)
        coverage_gaps = profile.get("coverageGaps", [])
        require(isinstance(coverage_gaps, list) and len(coverage_gaps) <= 256 and
                all(isinstance(gap, str) and len(gap) <= 2048 for gap in coverage_gaps), "invalid retained profile coverage gaps")
        report["retainedProfileCoverageGaps"] = coverage_gaps
        enums = profile.get("enumDefinitions", {})
        require(isinstance(enums, dict) and len(enums) <= 256, "enum definition budget exceeded")
        report["gaps"].extend(report["sources"]["gaps"])
        missing_enums = sorted({field["type"] for hook in hooks for field in hook["fields"]
                                if field.get("valueRepresentation") != "referenceIdentity" and field["type"] not in PRIMITIVES and field["type"] not in ("string", "float") and field["type"] not in enums})
        if missing_enums:
            report["gaps"].append("No retained enum definition for: " + ", ".join(missing_enums))
        enable_history = strict_enable_history_consistent(summary, len(hooks))
        strict = enable_history and all(strict_receipt_consistent(summary.get(key), len(hooks)) for key in ("strictEnable", "strictDisable"))
        failure_markers = [name for name in ("runtime.error", "mission-trace/aborted.json", "mission-trace/strict-fatal.txt")
                           if name in artifacts and artifacts[name]["bytes"] > 0]
        report["receiptFacts"] = {"captureCompleteClaim": summary.get("complete"), "healthyClaim": summary.get("healthy"),
                                  "failureReason": summary.get("failureReason"), "nativeInputHashesBoundToProfile": True,
                                  "collectionBoundFailureMarkers": failure_markers,
                                  "strictEnableAttempts": summary.get("strictEnableAttempts"),
                                  "strictEnableHistoryConsistent": enable_history,
                                  "strictTransitionReceiptsConsistent": strict, "strictReceiptProofBoundary": "Retained report consistency only; native transactions are not re-executed or independently observed."}
        journal_name = "mission-trace/events.jsonl"
        require(journal_name in artifacts and artifacts[journal_name]["bytes"] <= limits.journal_bytes, "missing or oversized journal")
        frequency = integer(summary.get("qpcFrequency"), "QPC frequency")
        require(frequency > 0, "zero QPC frequency")
        start_qpc, end_qpc = integer(summary.get("startQpc"), "startQpc"), integer(summary.get("statusQpc"), "statusQpc")
        start_tick, end_tick = integer(summary.get("startTickNs"), "startTickNs"), integer(summary.get("statusTickNs"), "statusTickNs")
        require(end_qpc >= start_qpc and end_tick >= start_tick, "invalid receipt clock bracket")
        base, image_size = integer(summary.get("moduleBase"), "moduleBase"), integer(summary.get("moduleImageSize"), "moduleImageSize", 1 << 32)
        calls, states, threads, sequences = Counter(), Counter(), Counter(), set()
        identifiers: dict[str, Counter[str]] = {"missionId": Counter(), "questId": Counter(), "parentQuestId": Counter()}
        byte_count, input_bytes, qpc_decreases, previous_qpc = 0, 0, 0, None
        journal_digest = hashlib.sha256()
        first_qpc, last_qpc = None, None
        with artifacts[journal_name]["path"].open("rb") as source, partial.open("xb") as destination:
            while line := source.readline(limits.input_line_bytes + 1):
                input_bytes += len(line)
                require(input_bytes <= limits.journal_bytes, "journal byte budget exceeded while decoding")
                journal_digest.update(line)
                require(len(line) <= limits.input_line_bytes and line.endswith(b"\n"), "journal line is oversized or unterminated")
                require(report["decodedRows"] < limits.rows, "journal row budget exceeded")
                row = parse_json(line, "journal row")
                require(isinstance(row, dict) and row.get("schema") == "endfieldCapture.missionTraceEntry.v1", "unsupported event schema")
                index = integer(row.get("hookIndex"), "hook index", len(hooks) - 1)
                hook = hooks[index]
                report["failedEvent"] = {"journal": journal_name, "row": report["decodedRows"] + 1, "hook": hook["name"],
                                         "hookIndex": index}
                require(row.get("hook") == hook["name"], "event hook binding mismatch")
                sequence = integer(row.get("sequence"), "event sequence")
                require(sequence > 0 and sequence not in sequences, "duplicate or zero event sequence")
                sequences.add(sequence)
                qpc, tick = integer(row.get("qpc"), "event QPC"), integer(row.get("tickNs"), "event tickNs")
                require(start_qpc <= qpc <= end_qpc and start_tick <= tick <= end_tick, "event outside receipt clock bracket")
                thread = integer(row.get("threadId"), "event thread", (1 << 32) - 1)
                require(thread > 0, "zero event thread")
                args = row.get("args")
                require(isinstance(args, list) and len(args) == 8, "invalid event raw arguments")
                for value in args:
                    integer(value, "raw argument")
                mask = integer(row.get("argsReadMask"), "argument read mask", 255)
                require(mask in (15, 255), "unsupported argument read mask")
                return_address = integer(row.get("returnAddress"), "return address")
                expected_caller = return_address - base if base <= return_address < base + image_size else 0
                require(row.get("callerGameAssemblyRva") == expected_caller, "caller address/RVA mismatch")
                fields = row.get("fields")
                require(isinstance(fields, list) and len(fields) == len(hook["fields"]), "event field count mismatch")
                decoded_fields = []
                for descriptor, observed in zip(hook["fields"], fields):
                    require(isinstance(observed, dict), "invalid observed field")
                    require(mask & (1 << descriptor["arg"]) or observed.get("state") == 2, "field uses unreadable argument")
                    if descriptor["kind"] == 4 and observed.get("state") == 1:
                        require(observed.get("value") == args[descriptor["arg"]], "scalar field/raw argument mismatch")
                    if descriptor["kind"] == 3 and descriptor["chain0"] == 4097 and observed.get("state") == 4:
                        require(args[descriptor["arg"]] == 0, "direct string null/raw argument mismatch")
                    value = decode_field(descriptor, observed, enums)
                    decoded_fields.append(value)
                    states[value["stateName"]] += 1
                    label = descriptor["label"].split(".")[-1]
                    if label in identifiers and value["state"] == 1 and descriptor["kind"] == 3 and value["value"]:
                        identities = identifiers[label]
                        if value["value"] not in identities:
                            require(sum(len(items) for items in identifiers.values()) < limits.identifiers, "observed identifier budget exceeded")
                        identities[value["value"]] += 1
                decoded = {"schema": "endfield.mission-trace-decoded-entry.v1", "sequence": sequence, "qpc": qpc, "tickNs": tick,
                           "qpcOffset": qpc - start_qpc, "qpcFrequency": frequency, "secondsFromStart": (qpc - start_qpc) / frequency,
                           "threadId": thread, "hookIndex": index, "hook": hook["name"], "returnAddress": return_address,
                           "callerGameAssemblyRva": expected_caller, "argsReadMask": mask, "rawArgs": args, "fields": decoded_fields}
                receiver = hook.get("receiverIdentity")
                if isinstance(receiver, dict):
                    argument = integer(receiver.get("arg"), "receiver argument", 7)
                    require(argument == 0 and isinstance(receiver.get("type"), str) and len(receiver["type"]) <= 256, "unsupported receiver identity carrier")
                    decoded["receiverIdentity"] = {"rawPointer": args[argument], "type": receiver["type"],
                                                    "boundary": "Observed entry pointer only; object lifetime and causal ownership unresolved."}
                payload = (json.dumps(decoded, ensure_ascii=True, separators=(",", ":"), allow_nan=False) + "\n").encode("ascii")
                byte_count += len(payload)
                require(len(payload) <= limits.output_line_bytes and byte_count <= limits.output_bytes, "decoded output byte budget exceeded")
                destination.write(payload)
                report["decodedRows"] += 1
                calls[index] += 1
                threads[thread] += 1
                qpc_decreases += int(previous_qpc is not None and qpc < previous_qpc)
                previous_qpc = qpc
                first_qpc = qpc if first_qpc is None else min(first_qpc, qpc)
                last_qpc = qpc if last_qpc is None else max(last_qpc, qpc)
                report.pop("failedEvent", None)
        require(input_bytes == artifacts[journal_name]["bytes"] and journal_digest.hexdigest() == artifacts[journal_name]["sha256"],
                "journal changed before or during decoding")
        require(report["decodedRows"] == integer(summary.get("written"), "written rows") and
                artifacts[journal_name]["bytes"] == integer(summary.get("bytesWritten"), "written bytes"), "journal/summary row or byte count mismatch")
        accounted = all(summary.get(key) == 0 for key in ("dropped", "unrecorded", "undrainedRecordsAtStop")) and summary.get("finalCountersStable") is True
        for name, state in (("unreadableFields", "unreadable"), ("truncatedFields", "truncated"), ("nullFields", "observedNull")):
            count = integer(summary.get(name), name)
            require((states[state] == count) if accounted else (states[state] <= count or summary.get("finalCountersStable") is not True), f"journal/summary field counter mismatch: {name}")
        attempted, admitted, dropped = (integer(summary.get(key), key) for key in ("attempted", "admitted", "dropped"))
        if summary.get("finalCountersStable") is True:
            require(attempted == admitted + dropped and sum(item["calls"] for item in summary["hooks"]) == attempted, "provider attempted/admitted/hook accounting mismatch")
        require(not sequences or max(sequences) <= attempted, "event sequence exceeds attempted callbacks")
        report["hookCoverage"] = []
        lanes: dict[str, dict[str, Any]] = {}
        for index, hook in enumerate(hooks):
            declared = summary["hooks"][index]["calls"]
            require(calls[index] == declared if accounted else calls[index] <= declared or summary.get("finalCountersStable") is not True, "journal/summary hook calls mismatch")
            lane = hook.get("lane", hook["name"].split(".", 1)[0])
            require(isinstance(lane, str) and len(lane) <= 127, "invalid hook lane")
            coverage = {"index": index, "hook": hook["name"], "lane": lane, "laneSource": "retained profile" if "lane" in hook else "hook-name prefix grouping",
                        "observedRows": calls[index], "receiptCalls": declared, "status": "observed" if calls[index] else "unhit"}
            report["hookCoverage"].append(coverage)
            lane_row = lanes.setdefault(lane, {"hooks": 0, "observedHooks": 0, "rows": 0})
            lane_row["hooks"] += 1
            lane_row["observedHooks"] += int(calls[index] > 0)
            lane_row["rows"] += calls[index]
        contiguous = not sequences or (min(sequences) == 1 and max(sequences) == len(sequences))
        if accounted:
            require(contiguous and attempted == report["decodedRows"] == admitted, "lossless receipt sequence/accounting mismatch")
        if summary.get("complete") is True:
            require(accounted and strict and summary.get("healthy") is True and summary.get("writeComplete") is True and
                    all(summary.get(key) is True for key in ("installed", "hooksEverEnabled", "stopped", "quiescent")) and
                    summary.get("disabledTrampolinesRetainedUntilProcessExit") is True and summary.get("missionFiltered") is False and not failure_markers and
                    all(summary.get(key) is False for key in ("budgetExhausted", "durationBudgetExhausted", "strictPendingRecovery", "returnValuesObserved")) and
                    summary.get("entryOnly") is True and summary.get("failureReason") == "none" and summary.get("firstFailure") is None and
                    summary.get("activeCallbacksAtStop") == 0 and summary.get("strictRecoveryAttempts") == 0 and summary.get("strictRecovery") is None and
                    report["decodedRows"] > 0 and integer(summary.get("startUtcFileTime100ns"), "UTC session anchor") > 0 and
                    states["unreadable"] == states["truncated"] == 0,
                    "complete provider receipt contradicts retained observations")
        report.update(status="inspected", decodedBytes=byte_count, fieldStates=dict(states), lanes=lanes,
                      clocks={"qpcFrequency": frequency, "startQpc": start_qpc, "endQpc": end_qpc, "firstEventQpc": first_qpc,
                              "lastEventQpc": last_qpc, "journalQpcDecreases": qpc_decreases, "sequenceContiguous": contiguous,
                              "startTickNs": start_tick, "endTickNs": end_tick,
                              "startUtcFileTime100ns": summary.get("startUtcFileTime100ns"),
                              "boundary": "Preserved per-entry clocks and sequence; cross-thread chronology is not a causal join."},
                      threads=[{"threadId": key, "rows": value} for key, value in sorted(threads.items())],
                      observedIdentifiers={key: [{"id": identity, "rows": count,
                                                  **({"archivedMissionAssignments": assignments.get(identity, [])} if key in ("questId", "parentQuestId") and join_sources else {})}
                                                 for identity, count in sorted(values.items())] for key, values in identifiers.items()})
        report["receiptFacts"]["allJournalRowsAccounted"] = accounted
        partial.rename(output_dir / "decoded.events.jsonl")
    except (InspectionError, OSError, UnicodeError, RecursionError, KeyError, TypeError, AttributeError) as exc:
        report["status"] = "failed"
        report["failure"] = str(exc)[:2048]
        report["decodedOutput"] = "decoded.events.partial.jsonl" if partial.exists() else None
        with (output_dir / "inspection.json").open("x", encoding="ascii") as target:
            target.write(json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False) + "\n")
        raise InspectionError(report["failure"]) from exc
    report["decodedOutput"] = "decoded.events.jsonl"
    with (output_dir / "inspection.json").open("x", encoding="ascii") as target:
        target.write(json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False) + "\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--join-sources", action="store_true", help="Add explicit assignments from verified archived MissionRuntimeAsset questDic rows.")
    args = parser.parse_args(argv)
    try:
        report = inspect_session(args.session, args.output_dir, join_sources=args.join_sources)
    except (InspectionError, OSError) as exc:
        print(f"[mission_trace_inspect] failed: {exc}")
        return 1
    observed = sum(row["status"] == "observed" for row in report["hookCoverage"])
    print(f"[mission_trace_inspect] verified {report['inventory']['artifacts']} artifacts; decoded {report['decodedRows']} rows; "
          f"observed {observed}/{len(report['hookCoverage'])} hooks; native execution is not re-validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

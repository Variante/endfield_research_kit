"""Validate one bounded audio capture session, and say what it cannot give.

`audio_native_hooks` records a chain that is statically closed as far as the
managed request and then stops: no static evidence joins a source key to an
opened file, to a decoder, or to audible output. The hooks for that join are
prepared in `tools/EndfieldCapture` and, in that file's words, are *prepared
evidence only until an authorized capture observes a match* -- and no verified
capture has produced the continuity rows yet.

This module is the consumer side of that. It reads a session written by
`StartCapture.bat audio`, applies the gates that make a session usable at all,
and reports what the artifacts on disk support. It never launches anything and
never writes into the session.

**Gates, all fail-closed, all read from real sessions rather than assumed.**
The provider publishes its own completeness counters in ``audio/summary.json``
and its window boundaries in ``audio/windows.jsonl``. A session is refused --
naming the gate -- when the schema is not the expected one, when a record was
dropped, when a call went unpaired, when a window was still open at session
stop, or when the provider did not mark the session complete. Each of those
means the record stream has holes, and anything computed across a hole is not
an observation.

**What it decodes, and on whose authority.** The per-callback records ship as
opaque ``payloadHex`` blobs in ``events.jsonl``. Their layout is not the
in-memory ``CallbackRecord`` -- the shipped payload is 208 bytes where that
struct is larger -- so it is read from the writer that packs it,
``AudioEventPayload`` in ``runtime_dll.cpp``: five u64, four u32, a kind byte,
then two fixed ASCII buffers, summing to 201 and padding to 208. That the
layout is right is checkable rather than asserted, and it checks: across a real
session every payload decodes, the hook-name field resolves to exactly the
three hook constants the adapter declares, and calls and results pair one to
one with no remainder.

**Nothing is joined across hooks.** A call and its result share a capture id,
so that pair is one observation. An Event posted and a file opened in the same
session are two facts about the session and not a chain; calling them one would
be the cross-record join this lane keeps refusing. Posts, prepared keys and
opened paths are therefore counted separately.

**A capture cannot recover an Event name, and it is worth being exact about
why.** The hooked post is
``(uint32 eventId, uint64 audioObjectId, uint32 callbackType, ...)`` --
`PostEventFn` in the audio hook adapter. It carries the hash, never the
spelling. The game does expose string overloads on `AudioManager`, so a
*different* hook could see a name, but the post this tooling observes cannot,
and no session run today will name a hash-only Event.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from scripts.repo_paths import REPO_ROOT as REPO


DEFAULT_SESSION_ROOT = REPO / "scratch/reverse_engineering/endfield_capture"
DEFAULT_OUTPUT = REPO / "reports/audio/runtime_capture_import.json"
EVENTS_FILE = REPO / "webui/data/lang/CN/audio/events.json"
WINDOW_SCHEMA = "endfieldCapture.audioWindow.v2"
SUMMARY_SCHEMA = "endfieldCapture.audioSummary.v2"
#: The audio provider's id in the session event stream.
AUDIO_PROVIDER_ID = 2
#: ``EventType::AudioCallback``.
AUDIO_CALLBACK_TYPE = 10
#: Hook names the provider publishes, as its integration contract fixes them.
POST_HOOK = "AudioAdapter._PostEvent"
POST_EXTERNAL_HOOK = "AudioAdapter._PostEventWithExternalSource"
PROVIDER_HOOK = "AkSoundEngine.SourceProviderPreparation"
MEDIA_HOOK = "AkSoundEngine.SourceMediaLookup"
IO_OPEN_HOOK = "AkSoundEngine.DefaultIoOpenDispatch"


class SessionError(ValueError):
    """A gate refused the session; the detail names which one."""


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = json.loads(stripped)
        except ValueError as error:
            raise SessionError(f"{path.name}:line {number}: {error}") from None
        if not isinstance(value, dict):
            raise SessionError(f"{path.name}:line {number}: not an object")
        rows.append(value)
    return rows


def check_session(session: Path) -> dict[str, Any]:
    """Refuse a session whose record stream has holes, and say which gate.

    Every field read here was taken from sessions on disk rather than assumed:
    the provider publishes its own completeness counters in
    ``audio/summary.json`` and its window boundaries in ``audio/windows.jsonl``,
    and those counters are the gate. A session that dropped a record or left a
    call unpaired has holes, and a join computed across a hole is not an
    observation.
    """
    audio = session / "audio"
    summary_file = audio / "summary.json"
    windows_file = audio / "windows.jsonl"
    if not summary_file.is_file():
        raise SessionError(
            f"no audio summary at {summary_file}; was this session run with "
            "StartCapture.bat audio?")
    summary = json.loads(summary_file.read_bytes())
    schema = str(summary.get("schema"))
    if schema != SUMMARY_SCHEMA:
        raise SessionError(f"unexpected audio summary schema {schema!r}")
    for counter, message in (
        ("dropped", "record(s) dropped by the callback queue"),
        ("unresolvedResults", "call(s) without a result"),
    ):
        value = int(summary.get(counter) or 0)
        if value:
            raise SessionError(f"{value} {message}: the record stream has holes")
    if summary.get("windowActiveAtSessionStop"):
        raise SessionError("a window was still open at session stop: the stream is truncated")
    started = int(summary.get("windowsStarted") or 0)
    completed = int(summary.get("windowsCompleted") or 0)
    if started == 0:
        raise SessionError("no audio window was started: nothing was published")
    if started != completed:
        raise SessionError(f"{started} window(s) started and {completed} completed")
    if not summary.get("complete"):
        raise SessionError("the provider did not mark the session complete")

    windows = _read_jsonl(windows_file) if windows_file.is_file() else []
    unexpected = {str(row.get("schema")) for row in windows} - {WINDOW_SCHEMA}
    if windows and unexpected:
        raise SessionError(f"unexpected window schema {sorted(unexpected)}")
    spans = [
        (int(row["startNs"]), int(row["endNs"]))
        for row in windows
        if row.get("action") == "stop" and row.get("startNs") and row.get("endNs")
    ]
    return {
        "status": "validated",
        "session": session.name,
        "windowsStarted": started,
        "windowsCompleted": completed,
        "enqueued": int(summary.get("enqueued") or 0),
        "attempted": int(summary.get("attempted") or 0),
        "observedMilliseconds": round(
            sum(end - start for start, end in spans) / 1_000_000, 3) if spans else 0.0,
    }


#: ``AudioEventPayload`` as ``runtime_dll.cpp`` packs it, read from that struct
#: rather than inferred: five u64, four u32, a kind byte, then two fixed ASCII
#: buffers. It sums to 201 and pads to 208, which is exactly the payload size
#: every shipped record carries.
PAYLOAD_BYTES = 208
HOOK_NAME_OFFSET, HOOK_NAME_BYTES = 57, 48
KEY_OR_PATH_OFFSET, KEY_OR_PATH_BYTES = 105, 96
#: ``CallbackKind``: a call, and its paired result.
KIND_CALL, KIND_RESULT = 0, 1
#: The writer sets these when it had to truncate a bounded text field.
FLAG_HOOK_NAME_TRUNCATED = 1 << 30
FLAG_KEY_OR_PATH_TRUNCATED = 1 << 31


def decode_payload(blob: bytes) -> dict[str, Any]:
    """One ``AudioEventPayload``, or a refusal if it is not that shape."""
    if len(blob) != PAYLOAD_BYTES:
        raise SessionError(f"audio payload is {len(blob)} bytes, expected {PAYLOAD_BYTES}")
    capture, parent, return_value, fact0, fact1 = struct.unpack_from("<5Q", blob, 0)
    nesting, hook_index, result_code, flags = struct.unpack_from("<4I", blob, 40)

    def text(offset: int, size: int) -> str:
        return blob[offset:offset + size].split(bytes(1), 1)[0].decode("ascii", "replace")

    return {
        "captureId": capture,
        "parentCaptureId": parent,
        "returnValue": return_value,
        "pointerFact0": fact0,
        "pointerFact1": fact1,
        "nestingId": nesting,
        "hookIndex": hook_index,
        "resultCode": result_code,
        "flags": flags,
        "kind": blob[56],
        "hookName": text(HOOK_NAME_OFFSET, HOOK_NAME_BYTES),
        "keyOrPath": text(KEY_OR_PATH_OFFSET, KEY_OR_PATH_BYTES),
        "truncated": bool(flags & (FLAG_HOOK_NAME_TRUNCATED | FLAG_KEY_OR_PATH_TRUNCATED)),
    }


def decoded_callbacks(session: Path) -> list[dict[str, Any]]:
    """Every audio callback record in the session, decoded."""
    stream = session / "events.jsonl"
    if not stream.is_file():
        return []
    records = []
    for row in _read_jsonl(stream):
        if row.get("provider") != AUDIO_PROVIDER_ID or row.get("type") != AUDIO_CALLBACK_TYPE:
            continue
        payload = row.get("payloadHex")
        if not isinstance(payload, str) or not payload:
            raise SessionError("an audio callback event carries no payload")
        records.append(dict(decode_payload(bytes.fromhex(payload)),
                            timestampNs=row.get("timestampNs")))
    return records


def observed(records: list[dict[str, Any]], inventory: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """What the decoded records say, with each claim kept to itself.

    A call and its result share a capture id, so the pair is one observation.
    Beyond that nothing is joined: an Event posted and a file opened in the
    same session are two facts about the session, not a chain, and calling
    them one would be the cross-record join this lane keeps refusing.
    """
    calls = [row for row in records if row["kind"] == KIND_CALL]
    results = {row["captureId"]: row for row in records if row["kind"] == KIND_RESULT}
    posts = Counter()
    playing_ids = set()
    for row in calls:
        if row["hookName"] not in (POST_HOOK, POST_EXTERNAL_HOOK):
            continue
        posts[row["pointerFact0"] & 0xFFFFFFFF] += 1
        paired = results.get(row["captureId"])
        if paired is not None and paired["returnValue"]:
            playing_ids.add(paired["returnValue"])
    # An external-source post carries both the source key and the media path it
    # names, in one paired record. That pair is a join the post itself makes --
    # not two facts placed side by side -- so it is reported as one.
    external: dict[int, set] = {}
    truncated_paths: set[str] = set()
    for row in calls:
        if row["hookName"] != POST_EXTERNAL_HOOK or not row["keyOrPath"]:
            continue
        external.setdefault(row["pointerFact0"] & 0xFFFFFFFF, set()).add(row["keyOrPath"])
        if row["truncated"] or len(row["keyOrPath"]) >= KEY_OR_PATH_BYTES - 1:
            truncated_paths.add(row["keyOrPath"])
    opened = {row["keyOrPath"] for row in records
              if row["hookName"] == IO_OPEN_HOOK and row["keyOrPath"]}
    prepared = {row["pointerFact0"] & 0xFFFFFFFF for row in records
                if row["hookName"] == PROVIDER_HOOK}
    unnamed = sorted(event for event in posts if event not in inventory)
    return {
        "callbackRecords": len(records),
        "calls": len(calls),
        "results": len(results),
        "unpairedCalls": sum(1 for row in calls if row["captureId"] not in results),
        "truncatedTexts": sum(1 for row in records if row["truncated"]),
        "postedEvents": {
            "distinct": len(posts),
            "total": sum(posts.values()),
            "withRecoveredName": sum(1 for event in posts if event in inventory),
            "withoutRecoveredName": len(unnamed),
            "unnamedEventIds": [f"0x{value:08X}" for value in unnamed[:40]],
            "distinctPlayingIds": len(playing_ids),
            "boundary": (
                "An Event id reached the post hook and the paired result returned a "
                "playing id. That is a call that was accepted, not a proof that it "
                "was audible, and the id is a hash: no name is recovered here."
            ),
        },
        "externalSourcePosts": {
            "distinctKeys": len(external),
            "distinctPaths": len({path for paths in external.values() for path in paths}),
            "keysNamingMoreThanOnePath": sum(1 for paths in external.values() if len(paths) > 1),
            "mostPathsForOneKey": max((len(paths) for paths in external.values()), default=0),
            "truncatedPaths": len(truncated_paths),
            "sample": [{"sourceKey": f"0x{key:08X}", "paths": len(paths),
                        "path": sorted(paths)[0],
                        "truncated": sorted(paths)[0] in truncated_paths}
                       for key, paths in sorted(external.items())[:20]],
            "boundary": (
                "The key and the path come from one call's own arguments, so this pair "
                "is a join the game made, not two facts observed nearby. The key is not "
                "a media identifier: one key is observed naming many different files, so "
                "a key-to-file mapping is many-to-one at best. A path reaching the "
                "capture's 95-character text bound is cut, and counted under "
                "truncatedPaths rather than presented as a whole path. None of this "
                "says whether the media was read, decoded, or heard."
            ),
        },
        "openedPaths": sorted(opened)[:40],
        "openedPathCount": len(opened),
        "preparedSourceKeys": len(prepared),
        "boundary": (
            "Posts, prepared keys and opened paths are counted separately and not "
            "joined. A key seen at two hooks in one session is a coincidence of "
            "numbers until ordering and identity are checked, which this does not do."
        ),
    }


def summarize(session: Path, inventory: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """What the session supports, with each claim kept separate."""
    gate = check_session(session)
    records = decoded_callbacks(session)
    body = observed(records, inventory)
    return {
        "gate": gate,
        "observed": body,
        "eventNameRecovery": {
            "possible": False,
            "reason": (
                "The hooked post takes a uint32 Event id, not a name: PostEventFn in "
                "the audio hook adapter is (uint32 eventId, uint64 audioObjectId, "
                "uint32 callbackType, ...). A capture therefore observes which Events "
                "fired, never how they are spelled."
            ),
            "inventoryEventsWithRecoveredName": len(inventory),
        },
    }


def load_inventory(path: Path = EVENTS_FILE) -> dict[int, dict[str, Any]]:
    if not path.is_file():
        return {}
    rows = json.loads(path.read_bytes()).get("events", [])
    return {
        int(row["hash"]) & 0xFFFFFFFF: row
        for row in rows
        if isinstance(row.get("hash"), int)
        and row.get("eventIdentityStatus") == "recoveredAuthoredName"
    }


def latest_session(root: Path) -> Path | None:
    """The newest session that actually carries an audio window stream."""
    if not root.is_dir():
        return None
    candidates = [
        child for child in sorted(root.iterdir(), reverse=True)
        if child.is_dir() and (child / "audio" / "windows.jsonl").is_file()
    ]
    return candidates[0] if candidates else None


def build(output: Path, session: Path | None, root: Path = DEFAULT_SESSION_ROOT) -> dict[str, Any]:
    started = time.perf_counter()
    output = output.resolve()
    reports = (REPO / "reports").resolve()
    if reports not in output.parents:
        raise ValueError(f"output-must-be-under={reports}")
    chosen = session or latest_session(root)
    if chosen is None:
        report: dict[str, Any] = {
            "schema": "endfield.audio-runtime-capture-import.v1",
            "summary": {
                "status": "no-session",
                "detail": f"no session under {root} carries audio/windows.jsonl",
            },
        }
    else:
        try:
            body = summarize(chosen, load_inventory())
            report = {
                "schema": "endfield.audio-runtime-capture-import.v1",
                **body,
                "summary": {
                    "status": "validated",
                    "session": chosen.name,
                    "windows": body["gate"]["windowsCompleted"],
                    "observedMilliseconds": body["gate"]["observedMilliseconds"],
                    "callbackRecords": body["observed"]["callbackRecords"],
                    "distinctEvents": body["observed"]["postedEvents"]["distinct"],
                    "withoutRecoveredName": body["observed"]["postedEvents"]["withoutRecoveredName"],
                    "openedPaths": body["observed"]["openedPathCount"],
                    "externalSourceKeys": body["observed"]["externalSourcePosts"]["distinctKeys"],
                    "elapsedSeconds": round(time.perf_counter() - started, 3),
                },
            }
        except SessionError as error:
            report = {
                "schema": "endfield.audio-runtime-capture-import.v1",
                "summary": {"status": "refused", "session": chosen.name,
                            "detail": str(error)},
            }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, default=None,
                        help="a capture session directory; the newest audio one by default")
    parser.add_argument("--session-root", type=Path, default=DEFAULT_SESSION_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        report = build(args.output, args.session, args.session_root)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "failed", "detail": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    return 0 if report["summary"]["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())

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

**What this does not do, and why.** The per-callback records are published as
opaque ``payloadHex`` blobs in ``events.jsonl``, not as JSON. Their serialized
layout is not the in-memory ``CallbackRecord``: the shipped payload is 208
bytes where that struct is larger, so the writer packs a different form. This
module therefore *counts* those payloads by type and size and decodes none of
their fields, because choosing an offset without the writer's layout would
invent facts rather than read them. Finishing the decode needs that layout, and
is what stands between a validated session and the key-to-file-to-decoder
continuity the audio topic is waiting on.

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


def callback_payloads(session: Path) -> dict[str, Any]:
    """Count the audio provider's binary callback payloads in the event stream.

    The per-callback records are published as opaque ``payloadHex`` blobs in
    ``events.jsonl`` rather than as JSON, so this reports how many are present
    and of what size, and does **not** decode their fields. Decoding them needs
    the writer's serialized layout, which is not the in-memory ``CallbackRecord``
    -- the shipped payload is 208 bytes where that struct is larger -- and
    guessing an offset would invent facts rather than read them.
    """
    stream = session / "events.jsonl"
    if not stream.is_file():
        return {"status": "absent"}
    sizes: Counter = Counter()
    for row in _read_jsonl(stream):
        if row.get("provider") == AUDIO_PROVIDER_ID:
            sizes[(int(row.get("type") or 0), int(row.get("payloadBytes") or 0))] += 1
    return {
        "status": "counted",
        "records": sum(sizes.values()),
        "byTypeAndSize": {f"type{kind}:{size}b": count
                          for (kind, size), count in sorted(sizes.items())},
        "boundary": (
            "Counted, not decoded. The payload is a packed binary record whose "
            "serialized layout differs from the in-memory struct, so no Event id, "
            "source key or path is read from it here."
        ),
    }


def summarize(session: Path, inventory: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """What the session supports, with each claim kept separate."""
    gate = check_session(session)
    payloads = callback_payloads(session)
    return {
        "gate": gate,
        "callbackPayloads": payloads,
        "eventNameRecovery": {
            "possible": False,
            "reason": (
                "The hooked post takes a uint32 Event id, not a name: "
                "PostEventFn in the audio hook adapter is "
                "(uint32 eventId, uint64 audioObjectId, uint32 callbackType, ...). "
                "A capture therefore observes which Events fired, never how they "
                "are spelled, and cannot name a hash-only Event."
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
                    "callbackPayloads": body["callbackPayloads"].get("records", 0),
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

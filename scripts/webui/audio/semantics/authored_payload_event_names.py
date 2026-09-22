"""Wwise Event-name literals shipped inside authored serialized payload roots.

``gameplay_audio`` already reads the MemoryPack length-prefixed
``au_*``/``bark_*``/``radio_*`` literals out of ``SkillData`` and ``BuffData``.
The level, level-script-template, interactive and spawner payload roots are
encoded the same way and carry the same literals, but nothing read them for
Event names.  Every Event whose only shipped spelling lives in one of those
roots therefore stayed a ``hashed-event:0x...`` identity, and the decoded media
it reaches stayed published by numeric id alone.

Nothing in this module decides that a literal *is* an Event.  It collects
candidates under two exact constraints -- the shipped ``au_``/``bark_``/
``radio_`` naming grammar, and the MemoryPack four-byte length prefix that
proves the bytes are a serialized string rather than an incidental ASCII run --
and the HIRC pass promotes a candidate exactly when its FNV-1 hash equals a
current Event object id.  A literal that matches no current Event names
nothing.  No prefix taxonomy, filename similarity, address ordering or
proximity argument is used, and a recovered spelling supplies only the Event's
identity: caller, trigger, selected branch, execution and audibility stay
exactly as unresolved as before.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from scripts.source_paths import ExportLayout
from scripts.webui.audio.semantics.gameplay_audio import length_prefixed_matches

# ``SkillData`` and ``BuffData`` are deliberately absent: ``gameplay_audio``
# owns them and already contributes their literals, so listing them here would
# duplicate one harvest across two owners.
AUTHORED_PAYLOAD_EVENT_NAME_ROOTS: tuple[str, ...] = (
    "Interactive",
    "LevelData",
    "LevelScriptData",
    "LevelScriptTemplateData",
    "SpawnerConfig",
)

# The same shipped naming grammar ``gameplay_audio`` accepts.  Widening it is a
# schema claim about a family this module has not proven, not a free win.
AUTHORED_PAYLOAD_EVENT_BYTES_RE = re.compile(
    rb"\b(?:au|bark|radio)_[A-Za-z0-9_]{2,160}\b"
)

EVIDENCE_BOUNDARY = (
    "An exact MemoryPack length-prefixed au_/bark_/radio_ literal in an "
    "authored serialized payload is an Event-name candidate only. It becomes "
    "an Event name exactly when its FNV-1 hash equals a current HIRC Event "
    "object id, and it then supplies that Event's identity and nothing else: "
    "no caller, trigger, selected branch, posting, execution or audibility."
)


def _payload_files(root: Path) -> Iterable[Path]:
    yield from sorted(root.rglob("*.json"))


def collect_authored_payload_event_names(
    export_root: Path,
) -> tuple[set[str], dict[str, Any]]:
    """Return candidate Event names plus a per-root read audit.

    A missing root contributes nothing and is reported as ``missingRoot``
    instead of being silently skipped, so a layout change is visible as a
    dropped source rather than as a quiet loss of Event names.
    """

    base = ExportLayout(export_root).game / "Json"
    candidates: set[str] = set()
    roots: list[dict[str, Any]] = []
    for family in AUTHORED_PAYLOAD_EVENT_NAME_ROOTS:
        root = base / family
        if not root.is_dir():
            roots.append({"root": family, "status": "missingRoot", "files": 0, "candidates": 0})
            continue
        found: set[str] = set()
        files = 0
        unreadable = 0
        for path in _payload_files(root):
            files += 1
            try:
                data = path.read_bytes()
            except OSError:
                unreadable += 1
                continue
            found.update(
                value.lower()
                for value in length_prefixed_matches(
                    data, AUTHORED_PAYLOAD_EVENT_BYTES_RE
                )
            )
        row: dict[str, Any] = {
            "root": family,
            "status": "read",
            "files": files,
            "candidates": len(found),
        }
        if unreadable:
            row["unreadableFiles"] = unreadable
            row["status"] = "readWithUnreadableFiles"
        roots.append(row)
        candidates.update(found)

    audit = {
        "schemaVersion": 1,
        "source": "authoredSerializedPayloadLengthPrefixedLiteral",
        "roots": roots,
        "candidateCount": len(candidates),
        "evidenceBoundary": EVIDENCE_BOUNDARY,
    }
    return candidates, audit


def summarize_authored_payload_event_name_recovery(
    candidates: set[str],
    audit: dict[str, Any],
    wwise_event_inventory: Iterable[dict[str, Any]],
    *,
    fnv1_32,
) -> dict[str, Any]:
    """Report how many candidates a current Event object id actually claims.

    The promoted count is measured against the Event objects the HIRC pass
    parsed, never asserted, and the coincidence expectation is published beside
    it so a reader can see that the hash equality is doing real work.
    """

    event_hashes = {
        int(row["eventHash"]) & 0xFFFFFFFF
        for row in wwise_event_inventory
        if isinstance(row, dict) and isinstance(row.get("eventHash"), int)
    }
    promoted = sorted(
        name for name in candidates if fnv1_32(name) in event_hashes
    )
    candidate_count = len(candidates)
    return {
        **audit,
        "currentWwiseEventObjectHashes": len(event_hashes),
        "promotedCount": len(promoted),
        "promotedNames": promoted,
        "expectedCoincidentalPreimages": round(
            candidate_count * len(event_hashes) / float(1 << 32), 4
        ),
    }

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

**Pooled strings.** Builds that ship ``Json/StringPool/`` stop inlining strings
in compact JsonData payloads: a string member becomes an ``i32`` global pool
index (``scripts.game_data.string_pool``), so the length-prefixed scan above
finds nothing for those members, and every Event whose only spelling moved
into the pool fell back to ``hashed-event:0x...`` (the first pooled build
left 1,078 such Events, most of them ``au_int_*`` interactive objects).
``collect_string_pool_event_names`` reads the pool through its exact ``USPC``
reader and offers each whole entry matching the managed audio grammar
(``au_``/``bark_``/``radio_``/``vo_``, the same closed prefix set as the
metadata literals, because a pool entry is a whole decoded string exactly like
a metadata literal). Promotion is unchanged: an FNV-1 hash equal to a current
Event object id. Tier: the spelling is ``exact`` (an exactly framed shipped
string whose hash is the Event id); which payload member holds the pool index
is not read, so the payload-to-Event relation stays ``structuralOnly``.
Entries outside the grammar (``Play_au_*``/``Stop_au_*``, ``indie_*``,
generic words such as ``Stop``) are counted in the audit but never promoted:
the pool has ~2.8e5 entries, so an unprefixed sweep yields about one
coincidental Event-id preimage per run and the prefix gate is what keeps the
promotion exact.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from scripts.game_data.string_pool import StringPoolDecodeError, export_string_pool
from scripts.source_paths import ExportLayout
from scripts.webui.audio.semantics.gameplay_audio import length_prefixed_matches
from scripts.webui.audio.semantics.identifiers import MANAGED_AUDIO_LITERAL_RE

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
# Dropping the word boundaries is not a widening: ``length_prefixed_matches``
# now anchors the match to the whole length-prefixed slice, which is a
# stricter test than a boundary-delimited substring, and the FNV-1 promotion
# gate is unchanged -- a candidate matching no current Event still names
# nothing.
AUTHORED_PAYLOAD_EVENT_BYTES_RE = re.compile(
    rb"(?:au|bark|radio)_[A-Za-z0-9_]{2,160}", re.IGNORECASE
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


STRING_POOL_EVIDENCE_BOUNDARY = (
    "A whole JsonData StringPool entry matching the au_/bark_/radio_/vo_ "
    "grammar is an Event-name candidate only. It becomes an Event name exactly "
    "when its FNV-1 hash equals a current HIRC Event object id; the spelling is "
    "then exact, but the payload member holding the pool index is not read, so "
    "the payload-to-Event relation is structuralOnly and no caller, trigger, "
    "selected branch, posting, execution or audibility follows."
)


def collect_string_pool_event_names(
    export_root: Path,
) -> tuple[set[str], dict[str, Any]]:
    """Return grammar-matching StringPool entries plus a read audit.

    An absent pool is ``absentPool`` (older builds inline their strings and the
    length-prefixed scan covers them); a pool that fails exact framing is
    ``decodeFailed`` with the reader's diagnostic and contributes nothing,
    never a partial page set.
    """

    json_dir = ExportLayout(export_root).game / "Json"
    audit: dict[str, Any] = {
        "schemaVersion": 1,
        "source": "authoredJsonDataStringPoolEntry",
        "evidenceBoundary": STRING_POOL_EVIDENCE_BOUNDARY,
    }
    try:
        pool = export_string_pool(json_dir)
        if pool is None:
            return set(), {**audit, "status": "absentPool", "entries": 0, "candidateCount": 0}
        entries = [pool.resolve(index) for index in range(len(pool))]
    except StringPoolDecodeError as exc:
        return set(), {
            **audit,
            "status": "decodeFailed",
            "detail": str(exc),
            "entries": 0,
            "candidateCount": 0,
        }
    candidates = {
        value.lower()
        for value in entries
        if isinstance(value, str) and MANAGED_AUDIO_LITERAL_RE.fullmatch(value)
    }
    return candidates, {
        **audit,
        "status": "read",
        "pages": len(pool.counts),
        "entries": len(entries),
        "candidateCount": len(candidates),
    }


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

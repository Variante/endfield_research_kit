"""Wwise Event names taken from the member that holds them, not their spelling.

``authored_payload_event_names`` and ``gameplay_audio`` find Event names in the
serialized payloads by scanning for a length-prefixed literal matching the
shipped ``au_``/``bark_``/``radio_`` grammar.  That grammar is the only handle a
byte scan has, and it is a real one, but it can only ever find names that look
like Event names.

The payload families now decode whole, so a stronger handle exists: a string
sitting in a member the generated wrapper calls ``_soundEvent`` is an Event
reference because of *where it is*, whatever it is spelled.  That reaches names
no grammar can, and the corpus is full of them --
``eny_0125_fdcentur_lance_skill_01_a_hit`` is an Event, and begins ``eny_``.

Nothing here decides that a literal *is* an Event, and the promotion gate is
the same one the grammar sources use: a candidate becomes an Event name exactly
when its FNV-1 hash equals a current Event object id, and a candidate matching
none names nothing.  What changes is only which candidates get offered.

Two constraints keep this from becoming a different kind of guess:

* the member names are an explicit allowlist, not a pattern over member names.
  A member is admitted because it was read and found to hold Event references,
  never because its name contains ``sound``;
* a decoded value is used only when its record consumed to EOF exactly, so a
  drifted cursor cannot contribute a string at all.

A recovered spelling supplies the Event's identity and nothing else.  Caller,
trigger, selected branch, execution and audibility stay exactly as unresolved
as they were.

Fails closed: without the installed build there are no plans, so there are no
candidates and the module contributes nothing.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from pathlib import Path
from typing import Any, Iterable

from scripts.game_data.memorypack import derived_values
from scripts.game_data.memorypack.derived_plans import (
    WHOLE_RECORD_FAMILIES,
    load_registry,
)
from scripts.repo_paths import REPO_ROOT as REPO
from scripts.source_paths import ExportLayout


DEFAULT_OUTPUT = REPO / "reports/audio/decoded_payload_event_names.json"
#: Members observed to hold a Wwise Event reference, by name. This is a list of
#: members that were read, not a pattern over member names: admitting a member
#: because its name contains ``sound`` would be the same guess this module
#: exists to avoid, one level up.
EVENT_MEMBERS = ("_soundEvent", "soundEvent")
EVIDENCE_BOUNDARY = (
    "A string in one of the listed members of a record that consumed to EOF is an "
    "Event-name candidate. It becomes an Event name exactly when its FNV-1 hash "
    "equals a current Event object id, which is the same gate the grammar sources "
    "use. The name supplies identity only: caller, trigger, branch, execution and "
    "audibility are unaffected."
)


def collect_member_strings(value: Any, found: dict[str, set], member: str = "") -> None:
    """Gather every string under a member named in ``EVENT_MEMBERS``.

    A union's bookkeeping keys neither rename the member nor hide it, so a
    reference inside a union subtype is collected like any other.
    """
    if isinstance(value, dict):
        for key, item in value.items():
            collect_member_strings(item, found, member if key.startswith("$") else key)
    elif isinstance(value, list):
        for item in value:
            collect_member_strings(item, found, member)
    elif isinstance(value, str) and value and member in EVENT_MEMBERS:
        found.setdefault(member, set()).add(value)


def collect_decoded_event_names(
    export_root: Path | None = None,
) -> tuple[dict[str, set], dict[str, Any]]:
    """Every Event-name candidate the decoded payload members hold."""
    registry, audit = load_registry()
    if not registry.named_roots:
        return {}, dict(audit, families={})
    layout = (ExportLayout(root=export_root) if export_root is not None
              else ExportLayout.configured())
    found: dict[str, set] = {}
    families: dict[str, Any] = {}
    for family, type_name in sorted(WHOLE_RECORD_FAMILIES.items()):
        definition = registry.named_roots.get(type_name)
        directory = layout.json_dir / family
        if definition is None or not directory.is_dir():
            families[family] = {"status": "unavailable"}
            continue
        decoded = refused = 0
        for path in sorted(directory.glob("*.json")):
            data = path.read_bytes()
            try:
                value, reached = derived_values.decode_file(
                    data, definition, registry, source=path.name)
            except (ValueError, IndexError, struct.error, UnicodeDecodeError):
                refused += 1
                continue
            if reached != len(data):
                refused += 1
                continue
            decoded += 1
            collect_member_strings(value, found)
        families[family] = {"status": "read", "decoded": decoded, "refused": refused}
    return found, dict(audit, families=families)


def summarize_decoded_event_name_recovery(
    candidates: dict[str, set],
    audit: dict[str, Any],
    wwise_event_inventory: Iterable[dict[str, Any]],
    *,
    fnv1_32,
    grammar_reachable: set[str] | None = None,
) -> dict[str, Any]:
    """Report how many candidates a current Event object id actually claims.

    ``grammar_reachable`` is what the existing byte scan already offers. It is
    reported beside the promotion so the module's own contribution is visible
    rather than merged into a total the other sources already reach.
    """
    event_hashes = {
        int(row["eventHash"]) & 0xFFFFFFFF
        for row in wwise_event_inventory
        if isinstance(row, dict) and isinstance(row.get("eventHash"), int)
    }
    names = {value.lower() for values in candidates.values() for value in values}
    promoted = {name for name in names if fnv1_32(name) in event_hashes}
    beyond = (promoted - {value.lower() for value in grammar_reachable}
              if grammar_reachable is not None else set())
    return {
        **audit,
        "members": {member: len(values) for member, values in sorted(candidates.items())},
        "candidateCount": len(names),
        "currentWwiseEventObjectHashes": len(event_hashes),
        "promotedCount": len(promoted),
        "promotedNames": sorted(promoted),
        "beyondGrammarCount": len(beyond),
        "beyondGrammarNames": sorted(beyond),
        "expectedCoincidentalPreimages": round(
            len(names) * len(event_hashes) / float(1 << 32), 4),
        "evidenceBoundary": EVIDENCE_BOUNDARY,
    }


def build(output: Path, export_root: Path | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    output = output.resolve()
    reports = (REPO / "reports").resolve()
    if reports not in output.parents:
        raise ValueError(f"output-must-be-under={reports}")
    from scripts.webui.audio.build_audio import fnv1_32
    from scripts.webui.audio.semantics.gameplay_audio import (
        GAMEPLAY_AUDIO_EVENT_BYTES_RE,
        length_prefixed_matches,
    )

    candidates, audit = collect_decoded_event_names(export_root)
    events_file = REPO / "webui/data/lang/CN/audio/events.json"
    inventory: list[dict[str, Any]] = []
    if events_file.is_file():
        inventory = [
            {"eventHash": int(row["hash"])}
            for row in json.loads(events_file.read_bytes()).get("events", [])
            if isinstance(row.get("hash"), int)
        ]
    layout = (ExportLayout(root=export_root) if export_root is not None
              else ExportLayout.configured())
    reachable: set[str] = set()
    for family in WHOLE_RECORD_FAMILIES:
        directory = layout.json_dir / family
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            reachable.update(
                length_prefixed_matches(path.read_bytes(), GAMEPLAY_AUDIO_EVENT_BYTES_RE))
    summary = summarize_decoded_event_name_recovery(
        candidates, audit, inventory, fnv1_32=fnv1_32, grammar_reachable=reachable)
    report = {
        "schema": "endfield.audio-decoded-payload-event-names.v1",
        "audit": summary,
        "summary": {
            "status": audit.get("status", "unresolved"),
            "candidates": summary["candidateCount"],
            "promoted": summary["promotedCount"],
            "beyondGrammar": summary["beyondGrammarCount"],
            "grammarReachable": len(reachable),
            "elapsedSeconds": round(time.perf_counter() - started, 3),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--export-root", type=Path, default=None)
    args = parser.parse_args()
    try:
        report = build(args.output, args.export_root)
    except (OSError, ValueError, KeyError, TypeError, struct.error) as error:
        print(json.dumps({"status": "failed", "detail": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(report["summary"], sort_keys=True))
    return 0 if report["summary"]["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())

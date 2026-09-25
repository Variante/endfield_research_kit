"""Wwise Event names taken from the member that holds them, not their spelling.

``authored_payload_event_names`` and ``gameplay_audio`` find Event names in the
serialized payloads by scanning for a length-prefixed literal matching the
shipped ``au_``/``bark_``/``radio_`` grammar.  That grammar is the only handle a
byte scan has, and it is a real one, but it can only ever find names that look
like Event names.

The payload families now decode whole, so a stronger handle exists: a string
sitting in a member the generated wrapper calls ``_soundEvent`` is an Event
candidate because of *where it is*, whatever it is spelled. One current
SkillData member instead carries a prose sound-design instruction, so member
placement alone does not prove an Event. The source also reaches names no
grammar can --
``eny_0125_fdcentur_lance_skill_01_a_hit`` is an Event, and begins ``eny_``.

Nothing here decides that a literal *is* an Event, and the promotion gate is
the same one the grammar sources use: a candidate becomes an Event name exactly
when its FNV-1 hash equals a selected HIRC Event object id, and a candidate matching
none names nothing.  What changes is only which candidates get offered.

Two constraints keep this from becoming a different kind of guess:

* the member names are an explicit allowlist, not a pattern over member names.
  A member is admitted because it was observed to carry Event candidates,
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
import hashlib
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
from scripts.common import resolve_installed_native_inputs
from scripts.repo_paths import REPO_ROOT as REPO
from scripts.source_paths import ExportLayout
from scripts.webui.audio.semantics.play_sound_actions import (
    FAMILIES as PLAY_SOUND_FAMILIES,
    action_row,
    walk_actions,
)


DEFAULT_OUTPUT = REPO / "reports/audio/decoded_payload_event_names.json"
#: Members observed to hold Wwise Event candidates, by name. This is a list of
#: members that were read, not a pattern over member names: admitting a member
#: because its name contains ``sound`` would be the same guess this module
#: exists to avoid, one level up.
EVENT_MEMBERS = ("_soundEvent", "soundEvent")
EVIDENCE_BOUNDARY = (
    "A string in one of the listed members of a record that consumed to EOF is an "
    "Event-name candidate, not necessarily an Event reference. It becomes an "
    "Event name on this source's authority only when its FNV-1 hash "
    "equals a selected HIRC Event object id, which is the same gate the grammar sources "
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
    *,
    gameassembly: Path,
    metadata: Path,
) -> tuple[dict[str, set], set[str], list[dict[str, Any]], dict[str, Any]]:
    """Event candidates, byte grammar and exact action contexts in one read."""
    registry, audit = load_registry(gameassembly=gameassembly, metadata=metadata)
    if not registry.named_roots:
        return {}, set(), [], dict(audit, families={})
    from scripts.webui.audio.semantics.gameplay_audio import (
        GAMEPLAY_AUDIO_EVENT_BYTES_RE,
        length_prefixed_matches,
    )
    layout = (ExportLayout(root=export_root) if export_root is not None
              else ExportLayout.configured())
    found: dict[str, set] = {}
    grammar_reachable: set[str] = set()
    action_rows: list[dict[str, Any]] = []
    families: dict[str, Any] = {}
    for family, type_name in sorted(WHOLE_RECORD_FAMILIES.items()):
        definition = registry.named_roots.get(type_name)
        directory = layout.json_dir / family
        if definition is None or not directory.is_dir():
            families[family] = {"status": "unavailable"}
            continue
        decoded = refused = action_count = 0
        for path in sorted(directory.glob("*.json")):
            data = path.read_bytes()
            grammar_reachable.update(
                length_prefixed_matches(data, GAMEPLAY_AUDIO_EVENT_BYTES_RE))
            try:
                value, reached = derived_values.decode_file(
                    data, definition, registry, source=path.name)
                if reached != len(data):
                    raise ValueError(f"cursor={reached}, expected={len(data)}")
                rows = (
                    [
                        action_row(
                            family,
                            path.relative_to(layout.root).as_posix(),
                            hashlib.sha256(data).hexdigest(),
                            action_path,
                            fields,
                            ancestors,
                        )
                        for action_path, fields, ancestors in walk_actions(value)
                    ]
                    if family in PLAY_SOUND_FAMILIES else []
                )
            except (ValueError, IndexError, struct.error, UnicodeDecodeError):
                refused += 1
                continue
            decoded += 1
            action_count += len(rows)
            action_rows.extend(rows)
            collect_member_strings(value, found)
        families[family] = {
            "status": "read", "decoded": decoded, "refused": refused,
            "playSoundActions": action_count,
        }
    return found, grammar_reachable, action_rows, dict(audit, families=families)


def summarize_decoded_event_name_recovery(
    candidates: dict[str, set],
    audit: dict[str, Any],
    wwise_event_inventory: Iterable[dict[str, Any]],
    *,
    fnv1_32,
    grammar_reachable: set[str] | None = None,
) -> dict[str, Any]:
    """Report how many candidates a selected HIRC Event object id claims.

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


def load_wwise_event_inventory(path: Path) -> tuple[list[dict[str, Any]], int]:
    """Read the source Audio index's HIRC objects, excluding page-only identities."""
    payload = json.loads(path.read_bytes())
    rows = payload.get("wwiseEventInventory")
    version = payload.get("eventEvidenceSchemaVersion")
    expected = (payload.get("counts") or {}).get("wwiseEventObjectOccurrences")
    if (
        not isinstance(version, int) or version < 1
        or not isinstance(rows, list) or not isinstance(expected, int)
        or len(rows) != expected or expected == 0
        or any(not isinstance(row, dict) or not isinstance(row.get("eventHash"), int)
               for row in rows)
    ):
        raise ValueError(f"incomplete source Audio HIRC inventory: {path}")
    return rows, version


def build(
    output: Path,
    export_root: Path | None = None,
    game_root: Path | None = None,
    language: str = "CN",
) -> dict[str, Any]:
    started = time.perf_counter()
    output = output.resolve()
    reports = (REPO / "reports").resolve()
    if reports not in output.parents:
        raise ValueError(f"output-must-be-under={reports}")
    from scripts.webui.audio.semantics.identifiers import fnv1_32

    gameassembly, metadata = (
        (game_root.parent / "GameAssembly.dll",
         game_root / "il2cpp_data" / "Metadata" / "global-metadata.dat")
        if game_root is not None else resolve_installed_native_inputs()
    )
    candidates, reachable, _actions, audit = collect_decoded_event_names(
        export_root,
        gameassembly=gameassembly,
        metadata=metadata,
    )
    layout = (ExportLayout(root=export_root) if export_root is not None
              else ExportLayout.configured())
    inventory_path = layout.audio_dir / language / "index.json"
    inventory, inventory_version = load_wwise_event_inventory(inventory_path)
    summary = summarize_decoded_event_name_recovery(
        candidates, audit, inventory, fnv1_32=fnv1_32, grammar_reachable=reachable)
    summary["inventorySource"] = str(inventory_path)
    summary["inventoryEventEvidenceSchemaVersion"] = inventory_version
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
    parser.add_argument("--game-root", type=Path, default=None)
    parser.add_argument("--language", choices=("CN", "EN", "JP", "KR"), default="CN")
    args = parser.parse_args()
    try:
        report = build(args.output, args.export_root, args.game_root, args.language)
    except (OSError, ValueError, KeyError, TypeError, struct.error) as error:
        print(json.dumps({"status": "failed", "detail": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(report["summary"], sort_keys=True))
    return 0 if report["summary"]["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())

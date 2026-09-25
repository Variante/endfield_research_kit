"""Audit exact SkillData/BuffData PlaySound actions and local-reader coverage.

Whole-record MemoryPack decoding supplies the action path and its enclosing
timeline or Buff event. The strings are retained exactly as serialized; a
PlaySound member alone does not establish a current Wwise Event object.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.common import resolve_installed_native_inputs
from scripts.game_data.memorypack import derived_values
from scripts.game_data.memorypack.derived_plans import WHOLE_RECORD_FAMILIES, load_registry
from scripts.repo_paths import REPO_ROOT
from scripts.source_paths import ExportLayout
from scripts.webui.audio.semantics.play_sound_actions import (
    FAMILIES, action_row, apply_event_enum_names, selected_event_enum_names,
    walk_actions,
)


DEFAULT_OUTPUT = REPO_ROOT / "reports/audio/play_sound_action_corpus.json"


def local_action_keys(export_root: Path, family: str) -> tuple[Counter, dict[str, Any]]:
    from scripts.webui.audio.semantics.gameplay_audio import (
        collect_buff_play_sound_actions, gameplay_config_records,
    )
    local = collect_buff_play_sound_actions(
        export_root, gameplay_config_records(export_root, family)
    )
    keys: Counter = Counter()
    for events in local["byBuffEvent"].values():
        for rows in events.values():
            for row in rows:
                for source in row.get("sourcePaths") or []:
                    keys[(
                        source, row.get("eventId"), row.get("serverActionIndex"),
                        row.get("startFrame"), row.get("endFrame"),
                    )] += 1
    return keys, local["counts"]


def build(
    output: Path = DEFAULT_OUTPUT,
    *,
    export_root: Path | None = None,
    gameassembly: Path,
    metadata: Path,
) -> dict[str, Any]:
    registry, native_audit = load_registry(gameassembly=gameassembly, metadata=metadata)
    if native_audit.get("status") != "validated":
        raise ValueError(f"selected-native-gate={native_audit.get('status')}: {native_audit}")
    event_enum_names, event_enum_audit = selected_event_enum_names(gameassembly, metadata)

    layout = ExportLayout(root=export_root) if export_root else ExportLayout.configured()
    actions: list[dict[str, Any]] = []
    families: dict[str, Any] = {}
    for family in FAMILIES:
        definition = registry.named_roots.get(WHOLE_RECORD_FAMILIES[family])
        if definition is None:
            raise ValueError(f"missing-whole-record-plan={family}")
        directory = layout.json_dir / family
        if not directory.is_dir():
            raise ValueError(f"missing-payload-family={directory}")
        counts: Counter = Counter()
        failures: list[dict[str, Any]] = []
        family_actions: list[dict[str, Any]] = []
        for file in sorted(directory.glob("*.json")):
            raw = file.read_bytes()
            source = file.relative_to(layout.root).as_posix()
            digest = hashlib.sha256(raw).hexdigest()
            counts["files"] += 1
            try:
                value, reached = derived_values.decode_file(
                    raw, definition, registry, source=source
                )
                if reached != len(raw):
                    raise ValueError(f"cursor={reached}, expected={len(raw)}")
                rows = [
                    action_row(family, source, digest, path, fields, ancestors)
                    for path, fields, ancestors in walk_actions(value)
                ]
            except (ValueError, IndexError, struct.error, UnicodeDecodeError) as error:
                counts["refusedFiles"] += 1
                failures.append({
                    "sourcePath": source, "sourceSha256": digest,
                    "check": "exactWholeRecordConsumption", "detail": str(error)[:400],
                })
                continue
            counts["exactFiles"] += 1
            counts["filesWithPlaySound"] += bool(rows)
            family_actions.extend(rows)
        if not counts["files"]:
            raise ValueError(f"empty-payload-family={directory}")
        counts["playSoundActions"] = len(family_actions)
        counts["nonemptyLiterals"] = sum(
            row["eventLiteralStatus"] != "empty" for row in family_actions
        )
        counts["outerWhitespaceLiterals"] = sum(
            row["eventLiteralStatus"] == "outerWhitespaceUnresolved"
            for row in family_actions
        )
        counts["timelineActions"] = sum(
            row["startFrame"] is not None for row in family_actions
        )
        counts["buffEventActions"] = sum(
            row["buffEvent"] is not None for row in family_actions
        )
        counts["abilityEventActions"] = sum(
            row["abilityEvent"] is not None for row in family_actions
        )
        counts["nestedActions"] = sum(
            bool(row["enclosingActionTypes"]) for row in family_actions
        )
        local_keys, local_counts = local_action_keys(layout.root, family)
        local_only = local_keys.copy()
        for row in family_actions:
            key = (
                row["sourcePath"], row["eventLiteral"],
                row["serializedAction"].get("serverActionIndex"),
                row["startFrame"], row["endFrame"],
            )
            if local_keys[key]:
                local_keys[key] -= 1
                local_only[key] -= 1
                row["localReaderStatus"] = "matched"
            else:
                row["localReaderStatus"] = "missed"
        counts["localReaderMissedActions"] = sum(
            row["localReaderStatus"] == "missed" for row in family_actions
        )
        counts["localReaderOnlyActions"] = sum(local_only.values())
        families[family] = {
            "counts": dict(counts),
            "localReaderCounts": local_counts,
            "failures": failures,
        }
        actions.extend(family_actions)

    apply_event_enum_names(actions, event_enum_names)

    report = {
        "schema": "endfield.audio-play-sound-action-corpus.v2",
        "status": (
            "complete"
            if all(not row["failures"] and row["counts"]["localReaderOnlyActions"] == 0
                   for row in families.values())
            else "incomplete"
        ),
        "nativeAudit": native_audit,
        "nativeEventEnums": event_enum_audit,
        "sourceRoot": str(layout.root),
        "families": families,
        "actions": actions,
    }
    output = output.resolve()
    reports = (REPO_ROOT / "reports").resolve()
    if reports not in output.parents:
        raise ValueError(f"output-must-be-under={reports}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--export-root", type=Path)
    parser.add_argument("--game-root", type=Path)
    args = parser.parse_args()
    gameassembly, metadata = (
        (args.game_root.parent / "GameAssembly.dll",
         args.game_root / "il2cpp_data" / "Metadata" / "global-metadata.dat")
        if args.game_root else resolve_installed_native_inputs()
    )
    try:
        report = build(
            args.output, export_root=args.export_root,
            gameassembly=gameassembly, metadata=metadata,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "failed", "detail": str(error)}), file=sys.stderr)
        return 2
    print(json.dumps({
        "status": report["status"],
        "families": {family: row["counts"] for family, row in report["families"].items()},
        "output": str(args.output),
    }, sort_keys=True))
    return 0 if report["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())

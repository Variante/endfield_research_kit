"""Audit exact SkillData/BuffData PlaySound actions and local-reader coverage.

Selected-build derived-plan EOF decoding supplies the action path and its
enclosing timeline or Buff event. This is not the independent Buff child-schema
gate. The strings are retained exactly as serialized; a
PlaySound member alone does not establish a current Wwise Event object.

It is a focused audit, not a page build. It writes
``reports/audio/play_sound_action_corpus.json`` with SkillData/BuffData
PlaySound paths, enclosing timeline, Buff/Ability event context, selected
native enum labels, raw literals, and a comparison with the narrower local
action reader. It requires the selected ``GameAssembly.dll`` and
``global-metadata.dat`` and refuses incomplete whole-record decodes. To bind
the result to the current installed JsonData set, pass ``--jsondata-report``
(``reports/animestudio/jsondata_current_latest.json``), ``--jsondata-files``
(``reports/animestudio/jsondata_current_files_latest.jsonl.gz``) and
``--expected-input-set-sha256`` from the current VFS audit together; every
SkillData/BuffData export file is then checked by path, length and SHA256.
Without the three options the audit describes only the selected export
directory.

In current-corpus mode the registry report's ledger digest is checked first,
then each exported file is joined to the JsonData ledger by path, length and
logical SHA256 before decoding; source drift, omissions and extra files are
refused. A whole-plan EOF over the set is a source-set and derived-plan
closure, not the stricter independently named Buff schema. The comparison
proves the local action reader is a strict subset (see ``play_sound_actions``);
the actions it misses do not become runtime-posting evidence by being added
to an inventory.
"""

from __future__ import annotations

import argparse
import gzip
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


def _current_source_index(
    report_path: Path, files_path: Path, *, expected_input_set_sha256: str,
    json_dir: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Bind this semantic sweep to the current VFS-authenticated JsonData set."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    expected = expected_input_set_sha256.upper()
    if not isinstance(report, dict):
        raise ValueError("playSoundCurrentSource:JsonData-report-shape")
    summary = report.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("playSoundCurrentSource:JsonData-report-shape")
    recorded_input = report.get("inputSetSha256")
    export_path = report.get("exportRoot")
    if (
        len(expected) != 64 or any(char not in "0123456789ABCDEF" for char in expected)
        or report.get("format") != "endfield-jsondata-current-corpus-v1"
        or report.get("status") != "complete"
        or not isinstance(recorded_input, str) or recorded_input.upper() != expected
        or summary.get("filesSelected") != summary.get("filesJoined")
        or not isinstance(export_path, str)
        or Path(export_path).resolve() != json_dir.resolve()
    ):
        raise ValueError("playSoundCurrentSource:JsonData-report-status-or-identity")
    files_bytes = files_path.read_bytes()
    files_sha256 = hashlib.sha256(files_bytes).hexdigest().upper()
    provenance = report.get("provenance")
    output_files = provenance.get("outputFiles") if isinstance(provenance, dict) else None
    if not isinstance(output_files, dict):
        raise ValueError("playSoundCurrentSource:JsonData-ledger-digest-missing")
    if (
        output_files.get("length") != len(files_bytes)
        or output_files.get("sha256") != files_sha256
    ):
        raise ValueError(
            "playSoundCurrentSource:JsonData-ledger-digest:"
            f"expected={output_files.get('length')}/{output_files.get('sha256')}:"
            f"actual={len(files_bytes)}/{files_sha256}"
        )
    counts = summary.get("families")
    if not isinstance(counts, dict) or any(
        not isinstance(counts.get(family), dict)
        or type(counts[family].get("files")) is not int
        for family in FAMILIES
    ):
        raise ValueError("playSoundCurrentSource:JsonData-family-counts")
    rows: dict[str, dict[str, Any]] = {}
    with gzip.open(files_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("playSoundCurrentSource:JsonData-ledger-row-shape")
            family = row.get("family")
            if family not in FAMILIES:
                continue
            name = row.get("exportRelativePath")
            if (
                not isinstance(name, str) or not name.startswith(f"{family}/")
                or name in rows or not isinstance(row.get("logicalSha256"), str)
                or type(row.get("length")) is not int
            ):
                raise ValueError(f"playSoundCurrentSource:invalid-or-duplicate-row:{name}")
            rows[name] = row
    for family in FAMILIES:
        selected = sum(row["family"] == family for row in rows.values())
        if selected != counts[family]["files"]:
            raise ValueError(
                f"playSoundCurrentSource:family-count:{family}:"
                f"expected={counts[family]['files']}:actual={selected}"
            )
    return rows, {
        "status": "validated-current-jsondata-file-set",
        "inputSetSha256": expected,
        "jsonDataReportSha256": hashlib.sha256(report_path.read_bytes()).hexdigest().upper(),
        "jsonDataFilesSha256": files_sha256,
    }


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
    jsondata_report: Path | None = None,
    jsondata_files: Path | None = None,
    expected_input_set_sha256: str | None = None,
) -> dict[str, Any]:
    registry, native_audit = load_registry(gameassembly=gameassembly, metadata=metadata)
    if native_audit.get("status") != "validated":
        raise ValueError(f"selected-native-gate={native_audit.get('status')}: {native_audit}")
    event_enum_names, event_enum_audit = selected_event_enum_names(gameassembly, metadata)

    layout = ExportLayout(root=export_root) if export_root else ExportLayout.configured()
    current_args = (jsondata_report, jsondata_files, expected_input_set_sha256)
    if any(value is not None for value in current_args) and not all(
        value is not None for value in current_args
    ):
        raise ValueError("playSoundCurrentSource:all-three-current-source-options-required")
    current_rows = None
    current_audit = None
    if jsondata_report is not None and jsondata_files is not None and expected_input_set_sha256 is not None:
        current_rows, current_audit = _current_source_index(
            jsondata_report, jsondata_files,
            expected_input_set_sha256=expected_input_set_sha256,
            json_dir=layout.json_dir,
        )
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
            if current_rows is not None:
                current_name = f"{family}/{file.name}"
                current = current_rows.pop(current_name, None)
                if current is None:
                    raise ValueError(f"playSoundCurrentSource:extra-export-file:{current_name}")
                if (
                    current["length"] != len(raw)
                    or current["logicalSha256"].upper() != digest.upper()
                ):
                    raise ValueError(
                        f"playSoundCurrentSource:source-drift:{current_name}:"
                        f"expected={current['length']}/{current['logicalSha256']}:"
                        f"actual={len(raw)}/{digest.upper()}"
                    )
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

    if current_rows:
        raise ValueError(
            f"playSoundCurrentSource:missing-export-files:{sorted(current_rows)[:4]}"
        )

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
        "currentVfsJoin": current_audit,
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
    parser.add_argument("--jsondata-report", type=Path)
    parser.add_argument("--jsondata-files", type=Path)
    parser.add_argument("--expected-input-set-sha256")
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
            jsondata_report=args.jsondata_report,
            jsondata_files=args.jsondata_files,
            expected_input_set_sha256=args.expected_input_set_sha256,
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

#!/usr/bin/env python3
"""Build operator-spacecraft Story content evidence without inventing missions.

Two original-data producer shapes are accepted:

* complete DialogText buckets contained by a typed DialogTree whose authored
  options use ``SpaceshipOptionGiftData`` or ``SpaceshipOptionWorkData``;
* complete ``sim_talk`` buckets mirrored by CharacterTable ``profileVoice``
  rows, with an exact pair of profile/dialog AudioDialog records.

The installed GameAssembly/global-metadata hashes pin the reviewed consumers;
an absent or different client build skips this audit rather than publishing
classifications its recorded native facts cannot back. No filename prefix alone
admits a Story key, and no mission ownership or cross-file chronology is
emitted.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
if __package__ == "story_builder":
    from common import (
        InstalledNativeInputs,
        check_installed_native_inputs,
        md_escape,
        native_evidence_required,
        native_evidence_skip_message,
        read_json,
        rel_path,
        safe_key,
        sha256_file,
        write_report_json,
        write_text_if_changed,
    )
elif __package__ == "scripts.story_builder":
    from scripts.common import (
        InstalledNativeInputs,
        check_installed_native_inputs,
        md_escape,
        native_evidence_required,
        native_evidence_skip_message,
        read_json,
        rel_path,
        safe_key,
        sha256_file,
        write_report_json,
        write_text_if_changed,
    )
else:  # pragma: no cover - direct file execution is intentionally unsupported
    raise ImportError("run this module with python -m scripts.story_builder.spaceship_story_content")
from .anime_assets import (
    _get_anime_tree_path_index,
    _load_anime_resource_payload,
    extract_dialog_tree_definition_evidence,
)


SCHEMA = "spaceshipStoryContentAudit.v2"
DEFAULT_TABLE_ROOT = (
    ROOT / "export_full" / "structured" / "StreamingAssets" / "Table"
)
DEFAULT_REPORT_ROOT = ROOT / "reports" / "story" / "recovery"

EXPECTED_GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
EXPECTED_METADATA_SHA256 = (
    "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
)
NATIVE_MAPPING_ID = (
    "gameassembly-2026-08-02-spaceship-story-consumers-v1"
)
NATIVE_METHODS = (
    {
        "type": "Beyond.Gameplay.Core.SpaceshipOptionHandler",
        "method": "OnSelectWhenDialogEnd",
        "methodPointerVa": "0x186e515f8",
        "calls": ["_DoGiftAction", "_DoWorkAction"],
    },
    {
        "type": "Beyond.Gameplay.Core.SpaceshipOptionHandler",
        "method": "_DoGiftAction",
        "methodPointerVa": "0x186e51798",
        "calls": ["Beyond.Gameplay.SpaceshipSystem.RecvGiftFromChar"],
    },
    {
        "type": "Beyond.Gameplay.Core.SpaceshipOptionHandler",
        "method": "_DoWorkAction",
        "methodPointerVa": "0x186e518ac",
        "calls": [
            "Beyond.Gameplay.Actions.GameAction.SpaceshipChangeCharWorkState",
            "Beyond.Gameplay.Core.DialogManager.SelectDialogTreeIndex",
        ],
    },
    {
        "type": "Beyond.Gameplay.Core.SpaceshipNpcReactionManager",
        "method": "_RefreshSingleNpcGift",
        "methodPointerVa": "0x18709b7ec",
        "calls": [
            "Beyond.Cfg.SpaceshipSubCharGiftData.get_list",
            "Beyond.Gameplay.Actions.GameAction.SetOverrideInteractDialogId",
        ],
    },
)

SPACESHIP_OPTION_TYPES = frozenset({
    "Beyond.Gameplay.SpaceshipOptionGiftData",
    "Beyond.Gameplay.SpaceshipOptionWorkData",
})
LINE_SUFFIX_RE = re.compile(r"_[0-9]+(?:_[0-9]+)?$")
PROFILE_TALK_RE = re.compile(
    r"^(?P<char>chr_[0-9]+_(?P<actor>[^_]+))_sim_talk_(?P<suffix>.+)$"
)
SPACESHIP_DIALOG_LINE_RE = re.compile(
    r"^sim_(?P<family>[^_]+)_(?P<actor>[^_]+)_(?P<suffix>.+)$"
)
AUDIO_EQUALITY_FIELDS = (
    "codec",
    "isPlaceholder",
    "wavDuration",
    "wavDurationEN",
    "wavDurationJP",
    "wavDurationKR",
)


class AuditError(RuntimeError):
    pass


def _source_sha256(path: Path) -> str:
    return sha256_file(path).upper()


def story_key_for_line(line_id: str) -> str:
    base = LINE_SUFFIX_RE.sub("", safe_key(line_id))
    return f"misc_{base}" if base else ""


def dialog_groups(dialog_rows: dict[str, Any]) -> dict[str, set[str]]:
    groups: dict[str, set[str]] = defaultdict(set)
    for line_id, row in dialog_rows.items():
        if not isinstance(row, dict):
            continue
        story_key = story_key_for_line(line_id)
        if story_key:
            groups[story_key].add(line_id)
    return dict(groups)


def _collect_types(value: Any, out: set[str]) -> None:
    if isinstance(value, dict):
        type_name = safe_key(value.get("$type"))
        if type_name:
            out.add(type_name)
        for child in value.values():
            _collect_types(child, out)
    elif isinstance(value, list):
        for child in value:
            _collect_types(child, out)


def classify_dialog_tree_payload(
    payload: dict[str, Any],
    asset_name: str,
    dialog_rows: dict[str, Any],
) -> dict[str, Any] | None:
    """Return exact spaceship consumer facts for one authored DialogTree."""
    evidence = extract_dialog_tree_definition_evidence(payload, asset_name)
    if evidence is None:
        return None
    connections = payload.get("connections")
    if (
        not isinstance(connections, list)
        or evidence.get("connectionCount") != len(connections)
    ):
        return None
    all_types: set[str] = set()
    _collect_types(payload, all_types)
    consumers = sorted(all_types & SPACESHIP_OPTION_TYPES)
    if not consumers:
        return None
    line_ids = sorted({
        line_id
        for line_id in evidence.get("lineIds") or []
        if line_id in dialog_rows
    })
    if not line_ids:
        return None
    return {
        "dialogTreeRoot": asset_name,
        "lineIds": line_ids,
        "consumerClasses": consumers,
        "runtimeOptionTypes": evidence.get("runtimeOptionTypes") or [],
        "nodeCount": evidence.get("nodeCount"),
        "connectionCount": evidence.get("connectionCount"),
    }


def collect_dialog_tree_classifications(
    dialog_rows: dict[str, Any],
    tree_rows: Iterable[tuple[str, Path, dict[str, Any]]],
) -> tuple[list[dict[str, Any]], set[Path]]:
    expected = dialog_groups(dialog_rows)
    dialog_text_source = (
        "export_full/structured/StreamingAssets/Table/DialogTextTable.json"
    )
    by_story: dict[str, dict[str, Any]] = {}
    used_paths: set[Path] = set()
    for asset_name, path, payload in tree_rows:
        facts = classify_dialog_tree_payload(payload, asset_name, dialog_rows)
        if facts is None:
            continue
        for line_id in facts["lineIds"]:
            story_key = story_key_for_line(line_id)
            row = by_story.setdefault(story_key, {
                "lineIds": set(),
                "dialogTreeRoots": set(),
                "consumerClasses": set(),
                "sourceFiles": set(),
            })
            row["lineIds"].add(line_id)
            row["dialogTreeRoots"].add(asset_name)
            row["consumerClasses"].update(facts["consumerClasses"])
            row["sourceFiles"].add(rel_path(path))
            row["sourceFiles"].add(dialog_text_source)
            used_paths.add(path)

    classifications: list[dict[str, Any]] = []
    for story_key, row in sorted(by_story.items()):
        if row["lineIds"] != expected.get(story_key):
            continue
        classifications.append({
            "storyKey": story_key,
            "recoveryStatus":
                "closed_exact_spaceship_runtime_non_mission_content",
            "evidenceKind": "spaceship_dialog_tree",
            "contentClass": "operator_spaceship_dialog_tree",
            "lineIds": sorted(row["lineIds"]),
            "dialogTreeRoots": sorted(row["dialogTreeRoots"]),
            "consumerClasses": sorted(row["consumerClasses"]),
            "sourceFiles": sorted(row["sourceFiles"]),
            "nativeMappingId": NATIVE_MAPPING_ID,
            "orderBoundary": (
                "the typed DialogTree proves internal operator-spacecraft "
                "content and branch membership, not mission ownership or "
                "cross-file chronology"
            ),
        })
    return classifications, used_paths


def collect_unconsumed_spaceship_dialog_definitions(
    dialog_rows: dict[str, Any],
    tree_rows: Iterable[tuple[str, Path, dict[str, Any]]],
    classified_story_keys: set[str],
) -> tuple[list[dict[str, Any]], set[Path]]:
    """Find complete ``sim_*`` buckets absent from related typed trees.

    Actor/family relationships are derived from exact line ids carried by
    typed spaceship DialogTrees. A filename or prefix alone cannot create a
    row, and any target line carried by a related tree rejects the candidate.
    """
    typed_roots_by_context: dict[
        tuple[str, str], list[tuple[str, Path, dict[str, Any]]]
    ] = defaultdict(list)
    for asset_name, path, payload in tree_rows:
        facts = classify_dialog_tree_payload(payload, asset_name, dialog_rows)
        if facts is None:
            continue
        contexts = {
            (match.group("family"), match.group("actor"))
            for line_id in facts["lineIds"]
            if (match := SPACESHIP_DIALOG_LINE_RE.fullmatch(line_id)) is not None
        }
        for context in contexts:
            typed_roots_by_context[context].append((asset_name, path, facts))

    dialog_text_source = (
        "export_full/structured/StreamingAssets/Table/DialogTextTable.json"
    )
    classifications: list[dict[str, Any]] = []
    used_paths: set[Path] = set()
    for story_key, line_ids in sorted(dialog_groups(dialog_rows).items()):
        if story_key in classified_story_keys:
            continue
        matches = [
            SPACESHIP_DIALOG_LINE_RE.fullmatch(line_id)
            for line_id in sorted(line_ids)
        ]
        contexts = {
            (match.group("family"), match.group("actor"))
            for match in matches
            if match is not None
        }
        if len(contexts) != 1 or any(match is None for match in matches):
            continue
        context = next(iter(contexts))
        related = typed_roots_by_context.get(context) or []
        if not related:
            continue
        carried_target_lines = sorted({
            line_id
            for _asset_name, _path, facts in related
            for line_id in facts["lineIds"]
            if line_id in line_ids
        })
        if carried_target_lines:
            continue
        roots = sorted({asset_name for asset_name, _path, _facts in related})
        paths = {path for _asset_name, path, _facts in related}
        consumers = sorted({
            consumer
            for _asset_name, _path, facts in related
            for consumer in facts["consumerClasses"]
        })
        used_paths.update(paths)
        classifications.append({
            "storyKey": story_key,
            "recoveryStatus": (
                "deferred_current_build_spaceship_dialog_definition_"
                "without_tree_carrier"
            ),
            "evidenceKind": (
                "spaceship_dialog_definition_without_tree_carrier"
            ),
            "contentClass": "operator_spaceship_dialog_definition",
            "lineIds": sorted(line_ids),
            "dialogTreeRoots": roots,
            "consumerClasses": consumers,
            "dialogFamily": context[0],
            "actorId": context[1],
            "carrierStatus": "absent_from_all_related_typed_dialog_trees",
            "sourceFiles": sorted({
                dialog_text_source,
                *(rel_path(path) for path in paths),
            }),
            "nativeMappingId": NATIVE_MAPPING_ID,
            "consumerBoundary": (
                "exact typed spaceship DialogTrees consume sibling lines for "
                "the same authored actor/family pair, while no related typed "
                "tree carries any line in this complete DialogText bucket"
            ),
            "orderBoundary": (
                "the relation classifies an unconsumed spaceship definition; "
                "it proves neither playback, mission ownership, nor relative "
                "Story chronology"
            ),
        })
    return classifications, used_paths


def _audio_by_stem(audio_rows: dict[str, Any]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()
    for row in audio_rows.values():
        if not isinstance(row, dict):
            continue
        path = safe_key(row.get("path")).replace("\\", "/")
        stem = PurePosixPath(path).stem if path else ""
        if not stem:
            continue
        if stem in found:
            duplicates.add(stem)
        else:
            found[stem] = row
    for stem in duplicates:
        found.pop(stem, None)
    return found


def collect_profile_talk_classifications(
    character_rows: dict[str, Any],
    dialog_rows: dict[str, Any],
    audio_rows: dict[str, Any],
) -> list[dict[str, Any]]:
    expected = dialog_groups(dialog_rows)
    audio_by_stem = _audio_by_stem(audio_rows)
    by_story: dict[str, dict[str, Any]] = {}
    for character_id, character in character_rows.items():
        if not isinstance(character, dict):
            continue
        for profile_index, voice in enumerate(character.get("profileVoice") or []):
            if not isinstance(voice, dict):
                continue
            voice_id = safe_key(voice.get("voId"))
            match = PROFILE_TALK_RE.fullmatch(voice_id)
            if match is None or match.group("char") != character_id:
                continue
            dialog_id = (
                f"sim_talk_{match.group('actor')}_{match.group('suffix')}"
            )
            dialog = dialog_rows.get(dialog_id)
            if not isinstance(dialog, dict):
                continue
            audio_override = safe_key(dialog.get("audioOverride"))
            if audio_override != f"au_{dialog_id}":
                continue
            profile_audio = audio_by_stem.get(voice_id)
            dialog_audio = audio_by_stem.get(audio_override)
            if (
                profile_audio is None
                or dialog_audio is None
                or any(
                    profile_audio.get(field) != dialog_audio.get(field)
                    for field in AUDIO_EQUALITY_FIELDS
                )
            ):
                continue
            profile_path = safe_key(profile_audio.get("path")).replace("\\", "/")
            dialog_path = safe_key(dialog_audio.get("path")).replace("\\", "/")
            if PurePosixPath(profile_path).parent != PurePosixPath(dialog_path).parent:
                continue
            story_key = story_key_for_line(dialog_id)
            row = by_story.setdefault(story_key, {
                "lineIds": set(),
                "characterIds": set(),
                "profileVoiceIds": set(),
                "profileIndexes": set(),
            })
            row["lineIds"].add(dialog_id)
            row["characterIds"].add(character_id)
            row["profileVoiceIds"].add(voice_id)
            row["profileIndexes"].add(profile_index)

    classifications: list[dict[str, Any]] = []
    for story_key, row in sorted(by_story.items()):
        if row["lineIds"] != expected.get(story_key):
            continue
        classifications.append({
            "storyKey": story_key,
            "recoveryStatus":
                "closed_exact_spaceship_runtime_non_mission_content",
            "evidenceKind": "character_profile_voice",
            "contentClass": "operator_spaceship_profile_talk",
            "lineIds": sorted(row["lineIds"]),
            "characterIds": sorted(row["characterIds"]),
            "profileVoiceIds": sorted(row["profileVoiceIds"]),
            "profileVoiceIndexes": sorted(row["profileIndexes"]),
            "sourceFiles": [
                "export_full/structured/StreamingAssets/Table/AudioDialog.json",
                "export_full/structured/StreamingAssets/Table/CharacterTable.json",
                "export_full/structured/StreamingAssets/Table/DialogTextTable.json",
            ],
            "nativeMappingId": NATIVE_MAPPING_ID,
            "orderBoundary": (
                "the character profile and byte-equivalent audio metadata "
                "prove operator profile content, not mission ownership or "
                "cross-file chronology"
            ),
        })
    return classifications


def _source_row(path: Path) -> dict[str, Any]:
    return {
        "path": rel_path(path),
        "bytes": path.stat().st_size,
        "sha256": _source_sha256(path),
    }


def build_report(
    table_root: Path,
    native: InstalledNativeInputs,
) -> dict[str, Any]:
    table_paths = {
        name: table_root / f"{name}.json"
        for name in ("AudioDialog", "CharacterTable", "DialogTextTable")
    }
    missing = [str(path) for path in table_paths.values() if not path.is_file()]
    if missing:
        raise AuditError("missing required table(s): " + ", ".join(missing))
    if not native.validated:
        raise AuditError(native.detail)
    gameassembly = native.gameassembly
    metadata = native.metadata
    game_hash = native.gameassembly_sha256.upper()
    metadata_hash = native.metadata_sha256.upper()

    audio_rows = read_json(table_paths["AudioDialog"], {})
    character_rows = read_json(table_paths["CharacterTable"], {})
    dialog_rows = read_json(table_paths["DialogTextTable"], {})
    if not all(isinstance(value, dict) for value in (
        audio_rows, character_rows, dialog_rows
    )):
        raise AuditError("required table root is not a JSON object")

    tree_rows: list[tuple[str, Path, dict[str, Any]]] = []
    for asset_name, path in _get_anime_tree_path_index().items():
        if not asset_name.startswith("dlg_npc_") or "_spaceship" not in asset_name:
            continue
        payload = _load_anime_resource_payload(path)
        if isinstance(payload, dict):
            tree_rows.append((asset_name, path, payload))
    tree_classifications, used_tree_paths = collect_dialog_tree_classifications(
        dialog_rows,
        tree_rows,
    )
    unconsumed_classifications, unconsumed_tree_paths = (
        collect_unconsumed_spaceship_dialog_definitions(
            dialog_rows,
            tree_rows,
            {row["storyKey"] for row in tree_classifications},
        )
    )
    talk_classifications = collect_profile_talk_classifications(
        character_rows,
        dialog_rows,
        audio_rows,
    )
    classifications = sorted(
        [
            *tree_classifications,
            *talk_classifications,
            *unconsumed_classifications,
        ],
        key=lambda row: row["storyKey"],
    )
    if len({row["storyKey"] for row in classifications}) != len(classifications):
        raise AuditError("a Story key matched multiple spaceship producer classes")

    source_paths = sorted(
        {
            *table_paths.values(),
            *used_tree_paths,
            *unconsumed_tree_paths,
        },
        key=lambda path: rel_path(path),
    )
    return {
        "_schema": SCHEMA,
        "summary": {
            "classifiedStoryKeys": len(classifications),
            "dialogTreeStoryKeys": len(tree_classifications),
            "profileTalkStoryKeys": len(talk_classifications),
            "unconsumedDialogDefinitionStoryKeys": len(
                unconsumed_classifications
            ),
            "dialogTreeRoots": len(used_tree_paths),
        },
        "nativeEvidence": {
            "validated": True,
            "mappingId": NATIVE_MAPPING_ID,
            "gameAssembly": str(gameassembly),
            "gameAssemblySha256": game_hash,
            "metadata": str(metadata),
            "metadataSha256": metadata_hash,
            "methods": list(NATIVE_METHODS),
        },
        "sources": [_source_row(path) for path in source_paths],
        "classifications": classifications,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Operator-spacecraft Story Content Audit",
        "",
        "This report classifies only complete original-data producer shapes. "
        "It does not infer mission ownership or cross-file order.",
        "",
        f"- Classified Story keys: `{summary['classifiedStoryKeys']}`",
        f"- DialogTree-contained keys: `{summary['dialogTreeStoryKeys']}`",
        f"- Character profile-talk keys: `{summary['profileTalkStoryKeys']}`",
        "- Unconsumed typed-context definitions: "
        f"`{summary['unconsumedDialogDefinitionStoryKeys']}`",
        f"- Exact DialogTree roots: `{summary['dialogTreeRoots']}`",
        f"- Native mapping: `{md_escape(report['nativeEvidence']['mappingId'])}`",
        "",
        "| Story key | Evidence | Original consumers |",
        "|---|---|---|",
    ]
    for row in report["classifications"]:
        consumers = row.get("consumerClasses") or row.get("characterIds") or []
        lines.append(
            f"| `{md_escape(row['storyKey'])}` | "
            f"`{md_escape(row['evidenceKind'])}` | "
            f"{md_escape(', '.join(consumers))} |"
        )
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table-root", type=Path, default=DEFAULT_TABLE_ROOT)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_REPORT_ROOT / "spaceship_story_content_audit.json",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=DEFAULT_REPORT_ROOT / "spaceship_story_content_audit.md",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    native = check_installed_native_inputs(
        EXPECTED_GAMEASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=args.gameassembly,
        metadata=args.metadata,
    )
    if not native.validated:
        required = native_evidence_required()
        print(
            native_evidence_skip_message(
                "spaceship-story-content", native, required=required
            ),
            file=sys.stderr,
        )
        # The published report stays as it is: its own source hashes decide
        # whether the recorded classifications still describe current tables.
        return 1 if required else 0
    try:
        report = build_report(args.table_root, native)
    except AuditError as exc:
        print(f"[spaceship-story-content] {exc}", file=sys.stderr)
        return 1
    write_report_json(args.out, report)
    write_text_if_changed(args.markdown, render_markdown(report))
    print(
        "[spaceship-story-content] classified "
        f"{report['summary']['classifiedStoryKeys']} non-mission Story keys "
        f"({report['summary']['dialogTreeStoryKeys']} DialogTree, "
        f"{report['summary']['profileTalkStoryKeys']} profile talk, "
        f"{report['summary']['unconsumedDialogDefinitionStoryKeys']} "
        "unconsumed definitions)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

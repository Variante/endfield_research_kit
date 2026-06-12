#!/usr/bin/env python3
"""Find exact repeated WebUI dialog text across different missions."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


TOKEN_RE = re.compile(r"\d+|\D+")
SPACE_RE = re.compile(r"\s+")


def natural_key(value: object) -> list[object]:
    parts: list[object] = []
    for token in TOKEN_RE.findall(str(value)):
        parts.append(int(token) if token.isdigit() else token.lower())
    return parts


def configure_stdout() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure:
        reconfigure(encoding="utf-8", errors="replace")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def first_actor_name(actor_names: dict[str, Any], actor_id: str) -> str:
    names = actor_names.get(actor_id)
    if isinstance(names, list):
        for name in names:
            if isinstance(name, str) and name:
                return name
    if isinstance(names, str):
        return names
    return ""


def normalize_text(text: str, *, keep_outer_whitespace: bool, collapse_whitespace: bool) -> str:
    value = text if keep_outer_whitespace else text.strip()
    if collapse_whitespace:
        value = SPACE_RE.sub(" ", value)
    return value


def relpath(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def load_metadata(lang_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    actor_names: dict[str, Any] = {}
    mission_names: dict[str, Any] = {}

    actor_path = lang_root / "actors.json"
    if actor_path.exists():
        actor_payload = load_json(actor_path)
        if isinstance(actor_payload, dict) and isinstance(actor_payload.get("actorNames"), dict):
            actor_names = actor_payload["actorNames"]

    mission_path = lang_root / "missions.json"
    if mission_path.exists():
        mission_payload = load_json(mission_path)
        if isinstance(mission_payload, dict) and isinstance(mission_payload.get("missionNames"), dict):
            mission_names = mission_payload["missionNames"]

    return actor_names, mission_names


def line_speaker(line: dict[str, Any], actor_names: dict[str, Any]) -> tuple[str, str]:
    speaker_id = str(line.get("aid") or line.get("actorId") or line.get("speakerId") or "")
    speaker = str(line.get("actor") or line.get("speaker") or "")
    if not speaker and speaker_id:
        speaker = first_actor_name(actor_names, speaker_id)
    if not speaker and speaker_id:
        speaker = speaker_id
    if not speaker_id and speaker:
        speaker_id = speaker
    return speaker_id, speaker


def iter_occurrences(args: argparse.Namespace) -> tuple[list[dict[str, Any]], set[str]]:
    webui_root = args.webui_root
    lang_root = webui_root / "data" / "lang" / args.language
    conv_root = lang_root / "conv"
    if not conv_root.is_dir():
        raise SystemExit(f"conversation directory not found: {conv_root}")

    actor_names, mission_names = load_metadata(lang_root)
    kinds = None if args.all_kinds else set(args.kind or ["dlg"])
    wanted_speakers = set(args.speaker or [])
    wanted_ids = set(args.line_id or [])
    seen_ids: set[str] = set()
    occurrences: list[dict[str, Any]] = []

    for path in sorted(conv_root.glob("*.json"), key=lambda item: natural_key(item.name)):
        payload = load_json(path)
        if not isinstance(payload, dict):
            continue
        kind = str(payload.get("kind") or "")
        if kinds is not None and kind not in kinds:
            continue

        mission = str(payload.get("mission") or "")
        if args.mission and mission not in args.mission:
            continue

        scene_key = str(payload.get("key") or path.stem)
        scene = payload.get("scene")
        lines = payload.get("lines") or []
        if not isinstance(lines, list):
            continue

        for index, line in enumerate(lines):
            if not isinstance(line, dict):
                continue
            text = line.get("text")
            if not isinstance(text, str):
                continue
            comparable_text = normalize_text(
                text,
                keep_outer_whitespace=args.keep_outer_whitespace,
                collapse_whitespace=args.collapse_whitespace,
            )
            if not comparable_text or len(comparable_text) < args.min_chars:
                continue

            line_id = str(line.get("id") or "")
            if line_id in wanted_ids:
                seen_ids.add(line_id)

            speaker_id, speaker = line_speaker(line, actor_names)
            if wanted_speakers and speaker_id not in wanted_speakers and speaker not in wanted_speakers:
                continue

            mission_name = mission_names.get(mission) if mission else ""
            occurrences.append(
                {
                    "lineId": line_id,
                    "text": comparable_text,
                    "rawText": text,
                    "mission": mission,
                    "missionName": mission_name if isinstance(mission_name, str) else "",
                    "sceneKey": scene_key,
                    "scene": scene,
                    "kind": kind,
                    "speakerId": speaker_id,
                    "speaker": speaker,
                    "lineIndex": index,
                    "path": relpath(path, Path.cwd()),
                }
            )

    return occurrences, seen_ids


def speaker_key(occurrence: dict[str, Any]) -> str:
    return str(occurrence.get("speakerId") or occurrence.get("speaker") or "")


def summarize_speakers(occurrences: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for occurrence in occurrences:
        grouped[speaker_key(occurrence)].append(occurrence)

    summary: list[dict[str, Any]] = []
    for key, speaker_occurrences in grouped.items():
        names = sorted(
            {
                str(occurrence.get("speaker") or "")
                for occurrence in speaker_occurrences
                if occurrence.get("speaker")
            },
            key=natural_key,
        )
        missions = sorted(
            {
                str(occurrence.get("mission") or "")
                for occurrence in speaker_occurrences
                if occurrence.get("mission")
            },
            key=natural_key,
        )
        summary.append(
            {
                "speakerId": key,
                "speaker": names[0] if names else key,
                "speakerNames": names,
                "count": len(speaker_occurrences),
                "missionCount": len(missions),
                "missions": missions,
            }
        )

    return sorted(
        summary,
        key=lambda item: (-int(item["missionCount"]), -int(item["count"]), natural_key(item["speakerId"])),
    )


def duplicate_groups(args: argparse.Namespace) -> tuple[list[dict[str, Any]], set[str]]:
    occurrences, seen_ids = iter_occurrences(args)
    by_text: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for occurrence in occurrences:
        by_text[str(occurrence["text"])].append(occurrence)

    wanted_ids = set(args.line_id or [])
    wanted_texts = {
        normalize_text(
            text,
            keep_outer_whitespace=args.keep_outer_whitespace,
            collapse_whitespace=args.collapse_whitespace,
        )
        for text in (args.text or [])
    }

    groups: list[dict[str, Any]] = []
    for text, text_occurrences in by_text.items():
        mission_count = len({item["mission"] for item in text_occurrences if item.get("mission")})
        if mission_count < args.min_missions:
            continue
        if len(text_occurrences) < args.min_occurrences:
            continue
        if wanted_texts and text not in wanted_texts:
            continue
        if wanted_ids and not any(item.get("lineId") in wanted_ids for item in text_occurrences):
            continue

        speakers = summarize_speakers(text_occurrences)
        repeated_speakers = [
            item for item in speakers if int(item["missionCount"]) >= args.min_missions
        ]
        if args.same_speaker_only and not repeated_speakers:
            continue

        text_occurrences = sorted(
            text_occurrences,
            key=lambda item: (
                natural_key(item.get("mission")),
                natural_key(item.get("sceneKey")),
                natural_key(item.get("lineId")),
                int(item.get("lineIndex") or 0),
            ),
        )
        groups.append(
            {
                "text": text,
                "occurrenceCount": len(text_occurrences),
                "missionCount": mission_count,
                "speakers": speakers,
                "repeatedSpeakers": repeated_speakers,
                "occurrences": text_occurrences,
            }
        )

    groups.sort(
        key=lambda item: (
            -int(item["missionCount"]),
            -int(item["occurrenceCount"]),
            -len(str(item["text"])),
            natural_key(item["text"]),
        )
    )
    if args.limit:
        groups = groups[: args.limit]
    return groups, seen_ids


def one_line(text: object) -> str:
    return str(text).replace("\r", "\\r").replace("\n", "\\n")


def format_speaker(item: dict[str, Any]) -> str:
    speaker_id = str(item.get("speakerId") or "")
    speaker = str(item.get("speaker") or "")
    if speaker_id and speaker and speaker != speaker_id:
        return f"{speaker_id} / {speaker}"
    return speaker or speaker_id or "<unknown>"


def write_text(groups: list[dict[str, Any]], seen_ids: set[str], args: argparse.Namespace) -> None:
    if args.line_id:
        missing = sorted(set(args.line_id) - seen_ids, key=natural_key)
        for line_id in missing:
            print(f"warning: requested line id was not found in scanned data: {line_id}", file=sys.stderr)

    print(
        f"Duplicate text groups: {len(groups)} "
        f"(language={args.language}, kinds={'all' if args.all_kinds else ','.join(args.kind or ['dlg'])})"
    )
    if not groups:
        return

    for index, group in enumerate(groups, 1):
        repeated = ", ".join(format_speaker(item) for item in group["repeatedSpeakers"])
        print()
        print(
            f"[{index}] {group['occurrenceCount']} lines across {group['missionCount']} missions"
            + (f"; repeated speakers: {repeated}" if repeated else "")
        )
        print(f"    text: {one_line(group['text'])}")
        for occurrence in group["occurrences"]:
            mission = occurrence.get("mission") or "<no mission>"
            mission_name = occurrence.get("missionName") or ""
            mission_label = f"{mission} ({mission_name})" if mission_name else str(mission)
            print(
                "    - "
                f"{occurrence.get('lineId') or '<no line id>'}"
                f" | {mission_label}"
                f" | {occurrence.get('sceneKey')}"
                f" | {format_speaker(occurrence)}"
                f" | {occurrence.get('path')}"
            )


def write_json(groups: list[dict[str, Any]], seen_ids: set[str], args: argparse.Namespace) -> None:
    payload = {
        "language": args.language,
        "kinds": "all" if args.all_kinds else args.kind or ["dlg"],
        "groupCount": len(groups),
        "missingLineIds": sorted(set(args.line_id or []) - seen_ids, key=natural_key),
        "groups": groups,
    }
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    print()


def write_csv(groups: list[dict[str, Any]], seen_ids: set[str], args: argparse.Namespace) -> None:
    fieldnames = [
        "group",
        "text",
        "occurrenceCount",
        "missionCount",
        "repeatedSpeakers",
        "lineId",
        "mission",
        "missionName",
        "sceneKey",
        "kind",
        "speakerId",
        "speaker",
        "path",
    ]
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for index, group in enumerate(groups, 1):
        repeated = "; ".join(format_speaker(item) for item in group["repeatedSpeakers"])
        for occurrence in group["occurrences"]:
            writer.writerow(
                {
                    "group": index,
                    "text": group["text"],
                    "occurrenceCount": group["occurrenceCount"],
                    "missionCount": group["missionCount"],
                    "repeatedSpeakers": repeated,
                    "lineId": occurrence.get("lineId") or "",
                    "mission": occurrence.get("mission") or "",
                    "missionName": occurrence.get("missionName") or "",
                    "sceneKey": occurrence.get("sceneKey") or "",
                    "kind": occurrence.get("kind") or "",
                    "speakerId": occurrence.get("speakerId") or "",
                    "speaker": occurrence.get("speaker") or "",
                    "path": occurrence.get("path") or "",
                }
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find exact repeated spoken WebUI lines across different missions.",
    )
    parser.add_argument(
        "--webui-root",
        type=Path,
        default=Path("webui"),
        help="Path to the WebUI root. Default: webui",
    )
    parser.add_argument(
        "--language",
        default="CN",
        help="Generated WebUI language to scan. Default: CN",
    )
    parser.add_argument(
        "--kind",
        action="append",
        help="Conversation kind to scan. Repeat for more kinds. Default: dlg",
    )
    parser.add_argument(
        "--all-kinds",
        action="store_true",
        help="Scan every conversation kind under conv/ instead of only dlg.",
    )
    parser.add_argument(
        "--mission",
        action="append",
        help="Only scan this mission id. Repeat for more missions.",
    )
    parser.add_argument(
        "--speaker",
        action="append",
        help="Only include this speaker id or display name. Repeat for more speakers.",
    )
    parser.add_argument(
        "--line-id",
        action="append",
        help="Only print duplicate groups containing this line id. Repeat for more ids.",
    )
    parser.add_argument(
        "--text",
        action="append",
        help="Only print duplicate groups for this exact text after the selected whitespace normalization.",
    )
    parser.add_argument(
        "--same-speaker-only",
        action="store_true",
        help="Only report text groups where at least one speaker repeats across the required missions.",
    )
    parser.add_argument(
        "--min-missions",
        type=int,
        default=2,
        help="Minimum number of distinct missions sharing the same text. Default: 2",
    )
    parser.add_argument(
        "--min-occurrences",
        type=int,
        default=2,
        help="Minimum number of matching lines in a group. Default: 2",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=1,
        help="Skip text shorter than this many characters after normalization. Default: 1",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum groups to print. Use 0 for all. Default: 50",
    )
    parser.add_argument(
        "--keep-outer-whitespace",
        action="store_true",
        help="Keep leading/trailing whitespace when comparing text. Default strips it.",
    )
    parser.add_argument(
        "--collapse-whitespace",
        action="store_true",
        help="Collapse all whitespace runs to one space before comparing.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json", "csv"),
        default="text",
        help="Output format. Default: text",
    )
    args = parser.parse_args()
    if args.min_missions < 1:
        parser.error("--min-missions must be at least 1")
    if args.min_occurrences < 1:
        parser.error("--min-occurrences must be at least 1")
    if args.min_chars < 1:
        parser.error("--min-chars must be at least 1")
    if args.limit < 0:
        parser.error("--limit must be 0 or greater")
    return args


def main() -> None:
    configure_stdout()
    args = parse_args()
    groups, seen_ids = duplicate_groups(args)
    if args.format == "json":
        write_json(groups, seen_ids, args)
    elif args.format == "csv":
        write_csv(groups, seen_ids, args)
    else:
        write_text(groups, seen_ids, args)


if __name__ == "__main__":
    main()

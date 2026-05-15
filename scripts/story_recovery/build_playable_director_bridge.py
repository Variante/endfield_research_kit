#!/usr/bin/env python3
"""Bridge PlayableDirector JSON exports to cutscene story-context records.

Each `PlayableDirector#*.json` already exposes the cutscene prefab in its
`container` field (e.g. `assets/beyond/dynamicassets/gameplay/
cutscenetransition/cutscene_map02_lv004_jinianguan_1/prefab/...`) plus the
Timeline asset PPtr and scene bindings under `pptrReferences`. This consumer
walks all PlayableDirector JSONs under
`export_full/recovered/AnimeStudio-cli/**/json_by_type/PlayableDirector/` and
emits a structured record per cutscene that bridges:

  cutscene_<scene> -> PlayableDirector PathID -> Timeline asset name ->
  Timeline track names -> exposed-reference bindings -> source CHK

The output lives under `reports/playable_director/` and is purely
diagnostic; it does not write into the WebUI directly.

Run:

    python scripts/story_recovery/build_playable_director_bridge.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXPORT_ROOT = ROOT / "export_full" / "recovered" / "AnimeStudio-cli"
DEFAULT_OUT_DIR = ROOT / "reports" / "playable_director"

# Any story-shaped prefix the container path may carry. Recognized as a story
# binding when followed by either a scene id (`e1m1`, `c17m3d2`, ...) or a
# generic map/level id (`map02_lv004`).
STORY_PREFIXES = (
    "cutscene",
    "cutscenetransition",
    "cs",
    "dlgtl",
    "dlg",
    "levelseq",
    "lvlseq",
    "fmv",
    "sns",
)
_STORY_NAME_PATTERN = (
    r"(?P<kind>" + "|".join(STORY_PREFIXES) + r")_"
    r"(?P<scene>(?:[a-z]+\d+m\d+(?:d\d+)?|map\d+_lv\d+)[a-z0-9_]*)"
)
STORY_NAME_RE = re.compile(_STORY_NAME_PATTERN, re.IGNORECASE)
MISSION_FROM_SCENE_RE = re.compile(
    r"^(?P<mission>(?:[a-z]+\d+m\d+|map\d+_lv\d+))(?:d\d+)?",
    re.IGNORECASE,
)


def iter_playable_director_jsons(export_root: Path):
    for path in export_root.rglob("PlayableDirector/PlayableDirector#*.json"):
        if path.is_file():
            yield path


def extract_story_name(container: str) -> tuple[str, str]:
    """Find a story-shaped identifier in the container path.

    Returns (kind, full_name) where ``kind`` is one of STORY_PREFIXES and
    ``full_name`` is for example ``cutscene_map02_lv004_jinianguan_1`` or
    ``dlgtl_e10m3_9_sub_1``. Returns ``("", "")`` if nothing matches.
    """
    if not container:
        return "", ""
    match = STORY_NAME_RE.search(container)
    if match:
        kind = match.group("kind").lower()
        scene = match.group("scene")
        full = f"{kind}_{scene}"
        return kind, full
    return "", ""


def extract_mission(story_name: str) -> str:
    if not story_name:
        return ""
    # strip the leading kind_ prefix (e.g. cutscene_, dlgtl_, ...)
    stem = story_name.split("_", 1)[1] if "_" in story_name else story_name
    match = MISSION_FROM_SCENE_RE.match(stem)
    return match.group("mission") if match else ""


def summarize_one(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    meta = payload.get("$animestudio") or {}
    container = meta.get("container") or ""
    kind, story_name = extract_story_name(container)
    mission = extract_mission(story_name)
    timeline_name = ""
    binding_track_types: Counter[str] = Counter()
    binding_total = 0
    binding_resolved = 0
    binding_examples: list[str] = []
    for ref in meta.get("pptrReferences") or []:
        ref_path = ref.get("path") or ""
        target_name = ref.get("targetName") or ""
        if ref_path == "$.m_PlayableAsset":
            timeline_name = target_name
        elif ref_path.startswith("$.m_SceneBindings") and ref_path.endswith(".key"):
            binding_total += 1
            if target_name:
                binding_resolved += 1
                binding_track_types[target_name.split(" (")[0].strip() or "unknown"] += 1
                if target_name not in binding_examples:
                    binding_examples.append(target_name)
    return {
        "playableDirectorJson": str(path.relative_to(ROOT)).replace("\\", "/"),
        "playableDirectorPathId": meta.get("pathId"),
        "container": container,
        "storyName": story_name,
        "storyKind": kind,
        "mission": mission,
        "timelineName": timeline_name,
        "sourceFile": meta.get("sourceFile"),
        "sourceCHK": meta.get("sourceOriginalPath"),
        "bindingCount": binding_total,
        "bindingResolvedCount": binding_resolved,
        "trackTypeCounts": dict(binding_track_types.most_common(12)),
        "bindingExamples": binding_examples[:8],
    }


def build_report(export_root: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    skipped = 0
    for path in iter_playable_director_jsons(export_root):
        record = summarize_one(path)
        if record is None:
            skipped += 1
            continue
        records.append(record)
    by_story: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_mission: dict[str, set[str]] = defaultdict(set)
    kind_counts: Counter[str] = Counter()
    unmatched: list[dict[str, Any]] = []
    track_type_totals: Counter[str] = Counter()
    for record in records:
        name = record["storyName"]
        if name:
            by_story[name].append(record)
            kind_counts[record["storyKind"]] += 1
            if record["mission"]:
                by_mission[record["mission"]].add(name)
        else:
            unmatched.append(record)
        for tt, count in (record["trackTypeCounts"] or {}).items():
            track_type_totals[tt] += count
    summary = {
        "generated": datetime.now(tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "exportRoot": str(export_root.relative_to(ROOT)).replace("\\", "/"),
        "playableDirectorJsonCount": len(records),
        "skippedReadFailures": skipped,
        "distinctStoryNames": len(by_story),
        "distinctMissions": len(by_mission),
        "withoutStoryNameInContainer": len(unmatched),
        "storyKindCounts": dict(kind_counts.most_common()),
        "topTrackTypes": dict(track_type_totals.most_common(20)),
        "topMissionsByStoryCount": sorted(
            [(m, len(stories)) for m, stories in by_mission.items()],
            key=lambda item: item[1],
            reverse=True,
        )[:25],
    }
    stories = []
    for name in sorted(by_story):
        entries = by_story[name]
        track_totals: Counter[str] = Counter()
        for entry in entries:
            track_totals.update(entry["trackTypeCounts"])
        stories.append({
            "storyName": name,
            "storyKind": entries[0]["storyKind"],
            "mission": entries[0]["mission"],
            "playableDirectorCount": len(entries),
            "timelineNames": sorted({entry["timelineName"] for entry in entries if entry["timelineName"]}),
            "totalBindings": sum(entry["bindingCount"] for entry in entries),
            "trackTypeCounts": dict(track_totals.most_common(12)),
            "containers": sorted({entry["container"] for entry in entries if entry["container"]})[:6],
            "sourceCHKs": sorted({entry["sourceCHK"] for entry in entries if entry["sourceCHK"]})[:6],
        })
    return {
        "summary": summary,
        "stories": stories,
        "withoutStoryName": unmatched[:50],
    }


def markdown_report(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    lines = [
        "# PlayableDirector Story-Context Bridge",
        "",
        f"Generated: {s['generated']}",
        "",
        "## Summary",
        "",
        f"- PlayableDirector JSON files scanned: {s['playableDirectorJsonCount']}",
        f"- Skipped read failures: {s['skippedReadFailures']}",
        f"- Distinct story-named PlayableDirectors: {s['distinctStoryNames']}",
        f"- Distinct missions inferred: {s['distinctMissions']}",
        f"- PlayableDirectors with no story name in container: "
        f"{s['withoutStoryNameInContainer']}",
        "",
        "## Story Kind Breakdown",
        "",
        "| kind | playable directors |",
        "| --- | ---: |",
    ]
    for kind, count in s["storyKindCounts"].items():
        lines.append(f"| `{kind}` | {count} |")
    lines.extend([
        "",
        "## Top Track Types",
        "",
        "| track | count |",
        "| --- | ---: |",
    ])
    for track, count in s["topTrackTypes"].items():
        lines.append(f"| `{track}` | {count} |")
    lines.extend([
        "",
        "## Top Missions by Story Count",
        "",
        "| mission | stories |",
        "| --- | ---: |",
    ])
    for mission, count in s["topMissionsByStoryCount"]:
        lines.append(f"| `{mission}` | {count} |")
    lines.extend([
        "",
        "## Story Index (first 50)",
        "",
        "| story | kind | mission | directors | bindings | timelines |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ])
    for story in payload["stories"][:50]:
        timelines = ", ".join(f"`{name}`" for name in story["timelineNames"][:3])
        lines.append(
            f"| `{story['storyName']}` "
            f"| `{story['storyKind']}` "
            f"| `{story['mission']}` "
            f"| {story['playableDirectorCount']} "
            f"| {story['totalBindings']} "
            f"| {timelines} |"
        )
    if len(payload["stories"]) > 50:
        lines.append(f"_... {len(payload['stories']) - 50} more in JSON_")
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--export-root",
        type=Path,
        default=EXPORT_ROOT,
        help=f"AnimeStudio recovery root (default: {EXPORT_ROOT.relative_to(ROOT)})",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Report output directory (default: {DEFAULT_OUT_DIR.relative_to(ROOT)})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    export_root = args.export_root.resolve()
    if not export_root.exists():
        print(f"missing export root: {export_root}", file=sys.stderr)
        return 1
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = build_report(export_root)
    json_path = out_dir / "playable_director_bridge.json"
    md_path = out_dir / "playable_director_bridge.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown_report(payload), encoding="utf-8")
    s = payload["summary"]
    print(f"PlayableDirector bridge: {md_path.relative_to(ROOT)}")
    print(f"PlayableDirector data:   {json_path.relative_to(ROOT)}")
    print(
        f"PlayableDirector JSONs scanned: {s['playableDirectorJsonCount']}; "
        f"distinct story names: {s['distinctStoryNames']}; "
        f"distinct missions: {s['distinctMissions']}; "
        f"without story name: {s['withoutStoryNameInContainer']}"
    )
    print("kind breakdown: " + ", ".join(f"{k}={v}" for k, v in s["storyKindCounts"].items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

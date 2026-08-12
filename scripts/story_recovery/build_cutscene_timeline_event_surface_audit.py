#!/usr/bin/env python3
"""Audit exact root-playback Timeline assets for mission/event track surfaces.

The reverse-PPtr Story audit proves a small set of
CutsceneRootComponent._director -> PlayableDirector.m_PlayableAsset aliases.
Those bindings establish what the root plays, but not who activates the root.
This audit checks the exact played TimelineAsset CABs for authored event,
signal, marker, mission, quest, level, or global-event surfaces that could
provide a separate context bridge.

It is an offline recovery audit and is not part of ``export.bat``.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
from collections import Counter
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import sha256_file  # noqa: E402

DEFAULT_REVERSE_AUDIT = (
    ROOT
    / "reports"
    / "story"
    / "recovery"
    / "animestudio_story_reverse_pptr_audit.json"
)
DEFAULT_OBJECT_INDEXES = (
    ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "StreamingAssets"
    / "object_index"
    / "objects.jsonl.gz",
    ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "Persistent"
    / "object_index"
    / "objects.jsonl.gz",
)
DEFAULT_OUT = (
    ROOT
    / "reports"
    / "story"
    / "recovery"
    / "cutscene_timeline_event_surface_audit.json"
)
DEFAULT_MARKDOWN = DEFAULT_OUT.with_suffix(".md")

SURFACE_TERMS = (
    "event",
    "global",
    "level",
    "marker",
    "mission",
    "quest",
    "raise",
    "send",
    "signal",
)
TERM_RE = re.compile("|".join(re.escape(term) for term in SURFACE_TERMS), re.IGNORECASE)


class AuditError(RuntimeError):
    """Raised when an input cannot support a fail-closed result."""


def rel_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )




def object_identity(value: Any) -> tuple[str, str, int, int]:
    if not isinstance(value, dict):
        raise AuditError("object identity is not a JSON object")
    try:
        return (
            str(value["serializedFile"]),
            str(value["source"]),
            int(value["sourceOffset"]),
            int(value["pathId"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AuditError(f"incomplete object identity: {value!r}") from exc


def cab_identity(value: Any) -> tuple[str, str, int]:
    serialized_file, source, source_offset, _ = object_identity(value)
    return serialized_file, source, source_offset


def iter_jsonl(path: Path) -> Iterable[dict]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AuditError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise AuditError(f"{path}:{line_number}: row is not an object")
            yield row


def collect_aliases(reverse_payload: Any) -> list[dict]:
    if not isinstance(reverse_payload, dict):
        raise AuditError("reverse-PPtr audit is not a JSON object")
    hosts = reverse_payload.get("directorHosts")
    if not isinstance(hosts, list):
        raise AuditError("reverse-PPtr audit has no directorHosts list")

    aliases: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for host in hosts:
        if not isinstance(host, dict):
            continue
        target_object = host.get("targetObject")
        host_aliases = host.get("crossStoryPlaybackAliases")
        if not isinstance(target_object, dict) or not isinstance(host_aliases, list):
            continue
        target_identity = object_identity(target_object)
        for alias in host_aliases:
            if not isinstance(alias, dict):
                continue
            root_key = str(alias.get("rootStoryKey") or "")
            playable_key = str(alias.get("playableAssetStoryKey") or "")
            if not root_key or not playable_key:
                raise AuditError("playback alias lacks root/playable Story keys")
            if alias.get("edgeStatus") != (
                "exact_root_playback_alias_no_chronology_or_mission_owner"
            ):
                raise AuditError(
                    f"{root_key} -> {playable_key}: unexpected alias evidence status"
                )
            key = (root_key, playable_key)
            if key in seen:
                continue
            seen.add(key)
            aliases.append(
                {
                    "rootStoryKey": root_key,
                    "playableAssetStoryKey": playable_key,
                    "targetObject": {
                        "serializedFile": target_identity[0],
                        "source": target_identity[1],
                        "sourceOffset": target_identity[2],
                        "pathId": target_identity[3],
                    },
                    "relation": alias.get("relation"),
                    "edgeStatus": alias.get("edgeStatus"),
                }
            )
    if not aliases:
        raise AuditError("reverse-PPtr audit contains no exact root playback aliases")
    return sorted(
        aliases,
        key=lambda item: (item["rootStoryKey"], item["playableAssetStoryKey"]),
    )


def row_surface_hits(row: dict) -> list[dict]:
    values: list[tuple[str, Any]] = [
        ("name", row.get("name")),
        ("script", (row.get("script") or {}).get("fullName")),
    ]
    for scalar in row.get("scalars") or []:
        if not isinstance(scalar, list) or len(scalar) != 3:
            continue
        values.append((f"scalar:{scalar[0]}", scalar[2]))

    hits: list[dict] = []
    for field, value in values:
        if value is None:
            continue
        text = str(value)
        terms = sorted({match.group(0).lower() for match in TERM_RE.finditer(text)})
        if terms:
            hits.append({"field": field, "value": value, "terms": terms})
    return hits


def scan_indexes(paths: tuple[Path, ...], aliases: list[dict]) -> dict:
    wanted_objects = {
        object_identity(alias["targetObject"]): index
        for index, alias in enumerate(aliases)
    }
    wanted_cabs: dict[tuple[str, str, int], list[int]] = {}
    for index, alias in enumerate(aliases):
        wanted_cabs.setdefault(cab_identity(alias["targetObject"]), []).append(index)

    results = [
        {
            "objectCount": 0,
            "scriptClasses": Counter(),
            "surfaceHits": [],
            "timelineAssetRow": None,
            "nonNullMarkerReferences": [],
        }
        for _ in aliases
    ]
    files_read = 0
    lines_read = 0

    for path in paths:
        if not path.is_file():
            raise AuditError(f"object index does not exist: {path}")
        files_read += 1
        for row in iter_jsonl(path):
            lines_read += 1
            raw_object = row.get("object")
            if not isinstance(raw_object, dict):
                continue
            try:
                identity = object_identity(raw_object)
            except AuditError:
                continue
            target_indexes = wanted_cabs.get(identity[:3])
            if not target_indexes:
                continue

            script = row.get("script") if isinstance(row.get("script"), dict) else {}
            script_name = str(script.get("fullName") or "")
            surface_hits = row_surface_hits(row)
            marker_refs = []
            for pointer in row.get("pptrs") or []:
                if not isinstance(pointer, dict):
                    continue
                if "marker" not in str(pointer.get("path") or "").lower():
                    continue
                if int(pointer.get("pathId") or 0) != 0:
                    marker_refs.append(pointer)

            for target_index in target_indexes:
                result = results[target_index]
                result["objectCount"] += 1
                if script_name:
                    result["scriptClasses"][script_name] += 1
                if surface_hits:
                    result["surfaceHits"].append(
                        {
                            "object": raw_object,
                            "type": row.get("type"),
                            "name": row.get("name"),
                            "scriptFullName": script_name or None,
                            "matches": surface_hits,
                        }
                    )
                if marker_refs:
                    result["nonNullMarkerReferences"].append(
                        {
                            "object": raw_object,
                            "references": marker_refs,
                        }
                    )

            target_index = wanted_objects.get(identity)
            if target_index is not None:
                results[target_index]["timelineAssetRow"] = {
                    "type": row.get("type"),
                    "name": row.get("name"),
                    "scriptFullName": script_name or None,
                    "decodeStatus": row.get("decodeStatus"),
                    "typeTreeSource": row.get("typeTreeSource"),
                }

    for alias, result in zip(aliases, results):
        row = result["timelineAssetRow"]
        label = (
            f"{alias['rootStoryKey']} -> {alias['playableAssetStoryKey']}"
        )
        if row is None:
            raise AuditError(f"{label}: target TimelineAsset object was not indexed")
        if row["scriptFullName"] != "UnityEngine.Timeline.TimelineAsset":
            raise AuditError(
                f"{label}: target object is not a typed TimelineAsset: {row!r}"
            )
        if row["decodeStatus"] != "decoded":
            raise AuditError(f"{label}: target TimelineAsset is not fully decoded")
        result["scriptClasses"] = dict(sorted(result["scriptClasses"].items()))
        result["surfaceHitCount"] = len(result["surfaceHits"])
        result["nonNullMarkerReferenceCount"] = len(
            result["nonNullMarkerReferences"]
        )
        result["finding"] = (
            "no_authored_event_or_mission_surface_in_exact_played_timeline"
            if not result["surfaceHits"] and not result["nonNullMarkerReferences"]
            else "candidate_surface_requires_manual_native_semantics_review"
        )

    return {
        "filesRead": files_read,
        "linesRead": lines_read,
        "results": results,
    }


def build_report(
    reverse_path: Path,
    object_indexes: tuple[Path, ...],
) -> dict:
    reverse_payload = read_json(reverse_path)
    aliases = collect_aliases(reverse_payload)
    scan = scan_indexes(object_indexes, aliases)

    rows = []
    for alias, result in zip(aliases, scan["results"]):
        rows.append({**alias, "playedTimelineSurface": result})

    candidate_count = sum(
        row["playedTimelineSurface"]["surfaceHitCount"]
        + row["playedTimelineSurface"]["nonNullMarkerReferenceCount"]
        for row in rows
    )
    return {
        "_schema": "endfield-cutscene-timeline-event-surface-audit-v1",
        "inputs": {
            "reversePptrAudit": rel_path(reverse_path),
            "reversePptrAuditSha256": sha256_file(reverse_path),
            "reversePptrSchema": reverse_payload.get("_schema"),
            "nativeMappingId": (reverse_payload.get("nativeEvidence") or {}).get(
                "mappingId"
            ),
            "objectIndexes": [
                {"path": rel_path(path), "sha256": sha256_file(path)}
                for path in object_indexes
            ],
        },
        "summary": {
            "aliasCount": len(rows),
            "objectIndexFilesScanned": scan["filesRead"],
            "objectIndexRowsScanned": scan["linesRead"],
            "candidateSurfaceCount": candidate_count,
            "finding": (
                "no_authored_event_or_mission_surface_in_exact_played_timelines"
                if candidate_count == 0
                else "candidate_surfaces_require_manual_native_semantics_review"
            ),
        },
        "aliases": rows,
        "evidencePolicy": {
            "accepted": (
                "Exact reverse-PPtr root/director/playable binding plus exact "
                "source/CAB/offset/PathID object-index identity and fully decoded "
                "typed TimelineAsset."
            ),
            "negativeBoundary": (
                "The complete indexed CAB of the exact played TimelineAsset has "
                "no event/signal/marker/mission/quest/level/global-named typed "
                "track or scalar surface."
            ),
            "notProved": (
                "Absence of an emitted-event surface does not prove that the "
                "root is unused, definition-only, mission-owned, or ordered. "
                "External registries, server/runtime selectors, indirect native "
                "state, and future builds remain outside this audit."
            ),
        },
    }


def markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# Cutscene Timeline event-surface audit",
        "",
        f"- Root playback aliases: **{summary['aliasCount']:,}**",
        (
            "- Object indexes: "
            f"**{summary['objectIndexFilesScanned']:,}** files / "
            f"**{summary['objectIndexRowsScanned']:,}** rows"
        ),
        f"- Candidate event/mission surfaces: **{summary['candidateSurfaceCount']:,}**",
        f"- Finding: `{summary['finding']}`",
        "",
        "## Exact played Timeline assets",
        "",
        "| Root | Played TimelineAsset | CAB objects | Typed script classes | Surface |",
        "|---|---|---:|---|---|",
    ]
    for row in report["aliases"]:
        surface = row["playedTimelineSurface"]
        scripts = ", ".join(
            f"`{name}` x{count}"
            for name, count in surface["scriptClasses"].items()
        )
        lines.append(
            "| `{root}` | `{played}` | {objects:,} | {scripts} | `{finding}` |".format(
                root=row["rootStoryKey"],
                played=row["playableAssetStoryKey"],
                objects=surface["objectCount"],
                scripts=scripts,
                finding=surface["finding"],
            )
        )
    lines.extend(
        [
            "",
            "## Evidence boundary",
            "",
            report["evidencePolicy"]["accepted"],
            "",
            report["evidencePolicy"]["negativeBoundary"],
            "",
            report["evidencePolicy"]["notProved"],
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reverse-audit", type=Path, default=DEFAULT_REVERSE_AUDIT)
    parser.add_argument(
        "--object-index",
        type=Path,
        action="append",
        help="Object-index JSONL(.gz); repeat for multiple sources.",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    reverse_path = args.reverse_audit.resolve()
    object_indexes = tuple(
        path.resolve()
        for path in (args.object_index or list(DEFAULT_OBJECT_INDEXES))
    )
    report = build_report(reverse_path, object_indexes)
    write_json(args.out.resolve(), report)
    markdown_path = args.markdown.resolve()
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown(report), encoding="utf-8")
    print(
        "[cutscene-timeline-event-surface] "
        f"{report['summary']['aliasCount']} aliases; "
        f"{report['summary']['candidateSurfaceCount']} candidate surfaces"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

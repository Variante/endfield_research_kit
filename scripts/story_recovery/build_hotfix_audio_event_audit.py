#!/usr/bin/env python3
"""Audit HotfixAudio media ids against embedded Wwise event metadata.

The maintained audio relinker includes HotfixAudio in its fingerprinted bank
set. This focused report streams the five Hotfix PCKs, resolves bank-local HIRC
objects against their package-family media union, and checks the decoded shared
audio inventory against Wwise event hashes and known event names.

Output:

    reports/story/recovery/hotfix_audio_event_audit.json
    reports/story/recovery/hotfix_audio_event_audit.md
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from struct import unpack_from
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from build_audio import (  # noqa: E402
    AUDIO_EXTENSIONS,
    DEFAULT_AUDIO_DUMPER,
    DEFAULT_EXPORT_ROOT,
    DEFAULT_GAME_ROOT,
    DEFAULT_WEBUI_ROOT,
    collect_audio_event_names,
    event_audio_category,
    fnv1_32,
    iter_bnk_sections,
    iter_akpk_bank_payloads_from_bytes,
    iter_akpk_media_ids_from_bytes,
    normalize_posix,
    parse_hirc_objects,
    traverse_hirc_event,
)
from common import ROOT, md_escape, write_report_json, write_text_if_changed  # noqa: E402

REPORT_DIR = ROOT / "reports" / "story" / "recovery"
DEFAULT_JSON = REPORT_DIR / "hotfix_audio_event_audit.json"
DEFAULT_MD = REPORT_DIR / "hotfix_audio_event_audit.md"
DEFAULT_HOTFIX_ASSETS = DEFAULT_GAME_ROOT / "Persistent"
DEFAULT_FALLBACK_ASSETS = DEFAULT_GAME_ROOT / "StreamingAssets"
DEFAULT_CONV_DIR = DEFAULT_WEBUI_ROOT / "data" / "lang" / "CN" / "conv"
DEFAULT_DECODED_ROOT = DEFAULT_EXPORT_ROOT / "structured" / "Audio"
DEFAULT_FILE_REGEX = r"(^|[\\/])hotfix.*\.pck$"


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path)


def hex_u32(value: int) -> str:
    return f"0x{value:08x}"


def stream_hotfix_pcks(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[str]]:
    command = [
        str(args.audio_dumper),
        "stream",
        "--streaming-assets",
        str(args.hotfix_assets),
        "--block-type",
        "hotfix-audio",
        "--file-regex",
        args.file_regex,
    ]
    if args.fallback_assets and args.fallback_assets.exists():
        command.extend(["--fallback-assets", str(args.fallback_assets)])

    result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    diagnostics = []
    if result.stderr.strip():
        diagnostics.append(result.stderr.strip())

    rows = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        raw_data = base64.b64decode(str(payload.get("dataBase64") or ""))
        if not raw_data:
            continue
        rows.append(
            {
                "blockType": str(payload.get("blockType") or "unknown"),
                "fileName": normalize_posix(str(payload.get("fileName") or "unknown.pck")),
                "bytes": len(raw_data),
                "data": raw_data,
            }
        )
    return rows, diagnostics


def decoded_media_stats(root: Path) -> dict[int, dict[str, Any]]:
    stats: dict[int, dict[str, Any]] = {}
    if not root.exists():
        return stats
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        if not path.stem.isdigit():
            continue
        media_id = int(path.stem)
        stats[media_id] = {
            "decodedPath": repo_rel(path),
            "decodedBytes": path.stat().st_size,
            "extension": path.suffix.lower().lstrip("."),
        }
    return stats


def append_unique(values: list[int], value: int) -> None:
    if value not in values:
        values.append(value)


def trace_event_media(
    objects: dict[int, dict[str, Any]],
    event_id: int,
    media_ids: set[int],
    bank_version: int | None,
) -> dict[str, Any] | None:
    traversal = traverse_hirc_event(
        event_id,
        objects,
        media_ids,
        bank_version=bank_version,
    )
    resolved = traversal.get("mediaIds") or []
    return {
        "eventHash": event_id,
        "eventHashHex": hex_u32(event_id),
        "bankVersion": bank_version,
        "actionIds": traversal.get("actionIds") or [],
        "visitedObjectCount": len(traversal.get("visitedObjectIds") or []),
        "visitedObjectSamples": (traversal.get("visitedObjectIds") or [])[:80],
        "mediaIds": resolved,
        "sourceMediaIds": traversal.get("sourceMediaIds") or [],
        "resolvedMediaCount": len(resolved),
        "rootPlayActionCount": traversal.get("rootPlayActionCount") or 0,
        "rootStopActionCount": traversal.get("rootStopActionCount") or 0,
        "actionEvidence": traversal.get("actionEvidence") or [],
        "traversalStatus": traversal.get("traversalStatus"),
        "unresolvedNodes": traversal.get("unresolvedNodes") or [],
    }


def known_event_names_by_hash(conv_dir: Path, export_root: Path) -> dict[int, list[str]]:
    names = collect_audio_event_names(conv_dir, export_root)
    prior_index = export_root / "structured" / "Audio" / "CN" / "index.json"
    if prior_index.is_file():
        payload = json.loads(prior_index.read_text(encoding="utf-8"))
        names.update(
            str(value or "").strip()
            for value in payload.get("eventNames") or []
            if str(value or "").strip()
        )
    webui_events = conv_dir.parent / "audio" / "events.json"
    if webui_events.is_file():
        payload = json.loads(webui_events.read_text(encoding="utf-8"))
        names.update(
            str(row.get("name") or row.get("id") or "").strip()
            for row in payload.get("events") or []
            if isinstance(row, dict) and str(row.get("name") or row.get("id") or "").strip()
        )
    by_hash: dict[int, list[str]] = defaultdict(list)
    for name in sorted(names):
        by_hash[fnv1_32(name.lower())].append(name)
    return dict(by_hash)


def indexed_event_names_by_media(export_root: Path) -> dict[int, list[str]]:
    """Load named Event relations from the complete current bank scan."""
    index_path = export_root / "structured" / "Audio" / "CN" / "index.json"
    if not index_path.is_file():
        return {}
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    by_media: dict[int, set[str]] = defaultdict(set)
    for row in payload.get("events") or []:
        if not isinstance(row, dict):
            continue
        try:
            media_id = int(row.get("mediaId"))
        except (TypeError, ValueError):
            continue
        name = str(row.get("eventId") or row.get("id") or "").strip()
        if name:
            by_media[media_id].add(name)
    return {media_id: sorted(names) for media_id, names in by_media.items()}


def indexed_wwise_event_hashes_by_media(export_root: Path) -> dict[int, list[int]]:
    """Load every raw Event-object relation from the complete current scan."""
    index_path = export_root / "structured" / "Audio" / "CN" / "index.json"
    if not index_path.is_file():
        return {}
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    by_media: dict[int, set[int]] = defaultdict(set)
    for row in payload.get("wwiseEventInventory") or []:
        if not isinstance(row, dict):
            continue
        try:
            event_hash = int(row.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            continue
        for value in row.get("mediaIds") or []:
            try:
                by_media[int(value)].add(event_hash)
            except (TypeError, ValueError):
                continue
    return {media_id: sorted(hashes) for media_id, hashes in by_media.items()}


def classify_event_row(row: dict[str, Any], hotfix_media_ids: set[int]) -> str:
    resolved = {int(value) for value in row.get("mediaIds") or []}
    source = {int(value) for value in row.get("sourceMediaIds") or []}
    if str(row.get("traversalStatus") or "") != "complete":
        return "partialObjectGraph"
    if resolved & hotfix_media_ids:
        return "hotfixMediaPlayback"
    if resolved:
        return "decodedBaseMediaPlayback"
    if source:
        return "sourceMediaOutsideDecodedLanguage"
    actions = row.get("actionEvidence") or []
    if actions and not any(bool(action.get("traversed")) for action in actions):
        return "controlOnly"
    return "noMediaLeaf"


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    pcks, diagnostics = stream_hotfix_pcks(args)
    decoded_stats = decoded_media_stats(args.decoded_root)
    known_by_hash = known_event_names_by_hash(args.conv_dir, args.export_root)
    indexed_names_by_media = indexed_event_names_by_media(args.export_root)
    indexed_hashes_by_media = indexed_wwise_event_hashes_by_media(args.export_root)

    pck_rows = []
    event_rows = []
    media_ids: set[int] = set()
    embedded_bank_count = 0

    for pck_index, pck in enumerate(pcks):
        raw_data = pck["data"]
        pck_media_ids = set(iter_akpk_media_ids_from_bytes(raw_data, pck["fileName"]))
        media_ids.update(pck_media_ids)
        bank_payloads = iter_akpk_bank_payloads_from_bytes(raw_data, pck["fileName"])
        embedded_bank_count += len(bank_payloads)
        pck["mediaIds"] = pck_media_ids
        pck["bankPayloads"] = bank_payloads
        pck_rows.append(
            {
                "index": pck_index,
                "blockType": pck["blockType"],
                "fileName": pck["fileName"],
                "bytes": pck["bytes"],
                "sha256": hashlib.sha256(raw_data).hexdigest(),
                "mediaIdCount": len(pck_media_ids),
                "embeddedBankCount": len(bank_payloads),
                "mediaIds": sorted(pck_media_ids),
            }
        )
    # Language Hotfix PCKs can carry Event/Action/Sound objects whose media is
    # physically stored in hotfix_main.pck. Resolve every bank against the
    # package-family media union while keeping each bank's HIRC object graph
    # isolated so unrelated object-id collisions cannot create false edges.
    for pck in pcks:
        for bank_id, bank_payload in pck["bankPayloads"]:
            bank_version = None
            for tag, body in iter_bnk_sections(bank_payload):
                if tag == b"BKHD" and len(body) >= 4:
                    bank_version = unpack_from("<I", body, 0)[0]
                    break
            objects = parse_hirc_objects(bank_payload)
            if not objects:
                continue
            for event_id, event_object in sorted(objects.items()):
                if int(event_object.get("type") or 0) != 4:
                    continue
                traced = trace_event_media(objects, event_id, set(decoded_stats), bank_version)
                known_names = known_by_hash.get(event_id, [])
                event_row = {
                        "sourcePck": pck["fileName"],
                        "bankId": bank_id,
                        "bankIdHex": hex_u32(bank_id),
                        "knownEventNames": known_names,
                        "eventCategories": sorted(
                            {
                                event_audio_category(name)
                                for name in known_names
                                if event_audio_category(name)
                            }
                        ),
                        **traced,
                    }
                event_row["hotfixMediaIds"] = sorted(
                    set(event_row.get("mediaIds") or []) & media_ids
                )
                event_row["eventRole"] = classify_event_row(event_row, media_ids)
                event_rows.append(event_row)

    event_rows.sort(key=lambda row: (str(row.get("sourcePck") or ""), int(row.get("eventHash") or 0)))
    events_by_media: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in event_rows:
        for media_id in row.get("hotfixMediaIds") or []:
            events_by_media[int(media_id)].append(row)

    media_rows = []
    for media_id in sorted(media_ids):
        events = events_by_media.get(media_id, [])
        known_names = sorted({name for event in events for name in event.get("knownEventNames") or []})
        indexed_names = indexed_names_by_media.get(media_id, [])
        indexed_hashes = indexed_hashes_by_media.get(media_id, [])
        if events:
            playback_location_status = "hotfixEventObject"
        elif indexed_names:
            playback_location_status = "namedEventObjectOutsideHotfix"
        elif indexed_hashes:
            playback_location_status = "unnamedEventObjectOutsideHotfix"
        else:
            playback_location_status = "unknownAcrossCompleteEventObjectInventory"
        media_rows.append(
            {
                "mediaId": media_id,
                "mediaIdHex": hex_u32(media_id),
                **decoded_stats.get(media_id, {}),
                "eventHashCount": len(events),
                "eventHashes": [row.get("eventHashHex") for row in events],
                "knownEventNames": known_names,
                "knownEventNameCount": len(known_names),
                "scannedNamedEventNames": indexed_names,
                "scannedNamedEventCount": len(indexed_names),
                "scannedEventHashes": [hex_u32(value) for value in indexed_hashes],
                "scannedEventHashCount": len(indexed_hashes),
                "playbackLocationStatus": playback_location_status,
            }
        )

    media_with_events = [row for row in media_rows if int(row.get("eventHashCount") or 0) > 0]
    media_with_known_names = [row for row in media_rows if int(row.get("knownEventNameCount") or 0) > 0]
    media_recovered_by_other_banks = [
        row for row in media_rows
        if row.get("playbackLocationStatus") == "namedEventObjectOutsideHotfix"
    ]
    media_recovered_by_unnamed_events = [
        row for row in media_rows
        if row.get("playbackLocationStatus") == "unnamedEventObjectOutsideHotfix"
    ]
    media_location_unknown = [
        row for row in media_rows
        if row.get("playbackLocationStatus") == "unknownAcrossCompleteEventObjectInventory"
    ]
    decoded_total_bytes = sum(int(row.get("decodedBytes") or 0) for row in media_rows)

    known_event_name_candidate_count = sum(len(names) for names in known_by_hash.values())

    return {
        "metadata": {
            "audioDumper": repo_rel(args.audio_dumper),
            "hotfixAssets": repo_rel(args.hotfix_assets),
            "fallbackAssets": repo_rel(args.fallback_assets),
            "exportRoot": repo_rel(args.export_root),
            "convDir": repo_rel(args.conv_dir),
            "decodedRoot": repo_rel(args.decoded_root),
            "fileRegex": args.file_regex,
        },
        "summary": {
            "hotfixPckCount": len(pcks),
            "embeddedBankCount": embedded_bank_count,
            "mediaIdCount": len(media_ids),
            "decodedFileCount": sum(1 for row in media_rows if row.get("decodedPath")),
            "decodedTotalBytes": decoded_total_bytes,
            "eventObjectCount": len(event_rows),
            "eventHashLinkCount": sum(bool(row.get("mediaIds")) for row in event_rows),
            "knownEventObjectCount": sum(bool(row.get("knownEventNames")) for row in event_rows),
            "knownEventNameCandidateCount": known_event_name_candidate_count,
            "mediaWithEventHashCount": len(media_with_events),
            "mediaWithKnownEventNameCount": len(media_with_known_names),
            "knownEventNameHitCount": sum(len(row.get("knownEventNames") or []) for row in event_rows),
            "hotfixLocalUnresolvedMediaIdCount": len(media_ids) - len(media_with_events),
            "recoveredByOtherBankNamedEventCount": len(media_recovered_by_other_banks),
            "recoveredByOtherBankUnnamedEventCount": len(media_recovered_by_unnamed_events),
            "unresolvedMediaIdCount": len(media_location_unknown),
            "unknownEventRoleCounts": dict(sorted(Counter(
                row.get("eventRole") or "unknown"
                for row in event_rows
                if not row.get("knownEventNames")
            ).items())),
            "diagnostics": diagnostics,
        },
        "interpretation": [
            "This audit parses HotfixAudio PCK bank metadata directly and checks the maintained decoded shared-audio root; it does not modify decoded audio or WebUI data.",
            "Language Hotfix banks are resolved against the current decoded shared/CN media inventory, while HIRC object graphs remain bank-local.",
            "A Hotfix media id absent from Hotfix-local Event graphs is checked against every raw Event object from the complete nine-PCK bank scan before its playback location is called unknown.",
            "Event hashes without known event names are still useful Wwise references, but need a name source before category-based linking.",
            "Media ids with no event hash evidence may be direct/unreferenced media or may require broader Wwise object decoding.",
        ],
        "pcks": [{key: value for key, value in row.items() if key != "data"} for row in pck_rows],
        "events": event_rows,
        "media": media_rows,
    }


def render_names(values: list[str], limit: int = 3) -> str:
    if not values:
        return "-"
    shown = values[:limit]
    suffix = "" if len(values) <= limit else f" (+{len(values) - limit})"
    return ", ".join(shown) + suffix


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# HotfixAudio Event Audit",
        "",
        f"- audio dumper: `{md_escape(payload.get('metadata', {}).get('audioDumper'))}`",
        f"- hotfix assets: `{md_escape(payload.get('metadata', {}).get('hotfixAssets'))}`",
        f"- fallback assets: `{md_escape(payload.get('metadata', {}).get('fallbackAssets'))}`",
        f"- decoded root: `{md_escape(payload.get('metadata', {}).get('decodedRoot'))}`",
        f"- hotfix PCKs: `{summary.get('hotfixPckCount')}`",
        f"- embedded banks: `{summary.get('embeddedBankCount')}`",
        f"- media ids: `{summary.get('mediaIdCount')}`",
        f"- decoded files: `{summary.get('decodedFileCount')}` "
        f"({summary.get('decodedTotalBytes')} bytes)",
        f"- Event objects: `{summary.get('eventObjectCount')}`",
        f"- Event objects with media links: `{summary.get('eventHashLinkCount')}`",
        f"- Event objects with known names: `{summary.get('knownEventObjectCount')}`",
        f"- known event-name candidates tested: `{summary.get('knownEventNameCandidateCount')}`",
        f"- media with event hash: `{summary.get('mediaWithEventHashCount')}`",
        f"- media with known event name: `{summary.get('mediaWithKnownEventNameCount')}`",
        f"- media without a Hotfix-local Event but recovered through another scanned bank: `{summary.get('recoveredByOtherBankNamedEventCount')}`",
        f"- media recovered only through unnamed Event hashes in another scanned bank: `{summary.get('recoveredByOtherBankUnnamedEventCount')}`",
        f"- unresolved media ids: `{summary.get('unresolvedMediaIdCount')}`",
        "",
        "## Interpretation",
        "",
    ]
    for item in payload.get("interpretation") or []:
        lines.append(f"- {md_escape(item)}")

    lines.extend(
        [
            "",
            "## PCKs",
            "",
            "| file | bytes | SHA-256 | media ids | banks |",
            "| --- | ---: | --- | ---: | ---: |",
        ]
    )
    for row in payload.get("pcks") or []:
        lines.append(
            f"| `{md_escape(row.get('fileName'))}` | {row.get('bytes')} | `{row.get('sha256')}` | "
            f"{row.get('mediaIdCount')} | {row.get('embeddedBankCount')} |"
        )

    lines.extend(
        [
            "",
            "## Media Links",
            "",
            "| media id | decoded bytes | event hashes | known event names |",
            "| ---: | ---: | ---: | --- |",
        ]
    )
    for row in (payload.get("media") or [])[:80]:
        lines.append(
            f"| `{row.get('mediaId')}` | {row.get('decodedBytes') or '-'} | "
            f"{row.get('eventHashCount')} | `{md_escape(render_names(row.get('knownEventNames') or []))}` |"
        )

    lines.extend(
        [
            "",
            "## Event Hashes",
            "",
            "| event hash | bank | media ids | known event names |",
            "| ---: | ---: | --- | --- |",
        ]
    )
    for row in (payload.get("events") or [])[:80]:
        media_ids = ", ".join(str(value) for value in row.get("mediaIds") or [])
        lines.append(
            f"| `{row.get('eventHashHex')}` | `{row.get('bankId')}` | "
            f"`{md_escape(media_ids)}` | `{md_escape(render_names(row.get('knownEventNames') or []))}` |"
        )

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio-dumper", type=Path, default=DEFAULT_AUDIO_DUMPER)
    parser.add_argument("--hotfix-assets", type=Path, default=DEFAULT_HOTFIX_ASSETS)
    parser.add_argument("--fallback-assets", type=Path, default=DEFAULT_FALLBACK_ASSETS)
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT_ROOT)
    parser.add_argument("--conv-dir", type=Path, default=DEFAULT_CONV_DIR)
    parser.add_argument("--decoded-root", type=Path, default=DEFAULT_DECODED_ROOT)
    parser.add_argument("--file-regex", default=DEFAULT_FILE_REGEX)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(args)
    write_report_json(args.json, payload)
    write_text_if_changed(args.markdown, render_markdown(payload))
    summary = payload["summary"]
    print(f"HotfixAudio event audit: {args.json}")
    print(f"HotfixAudio event report: {args.markdown}")
    print(
        "mediaIds="
        f"{summary['mediaIdCount']} "
        f"eventHashes={summary['eventHashLinkCount']} "
        f"knownNamedMedia={summary['mediaWithKnownEventNameCount']} "
        f"unresolvedMedia={summary['unresolvedMediaIdCount']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

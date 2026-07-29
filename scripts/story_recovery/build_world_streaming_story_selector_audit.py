#!/usr/bin/env python3
"""Audit skipped world-streaming bytes for unresolved Story-root selectors.

The normal WebUI export intentionally skips the Streaming and DynamicStreaming
VFS block families. This audit streams those files through AnimeStudio without
materializing them, then searches for exact unresolved Story root names,
registered resource paths, and both byte orders of their StringPathHash values.
It also checks the complete AnimeStudio object indexes for the ordered
Encounter/BattlerStage authoring systems that can call cutscene playback.
"""

from __future__ import annotations

import argparse
import base64
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import write_report_json, write_text_if_changed  # noqa: E402


DEFAULT_CLI = (
    ROOT
    / "tools"
    / "AnimeStudio"
    / "AnimeStudio.CLI"
    / "bin"
    / "Release"
    / "net9.0-windows"
    / "AnimeStudio.CLI.exe"
)
DEFAULT_GAME_ROOT = Path(
    os.environ.get(
        "ENDFIELD_GAME_ROOT",
        r"D:\Program Files\Endfield Game\Endfield_Data",
    )
)
DEFAULT_HASH_AUDIT = (
    ROOT
    / "reports"
    / "story"
    / "recovery"
    / "string_path_hash_story_audit.json"
)
DEFAULT_OBJECT_INDEX_ROOT = (
    ROOT / "export_full" / "recovered" / "AnimeStudio-cli"
)
DEFAULT_OUT = (
    ROOT
    / "reports"
    / "story"
    / "recovery"
    / "world_streaming_story_selector_audit.json"
)
DEFAULT_MARKDOWN = DEFAULT_OUT.with_suffix(".md")
DEFAULT_SOURCES = ("streaming", "persistent")

ORDERED_SYSTEM_TYPE_TERMS = (
    "battlerstage",
    "bossbattlerdata",
    "encounter",
)
ORDERED_SYSTEM_FIELD_LEAVES = frozenset({
    "activatemodealter",
    "activatetriggerslotidalter",
    "battlerstagedata",
    "checkpointpropertykey",
    "completedelaymode",
    "completedelaystrparam",
    "intropartalter",
    "operasegments",
    "operatype",
    "stagedatalist",
})
ARRAY_SUFFIX_RE = re.compile(r"\[[0-9]+\]$")


class AuditError(RuntimeError):
    pass


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_leaf(path: str) -> str:
    leaf = str(path or "").rsplit(".", 1)[-1]
    while ARRAY_SUFFIX_RE.search(leaf):
        leaf = ARRAY_SUFFIX_RE.sub("", leaf)
    return re.sub(r"[^a-z0-9]", "", leaf.lower())


def load_hash_targets(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"failed to read StringPathHash audit {path}: {exc}") from exc
    if int(report.get("schemaVersion") or 0) < 3:
        raise AuditError("StringPathHash audit predates the native-consumer census")
    rows = report.get("targetHashPaths")
    if not isinstance(rows, list) or not rows:
        raise AuditError("StringPathHash audit has no targetHashPaths")
    for index, row in enumerate(rows):
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("target"), str)
            or not isinstance(row.get("path"), str)
            or not isinstance(row.get("hashUnsigned"), int)
        ):
            raise AuditError(f"malformed targetHashPaths row {index}")
    return report, rows


def build_patterns(rows: Iterable[dict[str, Any]]) -> dict[bytes, list[dict[str, Any]]]:
    target_rows = list(rows)
    patterns: dict[bytes, list[dict[str, Any]]] = defaultdict(list)
    targets = sorted({str(row["target"]) for row in target_rows})
    paths = sorted({str(row["path"]) for row in target_rows})
    for target in targets:
        patterns[target.encode("utf-8")].append({
            "kind": "root_ascii",
            "value": target,
        })
        patterns[target.encode("utf-16le")].append({
            "kind": "root_utf16le",
            "value": target,
        })
    for path in paths:
        patterns[path.encode("utf-8")].append({
            "kind": "resource_path_ascii",
            "value": path,
        })
        patterns[path.encode("utf-16le")].append({
            "kind": "resource_path_utf16le",
            "value": path,
        })
    for row in target_rows:
        value = int(row["hashUnsigned"])
        for byte_order in ("little", "big"):
            patterns[value.to_bytes(8, byte_order)].append({
                "kind": f"hash_{byte_order}",
                "value": str(row.get("hashHex") or f"0x{value:016x}"),
                "target": row["target"],
                "path": row["path"],
            })
    return dict(patterns)


def pattern_summary(patterns: dict[bytes, list[dict[str, Any]]]) -> dict[str, Any]:
    identities = [identity for rows in patterns.values() for identity in rows]
    categories = Counter(str(row["kind"]) for row in identities)
    return {
        "uniqueBytePatterns": len(patterns),
        "patternIdentities": len(identities),
        "categories": dict(sorted(categories.items())),
    }


def stream_command(
    cli: Path,
    game_root: Path,
    source: str,
) -> list[str]:
    if source not in DEFAULT_SOURCES:
        raise AuditError(f"unsupported source {source!r}")
    source_root = game_root / (
        "Persistent" if source == "persistent" else "StreamingAssets"
    )
    command = [
        str(cli),
        "stream",
        "--streaming-assets",
        str(source_root),
    ]
    if source == "persistent":
        command.extend([
            "--fallback-assets",
            str(game_root / "StreamingAssets"),
        ])
    command.extend([
        "--block-type",
        "streaming",
        "--block-type",
        "dynamic-streaming",
    ])
    return command


def scan_stream_source(
    cli: Path,
    game_root: Path,
    source: str,
    patterns: dict[bytes, list[dict[str, Any]]],
) -> dict[str, Any]:
    matcher = re.compile(b"|".join(re.escape(value) for value in patterns))
    command = stream_command(cli, game_root, source)
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="strict",
        bufsize=1,
    )
    assert process.stdout is not None
    started = time.perf_counter()
    counts: Counter[str] = Counter()
    corpus_digest = hashlib.sha256()
    hits: list[dict[str, Any]] = []
    stdout_messages: list[str] = []
    for line in process.stdout:
        line = line.strip()
        if not line:
            continue
        if not line.startswith("{"):
            stdout_messages.append(line)
            continue
        try:
            row = json.loads(line)
            payload = base64.b64decode(row["dataBase64"], validate=True)
            expected = int(row["length"])
            block_type = str(row["blockType"])
            file_name = str(row["fileName"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            process.kill()
            raise AuditError(f"{source}: malformed stream row: {exc}") from exc
        if len(payload) != expected:
            process.kill()
            raise AuditError(
                f"{source}:{file_name}: decoded {len(payload)} bytes, "
                f"expected {expected}"
            )
        counts["files"] += 1
        counts["bytes"] += len(payload)
        counts[f"{block_type}Files"] += 1
        counts[f"{block_type}Bytes"] += len(payload)
        encoded_name = file_name.encode("utf-8")
        corpus_digest.update(len(encoded_name).to_bytes(4, "little"))
        corpus_digest.update(encoded_name)
        corpus_digest.update(len(payload).to_bytes(8, "little"))
        corpus_digest.update(payload)
        for match in matcher.finditer(payload):
            for identity in patterns[match.group(0)]:
                hits.append({
                    "blockType": block_type,
                    "fileName": file_name,
                    "fileLength": len(payload),
                    "offset": match.start(),
                    **identity,
                })
        if counts["files"] % 5000 == 0:
            print(
                f"{source}: {counts['files']:,} files / "
                f"{counts['bytes']:,} bytes / {len(hits):,} hits",
                flush=True,
            )
    stderr = process.stderr.read() if process.stderr is not None else ""
    return_code = process.wait()
    if return_code:
        raise AuditError(
            f"{source}: AnimeStudio stream failed with {return_code}: "
            f"{stderr.strip()}"
        )
    return {
        "source": source,
        "streamingAssets": command[3],
        "fallbackAssets": (
            command[5] if "--fallback-assets" in command else None
        ),
        "blockTypes": ["Streaming", "DynamicStreaming"],
        "counts": dict(sorted(counts.items())),
        "corpusSha256": corpus_digest.hexdigest(),
        "exactHitCount": len(hits),
        "hits": hits,
        "stdoutMessages": stdout_messages,
        "stderr": stderr.strip(),
        "seconds": round(time.perf_counter() - started, 3),
    }


def iter_gzip_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AuditError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise AuditError(f"{path}:{line_number}: row is not an object")
            yield row


def ordered_system_matches(row: dict[str, Any]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    script = row.get("script")
    script_name = (
        str(script.get("fullName") or "")
        if isinstance(script, dict)
        else ""
    )
    object_type = str(row.get("type") or "")
    for value_kind, value in (
        ("scriptFullName", script_name),
        ("objectType", object_type),
    ):
        lowered = value.lower()
        terms = [term for term in ORDERED_SYSTEM_TYPE_TERMS if term in lowered]
        if terms:
            matches.append({
                "kind": value_kind,
                "value": value,
                "terms": terms,
            })
    for scalar in row.get("scalars") or []:
        if not isinstance(scalar, list) or len(scalar) != 3:
            raise AuditError("malformed object-index scalar")
        leaf = normalized_leaf(str(scalar[0]))
        if leaf in ORDERED_SYSTEM_FIELD_LEAVES:
            matches.append({
                "kind": "scalarField",
                "path": scalar[0],
                "value": scalar[2],
                "leaf": leaf,
            })
    for pptr in row.get("pptrs") or []:
        if not isinstance(pptr, dict):
            raise AuditError("malformed object-index PPtr")
        leaf = normalized_leaf(str(pptr.get("path") or ""))
        if leaf in ORDERED_SYSTEM_FIELD_LEAVES:
            matches.append({
                "kind": "pptrField",
                "path": pptr.get("path"),
                "pathId": pptr.get("pathId"),
                "leaf": leaf,
            })
    return matches


def scan_object_index_source(root: Path, source: str) -> dict[str, Any]:
    index_dir = root / source / "object_index"
    summary_path = index_dir / "summary.json"
    object_path = index_dir / "objects.jsonl.gz"
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"{source}: invalid object-index summary: {exc}") from exc
    if summary.get("complete") is not True or summary.get("errors"):
        raise AuditError(f"{source}: object index is not complete")
    outputs = summary.get("outputs") or {}
    expected_output = outputs.get("objects") or {}
    if sha256_path(object_path) != str(expected_output.get("sha256") or ""):
        raise AuditError(f"{source}: object-index output hash drifted")

    counts: Counter[str] = Counter()
    samples: list[dict[str, Any]] = []
    for row in iter_gzip_jsonl(object_path):
        record_type = str(row.get("recordType") or "")
        counts[f"{record_type}Rows"] += 1
        if record_type != "object":
            continue
        matches = ordered_system_matches(row)
        if not matches:
            continue
        counts["matchedObjects"] += 1
        if len(samples) < 100:
            samples.append({
                "object": row.get("object"),
                "name": row.get("name"),
                "type": row.get("type"),
                "script": row.get("script"),
                "decodeStatus": row.get("decodeStatus"),
                "matches": matches,
            })
    expected_counts = summary.get("counts") or {}
    if counts["objectRows"] != int(expected_counts.get("objects") or 0):
        raise AuditError(f"{source}: object row count does not match summary")
    if counts["monoScriptRows"] != int(expected_counts.get("monoScripts") or 0):
        raise AuditError(f"{source}: MonoScript row count does not match summary")
    counts.setdefault("matchedObjects", 0)
    return {
        "source": source,
        "summary": str(summary_path),
        "objects": str(object_path),
        "objectsSha256": expected_output.get("sha256"),
        "stageSignatureSha256": (
            (summary.get("stageSignature") or {}).get("sha256")
        ),
        "counts": dict(sorted(counts.items())),
        "matchSamples": samples,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    for path in (args.cli, args.hash_audit):
        if not path.is_file():
            raise FileNotFoundError(path)
    _, target_rows = load_hash_targets(args.hash_audit)
    patterns = build_patterns(target_rows)
    object_sources = [
        scan_object_index_source(
            args.object_index_root,
            "StreamingAssets" if source == "streaming" else "Persistent",
        )
        for source in args.source
    ]
    stream_sources = [
        scan_stream_source(args.cli, args.game_root, source, patterns)
        for source in args.source
    ]
    object_matches = sum(
        int((source["counts"] or {}).get("matchedObjects") or 0)
        for source in object_sources
    )
    exact_hits = sum(int(source["exactHitCount"]) for source in stream_sources)
    return {
        "schemaVersion": 1,
        "scope": {
            "purpose": (
                "test the complete current Unity-object index and skipped "
                "world-streaming blocks for unresolved Story-root selectors "
                "or ordered Encounter/BattlerStage authoring carriers"
            ),
            "sources": list(args.source),
            "blockTypes": ["Streaming", "DynamicStreaming"],
            "targetRoots": sorted({
                str(row["target"]) for row in target_rows
            }),
            "registeredResourcePaths": len(target_rows),
        },
        "inputs": {
            "animeStudioCli": str(args.cli),
            "animeStudioCliSha256": sha256_path(args.cli),
            "gameRoot": str(args.game_root),
            "stringPathHashAudit": str(args.hash_audit),
            "stringPathHashAuditSha256": sha256_path(args.hash_audit),
            "objectIndexRoot": str(args.object_index_root),
        },
        "patternCensus": pattern_summary(patterns),
        "objectIndexCensus": {
            "typeTerms": list(ORDERED_SYSTEM_TYPE_TERMS),
            "distinctiveFieldLeaves": sorted(ORDERED_SYSTEM_FIELD_LEAVES),
            "sources": object_sources,
            "matchedObjects": object_matches,
        },
        "worldStreamingCensus": {
            "sources": stream_sources,
            "exactHitCount": exact_hits,
        },
        "conclusion": {
            "classification": (
                "no_exact_current_selector_or_ordered_system_carrier"
                if not object_matches and not exact_hits
                else "candidate_requires_typed_review"
            ),
            "missionGraphAction": "none",
            "ownerRecovered": False,
            "reason": (
                "The complete current Unity-object indexes contain no typed "
                "Encounter/BattlerStage authoring object or distinctive nested "
                "field, and the skipped current world-streaming corpora contain "
                "no exact unresolved root, registered resource path, or "
                "StringPathHash representation."
                if not object_matches and not exact_hits
                else "At least one exact candidate requires typed review."
            ),
        },
        "boundary": (
            "This closes exact current client-side selectors in the audited "
            "Unity-object and world-streaming surfaces. It does not rule out "
            "compressed or transformed identities inside an unknown nested "
            "format, indirect runtime construction, server-provided state, or "
            "future build data. No file co-location or system capability may "
            "be promoted into mission ownership or chronology."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    scope = report["scope"]
    patterns = report["patternCensus"]
    objects = report["objectIndexCensus"]
    world = report["worldStreamingCensus"]
    lines = [
        "# World-streaming Story selector audit",
        "",
        "## Scope",
        "",
        (
            f"- target roots: {len(scope['targetRoots']):,}; registered resource "
            f"paths: {scope['registeredResourcePaths']:,}"
        ),
        (
            f"- exact byte patterns: {patterns['uniqueBytePatterns']:,} "
            f"({patterns['patternIdentities']:,} identities)"
        ),
        "- VFS blocks: `Streaming`, `DynamicStreaming`",
        "",
        "The byte patterns cover each root and registered resource path as "
        "UTF-8/ASCII and UTF-16LE, plus both byte orders of every registered "
        "64-bit StringPathHash value.",
        "",
        "## Complete Unity-object indexes",
        "",
    ]
    for source in objects["sources"]:
        counts = source["counts"]
        lines.append(
            f"- `{source['source']}`: {counts.get('objectRows', 0):,} objects / "
            f"{counts.get('monoScriptRows', 0):,} MonoScripts / "
            f"{counts.get('matchedObjects', 0):,} ordered-system matches"
        )
    lines.extend([
        "",
        "The match requires a resolved script/type name containing "
        "`Encounter`, `BattlerStage`, or `BossBattlerData`, or an exact "
        "distinctive serialized leaf such as `operaSegments`, "
        "`stageDataList`, or `completeDelayMode`.",
        "",
        "## Skipped world-streaming bytes",
        "",
    ])
    for source in world["sources"]:
        counts = source["counts"]
        lines.append(
            f"- `{source['source']}`: {counts.get('files', 0):,} files / "
            f"{counts.get('bytes', 0):,} bytes / "
            f"{source['exactHitCount']:,} exact hits / "
            f"SHA-256 `{source['corpusSha256']}`"
        )
    lines.extend([
        "",
        "## Conclusion",
        "",
        report["conclusion"]["reason"],
        "",
        report["boundary"],
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    parser.add_argument("--hash-audit", type=Path, default=DEFAULT_HASH_AUDIT)
    parser.add_argument(
        "--object-index-root",
        type=Path,
        default=DEFAULT_OBJECT_INDEX_ROOT,
    )
    parser.add_argument(
        "--source",
        action="append",
        choices=DEFAULT_SOURCES,
        default=None,
        help="Source to scan; may be repeated. Defaults to both.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    args.source = tuple(args.source) if args.source else DEFAULT_SOURCES
    return args


def main() -> int:
    args = parse_args()
    report = build_report(args)
    write_report_json(args.output, report)
    write_text_if_changed(args.markdown, render_markdown(report))
    print(
        "World-streaming Story selector audit: "
        f"{report['worldStreamingCensus']['exactHitCount']} exact byte hits / "
        f"{report['objectIndexCensus']['matchedObjects']} ordered-system objects"
    )
    print(f"wrote JSON: {args.output}")
    print(f"wrote Markdown: {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

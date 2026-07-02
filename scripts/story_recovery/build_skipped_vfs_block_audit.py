#!/usr/bin/env python3
r"""Summarize VFS block families skipped by the normal WebUI export.

The production WebUI export intentionally avoids broad Lua, world-streaming,
extend-data, manifest, and patch dumps. This script consumes a VFS index JSON
from AnimeStudio.CLI or fluffy-dumper and turns it into a compact recovery
report so candidate blocks can be prioritized without dumping gigabytes first.

Example index command:

    .\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe ^
      vfs-index --streaming-assets "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" ^
      --output tmp\skipped_vfs_index.json ^
      --block-type lua --block-type extend-data --block-type streaming ^
      --block-type dynamic-streaming --block-type bundle-manifest

Output:

    reports/mission_order/skipped_vfs_block_audit.json
    reports/mission_order/skipped_vfs_block_audit.md
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

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from common import ROOT, md_escape, write_report_json, write_text_if_changed  # noqa: E402

REPORT_DIR = ROOT / "reports" / "mission_order"
DEFAULT_JSON = REPORT_DIR / "skipped_vfs_block_audit.json"
DEFAULT_MD = REPORT_DIR / "skipped_vfs_block_audit.md"

SIGNAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("dialog", re.compile(r"dialog|dlg", re.IGNORECASE)),
    ("sns", re.compile(r"sns|chat|friend", re.IGNORECASE)),
    ("remoteComm", re.compile(r"remote[_-]?comm|remotecomm", re.IGNORECASE)),
    ("mission", re.compile(r"mission|quest|task", re.IGNORECASE)),
    ("story", re.compile(r"story|narrative|cutscene", re.IGNORECASE)),
    ("level", re.compile(r"level|map|scene|dung|indie", re.IGNORECASE)),
    ("ui", re.compile(r"ui/|panel|widget|hud", re.IGNORECASE)),
    ("actor", re.compile(r"actor|avatar|char|npc", re.IGNORECASE)),
    ("item", re.compile(r"item|equip|weapon|shop", re.IGNORECASE)),
    ("factory", re.compile(r"factory|facbuild|spaceship", re.IGNORECASE)),
)

CANDIDATE_NOTES = {
    "Lua": (
        "High value. Small encrypted script block; AnimeStudio dump decrypts it "
        "to Lua source. Prioritize UI/SNS/Dialog/RemoteComm modules."
    ),
    "ExtendData": (
        "High value. Contains global binary lookup data such as StringPathHash "
        "and CompressData; useful for resolving hashed paths/references."
    ),
    "BundleManifest": (
        "Medium value. Manifest data can improve asset dependency and bundle "
        "name recovery."
    ),
    "Streaming": (
        "Targeted value. Mostly scene/world chunk bytes; use file-regex for "
        "StreamingChunkInfo or specific map roots before dumping."
    ),
    "DynamicStreaming": (
        "Targeted value. Scene dynamic bytes; prioritize small metadata-like "
        "files and known map roots."
    ),
    "IFixPatchOut": "Unknown/low until files are present in the index.",
    "AuditStreaming": "Unknown/low until files are present in the index.",
    "AuditDynamicStreaming": "Unknown/low until files are present in the index.",
    "AuditIV": "Unknown/low until files are present in the index.",
}


def repo_rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path).replace("\\", "/")


def load_index(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise SystemExit(f"failed to read index: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON index: {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        raise SystemExit(f"unsupported VFS index shape: {path}")
    return data


def safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def file_block(row: dict[str, Any]) -> str:
    return str(
        row.get("blockName")
        or row.get("fileBlockType")
        or row.get("blockType")
        or "[unknown]"
    )


def file_name(row: dict[str, Any]) -> str:
    return str(row.get("fileName") or row.get("name") or "")


def file_length(row: dict[str, Any]) -> int:
    return safe_int(row.get("length") or row.get("size") or row.get("byteLength"))


def file_extension(name: str) -> str:
    return Path(name).suffix.lower() or "[no extension]"


def directory_key(name: str, depth: int) -> str:
    parts = [part for part in name.replace("\\", "/").split("/") if part]
    if len(parts) <= 1:
        return name or "[no path]"
    return "/".join(parts[: min(depth, len(parts) - 1)])


def percentile(sorted_values: list[int], pct: float) -> int:
    if not sorted_values:
        return 0
    index = round((len(sorted_values) - 1) * pct)
    return sorted_values[index]


def top_counter(counter: Counter[str], limit: int) -> list[dict[str, Any]]:
    return [
        {"value": value, "count": count}
        for value, count in counter.most_common(limit)
    ]


def signal_hits(name: str) -> list[str]:
    return [label for label, pattern in SIGNAL_PATTERNS if pattern.search(name)]


def summarize_files(files: list[dict[str, Any]], *, directory_depth: int, limit: int) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in files:
        if isinstance(row, dict):
            groups[file_block(row)].append(row)

    summaries: list[dict[str, Any]] = []
    for block in sorted(groups):
        rows = groups[block]
        lengths = sorted(file_length(row) for row in rows)
        encrypted_counts: Counter[str] = Counter(
            "encrypted" if bool(row.get("encrypted")) else "plain" for row in rows
        )
        ext_counts: Counter[str] = Counter(file_extension(file_name(row)) for row in rows)
        dir_counts: Counter[str] = Counter(
            directory_key(file_name(row), directory_depth) for row in rows
        )
        signal_counts: Counter[str] = Counter()
        signal_samples: dict[str, list[str]] = {label: [] for label, _ in SIGNAL_PATTERNS}
        for row in rows:
            name = file_name(row)
            for label in signal_hits(name):
                signal_counts[label] += 1
                if len(signal_samples[label]) < limit:
                    signal_samples[label].append(name)

        largest = sorted(rows, key=file_length, reverse=True)[:limit]
        samples = sorted(rows, key=file_name)[:limit]
        summaries.append(
            {
                "block": block,
                "fileCount": len(rows),
                "byteCount": sum(lengths),
                "minBytes": lengths[0] if lengths else 0,
                "medianBytes": percentile(lengths, 0.5),
                "p95Bytes": percentile(lengths, 0.95),
                "maxBytes": lengths[-1] if lengths else 0,
                "encryption": dict(sorted(encrypted_counts.items())),
                "extensions": top_counter(ext_counts, limit),
                "topDirectories": top_counter(dir_counts, limit),
                "largestFiles": [
                    {
                        "name": file_name(row),
                        "length": file_length(row),
                        "encrypted": bool(row.get("encrypted")),
                    }
                    for row in largest
                ],
                "sampleFiles": [
                    {
                        "name": file_name(row),
                        "length": file_length(row),
                        "encrypted": bool(row.get("encrypted")),
                    }
                    for row in samples
                ],
                "signalCounts": dict(sorted(signal_counts.items())),
                "signalSamples": {
                    label: values
                    for label, values in signal_samples.items()
                    if values
                },
                "candidateNote": CANDIDATE_NOTES.get(block, ""),
            }
        )
    return {"blocks": summaries}


def block_order_key(block: dict[str, Any]) -> tuple[int, str]:
    note = str(block.get("candidateNote") or "")
    if note.startswith("High"):
        rank = 0
    elif note.startswith("Medium"):
        rank = 1
    elif note.startswith("Targeted"):
        rank = 2
    else:
        rank = 3
    return rank, str(block.get("block") or "")


def render_counter(values: list[dict[str, Any]]) -> str:
    if not values:
        return ""
    return ", ".join(f"{item['value']} ({item['count']})" for item in values)


def render_markdown(payload: dict[str, Any]) -> str:
    index = payload["index"]
    summary = payload["summary"]
    lines: list[str] = []
    lines.append("# Skipped VFS Block Audit")
    lines.append("")
    lines.append(f"- Generated: `{payload['generatedAt']}`")
    lines.append(f"- Index: `{md_escape(index['path'])}`")
    if index.get("streamingAssets"):
        lines.append(f"- Streaming assets: `{md_escape(index['streamingAssets'])}`")
    if index.get("blockFilter"):
        lines.append(f"- Block filter: `{md_escape(index['blockFilter'])}`")
    lines.append(f"- Files: `{summary['fileCount']}`")
    lines.append(f"- Bytes: `{summary['byteCount']}`")
    lines.append(f"- Chunks: `{summary.get('chunkCount', 0)}`")
    lines.append("")

    lines.append("## Candidate Priority")
    lines.append("")
    for block in sorted(payload["blocks"], key=block_order_key):
        note = block.get("candidateNote")
        if not note:
            continue
        lines.append(
            f"- `{md_escape(block['block'])}`: {md_escape(note)} "
            f"({block['fileCount']} files, {block['byteCount']} bytes)"
        )
    lines.append("")

    lines.append("## Block Summary")
    lines.append("")
    lines.append(
        "| Block | Files | Bytes | Median | P95 | Max | Encryption | Top Extensions | Signals |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---|---|---|")
    for block in payload["blocks"]:
        signals = ", ".join(
            f"{key}:{value}" for key, value in sorted(block["signalCounts"].items())
        )
        lines.append(
            "| "
            f"`{md_escape(block['block'])}` | "
            f"{block['fileCount']} | "
            f"{block['byteCount']} | "
            f"{block['medianBytes']} | "
            f"{block['p95Bytes']} | "
            f"{block['maxBytes']} | "
            f"{md_escape(block['encryption'])} | "
            f"{md_escape(render_counter(block['extensions']))} | "
            f"{md_escape(signals)} |"
        )
    lines.append("")

    for block in payload["blocks"]:
        lines.append(f"## {block['block']}")
        lines.append("")
        lines.append("Top directories:")
        for item in block["topDirectories"]:
            lines.append(f"- `{md_escape(item['value'])}`: {item['count']}")
        lines.append("")
        lines.append("Largest files:")
        for item in block["largestFiles"]:
            lines.append(f"- `{md_escape(item['name'])}`: {item['length']} bytes")
        if block["signalSamples"]:
            lines.append("")
            lines.append("Signal samples:")
            for label, names in sorted(block["signalSamples"].items()):
                sample = ", ".join(f"`{md_escape(name)}`" for name in names[:5])
                lines.append(f"- `{label}`: {sample}")
        lines.append("")

    missing = index.get("missingBlocks") or []
    if missing:
        lines.append("## Missing Blocks")
        lines.append("")
        for item in missing:
            lines.append(f"- `{md_escape(item)}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_payload(index_path: Path, data: dict[str, Any], *, directory_depth: int, limit: int) -> dict[str, Any]:
    files = [row for row in data.get("files", []) if isinstance(row, dict)]
    summarized = summarize_files(files, directory_depth=directory_depth, limit=limit)
    raw_summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "index": {
            "path": repo_rel(index_path),
            "schemaVersion": data.get("schemaVersion"),
            "streamingAssets": data.get("streamingAssets"),
            "fallbackAssets": data.get("fallbackAssets"),
            "blockFilter": data.get("blockFilter"),
            "generatedAtEpoch": data.get("generatedAtEpoch"),
            "missingBlocks": data.get("missingBlocks") or [],
        },
        "summary": {
            "fileCount": raw_summary.get("fileCount", len(files)),
            "byteCount": raw_summary.get("byteCount", sum(file_length(row) for row in files)),
            "blockCount": raw_summary.get("blockCount", len(summarized["blocks"])),
            "chunkCount": raw_summary.get("chunkCount", 0),
            "missingBlockCount": raw_summary.get("missingBlockCount", 0),
            "missingChunkCount": raw_summary.get("missingChunkCount", 0),
        },
        "blocks": summarized["blocks"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--index",
        required=True,
        type=Path,
        help="Path to a vfs-index JSON produced by AnimeStudio.CLI or fluffy-dumper.",
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--directory-depth", type=int, default=4)
    parser.add_argument("--limit", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = load_index(args.index)
    payload = build_payload(
        args.index,
        data,
        directory_depth=max(1, args.directory_depth),
        limit=max(1, args.limit),
    )
    write_report_json(args.output_json, payload)
    write_text_if_changed(args.output_md, render_markdown(payload))
    print(f"Skipped VFS audit: {args.output_json}")
    print(f"Skipped VFS report: {args.output_md}")
    print(
        "blocks={blocks} files={files} bytes={bytes}".format(
            blocks=payload["summary"]["blockCount"],
            files=payload["summary"]["fileCount"],
            bytes=payload["summary"]["byteCount"],
        )
    )


if __name__ == "__main__":
    main()

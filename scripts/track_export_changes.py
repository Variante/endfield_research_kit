from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import datetime as dt
import difflib
import hashlib
import heapq
import json
import os
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Iterable


TEXT_EXTENSIONS = {
    ".bat",
    ".cfg",
    ".conf",
    ".csv",
    ".ini",
    ".json",
    ".lua",
    ".md",
    ".rs",
    ".sql",
    ".toml",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}

READ_CHUNK_SIZE = 1024 * 1024
PROGRESS_EVERY_FILES = 5000
TEXT_DIFF_MAX_BYTES = 256 * 1024
TEXT_DIFF_MAX_LINES = 240


@dataclasses.dataclass(slots=True)
class SnapshotRow:
    path: str
    size: int
    mtime_ns: int
    digest: str
    line_count: int | None
    extension: str
    text_content: str | None = None


@dataclasses.dataclass(slots=True)
class PendingFile:
    rel_path: str
    full_path: str
    size: int
    mtime_ns: int
    extension: str
    count_lines: bool
    capture_text: bool
    old_size: int | None
    old_digest: str | None
    old_line_count: int | None
    old_text_content: str | None


@dataclasses.dataclass(slots=True)
class ScannedFile:
    rel_path: str
    size: int
    mtime_ns: int
    extension: str
    digest: str
    line_count: int | None
    text_content: str | None
    old_size: int | None
    old_digest: str | None
    old_line_count: int | None
    old_text_content: str | None


@dataclasses.dataclass(slots=True)
class ChangeEntry:
    path: str
    extension: str
    old_size: int | None = None
    new_size: int | None = None
    old_digest: str | None = None
    new_digest: str | None = None
    old_line_count: int | None = None
    new_line_count: int | None = None
    text_diff: list[str] | None = None
    text_diff_truncated: bool = False

    def to_dict(self) -> dict[str, object]:
        payload = {
            "path": self.path,
            "extension": self.extension,
            "old_size": self.old_size,
            "new_size": self.new_size,
            "old_digest": self.old_digest,
            "new_digest": self.new_digest,
            "old_line_count": self.old_line_count,
            "new_line_count": self.new_line_count,
        }
        if self.old_size is not None and self.new_size is not None:
            payload["size_delta"] = self.new_size - self.old_size
        if self.old_line_count is not None and self.new_line_count is not None:
            payload["line_delta"] = self.new_line_count - self.old_line_count
        if self.text_diff:
            payload["text_diff"] = self.text_diff
            if self.text_diff_truncated:
                payload["text_diff_truncated"] = True
        return payload


class ChangeAccumulator:
    def __init__(self, sample_limit: int, top_line_limit: int) -> None:
        self.sample_limit = sample_limit
        self.top_line_limit = top_line_limit

        self.scanned_files = 0
        self.reused_metadata_matches = 0
        self.metadata_only_updates = 0

        self.added_count = 0
        self.modified_count = 0
        self.deleted_count = 0

        self.added_by_extension: Counter[str] = Counter()
        self.modified_by_extension: Counter[str] = Counter()
        self.deleted_by_extension: Counter[str] = Counter()

        self.added_examples: list[ChangeEntry] = []
        self.modified_examples: list[ChangeEntry] = []
        self.deleted_examples: list[ChangeEntry] = []

        self._largest_line_changes: list[tuple[int, int, ChangeEntry]] = []
        self._line_order = 0

    def _remember_sample(self, bucket: list[ChangeEntry], entry: ChangeEntry) -> None:
        if len(bucket) < self.sample_limit:
            bucket.append(entry)

    def _remember_line_change(self, entry: ChangeEntry) -> None:
        if entry.old_line_count is None or entry.new_line_count is None:
            return
        magnitude = abs(entry.new_line_count - entry.old_line_count)
        if magnitude == 0:
            return
        token = (magnitude, self._line_order, entry)
        self._line_order += 1
        if len(self._largest_line_changes) < self.top_line_limit:
            heapq.heappush(self._largest_line_changes, token)
            return
        if token > self._largest_line_changes[0]:
            heapq.heapreplace(self._largest_line_changes, token)

    def note_scan(self) -> None:
        self.scanned_files += 1

    def note_reused_metadata_match(self) -> None:
        self.reused_metadata_matches += 1

    def note_metadata_only_update(self) -> None:
        self.metadata_only_updates += 1

    def record_added(self, scanned: ScannedFile) -> None:
        self.added_count += 1
        self.added_by_extension[display_extension(scanned.extension)] += 1
        text_diff, text_diff_truncated = build_text_diff(
            "",
            scanned.text_content,
            fromfile=f"a/{scanned.rel_path}",
            tofile=f"b/{scanned.rel_path}",
        )
        self._remember_sample(
            self.added_examples,
            ChangeEntry(
                path=scanned.rel_path,
                extension=scanned.extension,
                new_size=scanned.size,
                new_line_count=scanned.line_count,
                text_diff=text_diff,
                text_diff_truncated=text_diff_truncated,
            ),
        )

    def record_modified(self, scanned: ScannedFile) -> None:
        self.modified_count += 1
        self.modified_by_extension[display_extension(scanned.extension)] += 1
        text_diff, text_diff_truncated = build_text_diff(
            scanned.old_text_content,
            scanned.text_content,
            fromfile=f"a/{scanned.rel_path}",
            tofile=f"b/{scanned.rel_path}",
        )
        entry = ChangeEntry(
            path=scanned.rel_path,
            extension=scanned.extension,
            old_size=scanned.old_size,
            new_size=scanned.size,
            old_line_count=scanned.old_line_count,
            new_line_count=scanned.line_count,
            text_diff=text_diff,
            text_diff_truncated=text_diff_truncated,
        )
        self._remember_sample(self.modified_examples, entry)
        self._remember_line_change(entry)

    def record_deleted(
        self,
        rel_path: str,
        extension: str,
        old_size: int,
        old_line_count: int | None,
        old_text_content: str | None = None,
    ) -> None:
        self.deleted_count += 1
        self.deleted_by_extension[display_extension(extension)] += 1
        text_diff, text_diff_truncated = build_text_diff(
            old_text_content,
            "",
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
        )
        self._remember_sample(
            self.deleted_examples,
            ChangeEntry(
                path=rel_path,
                extension=extension,
                old_size=old_size,
                old_line_count=old_line_count,
                text_diff=text_diff,
                text_diff_truncated=text_diff_truncated,
            ),
        )

    def top_line_changes(self) -> list[ChangeEntry]:
        ordered = sorted(self._largest_line_changes, key=lambda item: (-item[0], item[1]))
        return [entry for _, _, entry in ordered]

    def to_dict(self, started_at: dt.datetime, finished_at: dt.datetime) -> dict[str, object]:
        return {
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
            "scanned_files": self.scanned_files,
            "changes": {
                "added": self.added_count,
                "modified": self.modified_count,
                "deleted": self.deleted_count,
                "metadata_only_updates": self.metadata_only_updates,
                "reused_metadata_matches": self.reused_metadata_matches,
            },
            "breakdown": {
                "added_by_extension": dict(self.added_by_extension.most_common()),
                "modified_by_extension": dict(self.modified_by_extension.most_common()),
                "deleted_by_extension": dict(self.deleted_by_extension.most_common()),
            },
            "samples": {
                "added": [entry.to_dict() for entry in self.added_examples],
                "modified": [entry.to_dict() for entry in self.modified_examples],
                "deleted": [entry.to_dict() for entry in self.deleted_examples],
                "largest_line_changes": [entry.to_dict() for entry in self.top_line_changes()],
            },
        }


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    exported_root = repo_root / "exported"
    log_dir = repo_root / "diff-log"
    state_dir = repo_root / ".export-tracker"

    parser = argparse.ArgumentParser(
        description="Track export diffs between runs and write a summary.",
    )
    parser.add_argument("--root", type=Path, default=exported_root, help="Export root to scan.")
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=state_dir,
        help="Directory for tracker state and history files.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=log_dir,
        help="Directory where dated summary logs are written.",
    )
    parser.add_argument(
        "--summary-prefix",
        default="export-change-summary",
        help="Filename prefix used for dated summary logs.",
    )
    parser.add_argument(
        "--timestamp-format",
        default="%Y%m%d-%H%M%S",
        help="strftime format used in dated summary filenames.",
    )
    parser.add_argument(
        "--summary-md",
        type=Path,
        default=None,
        help="Optional explicit path for the Markdown summary file.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=None,
        help="Optional explicit path for the JSON summary file.",
    )
    parser.add_argument(
        "--history-dir",
        type=Path,
        default=None,
        help="Optional directory for an additional timestamped copy of each report.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(2, min(8, (os.cpu_count() or 4))),
        help="Worker threads used for hashing files whose metadata changed.",
    )
    parser.add_argument(
        "--hash-batch-size",
        type=int,
        default=1024,
        help="How many changed files to hash per batch.",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=200,
        help="How many changed files per category to keep in the JSON summary.",
    )
    parser.add_argument(
        "--top-line-limit",
        type=int,
        default=25,
        help="How many text file line-delta entries to keep.",
    )
    parser.add_argument(
        "--ignore-relative-path",
        action="append",
        default=[],
        help="Relative path under the export root to exclude from tracking.",
    )
    parser.add_argument(
        "--include-relative-path",
        action="append",
        default=[],
        help=(
            "Relative file or directory under the export root to scan. May be "
            "repeated; when omitted, the whole root is scanned."
        ),
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Do not write timestamped history files.",
    )
    return parser.parse_args()


def display_extension(extension: str) -> str:
    return extension or "[no extension]"


def normalize_relative_path(path: str) -> str:
    return path.replace("\\", "/")


def normalize_cli_relative_path(path: str) -> str:
    return normalize_relative_path(path.strip().strip("/"))


def try_relative_to(path: Path, root: Path) -> str | None:
    try:
        return normalize_relative_path(str(path.resolve().relative_to(root.resolve())))
    except ValueError:
        return None


def is_text_extension(extension: str) -> bool:
    return extension.lower() in TEXT_EXTENSIONS


def build_text_diff(
    old_text: str | None,
    new_text: str | None,
    *,
    fromfile: str = "previous",
    tofile: str = "current",
) -> tuple[list[str] | None, bool]:
    if old_text is None or new_text is None:
        return None, False
    diff = list(
        difflib.unified_diff(
            old_text.splitlines(),
            new_text.splitlines(),
            fromfile=fromfile,
            tofile=tofile,
            lineterm="",
            n=3,
        )
    )
    if len(diff) > TEXT_DIFF_MAX_LINES:
        return diff[:TEXT_DIFF_MAX_LINES], True
    return diff or None, False


def scan_file(path: str, count_lines: bool, capture_text: bool) -> tuple[str, int | None, str | None]:
    digest = hashlib.blake2b(digest_size=16)
    line_count = 0
    last_byte: bytes | None = None
    text_chunks: list[bytes] | None = [] if capture_text else None
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(READ_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
            if text_chunks is not None:
                text_chunks.append(chunk)
            if count_lines:
                line_count += chunk.count(b"\n")
                last_byte = chunk[-1:]
    if count_lines and last_byte is not None and last_byte != b"\n":
        line_count += 1
    text_content = None
    if text_chunks is not None:
        text_content = b"".join(text_chunks).decode("utf-8-sig", errors="replace")
    return digest.hexdigest(), (line_count if count_lines else None), text_content


def should_ignore_path(rel_path: str, ignored_exact_paths: set[str], ignored_dir_prefixes: tuple[str, ...]) -> bool:
    if rel_path in ignored_exact_paths:
        return True
    return any(rel_path.startswith(prefix) for prefix in ignored_dir_prefixes)


def build_include_roots(root: Path, include_relative_paths: Iterable[str]) -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()
    root_resolved = root.resolve()
    for raw_path in include_relative_paths:
        rel_path = normalize_cli_relative_path(str(raw_path or ""))
        candidate = root if not rel_path or rel_path == "." else root / rel_path
        try:
            resolved = candidate.resolve()
            resolved.relative_to(root_resolved)
        except ValueError:
            print(
                f"[track_export_changes] Ignoring include path outside root: {raw_path}",
                file=sys.stderr,
            )
            continue
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        roots.append(resolved)
    return roots or [root]


def file_scan_entry(root: Path, path: Path) -> tuple[str, str, int, int, str] | None:
    try:
        stat_result = path.stat()
    except FileNotFoundError:
        return None
    if not path.is_file():
        return None
    rel_path = normalize_relative_path(str(path.relative_to(root)))
    extension = path.suffix.lower()
    return rel_path, str(path), stat_result.st_size, stat_result.st_mtime_ns, extension


def iter_export_files(
    root: Path,
    ignored_exact_paths: set[str],
    ignored_dir_prefixes: tuple[str, ...],
    include_relative_paths: Iterable[str] = (),
) -> Iterable[tuple[str, str, int, int, str]]:
    yielded_paths: set[str] = set()
    stack = list(reversed(build_include_roots(root, include_relative_paths)))
    while stack:
        current = stack.pop()
        if current.is_file():
            scan_entry = file_scan_entry(root, current)
            if scan_entry is None:
                continue
            rel_path = scan_entry[0]
            if should_ignore_path(rel_path, ignored_exact_paths, ignored_dir_prefixes):
                continue
            if rel_path in yielded_paths:
                continue
            yielded_paths.add(rel_path)
            yield scan_entry
            continue
        try:
            with os.scandir(current) as entries:
                ordered_entries = sorted(entries, key=lambda entry: entry.name)
        except FileNotFoundError:
            continue
        for entry in reversed(ordered_entries):
            full_path = Path(entry.path)
            rel_path = normalize_relative_path(str(full_path.relative_to(root)))
            if entry.is_dir(follow_symlinks=False):
                if should_ignore_path(rel_path, ignored_exact_paths, ignored_dir_prefixes):
                    continue
                stack.append(full_path)
                continue
            if not entry.is_file(follow_symlinks=False):
                continue
            if should_ignore_path(rel_path, ignored_exact_paths, ignored_dir_prefixes):
                continue
            if rel_path in yielded_paths:
                continue
            yielded_paths.add(rel_path)
            stat_result = entry.stat(follow_symlinks=False)
            extension = full_path.suffix.lower()
            yield rel_path, str(full_path), stat_result.st_size, stat_result.st_mtime_ns, extension


def ensure_database_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            size INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            digest TEXT NOT NULL,
            line_count INTEGER,
            extension TEXT NOT NULL,
            text_content TEXT
        )
        """
    )
    columns = {row[1] for row in conn.execute("PRAGMA table_info(files)")}
    if "text_content" not in columns:
        conn.execute("ALTER TABLE files ADD COLUMN text_content TEXT")
    conn.commit()


def prepare_scan_table(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS files_scan")
    conn.execute(
        """
        CREATE TABLE files_scan (
            path TEXT PRIMARY KEY,
            size INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            digest TEXT NOT NULL,
            line_count INTEGER,
            extension TEXT NOT NULL,
            text_content TEXT
        )
        """
    )


def batch_insert_rows(conn: sqlite3.Connection, rows: list[SnapshotRow]) -> None:
    if not rows:
        return
    conn.executemany(
        """
        INSERT INTO files_scan (path, size, mtime_ns, digest, line_count, extension, text_content)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row.path,
                row.size,
                row.mtime_ns,
                row.digest,
                row.line_count,
                row.extension,
                row.text_content,
            )
            for row in rows
        ],
    )
    rows.clear()


def process_pending_batch(
    pending_batch: list[PendingFile],
    conn: sqlite3.Connection,
    accumulator: ChangeAccumulator,
    executor: concurrent.futures.Executor,
) -> None:
    if not pending_batch:
        return

    insert_rows: list[SnapshotRow] = []
    future_map = {
        executor.submit(scan_file, item.full_path, item.count_lines, item.capture_text): item
        for item in pending_batch
    }
    for future in concurrent.futures.as_completed(future_map):
        item = future_map[future]
        digest, line_count, text_content = future.result()
        scanned = ScannedFile(
            rel_path=item.rel_path,
            size=item.size,
            mtime_ns=item.mtime_ns,
            extension=item.extension,
            digest=digest,
            line_count=line_count,
            text_content=text_content,
            old_size=item.old_size,
            old_digest=item.old_digest,
            old_line_count=item.old_line_count,
            old_text_content=item.old_text_content,
        )
        insert_rows.append(
            SnapshotRow(
                path=item.rel_path,
                size=item.size,
                mtime_ns=item.mtime_ns,
                digest=digest,
                line_count=line_count,
                extension=item.extension,
                text_content=text_content,
            )
        )
        if item.old_digest is None:
            accumulator.record_added(scanned)
        elif item.old_digest != digest:
            accumulator.record_modified(scanned)
        else:
            accumulator.note_metadata_only_update()

    batch_insert_rows(conn, insert_rows)
    pending_batch.clear()


def read_old_row(select_cursor: sqlite3.Cursor, rel_path: str) -> tuple[int, int, str, int | None, str, str | None] | None:
    row = select_cursor.execute(
        "SELECT size, mtime_ns, digest, line_count, extension, text_content FROM files WHERE path = ?",
        (rel_path,),
    ).fetchone()
    if row is None:
        return None
    return (
        int(row[0]),
        int(row[1]),
        str(row[2]),
        (None if row[3] is None else int(row[3])),
        str(row[4]),
        None if row[5] is None else str(row[5]),
    )


def find_deleted_rows(conn: sqlite3.Connection) -> Iterable[tuple[str, int, str, int | None, str, str | None]]:
    return conn.execute(
        """
        SELECT files.path, files.size, files.digest, files.line_count, files.extension, files.text_content
        FROM files
        LEFT JOIN files_scan ON files.path = files_scan.path
        WHERE files_scan.path IS NULL
        ORDER BY files.path
        """
    )


def format_counter(counter: Counter[str], limit: int = 15) -> list[str]:
    lines = []
    for extension, count in counter.most_common(limit):
        lines.append(f"- `{extension}`: {count}")
    return lines


def format_change_entry(entry: ChangeEntry) -> str:
    bits = [f"`{entry.path}`"]
    if entry.old_size is not None and entry.new_size is not None:
        bits.append(f"size {entry.old_size} -> {entry.new_size}")
    elif entry.new_size is not None:
        bits.append(f"size {entry.new_size}")
    elif entry.old_size is not None:
        bits.append(f"size {entry.old_size}")
    if entry.old_line_count is not None and entry.new_line_count is not None:
        delta = entry.new_line_count - entry.old_line_count
        bits.append(f"lines {entry.old_line_count} -> {entry.new_line_count} ({delta:+d})")
    elif entry.new_line_count is not None:
        bits.append(f"lines {entry.new_line_count}")
    elif entry.old_line_count is not None:
        bits.append(f"lines {entry.old_line_count}")
    return ", ".join(bits)


def change_entry_from_dict(payload: dict[str, object]) -> ChangeEntry:
    return ChangeEntry(
        path=str(payload["path"]),
        extension=str(payload["extension"]),
        old_size=None if payload.get("old_size") is None else int(payload["old_size"]),
        new_size=None if payload.get("new_size") is None else int(payload["new_size"]),
        old_line_count=None
        if payload.get("old_line_count") is None
        else int(payload["old_line_count"]),
        new_line_count=None
        if payload.get("new_line_count") is None
        else int(payload["new_line_count"]),
        text_diff=list(payload.get("text_diff") or []) or None,
        text_diff_truncated=bool(payload.get("text_diff_truncated")),
    )


def build_report_paths(namespace: argparse.Namespace, finished_at: dt.datetime) -> tuple[Path, Path]:
    stamp = finished_at.strftime(namespace.timestamp_format)
    if namespace.summary_md is not None:
        summary_md_path = Path(namespace.summary_md)
    else:
        summary_md_path = Path(namespace.log_dir) / f"{namespace.summary_prefix}-{stamp}.md"
    if namespace.summary_json is not None:
        summary_json_path = Path(namespace.summary_json)
    else:
        summary_json_path = Path(namespace.log_dir) / f"{namespace.summary_prefix}-{stamp}.json"
    return summary_md_path, summary_json_path


def write_reports(
    payload: dict[str, object],
    summary_md_path: Path,
    summary_json_path: Path,
    history_dir: Path | None,
    write_history: bool,
) -> None:
    started_at = dt.datetime.fromisoformat(str(payload["started_at"]))
    finished_at = dt.datetime.fromisoformat(str(payload["finished_at"]))
    changes = payload["changes"]
    breakdown = payload["breakdown"]
    samples = payload["samples"]

    markdown_lines = [
        "# Export change summary",
        "",
        f"- Scan started: `{started_at.isoformat()}`",
        f"- Scan finished: `{finished_at.isoformat()}`",
        f"- Duration: `{payload['duration_seconds']}` seconds",
        f"- Files scanned: `{payload['scanned_files']}`",
        "",
        "## Totals",
        "",
        f"- Added: `{changes['added']}`",
        f"- Modified: `{changes['modified']}`",
        f"- Deleted: `{changes['deleted']}`",
        f"- Metadata-only updates: `{changes['metadata_only_updates']}`",
        f"- Exact metadata matches reused from cache: `{changes['reused_metadata_matches']}`",
        "",
        "## Added by extension",
        "",
    ]
    markdown_lines.extend(format_counter(Counter(breakdown["added_by_extension"])))
    markdown_lines.extend(
        [
            "",
            "## Modified by extension",
            "",
        ]
    )
    markdown_lines.extend(format_counter(Counter(breakdown["modified_by_extension"])))
    markdown_lines.extend(
        [
            "",
            "## Deleted by extension",
            "",
        ]
    )
    markdown_lines.extend(format_counter(Counter(breakdown["deleted_by_extension"])))

    if samples["largest_line_changes"]:
        markdown_lines.extend(
            [
                "",
                "## Biggest text line deltas",
                "",
            ]
        )
        markdown_lines.extend(
            f"- {format_change_entry(change_entry_from_dict(entry))}"
            for entry in samples["largest_line_changes"]
        )

    for title, key in (
        ("Added samples", "added"),
        ("Modified samples", "modified"),
        ("Deleted samples", "deleted"),
    ):
        entries = samples[key]
        if not entries:
            continue
        markdown_lines.extend(["", f"## {title}", ""])
        markdown_lines.extend(
            f"- {format_change_entry(change_entry_from_dict(entry))}" for entry in entries[:25]
        )
        if len(entries) > 25:
            markdown_lines.append(f"- ... {len(entries) - 25} more captured in the JSON summary")

    markdown = "\n".join(markdown_lines) + "\n"

    summary_md_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_md_path.write_text(markdown, encoding="utf-8")
    summary_json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if not write_history or history_dir is None:
        return

    history_dir.mkdir(parents=True, exist_ok=True)
    stamp = finished_at.strftime("%Y%m%d-%H%M%S")
    history_md = history_dir / f"export-change-summary-{stamp}.md"
    history_json = history_dir / f"export-change-summary-{stamp}.json"
    history_md.write_text(markdown, encoding="utf-8")
    history_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def print_progress(prefix: str, processed: int, started_at: float) -> None:
    elapsed = max(time.monotonic() - started_at, 0.001)
    rate = processed / elapsed
    print(f"[track_export_changes] {prefix}: {processed} files ({rate:.1f}/s)")


def build_ignore_rules(namespace: argparse.Namespace, root: Path) -> tuple[set[str], tuple[str, ...]]:
    ignored_exact_paths: set[str] = set()
    ignored_dir_prefixes: set[str] = set()

    paths_to_check = [namespace.state_dir]
    if namespace.summary_md is not None:
        paths_to_check.append(namespace.summary_md)
    if namespace.summary_json is not None:
        paths_to_check.append(namespace.summary_json)
    if namespace.history_dir is not None:
        paths_to_check.append(namespace.history_dir)

    for path in paths_to_check:
        rel_path = try_relative_to(Path(path), root)
        if rel_path is None or rel_path == ".":
            continue
        ignored_exact_paths.add(rel_path)
        ignored_dir_prefixes.add(f"{rel_path}/")

    for raw_path in namespace.ignore_relative_path:
        rel_path = normalize_cli_relative_path(raw_path)
        if not rel_path:
            continue
        ignored_exact_paths.add(rel_path)
        ignored_dir_prefixes.add(f"{rel_path}/")

    return ignored_exact_paths, tuple(sorted(ignored_dir_prefixes))


def main() -> int:
    namespace = parse_args()

    root = namespace.root.resolve()
    if not root.exists():
        print(f"[track_export_changes] Export root does not exist: {root}", file=sys.stderr)
        return 1
    if not root.is_dir():
        print(f"[track_export_changes] Export root is not a directory: {root}", file=sys.stderr)
        return 1

    ignored_exact_paths, ignored_dir_prefixes = build_ignore_rules(namespace, root)

    namespace.state_dir.mkdir(parents=True, exist_ok=True)
    db_path = namespace.state_dir / "state.sqlite3"

    started_at = dt.datetime.now(dt.timezone.utc).astimezone()
    monotonic_start = time.monotonic()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")
    ensure_database_schema(conn)
    prepare_scan_table(conn)

    accumulator = ChangeAccumulator(
        sample_limit=namespace.sample_limit,
        top_line_limit=namespace.top_line_limit,
    )

    select_cursor = conn.cursor()
    unchanged_rows: list[SnapshotRow] = []
    pending_batch: list[PendingFile] = []

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=namespace.workers) as executor:
            with conn:
                for rel_path, full_path, size, mtime_ns, extension in iter_export_files(
                    root,
                    ignored_exact_paths,
                    ignored_dir_prefixes,
                    namespace.include_relative_path,
                ):
                    accumulator.note_scan()
                    old_row = read_old_row(select_cursor, rel_path)
                    if old_row is not None:
                        old_size, old_mtime_ns, old_digest, old_line_count, old_extension, old_text_content = old_row
                        should_capture_text = is_text_extension(extension) and size <= TEXT_DIFF_MAX_BYTES
                        has_cached_text = not should_capture_text or old_text_content is not None
                        if size == old_size and mtime_ns == old_mtime_ns and has_cached_text:
                            accumulator.note_reused_metadata_match()
                            unchanged_rows.append(
                                SnapshotRow(
                                    path=rel_path,
                                    size=size,
                                    mtime_ns=mtime_ns,
                                    digest=old_digest,
                                    line_count=old_line_count,
                                    extension=old_extension,
                                    text_content=old_text_content,
                                )
                            )
                            if len(unchanged_rows) >= namespace.hash_batch_size:
                                batch_insert_rows(conn, unchanged_rows)
                            if accumulator.scanned_files % PROGRESS_EVERY_FILES == 0:
                                print_progress("scanned", accumulator.scanned_files, monotonic_start)
                            continue
                    else:
                        old_size = None
                        old_digest = None
                        old_line_count = None
                        old_text_content = None

                    is_text = is_text_extension(extension)
                    pending_batch.append(
                        PendingFile(
                            rel_path=rel_path,
                            full_path=full_path,
                            size=size,
                            mtime_ns=mtime_ns,
                            extension=extension,
                            count_lines=is_text,
                            capture_text=is_text and size <= TEXT_DIFF_MAX_BYTES,
                            old_size=old_size,
                            old_digest=old_digest,
                            old_line_count=old_line_count,
                            old_text_content=old_text_content,
                        )
                    )
                    if len(pending_batch) >= namespace.hash_batch_size:
                        process_pending_batch(pending_batch, conn, accumulator, executor)
                    if accumulator.scanned_files % PROGRESS_EVERY_FILES == 0:
                        print_progress("scanned", accumulator.scanned_files, monotonic_start)

                batch_insert_rows(conn, unchanged_rows)
                process_pending_batch(pending_batch, conn, accumulator, executor)

                for rel_path, old_size, old_digest, old_line_count, extension, old_text_content in find_deleted_rows(conn):
                    accumulator.record_deleted(
                        rel_path,
                        extension,
                        int(old_size),
                        None if old_line_count is None else int(old_line_count),
                        old_text_content,
                    )

                conn.execute("DROP TABLE files")
                conn.execute("ALTER TABLE files_scan RENAME TO files")
    finally:
        conn.close()

    finished_at = dt.datetime.now(dt.timezone.utc).astimezone()
    payload = accumulator.to_dict(started_at, finished_at)
    include_paths = [
        normalize_cli_relative_path(path)
        for path in namespace.include_relative_path
        if normalize_cli_relative_path(path)
    ]
    if include_paths:
        payload["scan_scope"] = {
            "mode": "include_relative_paths",
            "include_relative_paths": include_paths,
        }
    summary_md_path, summary_json_path = build_report_paths(namespace, finished_at)
    write_reports(
        payload=payload,
        summary_md_path=summary_md_path,
        summary_json_path=summary_json_path,
        history_dir=namespace.history_dir,
        write_history=not namespace.no_history and namespace.history_dir is not None,
    )

    print(
        "[track_export_changes] Done:"
        f" added={accumulator.added_count},"
        f" modified={accumulator.modified_count},"
        f" deleted={accumulator.deleted_count},"
        f" metadata_only={accumulator.metadata_only_updates},"
        f" scanned={accumulator.scanned_files}"
    )
    print(f"[track_export_changes] Summary: {summary_md_path}")
    print(f"[track_export_changes] JSON: {summary_json_path}")
    if not namespace.no_history and namespace.history_dir is not None:
        print(f"[track_export_changes] History directory: {namespace.history_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

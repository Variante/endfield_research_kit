"""Current-input SkillData corpus gate.

The authoritative outer VFS
ledger supplies identity and encrypted physical boundaries.  AnimeStudio
``stream --verify-md5`` supplies the decrypted logical bytes; every stream row
must join one-for-one to the current ledger before the MemoryPack framer runs.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from scripts.game_data.memorypack.skill import frame_skill_common_prefix, frame_skill_memorypack


SKILL_PREFIX = "Data/Json/SkillData/"
SKILL_PATTERN = re.compile(r"^Data/Json/SkillData/[^/]+[.]json$")
HEX64 = re.compile(r"^[0-9A-F]{64}$")
MODULE_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTER = MODULE_REPO_ROOT / "reports/animestudio/vfs_understanding_latest.json"
DEFAULT_LEDGER = MODULE_REPO_ROOT / "reports/animestudio/vfs_understanding_files_latest.jsonl.gz"
DEFAULT_CLI = (
    MODULE_REPO_ROOT
    / "tools/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/AnimeStudio.CLI.exe"
)


class CensusGateError(ValueError):
    def __init__(
        self,
        code: str,
        *,
        source: str,
        expected: Any = None,
        actual: Any = None,
        offset: Any = None,
    ) -> None:
        self.diagnostic = {
            "code": code,
            "source": source,
            "offset": offset,
            "expected": expected,
            "actual": actual,
        }
        super().__init__(json.dumps(self.diagnostic, ensure_ascii=False, sort_keys=True))


def _fail(code: str, *, source: str, expected: Any = None, actual: Any = None, offset: Any = None) -> None:
    raise CensusGateError(code, source=source, expected=expected, actual=actual, offset=offset)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _fingerprint(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        _fail("missing-file", source=str(resolved), expected="regular file", actual="missing")
    return {"path": resolved.as_posix(), "length": resolved.stat().st_size, "sha256": _sha256_file(resolved)}


def _chunk_fingerprints(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_path: dict[str, Path] = {}
    expected_md5: dict[str, str] = {}
    for row in rows:
        path = Path(str(row.get("physicalChunkPath") or "")).resolve()
        key = os.path.normcase(str(path))
        by_path[key] = path
        declared = str(row.get("fileChunkMd5LittleEndianHex") or "").upper()
        previous = expected_md5.setdefault(key, declared)
        if declared != previous:
            _fail("chunk-md5-ledger-conflict", source=str(path), expected=previous, actual=declared)
    result: list[dict[str, Any]] = []
    for key in sorted(by_path):
        path = by_path[key]
        raw = path.read_bytes()
        actual_md5 = hashlib.md5(raw).hexdigest().upper()
        result.append({
            "path": path.as_posix(),
            "length": len(raw),
            # The ledger field is a chunk-reference identity.  It is retained
            # separately and is not assumed to equal the raw content digest.
            "chunkReferenceMd5": expected_md5[key],
            "rawMd5": actual_md5,
            "sha256": hashlib.sha256(raw).hexdigest().upper(),
        })
    return result


def _chunk_selection_snapshot(rows: Iterable[Mapping[str, Any]], outer: Mapping[str, Any]) -> list[dict[str, Any]]:
    roots = {
        "primary": Path(str(outer.get("primaryAssets") or "")).resolve(),
        "fallback": Path(str(outer.get("fallbackAssets") or "")).resolve(),
    }
    result_by_identity: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        virtual_path = str(row.get("virtualPath") or "")
        hash_directory = str(row.get("hashDirectory") or "")
        chunk_file = str(row.get("chunkFile") or "")
        if not re.fullmatch(r"[0-9A-Fa-f]{8}", hash_directory):
            _fail("invalid-hash-directory", source=virtual_path, actual=hash_directory)
        if not re.fullmatch(r"[0-9A-Fa-f]{32}[.]chk", chunk_file):
            _fail("invalid-chunk-file", source=virtual_path, actual=chunk_file)
        identity = (hash_directory.upper(), chunk_file.upper())
        candidates = {
            role: (root / "VFS" / hash_directory / chunk_file).resolve()
            for role, root in roots.items()
        }
        selected_role = "primary" if candidates["primary"].is_file() else "fallback" if candidates["fallback"].is_file() else None
        if selected_role is None:
            _fail("selected-chunk-missing", source=virtual_path, expected="primary or fallback chunk", actual={role: str(path) for role, path in candidates.items()})
        actual_path = Path(str(row.get("physicalChunkPath") or "")).resolve()
        if os.path.normcase(str(actual_path)) != os.path.normcase(str(candidates[selected_role])):
            _fail("chunk-overlay-selection-mismatch", source=virtual_path, expected=str(candidates[selected_role]), actual=str(actual_path))
        if row.get("physicalChunkSource") != selected_role:
            _fail("chunk-source-mismatch", source=virtual_path, expected=selected_role, actual=row.get("physicalChunkSource"))
        if os.path.normcase(str(Path(str(row.get("physicalChunkRoot") or "")).resolve())) != os.path.normcase(str(roots[selected_role])):
            _fail("chunk-root-mismatch", source=virtual_path, expected=str(roots[selected_role]), actual=row.get("physicalChunkRoot"))
        snapshot = {
            "hashDirectory": identity[0],
            "chunkFile": identity[1],
            "primaryPath": candidates["primary"].as_posix(),
            "primaryExists": candidates["primary"].is_file(),
            "fallbackPath": candidates["fallback"].as_posix(),
            "fallbackExists": candidates["fallback"].is_file(),
            "selectedRole": selected_role,
            "selectedPath": candidates[selected_role].as_posix(),
        }
        previous = result_by_identity.setdefault(identity, snapshot)
        if previous != snapshot:
            _fail("chunk-selection-conflict", source=virtual_path, expected=previous, actual=snapshot)
    return [result_by_identity[key] for key in sorted(result_by_identity)]


def _require_int(value: Any, *, source: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _fail("invalid-integer", source=source, expected=f"int >= {minimum}", actual=value)
    return value


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def _snapshot_pinned_files(rows: list[Mapping[str, Any]], *, label: str) -> list[dict[str, Any]]:
    if not rows:
        _fail("missing-fingerprints", source=label, expected="non-empty list", actual=rows)
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        raw_path = row.get("path")
        expected_length = row.get("length")
        expected_sha = str(row.get("sha256") or "").upper()
        if not isinstance(raw_path, str) or not raw_path:
            _fail("missing-fingerprint-path", source=f"{label}[{index}]", actual=raw_path)
        path = Path(raw_path).resolve()
        key = os.path.normcase(str(path))
        if key in seen:
            _fail("duplicate-fingerprint-path", source=f"{label}[{index}]", actual=str(path))
        seen.add(key)
        _require_int(expected_length, source=f"{label}[{index}].length")
        if not HEX64.fullmatch(expected_sha):
            _fail("invalid-fingerprint-sha256", source=f"{label}[{index}].sha256", actual=expected_sha)
        actual = _fingerprint(path)
        if actual["length"] != expected_length:
            _fail("fingerprint-length-mismatch", source=str(path), expected=expected_length, actual=actual["length"])
        if actual["sha256"] != expected_sha:
            _fail("fingerprint-sha256-mismatch", source=str(path), expected=expected_sha, actual=actual["sha256"])
        result.append({**actual, "role": row.get("role")})
    return result


def _discover_blc_paths(outer: Mapping[str, Any]) -> list[str]:
    paths: set[str] = set()
    for root_name in ("primaryAssets", "fallbackAssets"):
        raw_root = outer.get(root_name)
        if not isinstance(raw_root, str) or not raw_root:
            _fail("missing-assets-root", source=f"outer.{root_name}", actual=raw_root)
        root = Path(raw_root).resolve()
        for path in (root / "VFS").rglob("*.blc"):
            if path.is_file():
                paths.add(os.path.normcase(str(path.resolve())))
    return sorted(paths)


def _expected_blc_paths(outer: Mapping[str, Any]) -> list[str]:
    rows = outer.get("sourceFingerprints")
    if not isinstance(rows, list):
        _fail("missing-source-fingerprints", source="outer.sourceFingerprints", actual=type(rows).__name__)
    return sorted(os.path.normcase(str(Path(str(row.get("path") or "")).resolve())) for row in rows)


def _read_outer_and_ledger(
    outer_path: Path,
    ledger_path: Path,
    *,
    expected_input_set_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    expected_input = expected_input_set_sha256.upper()
    if not HEX64.fullmatch(expected_input):
        _fail("invalid-expected-input-set", source="argument", expected="64 uppercase hex", actual=expected_input_set_sha256)
    outer_bytes = outer_path.read_bytes()
    outer = json.loads(outer_bytes)
    if outer.get("format") != "animestudio-vfs-boundary-audit" or outer.get("schemaVersion") != 1:
        _fail("outer-schema-mismatch", source=str(outer_path), expected=["animestudio-vfs-boundary-audit", 1], actual=[outer.get("format"), outer.get("schemaVersion")])
    if outer.get("inputSetSha256") != expected_input:
        _fail("outer-input-set-mismatch", source=str(outer_path), expected=expected_input, actual=outer.get("inputSetSha256"))
    summary = outer.get("summary")
    if not isinstance(summary, dict) or summary.get("fullAuditPassed") is not True:
        _fail("outer-not-complete", source=str(outer_path), expected=True, actual=(summary or {}).get("fullAuditPassed") if isinstance(summary, dict) else None)

    ledger_fp = _fingerprint(ledger_path)
    published_ledger_sha = str((outer.get("publication") or {}).get("ledgerSha256") or "").upper()
    if ledger_fp["sha256"] != published_ledger_sha:
        _fail("ledger-publication-sha256-mismatch", source=str(ledger_path), expected=published_ledger_sha, actual=ledger_fp["sha256"])

    header: dict[str, Any] | None = None
    file_rows: list[dict[str, Any]] = []
    with gzip.open(ledger_path, "rt", encoding="utf-8") as handle:
        for line_index, line in enumerate(handle):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                _fail("ledger-json-invalid", source=str(ledger_path), offset=line_index, actual=str(exc))
            if line_index == 0:
                if row.get("recordType") != "audit_header":
                    _fail("ledger-header-missing", source=str(ledger_path), offset=0, expected="audit_header", actual=row.get("recordType"))
                header = row
                continue
            if row.get("recordType") == "audit_header":
                _fail("duplicate-ledger-header", source=str(ledger_path), offset=line_index)
            if row.get("recordType") == "file":
                file_rows.append(row)
    if header is None:
        _fail("ledger-empty", source=str(ledger_path))
    if header.get("schemaVersion") != 1 or header.get("inputSetSha256") != expected_input:
        _fail("ledger-header-mismatch", source=str(ledger_path), expected={"schemaVersion": 1, "inputSetSha256": expected_input}, actual={"schemaVersion": header.get("schemaVersion"), "inputSetSha256": header.get("inputSetSha256")})
    for field in ("primaryAssets", "fallbackAssets", "sourceFingerprints", "buildFingerprints"):
        if header.get(field) != outer.get(field):
            _fail("ledger-header-outer-mismatch", source=f"ledger.header.{field}", expected=outer.get(field), actual=header.get(field))
    expected_files = _require_int(summary.get("ledgerFileCount"), source="outer.summary.ledgerFileCount")
    if len(file_rows) != expected_files:
        _fail("ledger-file-count-mismatch", source=str(ledger_path), expected=expected_files, actual=len(file_rows))
    provenance = {
        "outer": {"path": outer_path.resolve().as_posix(), "length": len(outer_bytes), "sha256": hashlib.sha256(outer_bytes).hexdigest().upper()},
        "ledger": ledger_fp,
        "sourceFingerprints": _snapshot_pinned_files(outer.get("sourceFingerprints"), label="outer.sourceFingerprints"),
        "buildFingerprints": _snapshot_pinned_files(outer.get("buildFingerprints"), label="outer.buildFingerprints"),
        "blcPaths": _discover_blc_paths(outer),
    }
    expected_blcs = _expected_blc_paths(outer)
    if provenance["blcPaths"] != expected_blcs:
        _fail("blc-path-set-mismatch", source="outer assets roots", expected=expected_blcs, actual=provenance["blcPaths"])
    return outer, header, file_rows, provenance


def _skill_rows(file_rows: Iterable[Mapping[str, Any]], *, expected_input: str) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ledger_index, raw_row in enumerate(file_rows):
        virtual_path = raw_row.get("virtualPath")
        if not isinstance(virtual_path, str) or not virtual_path.startswith(SKILL_PREFIX):
            continue
        if not SKILL_PATTERN.fullmatch(virtual_path):
            _fail("unsupported-skill-path", source=f"ledger.file[{ledger_index}].virtualPath", actual=virtual_path)
        if virtual_path in seen:
            _fail("duplicate-skill-identity", source=f"ledger.file[{ledger_index}]", actual=virtual_path)
        seen.add(virtual_path)
        row = dict(raw_row)
        checks = {
            "recordType": "file",
            "inputSetSha256": expected_input,
            "status": "verified",
            "boundaryStatus": "boundary_verified",
            "blockName": "JsonData",
            "blockTypeValue": 19,
            "encrypted": True,
        }
        for field, expected in checks.items():
            if row.get(field) != expected:
                _fail("skill-ledger-field-mismatch", source=f"{virtual_path}.{field}", expected=expected, actual=row.get(field))
        length = _require_int(row.get("length"), source=f"{virtual_path}.length", minimum=1)
        actual_read = _require_int(row.get("actualBytesRead"), source=f"{virtual_path}.actualBytesRead")
        if actual_read != length:
            _fail("skill-ledger-byte-count-mismatch", source=virtual_path, expected=length, actual=actual_read)
        offset = _require_int(row.get("offset"), source=f"{virtual_path}.offset")
        physical = Path(str(row.get("physicalChunkPath") or "")).resolve()
        if not physical.is_file():
            _fail("skill-chunk-missing", source=virtual_path, expected="existing physical chunk", actual=str(physical))
        chunk_size = physical.stat().st_size
        if offset > chunk_size or length > chunk_size - offset:
            _fail("skill-ledger-range-out-of-bounds", source=virtual_path, offset=offset, expected=f"end <= {chunk_size}", actual=offset + length)
        md5 = str(row.get("recomputedFileDataMd5") or "").upper()
        if not re.fullmatch(r"[0-9A-F]{32}", md5):
            _fail("skill-ledger-md5-invalid", source=virtual_path, actual=md5)
        for field in ("physicalChunkSource", "metadataProvenance", "overlayState", "chunkOverlayState", "hashDirectory", "chunkFile"):
            if not isinstance(row.get(field), str) or not row[field]:
                _fail("skill-ledger-provenance-missing", source=f"{virtual_path}.{field}", actual=row.get(field))
        selected.append(row)
    if not selected:
        _fail("skill-ledger-empty", source="ledger", expected="at least one SkillData row", actual=0)
    return sorted(selected, key=lambda row: row["virtualPath"])


def _stream_tool_snapshot(cli_path: Path) -> list[dict[str, Any]]:
    cli_path = cli_path.resolve()
    paths = [cli_path]
    paths.extend(sorted(cli_path.parent.glob("AnimeStudio*.dll")))
    keys: set[str] = set()
    result: list[dict[str, Any]] = []
    for path in paths:
        key = os.path.normcase(str(path.resolve()))
        if key in keys:
            continue
        keys.add(key)
        result.append(_fingerprint(path))
    return result


def _parser_source_snapshots() -> list[dict[str, Any]]:
    source_root = MODULE_REPO_ROOT / "scripts/game_data/memorypack"
    # Pin the complete small package so a newly split terminal helper cannot be
    # executed without appearing in provenance.
    return [_fingerprint(path) for path in sorted(source_root.glob("*.py"))]


def _guard_output_path(output_path: Path, protected_paths: Iterable[Path]) -> None:
    output = output_path.resolve()
    output_key = os.path.normcase(str(output))
    for raw_path in protected_paths:
        protected = raw_path.resolve()
        if output_key == os.path.normcase(str(protected)):
            _fail("output-overlaps-input", source=str(output), expected="distinct output", actual=str(protected))
        if protected.is_dir() and output.is_relative_to(protected):
            _fail("output-inside-input-root", source=str(output),
                  expected="outside installed input roots", actual=str(protected))
        if output.exists() and protected.exists():
            try:
                if os.path.samefile(output, protected):
                    _fail("output-hardlinks-input", source=str(output), expected="distinct inode", actual=str(protected))
            except OSError:
                pass


def _guard_partial_output(output_path: Path) -> None:
    resolved = output_path.resolve()
    allowed = [MODULE_REPO_ROOT / name for name in ("tmp", "scratch")]
    if not any(resolved.is_relative_to(root.resolve()) for root in allowed):
        _fail("partial-output-outside-scratch", source=str(resolved),
              expected="output under repo tmp/ or scratch/", actual=str(resolved))


def _stream_command(cli_path: Path, outer: Mapping[str, Any], selected_rows: list[Mapping[str, Any]], *, partial: bool) -> list[str]:
    command = [
        str(cli_path.resolve()),
        "stream",
        "--streaming-assets", str(outer["primaryAssets"]),
        "--fallback-assets", str(outer["fallbackAssets"]),
        "--block-type", "json-data",
        "--verify-md5",
    ]
    if partial:
        for row in selected_rows:
            command.extend(("--file-regex", "^" + re.escape(str(row["virtualPath"])).replace(r"/", "/") + "$"))
    else:
        command.extend(("--file-regex", r"^Data/Json/SkillData/[^/]+[.]json$"))
    return command


def _read_stream_rows(command: list[str]) -> tuple[list[dict[str, Any]], str]:
    # The selected corpus is about 24 MiB (roughly 33 MiB base64), so bounded
    # communicate() avoids the stdout/stderr pipe deadlock of sequential drains.
    process = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(process.stdout.splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            _fail("stream-json-invalid", source="AnimeStudio stream stdout", offset=line_number, actual=str(exc))
        if not isinstance(row, dict):
            _fail("stream-row-not-object", source="AnimeStudio stream stdout", offset=line_number, actual=type(row).__name__)
        rows.append(row)
    if process.returncode != 0:
        _fail("stream-process-failed", source=command[0], expected=0, actual={"returnCode": process.returncode, "stderr": process.stderr[-4000:]})
    return rows, process.stderr


def _join_and_frame(
    ledger_rows: list[Mapping[str, Any]],
    stream_rows: list[Mapping[str, Any]],
    *,
    stderr: str,
) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, int]]:
    ledger_by_path = {str(row["virtualPath"]): row for row in ledger_rows}
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    coverage_counts: Counter[str] = Counter()
    for index, stream_row in enumerate(stream_rows):
        path = stream_row.get("fileName")
        if not isinstance(path, str) or path not in ledger_by_path:
            _fail("unexpected-stream-identity", source=f"stream[{index}].fileName", expected="selected ledger identity", actual=path)
        if path in seen:
            _fail("duplicate-stream-identity", source=f"stream[{index}]", actual=path)
        seen.add(path)
        ledger = ledger_by_path[path]
        if stream_row.get("blockType") != "JsonData" or stream_row.get("blockTypeValue") != 19:
            _fail("stream-block-mismatch", source=path, expected=["JsonData", 19], actual=[stream_row.get("blockType"), stream_row.get("blockTypeValue")])
        length = _require_int(stream_row.get("length"), source=f"stream:{path}.length", minimum=1)
        encoded = stream_row.get("dataBase64")
        if not isinstance(encoded, str):
            _fail("stream-base64-missing", source=path, actual=type(encoded).__name__)
        try:
            data = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            _fail("stream-base64-invalid", source=path, actual=str(exc))
        if length != len(data) or length != ledger["length"]:
            _fail("stream-length-mismatch", source=path, expected=ledger["length"], actual={"declared": length, "decoded": len(data)})
        actual_md5 = hashlib.md5(data).hexdigest().upper()
        if actual_md5 != ledger["recomputedFileDataMd5"]:
            _fail("stream-ledger-md5-mismatch", source=path, expected=ledger["recomputedFileDataMd5"], actual=actual_md5)
        identity_result = {
            "virtualPath": path,
            "blockName": ledger["blockName"],
            "blockTypeValue": ledger["blockTypeValue"],
            "length": length,
            "logicalMd5": actual_md5,
            "logicalSha256": hashlib.sha256(data).hexdigest().upper(),
            "physicalChunkPath": ledger["physicalChunkPath"],
            "physicalChunkSource": ledger["physicalChunkSource"],
            "metadataProvenance": ledger["metadataProvenance"],
            "overlayState": ledger["overlayState"],
            "chunkOverlayState": ledger["chunkOverlayState"],
            "physicalOffset": ledger["offset"],
            "encrypted": ledger["encrypted"],
        }
        try:
            common_prefix = frame_skill_common_prefix(data)
            framed = frame_skill_memorypack(data, source=path)
        except Exception as exc:
            coverage_counts["failed-framing"] += 1
            results.append({
                **identity_result,
                "coverageStatus": "failed-framing",
                "framingFailure": {
                    "code": "skill-framer-failed",
                    "source": path,
                    "offset": "0x0",
                    "expected": "valid maintained SkillData structural profile",
                    "actual": f"{type(exc).__name__}: {exc}",
                },
                "wholeSchemaExact": False,
            })
            continue
        status_counts[framed["status"]] += 1
        prefix_end = int(common_prefix["cursorOffset"], 0)
        candidate_coverage: list[dict[str, Any]] = []
        has_overlap = False
        for candidate_index, candidate in enumerate(framed["candidates"]):
            candidate_start = int(candidate["startOffset"], 0)
            overlap = candidate_start < prefix_end
            has_overlap = has_overlap or overlap
            candidate_coverage.append({
                "candidateIndex": candidate_index,
                "prefixCertifiedRange": {"start": 0, "end": prefix_end, "endExclusive": True},
                "terminalCertifiedRange": {"start": candidate_start, "end": len(data), "endExclusive": True},
                "rangesOverlap": overlap,
                "opaqueGap": None if overlap else {
                    "start": prefix_end,
                    "end": candidate_start,
                    "length": candidate_start - prefix_end,
                },
            })
        if has_overlap:
            coverage_status = "unsupported-overlapping-independent-ranges"
        elif framed["candidateCount"] == 0:
            coverage_status = "unsupported-no-terminal-candidate"
        elif framed["candidateCount"] > 1:
            coverage_status = "ambiguous-disjoint-independent-ranges"
        else:
            coverage_status = "unique-disjoint-independent-ranges"
        coverage_counts[coverage_status] += 1
        results.append({
            **identity_result,
            "commonPrefixFraming": common_prefix,
            "framing": framed,
            "coverageStatus": coverage_status,
            "candidateCoverage": candidate_coverage,
            "wholeSchemaExact": False,
        })
    missing = sorted(set(ledger_by_path) - seen)
    if missing:
        _fail("stream-missing-identities", source="AnimeStudio stream", expected=len(ledger_by_path), actual={"count": len(seen), "firstMissing": missing[:10]})
    matches = re.findall(r"(?m)^Streamed ([0-9]+) files\s*$", stderr)
    if len(matches) != 1 or int(matches[0]) != len(stream_rows):
        _fail("stream-terminal-count-mismatch", source="AnimeStudio stream stderr", expected=len(stream_rows), actual={"matches": matches, "stderrTail": stderr[-1000:]})
    return (
        sorted(results, key=lambda row: row["virtualPath"]),
        dict(sorted(status_counts.items())),
        dict(sorted(coverage_counts.items())),
    )


def build_current_census(
    *,
    outer_path: Path,
    ledger_path: Path,
    cli_path: Path,
    expected_input_set_sha256: str,
    max_files: int | None = None,
    output_path: Path | None = None,
    output_md_path: Path | None = None,
) -> dict[str, Any]:
    if max_files is not None:
        _require_int(max_files, source="maxFiles", minimum=1)
    if output_path is not None and output_md_path is not None:
        _guard_output_path(output_path, [output_md_path])
    outer, _header, file_rows, provenance_start = _read_outer_and_ledger(
        outer_path, ledger_path, expected_input_set_sha256=expected_input_set_sha256
    )
    all_skill_rows = _skill_rows(file_rows, expected_input=expected_input_set_sha256.upper())
    selected = all_skill_rows if max_files is None else all_skill_rows[:max_files]
    partial = max_files is not None
    chunk_selection_start = _chunk_selection_snapshot(selected, outer)
    selected_chunks_start = _chunk_fingerprints(selected)
    stream_tool_start = _stream_tool_snapshot(cli_path)
    cli_key = os.path.normcase(str(cli_path.resolve()))
    authenticated_build_paths = {
        os.path.normcase(str(Path(row["path"]).resolve()))
        for row in provenance_start["buildFingerprints"]
    }
    if cli_key not in authenticated_build_paths:
        _fail("stream-cli-not-in-outer-build-fingerprints", source=str(cli_path.resolve()),
              expected=sorted(authenticated_build_paths), actual=cli_key)
    parser_start = _parser_source_snapshots()
    gate_start = _fingerprint(Path(__file__))
    outputs = [path for path in (output_path, output_md_path) if path is not None]
    if outputs:
        protected = [outer_path, ledger_path, Path(__file__),
                     Path(outer["primaryAssets"]), Path(outer["fallbackAssets"])]
        # Outputs must not damage unselected format families either. Retain
        # all ledger chunk paths for collision checks without hashing them.
        chunk_paths = sorted({str(row.get("physicalChunkPath")) for row in file_rows
                              if row.get("physicalChunkPath")})
        vfs_roots = [(Path(outer[field]) / "VFS").resolve()
                     for field in ("primaryAssets", "fallbackAssets")]
        for raw_path in chunk_paths:
            chunk_path = Path(raw_path).resolve()
            if not any(chunk_path.is_relative_to(root) for root in vfs_roots):
                _fail("ledger-chunk-outside-input-roots", source=raw_path,
                      expected=[str(root) for root in vfs_roots], actual=str(chunk_path))
            protected.append(chunk_path)
        protected.extend(Path(row["path"]) for row in provenance_start["sourceFingerprints"])
        protected.extend(Path(row["path"]) for row in provenance_start["buildFingerprints"])
        protected.extend(Path(row["path"]) for row in stream_tool_start)
        protected.extend(Path(row["path"]) for row in selected_chunks_start)
        protected.extend(Path(row["path"]) for row in parser_start)
        for output in outputs:
            if partial:
                _guard_partial_output(output)
            _guard_output_path(output, protected + [path for path in outputs if path != output])
    command = _stream_command(cli_path, outer, selected, partial=partial)
    stream_rows, stderr = _read_stream_rows(command)
    rows, status_counts, coverage_counts = _join_and_frame(selected, stream_rows, stderr=stderr)

    _outer_end, _header_end, end_file_rows, provenance_end = _read_outer_and_ledger(
        outer_path, ledger_path, expected_input_set_sha256=expected_input_set_sha256
    )
    end_skill_rows = _skill_rows(end_file_rows, expected_input=expected_input_set_sha256.upper())
    if [row["virtualPath"] for row in end_skill_rows] != [row["virtualPath"] for row in all_skill_rows]:
        _fail("skill-ledger-set-drift", source=str(ledger_path), expected=len(all_skill_rows), actual=len(end_skill_rows))
    stream_tool_end = _stream_tool_snapshot(cli_path)
    selected_chunks_end = _chunk_fingerprints(selected)
    chunk_selection_end = _chunk_selection_snapshot(selected, outer)
    parser_end = _parser_source_snapshots()
    gate_end = _fingerprint(Path(__file__))
    if provenance_start != provenance_end:
        _fail("outer-provenance-drift", source=str(outer_path), expected=provenance_start, actual=provenance_end)
    if stream_tool_start != stream_tool_end:
        _fail("stream-tool-drift", source=str(cli_path), expected=stream_tool_start, actual=stream_tool_end)
    if selected_chunks_start != selected_chunks_end:
        _fail("selected-chunk-drift", source="SkillData physical chunks", expected=selected_chunks_start, actual=selected_chunks_end)
    if chunk_selection_start != chunk_selection_end:
        _fail("chunk-overlay-selection-drift", source="SkillData chunk selection", expected=chunk_selection_start, actual=chunk_selection_end)
    if parser_start != parser_end or gate_start != gate_end:
        _fail("code-drift", source="SkillData census code", expected={"parser": parser_start, "corpusGate": gate_start}, actual={"parser": parser_end, "corpusGate": gate_end})
    for output in outputs:
        _guard_output_path(output, protected + [path for path in outputs if path != output])

    identity_rows = [
        {key: row[key] for key in (
            "virtualPath", "blockTypeValue", "length", "logicalMd5", "logicalSha256",
            "physicalChunkPath", "physicalChunkSource", "metadataProvenance", "overlayState",
            "chunkOverlayState", "physicalOffset", "encrypted",
        )}
        for row in rows
    ]
    unique_count = coverage_counts.get("unique-disjoint-independent-ranges", 0)
    ambiguous_count = coverage_counts.get("ambiguous-disjoint-independent-ranges", 0)
    failed_count = coverage_counts.get("failed-framing", 0)
    unsupported_count = len(rows) - unique_count - ambiguous_count - failed_count
    final_status = "failed" if failed_count else "partial" if partial else "complete"
    return {
        "format": "animestudio-skilldata-current-vfs-corpus",
        "schemaVersion": 1,
        "status": final_status,
        "publicationEligible": not partial and failed_count == 0,
        "inputSetSha256": expected_input_set_sha256.upper(),
        "provenance": {
            **provenance_start,
            "combinedOuterFingerprintCount": len(provenance_start["sourceFingerprints"]) + len(provenance_start["buildFingerprints"]),
            "streamToolFingerprints": stream_tool_start,
            "selectedChunkFingerprints": selected_chunks_start,
            "selectedChunkResolution": chunk_selection_start,
            "parser": parser_start,
            "corpusGate": gate_start,
        },
        "summary": {
            "ledgerSkillFiles": len(all_skill_rows),
            "filesSelected": len(selected),
            "filesSucceeded": len(rows) - failed_count,
            "filesFailed": failed_count,
            "filesUnique": unique_count,
            "filesAmbiguous": ambiguous_count,
            "filesUnsupported": unsupported_count,
            "logicalBytes": sum(row["length"] for row in rows),
            "physicalChunkCount": len({row["physicalChunkPath"] for row in rows}),
            "framingStatusCounts": status_counts,
            "coverageStatusCounts": coverage_counts,
        },
        "identitySetSha256": _canonical_sha256(identity_rows),
        "wholeSchemaExact": False,
        "evidenceBoundary": (
            "current outer-ledger identities plus AnimeStudio stream --verify-md5 decrypted bytes; "
            "the maintained framer proves only the 48-member envelope and anonymous EOF terminal "
            "candidate shapes, while prefix fields, candidate ownership, field order, and semantics remain unresolved"
        ),
        "files": rows,
    }


def _atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# SkillData current VFS corpus", "",
        f"Status: `{report['status']}`; inputSetSha256: `{report['inputSetSha256']}`.", "",
        f"Selected: {summary['filesSelected']}/{summary['ledgerSkillFiles']}; "
        f"successful: {summary['filesSucceeded']}; failed: {summary['filesFailed']}; "
        f"unsupported: {summary['filesUnsupported']}.",
        f"Unique supported candidates: {summary['filesUnique']}; "
        f"ambiguous: {summary['filesAmbiguous']}; logical bytes: {summary['logicalBytes']}.", "",
        report["evidenceBoundary"], "",
        "A candidate is not an independently proven formatter start. "
        "Whole-schema exactness and field semantics remain unresolved.", "",
        "Full identities, hashes, ranges and source gates are in the companion JSON.", "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-summary", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--outer-ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--animestudio-cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--max-files", type=int)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-md", type=Path)
    args = parser.parse_args(argv)
    try:
        result = build_current_census(
            outer_path=args.outer_summary,
            ledger_path=args.outer_ledger,
            cli_path=args.animestudio_cli,
            expected_input_set_sha256=args.expected_input_set_sha256,
            max_files=args.max_files,
            output_path=args.output,
            output_md_path=args.output_md,
        )
        if args.output_md is not None:
            if args.max_files is not None:
                _guard_partial_output(args.output_md)
            protected = [args.output, args.outer_summary, args.outer_ledger]
            provenance = result["provenance"]
            for field in ("sourceFingerprints", "buildFingerprints", "streamToolFingerprints",
                          "selectedChunkFingerprints", "parser"):
                protected.extend(Path(row["path"]) for row in provenance[field])
            _guard_output_path(args.output_md, protected)
            args.output_md.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(dir=args.output_md.parent, suffix=".tmp")
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(render_markdown(result))
                os.replace(temporary, args.output_md)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        # JSON is the final publication marker after the optional Markdown.
        _atomic_write_json(args.output, result)
    except Exception as exc:
        diagnostic = exc.diagnostic if isinstance(exc, CensusGateError) else {
            "code": "unexpected-error", "source": "skilldata-current-census", "offset": None,
            "expected": None, "actual": f"{type(exc).__name__}: {exc}",
        }
        print(json.dumps({"status": "failed", "diagnostic": diagnostic}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({"status": result["status"], "files": result["summary"]["filesSucceeded"], "output": str(args.output)}, ensure_ascii=False))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())

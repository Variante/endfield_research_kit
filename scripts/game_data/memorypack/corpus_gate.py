"""Shared current-input MemoryPack corpus gate.

Family-agnostic provenance, overlay-selection, drift, and output guards used by
each JsonData family census (``skill_corpus``, ``buff_corpus``).  A family
module supplies its own ledger prefix/pattern, framer, coverage classification,
report format, and Markdown rendering; nothing here interprets payload bytes.
"""

from __future__ import annotations

import ast
import gzip
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping

HEX64 = re.compile(r"^[0-9A-F]{64}$")
from scripts.repo_paths import REPO_ROOT
from scripts.common import sha256_file_upper as _sha256_file

MODULE_REPO_ROOT = REPO_ROOT
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
        candidates: dict[str, Path] = {}
        for role, root in roots.items():
            candidate = (root / "VFS" / hash_directory / chunk_file).resolve()
            if not candidate.is_relative_to(root):
                _fail(
                    "chunk-path-outside-assets-root",
                    source=virtual_path,
                    expected={"role": role, "root": str(root)},
                    actual=str(candidate),
                )
            candidates[role] = candidate
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


def verify_current_report_inputs(
    report: Mapping[str, Any],
    *,
    expected_format: str = "animestudio-skilldata-current-vfs-corpus",
    label: str = "SkillData",
) -> dict[str, Any]:
    """Recheck live provenance of an already authenticated complete report.

    This does not re-stream bytes or certify an arbitrary report. Consumers
    must first authenticate the report itself; a report hash alone cannot
    establish that its tool, parser, catalog and chunk inputs are still live.
    """
    if (report.get("format") != expected_format
            or report.get("schemaVersion") != 1 or report.get("status") != "complete"
            or report.get("publicationEligible") is not True):
        _fail("report-not-complete", source=f"{label} corpus report", actual=report.get("status"))
    provenance = report.get("provenance")
    if not isinstance(provenance, Mapping):
        _fail("report-provenance-missing", source=f"{label} corpus report")
    checked = {}
    for role in ("outer", "ledger", "corpusGate"):
        row = provenance.get(role)
        checked[role] = _snapshot_pinned_files([row] if isinstance(row, Mapping) else [], label=role)
    for role in ("sourceFingerprints", "buildFingerprints", "streamToolFingerprints",
                 "selectedChunkFingerprints", "parser"):
        rows = provenance.get(role)
        if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
            _fail("report-fingerprint-list-invalid", source=role, expected="list of mappings", actual=type(rows).__name__)
        checked[role] = _snapshot_pinned_files(rows, label=role)
    outer = json.loads(Path(provenance["outer"]["path"]).read_bytes())
    if outer.get("inputSetSha256") != report.get("inputSetSha256"):
        _fail("report-outer-input-set-mismatch", source=provenance["outer"]["path"],
              expected=report.get("inputSetSha256"), actual=outer.get("inputSetSha256"))
    current_paths = _discover_blc_paths(outer)
    if current_paths != provenance.get("blcPaths"):
        _fail("blc-path-set-mismatch", source=f"current {label} report roots",
              expected=provenance.get("blcPaths"), actual=current_paths)
    resolutions = provenance.get("selectedChunkResolution")
    if not isinstance(resolutions, list) or not resolutions or not all(isinstance(row, Mapping) for row in resolutions):
        _fail("report-chunk-resolution-missing", source=f"saved {label} provenance")
    selection_rows = []
    for row in resolutions:
        role = row.get("selectedRole")
        root_key = {"primary": "primaryAssets", "fallback": "fallbackAssets"}.get(role)
        if root_key is None:
            _fail("report-chunk-role-invalid", source=f"saved {label} provenance", actual=role)
        selection_rows.append({"virtualPath": "saved report chunk", "hashDirectory": row.get("hashDirectory"),
                               "chunkFile": Path(str(row.get("selectedPath") or "")).name,
                               "physicalChunkPath": row.get("selectedPath"),
                               "physicalChunkSource": role, "physicalChunkRoot": outer[root_key]})
    current_resolution = _chunk_selection_snapshot(selection_rows, outer)
    if current_resolution != resolutions:
        _fail("report-chunk-resolution-drift", source=f"saved {label} provenance",
              expected=resolutions, actual=current_resolution)
    return checked


def family_rows(
    file_rows: Iterable[Mapping[str, Any]],
    *,
    expected_input: str,
    prefix: str,
    pattern: re.Pattern[str],
    label: str,
) -> list[dict[str, Any]]:
    """Select and gate one JsonData family's current ledger rows."""
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ledger_index, raw_row in enumerate(file_rows):
        virtual_path = raw_row.get("virtualPath")
        if not isinstance(virtual_path, str) or not virtual_path.startswith(prefix):
            continue
        if not pattern.fullmatch(virtual_path):
            _fail(f"unsupported-{label}-path", source=f"ledger.file[{ledger_index}].virtualPath", actual=virtual_path)
        if virtual_path in seen:
            _fail(f"duplicate-{label}-identity", source=f"ledger.file[{ledger_index}]", actual=virtual_path)
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
                _fail(f"{label}-ledger-field-mismatch", source=f"{virtual_path}.{field}", expected=expected, actual=row.get(field))
        length = _require_int(row.get("length"), source=f"{virtual_path}.length", minimum=1)
        actual_read = _require_int(row.get("actualBytesRead"), source=f"{virtual_path}.actualBytesRead")
        if actual_read != length:
            _fail(f"{label}-ledger-byte-count-mismatch", source=virtual_path, expected=length, actual=actual_read)
        offset = _require_int(row.get("offset"), source=f"{virtual_path}.offset")
        physical = Path(str(row.get("physicalChunkPath") or "")).resolve()
        if not physical.is_file():
            _fail(f"{label}-chunk-missing", source=virtual_path, expected="existing physical chunk", actual=str(physical))
        chunk_size = physical.stat().st_size
        if offset > chunk_size or length > chunk_size - offset:
            _fail(f"{label}-ledger-range-out-of-bounds", source=virtual_path, offset=offset, expected=f"end <= {chunk_size}", actual=offset + length)
        md5 = str(row.get("recomputedFileDataMd5") or "").upper()
        if not re.fullmatch(r"[0-9A-F]{32}", md5):
            _fail(f"{label}-ledger-md5-invalid", source=virtual_path, actual=md5)
        for field in ("physicalChunkSource", "metadataProvenance", "overlayState", "chunkOverlayState", "hashDirectory", "chunkFile"):
            if not isinstance(row.get(field), str) or not row[field]:
                _fail(f"{label}-ledger-provenance-missing", source=f"{virtual_path}.{field}", actual=row.get(field))
        selected.append(row)
    if not selected:
        _fail(f"{label}-ledger-empty", source="ledger", expected=f"at least one {label} row", actual=0)
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


PARSER_PACKAGE = "scripts.game_data.memorypack"


def _package_import_closure(entry: Path) -> list[Path]:
    """Every module of the package that ``entry`` can execute, found statically.

    Imports are followed wherever they appear, including inside functions, so
    a newly split helper cannot run without being fingerprinted. The package
    has no dynamic imports, which is what makes the static closure complete.
    """

    source_root = MODULE_REPO_ROOT / "scripts/game_data/memorypack"
    pending = [entry.resolve()]
    seen: set[Path] = set()
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        tree = ast.parse(path.read_bytes(), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = ".".join(PARSER_PACKAGE.split(".")[: len(PARSER_PACKAGE.split(".")) - node.level + 1])
                    module = f"{base}.{node.module}" if node.module else base
                else:
                    module = node.module or ""
                names = [module] + [f"{module}.{alias.name}" for alias in node.names]
            for name in names:
                if not name.startswith(PARSER_PACKAGE + "."):
                    continue
                leaf = name[len(PARSER_PACKAGE) + 1:].split(".")[0]
                candidate = source_root / f"{leaf}.py"
                if candidate.is_file():
                    pending.append(candidate.resolve())
    init = source_root / "__init__.py"
    if init.is_file():
        seen.add(init.resolve())
    return sorted(seen)


def _parser_source_snapshots(entry: Path) -> list[dict[str, Any]]:
    """Fingerprint the parser modules one family's gate executes.

    Pinning the whole package made every family's report stale whenever an
    unrelated family's reader changed; the import closure keeps the guarantee
    that matters -- nothing executed escapes provenance -- without that.
    """

    return [_fingerprint(path) for path in _package_import_closure(Path(entry))]


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



"""Authenticate and decode the installed ExtendData CompressData archive.

The exact Brotli/UTF-16LE/JSON reader lives in AnimeStudio's
``EndfieldCompressData``. This gate binds that reader to one full VFS audit,
rechecks the selected physical file slice, and verifies the decoder manifest
against the archive's complete offset table. Decoded JSON remains temporary.

AnimeStudio exposes the reader as the opt-in ``extend-data`` CLI command. The
gate binds the targeted, MD5-verified dump and the audited CLI apphost to the
same input set and pins the compiled decoder's complete output closure through
the ``extend_data_compress_reader.json`` contract. Each record has two
little-endian lengths and an exact Brotli body that decodes as strict UTF-16LE
JSON; the last record reaches EOF, and every current root is a NodeCanvas
behavior tree. The same run enforces the graph schema (``extend_data_graph``)
and the task envelopes (``extend_data_tasks``). The bytes establish authored
graph structure, not a selected runtime branch or blackboard value.

Pass the VFS audit's ``inputSetSha256`` as ``--expected-input-set-sha256``;
the report is ``reports/animestudio/extend_data_compress_current_latest.json``.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.game_data.corpus_common import atomic_write_text, validate_provenance
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.extend_data_graph import load_contract as load_graph_contract, validate_graph
from scripts.game_data.extend_data_tasks import load_contract as load_task_contract, validate_tasks
from scripts.repo_paths import REPO_ROOT


VIRTUAL_PATH = "Data/ExtendData/Main/CompressData.bin"
BLOCK_TYPE = 20
SCHEMA = "endfield.extend-data-compress-corpus.v1"
DEFAULT_CLI = REPO_ROOT / "tools/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/AnimeStudio.CLI.exe"
READER_CONTRACT = CONTRACTS_DIR / "extend_data_compress_reader.json"


class CompressCorpusError(ValueError):
    """Selected source or decoder receipt failed a current-corpus check."""


def _selected_row(summary_path: Path, ledger_path: Path,
                  expected_input_set: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    headers: list[dict[str, Any]] = []
    matches: list[dict[str, Any]] = []
    with gzip.open(ledger_path, "rt", encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            if row.get("recordType") == "audit_header":
                headers.append(row)
            elif row.get("recordType") == "file" and row.get("fileName") == VIRTUAL_PATH:
                matches.append(row)
    if len(headers) != 1 or len(matches) != 1:
        raise CompressCorpusError(f"expected one ledger header and one {VIRTUAL_PATH} row; got {len(headers)} and {len(matches)}")
    failures, provenance = validate_provenance(summary, headers[0], ledger_path, expected_input_set)
    if failures:
        raise CompressCorpusError(f"outer audit provenance mismatch: {failures[:4]}")
    row = matches[0]
    if (row.get("inputSetSha256", "").upper() != expected_input_set.upper()
            or row.get("status") != "verified"
            or row.get("boundaryStatus") != "boundary_verified"
            or row.get("blockTypeValue") != BLOCK_TYPE
            or row.get("encrypted") is not False):
        raise CompressCorpusError(f"selected ledger row is not verified raw ExtendData: {row.get('status')}")
    return summary, provenance, row


def _decoder_closure(cli: Path) -> dict[str, Any]:
    root = cli.resolve().parent
    if not root.is_dir():
        raise CompressCorpusError(f"decoder output directory is missing: {root}")
    paths = sorted((path for path in root.rglob("*") if path.is_file()),
                   key=lambda path: path.relative_to(root).as_posix().casefold())
    files: list[dict[str, Any]] = []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        before = path.stat()
        digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        after = path.stat()
        if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
            raise CompressCorpusError(f"decoder output changed while hashing: {relative}")
        files.append({"path": relative, "length": after.st_size, "sha256": digest})
    raw = json.dumps(files, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    return {"manifestFormat": "relative-path-length-sha256-v1",
            "fileCount": len(files), "manifestSha256": hashlib.sha256(raw).hexdigest().upper(),
            "files": files}


def _cli_identity(summary: dict[str, Any], cli: Path,
                  closure: dict[str, Any], reader_contract: dict[str, Any]) -> dict[str, Any]:
    if not cli.is_file():
        raise CompressCorpusError(f"decoder CLI is missing: {cli}")
    matches = [fingerprint for fingerprint in summary.get("buildFingerprints", [])
               if Path(str(fingerprint.get("path", ""))).resolve() == cli.resolve()]
    if len(matches) != 1:
        raise CompressCorpusError(f"outer audit has no unique decoder CLI fingerprint: {cli}")
    digest = hashlib.sha256(cli.read_bytes()).hexdigest().upper()
    if digest != str(matches[0].get("sha256", "")).upper() or cli.stat().st_size != matches[0].get("length"):
        raise CompressCorpusError("decoder CLI differs from the selected outer audit")
    expected = reader_contract.get("decoderOutputClosure") or {}
    if (closure["manifestFormat"] != expected.get("manifestFormat")
            or closure["manifestSha256"] != expected.get("manifestSha256")
            or closure["fileCount"] != expected.get("fileCount")):
        raise CompressCorpusError("decoder output closure differs from reviewed reader contract")
    critical = {row["path"]: row for row in closure["files"]}
    for name in ("AnimeStudio.CLI.exe", "AnimeStudio.CLI.dll", "AnimeStudio.dll",
                 "Newtonsoft.Json.dll", "AnimeStudio.CLI.deps.json"):
        if name not in critical:
            raise CompressCorpusError(f"decoder output closure is missing {name}")
    for reviewed in expected.get("reviewedFiles", []):
        actual = critical.get(reviewed.get("path"))
        if actual is None or actual["length"] != reviewed.get("length") or actual["sha256"] != reviewed.get("sha256"):
            raise CompressCorpusError(f"reviewed decoder file differs: {reviewed.get('path')}")
    return {"path": str(cli), "outerApphostSha256": digest, "outputClosure": closure}


def _source_bytes(row: dict[str, Any]) -> tuple[bytes, str]:
    path = Path(row["physicalChunkPath"])
    with path.open("rb") as source:
        source.seek(row["offset"])
        raw = source.read(row["length"])
    if len(raw) != row["length"]:
        raise CompressCorpusError(f"short physical slice: {len(raw)} vs {row['length']}")
    md5 = hashlib.md5(raw).hexdigest().upper()
    if md5 != str(row.get("recomputedFileDataMd5", "")).upper():
        raise CompressCorpusError(f"physical slice MD5 mismatch: {md5}")
    return raw, md5


def _decode_and_check(cli: Path, raw: bytes) -> dict[str, Any]:
    if len(raw) < 4:
        raise CompressCorpusError("archive has no count header")
    count = struct.unpack_from("<I", raw)[0]
    table_end = 4 + 4 * count
    if table_end > len(raw):
        raise CompressCorpusError(f"offset table exceeds source: {table_end} > {len(raw)}")
    (REPO_ROOT / "tmp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="extend_compress_", dir=REPO_ROOT / "tmp") as temporary:
        root = Path(temporary)
        source_path = root / "CompressData.bin"
        source_path.write_bytes(raw)
        output = root / "decoded"
        command = [str(cli), "extend-data", "--input", str(source_path), "--output", str(output)]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
        if completed.returncode != 0:
            raise CompressCorpusError(f"decoder failed ({completed.returncode}): {completed.stderr[-500:]}")
        manifest_path = output / "manifest.json"
        if not manifest_path.is_file():
            raise CompressCorpusError("decoder emitted no manifest")
        manifest_raw = manifest_path.read_bytes()
        manifest = json.loads(manifest_raw)
        rows = manifest.get("records")
        source_sha = hashlib.sha256(raw).hexdigest().upper()
        if (manifest.get("format") != "animestudio-extend-data-compress"
                or manifest.get("schemaVersion") != 1
                or manifest.get("recordCount") != count
                or not isinstance(rows, list) or len(rows) != count
                or manifest.get("sourceLength") != len(raw)
                or str(manifest.get("sourceSha256", "")).upper() != source_sha):
            raise CompressCorpusError("decoder manifest header/source mismatch")
        types: Counter[str] = Counter()
        graph_contract = load_graph_contract()
        task_contract = load_task_contract()
        graph_totals: Counter[str] = Counter()
        graph_shapes: Counter[tuple[str, tuple[str, ...]]] = Counter()
        task_totals: Counter[str] = Counter()
        task_types: Counter[str] = Counter()
        behavior_tags: Counter[int] = Counter()
        previous_end = table_end
        for index, record in enumerate(rows):
            offset = struct.unpack_from("<I", raw, 4 + 4 * index)[0]
            if record.get("index") != index or record.get("sourceOffset") != offset or offset != previous_end:
                raise CompressCorpusError(f"record {index} offset continuity mismatch")
            if offset + 8 > len(raw):
                raise CompressCorpusError(f"record {index} header outside source")
            compressed, uncompressed = struct.unpack_from("<II", raw, offset)
            if (record.get("compressedLength") != compressed
                    or record.get("uncompressedLength") != uncompressed):
                raise CompressCorpusError(f"record {index} length manifest mismatch")
            previous_end = offset + 8 + compressed
            if previous_end > len(raw):
                raise CompressCorpusError(f"record {index} exceeds source")
            name = f"{index:06d}.json"
            if record.get("output") != name:
                raise CompressCorpusError(f"record {index} output name mismatch")
            document = json.loads((output / name).read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise CompressCorpusError(f"record {index} output JSON is not an object")
            root_type = document.get("$type", document.get("type"))
            if record.get("rootType") != root_type:
                raise CompressCorpusError(f"record {index} root type mismatch")
            types[str(root_type)] += 1
            graph_receipt = validate_graph(document, label=f"record {index}", contract=graph_contract)
            for field in ("nodeCount", "connectionCount", "idlessNodeCount",
                          "disabledConnectionCount", "canvasGroupCount", "blackboardVariableCount"):
                graph_totals[field] += graph_receipt[field]
            for shape in graph_receipt["nodeShapes"]:
                graph_shapes[(shape["type"], tuple(shape["fields"]))] += shape["count"]
            task_receipt = validate_tasks(document, label=f"record {index}", contract=task_contract)
            for field in ("taskCount", "selectedTaskCount", "unreviewedTaskCount", "typedChildCount"):
                task_totals[field] += task_receipt[field]
            task_totals["maxDepth"] = max(task_totals["maxDepth"], task_receipt["maxDepth"])
            task_types.update(task_receipt["typeCounts"])
            behavior_tags.update(task_receipt["behaviorTagIds"])
        if previous_end != len(raw):
            raise CompressCorpusError(f"archive has {len(raw)-previous_end} unconsumed bytes")
        return {"recordCount": count, "tableEnd": table_end, "lastRecordEnd": previous_end,
                "sourceLength": len(raw), "sourceSha256": source_sha,
                "rootTypes": dict(sorted(types.items())),
                "graphStructure": {"schema": graph_contract["schema"],
                                   "totals": dict(graph_totals),
                                   "nodeShapes": [{"type": tag, "fields": list(fields), "count": count}
                                                  for (tag, fields), count in sorted(graph_shapes.items())]},
                "taskStructure": {"schema": task_contract["schema"],
                                  "totals": dict(task_totals),
                                  "typeCounts": dict(sorted(task_types.items())),
                                  "behaviorTagIds": dict(sorted(behavior_tags.items()))},
                "decoderManifestSha256": hashlib.sha256(manifest_raw).hexdigest().upper()}


def audit(summary_path: Path, ledger_path: Path, expected_input_set: str,
          cli: Path) -> dict[str, Any]:
    summary, provenance, row = _selected_row(summary_path, ledger_path, expected_input_set)
    reader_contract = json.loads(READER_CONTRACT.read_text(encoding="utf-8"))
    if reader_contract.get("schema") != "endfield.extend-data-compress-reader.v1":
        raise CompressCorpusError("unsupported reviewed reader contract")
    closure_before = _decoder_closure(cli)
    cli_receipt = _cli_identity(summary, cli, closure_before, reader_contract)
    raw, md5 = _source_bytes(row)
    framing = _decode_and_check(cli, raw)
    closure_after = _decoder_closure(cli)
    if closure_after["manifestSha256"] != closure_before["manifestSha256"]:
        raise CompressCorpusError("decoder output closure changed during decode")
    return {"schema": SCHEMA, "status": "validated", "source": provenance,
            "virtualPath": VIRTUAL_PATH,
            "physicalSlice": {"chunkPath": row["physicalChunkPath"], "offset": row["offset"],
                              "length": row["length"], "md5": md5},
            "decoder": cli_receipt, "framing": framing,
            "evidenceBoundary": "exact source envelope, Brotli/UTF-16LE/JSON and EOF via selected CLI; reviewed decoded root/node/connection shape, local edge-reference closure, and all currently reached shallow typed task envelopes; nested object/blackboard contents, runtime producer, graph owner, field meaning, execution and blackboard state remain unresolved"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-summary", type=Path, default=REPO_ROOT / "reports/animestudio/vfs_understanding_latest.json")
    parser.add_argument("--outer-ledger", type=Path, default=REPO_ROOT / "reports/animestudio/vfs_understanding_files_latest.jsonl.gz")
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "reports/animestudio/extend_data_compress_current_latest.json")
    args = parser.parse_args()
    try:
        report = audit(args.outer_summary, args.outer_ledger, args.expected_input_set_sha256, args.cli)
    except Exception as exc:
        print(f"ExtendData CompressData audit failed: {type(exc).__name__}: {exc}")
        return 2
    atomic_write_text(args.output, json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"ExtendData CompressData validated: {report['framing']['recordCount']} records; report={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

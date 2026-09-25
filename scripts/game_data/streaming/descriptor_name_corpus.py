"""Sweep authenticated InitChunkData bytes for the descriptor-21 name prefix.

The VFS audit is the sole input-set authority. Every selected logical file is
re-read from its physical chunk and checked against the ledger before the
framing reader sees it. A limited run is diagnostic and cannot publish a
complete-corpus result.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.game_data.streaming.descriptor_names import audit_packed_init
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.streaming-descriptor-name-corpus.v1"
DEFAULT_AUDIT = REPO_ROOT / "reports/animestudio/vfs_understanding_latest.json"
DEFAULT_LEDGER = REPO_ROOT / "reports/animestudio/vfs_understanding_files_latest.jsonl.gz"
DEFAULT_OUTPUT = REPO_ROOT / "reports/chunk_data/descriptor_name_corpus_latest.json"
TOTAL_FIELDS = (
    "groupCount", "descriptor21Groups", "descriptor21Slots",
    "descriptorMajorValidNameSlots", "descriptorMajorExactRootPairs",
    "descriptorMajorExactRootPrefixPairs", "truncatedRootNamePairs",
    "descriptorPairsOutsideRootPrefix", "rootPrefixPairsOutsideDescriptor",
    "rowMajorValidNameSlots", "rowMajorExactRootPairs",
    "rowMajorExactRootPrefixPairs", "rootPairs",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _selected_rows(ledger_path: Path, input_set: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with gzip.open(ledger_path, "rt", encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            row = json.loads(line)
            path = row.get("virtualPath", "")
            if "/InitChunkData_" not in path or not path.endswith(".bytes"):
                continue
            if path in rows:
                raise ValueError(f"ledger line {line_number}: duplicate Init path {path}")
            if row.get("inputSetSha256") != input_set:
                raise ValueError(f"ledger line {line_number}: input-set mismatch for {path}")
            if (row.get("status"), row.get("encrypted"), row.get("blockTypeValue")) != (
                "verified", False, 15
            ):
                raise ValueError(f"ledger line {line_number}: unauthenticated Init row {path}")
            rows[path] = row
    if not rows:
        raise ValueError("current ledger contains no authenticated InitChunkData rows")
    return rows


def audit_descriptor_name_corpus(
    *,
    audit_path: Path = DEFAULT_AUDIT,
    ledger_path: Path = DEFAULT_LEDGER,
    expected_input_set_sha256: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    audit = json.loads(audit_path.read_text(encoding="utf-8-sig"))
    input_set = audit.get("inputSetSha256")
    if not isinstance(input_set, str) or len(input_set) != 64:
        raise ValueError(f"{audit_path}: missing 64-character inputSetSha256")
    if not audit.get("summary", {}).get("fullAuditPassed"):
        raise ValueError(f"{audit_path}: VFS audit did not pass its full source gate")
    if expected_input_set_sha256 is not None and expected_input_set_sha256.upper() != input_set:
        raise ValueError(
            f"expected input-set {expected_input_set_sha256.upper()}, current audit {input_set}"
        )
    source_rows = _selected_rows(ledger_path, input_set)
    if limit is not None and limit <= 0:
        raise ValueError(f"limit must be positive, actual {limit}")
    paths = sorted(source_rows)
    selected_paths = paths if limit is None else paths[:limit]
    files: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for path in selected_paths:
        source = source_rows[path]
        try:
            with Path(source["physicalChunkPath"]).open("rb") as chunk:
                chunk.seek(source["offset"])
                packed = chunk.read(source["length"])
            if len(packed) != source["length"]:
                raise ValueError(
                    f"short physical read: expected {source['length']}, actual {len(packed)}"
                )
            digest = hashlib.md5(packed).hexdigest().upper()
            if digest != source["recomputedFileDataMd5"]:
                raise ValueError(
                    f"physical MD5 mismatch: expected {source['recomputedFileDataMd5']}, actual {digest}"
                )
            row = audit_packed_init(packed, virtual_path=path)
            if row["packedMd5"] != digest:
                raise ValueError("reader packed MD5 differs from authenticated source")
            files.append(row)
        except (OSError, ValueError, KeyError, struct.error) as exc:
            if len(failures) < 25:
                failures.append({"virtualPath": path, "error": str(exc)})
    totals = {field: sum(int(row[field]) for row in files) for field in TOTAL_FIELDS}
    joined = (
        totals["groupCount"] == totals["descriptor21Groups"]
        and totals["descriptor21Slots"] == totals["descriptorMajorValidNameSlots"]
        == totals["descriptorMajorExactRootPrefixPairs"]
    )
    complete = limit is None and len(files) == len(paths) and joined and not failures
    return {
        "schema": SCHEMA,
        "status": "complete-exact-prefix-join" if complete else (
            "bounded-probe" if limit is not None and not failures and joined else "failed-closed"
        ),
        "inputSetSha256": input_set,
        "vfsAuditSha256": _sha256_file(audit_path),
        "vfsLedgerSha256": _sha256_file(ledger_path),
        "allInitFilesInLedger": len(paths),
        "filesSelected": len(selected_paths),
        "filesSucceeded": len(files),
        "totals": totals,
        "failures": failures,
        "files": files,
        "evidenceBoundary": (
            "Each descriptor-21 slot is compared with the same-file root name's first "
            "63 bytes under an exact ID. The fixed slot omits long-name suffixes. "
            "Unjoined root pairs remain separate; this proves stored duplication, "
            "not a runtime component name or object-instantiation receipt."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--expected-input-set-sha256")
    parser.add_argument("--limit", type=int, help="diagnostic first-N probe; cannot certify the corpus")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    result = audit_descriptor_name_corpus(
        audit_path=args.audit,
        ledger_path=args.ledger,
        expected_input_set_sha256=args.expected_input_set_sha256,
        limit=args.limit,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"], result["filesSucceeded"], "/", result["filesSelected"], result["totals"])
    return 0 if result["status"] != "failed-closed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

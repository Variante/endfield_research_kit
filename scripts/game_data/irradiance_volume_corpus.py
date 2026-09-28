"""Current VFS-ledger gate for IrradianceVolume index and room framing.

The outer audit owns file-byte identity. This gate reopens the small index files,
checks their MD5s, and joins their opaque directories to authenticated payload
lengths. It records cross-index word agreement without naming renderer fields.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.game_data.corpus_common import atomic_write_text, validate_provenance
from scripts.game_data import irradiance_volume
from scripts.game_data.irradiance_volume import (
    INDEX_MAGIC_LEGACY_GACHA,
    INDEX_MAGIC_V3_GACHA,
    INDEX_MAGIC_V3_SCENE,
    REGION_HEADER_SIZE,
    REGION_RECORD_SIZE,
    parse_grouped_indexed_payload_framing,
    parse_index_bytes,
    parse_indexed_payload_framing,
    parse_legacy_grouped_indexed_payload_framing,
    read_region_header,
)
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.irradiance-volume-corpus.v1"
BLOCK_TYPE = 14
GACHA_KINDS = ("character", "weapon")


class IrradianceCorpusError(ValueError):
    """A current-corpus provenance or framing check failed."""


def _load_rows(summary_path: Path, ledger_path: Path, expected_input_set: str) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    headers: list[dict[str, Any]] = []
    rows: dict[str, dict[str, Any]] = {}
    with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            row = json.loads(line)
            if row.get("recordType") == "audit_header":
                headers.append(row)
            if row.get("recordType") != "file" or row.get("blockTypeValue") != BLOCK_TYPE:
                continue
            path = row.get("fileName")
            if not isinstance(path, str) or path in rows:
                raise IrradianceCorpusError(f"IV ledger line {line_number}: invalid or duplicate logical path {path!r}")
            if row.get("blockName") != "IV" or row.get("boundaryStatus") != "boundary_verified":
                raise IrradianceCorpusError(f"IV ledger line {line_number}: unverified IV file {path}")
            if str(row.get("inputSetSha256", "")).upper() != expected_input_set.upper():
                raise IrradianceCorpusError(f"IV ledger line {line_number}: input set differs for {path}")
            if row.get("encrypted") is not False:
                raise IrradianceCorpusError(f"IV ledger line {line_number}: encrypted body needs a selected decoder: {path}")
            if not isinstance(row.get("length"), int) or row["length"] <= 0:
                raise IrradianceCorpusError(f"IV ledger line {line_number}: invalid length for {path}")
            if not row.get("recomputedFileDataMd5"):
                raise IrradianceCorpusError(f"IV ledger line {line_number}: missing decoded MD5 for {path}")
            rows[path] = row
    if len(headers) != 1:
        raise IrradianceCorpusError(f"expected one audit header; actual {len(headers)}")
    failures, provenance = validate_provenance(summary, headers[0], ledger_path, expected_input_set)
    if failures:
        raise IrradianceCorpusError(f"outer audit provenance mismatch: {failures[:4]}")
    provenance["readerSha256"] = hashlib.sha256(Path(irradiance_volume.__file__).read_bytes()).hexdigest().upper()
    provenance["corpusGateSha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()
    blocks = [block for block in summary.get("blocks", []) if block.get("blockTypeValue") == BLOCK_TYPE]
    if len(blocks) != 1 or len(rows) != blocks[0].get("declaredFileCount"):
        raise IrradianceCorpusError(f"IV ledger count {len(rows)} differs from block declaration {blocks}")
    return provenance, rows


def _read_file(row: dict[str, Any], *, header_only: bool = False) -> bytes:
    path = Path(row["physicalChunkPath"])
    count = min(row["length"], REGION_HEADER_SIZE) if header_only else row["length"]
    with path.open("rb") as stream:
        stream.seek(row["offset"])
        data = stream.read(count)
    if len(data) != count:
        raise IrradianceCorpusError(f"short physical read: {row['fileName']}: expected {count}, actual {len(data)}")
    if not header_only:
        actual = hashlib.md5(data).hexdigest().upper()
        expected = str(row["recomputedFileDataMd5"]).upper()
        if actual != expected:
            raise IrradianceCorpusError(f"IV MD5 mismatch: {row['fileName']}: expected {expected}, actual {actual}")
    return data


def compare_ordered_records(left: list[tuple[int, ...]], right: list[tuple[int, ...]]) -> dict[str, Any]:
    """Compare index words by authored sequence, retaining disagreement."""
    if not left or len(left) != len(right) or len({len(row) for row in left + right}) != 1:
        return {"equalCount": False, "leftCount": len(left), "rightCount": len(right)}
    width = len(left[0])
    return {
        "equalCount": True,
        "leftCount": len(left),
        "rightCount": len(right),
        "equalByWord": [sum(a[word] == b[word] for a, b in zip(left, right)) for word in range(width)],
        "identicalRecordCount": sum(a == b for a, b in zip(left, right)),
    }


def sweep(summary_path: Path, ledger_path: Path, expected_input_set: str) -> dict[str, Any]:
    """Reframe every current IV index and region against one full VFS audit."""
    provenance, rows = _load_rows(summary_path, ledger_path, expected_input_set)
    indexes = {path: row for path, row in rows.items() if path.endswith("/index.bytes")}
    regions = {path: row for path, row in rows.items() if "/regionIv_room_" in path}
    payloads = {path: row for path, row in rows.items() if "/iv_" in path and path.endswith(".bytes")}
    if len(indexes) + len(regions) + len(payloads) != len(rows):
        raise IrradianceCorpusError("IV ledger has a path outside index, region and iv_ payload families")

    magic_counts: Counter[str] = Counter()
    record_counts: Counter[str] = Counter()
    relations: Counter[str] = Counter()
    index_sources: list[dict[str, Any]] = []
    indexed_payloads: set[str] = set()
    gacha_records: dict[str, list[tuple[int, ...]]] = {}

    for path, row in sorted(indexes.items()):
        data = _read_file(row)
        index = parse_index_bytes(data)
        parent = path.rsplit("/", 1)[0]
        siblings = {name[len(parent) + 1:]: sibling["length"] for name, sibling in payloads.items()
                    if name.startswith(parent + "/") and "/" not in name[len(parent) + 1:]}
        if set(index.filenames) != set(siblings):
            raise IrradianceCorpusError(f"index-to-payload name mismatch: {path}: indexed={index.filenames}, siblings={sorted(siblings)}")
        indexed_payloads.update(parent + "/" + name for name in index.filenames)

        if index.magic == INDEX_MAGIC_V3_SCENE and len(index.filenames) > 1:
            framing = parse_grouped_indexed_payload_framing(data, siblings)
            records = [record.words for group in framing.groups for record in group.records]
        elif index.magic == INDEX_MAGIC_LEGACY_GACHA:
            framing = parse_legacy_grouped_indexed_payload_framing(data, siblings)
            records = [record.words for group in framing.groups for record in group.records]
        else:
            if len(index.filenames) != 1:
                raise IrradianceCorpusError(f"unsupported IV index layout: {path}")
            framing = parse_indexed_payload_framing(data, siblings[index.filenames[0]])
            records = [record.words for record in framing.records]

        magic = f"0x{index.magic:08X}"
        magic_counts[magic] += 1
        record_counts[magic] += len(records)
        if index.magic == INDEX_MAGIC_V3_SCENE:
            relations["sceneW4EqualsW5PlusW6"] += sum(r[4] == r[5] + r[6] for r in records)
            relations["sceneW3LessThanW5"] += sum(r[3] < r[5] for r in records)
        elif index.magic == INDEX_MAGIC_V3_GACHA:
            relations["gachaW3EqualsW4PlusW5"] += sum(r[3] == r[4] + r[5] for r in records)
            for kind in GACHA_KINDS:
                if path.endswith(f"/gacha/{kind}/v3/index.bytes"):
                    if kind in gacha_records:
                        raise IrradianceCorpusError(f"multiple gacha {kind} V3 indexes")
                    gacha_records[kind] = records
        index_sources.append({"path": path, "md5": row["recomputedFileDataMd5"], "magic": magic,
                              "filenameCount": len(index.filenames), "recordCount": len(records)})

    if indexed_payloads != set(payloads):
        raise IrradianceCorpusError(f"unindexed IV payloads: {sorted(set(payloads) - indexed_payloads)[:8]}")
    for path, row in sorted(regions.items()):
        header = read_region_header(io.BytesIO(_read_file(row, header_only=True)))
        expected = REGION_HEADER_SIZE + header.record_count * REGION_RECORD_SIZE
        if row["length"] != expected:
            raise IrradianceCorpusError(f"room grid length mismatch: {path}: expected {expected}, actual {row['length']}")

    if set(gacha_records) != set(GACHA_KINDS):
        raise IrradianceCorpusError(
            f"V3 Gacha index pair is incomplete: available={sorted(gacha_records)}"
        )
    pair = compare_ordered_records(gacha_records["character"], gacha_records["weapon"])
    if not pair["equalCount"] or any(
        pair["equalByWord"][word] != pair["leftCount"] for word in (0, 1, 6, 7)
    ):
        raise IrradianceCorpusError(
            "V3 Gacha stored-key relation changed: expected full agreement "
            f"at words 0,1,6,7; actual={pair}"
        )
    return {
        "schema": SCHEMA,
        "status": "validated",
        "evidenceBoundary": "exact index and room framing against a current full VFS ledger; cross-index word equality is structural only",
        "source": provenance,
        "summary": {"ivFiles": len(rows), "indexes": len(indexes), "payloads": len(payloads),
                    "rooms": len(regions), "magicCounts": dict(sorted(magic_counts.items())),
                    "recordCounts": dict(sorted(record_counts.items())), "relations": dict(sorted(relations.items()))},
        "gachaV3Pair": pair,
        "indexSources": index_sources,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer-summary", type=Path, default=REPO_ROOT / "reports/animestudio/vfs_understanding_latest.json")
    parser.add_argument("--outer-ledger", type=Path, default=REPO_ROOT / "reports/animestudio/vfs_understanding_files_latest.jsonl.gz")
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "reports/irradiance/volume_corpus_latest.json")
    args = parser.parse_args()
    try:
        report = sweep(args.outer_summary, args.outer_ledger, args.expected_input_set_sha256)
    except Exception as exc:
        failure = {
            "schema": SCHEMA,
            "status": "failed",
            "expectedInputSetSha256": args.expected_input_set_sha256.upper(),
            "firstFailure": f"{type(exc).__name__}: {exc}",
        }
        atomic_write_text(args.output, json.dumps(failure, indent=2) + "\n")
        print(f"irradiance corpus failed: {failure['firstFailure']}; report={args.output}")
        return 2
    atomic_write_text(args.output, json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"irradiance corpus validated: {report['summary']}; report={args.output}")
    return 0


if __name__ == "__main__":
    if not __package__:
        raise SystemExit("Run as: python -m scripts.game_data.irradiance_volume_corpus")
    raise SystemExit(main())

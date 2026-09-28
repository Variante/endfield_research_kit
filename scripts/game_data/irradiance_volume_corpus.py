"""Current VFS-ledger gate for IrradianceVolume index and room framing.

The outer audit owns file-byte identity. This gate reopens the small index files,
checks their MD5s, and joins their opaque directories to authenticated payload
lengths. It records cross-index word agreement without naming renderer fields.

``python -m scripts.game_data.irradiance_volume_corpus
--expected-input-set-sha256 INPUT_SET_SHA256`` checks every current IV index
and room against the full authenticated VFS ledger (``--outer-summary`` and
``--outer-ledger`` default to the ``reports/animestudio/vfs_understanding_*``
pair) and writes ``reports/irradiance/volume_corpus_latest.json``. It reports
directory arithmetic and the ordered V3 Gacha character/weapon word agreement
without assigning those words a renderer meaning. Report schema v2 adds
``indexWordRelations`` and keeps every v1 key; a failed run writes
``status: failed`` with ``firstFailure`` and the structured ``failures``.

The two installed V3 Gacha ``character`` and ``weapon`` indexes have the same
ordered record count, and every positional pair agrees on anonymous words 0,
1, 6 and 7 while interval offsets and lengths differ; the gate fails if that
agreement changes. This is a shared stored key and order (structural), not
evidence that the records load together, that the words are coordinates, or
that the payloads hold the same lighting.

Index-word additive relations (``indexWordRelations``, exact stored
arithmetic, unnamed). ``index_word_relations`` counts, per index magic, the
records with ``w4 = w5 + w6`` and with ``w3 = w4 + w5``, and fails unless:
every scene V3 (``0x03000003``) record has ``w4 = w5 + w6``; every Gacha V3
(``0x03000002``) record has ``w3 = w4 + w5``; neither relation holds for every
legacy (``0x01000043``) record; and the scene counterexamples to an interval
split are still present (some ``w4`` exceeds the interval length ``w3`` and
some ``w3`` is shorter than ``w5``). Each failure names the check, the magic
and the first counterexample index path, record ordinal and words. The
relations are not compression sizes, texture roles, selection rules or
physical splits; no consumer names the parts.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from scripts.game_data.corpus_common import atomic_write_text, validate_provenance
from scripts.game_data import irradiance_volume
from scripts.game_data.irradiance_volume import (
    INDEX_MAGIC_LEGACY_GACHA,
    INDEX_MAGIC_V3_GACHA,
    INDEX_MAGIC_V3_SCENE,
    REGION_HEADER_SIZE,
    REGION_RECORD_SIZE,
    LegacyIndexedPayloadRange,
    parse_grouped_indexed_payload_framing,
    parse_index_bytes,
    parse_indexed_payload_framing,
    parse_legacy_grouped_indexed_payload_framing,
    read_region_header,
)
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.irradiance-volume-corpus.v2"
BLOCK_TYPE = 14
GACHA_KINDS = ("character", "weapon")
W4_SUM = "word4EqualsWord5PlusWord6"
W3_SUM = "word3EqualsWord4PlusWord5"
# The one additive relation each V3 magic holds for every record; legacy holds neither.
CHECKED_RELATIONS = {INDEX_MAGIC_V3_SCENE: W4_SUM, INDEX_MAGIC_V3_GACHA: W3_SUM}


class IrradianceCorpusError(ValueError):
    """A current-corpus provenance, framing or stored-relation check failed."""

    def __init__(self, message: str, failures: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.failures = list(failures or [])


def _magic_name(magic: int) -> str:
    return f"0x{magic:08X}"


def _relation_holds(name: str, words: tuple[int, ...]) -> bool:
    if len(words) < 7:
        return False
    if name == W4_SUM:
        return words[4] == words[5] + words[6]
    return words[3] == words[4] + words[5]


def index_word_relations(
    records: Iterable[tuple[int, str, int, tuple[int, ...], tuple[int, int]]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Count and check the stored additive relations of every index directory record.

    ``records`` yields ``(magic, indexPath, recordOrdinal, words, intervalWordPair)``.
    Returns the per-magic families and every failed check (empty when all hold).
    """
    grouped: dict[int, list[tuple[str, int, tuple[int, ...], tuple[int, int]]]] = {}
    for magic, path, ordinal, words, pair in records:
        grouped.setdefault(magic, []).append((path, ordinal, tuple(words), tuple(pair)))
    families: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []

    def fail(check: str, magic: int, expected: Any, actual: Any, sample: Any = None) -> None:
        failures.append({"check": check, "magic": _magic_name(magic), "expected": expected,
                         "actual": actual, "firstCounterexample": sample})

    def sample(row: tuple[str, int, tuple[int, ...], tuple[int, int]]) -> dict[str, Any]:
        return {"indexPath": row[0], "record": row[1], "words": list(row[2])}

    for magic in (INDEX_MAGIC_V3_SCENE, INDEX_MAGIC_V3_GACHA):
        if not grouped.get(magic):
            fail(f"{CHECKED_RELATIONS[magic]}:family-present", magic, "at least one record", 0)
    for magic, rows in sorted(grouped.items()):
        widths = sorted({len(words) for _path, _ordinal, words, _pair in rows})
        pairs = sorted({pair for _path, _ordinal, _words, pair in rows})
        family: dict[str, Any] = {
            "indexCount": len({path for path, _ordinal, _words, _pair in rows}),
            "recordCount": len(rows),
            "recordWidthWords": widths[0] if len(widths) == 1 else widths,
            W4_SUM: sum(_relation_holds(W4_SUM, words) for _p, _o, words, _i in rows),
            W3_SUM: sum(_relation_holds(W3_SUM, words) for _p, _o, words, _i in rows),
            "payloadIntervalWordPair": list(pairs[0]) if len(pairs) == 1 else [list(p) for p in pairs],
        }
        if len(widths) != 1 or len(pairs) != 1:
            fail("record-shape", magic, "one record width and interval word pair",
                 {"widths": widths, "pairs": [list(p) for p in pairs]})
        checked = CHECKED_RELATIONS.get(magic)
        if checked is not None and family[checked] != len(rows):
            broken = next(row for row in rows if not _relation_holds(checked, row[2]))
            fail(checked, magic, len(rows), family[checked], sample(broken))
        if checked is None:
            for name in (W4_SUM, W3_SUM):
                if rows and family[name] == len(rows):
                    fail(f"{name}:not-universal", magic, f"fewer than {len(rows)}", family[name])
        if magic == INDEX_MAGIC_V3_SCENE:
            longer = [row for row in rows if row[2][4] > row[2][row[3][1]]]
            equal = sum(row[2][4] == row[2][row[3][1]] for row in rows)
            shorter_than_w5 = sum(row[2][row[3][1]] < row[2][5] for row in rows)
            family["word4VsIntervalLengthWord3"] = {
                "greater": len(longer), "equal": equal, "less": len(rows) - len(longer) - equal,
            }
            family["intervalLengthWord3LessThanWord5"] = shorter_than_w5
            if not longer or not shorter_than_w5:
                fail("scene-interval-split-counterexamples", magic,
                     "some w4 > w3 and some w3 < w5",
                     {"word4GreaterThanWord3": len(longer), "word3LessThanWord5": shorter_than_w5})
        families[_magic_name(magic)] = family
    return families, failures


def _interval_word_pair(record: Any) -> tuple[int, int]:
    """The directory words the reader exposes as the proven payload interval."""
    pair = (7, 8) if isinstance(record, LegacyIndexedPayloadRange) else (2, 3)
    if (record.words[pair[0]], record.words[pair[1]]) != (record.offset, record.length):
        raise IrradianceCorpusError(f"reader interval words moved: expected words {pair}")
    return pair


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
    word_records: list[tuple[int, str, int, tuple[int, ...], tuple[int, int]]] = []

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
            ranges = [record for group in framing.groups for record in group.records]
        elif index.magic == INDEX_MAGIC_LEGACY_GACHA:
            framing = parse_legacy_grouped_indexed_payload_framing(data, siblings)
            ranges = [record for group in framing.groups for record in group.records]
        else:
            if len(index.filenames) != 1:
                raise IrradianceCorpusError(f"unsupported IV index layout: {path}")
            framing = parse_indexed_payload_framing(data, siblings[index.filenames[0]])
            ranges = list(framing.records)
        records = [record.words for record in ranges]
        word_records.extend(
            (index.magic, path, ordinal, record.words, _interval_word_pair(record))
            for ordinal, record in enumerate(ranges)
        )

        magic = _magic_name(index.magic)
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
    families, relation_failures = index_word_relations(word_records)
    if relation_failures:
        first = relation_failures[0]
        raise IrradianceCorpusError(
            f"index-word relation changed: {first['check']} for {first['magic']}: "
            f"expected {first['expected']!r}, actual {first['actual']!r}, "
            f"first counterexample {first['firstCounterexample']}",
            relation_failures,
        )
    return {
        "schema": SCHEMA,
        "status": "validated",
        "evidenceBoundary": "exact index and room framing against a current full VFS ledger; exact stored index-word arithmetic with no field names; cross-index word equality is structural only",
        "source": provenance,
        "summary": {"ivFiles": len(rows), "indexes": len(indexes), "payloads": len(payloads),
                    "rooms": len(regions), "magicCounts": dict(sorted(magic_counts.items())),
                    "recordCounts": dict(sorted(record_counts.items())), "relations": dict(sorted(relations.items()))},
        "indexWordRelations": {
            "checked": {_magic_name(magic): name for magic, name in sorted(CHECKED_RELATIONS.items())},
            "families": families,
        },
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
            "failures": getattr(exc, "failures", []),
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

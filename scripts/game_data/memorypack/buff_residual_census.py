"""Rank unresolved Buff storage cohorts from a source-authenticated census.

The recorded complete family report owns admission. This tool excludes its
whole-root exact rows before counting residual obligations and union cohorts;
it does not reuse the legacy all-row ``namedSchemaReceipts`` denominator.
All logical files are rejoined to current exported bytes. The installed source
receipt is checked before and after the scan, while parser changes remain a
separate future family replay obligation. Nothing here admits a new schema.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import ROOT, canonical_json_sha256, resolve_installed_native_inputs, sha256_file
from scripts.game_data.jsondata_source_provenance import authenticate_current_jsondata_receipt
from scripts.game_data.memorypack.corpus_gate import _fingerprint

SCHEMA = "endfield.buff-residual-census.v1"


def summarize_residuals(report: dict[str, Any], *, export_root: Path) -> dict[str, Any]:
    """Validate complete identities/bytes and count distinct residual sources."""
    rows = report.get("files")
    summary = report.get("summary") or {}
    if (report.get("format") != "animestudio-buffdata-current-vfs-corpus"
            or report.get("status") != "complete" or report.get("publicationEligible") is not True
            or not isinstance(rows, list) or summary.get("filesSelected") != len(rows)
            or summary.get("filesFailed") != 0 or summary.get("filesUnsupported") != 0):
        raise ValueError("buffResidualCensus:complete-family-required")
    if canonical_json_sha256([{"identity": row.get("identity"), "logicalSha256": row.get("logicalSha256")}
                             for row in rows]) != report.get("identitySetSha256"):
        raise ValueError("buffResidualCensus:identity-set-mismatch")
    names: set[str] = set()
    obligations: dict[tuple[str, str], set[str]] = defaultdict(set)
    first: dict[tuple[str, str], set[str]] = defaultdict(set)
    unions: dict[tuple[str, int], set[str]] = defaultdict(set)
    union_instances: Counter[tuple[str, int]] = Counter()
    residuals = []
    exact = 0
    for row in rows:
        identity = row.get("identity") or {}
        source = identity.get("virtualPath", "")
        parts = PurePosixPath(source).parts
        if ("\\" in source or "/".join(parts) != source
                or len(parts) != 4 or parts[:3] != ("Data", "Json", "BuffData")
                or not source.endswith(".json") or source != identity.get("fileName")
                or source in names or identity.get("inputSetSha256") != report.get("inputSetSha256")
                or identity.get("status") != "verified" or identity.get("boundaryStatus") != "boundary_verified"):
            raise ValueError(f"buffResidualCensus:logical-identity:{source}")
        names.add(source)
        path = export_root / "game" / "Json" / "BuffData" / parts[-1]
        data = path.read_bytes()
        if len(data) != identity.get("length") or hashlib.sha256(data).hexdigest().upper() != row.get("logicalSha256"):
            raise ValueError(f"buffResidualCensus:logical-byte-join:{source}")
        if type(row.get("wholeSchemaExact")) is not bool:
            raise ValueError(f"buffResidualCensus:exact-status:{source}")
        if row["wholeSchemaExact"]:
            exact += 1
            continue
        candidates = row.get("candidates") or []
        source_obligations = set()
        source_first = set()
        source_unions = Counter()
        for candidate in candidates:
            receipt = candidate.get("namedSchemaReceipt") or {}
            blockers = receipt.get("blockers") or []
            if not blockers:
                blockers = [{"field": "root", "category": "no-composed-naming-receipt"}]
            for blocker in blockers:
                key = (blocker["field"], blocker["category"])
                source_obligations.add(key)
                obligations[key].add(source)
            key = (blockers[0]["field"], blockers[0]["category"])
            first[key].add(source)
            source_first.add(key)
            for owner in ("currentEventPrefix", "currentRootContinuation"):
                profile = candidate.get(owner) or {}
                fields = profile.get("namedFields") or []
                for record in profile.get("completedRecords") or []:
                    if record.get("kind") != "union":
                        continue
                    owners = [field["name"] for field in fields
                              if field["start"] <= record["start"] < record["end"] <= field["end"]]
                    if len(owners) != 1:
                        continue  # Nested/unfinished ownership is not assigned by proximity.
                    key = (owners[0], record["tag"])
                    source_unions[key] += 1
        for key, count in source_unions.items():
            unions[key].add(source)
            union_instances[key] += count
        residuals.append({"source": source, "logicalSha256": row["logicalSha256"],
                          "length": len(data), "candidateCount": len(candidates),
                          "firstObligations": [{"field": f, "category": c} for f, c in sorted(source_first)],
                          "obligations": [{"field": f, "category": c} for f, c in sorted(source_obligations)],
                          "completedUnionCohorts": [{"field": f, "tag": t, "instances": n}
                                                     for (f, t), n in sorted(source_unions.items())]})
    if summary.get("filesWholeSchemaExact") != exact:
        raise ValueError("buffResidualCensus:exact-count-mismatch")
    def rank(groups, *, tags=False):
        result = []
        for (field, value), sources in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
            item = {"field": field, "tag" if tags else "category": value,
                    "distinctFiles": len(sources), "examples": sorted(sources)[:8]}
            if tags:
                item["instances"] = union_instances[(field, value)]
            result.append(item)
        return result
    return {"schema": SCHEMA, "status": "source-authenticated-recorded-frontier",
            "inputSetSha256": report["inputSetSha256"], "publicationEligible": False,
            "summary": {"filesChecked": len(rows), "exactRootsExcluded": exact,
                        "residualFiles": len(residuals), "firstObligationCohorts": len(first),
                        "completedUnionCohorts": len(unions)},
            "firstObligations": rank(first), "allObligations": rank(obligations),
            "completedUnionCohorts": rank(unions, tags=True), "files": residuals,
            "evidenceBoundary": "Counts concern unresolved files in the recorded complete family receipt. "
                "All original logical bytes are rejoined, but changed readers are not replayed here. "
                "Cohorts overlap; completed unions are stored spans, not first-stop claims, execution, "
                "or predicted whole-file closures. Only the complete family gate can admit new exact roots."}


def build_census(*, summary_path: Path, ledger_path: Path, export_root: Path,
                 buff_report: Path | None = None, replay_no_positive: bool = False) -> dict[str, Any]:
    summary_pin = _fingerprint(summary_path)
    registry = json.loads(summary_path.read_bytes())
    gameassembly, metadata = resolve_installed_native_inputs()
    paths = {"GameAssembly.dll": str(gameassembly), "global-metadata.dat": str(metadata)}
    args = {"summary_path": summary_path, "ledger_path": ledger_path,
            "expected_summary_sha256": summary_pin["sha256"], "native_sources": paths,
            "native_inputs": {name: sha256_file(Path(path)).upper() for name, path in paths.items()}}
    before = authenticate_current_jsondata_receipt(**args)
    pin = registry.get("provenance", {}).get("familyReports", {}).get("BuffData") or {}
    selected = Path(pin.get("path", ""))
    if not selected.is_absolute():
        selected = ROOT / selected
    if buff_report is not None and buff_report.resolve() != selected.resolve():
        raise ValueError("buffResidualCensus:report-not-selected-by-current-registry")
    actual = _fingerprint(selected)
    if any(actual[key] != pin.get(key) for key in ("length", "sha256")):
        raise ValueError("buffResidualCensus:family-report-byte-join")
    report = json.loads(selected.read_bytes())
    if report.get("inputSetSha256") != before["inputSetSha256"]:
        raise ValueError("buffResidualCensus:family-source-input-set")
    result = summarize_residuals(report, export_root=export_root)
    if replay_no_positive:
        # This is a bounded development replay, not a second family gate. The
        # historical exact roots were already excluded from its denominator.
        from scripts.game_data.memorypack import buff_root_no_positive as root
        native = root.validate_current_native_contract()
        if native.get("status") != "validated":
            raise ValueError(f"buffResidualCensus:root-native:{native.get('status')}:{native.get('detail')}")
        receipts, refusals = [], []
        for row in report["files"]:
            if row["wholeSchemaExact"] or not root.is_no_positive_candidate(row, length=row["identity"]["length"]):
                continue
            source = row["identity"]["virtualPath"]
            data = (export_root / "game" / "Json" / "BuffData" / PurePosixPath(source).name).read_bytes()
            try:
                receipt = root.decode_no_positive_buff(data, source=source,
                    expected_sha256=row["logicalSha256"], native_validation=native)
            except ValueError as exc:
                refusals.append({"source": source, "diagnostic": str(exc)})
            else:
                receipts.append(receipt)
        result["currentReaderReplay"] = {"publicationEligible": False,
            "candidateFiles": len(receipts) + len(refusals), "wholeRootReceipts": len(receipts),
            "refusedFiles": len(refusals), "nativeValidation": native,
            "receipts": receipts, "refusals": refusals,
            "evidenceBoundary": "Fresh native-gated forward root receipts from residual source bytes. "
                "Publication requires the complete Buff gate and canonical registry replay."}
    if _fingerprint(selected) != actual or authenticate_current_jsondata_receipt(**args) != before:
        raise ValueError("buffResidualCensus:source-drift")
    result["provenance"] = {"sourceReceipt": before, "familyReport": actual,
                            "censusReader": _fingerprint(Path(__file__))}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=ROOT / "reports/animestudio/jsondata_current_latest.json")
    parser.add_argument("--ledger", type=Path, default=ROOT / "reports/animestudio/jsondata_current_files_latest.jsonl.gz")
    parser.add_argument("--export-root", type=Path, default=ROOT / "export_full")
    parser.add_argument("--buff-report", type=Path)
    parser.add_argument("--replay-no-positive", action="store_true",
                        help="replay residual candidates through the current shared root reader; no publication")
    parser.add_argument("--output-json", type=Path, default=ROOT / "reports/game_data/buff_residual_census_latest.json")
    args = parser.parse_args()
    report = build_census(summary_path=args.summary, ledger_path=args.ledger,
                          export_root=args.export_root, buff_report=args.buff_report,
                          replay_no_positive=args.replay_no_positive)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    if "currentReaderReplay" in report:
        print(json.dumps({key: report["currentReaderReplay"][key]
                          for key in ("candidateFiles", "wholeRootReceipts", "refusedFiles")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

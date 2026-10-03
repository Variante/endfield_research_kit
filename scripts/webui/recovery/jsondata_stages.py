"""Check Recovery JsonData L2 declarations against the authenticated registry.

This is an optional publication preflight, not a payload reader. A missing
registry leaves general VFS volume publication available. Once a registry is
present, stale receipt inputs, an unpinned ledger, malformed identities, or a
declaration mismatch refuse publication. The registry owns byte/reader proof;
this check authenticates its receipts and partitions its per-file terminal
states by the exact Recovery path regexes, including composite families.
Saved summary/ledger and receipt pins are checked before and after the row
scan; the outer build owns the explicit authenticated AnimeStudio CLI pin.

Run: python -m scripts.webui.recovery.jsondata_stages
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

if __package__ in {None, ""}:
    raise SystemExit("Run this maintained entry point as: python -m scripts.webui.recovery.jsondata_stages")

from scripts.common import REPORTS_DIR, write_canonical_json
from scripts.game_data.game_file_store import locate_game_folder
from scripts.source_paths import ExportLayout
from scripts.game_data.memorypack.corpus_gate import (
    CensusGateError, _discover_blc_paths, _fingerprint, _snapshot_pinned_files,
)

DEFAULT_SUMMARY = REPORTS_DIR / "animestudio/jsondata_current_latest.json"
DEFAULT_LEDGER = REPORTS_DIR / "animestudio/jsondata_current_files_latest.jsonl.gz"
DEFAULT_OUTPUT = REPORTS_DIR / "game_data/recovery_jsondata_stages_latest.json"
SCHEMA = "endfield.recovery-jsondata-stages.v1"
VALIDATOR = "jsondata-stage-consistency"
REGISTRY_FORMAT = "endfield-jsondata-current-corpus-v1"
HEX32 = re.compile(r"[0-9A-Fa-f]{32}")
HEX64 = re.compile(r"[0-9A-Fa-f]{64}")
MAX_DIAGNOSTICS = 20


def _diagnostic(check: str, source: Any, expected: Any, actual: Any, **extra: Any) -> dict[str, Any]:
    if isinstance(actual, str):
        actual = actual[:240]
    return {"validator": VALIDATOR, "check": check, "source": str(source),
            "expected": expected, "actual": actual, **extra}


def describe_failure(result: dict[str, Any]) -> str:
    first = result["diagnostics"][0]
    return (f"{VALIDATOR}: {result['status']}; {first['check']}: {first['source']}; "
            f"expected {first['expected']!r}, actual {first['actual']!r}")


def _receipt_snapshot(provenance: dict[str, Any], *, summary_pin: dict[str, Any],
                      ledger_path: Path) -> dict[str, Any]:
    """Authenticate the same saved receipt pins before and after the row scan."""
    checked: dict[str, Any] = {
        "summary": _snapshot_pinned_files([summary_pin], label="current registry summary"),
    }
    for role in ("outer", "ledger", "registry"):
        pin = provenance.get(role)
        checked[role] = _snapshot_pinned_files([pin] if isinstance(pin, dict) else [],
                                             label=f"provenance.{role}")
    for role in ("sourceFingerprints", "buildFingerprints"):
        pins = provenance.get(role)
        if not isinstance(pins, list) or not all(isinstance(pin, dict) for pin in pins):
            raise CensusGateError("missing-fingerprints", source=f"provenance.{role}",
                                  expected="non-empty fingerprint list", actual=type(pins).__name__)
        checked[role] = _snapshot_pinned_files(pins, label=f"provenance.{role}")
    family_reports = provenance.get("familyReports")
    if (not isinstance(family_reports, dict)
            or not all(isinstance(pin, dict) for pin in family_reports.values())):
        raise CensusGateError("family-receipts-missing", source="provenance.familyReports",
                              expected="receipt object", actual=type(family_reports).__name__)
    checked["familyReports"] = (_snapshot_pinned_files(list(family_reports.values()),
                                 label="provenance.familyReports") if family_reports else [])
    output = provenance.get("outputFiles")
    pin = {**output, "path": ledger_path.as_posix()} if isinstance(output, dict) else {}
    checked["outputFiles"] = _snapshot_pinned_files([pin], label="provenance.outputFiles")
    selected_replay = provenance.get("buffSelectedRootReplayInputs")
    if selected_replay is not None:
        if not isinstance(selected_replay, list) or not all(isinstance(pin, dict) for pin in selected_replay):
            raise CensusGateError("buff-selected-root-replay-pins-invalid", source="provenance.buffSelectedRootReplayInputs",
                                  expected="current replay input fingerprint list", actual=type(selected_replay).__name__)
        checked["buffSelectedRootReplayInputs"] = _snapshot_pinned_files(selected_replay, label="Buff selected root registry replay")
    return checked


def _stale_receipt(result: dict[str, Any], exc: Exception, summary_path: Path) -> dict[str, Any]:
    result["status"] = "stale"
    result["families"] = []
    if isinstance(exc, CensusGateError):
        d = exc.diagnostic
        result["diagnostics"] = [_diagnostic(d["code"], d["source"], d["expected"], d["actual"])]
    else:
        result["diagnostics"] = [_diagnostic("receipt-readable", summary_path,
                                              "current pinned receipt inputs", str(exc))]
    return result


def check_jsondata_stages(
    block: dict[str, Any], *, summary_path: Path = DEFAULT_SUMMARY,
    ledger_path: Path = DEFAULT_LEDGER, export_root: Path | None = None,
) -> dict[str, Any]:
    """Return verified/missing/stale/mismatched with bounded diagnostics.

    Missing means the optional registry summary is absent. A present summary
    with missing dependencies is stale; it never becomes an optional skip.
    No file count or schema-decoded claim comes from a family-name match.
    """
    result: dict[str, Any] = {"schema": SCHEMA, "status": "missing", "diagnostics": [],
                             "families": [], "sources": {"summary": summary_path.as_posix(),
                                                         "ledger": ledger_path.as_posix()}}
    if not summary_path.is_file():
        result["diagnostics"] = [_diagnostic("optional-summary-missing", summary_path,
                                              "current JsonData registry", "missing")]
        return result
    result["status"] = "mismatched"
    try:
        summary_pin = _fingerprint(summary_path)
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except CensusGateError as exc:
        return _stale_receipt(result, exc, summary_path)
    except (OSError, UnicodeError, ValueError) as exc:
        result["diagnostics"] = [_diagnostic("summary-readable", summary_path, "JSON object", str(exc))]
        return result
    if not isinstance(summary, dict):
        result["diagnostics"] = [_diagnostic("summary-readable", summary_path, "JSON object", type(summary).__name__)]
        return result
    result["sources"]["summarySha256"] = summary_pin["sha256"]
    counts = summary.get("summary")
    provenance = summary.get("provenance")
    for check, expected, actual in (
        ("summary-format", [REGISTRY_FORMAT, 1], [summary.get("format"), summary.get("schemaVersion")]),
        ("summary-status", "complete", summary.get("status")),
        ("summary-counts", "object", type(counts).__name__),
        ("summary-provenance", "object", type(provenance).__name__),
    ):
        if actual != expected and not (expected == "object" and actual == "dict"):
            result["diagnostics"].append(_diagnostic(check, summary_path, expected, actual))
    if result["diagnostics"]:
        return result
    if (any(type(counts.get(key)) is not int or counts[key] <= 0
            for key in ("filesSelected", "filesJoined", "familyCount"))
            or type(counts.get("logicalBytes")) is not int or counts["logicalBytes"] < 0):
        result["diagnostics"] = [_diagnostic("summary-count-values", summary_path,
                                              "positive file/family counts and nonnegative logical bytes", "malformed counts")]
        return result
    if not isinstance(counts.get("families"), dict) or not isinstance(counts.get("statusCounts"), dict):
        result["diagnostics"] = [_diagnostic("summary-tallies", summary_path,
                                              "families and statusCounts objects", "missing or malformed")]
        return result
    input_set = summary.get("inputSetSha256")
    if not isinstance(input_set, str) or not HEX64.fullmatch(input_set):
        result["diagnostics"] = [_diagnostic("summary-input-set", summary_path, "SHA-256", input_set)]
        return result
    if export_root is not None:
        # The corpus's historical exportRoot field records its Json source
        # directory; Recovery selects the containing export tree. Use the same
        # marked-layout resolver as the producer, never strip arbitrary parents
        # or admit another game folder or Json subfamily.
        layout = ExportLayout(export_root)
        expected_json_root = layout.json_dir.resolve()
        recorded = summary.get("exportRoot")
        try:
            recorded_path = Path(recorded).resolve() if isinstance(recorded, str) and recorded else None
            located = locate_game_folder(recorded_path) if recorded_path is not None else None
            matched = (located is not None and located[0].resolve() == layout.root.resolve()
                       and located[1].casefold() == "json" and recorded_path == expected_json_root)
        except (OSError, ValueError):
            matched = False
        if not matched:
            result["status"] = "stale"
            result["diagnostics"] = [_diagnostic("summary-export-root", summary_path,
                expected_json_root.as_posix(), recorded, selectedExportRoot=layout.root.resolve().as_posix())]
            return result
    # Reuse the installed-corpus pin verifier. The optional preflight must not
    # bless an old producer, native build, metadata catalog, or family receipt.
    try:
        receipts_start = _receipt_snapshot(provenance, summary_pin=summary_pin, ledger_path=ledger_path)
        result["sources"]["ledgerSha256"] = receipts_start["outputFiles"][0]["sha256"]
        outer_path = Path(provenance["outer"]["path"])
        outer = json.loads(outer_path.read_text(encoding="utf-8"))
        if not isinstance(outer, dict):
            raise CensusGateError("outer-schema", source=outer_path.as_posix(),
                                  expected="audit object", actual=type(outer).__name__)
        if (outer.get("format") != "animestudio-vfs-boundary-audit"
                or outer.get("schemaVersion") != 1
                or outer.get("inputSetSha256") != input_set
                or not isinstance(outer.get("summary"), dict)
                or outer["summary"].get("fullAuditPassed") is not True
                or not isinstance(outer.get("publication"), dict)
                or str(outer["publication"].get("ledgerSha256", "")).upper()
                    != str(provenance["ledger"].get("sha256", "")).upper()):
            raise CensusGateError("outer-input-set", source=outer_path.as_posix(),
                                  expected="complete v1 VFS audit with the registry input set and pinned outer ledger",
                                  actual={"format": outer.get("format"), "schemaVersion": outer.get("schemaVersion"),
                                          "inputSetSha256": outer.get("inputSetSha256")})
        for role in ("sourceFingerprints", "buildFingerprints"):
            pins = outer.get(role)
            if not isinstance(pins, list) or not all(isinstance(pin, dict) for pin in pins):
                raise CensusGateError("outer-fingerprints-missing", source=f"outer.{role}",
                                      expected="current fingerprint list", actual=type(pins).__name__)
            if _snapshot_pinned_files(pins, label=f"outer.{role}") != receipts_start[role]:
                raise CensusGateError("outer-registry-fingerprints-mismatch", source=f"outer.{role}",
                                      expected="the registry's authenticated outer input pins", actual="pins differ")
        stream_tools = [pin for pin in receipts_start["buildFingerprints"]
                        if Path(pin["path"]).name.lower() == "animestudio.cli.exe"]
        if len(stream_tools) != 1:
            raise CensusGateError("outer-cli-fingerprint-missing", source="outer.buildFingerprints",
                                  expected="one authenticated AnimeStudio.CLI.exe", actual=len(stream_tools))
        result["sources"]["streamToolFingerprint"] = stream_tools[0]
        with gzip.open(Path(provenance["ledger"]["path"]), "rt", encoding="utf-8") as stream:
            header = json.loads(stream.readline())
        if (not isinstance(header, dict) or header.get("recordType") != "audit_header"
                or header.get("schemaVersion") != 1 or header.get("inputSetSha256") != input_set):
            raise CensusGateError("outer-ledger-header", source=provenance["ledger"]["path"],
                                  expected="v1 audit header with the registry input set", actual="missing or mismatched header")
        for role in ("primaryAssets", "fallbackAssets", "sourceFingerprints", "buildFingerprints"):
            if header.get(role) != outer.get(role):
                raise CensusGateError("outer-ledger-header", source=provenance["ledger"]["path"],
                                      expected=f"header {role} matches the pinned audit", actual="mismatched header")
        current_blcs = _discover_blc_paths(outer)
        if current_blcs != provenance.get("blcPaths"):
            raise CensusGateError("blc-path-set-mismatch", source=outer_path.as_posix(),
                                  expected="the saved catalog path set", actual="installed catalog path set changed")
    except (CensusGateError, OSError, UnicodeError, ValueError, TypeError) as exc:
        return _stale_receipt(result, exc, summary_path)

    states: Counter[str] = Counter()
    registry_families: dict[str, Counter[str]] = defaultdict(Counter)
    declared_families: dict[str, Counter[str]] = defaultdict(Counter)
    seen: set[str] = set()
    diagnostics = result["diagnostics"]
    try:
        with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                row = json.loads(line)
                where = f"{ledger_path}:{line_number}"
                if not isinstance(row, dict):
                    diagnostics.append(_diagnostic("ledger-row", where, "identity object", type(row).__name__))
                    break
                virtual = row.get("virtualPath")
                relative = row.get("exportRelativePath")
                path = PurePosixPath(relative) if isinstance(relative, str) else None
                valid = (path is not None and bool(relative) and not path.is_absolute()
                         and ".." not in path.parts and "\\" not in relative
                         and ":" not in relative and path.as_posix() == relative
                         and virtual == "Data/Json/" + relative and virtual not in seen
                         and type(row.get("length")) is int and row["length"] >= 0
                         and isinstance(row.get("family"), str) and bool(row["family"])
                         and isinstance(row.get("status"), str) and bool(row["status"])
                         and isinstance(row.get("logicalMd5"), str) and HEX32.fullmatch(row["logicalMd5"])
                         and isinstance(row.get("logicalSha256"), str) and HEX64.fullmatch(row["logicalSha256"]))
                if not valid:
                    diagnostics.append(_diagnostic("ledger-identity", where,
                        "unique safe JsonData path, nonnegative length, terminal status and MD5/SHA-256", virtual))
                    break
                seen.add(virtual)
                states[row["status"]] += 1
                family = registry_families[row["family"]]
                family["files"] += 1
                family["bytes"] += row["length"]
                family[row["status"]] += 1
                matches = [family["id"] for family in block["families"] if family["_pattern"].fullmatch(virtual)]
                if len(matches) > 1:
                    diagnostics.append(_diagnostic("declaration-partition", where,
                                                  "at most one exact path pattern", matches, virtualPath=virtual))
                    break
                declared_families[matches[0] if matches else "_other"][row["status"]] += 1
    except (OSError, UnicodeError, ValueError, EOFError) as exc:
        diagnostics.append(_diagnostic("ledger-readable", ledger_path, "authenticated JSONL gzip", str(exc)))
    # Reject a mixed receipt even when the bytes read happened to form valid
    # rows or a malformed row already produced a declaration diagnostic. Hash
    # saved inputs again; do not load the corpus or decode payloads a second time.
    try:
        receipts_end = _receipt_snapshot(provenance, summary_pin=summary_pin, ledger_path=ledger_path)
        if receipts_end != receipts_start:
            raise CensusGateError("receipt-input-drift", source=summary_path.as_posix(),
                                  expected="unchanged authenticated receipts before and after ledger scan",
                                  actual="receipt snapshot differs")
        if _discover_blc_paths(outer) != current_blcs:
            raise CensusGateError("blc-path-set-drift", source=outer_path.as_posix(),
                                  expected="unchanged installed catalog paths during ledger scan",
                                  actual="catalog path set changed")
        result["sources"]["receiptInputsRechecked"] = True
    except (CensusGateError, OSError, UnicodeError, ValueError, TypeError) as exc:
        return _stale_receipt(result, exc, summary_path)
    if diagnostics:
        return result
    # The pinned per-file receipt must account for every registry tally; this
    # also catches unsupported row shapes and incomplete/extra ledger records.
    actual_families = {name: dict(tally) for name, tally in registry_families.items()}
    comparisons = [
        ("joined-file-count", counts.get("filesJoined"), len(seen)),
        ("selected-file-count", counts.get("filesSelected"), len(seen)),
        ("logical-byte-count", counts.get("logicalBytes"), sum(tally["bytes"] for tally in registry_families.values())),
        ("status-tallies", counts["statusCounts"], dict(states)),
        ("family-count", counts.get("familyCount"), len(actual_families)),
    ]
    for check, expected, actual in comparisons:
        if expected != actual:
            diagnostics.append(_diagnostic(check, summary_path, expected, actual))
    for name in sorted(set(counts["families"]) | set(actual_families)):
        if counts["families"].get(name) != actual_families.get(name):
            diagnostics.append(_diagnostic("registry-family-tallies", summary_path,
                counts["families"].get(name), actual_families.get(name), family=name))
    for family in block["families"]:
        tally = declared_families.get(family["id"], Counter())
        if not tally:
            continue  # No current identity: do not infer a stage from an empty set.
        expected = "closed" if tally.get("schema_decoded", 0) == sum(tally.values()) else "partial"
        declared = next(stage["state"] for stage in family["stages"] if stage["level"] == 2)
        result["families"].append({"id": family["id"], "files": sum(tally.values()),
                                    "statusCounts": dict(sorted(tally.items())),
                                    "declaredL2": declared, "expectedL2": expected})
        if declared != expected:
            diagnostics.append(_diagnostic("declaration-l2", summary_path, expected, declared,
                                           family=family["id"], pathRegex=family["pathRegex"]))
    if declared_families.get("_other"):
        tally = declared_families["_other"]
        result["families"].append({"id": "_other", "files": sum(tally.values()),
                                    "statusCounts": dict(sorted(tally.items())),
                                    "declaredL2": "notAssessed", "expectedL2": "notAssessed"})
    result["omittedDiagnostics"] = max(0, len(diagnostics) - MAX_DIAGNOSTICS)
    result["diagnostics"] = diagnostics[:MAX_DIAGNOSTICS]
    result["status"] = "mismatched" if diagnostics else "verified"
    return result


def main(argv: list[str] | None = None) -> int:
    from scripts.webui.recovery.build_recovery import load_declarations, resolve_vfs_blocks
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    if not args.output.resolve().is_relative_to(REPORTS_DIR.resolve()):
        parser.error("generated check output must stay under reports/")
    declarations = load_declarations()
    block = next(row for row in resolve_vfs_blocks(declarations,
        lane_ids=set(declarations["lanes"]["entries"])) if row["enumName"] == "JsonData")
    result = check_jsondata_stages(block, summary_path=args.summary, ledger_path=args.ledger)
    write_canonical_json(args.output, result)
    print(f"{VALIDATOR}: verified {len(result['families'])} path families -> {args.output}"
          if result["status"] == "verified" else describe_failure(result))
    return 0 if result["status"] in {"verified", "missing"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

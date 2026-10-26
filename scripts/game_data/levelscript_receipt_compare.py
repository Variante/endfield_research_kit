"""Compare saved complete LevelScript receipts without claiming current inputs.

Receipt hashes authenticate the selected saved artifacts. Matching source and
native identities permits a historical status comparison; each receipt retains
its own reader scope. Partial cursor progress and present-day EOF are not inferred.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

if __name__ == "__main__" and not __package__:
    raise SystemExit("Run with python -m scripts.game_data.levelscript_receipt_compare")

from scripts.game_data.corpus_common import atomic_write_text
from scripts.repo_paths import REPO_ROOT

FORMAT = "endfield-levelscript-receipt-comparison-v2"
RECEIPT_FORMAT = "endfield-levelscript-current-corpus-v1"
FAMILIES = ("LevelScriptData", "LevelScriptTemplateData")
IDENTITY_FIELDS = ("family", "length", "logicalMd5", "logicalSha256", "exportRelativePath")


class ReceiptComparisonError(ValueError):
    def __init__(self, check: str, source: str, expected: Any, actual: Any):
        self.diagnostic = {"validator": "levelscript_receipt_compare", "check": check,
                           "source": source, "expected": _bounded(expected), "actual": _bounded(actual)}
        super().__init__(json.dumps(self.diagnostic, ensure_ascii=False, sort_keys=True))


def _bounded(value: Any) -> Any:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return value if len(encoded) <= 700 else encoded[:700] + "..."


def _require(check: str, source: str, expected: Any, actual: Any) -> None:
    if actual != expected:
        raise ReceiptComparisonError(check, source, expected, actual)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def _hex(value: Any, width: int, source: str) -> str:
    if not isinstance(value, str) or len(value) != width or any(c not in "0123456789abcdefABCDEF" for c in value):
        raise ReceiptComparisonError("digest-shape", source, f"{width} hexadecimal characters", value)
    return value.upper()


def _index(receipt: dict[str, Any], source: str) -> dict[str, dict[str, Any]]:
    _require("receipt-format", source, RECEIPT_FORMAT, receipt.get("format"))
    _require("receipt-version-type", source, "int", type(receipt.get("schemaVersion")).__name__)
    _require("receipt-version", source, 1, receipt.get("schemaVersion"))
    _require("receipt-complete", source, "complete", receipt.get("status"))
    _require("receipt-families", source, list(FAMILIES), receipt.get("families"))
    _hex(receipt.get("inputSetSha256"), 64, source + ".inputSetSha256")
    rows = receipt.get("rows")
    if not isinstance(rows, list):
        raise ReceiptComparisonError("receipt-rows", source, "row array", type(rows).__name__)
    indexed: dict[str, dict[str, Any]] = {}
    counts = {family: Counter() for family in FAMILIES}
    for row in rows:
        if not isinstance(row, dict):
            raise ReceiptComparisonError("receipt-row", source, "row object", type(row).__name__)
        path = row.get("virtualPath")
        if not isinstance(path, str) or not path or path in indexed:
            raise ReceiptComparisonError("receipt-unique-path", source, "unique nonempty virtualPath", path)
        family = row.get("family")
        if family not in FAMILIES or not path.startswith("Data/Json/" + family + "/"):
            raise ReceiptComparisonError("receipt-row-family", path, list(FAMILIES), family)
        _require("receipt-export-path", path, path.removeprefix("Data/Json/"), row.get("exportRelativePath"))
        length = row.get("length")
        if type(length) is not int or length < 0:
            raise ReceiptComparisonError("receipt-source-length", path, "nonnegative integer", length)
        _hex(row.get("logicalMd5"), 32, path + ".logicalMd5")
        _hex(row.get("logicalSha256"), 64, path + ".logicalSha256")
        status = row.get("status")
        if status not in ("schema_decoded", "bounded_partial"):
            raise ReceiptComparisonError("receipt-row-status", path, ["schema_decoded", "bounded_partial"], status)
        if status == "schema_decoded":
            _require("receipt-decoded-named-status", path, "named_exact", row.get("namedSchemaStatus"))
            _require("receipt-decoded-cursor-type", path, "int", type(row.get("bytesConsumed")).__name__)
            _require("receipt-decoded-eof", path, length, row.get("bytesConsumed"))
        else:
            _require("receipt-partial-named-status", path, "partial", row.get("namedSchemaStatus"))
        indexed[path] = row
        counts[family][status] += 1
    summary = {"filesSelected": len(rows), "filesJoined": len(rows), "families": {
        family: {"files": sum(counts[family].values()), **dict(counts[family])} for family in FAMILIES}}
    _require("receipt-summary", source, summary, receipt.get("summary"))
    return indexed


def _native_identities(receipt: dict[str, Any], source: str) -> list[dict[str, Any]]:
    entries = receipt.get("provenance", {}).get("nativeInputs")
    if not isinstance(entries, list) or len(entries) != 2:
        raise ReceiptComparisonError("receipt-native-inputs", source, "two selected native input fingerprints", entries)
    result = []
    for row in entries:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str) or type(row.get("length")) is not int or row["length"] < 0:
            raise ReceiptComparisonError("receipt-native-fingerprint", source, "path/length/SHA256 fingerprint", row)
        result.append({"path": row["path"], "length": row["length"], "sha256": _hex(row.get("sha256"), 64, source)})
    _require("receipt-native-roles", source, ["GameAssembly.dll", "global-metadata.dat"],
             sorted(Path(row["path"]).name for row in result))
    return sorted(result, key=lambda row: row["path"])


def compare_receipts(before: dict[str, Any], after: dict[str, Any], *,
                     before_source: str = "before", after_source: str = "after",
                     allow_audit_run_change: bool = False) -> dict[str, Any]:
    old, new = _index(before, before_source), _index(after, after_source)
    if type(allow_audit_run_change) is not bool:
        raise ReceiptComparisonError("comparison-audit-run-policy-type", after_source, "builtin bool",
                                     {"actualType": type(allow_audit_run_change).__name__, "builtinBool": False})
    if not allow_audit_run_change:
        _require("comparison-input-set", after_source, before["inputSetSha256"], after["inputSetSha256"])
    _require("comparison-native-inputs", after_source, _native_identities(before, before_source),
             _native_identities(after, after_source))
    if old.keys() != new.keys():
        raise ReceiptComparisonError("comparison-source-path-set", after_source,
            {"files": len(old), "missingPaths": sorted(old.keys() - new.keys())[:8]},
            {"files": len(new), "addedPaths": sorted(new.keys() - old.keys())[:8]})
    changes = []
    for path in sorted(old):
        a, b = old[path], new[path]
        for field in IDENTITY_FIELDS:
            _require("comparison-source-identity:" + field, path, a[field], b[field])
        if a["status"] == "schema_decoded" and b["status"] != "schema_decoded":
            raise ReceiptComparisonError("comparison-schema-regression", path, a["status"], b["status"])
        if a["status"] != b["status"]:
            changes.append({"virtualPath": path, "before": a["status"], "after": b["status"],
                            "logicalSha256": b["logicalSha256"]})
    return {"format": FORMAT, "status": "same-source-no-schema-regression", "filesCompared": len(new),
            "auditRuns": {"beforeInputSetSha256": before["inputSetSha256"],
                          "afterInputSetSha256": after["inputSetSha256"],
                          "identical": before["inputSetSha256"] == after["inputSetSha256"],
                          "changeExplicitlyAllowed": allow_audit_run_change},
            "beforeSummary": before["summary"], "afterSummary": after["summary"],
            "transitions": dict(Counter(row["before"] + " -> " + row["after"] for row in changes)),
            "changes": changes, "currentInputsAuthenticated": False, "partialCursorProgressCompared": False,
            "evidenceBoundary": "Saved complete receipts only. Source and selected native fingerprints agree; reader scopes remain independent. No present-day native/source/reader validity or owner EOF is inherited."}


def _read(path: Path, expected_sha256: str) -> tuple[bytes, dict[str, Any]]:
    expected = _hex(expected_sha256, 64, str(path))
    raw = path.read_bytes()
    _require("receipt-artifact-sha256", str(path), expected, _sha(raw))
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ReceiptComparisonError("receipt-object", str(path), "object", type(value).__name__)
    return raw, value


def _guard_output(output: Path, protected: list[Path]) -> None:
    resolved = output.resolve()
    reports = (REPO_ROOT / "reports").resolve()
    if not resolved.is_relative_to(reports) or resolved == reports:
        raise ReceiptComparisonError("comparison-output-root", str(output), "file within reports/", str(resolved))
    for path in protected:
        if resolved == path.resolve() or (resolved.exists() and path.exists() and os.path.samefile(resolved, path)):
            raise ReceiptComparisonError("comparison-output-input-alias", str(output), "distinct output", str(path))
    if resolved.exists():
        existing = json.loads(resolved.read_bytes())
        _require("comparison-output-owner", str(output), FORMAT,
                 existing.get("format") if isinstance(existing, dict) else None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--expected-before-sha256", required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--expected-after-sha256", required=True)
    parser.add_argument("--allow-audit-run-change", action="store_true",
                        help="Permit different recorded audit input sets; every source identity and selected native fingerprint must still agree.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        old_raw, before = _read(args.before, args.expected_before_sha256)
        new_raw, after = _read(args.after, args.expected_after_sha256)
        result = compare_receipts(before, after, before_source=str(args.before), after_source=str(args.after),
                                  allow_audit_run_change=args.allow_audit_run_change)
        result["beforeReceipt"] = {"path": str(args.before), "sha256": _sha(old_raw)}
        result["afterReceipt"] = {"path": str(args.after), "sha256": _sha(new_raw)}
        protected = [args.before, args.after, Path(__file__)]
        for receipt in (before, after):
            for values in receipt.get("provenance", {}).values():
                protected.extend(Path(row["path"]) for row in (values if isinstance(values, list) else [values])
                                 if isinstance(row, dict) and isinstance(row.get("path"), str))
        encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            _guard_output(args.output, protected)
        _require("comparison-before-unchanged", str(args.before), _sha(old_raw), _sha(args.before.read_bytes()))
        _require("comparison-after-unchanged", str(args.after), _sha(new_raw), _sha(args.after.read_bytes()))
        if args.output:
            _guard_output(args.output, protected)
            atomic_write_text(args.output, encoded)
        else:
            print(encoded, end="")
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        diagnostic = getattr(exc, "diagnostic", {"validator": "levelscript_receipt_compare", "check": "comparison-input-readable",
                                                  "source": "selected saved receipts", "expected": "comparable complete receipts",
                                                  "actual": str(exc)[:700]})
        print(json.dumps({"status": "failed", "diagnostic": diagnostic}, ensure_ascii=False), file=sys.stderr)
        return 2
    if args.output:
        print(json.dumps({"status": result["status"], "filesCompared": result["filesCompared"],
                          "transitions": result["transitions"], "report": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Rank the first refusal of every current bounded-partial LevelScript file.

What it proves. Every ``LevelScriptData`` row the JsonData corpus receipt
records as ``bounded_partial`` is reread from the structured export, checked
against the receipt by length and logical SHA-256, and handed once to the
LevelScript sequential owner
(``codecs.levelscript.current_action_sequence.frame_levelscript_current_action_sequence_leader_enter``).
The owner's first refusal, with byte offsets normalized to ``offset=<n>``, is
that file's first stop; a file the owner now frames is recorded as
``complete:<schemaStatus>`` (plus the stop field and first task-condition gate
for a partial frame). ``topFirstStops`` counts whole files per first stop, so
it ranks the next union routes by the files each would move past their first
refusal.

Evidence tier. ``exact`` for the source identity join (JsonData summary,
per-file ledger and export bytes) and for the owner's refusal on those bytes
under the selected build. The ranking is a work-ordering lead only.

What it does not prove. A first stop hides every later stop in the same file,
so closing a route does not by itself close a file: rerank after each
integration and after the next full JsonData gate. A stop names where the
reviewed readers refuse, never a field meaning, runtime dispatch or execution.
A file whose frame now closes while an older JsonData receipt still says
``bounded_partial`` remains provisional until a complete owning corpus gate.
The independent family gate owns its two stored families; ``jsondata_corpus``
owns the combined registry and WebUI classification.

Fail-closed gates, each reported with the failed check, source path and
bounded expected/actual values (all independent failures, not only the
first):

- the summary is a complete ``endfield-jsondata-current-corpus-v1`` receipt
  for ``--expected-input-set-sha256`` whose ``exportRoot`` is ``--export-root``
  and whose ``provenance.outputFiles`` pins the ``--ledger`` bytes;
- the ledger's LevelScript file and partial counts equal the summary's;
- the installed build matches the reviewed action-map layout contract, since
  on any other build every reviewed node would refuse at the build gate and
  the census would rank that refusal instead of a format stop;
- every partial file exists and matches its ledger length and SHA-256;
- no first stop is itself a native-gate refusal.

A failed run preserves the last census and writes a ``status: failed`` report
to its separate ``.validation.json`` companion. A saved ranking remains tied
to its authenticated source/native/reader inputs; the companion does not make
a historical ranking current.

Run from the repository root (the input set comes from the VFS audit)::

    python -m scripts.game_data.levelscript_first_stop_census --expected-input-set-sha256 SHA

``--summary``, ``--ledger`` and ``--export-root`` default to
``reports/animestudio/jsondata_current_latest.json``,
``reports/animestudio/jsondata_current_files_latest.jsonl.gz`` and
``export_full/game/Json``; the report defaults to
``reports/game_data/levelscript_partial_first_stops_current.json``.
Schema v3 retains the authenticated v2 report and adds ``family`` and
``--family LevelScriptTemplateData`` with its own owner and default output.
Template action-map record indices are normalized so one route ranks together.
Reached module refusals group by their raw union tag/member count and the
current native-gated type name when available. Optional row ``stopDetail``
retains the actual module key, index and byte offset; those source identities
do not fragment a shape bucket, and a known type does not prove its grammar.
It keeps every v1 key (``inputSetSha256``, ``sourceSummarySha256``,
``sourceLedgerSha256``, ``partialFiles``, ``topFirstStops`` as
``[stop, files]`` pairs, ``rows`` of ``path``/``sha256``/``firstStop``) and
adds ``evidenceBoundary``, ``sourceLedgerLength``, ``owner`` and
``nativeGate``.

``--family-receipt`` explicitly selects the separate complete LevelScript
receipt. It requires ``--expected-family-receipt-sha256`` as well as the input
set gate and emits schema v4 with the source receipt format stated. Every live
source, native/chunk and complete reader input is rechecked before and after
the partial-owner replay. This mode never accepts a family receipt as the
combined JsonData registry.
"""

from __future__ import annotations

if __name__ == "__main__" and not __package__:
    raise SystemExit("Run as: python -m scripts.game_data.levelscript_first_stop_census")

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file_upper
from scripts.game_data.codecs.levelscript.action_map import (
    CONTRACT_PATH as LAYOUT_CONTRACT_PATH,
)
from scripts.game_data.codecs.levelscript.current_action_sequence import (
    frame_levelscript_current_action_sequence_leader_enter,
)
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.levelscript_template_binary import frame_levelscript_template
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.levelscript-partial-first-stop-census.v3"
FAMILY_RECEIPT_SCHEMA = "endfield.levelscript-partial-first-stop-census.v4"
VALIDATOR = "levelscript_first_stop_census"
JSONDATA_FORMAT = "endfield-jsondata-current-corpus-v1"
FAMILY = "LevelScriptData"
PARTIAL_STATUS = "bounded_partial"
OWNER = (
    "scripts.game_data.codecs.levelscript.current_action_sequence."
    "frame_levelscript_current_action_sequence_leader_enter"
)
DEFAULT_SUMMARY = REPO_ROOT / "reports/animestudio/jsondata_current_latest.json"
DEFAULT_LEDGER = REPO_ROOT / "reports/animestudio/jsondata_current_files_latest.jsonl.gz"
DEFAULT_EXPORT = REPO_ROOT / "export_full/game/Json"
DEFAULT_OUTPUT = REPO_ROOT / "reports/game_data/levelscript_partial_first_stops_current.json"
TOP_STOPS = 100
MAX_REPORTED_FAILURES = 25
OFFSET = re.compile(r"offset=\d+")
TEMPLATE_RECORD = re.compile(r"(\.lists\[\d+\])\[\d+\]")
# Refusals raised by a build or body gate rather than by a format read:
# the layout build gate, per-route contract gates, per-route audits
# (``actionMap.<route>Native:``), validator labels and enum-native checks.
NATIVE_REFUSAL = re.compile(r"installed_native_inputs|nativeGate:|[a-z]Native:|\.native[:=]|\.nativeContract:|-native=")
EVIDENCE_BOUNDARY = (
    "exact source identity join and the sequential owner's first refusal on the "
    "current bytes under the selected build; a first stop hides later stops in the "
    "same file and ranks work, never field meaning or runtime behaviour"
)


class CensusError(ValueError):
    """One or more census gates failed; ``failures`` holds every diagnostic."""

    def __init__(self, failures: list[dict[str, Any]]) -> None:
        self.failures = failures
        first = failures[0]
        more = f" (+{len(failures) - 1} more)" if len(failures) > 1 else ""
        super().__init__(
            f"{first['check']}: {first['source']}: expected {first['expected']!r}, "
            f"actual {first['actual']!r}{more}"
        )


def _failure(check: str, source: Any, expected: Any, actual: Any, **extra: Any) -> dict[str, Any]:
    return {"validator": VALIDATOR, "check": check, "source": str(source),
            "expected": expected, "actual": actual, **extra}


def _bounded(value: Any, limit: int = 240) -> Any:
    return value[:limit] if isinstance(value, str) else value


def _read_summary(
    summary_path: Path, ledger_path: Path, export_root: Path, expected_input_set: str,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Check the JsonData receipt identity; return it, its ledger pin and failures."""
    failures: list[dict[str, Any]] = []
    try:
        summary = json.loads(summary_path.read_bytes())
    except (OSError, ValueError) as exc:
        return {}, {}, [_failure("summary-readable", summary_path, "JSON object", _bounded(str(exc)))]
    if not isinstance(summary, dict):
        return {}, {}, [_failure("summary-readable", summary_path, "JSON object", type(summary).__name__)]
    counts = summary.get("summary") if isinstance(summary.get("summary"), dict) else {}
    for check, expected, actual in (
        ("summary-format", JSONDATA_FORMAT, summary.get("format")),
        ("summary-status", "complete", summary.get("status")),
        ("summary-input-set", expected_input_set, str(summary.get("inputSetSha256", "")).upper()),
        ("summary-join-complete", counts.get("filesSelected"), counts.get("filesJoined")),
    ):
        if actual != expected:
            failures.append(_failure(check, summary_path, expected, actual))
    recorded_root = summary.get("exportRoot")
    if not isinstance(recorded_root, str) or Path(recorded_root).resolve() != export_root.resolve():
        failures.append(_failure("summary-export-root", summary_path,
                                 export_root.resolve().as_posix(), recorded_root))
    pinned = (summary.get("provenance") or {}).get("outputFiles") or {}
    ledger: dict[str, Any] = {}
    try:
        ledger = {"length": ledger_path.stat().st_size, "sha256": sha256_file_upper(ledger_path)}
    except OSError as exc:
        failures.append(_failure("ledger-readable", ledger_path, "readable file", _bounded(str(exc))))
    else:
        actual = {"length": ledger["length"], "sha256": ledger["sha256"]}
        expected = {"length": pinned.get("length"), "sha256": str(pinned.get("sha256", "")).upper()}
        if actual != expected:
            failures.append(_failure("summary-ledger-join", ledger_path, expected, actual))
    return summary, ledger, failures


def _read_ledger(
    ledger_path: Path, summary_path: Path, summary: dict[str, Any],
    family: str = FAMILY,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return the ledger's partial LevelScript rows in ledger order, plus failures."""
    failures: list[dict[str, Any]] = []
    partial: list[dict[str, Any]] = []
    seen: set[str] = set()
    total = 0
    with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            row = json.loads(line)
            if not isinstance(row, dict) or row.get("family") != family:
                continue
            total += 1
            name = row.get("exportRelativePath")
            posix = PurePosixPath(name) if isinstance(name, str) else None
            if (
                posix is None or not name.startswith(family + "/") or "\\" in name
                or posix.is_absolute() or ".." in posix.parts or name in seen
                or type(row.get("length")) is not int
                or not isinstance(row.get("logicalSha256"), str)
            ):
                failures.append(_failure("ledger-row", f"{ledger_path}:{line_number}",
                                         f"unique safe {family} path with length and SHA-256",
                                         _bounded(name if isinstance(name, str) else repr(name))))
                continue
            seen.add(name)
            if row.get("status") == PARTIAL_STATUS:
                partial.append(row)
    declared = ((summary.get("summary") or {}).get("families") or {}).get(family) or {}
    if total != declared.get("files"):
        failures.append(_failure("family-file-count", summary_path, declared.get("files"), total))
    if len(partial) != declared.get(PARTIAL_STATUS, 0):
        failures.append(_failure("family-partial-count", summary_path,
                                 declared.get(PARTIAL_STATUS, 0), len(partial)))
    return partial, failures


def _native_gate() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Gate the installed build against the reviewed action-map layout contract."""
    contract = json.loads(LAYOUT_CONTRACT_PATH.read_bytes())
    pins = contract["nativeInputs"]
    native = check_installed_native_inputs(pins["gameAssembly"]["sha256"], pins["metadata"]["sha256"])
    record = {"contract": LAYOUT_CONTRACT_PATH.name, "status": native.status}
    if native.status == "validated":
        return record, []
    return record, [_failure("native-inputs", getattr(native, "gameassembly", ""), "validated",
                             native.status, detail=_bounded(getattr(native, "detail", "")))]


def module_first_stop(frame: dict[str, Any]) -> str | None:
    """Group a reached module shape, retaining per-source identity elsewhere."""
    if frame.get("stopField") != "modules":
        return None
    detail = frame.get("stopDetail")
    if not isinstance(detail, dict):
        return None
    diagnostics = detail.get("diagnostics")
    if not isinstance(diagnostics, list) or not diagnostics or not isinstance(diagnostics[0], dict):
        return None
    diagnostic = diagnostics[0]
    tag = diagnostic.get("moduleUnionTag")
    count = diagnostic.get("serializedMemberCount")
    if (diagnostic.get("gate") != "supportedModuleUnionShape"
            or not isinstance(tag, str) or not re.fullmatch(r"0x[0-9a-fA-F]{4}", tag)
            or (count is not None and (type(count) is not int or not 0 <= count <= 255))):
        return None
    stop = "modules:supportedModuleUnionShape:" + tag.lower()
    stop += ":members=" + ("unreadable" if count is None else str(count))
    module_type = diagnostic.get("moduleType")
    if isinstance(module_type, str) and module_type:
        stop += ":type=" + module_type
    return stop


def first_stop(data: bytes, family: str = FAMILY, *, diagnostics: list[dict[str, Any]] | None = None) -> str:
    """The sequential owner's first refusal, or its completion status."""
    try:
        frame = (frame_levelscript_template(data) if family == "LevelScriptTemplateData"
                 else frame_levelscript_current_action_sequence_leader_enter(data))
    except ValueError as error:
        from scripts.game_data.levelscript_corpus import _diagnostic_messages
        messages = [str(error), *_diagnostic_messages(getattr(error, "diagnostics", []))]
        native = next((message for message in messages if NATIVE_REFUSAL.search(message)), None)
        if native:
            return native
        return OFFSET.sub("offset=<n>", str(error))
    from scripts.game_data.levelscript_corpus import _diagnostic_messages
    messages = _diagnostic_messages([frame.get(key, []) for key in
                                    ("readerRefusals", "diagnostics", "taskDiagnostics", "stopDetail")])
    native = next((message for message in messages if NATIVE_REFUSAL.search(message)), None)
    if native:
        return native
    stop = "complete:" + str(frame.get("schemaStatus"))
    if frame.get("schemaStatus") == "partial":
        module_stop = module_first_stop(frame)
        if module_stop:
            if diagnostics is not None:
                diagnostics.append(frame["stopDetail"])
            return stop + ":" + module_stop
        if family == "LevelScriptTemplateData":
            reason = (frame.get("actionMap") or {}).get("unresolvedReason")
            if reason:
                return TEMPLATE_RECORD.sub(r"\1[<n>]", OFFSET.sub("offset=<n>", str(reason)))
            diagnostics = frame.get("diagnostics") or []
            if diagnostics:
                return OFFSET.sub("offset=<n>", str(diagnostics[0]["detail"]))
        stop += ":" + str(frame.get("stopField"))
        diagnostics = frame.get("taskDiagnostics") or []
        if diagnostics:
            detail = diagnostics[0]
            stop += ":" + str(detail.get("gate"))
            if detail.get("conditionUnionTag"):
                stop += ":" + str(detail["conditionUnionTag"])
    return stop


def build_census(
    *,
    summary_path: Path = DEFAULT_SUMMARY,
    ledger_path: Path = DEFAULT_LEDGER,
    export_root: Path = DEFAULT_EXPORT,
    expected_input_set_sha256: str,
    top: int = TOP_STOPS,
    family: str = FAMILY,
) -> dict[str, Any]:
    """Rerun the owner over every current partial LevelScript file and rank first stops."""
    expected = expected_input_set_sha256.upper()
    if family not in (FAMILY, "LevelScriptTemplateData"):
        raise ValueError(f"unsupported census family: {family}")
    summary, ledger, failures = _read_summary(summary_path, ledger_path, export_root, expected)
    native, native_failures = _native_gate()
    failures += native_failures
    if failures:
        raise CensusError(failures)
    partial, failures = _read_ledger(ledger_path, summary_path, summary, family)
    if failures:
        raise CensusError(failures)

    rows: list[dict[str, Any]] = []
    for item in partial:
        name = item["exportRelativePath"]
        source = export_root / name
        try:
            data = source.read_bytes()
        except OSError as exc:
            failures.append(_failure("source-readable", source, "exported file", _bounded(str(exc))))
            continue
        digest = hashlib.sha256(data).hexdigest().upper()
        if len(data) != item["length"] or digest != item["logicalSha256"].upper():
            failures.append(_failure(
                "source-identity", source,
                {"length": item["length"], "sha256": item["logicalSha256"].upper()},
                {"length": len(data), "sha256": digest},
            ))
            continue
        stop_details: list[dict[str, Any]] = []
        stop = first_stop(data, family, diagnostics=stop_details)
        if NATIVE_REFUSAL.search(stop):
            failures.append(_failure("native-refusal-stop", source, "a format stop",
                                     _bounded(stop), sha256=digest))
            continue
        rows.append({"path": name, "sha256": digest, "firstStop": stop,
                     **({"stopDetail": stop_details[0]} if stop_details else {})})
    if failures:
        raise CensusError(failures)

    counts = Counter(row["firstStop"] for row in rows)
    return {
        "schema": SCHEMA,
        "family": family,
        "status": "current-source-authenticated",
        "evidenceBoundary": EVIDENCE_BOUNDARY,
        "inputSetSha256": expected,
        "sourceSummarySha256": sha256_file_upper(summary_path),
        "sourceLedgerSha256": ledger["sha256"],
        "sourceLedgerLength": ledger["length"],
        "owner": ("scripts.game_data.levelscript_template_binary.frame_levelscript_template"
                  if family == "LevelScriptTemplateData" else OWNER),
        "nativeGate": native,
        "partialFiles": len(rows),
        "topFirstStops": counts.most_common(top),
        "rows": rows,
    }


def build_family_census(*, receipt_path: Path, expected_receipt_sha256: str,
                        export_root: Path, expected_input_set_sha256: str,
                        family: str = FAMILY, top: int = TOP_STOPS) -> dict[str, Any]:
    """Replay a partial cohort from an explicitly authenticated family receipt."""
    from scripts.game_data.levelscript_corpus import verify_family_receipt, FORMAT
    from scripts.game_data.game_file_store import read_game_file
    if family not in (FAMILY, "LevelScriptTemplateData"):
        raise ValueError(f"unsupported census family: {family}")
    game_export = export_root.parent.parent
    if (game_export / "game/Json").resolve() != export_root.resolve():
        raise CensusError([_failure("family-export-layout", export_root, "export-root/game/Json", str(export_root))])
    options = dict(expected_sha256=expected_receipt_sha256,
                   expected_input_set_sha256=expected_input_set_sha256, export_root=game_export)
    receipt = verify_family_receipt(receipt_path, **options)
    partial = [row for row in receipt["rows"] if row["family"] == family and row["status"] == PARTIAL_STATUS]
    rows, failures = [], []
    for item in partial:
        name = item["exportRelativePath"]
        data = read_game_file(game_export, "Json/" + name)
        digest = hashlib.sha256(data).hexdigest().upper()
        if len(data) != item["length"] or digest != item["logicalSha256"]:
            failures.append(_failure("source-identity", name,
                {"length": item["length"], "sha256": item["logicalSha256"]},
                {"length": len(data), "sha256": digest}))
            continue
        stop_details: list[dict[str, Any]] = []
        stop = first_stop(data, family, diagnostics=stop_details)
        if NATIVE_REFUSAL.search(stop):
            failures.append(_failure("native-refusal-stop", name, "a format stop", _bounded(stop), sha256=digest))
            continue
        rows.append({"path": name, "sha256": digest, "firstStop": stop,
                     **({"stopDetail": stop_details[0]} if stop_details else {})})
    if failures:
        raise CensusError(failures)
    verify_family_receipt(receipt_path, **options)
    return {"schema": FAMILY_RECEIPT_SCHEMA, "family": family, "status": "current-source-authenticated",
            "evidenceBoundary": EVIDENCE_BOUNDARY, "inputSetSha256": receipt["inputSetSha256"],
            "sourceReceiptFormat": FORMAT, "sourceReceiptSha256": expected_receipt_sha256.upper(),
            "sourceSummarySha256": expected_receipt_sha256.upper(),
            "sourceLedgerSha256": receipt["provenance"]["ledger"]["sha256"],
            "sourceLedgerLength": receipt["provenance"]["ledger"]["length"],
            "owner": ("scripts.game_data.levelscript_template_binary.frame_levelscript_template"
                      if family == "LevelScriptTemplateData" else OWNER),
            "nativeGate": {"status": "validated", "source": "authenticated complete family receipt",
                           "inputs": receipt["provenance"]["nativeInputs"]},
            "partialFiles": len(rows), "topFirstStops": Counter(row["firstStop"] for row in rows).most_common(top),
            "rows": rows}


def failure_report(expected_input_set_sha256: str, failures: list[dict[str, Any]], *, schema: str = SCHEMA) -> dict[str, Any]:
    return {
        "schema": schema,
        "status": "failed",
        "expectedInputSetSha256": expected_input_set_sha256.upper(),
        "failureCount": len(failures),
        "failures": failures[:MAX_REPORTED_FAILURES],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT)
    parser.add_argument("--top", type=int, default=TOP_STOPS)
    parser.add_argument("--family", choices=(FAMILY, "LevelScriptTemplateData"), default=FAMILY)
    parser.add_argument("--family-receipt", type=Path)
    parser.add_argument("--expected-family-receipt-sha256")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if bool(args.family_receipt) != bool(args.expected_family_receipt_sha256):
        parser.error("--family-receipt and --expected-family-receipt-sha256 must be supplied together")
    if args.output is None:
        args.output = (DEFAULT_OUTPUT.with_name("levelscript_template_partial_first_stops_current.json")
                       if args.family == "LevelScriptTemplateData" else DEFAULT_OUTPUT)
    from scripts.game_data.levelscript_corpus import _guard_output
    from scripts.game_data.levelscript_reader_inputs import complete_reader_input_paths
    protected = [args.summary, args.ledger, args.export_root, REPO_ROOT / "scripts", *complete_reader_input_paths()]
    if args.family_receipt is not None:
        protected.append(args.family_receipt)
        try:
            receipt = json.loads(args.family_receipt.read_bytes())
            for value in receipt.get("provenance", {}).values():
                values = value if isinstance(value, list) else [value]
                protected.extend(Path(row["path"]) for row in values if isinstance(row, dict) and isinstance(row.get("path"), str))
        except (OSError, ValueError, AttributeError):
            pass
    if args.export_root.is_dir():
        protected.extend(path for path in args.export_root.rglob("*") if path.is_file())
    native = check_installed_native_inputs()
    protected.extend(Path(path) for path in (getattr(native, "gameassembly", None), getattr(native, "metadata", None)) if path)
    try:
        _guard_output(args.output, protected)
        _guard_output(args.output.with_suffix(".validation.json"), protected + [args.output])
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    try:
        if args.family_receipt is not None:
            report = build_family_census(receipt_path=args.family_receipt,
                expected_receipt_sha256=args.expected_family_receipt_sha256,
                export_root=args.export_root, expected_input_set_sha256=args.expected_input_set_sha256,
                top=args.top, family=args.family)
        else:
            report = build_census(
                summary_path=args.summary, ledger_path=args.ledger, export_root=args.export_root,
                expected_input_set_sha256=args.expected_input_set_sha256, top=args.top, family=args.family,
            )
        current_protected = protected + complete_reader_input_paths()
        _guard_output(args.output, current_protected)
        _guard_output(args.output.with_suffix(".validation.json"), current_protected + [args.output])
    except (CensusError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        failures = exc.failures if isinstance(exc, CensusError) else [
            {**getattr(exc, "diagnostic", _failure("unexpected-input", args.family_receipt or args.ledger,
                "readable receipt inputs", _bounded(f"{type(exc).__name__}: {exc}"))), "validator": VALIDATOR}
        ]
        for failure in failures:
            failure.setdefault("check", failure.get("code", "unexpected-input"))
        failed = failure_report(args.expected_input_set_sha256, failures,
            schema=FAMILY_RECEIPT_SCHEMA if args.family_receipt is not None else SCHEMA)
        companion = args.output.with_suffix(".validation.json")
        try:
            _guard_output(companion, protected + [args.output, *complete_reader_input_paths()])
            atomic_write_text(companion, json.dumps(failed, ensure_ascii=False, indent=2) + "\n")
        except (OSError, ValueError, KeyError, RuntimeError) as output_exc:
            print(json.dumps({"diagnosticPublicationRefusal": {
                "validator": VALIDATOR, "check": "diagnostic-output-refused", "source": str(companion),
                "expected": "safe writable diagnostic path", "actual": _bounded(str(output_exc)),
            }}, ensure_ascii=False))
        print(f"levelscript first-stop census failed ({len(failures)} failures); diagnostic={companion}")
        for failure in failures[:5]:
            print(f"  {failure['check']}: {failure['source']}: expected {failure['expected']!r}, "
                  f"actual {failure['actual']!r}")
        return 2
    atomic_write_text(args.output, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(args.output.with_suffix(".validation.json"), json.dumps({
        "schema": report["schema"], "status": "validated", "diagnostic": None,
        "inputSetSha256": report["inputSetSha256"],
        **({"sourceReceiptSha256": report["sourceReceiptSha256"]} if "sourceReceiptSha256" in report else {}),
    }, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "partialFiles": report["partialFiles"],
                      "topFirstStops": report["topFirstStops"][:10], "report": str(args.output)},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

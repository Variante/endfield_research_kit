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
A file whose frame now closes while the receipt still says
``bounded_partial`` means the receipt is older than the codec, not that the
file is exact: only ``jsondata_corpus`` promotes a file.

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

A failed run overwrites the output with a ``status: failed`` report so a stale
ranking is never read as current.

Run from the repository root (the input set comes from the VFS audit)::

    python -m scripts.game_data.levelscript_first_stop_census --expected-input-set-sha256 SHA

``--summary``, ``--ledger`` and ``--export-root`` default to
``reports/animestudio/jsondata_current_latest.json``,
``reports/animestudio/jsondata_current_files_latest.jsonl.gz`` and
``export_full/game/Json``; the report defaults to
``reports/game_data/levelscript_partial_first_stops_current.json``.
Schema v2 keeps every v1 key (``inputSetSha256``, ``sourceSummarySha256``,
``sourceLedgerSha256``, ``partialFiles``, ``topFirstStops`` as
``[stop, files]`` pairs, ``rows`` of ``path``/``sha256``/``firstStop``) and
adds ``evidenceBoundary``, ``sourceLedgerLength``, ``owner`` and
``nativeGate``.
"""

from __future__ import annotations

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
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.levelscript-partial-first-stop-census.v2"
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
# Refusals raised by a build or body gate rather than by a format read:
# the layout build gate, per-route contract gates, per-route audits
# (``actionMap.<route>Native:``), validator labels and enum-native checks.
NATIVE_REFUSAL = re.compile(r"installed_native_inputs|nativeGate:|[a-z]Native:|\.native[:=]|-native=")
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
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return the ledger's partial LevelScript rows in ledger order, plus failures."""
    failures: list[dict[str, Any]] = []
    partial: list[dict[str, Any]] = []
    seen: set[str] = set()
    total = 0
    with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            row = json.loads(line)
            if not isinstance(row, dict) or row.get("family") != FAMILY:
                continue
            total += 1
            name = row.get("exportRelativePath")
            posix = PurePosixPath(name) if isinstance(name, str) else None
            if (
                posix is None or not name.startswith(FAMILY + "/") or "\\" in name
                or posix.is_absolute() or ".." in posix.parts or name in seen
                or type(row.get("length")) is not int
                or not isinstance(row.get("logicalSha256"), str)
            ):
                failures.append(_failure("ledger-row", f"{ledger_path}:{line_number}",
                                         "unique safe LevelScriptData path with length and SHA-256",
                                         _bounded(name if isinstance(name, str) else repr(name))))
                continue
            seen.add(name)
            if row.get("status") == PARTIAL_STATUS:
                partial.append(row)
    declared = ((summary.get("summary") or {}).get("families") or {}).get(FAMILY) or {}
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


def first_stop(data: bytes) -> str:
    """The sequential owner's first refusal, or its completion status."""
    try:
        frame = frame_levelscript_current_action_sequence_leader_enter(data)
    except ValueError as error:
        return OFFSET.sub("offset=<n>", str(error))
    stop = "complete:" + str(frame.get("schemaStatus"))
    if frame.get("schemaStatus") == "partial":
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
) -> dict[str, Any]:
    """Rerun the owner over every current partial LevelScript file and rank first stops."""
    expected = expected_input_set_sha256.upper()
    summary, ledger, failures = _read_summary(summary_path, ledger_path, export_root, expected)
    native, native_failures = _native_gate()
    failures += native_failures
    if failures:
        raise CensusError(failures)
    partial, failures = _read_ledger(ledger_path, summary_path, summary)
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
        stop = first_stop(data)
        if NATIVE_REFUSAL.search(stop):
            failures.append(_failure("native-refusal-stop", source, "a format stop",
                                     _bounded(stop), sha256=digest))
            continue
        rows.append({"path": name, "sha256": digest, "firstStop": stop})
    if failures:
        raise CensusError(failures)

    counts = Counter(row["firstStop"] for row in rows)
    return {
        "schema": SCHEMA,
        "status": "current-source-authenticated",
        "evidenceBoundary": EVIDENCE_BOUNDARY,
        "inputSetSha256": expected,
        "sourceSummarySha256": sha256_file_upper(summary_path),
        "sourceLedgerSha256": ledger["sha256"],
        "sourceLedgerLength": ledger["length"],
        "owner": OWNER,
        "nativeGate": native,
        "partialFiles": len(rows),
        "topFirstStops": counts.most_common(top),
        "rows": rows,
    }


def failure_report(expected_input_set_sha256: str, failures: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
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
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    if args.output.resolve() in {args.summary.resolve(), args.ledger.resolve()}:
        parser.error("--output must not overwrite the JsonData summary or ledger")
    try:
        report = build_census(
            summary_path=args.summary, ledger_path=args.ledger, export_root=args.export_root,
            expected_input_set_sha256=args.expected_input_set_sha256, top=args.top,
        )
    except (CensusError, OSError, ValueError, KeyError) as exc:
        failures = exc.failures if isinstance(exc, CensusError) else [
            _failure("unexpected-input", args.ledger, "readable receipt inputs",
                     _bounded(f"{type(exc).__name__}: {exc}"))
        ]
        failed = failure_report(args.expected_input_set_sha256, failures)
        atomic_write_text(args.output, json.dumps(failed, ensure_ascii=False, indent=2) + "\n")
        print(f"levelscript first-stop census failed ({len(failures)} failures); report={args.output}")
        for failure in failures[:5]:
            print(f"  {failure['check']}: {failure['source']}: expected {failure['expected']!r}, "
                  f"actual {failure['actual']!r}")
        return 2
    atomic_write_text(args.output, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "partialFiles": report["partialFiles"],
                      "topFirstStops": report["topFirstStops"][:10], "report": str(args.output)},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if not __package__:
        raise SystemExit("Run as: python -m scripts.game_data.levelscript_first_stop_census")
    raise SystemExit(main())

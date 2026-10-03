"""Stage or collect bounded LevelScript ReadValue provider observations.

Default mode authenticates the selected native build and one current logical
source, then writes a plan and Frida observer under reports/. It never attaches
to a process unless --pid is supplied. Captures are observations, not automatic
reader admission or evidence of gameplay execution.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.levelscript_on_squad_member_usp_native import load_on_squad_member_usp_contract
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.jsondata_source_provenance import authenticate_current_jsondata_receipt
from scripts.game_data.memorypack.corpus_gate import CensusGateError

SCHEMA = "endfield.levelscript-provider-observer-plan.v2"
AGENT_PATH = Path(__file__).with_suffix(".js")
MAX_SOURCE_BYTES = 1 << 20
MAX_OBSERVATIONS = 32


class CaptureError(ValueError):
    def __init__(self, check: str, source: Any, expected: Any, actual: Any):
        self.diagnostic = {"validator": "levelscriptProviderCapture", "check": check,
                           "source": str(source), "expected": expected, "actual": actual}
        super().__init__(f"{check}: {source}: expected {expected!r}, actual {actual!r}")


def _require(check: str, source: Any, expected: Any, actual: Any) -> None:
    if actual != expected:
        raise CaptureError(check, source, expected, actual)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def authenticate_source(*, export_root: Path, summary_path: Path, ledger_path: Path,
                        source: str, max_source_bytes: int) -> dict[str, Any]:
    """Join exported bytes to a complete saved logical receipt, without freshness."""
    path = PurePosixPath(source)
    if (path.is_absolute() or ".." in path.parts or "\\" in source
            or not source.startswith("LevelScriptData/")):
        raise CaptureError("source-path", source, "safe relative LevelScriptData path", source)
    if not 1 <= max_source_bytes <= MAX_SOURCE_BYTES:
        raise CaptureError("source-cap", source, f"1..{MAX_SOURCE_BYTES}", max_source_bytes)
    raw_summary = summary_path.read_bytes()
    summary = json.loads(raw_summary)
    _require("summary-status", summary_path, "complete", summary.get("status"))
    _require("summary-export-root", summary_path, export_root.resolve().as_posix(),
             Path(summary.get("exportRoot", "")).resolve().as_posix())
    counts = summary.get("summary") or {}
    if type(counts.get("filesSelected")) is not int or counts["filesSelected"] <= 0:
        raise CaptureError("summary-selected-count", summary_path, "positive integer", counts.get("filesSelected"))
    _require("summary-joined", summary_path, counts.get("filesSelected"), counts.get("filesJoined"))
    pin = (summary.get("provenance") or {}).get("outputFiles") or {}
    raw_ledger = ledger_path.read_bytes()
    _require("summary-ledger-join", ledger_path,
             {"length": pin.get("length"), "sha256": str(pin.get("sha256", "")).upper()},
             {"length": len(raw_ledger), "sha256": _sha(raw_ledger)})
    selected = [row for line in gzip.decompress(raw_ledger).splitlines()
                if (row := json.loads(line)).get("exportRelativePath") == source]
    _require("source-ledger-unique", source, 1, len(selected))
    row = selected[0]
    _require("source-family", source, "LevelScriptData", row.get("family"))
    physical = (export_root / path).resolve()
    if not physical.is_relative_to(export_root.resolve()):
        raise CaptureError("source-root", physical, str(export_root.resolve()), str(physical))
    data = physical.read_bytes()
    if not 0 < len(data) <= max_source_bytes:
        raise CaptureError("source-bounded-copy", source, f"1..{max_source_bytes}", len(data))
    _require("source-logical-join", physical,
             {"length": row.get("length"), "sha256": str(row.get("logicalSha256", "")).upper()},
             {"length": len(data), "sha256": _sha(data)})
    return {"relativePath": source, "path": str(physical), "length": len(data), "sha256": _sha(data),
            "inputSetSha256": summary.get("inputSetSha256"), "ledgerSha256": _sha(raw_ledger),
            "summarySha256": _sha(raw_summary)}


def _current_source_receipt(*, summary_path: Path, ledger_path: Path, selected: dict[str, Any],
                            contract: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    try:
        return authenticate_current_jsondata_receipt(summary_path=summary_path, ledger_path=ledger_path,
            expected_summary_sha256=selected["summarySha256"], native_sources=audit["nativeSources"],
            native_inputs=contract["nativeInputs"])
    except CensusGateError as exc:
        diagnostic = exc.diagnostic
        raise CaptureError("source-provenance-" + diagnostic["code"], diagnostic["source"],
                           diagnostic["expected"], diagnostic["actual"]) from exc
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError) as exc:
        raise CaptureError("source-provenance-readable", summary_path,
                           "current selected native/catalog receipt", str(exc)[:500]) from exc


def stage(*, export_root: Path, summary_path: Path, ledger_path: Path, source: str,
          output_dir: Path, game_root: Path | None = None,
          max_source_bytes: int = 65536, max_observations: int = 8) -> dict[str, Any]:
    if not 1 <= max_observations <= MAX_OBSERVATIONS:
        raise CaptureError("observation-cap", output_dir, f"1..{MAX_OBSERVATIONS}", max_observations)
    selected = authenticate_source(export_root=export_root, summary_path=summary_path,
        ledger_path=ledger_path, source=source, max_source_bytes=max_source_bytes)
    contract, audit = load_on_squad_member_usp_contract(game_root=game_root)
    _require("installed-native-inputs", "levelscript_on_squad_member_usp_native", "validated", audit.get("status"))
    source_receipt = _current_source_receipt(summary_path=summary_path, ledger_path=ledger_path,
        selected=selected, contract=contract, audit=audit)
    image = open_native_image(Path(audit["nativeSources"]["GameAssembly.dll"]),
                              Path(audit["nativeSources"]["global-metadata.dat"]))
    context = json.loads((CONTRACTS_DIR / "il2cpp_context_audit_native.json").read_bytes())
    _require("context-schema", "il2cpp_context_audit_native", "endfield.il2cpp-context-audit-native-contract.v3", context.get("schema"))
    _require("context-native-build", "il2cpp_context_audit_native", contract["nativeInputs"], context.get("nativeInputs"))
    windows = [{"startRva": int(start, 16), "endRva": int(end, 16), "sha256": digest}
               for start, end, digest in context["consumerWindows"]]
    image.check_windows(windows, label="levelscriptProviderCapture.context")
    construction = context["pins"]["selectedReaderConstruction"]
    image.check_instruction_windows([[int(rva, 16), raw] for rva, raw in construction["getterLeaves"]],
                                     label="levelscriptProviderCapture.reader")
    # These are structure offsets whose native construction/accessors the
    # context contract proves. A segmented/refilled span is never copied.
    layout = {"totalLength": 0x18, "sourceBase": 0x20, "segmentLength": 0x30,
              "consumed": 0x44, "current": 0x50, "stateBytes": 0x58}
    nested_edges = context["pins"]["selectedReaderCursorConsumers"]["edges"]
    provider = int(nested_edges[-2][2], 16)
    dispatcher = int(nested_edges[-1][2], 16)
    hooks = []

    def add_hook(role: str, rva: int, **extra: Any) -> None:
        hooks.append({"role": role, "rva": rva, "entryHex":
            image.pe.bytes_at_va(image.pe.image_base + rva, 16).hex().upper(), **extra})

    targets = {row["targetRva"] for row in contract["route"]["paramContexts"]}
    _require("shared-readvalue-target", "OnSquadMemberUspReachMax", 1, len(targets))
    add_hook("readvalue", next(iter(targets)), callsites=[{"returnRva": row["callRva"] + 5,
        "fieldName": row["fieldName"], "memberIndex": row["memberIndex"]}
        for row in contract["route"]["paramContexts"]])
    bodies = BodyIndex(image)
    reader_pointer = image.pe.image_base + next(iter(targets))
    caller_ranges = [[reader_pointer - image.pe.image_base,
                      bodies.extents[reader_pointer] - image.pe.image_base]]
    caller_ranges.extend([[start - image.pe.image_base, start + size - image.pe.image_base]
                          for start, size in bodies.chained_fragments.get(reader_pointer, ())])
    add_hook("provider", provider, callerRanges=caller_ranges)
    add_hook("dispatch", dispatcher, callerRanges=caller_ranges)
    for child in contract["children"]:
        for method in child["methods"]:
            add_hook("child", method[3], childKind=child["kind"], methodIndex=method[0], methodName=method[2])
    plan = {"schema": SCHEMA, "status": "preflight-validated", "nativeInputs": contract["nativeInputs"],
            "nativeModulePath": audit["nativeSources"]["GameAssembly.dll"], "source": selected,
            "sourceProvenance": source_receipt,
            "readerLayout": layout, "hooks": hooks, "maxSourceBytes": max_source_bytes,
            "maxObservations": max_observations, "maxEvents": max_observations * 64,
            "contextSnapshotBytes": 64,
            "evidenceBoundary": "conditional observation only: exact Usp callsite, copied logical-source identity, actual MethodInfo/provider-return/dispatch/child-reader and before/after cursor. No automatic parent admission, cache generalization, gameplay execution or whole-owner EOF."}
    selected_after = authenticate_source(export_root=export_root, summary_path=summary_path,
        ledger_path=ledger_path, source=source, max_source_bytes=max_source_bytes)
    _require("source-receipt-drift", source, True, selected_after == selected)
    source_receipt_after = _current_source_receipt(summary_path=summary_path, ledger_path=ledger_path,
        selected=selected, contract=contract, audit=audit)
    _require("source-provenance-drift", summary_path, True, source_receipt_after == source_receipt)
    plan["sourceProvenance"]["recheckedAfterStaging"] = True
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    (output_dir / "observer.js").write_text("const CONFIG = " + json.dumps(plan) + ";\n" + AGENT_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return plan


def collect(plan: dict[str, Any], output_dir: Path, pid: int) -> dict[str, Any]:
    """One normal attach; no escalation or retry after an attach denial."""
    try:
        import frida  # Optional live-capture environment; staging stays stdlib.
    except ImportError as exc:
        raise CaptureError("frida-environment", "--pid", "Python environment with Frida", str(exc)) from exc
    events: list[dict[str, Any]] = []
    copied: dict[str, Any] | None = None
    authenticated_observations: list[int] = []
    errors: list[Any] = []

    def on_message(message: dict[str, Any], data: bytes | None) -> None:
        nonlocal copied
        if message.get("type") == "error":
            errors.append(message.get("description", message))
            return
        event = message.get("payload") or {}
        if len(events) >= plan["maxEvents"] + 16:
            errors.append("host-event-cap")
            return
        if event.get("kind") == "source-copy":
            actual = {"length": len(data or b""), "sha256": _sha(data or b"")}
            expected = {key: plan["source"][key] for key in ("length", "sha256")}
            if actual == expected:
                copied = {**actual, "relativePath": plan["source"]["relativePath"]}
                authenticated_observations.append(event["id"])
                (output_dir / "observed-source.bin").write_bytes(data or b"")
                event["authenticatedSource"] = True
            else:
                errors.append({"check": "observed-source-join", "expected": expected, "actual": actual})
                event["authenticatedSource"] = False
        elif event.get("kind") == "event-cap-exceeded":
            errors.append({"check": "observer-event-cap", "actual": event})
        events.append(event)

    session = None
    script = None
    teardown: dict[str, Any] = {"status": "not-attached"}
    try:
        session = frida.get_local_device().attach(pid)
        script = session.create_script((output_dir / "observer.js").read_text(encoding="utf-8"))
        script.on("message", on_message)
        script.load()
        print("Observer loaded. Exercise the selected source, then press Ctrl+C to stop.", flush=True)
        import threading
        stopped = threading.Event()
        session.on("detached", lambda *args: stopped.set())
        stopped.wait()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        errors.append({"check": "live-attach-or-script-load", "actual": str(exc)})
        raise CaptureError("live-attach-or-script-load", pid, "one normal attach and observer load", str(exc)) from exc
    finally:
        if script is not None:
            try:
                teardown = script.exports_sync.stop()
                script.unload()
            except Exception as exc:
                teardown = {"status": "teardown-failed", "detail": str(exc)}
        if session is not None:
            try:
                session.detach()
                teardown["detached"] = True
            except Exception as exc:
                teardown["detached"] = False
                teardown["detachDetail"] = str(exc)
        receipt = {"schema": "endfield.levelscript-provider-observation.v1", "status": "observation-only",
                   "source": copied, "sourceAuthenticated": copied is not None,
                   "authenticatedObservationIds": authenticated_observations, "events": events,
                   "errors": errors, "teardown": teardown, "evidenceBoundary": plan["evidenceBoundary"]}
        (output_dir / "observation.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Relative current LevelScriptData logical source")
    parser.add_argument("--export-root", type=Path, default=Path("export_full/game/Json"))
    parser.add_argument("--summary", type=Path, default=Path("reports/animestudio/jsondata_current_latest.json"))
    parser.add_argument("--ledger", type=Path, default=Path("reports/animestudio/jsondata_current_files_latest.jsonl.gz"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/game_data/levelscript_provider_capture"))
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--max-source-bytes", type=int, default=65536)
    parser.add_argument("--max-observations", type=int, default=8)
    parser.add_argument("--pid", type=int, help="Explicit live attach; omitted means preflight/staging only")
    args = parser.parse_args(argv)
    try:
        plan = stage(export_root=args.export_root, summary_path=args.summary, ledger_path=args.ledger,
            source=args.source, output_dir=args.output_dir, game_root=args.game_root,
            max_source_bytes=args.max_source_bytes, max_observations=args.max_observations)
        receipt = collect(plan, args.output_dir, args.pid) if args.pid is not None else plan
        print(json.dumps({"status": receipt["status"], "source": args.source, "outputDir": str(args.output_dir)}, indent=2))
        return 0
    except (CaptureError, OSError, ValueError) as exc:
        diagnostic = exc.diagnostic if isinstance(exc, CaptureError) else {"check": "stage-or-capture", "actual": str(exc)}
        print(json.dumps({"status": "failed-closed", "diagnostic": diagnostic}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Regenerate plain Buff formatter-window contracts against the selected build.

Method identities are resolved by declaration names. Every reviewed window must
be attributable to a reviewed method-entry window by exact entry or containment;
old address proximity and a similar new fragment size establish no ownership.
Unattributable helpers and cold fragments remain pending review. Each attributed
method is rebuilt from its complete declared exception-table family, including
noncontiguous chained ranges. The nested type sequence must remain identical
(new unmanaged value-type enum contexts may be excluded as in the frontier
regenerator). Names, anonymous read order, and evidence boundaries are retained.

Special contract shapes are held. Refusal never modifies a reviewed contract;
the CLI emits its pendingReview reason in a report under reports/ when requested.
Run: python -m scripts.game_data.buff_formatter_windows_regenerate --regenerate
     [--write] [--only buff_1f_native.json] [--report reports/buff_repin.json]
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Callable

from scripts.common import check_installed_native_inputs, sha256_file_upper
from scripts.game_data.buff_frontiers_regenerate import _method_row, _nested_contexts
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.levelscript_two_routes_native import RouteRefused, _window, open_selected_build
from scripts.repo_paths import REPO_ROOT


PLAIN_SHAPE = frozenset(("schemaVersion", "methods", "codeWindows", "nestedContexts",
                         "anonymousReadOrder", "boundary"))
HELD_FIELDS = frozenset(("dataWindows", "methodGroups", "header", "hexTag", "tag",
                        "unionRoute", "sourceReadCallSites", "nativeInputs"))
NAME = re.compile(r"buff_[0-9a-f]+_native\.json")


def contract_family(directory: Path = CONTRACTS_DIR) -> list[Path]:
    """Inventory names, including special variants so their holds are reported."""
    return [p for p in sorted(directory.glob("buff_*_native.json")) if NAME.fullmatch(p.name)]


def attribute_windows(contract: dict[str, Any]) -> tuple[list[int], dict[int, str]]:
    """Return window owners and each owner's reviewed primary boundary.

    Only an exact reviewed method entry anchors an interval. A second window
    contained in that reviewed interval inherits its owner. A cold fragment
    outside all anchored intervals has no old unwind membership proof here.
    """
    methods, windows = contract["methods"], contract["codeWindows"]
    entries: dict[int, list[int]] = {}
    for index, row in enumerate(methods):
        if (not isinstance(row, list) or len(row) != 4 or type(row[0]) is not int
                or not isinstance(row[1], str) or not isinstance(row[2], str)
                or type(row[3]) is not int or row[3] <= 0):
            raise RouteRefused(f"method-row={index}:expected-name-and-rva")
        entries.setdefault(row[3], []).append(index)
    anchors, boundaries = [], {}
    for index, window in enumerate(windows):
        if (frozenset(window) != frozenset(("startRva", "endRva", "sha256", "boundary"))
                or type(window["startRva"]) is not int or type(window["endRva"]) is not int
                or not 0 < window["startRva"] < window["endRva"]
                or not isinstance(window["boundary"], str)
                or not re.fullmatch(r"[0-9A-Fa-f]{64}", window["sha256"])):
            raise RouteRefused(f"window={index}:unsupported-shape")
        owners = entries.get(window["startRva"], [])
        if len(owners) > 1:
            raise RouteRefused(f"window={index}:ambiguous-method-entry={owners}")
        if owners:
            owner = owners[0]
            crossed = [i for start, indexes in entries.items()
                       if window["startRva"] < start < window["endRva"] for i in indexes]
            if crossed:
                raise RouteRefused(f"window={index}:crosses-reviewed-method-entries={crossed}")
            if owner in boundaries:
                raise RouteRefused(f"window={index}:duplicate-primary-window:method={owner}")
            anchors.append((window["startRva"], window["endRva"], owner))
            boundaries[owner] = window["boundary"]
    attributed = []
    for index, window in enumerate(windows):
        owners = {owner for lo, hi, owner in anchors
                  if lo <= window["startRva"] < window["endRva"] <= hi}
        if len(owners) != 1:
            raise RouteRefused(
                f"window={index}:old-unwind-owner-unproved:range="
                f"{window['startRva']:#x}..{window['endRva']:#x}"
                f":boundary={window['boundary'][:180]!r}:candidate-methods={sorted(owners)}")
        attributed.append(next(iter(owners)))
    missing = sorted(set(range(len(methods))) - set(attributed))
    if missing:
        raise RouteRefused(f"methods-without-reviewed-windows={missing}")
    return attributed, boundaries


def _current_boundaries(contract: dict[str, Any], methods: list[list[Any]], image: Any) -> dict[int, str]:
    """Revalidate an already regenerated contract using current unwind membership.

    This path is available only when every stored method identity and every
    stored code byte already matches the selected image. It makes regeneration
    repeatable without using an installed family to guess an old cold owner.
    """
    if methods != contract["methods"]:
        raise RouteRefused("current-attribution:method-identities-differ")
    ranges = [(lo, hi, index) for index, row in enumerate(methods)
              for lo, hi, _info in (r["runtimeTriple"]
                    for r in image.unwind_index.family(row[3])["ranges"])]
    boundaries = {}
    for index, window in enumerate(contract["codeWindows"]):
        current = _window(image, image.pe.image_base + window["startRva"],
                          image.pe.image_base + window["endRva"], window["boundary"])
        if current["sha256"] != window["sha256"]:
            raise RouteRefused(f"current-attribution:window={index}:code-bytes-differ")
        owners = {owner for lo, hi, owner in ranges
                  if lo <= window["startRva"] < window["endRva"] <= hi}
        if len(owners) != 1:
            raise RouteRefused(f"current-attribution:window={index}:unwind-owner={sorted(owners)}")
        owner = next(iter(owners))
        if window["startRva"] == methods[owner][3]:
            if owner in boundaries:
                raise RouteRefused(f"current-attribution:method={owner}:duplicate-primary")
            boundaries[owner] = window["boundary"]
    if set(boundaries) != set(range(len(methods))):
        raise RouteRefused("current-attribution:missing-primary-window")
    return boundaries


def regenerate(contract: dict[str, Any], image: Any, *, name: str = "",
               method_resolver: Callable[[Any, list[Any]], list[Any]] = _method_row,
               context_reader: Callable[[Any, dict[str, Any]], list[dict[str, Any]]] = _nested_contexts,
               ) -> dict[str, Any]:
    """Return a rebuilt plain contract or raise a bounded review diagnostic."""
    if name == "validator_02_native.json":
        raise RouteRefused("validator_02:explicit-review-hold")
    held = sorted(set(contract) & HELD_FIELDS)
    if held:
        raise RouteRefused(f"special-shape:held-fields={held}")
    if frozenset(contract) != PLAIN_SHAPE or contract.get("schemaVersion") != 1:
        raise RouteRefused(f"plain-shape:unexpected-fields={sorted(set(contract) - PLAIN_SHAPE)}"
                           f":missing-fields={sorted(PLAIN_SHAPE - set(contract))}")
    if not contract["methods"] or not contract["codeWindows"]:
        raise RouteRefused("plain-shape:empty-methods-or-windows")
    try:
        _owners, boundaries = attribute_windows(contract)
    except RouteRefused as original:
        # A fully regenerated contract includes disjoint chained ranges. They
        # need a current authenticated unwind join, not an old interval guess.
        methods = [method_resolver(image, row) for row in contract["methods"]]
        if methods != contract["methods"]:
            raise original
        boundaries = _current_boundaries(contract, methods, image)
    else:
        methods = [method_resolver(image, row) for row in contract["methods"]]
    base = image.pe.image_base
    windows = []
    for index, row in enumerate(methods):
        family = image.unwind_index.family(row[3])
        if family.get("selectedPrimaryRva") != row[3]:
            raise RouteRefused(f"method={index}:unwind-primary-identity")
        ranges = [r["runtimeTriple"][:2] for r in family["ranges"]]
        if not ranges or ranges[0][0] != row[3]:
            raise RouteRefused(f"method={index}:unwind-missing-primary-range")
        for lo, hi in ranges:
            windows.append(_window(image, base + lo, base + hi, boundaries[index]))
    # Method order is the reviewed context traversal order, not RVA order.
    derived = [context for window in windows for context in context_reader(image, window)]
    reviewed = contract["nestedContexts"]
    expected = [context["typeName"] for context in reviewed]
    if [context["typeName"] for context in derived] != expected:
        derived = [context for context in derived if context["typeKind"] != 0x11]
    actual = [context["typeName"] for context in derived]
    if actual != expected:
        raise RouteRefused(f"nested-type-sequence:reviewed={expected[:40]}:installed={actual[:40]}"
                           f":reviewed-count={len(expected)}:installed-count={len(actual)}")
    contexts = []
    for index, (old, new) in enumerate(zip(reviewed, derived)):
        unknown = sorted(set(old) - set(new))
        if unknown:
            raise RouteRefused(f"context={index}:unresolved-reviewed-fields={unknown}")
        contexts.append({key: new[key] for key in old})
    out = copy.deepcopy(contract)
    out.update(methods=methods, codeWindows=windows, nestedContexts=contexts)
    return out


def _publication_gate(image: Any, inputs: dict[str, str]) -> None:
    """Authenticate the explicitly opened files again after derivation."""
    gate = check_installed_native_inputs(inputs["GameAssembly.dll"], inputs["global-metadata.dat"],
                                        gameassembly=image.gameassembly, metadata=image.metadata_path)
    if gate.status != "validated":
        raise RouteRefused(f"publication-native-inputs:{gate.status}:{gate.detail}")
    unity = image.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file():
        raise RouteRefused(f"publication-native-inputs:missing:{unity}")
    if sha256_file_upper(unity) != inputs["UnityPlayer.dll"].upper():
        raise RouteRefused("publication-native-inputs:mismatched:UnityPlayer.dll hash differs")


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--regenerate", action="store_true", required=True)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--only", action="append", metavar="CONTRACT")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    paths = contract_family()
    if args.only:
        selected = set(args.only)
        paths = [p for p in paths if p.name in selected]
        unknown = selected - {p.name for p in paths}
        if unknown:
            parser.error(f"unknown Buff formatter contract names: {sorted(unknown)}")
    if args.report:
        report = args.report.resolve()
        report_root = (REPO_ROOT / "reports").resolve()
        # All run output stays local; a generated report is never a contract.
        if not report.is_relative_to(report_root):
            parser.error("--report must be below the repository reports/ directory")
    try:
        image, inputs = open_selected_build()
    except (RouteRefused, ValueError, OSError) as error:
        failure = {"status": "pendingReview", "reason": str(error)[:2500], "written": False}
        print(json.dumps(failure), flush=True)
        if args.report:
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps({"nativeInputFailure": failure, "contracts": []}, indent=2)
                              + "\n", encoding="utf-8")
        return 1
    results, candidates, status = [], [], 0
    for path in paths:
        contract = json.loads(path.read_bytes())
        try:
            result = regenerate(contract, image, name=path.name)
        except (RouteRefused, ValueError, KeyError, IndexError) as error:
            row = {"contract": path.name, "status": "pendingReview", "reason": str(error)[:2500],
                   "written": False}
            status = 1
        else:
            row = {"contract": path.name, "status": "regenerated", "written": False,
                   "methodCount": len(result["methods"]), "windowCount": len(result["codeWindows"])}
            candidates.append((path, result, row))
        results.append(row)
    if args.write and candidates:
        try:
            _publication_gate(image, inputs)
        except (RouteRefused, ValueError, OSError) as error:
            status = 1
            for _path, _result, row in candidates:
                row.update(status="pendingReview", reason=str(error)[:2500])
        else:
            for path, result, row in candidates:
                path.write_bytes((json.dumps(result, indent=2, ensure_ascii=False)
                                  .replace("\n", "\r\n") + "\r\n").encode("utf-8"))
                row["written"] = True
    for row in results:
        print(json.dumps(row, ensure_ascii=False), flush=True)
    if args.report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps({"nativeInputs": inputs, "contracts": results}, indent=2,
                                    ensure_ascii=False) + "\n", encoding="utf-8")
    return status


if __name__ == "__main__":
    raise SystemExit(main())

"""Replay only the LevelScript files named by one reviewed route contract.

This projects newly exposed first stops from authenticated source receipts.
It is deliberately scoped: it does not claim a whole JsonData corpus result.
"""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath

from scripts.game_data.levelscript_first_stop_census import first_stop


REPO_ROOT = Path(__file__).resolve().parents[2]


def replay_selected(contract_path: Path, export_root: Path, expected_files: int) -> dict:
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    routes = contract.get("routes")
    if routes is not None and (not isinstance(routes, list) or len(routes) != 1):
        raise ValueError("targetedReplay.contract:single-route-required")
    route = contract.get("route") if routes is None else routes[0]
    route = route or {}
    family = route.get("family")
    if family == "GameCondition":
        receipts = route.get("sourceReceipts")
        boundary = contract.get("evidenceBoundary")
        exact = isinstance(boundary, dict) and isinstance(boundary.get("exact"), str)
    else:
        receipts = contract.get("sourceReceipts") if routes is None else route.get("sourceReceipts")
        exact = contract.get("evidenceBoundary") == "exact"
    if (
        contract.get("status") != "exact-current-build"
        or not exact
        or family not in {"ActionBase", "ActionHeader", "GetterBase", "GameCondition"}
        or type(route.get("tag")) is not int
        or not isinstance(receipts, list) or not receipts
        or type(expected_files) is not int or expected_files < 1
    ):
        raise ValueError("targetedReplay.contract:unreviewed-route-or-scope")

    by_path: dict[str, tuple[str, list[tuple[int, int, str]]]] = {}
    for receipt in receipts:
        if not isinstance(receipt, list) or len(receipt) != 5:
            raise ValueError("targetedReplay.contract:receipt-shape")
        name, digest, start, end, span_digest = receipt
        parts = PurePosixPath(name).parts if isinstance(name, str) else ()
        if (
            len(parts) < 2 or parts[0] != "LevelScriptData"
            or ".." in parts or "\\" in name
            or not isinstance(digest, str) or len(digest) != 64
            or not isinstance(span_digest, str) or len(span_digest) != 64
            or type(start) is not int or type(end) is not int
        ):
            raise ValueError(f"targetedReplay.contract:invalid-source={name}")
        prior = by_path.get(name)
        if prior is not None and prior[0] != digest:
            raise ValueError(f"targetedReplay.contract:source-hash-conflict={name}")
        spans = prior[1] if prior else []
        spans.append((start, end, span_digest))
        by_path[name] = (digest, spans)
    if len(by_path) != expected_files:
        raise ValueError(
            f"targetedReplay.scope:expected={expected_files},actual={len(by_path)}"
        )

    rows = []
    counts: Counter[str] = Counter()
    for name, (digest, spans) in sorted(by_path.items()):
        source = export_root.joinpath(*PurePosixPath(name).parts)
        data = source.read_bytes()
        actual = sha256(data).hexdigest().upper()
        if actual != digest.upper():
            raise ValueError(f"targetedReplay.source:sha256={name}")
        for start, end, span_digest in spans:
            if (
                not 0 <= start < end <= len(data)
                or sha256(data[start:end]).hexdigest().upper() != span_digest.upper()
            ):
                raise ValueError(f"targetedReplay.source:span={name}@{start}:{end}")
        stop = first_stop(data)
        counts[stop] += 1
        rows.append({"path": name, "sha256": actual, "firstStop": stop})
    return {
        "status": "scoped-projection",
        "sourceContract": str(contract_path),
        "sourceContractSha256": sha256(contract_bytes).hexdigest().upper(),
        "route": {"family": route["family"], "tag": route["tag"]},
        "selectedFiles": len(rows),
        "nextFirstStops": dict(counts),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--export-root", type=Path,
                        default=REPO_ROOT / "export_full/game/Json")
    parser.add_argument("--expected-files", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((REPO_ROOT / "reports").resolve()):
        parser.error("--output must be under reports/")
    result = replay_selected(args.contract, args.export_root, args.expected_files)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    print(json.dumps({key: result[key] for key in ("status", "selectedFiles", "nextFirstStops")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

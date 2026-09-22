"""Audit every binary GPU UI configuration against the current VFS ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts.game_data.gpu_ui_binary import decode_damage_text, decode_gpu_ui_root16
from scripts.game_data.jsondata_corpus import _atomic_write, _safe_export_path
from scripts.game_data.memorypack.corpus_gate import (
    DEFAULT_LEDGER, DEFAULT_OUTER, CensusGateError, _guard_output_path,
    _read_outer_and_ledger,
)
from scripts.repo_paths import REPO_ROOT


PREFIX = "Data/Json/GPUISystemConfig/"
ROOT16_FILES = {"buff_icon.json", "buff_icon_main.json", "outscreen_target.json"}
DEFAULT_EXPORT = REPO_ROOT / "export_full/game/Json"
DEFAULT_OUTPUT = REPO_ROOT / "reports/animestudio/gpu_ui_current_latest.json"


def audit_gpu_ui(
    *, expected_input_set_sha256: str, outer_path: Path = DEFAULT_OUTER,
    ledger_path: Path = DEFAULT_LEDGER, export_root: Path = DEFAULT_EXPORT,
) -> dict:
    expected = expected_input_set_sha256.upper()
    _, _, ledger, provenance = _read_outer_and_ledger(
        outer_path, ledger_path, expected_input_set_sha256=expected,
    )
    selected = sorted(
        (row for row in ledger if str(row.get("virtualPath", "")).startswith(PREFIX)),
        key=lambda row: row["virtualPath"],
    )
    if not selected:
        raise ValueError("current VFS ledger contains no GPUISystemConfig files")
    seen: set[str] = set()
    results = []
    root = export_root.resolve()
    for row in selected:
        name = row["virtualPath"]
        if (row.get("blockName") != "JsonData" or row.get("blockTypeValue") != 19
                or row.get("status") != "verified"
                or row.get("boundaryStatus") != "boundary_verified"
                or row.get("inputSetSha256") != expected):
            raise ValueError(f"GPU UI ledger row is not current and authenticated: {name}")
        path, relative, _ = _safe_export_path(root, name)
        if relative.casefold() in seen:
            raise ValueError(f"duplicate GPU UI logical path: {name}")
        seen.add(relative.casefold())
        data = path.read_bytes()
        md5 = hashlib.md5(data).hexdigest().upper()
        if len(data) != row["length"] or md5 != str(row["recomputedFileDataMd5"]).upper():
            raise ValueError(
                f"GPU UI export differs from ledger: {name}; "
                f"length={len(data)}/{row['length']}; "
                f"md5={md5}/{row['recomputedFileDataMd5']}"
            )
        leaf = name.removeprefix(PREFIX)
        if leaf == "damage_text.json":
            decoded = decode_damage_text(data)
        elif leaf in ROOT16_FILES:
            decoded = decode_gpu_ui_root16(data)
        else:
            raise ValueError(f"unsupported GPU UI configuration: {name}")
        if decoded["schemaStatus"] != "named_exact" or decoded["bytesConsumed"] != len(data):
            raise ValueError(f"GPU UI reader did not close its named schema: {name}")
        result = {
            "virtualPath": name, "length": len(data), "logicalMd5": md5,
            "logicalSha256": hashlib.sha256(data).hexdigest().upper(),
            "schemaStatus": decoded["schemaStatus"], "bytesConsumed": decoded["bytesConsumed"],
            "fieldOrder": decoded["fieldOrder"],
            "prefabNames": [prefab["prefabName"] for prefab in decoded["fields"]["prefabs"] or []],
        }
        for key in ("entryCount", "animationCount", "nodeMetadataCount", "renderNodeCount",
                    "rootFieldRanges", "recordSpans", "nativeAudit", "evidenceBoundary"):
            if key in decoded:
                result[key] = decoded[key]
        results.append(result)
    return {
        "schema": "endfield.gpu-ui-current-corpus.v1", "status": "complete",
        "inputSetSha256": expected, "provenance": provenance,
        "filesSelected": len(selected), "filesNamedExact": len(results),
        "logicalBytes": sum(row["length"] for row in results), "files": results,
        "evidenceBoundary": "Every selected GPU UI file is length/MD5-joined to the current VFS ledger and decoded by a sequential named-schema cursor to EOF. Runtime rendering and resource-hash resolution are separate joins.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--outer-summary", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--outer-ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        _guard_output_path(args.output_json, [args.outer_summary, args.outer_ledger, args.export_root])
        report = audit_gpu_ui(
            expected_input_set_sha256=args.expected_input_set_sha256,
            outer_path=args.outer_summary, ledger_path=args.outer_ledger,
            export_root=args.export_root,
        )
        _atomic_write(args.output_json, (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    except (CensusGateError, OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "failed", "diagnostic": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps({key: report[key] for key in ("status", "filesSelected", "filesNamedExact", "logicalBytes")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

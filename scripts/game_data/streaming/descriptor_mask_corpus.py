"""Audit authenticated Init descriptor IDs against the selected native mask width.

This is a structural range check, not an ID-to-component dictionary. A limited
run is diagnostic and cannot publish a complete current-corpus result.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

from scripts.game_data.streaming.descriptor_component_index_gate import _authenticated_decoded_file
from scripts.game_data.streaming.descriptor_mask_native import validate_descriptor_mask_native
from scripts.game_data.streaming.descriptor_name_corpus import (
    DEFAULT_AUDIT, DEFAULT_LEDGER, _selected_rows,
)
from scripts.game_data.streaming.descriptor_names import _table_vector
from scripts.game_data.streaming.framing import _bounded_vector, _root_layout
from scripts.game_data.streaming.native import validate_streaming_field2_native_contract
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.streaming-descriptor-mask-corpus.v1"
DEFAULT_OUTPUT = REPO_ROOT / "reports/chunk_data/descriptor_mask_corpus_latest.json"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _inspect_decoded(decoded: bytes) -> tuple[Counter[int], int, int, int]:
    """Return ID histogram, group count, descriptor count, max group width."""
    root = _root_layout(decoded)
    root["tableOffset"] = root["rootOffset"]
    groups = _table_vector(decoded, root, 7, "root field 7 groups")
    ids: Counter[int] = Counter()
    descriptors = max_group_width = 0
    for group in groups:
        start, count, _end = _bounded_vector(decoded, group, 3, 8, "group descriptors")
        descriptors += count
        max_group_width = max(max_group_width, count)
        for index in range(count):
            raw_id, stride, reserved = struct.unpack_from(
                "<hHI", decoded, start + 4 + index * 8
            )
            if stride == 0 or reserved:
                raise ValueError(f"descriptor[{index}]:invalid stride or reserved word")
            ids[raw_id] += 1
    return ids, len(groups), descriptors, max_group_width


def audit_descriptor_mask_corpus(
    *, game_root: Path, expected_input_set_sha256: str,
    audit_path: Path = DEFAULT_AUDIT, ledger_path: Path = DEFAULT_LEDGER,
    limit: int | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"schema": SCHEMA, "status": "validation_failed"}
    first_root = validate_streaming_field2_native_contract(game_root=game_root)
    if first_root["status"] != "validated":
        result["reason"] = {"firstRootStatus": first_root["status"],
                            "failures": first_root.get("validationFailures", [])[:5]}
        return result
    mask = validate_descriptor_mask_native(game_root=game_root)
    if mask["status"] != "validated":
        result["reason"] = {"maskNativeStatus": mask["status"], "detail": mask.get("reason", "")}
        return result
    try:
        audit = json.loads(Path(audit_path).read_text(encoding="utf-8-sig"))
        input_set = audit.get("inputSetSha256")
        if not audit.get("summary", {}).get("fullAuditPassed") or not isinstance(input_set, str):
            raise ValueError("vfs-audit:not-current-complete")
        if len(input_set) != 64 or input_set != expected_input_set_sha256.upper():
            raise ValueError("vfs-audit:expected-input-set-mismatch")
        sources = _selected_rows(Path(ledger_path), input_set)
        if limit is not None and limit <= 0:
            raise ValueError("limit:expected-positive")
        paths = sorted(sources)
        selected = paths if limit is None else paths[:limit]
        ids: Counter[int] = Counter()
        total_groups = total_descriptors = max_group_width = 0
        failures: list[dict[str, str]] = []
        succeeded = 0
        for path in selected:
            try:
                decoded, _packed_md5, _decoded_sha = _authenticated_decoded_file(sources[path], path)
                file_ids, groups, descriptors, width = _inspect_decoded(decoded)
                ids.update(file_ids)
                total_groups += groups
                total_descriptors += descriptors
                max_group_width = max(max_group_width, width)
                succeeded += 1
            except (OSError, ValueError, KeyError, IndexError, struct.error) as error:
                if len(failures) < 25:
                    failures.append({"virtualPath": path, "error": str(error)[:500]})
        out_of_range = {key: value for key, value in sorted(ids.items()) if key < 0 or key >= 128}
        complete = limit is None and succeeded == len(paths) and not failures
        status = ("complete-current-mask-range" if complete and not out_of_range else
                  "complete-range-counterexample" if complete else
                  "bounded-probe" if limit is not None and not failures else "validation_failed")
        return {
            "schema": SCHEMA, "status": status, "inputSetSha256": input_set,
            "vfsAuditSha256": _sha256_file(Path(audit_path)),
            "vfsLedgerSha256": _sha256_file(Path(ledger_path)),
            "firstRootNativeContractSha256": first_root["contractSha256"],
            "maskNativeContractSha256": mask["contractSha256"],
            "allInitFilesInLedger": len(paths), "filesSelected": len(selected),
            "filesSucceeded": succeeded, "groupCount": total_groups,
            "descriptorCount": total_descriptors, "maxDescriptorsPerGroup": max_group_width,
            "idCounts": {str(key): value for key, value in sorted(ids.items())},
            "outOfMaskRangeIdCounts": {str(key): value for key, value in out_of_range.items()},
            "failures": failures,
            "evidenceBoundary": (
                "The selected native setup reads signed descriptor IDs as bit positions "
                "in a two-QWORD anonymous mask. Every counted Init source is re-read from "
                "its authenticated physical VFS chunk and framed independently. The ID "
                "range is a current-corpus observation only; no ID is assigned a named "
                "component, and the native setup is not a general validity check."
            ),
        }
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        result["reason"] = str(error)
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--limit", type=int, help="diagnostic first-N probe")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if (REPO_ROOT / "reports").resolve() not in output.parents:
        parser.error("--output must be under reports/")
    report = audit_descriptor_mask_corpus(
        game_root=args.game_root, expected_input_set_sha256=args.expected_input_set_sha256,
        audit_path=args.audit, ledger_path=args.ledger, limit=args.limit,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(f"Init descriptor mask corpus: {report['status']} "
          f"{report.get('filesSucceeded', 0)}/{report.get('filesSelected', 0)}")
    if report["status"] == "validation_failed":
        print(report.get("reason", report.get("failures", [])[:2]))
    return 1 if report["status"] == "validation_failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())

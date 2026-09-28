"""Audit authenticated Init descriptor IDs against the selected native mask width.

This is a structural range check, not an ID-to-component dictionary. A limited
run is diagnostic and cannot publish a complete current-corpus result.

A complete run rereads every current Init logical file, checks its physical
VFS MD5, frames its groups and counts signed descriptor IDs. Every observed
ID is nonnegative and inside the two-QWORD mask, including IDs that select
the second QWORD; that is a current-input observation, not a rule for
future inputs.

The same pass compares each group's inline 16-byte field 0, read as one
little-endian 128-bit mask, with the set of that group's own field-3
descriptor IDs (``field0DescriptorIdMask``). Equality in every group makes
field 0 the group's descriptor-ID mask -- the same two-QWORD mask the native
setup builds -- and refutes naming its bits by ``StreamingComponentType``,
whose numeric equality ``descriptor_component_index_gate`` already refuses.

The IDs are read from slot 7 through the maintained framing reader and stay
anonymous packed-column positions. Both selected native gates (first root
and descriptor mask) must validate. Pass ``--game-root`` and the VFS audit's
``--expected-input-set-sha256``; the default report is
``reports/chunk_data/descriptor_mask_corpus_latest.json``.
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
from scripts.game_data.streaming.framing import _bounded_vector, _field_address, _root_layout
from scripts.game_data.streaming.native import validate_streaming_field2_native_contract
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.streaming-descriptor-mask-corpus.v2"
DEFAULT_OUTPUT = REPO_ROOT / "reports/chunk_data/descriptor_mask_corpus_latest.json"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _field0_mask_bits(decoded: bytes, group: dict[str, Any]) -> set[int] | None:
    """The set bits of a group's inline 128-bit field 0, or None when absent."""
    address = _field_address(group, 0)
    if address is None:
        return None
    if address + 16 > int(group["tableOffset"]) + int(group["objectSize"]):
        raise ValueError("group field 0:128-bit mask exceeds table object")
    low, high = struct.unpack_from("<QQ", decoded, address)
    mask = low | (high << 64)
    return {bit for bit in range(128) if mask >> bit & 1}


def _inspect_decoded(
    decoded: bytes, field0: dict[str, Any] | None = None,
) -> tuple[Counter[int], int, int, int]:
    """Return ID histogram, group count, descriptor count, max group width.

    When ``field0`` is given, each group's field-0 mask is compared with the
    set of that group's own descriptor IDs and the tally is added to it.
    """
    root = _root_layout(decoded)
    root["tableOffset"] = root["rootOffset"]
    groups = _table_vector(decoded, root, 7, "root field 7 groups")
    ids: Counter[int] = Counter()
    descriptors = max_group_width = 0
    for group_index, group in enumerate(groups):
        start, count, _end = _bounded_vector(decoded, group, 3, 8, "group descriptors")
        descriptors += count
        max_group_width = max(max_group_width, count)
        group_ids: set[int] = set()
        for index in range(count):
            raw_id, stride, reserved = struct.unpack_from(
                "<hHI", decoded, start + 4 + index * 8
            )
            if stride == 0 or reserved:
                raise ValueError(f"descriptor[{index}]:invalid stride or reserved word")
            ids[raw_id] += 1
            group_ids.add(raw_id)
        if field0 is not None:
            bits = _field0_mask_bits(decoded, group)
            if bits is None:
                field0["groupsWithoutField0"] += 1
            elif bits == group_ids:
                field0["groupsEqual"] += 1
            else:
                field0["groupsDiffer"] += 1
                if len(field0["examples"]) < 10:
                    field0["examples"].append({
                        "group": group_index,
                        "field0Bits": sorted(bits), "descriptorIds": sorted(group_ids),
                    })
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
        field0: dict[str, Any] = {
            "groupsEqual": 0, "groupsDiffer": 0, "groupsWithoutField0": 0, "examples": [],
        }
        succeeded = 0
        for path in selected:
            try:
                decoded, _packed_md5, _decoded_sha = _authenticated_decoded_file(sources[path], path)
                file_ids, groups, descriptors, width = _inspect_decoded(decoded, field0)
                for example in field0["examples"]:
                    example.setdefault("virtualPath", path)
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
        field0_status = (
            "bounded-probe" if not complete else
            "every-group-field0-equals-its-descriptor-ids"
            if field0["groupsDiffer"] == 0 and field0["groupsWithoutField0"] == 0
            and field0["groupsEqual"] == total_groups else
            "field0-descriptor-id-counterexample"
        )
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
            "field0DescriptorIdMask": {"status": field0_status, **field0},
            "failures": failures,
            "evidenceBoundary": (
                "The selected native setup reads signed descriptor IDs as bit positions "
                "in a two-QWORD anonymous mask. Every counted Init source is re-read from "
                "its authenticated physical VFS chunk and framed independently. The ID "
                "range is a current-corpus observation only; no ID is assigned a named "
                "component, and the native setup is not a general validity check. "
                "Each group's inline 128-bit field 0 is compared with the set of that "
                "group's own descriptor IDs; equality in every group makes field 0 the "
                "group's descriptor-ID mask, which still names no component."
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

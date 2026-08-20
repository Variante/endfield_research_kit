#!/usr/bin/env python3
"""Verify concrete secondary-dynamics generic slots without closing generics.

The job contract measures each closed NativeArray/NativeReference field slot
from the pinned MetadataRegistration field offsets and the native-size tail.
The inner contract only supplies accessor offsets and lower bounds for the open
generic definitions.  This verifier joins those two boundaries and refuses to
promote the concrete 16-byte job slot to a generic type-size claim.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TOOLS_ROOT = Path(__file__).resolve().parent
LAB_ROOT = TOOLS_ROOT.parent
SOURCE_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
JOB_OUTPUT = SOURCE_ROOT / "secondary_dynamics_job_layout_contract.json"
INNER_OUTPUT = SOURCE_ROOT / "secondary_dynamics_inner_layout_contract.json"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import build_secondary_dynamics_inner_layout_contract as inner_builder
import build_secondary_dynamics_job_layout_contract as job_builder


class ContractError(RuntimeError):
    """Raised when either pinned layout boundary fails closed."""


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ContractError(f"missing contract: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid contract JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"contract root is not an object: {path}")
    return value


def _validate_combined(job: dict[str, Any], inner: dict[str, Any]) -> dict[str, Any]:
    if job.get("status") != "outer_job_layout_closed":
        raise ContractError("job contract is not closed at the outer-job boundary")
    if not job.get("outer_job_layout_recovered"):
        raise ContractError("job contract lacks outer_job_layout_recovered")
    if job.get("job_payload_layout_recovered"):
        raise ContractError("job contract incorrectly claims full payload recovery")
    basis = job.get("layoutBasis", {}).get("concreteGenericSlotWidths", {})
    if basis.get("status") != "closed_from_adjacent_offsets_and_native_size_tail":
        raise ContractError("concrete generic slot-width boundary is not closed")
    if basis.get("genericTypeSizeClaimed") is not False:
        raise ContractError("concrete slot contract makes a generic type-size claim")
    if basis.get("abiAlignmentBytes") != job_builder.NATIVE_ABI_ALIGNMENT_BYTES:
        raise ContractError("job ABI alignment evidence drift")

    if inner.get("status") != "inner_payload_offsets_closed_size_unresolved_burst_mapping_unresolved":
        raise ContractError("inner contract is not at its fail-closed size boundary")
    if not inner.get("inner_payload_offsets_recovered"):
        raise ContractError("inner contract lacks recovered accessor offsets")
    if inner.get("inner_payload_layout_recovered"):
        raise ContractError("inner contract incorrectly claims generic size recovery")
    if inner.get("job_payload_layout_recovered"):
        raise ContractError("inner contract incorrectly claims job payload recovery")

    lower_bounds: dict[str, int] = {}
    for kind, key in (("NativeArray", "nativeArray"), ("NativeReference", "nativeReference")):
        record = inner.get(key)
        if not isinstance(record, dict) or record.get("nativeSizeBytes") is not None:
            raise ContractError(f"{kind} generic native size is unexpectedly closed")
        evidence = record.get("nativeSizeEvidence", {})
        if evidence.get("status") != "lower_bound_only":
            raise ContractError(f"{kind} generic size evidence boundary drift")
        lower_bound = evidence.get("lowerBoundBytes")
        if not isinstance(lower_bound, int) or lower_bound <= 0:
            raise ContractError(f"{kind} generic lower bound is invalid")
        lower_bounds[kind] = lower_bound

    counts = {"NativeArray": 0, "NativeReference": 0}
    widths: dict[str, set[int]] = {"NativeArray": set(), "NativeReference": set()}
    for job_row in job.get("jobs", []):
        fields = job_row.get("fields", [])
        if not isinstance(fields, list):
            raise ContractError(f"{job_row.get('type', '<unknown>')} fields are not a list")
        for field in fields:
            kind = field.get("kind")
            if kind not in widths:
                continue
            counts[kind] += 1
            width = field.get("slotWidthBytes")
            evidence = field.get("slotWidthEvidence")
            if not isinstance(width, int) or width <= 0:
                raise ContractError(f"{job_row.get('type')} {field.get('name')} has invalid slot width")
            if not isinstance(evidence, dict) or evidence.get("status") != "closed":
                raise ContractError(f"{job_row.get('type')} {field.get('name')} lacks closed slot evidence")
            if evidence.get("slotSpanBytes") != width:
                raise ContractError(f"{job_row.get('type')} {field.get('name')} width/span drift")
            if evidence.get("genericTypeSizeClaimed") is not False:
                raise ContractError(f"{job_row.get('type')} {field.get('name')} claims generic size")
            if width < lower_bounds[kind]:
                raise ContractError(
                    f"{job_row.get('type')} {field.get('name')} concrete slot {width} "
                    f"is below inner {kind} lower bound {lower_bounds[kind]}"
                )
            widths[kind].add(width)

    if not all(counts.values()):
        raise ContractError(f"generic field coverage is incomplete: {counts}")
    # These are exact facts about the four pinned closed job instances.  They
    # do not alter the unresolved generic nativeSizeBytes boundary above.
    for kind, observed in widths.items():
        if observed != {16}:
            raise ContractError(f"pinned concrete {kind} slot widths drifted: {sorted(observed)}")
    return {
        "status": "validated",
        "concreteSlotWidthsBytes": {kind: 16 for kind in widths},
        "genericSizeStatus": "unresolved_lower_bound_only",
        "fieldCounts": counts,
        "genericLowerBoundsBytes": lower_bounds,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-contract", type=Path, default=JOB_OUTPUT)
    parser.add_argument("--inner-contract", type=Path, default=INNER_OUTPUT)
    parser.add_argument("--game-assembly", type=Path, default=job_builder.DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=job_builder.DEFAULT_METADATA)
    args = parser.parse_args()
    try:
        # Both builders invoke common.check_installed_native_inputs with these
        # explicit paths.  No module-global game root or stale JSON can pass
        # the native gate.
        expected_job = job_builder.build_contract(
            game_assembly=args.game_assembly,
            metadata=args.metadata,
        )
        expected_inner = inner_builder.build_contract(
            game_assembly=args.game_assembly,
            metadata=args.metadata,
        )
        actual_job = _load_json(args.job_contract)
        actual_inner = _load_json(args.inner_contract)
        if actual_job != expected_job:
            raise ContractError("job contract differs from a fresh native reconstruction")
        if actual_inner != expected_inner:
            raise ContractError("inner contract differs from a fresh native reconstruction")
        print(json.dumps(_validate_combined(actual_job, actual_inner)))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError,
            job_builder.ContractError, inner_builder.ContractError, ContractError) as exc:
        print(json.dumps({"status": "unavailable", "validationFailures": [str(exc)]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

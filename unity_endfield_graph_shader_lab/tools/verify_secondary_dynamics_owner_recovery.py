#!/usr/bin/env python3
"""Verify the current installed Character Info secondary-dynamics contract."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = LAB_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from build_secondary_dynamics_owner_recovery import OUTPUT, build_contract  # noqa: E402


VALIDATOR = "verify_secondary_dynamics_owner_recovery"
# The published common-invariant block is explicitly the reviewed Character
# Info cohort.  The three earlier postmodels remain in the owner contract but
# carry their own authored LOD/update values and must not be compared to this
# cohort's values.
COMMON_INVARIANT_ACTORS = ("lastrite", "wulfa", "zhuangfy", "lizhiyan")


def _component_totals(contract: dict[str, Any]) -> dict[str, int]:
    """Sum the per-actor source inventory, never a verifier-local pin."""

    totals: Counter[str] = Counter()
    for actor in contract.get("actors", {}).values():
        totals.update(
            {
                str(component): int(count)
                for component, count in (
                    actor.get("dynamic_component_counts") or {}
                ).items()
            }
        )
    return dict(sorted(totals.items()))


def _actor_source(contract: dict[str, Any], token: str) -> dict[str, Any]:
    """Return the pinned source path/hash context for one actor inventory."""

    actor = (contract.get("actors") or {}).get(token) or {}
    target_filter = actor.get("target_filter") or {}
    if target_filter.get("repo_path") or target_filter.get("path_at_recovery"):
        return {
            "path": target_filter.get("repo_path")
            or target_filter.get("path_at_recovery"),
            "sha256": target_filter.get("sha256"),
        }

    # Keep diagnostics useful for malformed/partial contracts too.  The VFS
    # chunk is the next source boundary recorded by the owner contract.
    chunk = actor.get("source_chunk")
    chunk_record = (contract.get("source_build", {}).get("vfs_chunks") or {}).get(
        chunk, {}
    )
    return {
        "path": chunk_record.get("repo_path") or chunk_record.get("path_at_recovery"),
        "sha256": chunk_record.get("sha256"),
    }


def _source_pair(
    expected: dict[str, Any], observed: dict[str, Any], token: str
) -> dict[str, Any]:
    expected_source = _actor_source(expected, token)
    actual_source = _actor_source(observed, token)
    return {
        "path": actual_source.get("path") or expected_source.get("path"),
        "expected_sha256": expected_source.get("sha256"),
        "actual_sha256": actual_source.get("sha256"),
    }


def _aggregate_source_inputs(contract: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "actor": token,
            "path": source["path"],
            "sha256": source["sha256"],
        }
        for token in sorted(contract.get("actors", {}))
        for source in [_actor_source(contract, token)]
    ]


def owner_contract_total_diagnostics(contract: dict[str, Any]) -> list[dict[str, Any]]:
    """Report an internally inconsistent owner contract without accepting it."""

    expected_totals = {
        str(component): int(count)
        for component, count in (contract.get("totals") or {}).items()
    }
    actual_totals = _component_totals(contract)
    diagnostics: list[dict[str, Any]] = []
    for component in sorted(set(expected_totals) | set(actual_totals)):
        expected_count = expected_totals.get(component, 0)
        actual_count = actual_totals.get(component, 0)
        if expected_count == actual_count:
            continue
        diagnostics.append(
            {
                "validator": VALIDATOR,
                "check": "owner_contract_totals_match_actor_source_inventory",
                "actor": "<aggregate>",
                "type": component,
                "expected": expected_count,
                "actual": actual_count,
                "source": {
                    "path": "actors.*.dynamic_component_counts",
                    "expected_sha256": None,
                    "actual_sha256": None,
                    "inputs": _aggregate_source_inputs(contract),
                },
            }
        )
    return diagnostics


def contract_drift_diagnostics(
    expected: dict[str, Any], observed: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return bounded, actionable diagnostics for source/contract drift."""

    diagnostics: list[dict[str, Any]] = []
    expected_actors = expected.get("actors") or {}
    observed_actors = observed.get("actors") or {}
    for token in sorted(set(expected_actors) | set(observed_actors)):
        expected_actor = expected_actors.get(token) or {}
        observed_actor = observed_actors.get(token) or {}
        expected_counts = {
            str(component): int(count)
            for component, count in (
                expected_actor.get("dynamic_component_counts") or {}
            ).items()
        }
        observed_counts = {
            str(component): int(count)
            for component, count in (
                observed_actor.get("dynamic_component_counts") or {}
            ).items()
        }
        source = _source_pair(expected, observed, token)
        for component in sorted(set(expected_counts) | set(observed_counts)):
            expected_count = expected_counts.get(component, 0)
            actual_count = observed_counts.get(component, 0)
            if expected_count == actual_count:
                continue
            diagnostics.append(
                {
                    "validator": VALIDATOR,
                    "check": "owner_contract_matches_actor_source_inventory",
                    "actor": token,
                    "type": component,
                    "expected": expected_count,
                    "actual": actual_count,
                    "source": source,
                }
            )

        for source_name in ("target_filter", "hierarchy_name_map", "overview_controller"):
            expected_record = expected_actor.get(source_name) or {}
            observed_record = observed_actor.get(source_name) or {}
            expected_hash = expected_record.get("sha256")
            actual_hash = observed_record.get("sha256")
            if expected_hash == actual_hash:
                continue
            expected_path = expected_record.get("repo_path") or expected_record.get(
                "path_at_recovery"
            )
            actual_path = observed_record.get("repo_path") or observed_record.get(
                "path_at_recovery"
            )
            diagnostics.append(
                {
                    "validator": VALIDATOR,
                    "check": "owner_contract_source_hashes_match",
                    "actor": token,
                    "type": source_name,
                    "expected": expected_hash,
                    "actual": actual_hash,
                    "source": {
                        "path": actual_path or expected_path,
                        "expected_sha256": expected_hash,
                        "actual_sha256": actual_hash,
                    },
                }
            )

    expected_totals = {
        str(component): int(count)
        for component, count in (expected.get("totals") or {}).items()
    }
    observed_totals = {
        str(component): int(count)
        for component, count in (observed.get("totals") or {}).items()
    }
    for component in sorted(set(expected_totals) | set(observed_totals)):
        expected_count = expected_totals.get(component, 0)
        actual_count = observed_totals.get(component, 0)
        if expected_count == actual_count:
            continue
        diagnostics.append(
            {
                "validator": VALIDATOR,
                "check": "owner_contract_totals_match_source_reconstruction",
                "actor": "<aggregate>",
                "type": component,
                "expected": expected_count,
                "actual": actual_count,
                "source": {
                    "path": "actors.*.dynamic_component_counts",
                    "expected_sha256": None,
                    "actual_sha256": None,
                    "inputs": {
                        "expected": _aggregate_source_inputs(expected),
                        "actual": _aggregate_source_inputs(observed),
                    },
                },
            }
        )

    # A source/runtime field can drift without touching component counts. Keep
    # the validator fail-closed and still provide a structured root diagnostic.
    if expected != observed and not diagnostics:
        diagnostics.append(
            {
                "validator": VALIDATOR,
                "check": "owner_contract_matches_source_reconstruction",
                "actor": "<contract>",
                "type": "<non-component-field>",
                "expected": "published owner contract",
                "actual": "fresh source reconstruction",
                "source": {
                    "path": str(OUTPUT),
                    "expected_sha256": None,
                    "actual_sha256": None,
                },
            }
        )
    return diagnostics


def _format_diagnostics(diagnostics: list[dict[str, Any]]) -> str:
    return json.dumps(
        {"validator": VALIDATOR, "failures": diagnostics},
        ensure_ascii=False,
        sort_keys=True,
    )


def fail(message: str, diagnostics: list[dict[str, Any]] | None = None) -> None:
    detail = ""
    if diagnostics:
        detail = "\n" + _format_diagnostics(diagnostics)
    raise SystemExit(f"FAIL: {message}{detail}")


def main() -> int:
    if not OUTPUT.is_file():
        fail(f"missing recovery contract: {OUTPUT}")
    expected = json.loads(OUTPUT.read_text(encoding="utf-8"))
    observed = build_contract()
    total_diagnostics = owner_contract_total_diagnostics(expected)
    if total_diagnostics:
        fail(
            "published owner contract totals disagree with actor source inventory",
            total_diagnostics,
        )
    if observed != expected:
        fail(
            "installed/source evidence no longer matches the reviewed contract; "
            "run build_secondary_dynamics_owner_recovery.py and review the diff",
            contract_drift_diagnostics(expected, observed),
        )

    totals = expected["totals"]
    if totals != _component_totals(expected):
        # This is guarded above; retain a separate named check if the contract
        # shape changes in the future and make the failure fail closed.
        fail(
            "unexpected dynamic component totals",
            owner_contract_total_diagnostics(expected),
        )

    common = expected["common_serialized_invariants"]
    for token in COMMON_INVARIANT_ACTORS:
        actor = expected["actors"].get(token)
        if actor is None:
            fail(
                "common serialized invariant actor is missing",
                [
                    {
                        "validator": VALIDATOR,
                        "check": "common_invariant_actor_present",
                        "actor": token,
                        "type": "BeyondDynamicBone.BeyondBoneCloth",
                        "expected": "actor present",
                        "actual": "actor missing",
                        "source": _actor_source(expected, token),
                    }
                ],
            )
        if actor["overview_controller"]["magica_cloth_weight"] != 0.01:
            fail(f"{token}: Overview MagicaClothWeight is no longer 0.01")
        for cloth in actor["cloths"]:
            parameters = cloth["parameters"]
            comparisons = {
                "cloth_type": common["cloth_type"],
                "update_mode": common["update_mode"],
                "animator_ability_lod_threshold": common[
                    "animator_ability_lod_threshold"
                ],
                "animator_lod_threshold": common["animator_lod_threshold"],
                "lod_fade_time": common["lod_fade_time"],
                "simulate_weight": common["authored_simulate_weight"],
                "blend_weight": common["blend_weight"],
            }
            for key, value in comparisons.items():
                if parameters[key] != value:
                    fail(f"{token}/{cloth['game_object_path']}: {key} changed")
            if parameters["culling"]["cameraCullingMode"] != common[
                "camera_culling_mode"
            ]:
                fail(f"{token}/{cloth['game_object_path']}: culling mode changed")
            if parameters["culling"]["distanceCullingLength"]["use"] != common[
                "distance_culling_enabled"
            ]:
                fail(f"{token}/{cloth['game_object_path']}: distance culling changed")
            if cloth["selection"]["prebuild_enabled"] != common["prebuild_enabled"]:
                fail(f"{token}/{cloth['game_object_path']}: prebuild state changed")

    environment = expected["charinfo_environment"]
    if any(
        environment[key] != 0
        for key in (
            "cloth_component_count",
            "collider_component_count",
            "wind_zone_component_count",
        )
    ):
        fail("Character Info environment unexpectedly owns dynamics")

    audit = expected["runtime"]["charui_model_owner"]["all_method_call_audit"]
    if audit["mapped_method_count"] != 68:
        fail("CharUIModelMono method surface changed")
    if audit["dynamic_system_direct_calls"] != [
        {
            "caller": "_UpdateMagicaClothWeight",
            "caller_method_index": 49735,
            "callee": "BeyondDynamicBone.BeyondBoneCloth.SetClothSimulateWeight",
        }
    ]:
        fail("CharUIModelMono gained or lost a direct secondary-dynamics call")

    if expected["runtime"]["manager"]["player_loop_insertion_count"] != 7:
        fail("BeyondDynamicBone PlayerLoop insertion count changed")
    if expected["ifix_boundary"]["beyond_dynamic_bone_patch_present"]:
        fail("installed Persistent overlay now replaces BeyondDynamicBone")
    if expected["ifix_boundary"]["charui_model_target_present"]:
        fail("installed Persistent overlay now replaces CharUIModelMono")
    if expected["implementation_boundary"]["lab_solver_implemented"]:
        fail("contract must not claim an unverified lab solver")

    cloth_count = totals.get("BeyondDynamicBone.BeyondBoneCloth", 0)
    collider_count = sum(
        count
        for component, count in totals.items()
        if component.endswith("Collider")
    )
    print(
        "PASS: current installed BeyondDynamicBone ownership is hash-pinned for "
        f"all reviewed actors ({cloth_count} cloths, {collider_count} colliders); "
        "CharUIModelMono weight/lifecycle and current IFix non-replacement are unchanged"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

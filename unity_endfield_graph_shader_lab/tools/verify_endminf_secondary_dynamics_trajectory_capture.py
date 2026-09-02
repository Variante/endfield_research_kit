#!/usr/bin/env python3
"""Verify a bounded Endminf four-owner TransformAccess trajectory capture."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    REPO / "reports/assets/character_recovery"
    / "endminf_secondary_dynamics_trajectory_capture_latest.json"
)
STATIC_OWNER_NAMES = {
    "Ribbon2": "MC_Ribbon2",
    "Hair": "MC_Hair",
    "Ribbon": "MC_Ribbon",
    "Coat": "MC_Coat",
}
OWNER_BY_STATIC_NAME = {
    static_name: owner for owner, static_name in STATIC_OWNER_NAMES.items()
}
TRANSFORM_READ_CONTRACT_SHA256 = (
    "67167af46bc3363f2b0676f82896fecbfe7d3d22c7e218e3e7748006afd21d9a")
GAME_ASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce")
GLOBAL_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e")
OVERVIEW_START_FULL_PATH_HASH = 1560421867
OVERVIEW_LOOP_FULL_PATH_HASH = -1345940313
TRANSFORM_READ_CONTRACT = (
    REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
    / "Generated/OriginalData/CharInfoPresentation"
    / "secondary_dynamics_transform_read_contract.json"
)


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def finite_vector(row: dict[str, Any], key: str, lanes: int) -> None:
    value = row.get(key)
    require(isinstance(value, list) and len(value) == lanes,
            f"{key} is not a {lanes}-lane vector")
    require(all(isinstance(item, (int, float)) and math.isfinite(item)
                for item in value), f"{key} contains a non-finite lane")


def usable_quaternion(row: dict[str, Any], key: str) -> None:
    finite_vector(row, key, 4)
    value = row[key]
    require(sum(float(item) * float(item) for item in value) > 1.0e-8,
            f"{key} is degenerate")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_expected_owner_hierarchy_paths() -> dict[str, list[str]]:
    contract_bytes = TRANSFORM_READ_CONTRACT.read_bytes()
    require(hashlib.sha256(contract_bytes).hexdigest() ==
            TRANSFORM_READ_CONTRACT_SHA256,
            "static secondary-dynamics transform-read contract hash drifted")
    contract = json.loads(contract_bytes)
    require(contract.get("schema") ==
            "endfield.charinfo.secondary-dynamics-transform-read.v1" and
            contract.get("status") ==
            "endminf_transform_read_callback_closed_relative_and_cross_frame_telemetry_required" and
            contract.get("nativeGate", {}).get("status") == "validated",
            "static secondary-dynamics transform-read contract is not validated")
    gate = contract["nativeGate"]
    require(gate.get("gameAssembly", {}).get("sha256") ==
            GAME_ASSEMBLY_SHA256 and
            gate.get("globalMetadata", {}).get("sha256") ==
            GLOBAL_METADATA_SHA256,
            "static secondary-dynamics native build hashes drifted")
    endminf = contract.get("endminf", {})
    require(endminf.get("ownerOrder") == list(STATIC_OWNER_NAMES.values()),
            "static Endminf owner order drifted")
    entries = endminf.get("orderedEntries")
    require(isinstance(entries, list) and entries,
            "static Endminf transform-read entries are incomplete")
    owners = endminf.get("owners")
    require(isinstance(owners, list) and len(owners) == 4,
            "static Endminf owner ranges are incomplete")
    owner_rows = {row.get("owner"): row for row in owners}
    output: dict[str, list[str]] = {}
    for candidate, static_owner in STATIC_OWNER_NAMES.items():
        owner_row = owner_rows.get(static_owner, {})
        start = owner_row.get("orderedStart")
        count = owner_row.get("bindingCount")
        require(isinstance(start, int) and start >= 0 and
                isinstance(count, int) and count > 0 and
                owner_row.get("excludedOwnerRoot") == static_owner,
                f"static {static_owner} owner range drifted")
        owner_entries = [row for row in entries
                         if row.get("owner") == static_owner]
        paths = [row.get("hierarchyPath") for row in owner_entries]
        require(len(paths) == count and
                all(isinstance(path, str) and path.startswith("Root/")
                    for path in paths),
                f"static {static_owner} path vector is incomplete")
        require([row.get("orderedIndex") for row in owner_entries] ==
                list(range(start, start + count)) and
                [row.get("managerIndex") for row in owner_entries] ==
                list(range(start, start + count)) and
                [row.get("ownerLocalIndex") for row in owner_entries] ==
                list(range(count)),
                f"static {static_owner} ordered index vector drifted")
        output[candidate] = paths
    require(sum(len(paths) for paths in output.values()) == len(entries),
            "static Endminf entries contain an unexpected owner")
    duplicates = endminf.get("duplicates", {})
    unique_path_count = len(set(
        path for paths in output.values() for path in paths))
    require(duplicates.get("bindingEntries") == len(entries) and
            duplicates.get("uniqueTransforms") == unique_path_count and
            duplicates.get("duplicateEntries") ==
                len(entries) - unique_path_count and
            duplicates.get("preservedAsDistinctManagerEntries") is True and
            unique_path_count > 0,
            "static Endminf path duplicate contract drifted")
    return output


def load_expected_owner_paths() -> dict[str, list[str]]:
    return {owner: [sha256_text(path) for path in paths]
            for owner, paths in load_expected_owner_hierarchy_paths().items()}


def load_last_window(capture: Path) -> dict[str, Any]:
    path = capture / "secondary-dynamics/windows.jsonl"
    require(path.is_file(), f"dynamics window file is absent: {path}")
    rows = [line for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    require(rows, "dynamics window file is empty")
    return json.loads(rows[-1])


def load_summary(capture: Path) -> dict[str, Any]:
    path = capture / "secondary-dynamics/summary.json"
    require(path.is_file(), f"dynamics summary is absent: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_first_loop_wrap_ns(capture: Path) -> tuple[int, int]:
    path = capture / "graphics/endminf_animator/metadata.json"
    require(path.is_file(), f"Endminf animator metadata is absent: {path}")
    metadata = json.loads(path.read_text(encoding="utf-8"))
    require(metadata.get("schema") ==
            "endfieldCapture.endminfAnimatorTimeline.v3" and
            metadata.get("characterId") == "chr_0003_endminf" and
            metadata.get("sequenceComplete") is True and
            metadata.get("complete") is True and
            metadata.get("stableIdentity") is True and
            metadata.get("stateHashesValid") is True and
            int(metadata.get("classifiedIdentitySegments", 0)) > 0 and
            int(metadata.get("completeIdentitySegments", 0)) > 0 and
            int(metadata.get("selectedIdentitySegment", -1)) >= 0 and
            int(metadata.get("selectedSegmentSampleCount", 0)) > 0,
            "Endminf animator timeline does not certify a complete sequence")
    state_hashes = metadata.get("stateHashes", {})
    require(state_hashes.get("startFullPath") == OVERVIEW_START_FULL_PATH_HASH and
            state_hashes.get("loopFullPath") == OVERVIEW_LOOP_FULL_PATH_HASH,
            "Endminf animator overview state identities drifted")
    indices = metadata.get("indices")
    samples = metadata.get("samples")
    require(isinstance(indices, dict) and isinstance(samples, list),
            "Endminf animator timeline structure is incomplete")
    wrap = int(indices.get("firstWrap", -1))
    segment_offset = int(metadata.get("selectedSegmentOffset", -1))
    segment_count = int(metadata.get("selectedSegmentSampleCount", 0))
    require(0 <= segment_offset < len(samples) and
            segment_count <= len(samples) - segment_offset and
            segment_offset <= wrap < segment_offset + segment_count,
            "Endminf animator selected segment or first-wrap index is outside the sample array")
    selected_samples = samples[segment_offset:segment_offset + segment_count]
    selected_threads = {int(row.get("threadId", 0))
                        for row in selected_samples}
    selected_owners = {row.get("owner") for row in selected_samples}
    selected_animators = {row.get("animator") for row in selected_samples}
    require(len(selected_threads) == len(selected_owners) ==
            len(selected_animators) == 1 and
            next(iter(selected_threads)) > 0 and
            all(isinstance(value, str) and value.startswith("0x") and
                int(value, 16) != 0
                for value in selected_owners | selected_animators),
            "Endminf animator selected identity segment is not stable")
    sample = samples[wrap]
    tick = int(sample.get("qpcTick", 0))
    frequency = int(sample.get("qpcFrequency", 0))
    thread_id = next(iter(selected_threads))
    require(tick > 0 and frequency > 0 and thread_id > 0,
            "Endminf animator first-wrap clock is invalid")
    return ((tick * 1_000_000_000 + frequency - 1) // frequency,
            thread_id)


def build_report(capture: Path, minimum_writebacks: int = 60) -> dict[str, Any]:
    expected_owner_paths = load_expected_owner_paths()
    expected_owner_hierarchy_paths = load_expected_owner_hierarchy_paths()
    first_loop_wrap_ns, animator_thread_id = load_first_loop_wrap_ns(capture)
    summary = load_summary(capture)
    require(summary.get("schema") ==
            "endfieldCapture.secondaryDynamicsSummary.v4",
            "secondary-dynamics summary schema is not v4")
    for field in ("hooksInstalled", "clothUpdateHookInstalled",
                  "alwaysTeamUpdateHookInstalled", "writeTransformHookInstalled",
                  "completeMasterJobHookInstalled", "addClothHookInstalled",
                  "removeClothHookInstalled", "addTransformHookInstalled",
                  "addTransformBulkHookInstalled",
                  "removeTransformHookInstalled",
                  "hierarchyIdentityGettersPinned",
                  "registrationSourceComplete",
                  "quiescentCleanup",
                  "automaticTriggerCallbackQuiescent", "complete"):
        require(summary.get(field) is True,
                f"secondary-dynamics summary {field} is not true")
    windows_completed = int(summary.get("windowsCompleted", -1))
    require(windows_completed == 1,
            f"expected one completed dynamics window, observed {windows_completed}")
    require(int(summary.get("windowsFailed", -1)) == 0,
            "secondary-dynamics window finalization reported a failure")
    require(int(summary.get("evidenceCompleteWindows", -1)) ==
            windows_completed and
            int(summary.get("evidenceIncompleteWindows", -1)) == 0,
            "secondary-dynamics evidence-window counts are incomplete")
    require(int(summary.get("automaticTriggerArmFailures", -1)) == 0 and
            int(summary.get("automaticTriggerLifecycleFailures", -1)) == 0,
            "secondary-dynamics trigger lifecycle reported a failure")
    registration_thread_id = int(summary.get("registrationCallbackThreadId", 0))
    main_window_thread_id = int(summary.get("mainWindowThreadId", 0))
    require(registration_thread_id > 0 and
            registration_thread_id == main_window_thread_id and
            registration_thread_id == animator_thread_id and
            int(summary.get("registrationCallbackThreadMismatches", -1)) == 0,
            "registration callbacks and Animator sampling did not remain on the main window thread")
    require(int(summary.get("hierarchyIdentityRecordCapacityFailures", -1)) == 0 and
            int(summary.get("hierarchyIdentityArenaCapacityFailures", -1)) == 0,
            "hierarchy identity immutable storage capacity failed")
    require(int(summary.get("registrationLifecycleFailures", -1)) == 0,
            "registration lifecycle invalidation reported a failure")
    window = load_last_window(capture)
    require(window.get("schema") ==
            "endfieldCapture.secondaryDynamicsWindow.v4",
            "secondary-dynamics window schema is not v4")
    prior_present = int(window.get("automaticTriggerPriorPresent", 0))
    graphics_present = int(window.get("automaticTriggerGraphicsPresent", 0))
    require(window.get("automaticTriggerComplete") is True and
            prior_present > 0 and graphics_present > prior_present and
            graphics_present - prior_present <= 2,
            "window is not joined to the exact Animator/graphics trigger")
    require(window.get("trajectoryComplete") is True,
            "window does not certify complete trajectory retention")
    require(window.get("registrationLifecycleJoinComplete") is True,
            "window does not join every sample to its cloth registration")
    require(window.get("effectivePostJobPoseComplete") is True,
            "window does not contain every effective post-job Transform pose")
    require(window.get("registrationHierarchyIdentityComplete") is True,
            "window does not contain every registration hierarchy identity")
    scheduled = int(window.get("transformScheduledCalls", -1))
    completed = int(window.get("transformCompletedCalls", -1))
    recorded = int(window.get("transformWriteCalls", -1))
    require(scheduled > 0 and scheduled == completed == recorded,
            "scheduled, completed, and recorded transform writebacks differ")
    require(window.get("registrationSourceComplete") is True,
            "window does not certify its registration source")
    require(window.get("endminfTrajectoryFourOwnerCoverage") is True,
            "window does not certify exact four-owner coverage")
    require(window.get("endminfSourceOwnerSetUnambiguous") is True,
            "window does not certify an unambiguous source-owner set")
    require(int(window.get("transformWriteUnreadableCalls", -1)) == 0,
            "one or more transform writes was unreadable")
    require(int(window.get("transformSampleOverflow", -1)) == 0,
            "transform sample capacity overflowed")
    window_id = int(window["windowId"])

    path = capture / "secondary-dynamics/trajectories.jsonl"
    require(path.is_file(), f"trajectory file is absent: {path}")
    rows_by_writeback: dict[int, list[dict[str, Any]]] = defaultdict(list)
    writeback_timestamps: dict[int, int] = {}
    retained_rows = 0
    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if int(row.get("windowId", -1)) != window_id:
                continue
            static_owner = row.get("clothName")
            require(static_owner in OWNER_BY_STATIC_NAME,
                    f"line {line_number} has no exact Endminf cloth owner")
            owner = OWNER_BY_STATIC_NAME[static_owner]
            require(row.get("endminfOwnerCandidate") == owner,
                    f"line {line_number} runtime owner certification differs from its exact cloth name")
            finite_vector(row, "position", 3)
            finite_vector(row, "rotation", 4)
            finite_vector(row, "localPosition", 3)
            finite_vector(row, "localRotation", 4)
            require(row.get("schema") ==
                    "endfieldCapture.secondaryDynamicsTransform.v4",
                    f"line {line_number} trajectory schema is not v4")
            require(row.get("registrationJoined") is True,
                    f"line {line_number} has no registration lifecycle join")
            require(row.get("effectivePoseReadable") is True,
                    f"line {line_number} has no effective post-job pose")
            finite_vector(row, "effectivePosition", 3)
            usable_quaternion(row, "effectiveRotation")
            finite_vector(row, "effectiveLocalPosition", 3)
            usable_quaternion(row, "effectiveLocalRotation")
            for pointer in ("clothProcess", "clothComponent", "clothTransform",
                            "registeredTransform", "liveTransform"):
                value = row.get(pointer)
                require(isinstance(value, str) and value.startswith("0x") and
                        int(value, 16) != 0,
                        f"line {line_number} {pointer} is absent")
            cloth_instance_id = int(row.get("clothInstanceId", 0))
            component_id = int(row.get("componentId", 0))
            cloth_transform_instance_id = int(
                row.get("clothTransformInstanceId", 0))
            registered_instance_id = int(
                row.get("registeredTransformInstanceId", 0))
            live_instance_id = int(row.get("liveTransformInstanceId", 0))
            require(cloth_instance_id != 0 and cloth_transform_instance_id != 0 and
                    registered_instance_id != 0 and
                    live_instance_id == registered_instance_id,
                    f"line {line_number} live Transform identity differs from registration")
            require(row.get("componentClothInstanceMatch") is True and
                    component_id == cloth_instance_id,
                    f"line {line_number} component/cloth identity is not certified")
            require(row.get("hierarchyIdentityReadable") is True,
                    f"line {line_number} hierarchy identity is unreadable")
            for digest_key in ("hierarchyPathSha256", "clothNameSha256"):
                digest = row.get(digest_key)
                require(isinstance(digest, str) and len(digest) == 64 and
                        all(lane in "0123456789abcdef" for lane in digest) and
                        digest != "0" * 64,
                        f"line {line_number} {digest_key} is invalid")
            for text_key, digest_key in (
                    ("hierarchyPath", "hierarchyPathSha256"),
                    ("clothName", "clothNameSha256")):
                text = row.get(text_key)
                require(isinstance(text, str) and text and
                        sha256_text(text) == row[digest_key],
                        f"line {line_number} {text_key} does not match its digest")
            require(int(row.get("clothRegistrationGeneration", 0)) > 0 and
                    int(row.get("transformRegistrationGeneration", 0)) > 0,
                    f"line {line_number} registration generation is absent")
            require(int(row.get("hierarchyIdentityRecordId", 0)) > 0 and
                    int(row.get("clothNameRecordId", 0)) > 0,
                    f"line {line_number} immutable hierarchy record is absent")
            require(int(row.get("clothParentInstanceId", 0)) > 0 and
                    int(row.get("hierarchyRootInstanceId", 0)) > 0 and
                    int(row.get("hierarchyActorParentInstanceId", 0)) > 0,
                    f"line {line_number} actor hierarchy association is absent")
            require(int(row.get("registrationStart", -1)) ==
                    int(row.get("transformIndex", -2)) and
                    int(row.get("registrationLength", -1)) == 1,
                    f"line {line_number} registration chunk does not name its row")
            writeback = int(row["writebackId"])
            timestamp = int(row["timestampNs"])
            prior = writeback_timestamps.setdefault(writeback, timestamp)
            require(prior == timestamp,
                    f"writeback {writeback} has inconsistent timestamps")
            rows_by_writeback[writeback].append(row)
            retained_rows += 1

    require(retained_rows == int(window.get("transformSampleCount", -1)),
            "trajectory rows do not match the certified sample count")
    require(len(writeback_timestamps) >= minimum_writebacks,
            f"only {len(writeback_timestamps)} writebacks were retained")
    ordered_writebacks = sorted(writeback_timestamps)
    require(ordered_writebacks == list(range(ordered_writebacks[0],
                                              ordered_writebacks[-1] + 1)),
            "writeback IDs are not contiguous")
    timestamps = [writeback_timestamps[item] for item in ordered_writebacks]
    require(all(right > left for left, right in zip(timestamps, timestamps[1:])),
            "writeback timestamps are not strictly increasing")
    require(timestamps[-1] >= first_loop_wrap_ns,
            "secondary-dynamics trajectory ends before the first settled loop wrap")

    expected_total_rows = sum(
        len(paths) for paths in expected_owner_hierarchy_paths.values())
    expected_unique_paths = len(set(
        path for paths in expected_owner_hierarchy_paths.values()
        for path in paths))
    baseline: dict[tuple[str, int], dict[str, Any]] | None = None
    owners: dict[str, dict[str, Any]] = {}

    def identity(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "teamId": int(row["teamId"]),
            "componentId": int(row["componentId"]),
            "clothInstanceId": int(row["clothInstanceId"]),
            "clothTransformInstanceId": int(
                row["clothTransformInstanceId"]),
            "clothRegistrationGeneration": int(
                row["clothRegistrationGeneration"]),
            "transformRegistrationGeneration": int(
                row["transformRegistrationGeneration"]),
            "registeredTransformInstanceId": int(
                row["registeredTransformInstanceId"]),
            "hierarchyIdentityRecordId": int(
                row["hierarchyIdentityRecordId"]),
            "hierarchyPathSha256": row["hierarchyPathSha256"],
            "clothNameRecordId": int(row["clothNameRecordId"]),
            "clothNameSha256": row["clothNameSha256"],
            "hierarchyRootInstanceId": int(
                row["hierarchyRootInstanceId"]),
            "hierarchyActorParentInstanceId": int(
                row["hierarchyActorParentInstanceId"]),
            "clothParentInstanceId": int(row["clothParentInstanceId"]),
            "clothProcess": row["clothProcess"],
            "clothComponent": row["clothComponent"],
            "clothTransform": row["clothTransform"],
            "registeredTransform": row["registeredTransform"],
        }

    for writeback in ordered_writebacks:
        writeback_rows = rows_by_writeback[writeback]
        require(len(writeback_rows) == expected_total_rows,
                f"writeback {writeback} does not contain the complete static owner row count")
        owner_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in writeback_rows:
            owner_rows[OWNER_BY_STATIC_NAME[row["clothName"]]].append(row)
        require(set(owner_rows) == set(STATIC_OWNER_NAMES),
                f"writeback {writeback} does not contain exactly four cloth owners")

        roots = {int(row["hierarchyRootInstanceId"])
                 for row in writeback_rows}
        actor_parents = {int(row["hierarchyActorParentInstanceId"])
                         for row in writeback_rows}
        cloth_parents = {int(row["clothParentInstanceId"])
                         for row in writeback_rows}
        require(len(roots) == 1 and len(actor_parents) == 1 and
                cloth_parents == actor_parents,
                f"writeback {writeback} splits the four owners across actor hierarchies")

        current: dict[tuple[str, int], dict[str, Any]] = {}
        owner_identities: list[tuple[int, int, int, int]] = []
        for owner, static_owner in STATIC_OWNER_NAMES.items():
            rows = owner_rows[owner]
            expected_paths = expected_owner_hierarchy_paths[owner]
            require(len(rows) == len(expected_paths),
                    f"writeback {writeback} {owner} row count differs from the static contract")
            require(Counter(row["hierarchyPath"] for row in rows) ==
                    Counter(expected_paths) and
                    Counter(row["hierarchyPathSha256"] for row in rows) ==
                    Counter(expected_owner_paths[owner]),
                    f"writeback {writeback} {owner} hierarchy-path multiset differs from the static contract")
            require({row["clothName"] for row in rows} == {static_owner} and
                    {row["clothNameSha256"] for row in rows} ==
                        {sha256_text(static_owner)},
                    f"writeback {writeback} {owner} exact cloth name drifted")

            team_ids = {int(row["teamId"]) for row in rows}
            component_ids = {int(row["componentId"]) for row in rows}
            cloth_ids = {int(row["clothInstanceId"]) for row in rows}
            cloth_generations = {
                int(row["clothRegistrationGeneration"]) for row in rows}
            require(len(team_ids) == len(component_ids) == len(cloth_ids) ==
                    len(cloth_generations) == 1,
                    f"writeback {writeback} {owner} has ambiguous cloth registration identity")
            team_id = next(iter(team_ids))
            component_id = next(iter(component_ids))
            cloth_id = next(iter(cloth_ids))
            cloth_generation = next(iter(cloth_generations))
            owner_identities.append(
                (team_id, component_id, cloth_id, cloth_generation))

            for row in rows:
                key = (owner, int(row["transformIndex"]))
                require(key not in current,
                        f"writeback {writeback} duplicates {owner} transform index {key[1]}")
                current[key] = identity(row)

            if baseline is None:
                first = rows[0]
                owners[static_owner] = {
                    "teamId": team_id,
                    "componentId": component_id,
                    "clothInstanceId": cloth_id,
                    "clothRegistrationGeneration": cloth_generation,
                    "transformIndices": sorted(
                        int(row["transformIndex"]) for row in rows),
                    "bindingCount": len(rows),
                    "sampleCount": len(rows) * len(ordered_writebacks),
                    "clothProcess": first["clothProcess"],
                    "clothComponent": first["clothComponent"],
                    "clothTransform": first["clothTransform"],
                    "clothTransformInstanceId": int(
                        first["clothTransformInstanceId"]),
                    "clothNameRecordId": int(first["clothNameRecordId"]),
                    "clothParentInstanceId": int(
                        first["clothParentInstanceId"]),
                    "hierarchyRootInstanceId": int(
                        first["hierarchyRootInstanceId"]),
                    "hierarchyActorParentInstanceId": int(
                        first["hierarchyActorParentInstanceId"]),
                }

        require(len({item[0] for item in owner_identities}) == 4 and
                len({item[1] for item in owner_identities}) == 4 and
                len({item[2] for item in owner_identities}) == 4 and
                len({item[3] for item in owner_identities}) == 4,
                f"writeback {writeback} does not contain four distinct owner registrations")
        if baseline is None:
            baseline = current
        else:
            require(set(current) == set(baseline),
                    f"writeback {writeback} owner/transform identity key set drifted")
            for key, expected_identity in baseline.items():
                require(current[key] == expected_identity,
                        f"writeback {writeback} {key[0]} transform {key[1]} identity drifted from the first writeback")

    require(baseline is not None and len(baseline) == expected_total_rows,
            "first-writeback identity baseline is incomplete")
    path_to_instances: dict[str, set[int]] = defaultdict(set)
    instance_to_paths: dict[int, set[str]] = defaultdict(set)
    transform_generations: set[int] = set()
    transform_records: set[int] = set()
    cloth_name_records: set[int] = set()
    for values in baseline.values():
        registered_instance_id = values["registeredTransformInstanceId"]
        path_digest = values["hierarchyPathSha256"]
        path_to_instances[path_digest].add(registered_instance_id)
        instance_to_paths[registered_instance_id].add(path_digest)
        transform_generations.add(values["transformRegistrationGeneration"])
        transform_records.add(values["hierarchyIdentityRecordId"])
        cloth_name_records.add(values["clothNameRecordId"])
    require(len(path_to_instances) == len(instance_to_paths) ==
            expected_unique_paths and
            all(len(values) == 1 for values in path_to_instances.values()) and
            all(len(values) == 1 for values in instance_to_paths.values()),
            "runtime Transform identity does not preserve the static hierarchy-path duplicate contract")
    require(len(transform_generations) == expected_total_rows,
            "runtime registration generations are reused or incomplete")
    require(len(transform_records) == expected_total_rows and
            len(cloth_name_records) == len(STATIC_OWNER_NAMES) and
            transform_records.isdisjoint(cloth_name_records),
            "immutable hierarchy record IDs are reused or incomplete")

    return {
        "schema": "endfield.endminf-secondary-dynamics-trajectory-capture.v3",
        "status": "validated_four_static_owner_path_joined_post_job_trajectories",
        "capture": str(capture.resolve()),
        "windowId": window_id,
        "automaticTriggerPriorPresent": prior_present,
        "automaticTriggerGraphicsPresent": graphics_present,
        "writebackCount": len(ordered_writebacks),
        "scheduledWritebackCount": scheduled,
        "firstTimestampNs": timestamps[0],
        "lastTimestampNs": timestamps[-1],
        "firstSettledLoopWrapNs": first_loop_wrap_ns,
        "transformReadContractSha256": TRANSFORM_READ_CONTRACT_SHA256,
        "sampleCount": retained_rows,
        "owners": owners,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--minimum-writebacks", type=int, default=60)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        report = build_report(args.capture.resolve(), args.minimum_writebacks)
    except (OSError, ValueError, VerificationError) as exc:
        print(f"ERROR: {exc}")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

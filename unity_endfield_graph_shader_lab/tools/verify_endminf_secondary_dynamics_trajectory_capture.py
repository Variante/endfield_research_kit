#!/usr/bin/env python3
"""Verify a bounded Endminf four-owner TransformAccess trajectory capture."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    REPO / "reports/assets/character_recovery"
    / "endminf_secondary_dynamics_trajectory_capture_latest.json"
)
OWNER_LENGTHS = {"Ribbon2": 6, "Hair": 30, "Ribbon": 20, "Coat": 70}
STATIC_OWNER_NAMES = {owner: f"MC_{owner}" for owner in OWNER_LENGTHS}
OWNER_STARTS = {"Ribbon2": 0, "Hair": 6, "Ribbon": 36, "Coat": 56}
TRANSFORM_READ_CONTRACT_SHA256 = (
    "87ea60222e32d9037ef2d8968d441109c0de61933187f17e51a338361dea66b8")
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
    require(isinstance(entries, list) and len(entries) == 126,
            "static Endminf transform-read entries are incomplete")
    owners = endminf.get("owners")
    require(isinstance(owners, list) and len(owners) == 4,
            "static Endminf owner ranges are incomplete")
    owner_rows = {row.get("owner"): row for row in owners}
    output: dict[str, list[str]] = {}
    for candidate, static_owner in STATIC_OWNER_NAMES.items():
        owner_row = owner_rows.get(static_owner, {})
        require(owner_row.get("orderedStart") == OWNER_STARTS[candidate] and
                owner_row.get("bindingCount") == OWNER_LENGTHS[candidate] and
                owner_row.get("excludedOwnerRoot") == static_owner,
                f"static {static_owner} owner range drifted")
        owner_entries = [row for row in entries
                         if row.get("owner") == static_owner]
        paths = [row.get("hierarchyPath") for row in owner_entries]
        require(len(paths) == OWNER_LENGTHS[candidate] and
                all(isinstance(path, str) and path.startswith("Root/")
                    for path in paths),
                f"static {static_owner} path vector is incomplete")
        start = OWNER_STARTS[candidate]
        require([row.get("orderedIndex") for row in owner_entries] ==
                list(range(start, start + OWNER_LENGTHS[candidate])) and
                [row.get("managerIndex") for row in owner_entries] ==
                list(range(start, start + OWNER_LENGTHS[candidate])) and
                [row.get("ownerLocalIndex") for row in owner_entries] ==
                list(range(OWNER_LENGTHS[candidate])),
                f"static {static_owner} ordered index vector drifted")
        output[candidate] = paths
    duplicates = endminf.get("duplicates", {})
    require(duplicates.get("bindingEntries") == 126 and
            duplicates.get("uniqueTransforms") == 100 and
            duplicates.get("duplicateEntries") == 26 and
            duplicates.get("preservedAsDistinctManagerEntries") is True and
            len(set(path for paths in output.values() for path in paths)) == 100,
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
                  "removeTransformHookInstalled",
                  "hierarchyIdentityGettersPinned",
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
    require(window.get("endminfTrajectoryFourChunkCandidateCoverage") is True,
            "window does not contain all four Endminf chunk candidates")
    require(window.get("endminfTrajectoryFourOwnerCoverage") is not True,
            "capture must not claim owner identity from chunk length alone")
    require(int(window.get("transformWriteUnreadableCalls", -1)) == 0,
            "one or more transform writes was unreadable")
    require(int(window.get("transformSampleOverflow", -1)) == 0,
            "transform sample capacity overflowed")
    window_id = int(window["windowId"])

    path = capture / "secondary-dynamics/trajectories.jsonl"
    require(path.is_file(), f"trajectory file is absent: {path}")
    by_candidate: dict[tuple[str, int, int], dict[int, list[dict[str, Any]]]] = (
        defaultdict(lambda: defaultdict(list)))
    writeback_timestamps: dict[int, int] = {}
    retained_rows = 0
    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if int(row.get("windowId", -1)) != window_id:
                continue
            owner = row.get("endminfOwnerCandidate")
            if owner not in OWNER_LENGTHS:
                continue
            require(int(row.get("proxyTransformLength", -1)) == OWNER_LENGTHS[owner],
                    f"line {line_number} owner length drifted")
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
            cloth_transform_instance_id = int(
                row.get("clothTransformInstanceId", 0))
            registered_instance_id = int(
                row.get("registeredTransformInstanceId", 0))
            live_instance_id = int(row.get("liveTransformInstanceId", 0))
            require(cloth_instance_id != 0 and cloth_transform_instance_id != 0 and
                    registered_instance_id != 0 and
                    live_instance_id == registered_instance_id,
                    f"line {line_number} live Transform identity differs from registration")
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
            key = (owner, int(row["teamId"]), int(row["componentId"]))
            by_candidate[key][writeback].append(row)
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

    owners: dict[str, dict[str, Any]] = {}
    validated_rows: list[dict[str, Any]] = []
    for owner, length in OWNER_LENGTHS.items():
        candidates = []
        for (candidate_owner, team_id, component_id), writebacks in by_candidate.items():
            if candidate_owner != owner or set(writebacks) != set(ordered_writebacks):
                continue
            valid = True
            chunk_start = None
            for rows in writebacks.values():
                if len(rows) != length:
                    valid = False
                    break
                starts = {int(row["proxyTransformStart"]) for row in rows}
                indices = sorted(int(row["transformIndex"]) for row in rows)
                if len(starts) != 1:
                    valid = False
                    break
                start = next(iter(starts))
                if indices != list(range(start, start + length)):
                    valid = False
                    break
                ordered_rows = sorted(rows, key=lambda row: int(row["transformIndex"]))
                if ([row["hierarchyPathSha256"] for row in ordered_rows] !=
                        expected_owner_paths[owner]):
                    valid = False
                    break
                if ([row["hierarchyPath"] for row in ordered_rows] !=
                        expected_owner_hierarchy_paths[owner]):
                    valid = False
                    break
                if chunk_start is None:
                    chunk_start = start
                elif chunk_start != start:
                    valid = False
                    break
            if valid:
                candidates.append((team_id, component_id, chunk_start))
        require(len(candidates) == 1,
                f"{owner} has {len(candidates)} complete team candidates")
        team_id, component_id, chunk_start = candidates[0]
        require(chunk_start == OWNER_STARTS[owner],
                f"{owner} manager range does not match the pinned contract")
        candidate_rows = [row for rows in by_candidate[
            (owner, team_id, component_id)].values() for row in rows]
        cloth_processes = {row["clothProcess"] for row in candidate_rows}
        cloth_components = {row["clothComponent"] for row in candidate_rows}
        cloth_transforms = {row["clothTransform"] for row in candidate_rows}
        cloth_instance_ids = {int(row["clothInstanceId"])
                              for row in candidate_rows}
        cloth_transform_instance_ids = {
            int(row["clothTransformInstanceId"]) for row in candidate_rows}
        cloth_names = {row["clothNameSha256"] for row in candidate_rows}
        cloth_parent_instance_ids = {int(row["clothParentInstanceId"])
                                     for row in candidate_rows}
        hierarchy_root_instance_ids = {int(row["hierarchyRootInstanceId"])
                                       for row in candidate_rows}
        hierarchy_actor_parent_instance_ids = {
            int(row["hierarchyActorParentInstanceId"])
            for row in candidate_rows}
        cloth_generations = {int(row["clothRegistrationGeneration"])
                             for row in candidate_rows}
        cloth_name_records = {int(row["clothNameRecordId"])
                              for row in candidate_rows}
        require(len(cloth_processes) == len(cloth_components) ==
                len(cloth_transforms) == len(cloth_instance_ids) ==
                len(cloth_transform_instance_ids) ==
                len(cloth_names) == len(cloth_parent_instance_ids) ==
                len(hierarchy_root_instance_ids) ==
                len(hierarchy_actor_parent_instance_ids) ==
                len(cloth_generations) == len(cloth_name_records) ==
                1,
                f"{owner} registration identity changes across writebacks")
        static_owner = STATIC_OWNER_NAMES[owner]
        require(next(iter(cloth_names)) == sha256_text(static_owner),
                f"{owner} cloth name does not identify {static_owner}")
        require({row["clothName"] for row in candidate_rows} == {static_owner},
                f"{owner} cloth name text does not identify {static_owner}")
        registered_by_index: dict[int, set[int]] = defaultdict(set)
        generations_by_index: dict[int, set[int]] = defaultdict(set)
        records_by_index: dict[int, set[int]] = defaultdict(set)
        for row in candidate_rows:
            registered_by_index[int(row["transformIndex"])].add(
                int(row["registeredTransformInstanceId"]))
            generations_by_index[int(row["transformIndex"])].add(
                int(row["transformRegistrationGeneration"]))
            records_by_index[int(row["transformIndex"])].add(
                int(row["hierarchyIdentityRecordId"]))
        require(all(len(values) == 1 for values in registered_by_index.values()) and
                len({next(iter(values)) for values in
                     registered_by_index.values()}) == length,
                f"{owner} registered Transform identity is not stable and unique")
        require(all(len(values) == 1 for values in generations_by_index.values()) and
                all(len(values) == 1 for values in records_by_index.values()),
                f"{owner} registration generation or immutable record changes across writebacks")
        validated_rows.extend(candidate_rows)
        owners[static_owner] = {
            "teamId": team_id,
            "componentId": component_id,
            "proxyTransformStart": chunk_start,
            "proxyTransformLength": length,
            "sampleCount": length * len(ordered_writebacks),
            "clothProcess": next(iter(cloth_processes)),
            "clothComponent": next(iter(cloth_components)),
            "clothTransform": next(iter(cloth_transforms)),
            "clothInstanceId": next(iter(cloth_instance_ids)),
            "clothTransformInstanceId": next(iter(cloth_transform_instance_ids)),
            "clothNameRecordId": next(iter(cloth_name_records)),
            "clothParentInstanceId": next(iter(cloth_parent_instance_ids)),
            "hierarchyRootInstanceId": next(iter(hierarchy_root_instance_ids)),
            "hierarchyActorParentInstanceId": next(
                iter(hierarchy_actor_parent_instance_ids)),
        }

    require(len({row["clothProcess"] for row in owners.values()}) == 4 and
            len({row["clothComponent"] for row in owners.values()}) == 4 and
            len({row["clothTransform"] for row in owners.values()}) == 4 and
            len({row["clothInstanceId"] for row in owners.values()}) == 4 and
            len({row["clothTransformInstanceId"] for row in owners.values()}) == 4,
            "the four chunk candidates do not map to four distinct cloth owners")
    root_instance_ids = {row["hierarchyRootInstanceId"]
                         for row in owners.values()}
    actor_parent_instance_ids = {row["hierarchyActorParentInstanceId"]
                                 for row in owners.values()}
    cloth_parent_instance_ids = {row["clothParentInstanceId"]
                                 for row in owners.values()}
    require(len(root_instance_ids) == 1 and
            len(actor_parent_instance_ids) == 1 and
            cloth_parent_instance_ids == actor_parent_instance_ids,
            "the four cloth owners and skeleton Root do not share one actor parent")

    path_to_instances: dict[str, set[int]] = defaultdict(set)
    instance_to_paths: dict[int, set[str]] = defaultdict(set)
    transform_generations: dict[int, set[int]] = defaultdict(set)
    transform_records: dict[int, set[int]] = defaultdict(set)
    for row in validated_rows:
        digest = row["hierarchyPathSha256"]
        instance_id = int(row["registeredTransformInstanceId"])
        index = int(row["transformIndex"])
        path_to_instances[digest].add(instance_id)
        instance_to_paths[instance_id].add(digest)
        transform_generations[index].add(
            int(row["transformRegistrationGeneration"]))
        transform_records[index].add(int(row["hierarchyIdentityRecordId"]))
    require(len(path_to_instances) == len(instance_to_paths) == 100 and
            all(len(values) == 1 for values in path_to_instances.values()) and
            all(len(values) == 1 for values in instance_to_paths.values()),
            "runtime Transform identity does not preserve the 100-path/26-duplicate contract")
    require(len(transform_generations) == 126 and
            all(len(values) == 1 for values in transform_generations.values()) and
            len({next(iter(values)) for values in
                 transform_generations.values()}) == 126,
            "runtime registration generations are stale, reused, or incomplete")
    stable_transform_records = {next(iter(values))
                                for values in transform_records.values()
                                if len(values) == 1}
    cloth_name_records = {int(row["clothNameRecordId"])
                          for row in owners.values()}
    require(len(transform_records) == 126 and
            len(stable_transform_records) == 126 and
            len(cloth_name_records) == 4 and
            stable_transform_records.isdisjoint(cloth_name_records),
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

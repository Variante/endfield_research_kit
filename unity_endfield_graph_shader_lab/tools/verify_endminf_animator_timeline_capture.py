#!/usr/bin/env python3
"""Validate an exact Endminf UI Animator timeline captured with graphics Full."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_draw_contract_capture",
    HERE / "verify_endminf_draw_contract_capture.py")
assert SPEC and SPEC.loader
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
OBSERVER_SPEC = importlib.util.spec_from_file_location(
    "endfield_capture_observer_build_contract",
    HERE.parents[1] / "scripts/endfield_capture_observer_build_contract.py")
assert OBSERVER_SPEC and OBSERVER_SPEC.loader
OBSERVER_BUILD = importlib.util.module_from_spec(OBSERVER_SPEC)
OBSERVER_SPEC.loader.exec_module(OBSERVER_BUILD)
OBSERVER_CONTRACT = OBSERVER_BUILD.load_contract()

EXPECTED_SCHEMA = "endfieldCapture.endminfAnimatorTimeline.v3"
EXPECTED_CHARACTER = "chr_0003_endminf"
EXPECTED_CAPACITY = OBSERVER_CONTRACT["producerContracts"][
    "animatorTimeline"]["sampleCapacity"]
HEX_IDENTITY = re.compile(r"0x[1-9a-fA-F][0-9a-fA-F]*\Z")
EXPECTED_START_STATE = {
    "name": "Base Layer.Overview.FromOveview",
    "fullPathHash": 0x5D0225EB,
}
EXPECTED_LOOP_STATE = {
    "name": "Base Layer.Overview.OverviewIdle",
    "fullPathHash": -1345940313,  # unsigned 0xAFC694A7
}


class TimelineError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TimelineError(message)


def integer(value: Any, label: str, minimum: int | None = None) -> int:
    require(isinstance(value, int) and not isinstance(value, bool),
            f"{label} is not an integer")
    if minimum is not None:
        require(value >= minimum, f"{label} is less than {minimum}")
    return value


def int32(value: Any, label: str) -> int:
    result = integer(value, label)
    require(-(1 << 31) <= result < (1 << 31),
            f"{label} is outside signed 32-bit range")
    return result


def number(value: Any, label: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool) and
            math.isfinite(float(value)), f"{label} is not a finite number")
    return float(value)


def boolean(value: Any, label: str) -> bool:
    require(isinstance(value, bool), f"{label} is not a boolean")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def close(actual: float, expected: float) -> bool:
    return math.isclose(actual, expected, rel_tol=1.0e-6, abs_tol=1.0e-6)


def validate_state(value: Any, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} is not an object")
    result: dict[str, Any] = {}
    for field in ("nameHash", "pathHash", "fullPathHash", "tagHash",
                  "syncGroup", "syncGroupRole", "cullingMode",
                  "sourceMessage"):
        result[field] = int32(value.get(field), f"{label} {field}")
    result["loop"] = integer(value.get("loop"), f"{label} loop")
    require(result["loop"] in (0, 1), f"{label} loop is not 0 or 1")
    for field in ("normalizedTime", "length", "speed", "speedMultiplier"):
        result[field] = number(value.get(field), f"{label} {field}")
    require(result["normalizedTime"] >= 0.0,
            f"{label} normalizedTime is negative")
    require(result["length"] > 0.0, f"{label} length is not positive")

    derived = value.get("derived")
    require(isinstance(derived, dict), f"{label} derived values are absent")
    unwrapped = number(derived.get("unwrappedStateSeconds"),
                       f"{label} unwrappedStateSeconds")
    cycle = integer(derived.get("cycleIndex"), f"{label} cycleIndex", 0)
    local = number(derived.get("cycleLocalSeconds"),
                   f"{label} cycleLocalSeconds")
    expected_cycle = math.floor(result["normalizedTime"])
    require(cycle == expected_cycle, f"{label} derived cycleIndex disagrees")
    require(close(unwrapped,
                  result["normalizedTime"] * result["length"]),
            f"{label} derived unwrappedStateSeconds disagrees")
    require(close(local, (result["normalizedTime"] - expected_cycle) *
                  result["length"]),
            f"{label} derived cycleLocalSeconds disagrees")
    result["derived"] = {
        "unwrappedStateSeconds": unwrapped,
        "cycleIndex": cycle,
        "cycleLocalSeconds": local,
    }
    return result


def validate_transition(value: Any, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} is not an object")
    result = {
        field: int32(value.get(field), f"{label} {field}")
        for field in ("fullPathHash", "userNameHash", "nameHash",
                      "transitionType")
    }
    for field in ("hasFixedDuration", "anyState"):
        result[field] = integer(value.get(field), f"{label} {field}")
        require(result[field] in (0, 1),
                f"{label} {field} is not 0 or 1")
    result["duration"] = number(value.get("duration"), f"{label} duration")
    result["normalizedTime"] = number(
        value.get("normalizedTime"), f"{label} normalizedTime")
    require(result["duration"] >= 0.0,
            f"{label} duration is negative")
    require(result["normalizedTime"] >= 0.0,
            f"{label} normalizedTime is negative")
    return result


def validate_samples(value: Any) -> list[dict[str, Any]]:
    require(isinstance(value, list) and value,
            "animator timeline samples are absent or empty")
    samples: list[dict[str, Any]] = []
    for index, row in enumerate(value):
        label = f"sample {index}"
        require(isinstance(row, dict), f"{label} is not an object")
        ordinal = integer(row.get("ordinal"), f"{label} ordinal", 1)
        qpc_tick = integer(row.get("qpcTick"), f"{label} qpcTick", 1)
        frequency = integer(row.get("qpcFrequency"),
                            f"{label} qpcFrequency", 1)
        present = integer(row.get("priorPresentOrdinal"),
                          f"{label} priorPresentOrdinal", 1)
        last_present = integer(row.get("priorPresentQpc"),
                               f"{label} priorPresentQpc", 1)
        next_ordinal_value = row.get("nextObservedPresentOrdinal")
        next_qpc_value = row.get("nextObservedPresentQpc")
        require((next_ordinal_value is None) == (next_qpc_value is None),
                f"{label} next observed Present pair is partial")
        next_ordinal = (None if next_ordinal_value is None else
                        integer(next_ordinal_value,
                                f"{label} nextObservedPresentOrdinal", 1))
        next_qpc = (None if next_qpc_value is None else
                    integer(next_qpc_value,
                            f"{label} nextObservedPresentQpc", 1))
        require(qpc_tick > last_present,
                f"{label} qpcTick is not after lastPresentQpc")
        delta = number(row.get("deltaTime"), f"{label} deltaTime")
        require(delta > 0.0, f"{label} deltaTime is not positive")
        thread = integer(row.get("threadId"), f"{label} threadId", 1)
        owner = row.get("owner")
        animator = row.get("animator")
        require(isinstance(owner, str) and HEX_IDENTITY.fullmatch(owner),
                f"{label} owner identity is invalid")
        require(isinstance(animator, str) and HEX_IDENTITY.fullmatch(animator),
                f"{label} animator identity is invalid")
        current = validate_state(row.get("current"), f"{label} current")
        in_transition = boolean(row.get("inTransition"),
                                f"{label} inTransition")
        if in_transition:
            next_state = validate_state(row.get("next"), f"{label} next")
            transition = validate_transition(row.get("transition"),
                                             f"{label} transition")
        else:
            require(row.get("next") is None and row.get("transition") is None,
                    f"{label} has next/transition data while not transitioning")
            next_state = None
            transition = None
        samples.append({
            "ordinal": ordinal, "qpcTick": qpc_tick,
            "qpcFrequency": frequency, "presentOrdinal": present,
            "lastPresentQpc": last_present,
            "nextObservedPresentOrdinal": next_ordinal,
            "nextObservedPresentQpc": next_qpc,
            "deltaTime": delta,
            "threadId": thread, "owner": owner.lower(),
            "animator": animator.lower(), "current": current,
            "inTransition": in_transition, "next": next_state,
            "transition": transition,
        })
    return samples


def validate_global_chronology(samples: list[dict[str, Any]]) -> None:
    for index in range(1, len(samples)):
        before = samples[index - 1]
        after = samples[index]
        require(after["ordinal"] > before["ordinal"],
                f"sample ordinal does not increase at sample {index}")
        require(after["qpcTick"] > before["qpcTick"],
                f"QPC cadence does not increase at sample {index}")
        require(after["presentOrdinal"] >= before["presentOrdinal"],
                f"Present ordinal regresses at sample {index}")
        require(after["lastPresentQpc"] >= before["lastPresentQpc"],
                f"associated Present QPC regresses at sample {index}")
        if after["presentOrdinal"] == before["presentOrdinal"]:
            require(after["lastPresentQpc"] == before["lastPresentQpc"],
                    f"same Present ordinal has inconsistent QPC at sample {index}")
        else:
            require(after["lastPresentQpc"] > before["lastPresentQpc"],
                    f"new Present ordinal lacks a new QPC at sample {index}")

    # Runtime serialization derives these pairs across the entire retained
    # sample vector, including an identity-segment boundary.
    for index, sample in enumerate(samples):
        next_index = next((later for later in range(index + 1, len(samples))
                           if samples[later]["presentOrdinal"] >
                           sample["presentOrdinal"]), None)
        expected_ordinal = (None if next_index is None else
                            samples[next_index]["presentOrdinal"])
        expected_qpc = (None if next_index is None else
                        samples[next_index]["lastPresentQpc"])
        require(sample["nextObservedPresentOrdinal"] == expected_ordinal and
                sample["nextObservedPresentQpc"] == expected_qpc,
                f"derived next observed Present disagrees at sample {index}")


def classify(samples: list[dict[str, Any]]) -> dict[str, Any]:
    first = samples[0]
    identity = (first["owner"], first["animator"], first["threadId"],
                first["qpcFrequency"])
    for index, sample in enumerate(samples):
        observed = (sample["owner"], sample["animator"], sample["threadId"],
                    sample["qpcFrequency"])
        require(observed == identity,
                f"ownership identity changes at sample {index}")

        current = sample["current"]
        current_hash = current["fullPathHash"]
        require(current_hash in (EXPECTED_START_STATE["fullPathHash"],
                                 EXPECTED_LOOP_STATE["fullPathHash"]),
                f"unexpected current state hash at sample {index}")
        require((current_hash == EXPECTED_START_STATE["fullPathHash"] and
                 current["loop"] == 0) or
                (current_hash == EXPECTED_LOOP_STATE["fullPathHash"] and
                 current["loop"] == 1),
                f"exact current state loop semantics disagree at sample {index}")
        if sample["inTransition"]:
            require(current_hash == EXPECTED_START_STATE["fullPathHash"] and
                    sample["next"]["fullPathHash"] ==
                    EXPECTED_LOOP_STATE["fullPathHash"] and
                    sample["next"]["loop"] == 1,
                    f"exact transition state semantics disagree at sample {index}")

    start = next((index for index, sample in enumerate(samples)
                  if not sample["inTransition"] and
                  sample["current"]["loop"] == 0 and
                  sample["current"]["fullPathHash"] ==
                  EXPECTED_START_STATE["fullPathHash"]), None)
    require(start is not None,
            "exact Base Layer.Overview.FromOveview start state is absent")
    start_hash = samples[start]["current"]["fullPathHash"]

    transition_start = None
    loop_hash = None
    for index in range(start + 1, len(samples)):
        sample = samples[index]
        next_state = sample["next"]
        if (sample["inTransition"] and
                sample["current"]["fullPathHash"] == start_hash and
                next_state["loop"] == 1 and
                next_state["fullPathHash"] ==
                EXPECTED_LOOP_STATE["fullPathHash"]):
            transition_start = index
            loop_hash = next_state["fullPathHash"]
            break
    require(transition_start is not None,
            "start-to-loop transition is absent")

    prior_start_time = samples[start]["current"]["normalizedTime"]
    for index in range(start + 1, transition_start + 1):
        current_time = samples[index]["current"]["normalizedTime"]
        require(current_time + 1.0e-5 >= prior_start_time,
                f"start state time regresses at sample {index}")
        prior_start_time = current_time

    transition_end = None
    prior_progress = samples[transition_start]["transition"]["normalizedTime"]
    for index in range(transition_start, len(samples)):
        sample = samples[index]
        if not sample["inTransition"]:
            transition_end = index
            break
        require(sample["current"]["fullPathHash"] == start_hash and
                sample["next"]["fullPathHash"] == loop_hash and
                sample["next"]["loop"] == 1,
                f"transition identity changes at sample {index}")
        current_time = sample["current"]["normalizedTime"]
        require(current_time + 1.0e-5 >= prior_start_time,
                f"start state time regresses during transition at sample {index}")
        progress = sample["transition"]["normalizedTime"]
        require(progress + 1.0e-5 >= prior_progress,
                f"transition progress regresses at sample {index}")
        prior_progress = progress
        prior_start_time = current_time
    require(transition_end is not None,
            "transition does not settle into the loop")
    require(samples[transition_end]["current"]["fullPathHash"] == loop_hash and
            samples[transition_end]["current"]["loop"] == 1,
            "transition ends on a different or non-loop state")

    require(transition_end + 2 < len(samples),
            "three settled loop samples are absent")
    for index in range(transition_end, transition_end + 3):
        sample = samples[index]
        require(not sample["inTransition"] and
                sample["current"]["loop"] == 1 and
                sample["current"]["fullPathHash"] == loop_hash,
                f"loop is not settled at sample {index}")
        if index != transition_end:
            require(sample["current"]["normalizedTime"] + 1.0e-5 >=
                    samples[index - 1]["current"]["normalizedTime"],
                    f"settled loop time regresses at sample {index}")

    wrap = None
    for index in range(transition_end + 1, len(samples)):
        before = samples[index - 1]
        after = samples[index]
        if (before["inTransition"] or after["inTransition"] or
                before["current"]["fullPathHash"] != loop_hash or
                after["current"]["fullPathHash"] != loop_hash):
            continue
        require(after["current"]["normalizedTime"] + 1.0e-5 >=
                before["current"]["normalizedTime"],
                f"loop time regresses at sample {index}")
        if (math.floor(after["current"]["normalizedTime"]) ==
                math.floor(before["current"]["normalizedTime"]) + 1):
            wrap = index
            break
    require(wrap is not None, "first adjacent loop wrap is absent")

    for index in range(1, len(samples)):
        before = samples[index - 1]
        after = samples[index]
        require(after["ordinal"] > before["ordinal"],
                f"sample ordinal does not increase at sample {index}")
        require(after["qpcTick"] > before["qpcTick"],
                f"QPC cadence does not increase at sample {index}")
        require(after["presentOrdinal"] >= before["presentOrdinal"],
                f"Present ordinal regresses at sample {index}")
        require(after["lastPresentQpc"] >= before["lastPresentQpc"],
                f"associated Present QPC regresses at sample {index}")
        if after["presentOrdinal"] == before["presentOrdinal"]:
            require(after["lastPresentQpc"] == before["lastPresentQpc"],
                    f"same Present ordinal has inconsistent QPC at sample {index}")
        else:
            require(after["lastPresentQpc"] > before["lastPresentQpc"],
                    f"new Present ordinal lacks a new QPC at sample {index}")

    return {
        "stableIdentity": True,
        "stateHashesValid": True,
        "cadenceValid": True,
        "transitionObserved": True,
        "loopSettled": True,
        "firstWrapObserved": True,
        "sequenceComplete": True,
        "indices": {
            "start": start, "transitionStart": transition_start,
            "transitionEnd": transition_end, "firstWrap": wrap,
        },
        "stateHashes": {
            "startFullPath": start_hash, "loopFullPath": loop_hash,
        },
    }


def classify_segments(samples: list[dict[str, Any]]) -> dict[str, Any]:
    segments: list[dict[str, Any]] = []
    offset = 0
    while offset < len(samples):
        end = offset + 1
        identity = (samples[offset]["owner"], samples[offset]["animator"])
        while (end < len(samples) and
               (samples[end]["owner"], samples[end]["animator"]) == identity):
            end += 1
        try:
            classification = classify(samples[offset:end])
        except TimelineError as exc:
            segments.append({
                "offset": offset,
                "sampleCount": end - offset,
                "owner": identity[0],
                "animator": identity[1],
                "complete": False,
                "diagnostic": str(exc),
            })
        else:
            segments.append({
                "offset": offset,
                "sampleCount": end - offset,
                "owner": identity[0],
                "animator": identity[1],
                "complete": True,
                "classification": classification,
            })
        offset = end

    complete = [index for index, segment in enumerate(segments)
                if segment["complete"]]
    if not complete and len(segments) == 1:
        raise TimelineError(segments[0]["diagnostic"])
    require(complete, "no identity segment contains a complete exact "
            "Endminf start-to-loop-wrap sequence")
    selected_index = complete[0]
    selected = segments[selected_index]
    local = selected["classification"]
    derived = {**local, "indices": {
        key: value + selected["offset"]
        for key, value in local["indices"].items()
    }}
    return {
        "classification": derived,
        "classifiedIdentitySegments": len(segments),
        "completeIdentitySegments": len(complete),
        "selectedIdentitySegment": selected_index,
        "selectedSegmentOffset": selected["offset"],
        "selectedSegmentSampleCount": selected["sampleCount"],
        "segments": segments,
    }


def validate_metadata(metadata: dict[str, Any],
                      samples: list[dict[str, Any]],
                      segmented: dict[str, Any]) -> dict[str, Any]:
    derived = segmented["classification"]
    require(metadata.get("schema") == EXPECTED_SCHEMA,
            "animator timeline metadata schema is invalid")
    require(metadata.get("characterId") == EXPECTED_CHARACTER,
            "animator timeline characterId is not chr_0003_endminf")
    for field in ("hooksInstalled", "quiescentCleanup", "recorderComplete",
                  "stateHashesValid", "stableIdentity", "cadenceValid", "transitionObserved",
                  "loopSettled", "firstWrapObserved", "sequenceComplete",
                  "complete"):
        require(metadata.get(field) is True,
                f"animator timeline metadata {field} gate is not true")
    require(integer(metadata.get("sampleCapacity"), "sampleCapacity", 1) ==
            EXPECTED_CAPACITY, "animator sampleCapacity is not 8192")
    sample_count = integer(metadata.get("sampleCount"), "sampleCount", 1)
    require(sample_count == len(samples),
            "metadata sampleCount differs from samples length")
    require(sample_count <= EXPECTED_CAPACITY,
            "metadata sampleCount exceeds sampleCapacity")

    counters = {}
    for field in ("originalCalls", "candidateCalls", "ownerMatches",
                  "ownerMismatches", "ownerReadFailures",
                  "exactOwnerReadFailures", "tickNotStarted",
                  "invalidAnimator", "stateApiFailures", "qpcFailures",
                  "presentClockFailures", "ownershipChanges",
                  "identitySegments", "sampleOverflow"):
        counters[field] = integer(metadata.get(field), field)
    require(counters["originalCalls"] == counters["candidateCalls"],
            "originalCalls and candidateCalls differ")
    require(counters["candidateCalls"] == counters["ownerMatches"] +
            counters["ownerMismatches"] + counters["ownerReadFailures"],
            "candidate owner counters do not account for candidateCalls")
    require(counters["ownerMatches"] >= sample_count,
            "ownerMatches is less than sampleCount")
    for field in ("ownerReadFailures", "exactOwnerReadFailures",
                  "tickNotStarted", "invalidAnimator",
                  "stateApiFailures", "qpcFailures",
                  "presentClockFailures", "sampleOverflow"):
        require(counters[field] == 0,
                f"animator timeline metadata {field} is nonzero")
    require(counters["identitySegments"] ==
            segmented["classifiedIdentitySegments"] and
            counters["ownershipChanges"] == counters["identitySegments"] - 1,
            "animator identity-segment lifecycle counters disagree")
    reentrant_calls = integer(metadata.get("reentrantCalls"), "reentrantCalls")
    require(reentrant_calls == 0,
            "animator timeline metadata reentrantCalls is nonzero")
    counters["reentrantCalls"] = reentrant_calls

    require(metadata.get("indices") == derived["indices"],
            "metadata indices disagree with independently derived indices")
    require(metadata.get("stateHashes") == derived["stateHashes"],
            "metadata stateHashes disagree with independently derived hashes")
    for field in ("classifiedIdentitySegments", "completeIdentitySegments",
                  "selectedIdentitySegment", "selectedSegmentOffset",
                  "selectedSegmentSampleCount"):
        require(integer(metadata.get(field), field) == segmented[field],
                f"metadata {field} disagrees with independent segmentation")
    for field in ("stableIdentity", "stateHashesValid", "cadenceValid", "transitionObserved",
                  "loopSettled", "firstWrapObserved", "sequenceComplete"):
        require(metadata.get(field) == derived[field],
                f"metadata {field} disagrees with independent classification")
    return {
        "sampleCapacity": EXPECTED_CAPACITY,
        "sampleCount": sample_count,
        "counters": counters,
        "classifiedIdentitySegments": segmented["classifiedIdentitySegments"],
        "completeIdentitySegments": segmented["completeIdentitySegments"],
        "selectedIdentitySegment": segmented["selectedIdentitySegment"],
        "selectedSegmentOffset": segmented["selectedSegmentOffset"],
        "selectedSegmentSampleCount": segmented["selectedSegmentSampleCount"],
    }


def build_report(capture: Path, *,
                 expected_observer_sha256: str | None = None,
                 expected_observer_bytes: int | None = None) -> dict[str, Any]:
    capture = capture.resolve()
    observer = capture / "private/EndfieldCapture.dll"
    try:
        observer_facts = OBSERVER_BUILD.validate_observer_binary(
            observer, build_label="animator timeline build",
            expected_sha256=expected_observer_sha256,
            expected_bytes=expected_observer_bytes)
    except OBSERVER_BUILD.ObserverBuildContractError as exc:
        raise TimelineError(str(exc)) from exc
    observed_sha = observer_facts["sha256"]
    session = BASE.validate_session(capture)
    summary_path = capture / "graphics/summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    require(summary.get("endminfAnimatorRequested") is True,
            "graphics summary endminfAnimatorRequested gate is not true")
    require(summary.get("endminfAnimatorComplete") is True,
            "graphics summary endminfAnimatorComplete gate is not true")

    metadata_path = capture / "graphics/endminf_animator/metadata.json"
    require(metadata_path.is_file(),
            f"Endminf animator metadata is absent: {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    require(isinstance(metadata, dict), "animator metadata is not an object")
    samples = validate_samples(metadata.get("samples"))
    validate_global_chronology(samples)
    segmented = classify_segments(samples)
    derived = segmented["classification"]
    validated_metadata = validate_metadata(metadata, samples, segmented)

    start = derived["indices"]["start"]
    transition_start = derived["indices"]["transitionStart"]
    transition_end = derived["indices"]["transitionEnd"]
    wrap = derived["indices"]["firstWrap"]
    frequency = samples[start]["qpcFrequency"]
    start_state = samples[start]["current"]
    transition_sample = samples[transition_start]
    transition_state = transition_sample["current"]
    transition_contract = transition_sample["transition"]
    transition_duration = transition_contract["duration"]
    if transition_contract["hasFixedDuration"] == 0:
        transition_duration *= transition_state["length"]
    timing = {
        "observedQpcBoundaryIntervals": {
            "firstRetainedStartSampleToFirstTransitionSampleSeconds":
            (samples[transition_start]["qpcTick"] -
             samples[start]["qpcTick"]) / frequency,
            "firstTransitionSampleToFirstSettledLoopSampleSeconds":
            (samples[transition_end]["qpcTick"] -
             samples[transition_start]["qpcTick"]) / frequency,
            "firstSettledLoopSampleToFirstAdjacentFloorRiseSeconds":
            (samples[wrap]["qpcTick"] -
             samples[transition_end]["qpcTick"]) / frequency,
            "firstRetainedStartSampleToFirstAdjacentFloorRiseSeconds":
            (samples[wrap]["qpcTick"] - samples[start]["qpcTick"]) /
            frequency,
            "boundary": (
                "Tick-observed, Present-associated intervals are quantized "
                "capture boundaries, not exact state-entry durations."),
        },
        "animatorStateContract": {
            "start": {
                "lengthSeconds": start_state["length"],
                "speed": start_state["speed"],
                "speedMultiplier": start_state["speedMultiplier"],
                "normalizedTimeAtFirstRetainedStart":
                    start_state["normalizedTime"],
                "stateSecondsAtFirstRetainedStart":
                    start_state["derived"]["unwrappedStateSeconds"],
                "normalizedTimeAtTransitionStart":
                    transition_state["normalizedTime"],
                "stateSecondsAtTransitionStart":
                    transition_state["derived"]["unwrappedStateSeconds"],
            },
            "transition": {
                "hasFixedDuration": transition_contract["hasFixedDuration"],
                "duration": transition_contract["duration"],
                "derivedContractSeconds": transition_duration,
            },
            "loop": {
                "lengthSeconds": samples[transition_end]["current"]["length"],
                "speed": samples[transition_end]["current"]["speed"],
                "speedMultiplier":
                    samples[transition_end]["current"]["speedMultiplier"],
                "normalizedTimeAtTransitionStart":
                    transition_sample["next"]["normalizedTime"],
                "normalizedTimeAtFirstSettledSample":
                    samples[transition_end]["current"]["normalizedTime"],
            },
        },
    }
    return {
        "schema": "endfield.endminf-animator-timeline-capture.v1",
        "status": "validated_endminf_start_transition_loop_wrap_evidence",
        "capture": str(capture),
        "observerSha256": observed_sha,
        "session": session,
        "summary": {"endminfAnimatorRequested": True,
                    "endminfAnimatorComplete": True},
        "metadata": validated_metadata,
        "classification": derived,
        "identitySegments": segmented["segments"],
        "timing": timing,
        "stateHashes": derived["stateHashes"],
        "controllerStateEvidence": {
            "start": EXPECTED_START_STATE,
            "loop": EXPECTED_LOOP_STATE,
            "boundary": (
                "Exact full-path hashes are joined to the recovered source "
                "AnimatorController state names, rather than inferred from "
                "generic non-loop/loop behavior."),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = (args.output or args.capture /
              "endminf_animator_timeline_verification.json")
    try:
        report = build_report(args.capture)
    except (OSError, ValueError, json.JSONDecodeError, TimelineError,
            BASE.ContractError) as exc:
        report = {
            "schema": "endfield.endminf-animator-timeline-capture.v1",
            "status": "validation_failed",
            "capture": str(args.capture.resolve()),
            "diagnostic": str(exc),
        }
        exit_code = 1
    else:
        exit_code = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if exit_code:
        print("ERROR: " + report["diagnostic"])
    print(output)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

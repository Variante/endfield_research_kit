from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_animator_timeline_capture",
    HERE / "verify_endminf_animator_timeline_capture.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

START_HASH = 1560421867       # 0x5D0225EB
LOOP_HASH = -1345940313       # 0xAFC694A7


def state(full_hash: int, normalized: float, loop: int) -> dict[str, object]:
    length = 2.0
    cycle = int(normalized // 1)
    return {
        "nameHash": 101,
        "pathHash": 102,
        "fullPathHash": full_hash,
        "normalizedTime": normalized,
        "length": length,
        "speed": 1.0,
        "speedMultiplier": 1.0,
        "tagHash": 0,
        "loop": loop,
        "syncGroup": 0,
        "syncGroupRole": 0,
        "cullingMode": 0,
        "sourceMessage": 0,
        "derived": {
            "unwrappedStateSeconds": normalized * length,
            "cycleIndex": cycle,
            "cycleLocalSeconds": (normalized - cycle) * length,
        },
    }


def transition(progress: float) -> dict[str, object]:
    return {
        "fullPathHash": 7001,
        "userNameHash": 7002,
        "nameHash": 7003,
        "hasFixedDuration": 0,
        "duration": 0.3,
        "normalizedTime": progress,
        "anyState": 0,
        "transitionType": 0,
    }


def sample(index: int, current: dict[str, object], *,
           next_state: dict[str, object] | None = None,
           progress: float | None = None) -> dict[str, object]:
    in_transition = next_state is not None
    return {
        "ordinal": index + 1,
        "qpcTick": 1000 + index * 100,
        "qpcFrequency": 1000,
        "priorPresentOrdinal": 10 + index,
        "priorPresentQpc": 900 + index * 100,
        "nextObservedPresentOrdinal": None,
        "nextObservedPresentQpc": None,
        "deltaTime": 1.0 / 60.0,
        "threadId": 99,
        "owner": "0x1234",
        "animator": "0x5678",
        "current": current,
        "inTransition": in_transition,
        "next": next_state,
        "transition": transition(progress if progress is not None else 0.0)
        if in_transition else None,
    }


def good_samples() -> list[dict[str, object]]:
    samples = [
        sample(0, state(START_HASH, 0.0, 0)),
        sample(1, state(START_HASH, 0.3, 0)),
        sample(2, state(START_HASH, 0.6, 0),
               next_state=state(LOOP_HASH, 0.0, 1), progress=0.2),
        sample(3, state(START_HASH, 0.9, 0),
               next_state=state(LOOP_HASH, 0.05, 1), progress=0.8),
        sample(4, state(LOOP_HASH, 0.1, 1)),
        sample(5, state(LOOP_HASH, 0.4, 1)),
        sample(6, state(LOOP_HASH, 0.8, 1)),
        sample(7, state(LOOP_HASH, 1.1, 1)),
    ]
    for index, row in enumerate(samples[:-1]):
        row["nextObservedPresentOrdinal"] = samples[index + 1][
            "priorPresentOrdinal"]
        row["nextObservedPresentQpc"] = samples[index + 1][
            "priorPresentQpc"]
    return samples


class AnimatorTimelineCaptureTests(unittest.TestCase):
    def make_capture(self, root: Path) -> str:
        graphics = root / "graphics"
        sidecar = graphics / "endminf_animator"
        private = root / "private"
        sidecar.mkdir(parents=True)
        private.mkdir()
        observer = private / "EndfieldCapture.dll"
        observer.write_bytes(b"animator timeline observer")
        observer_hash = MODULE.sha256(observer)
        summary = {
            "complete": True,
            "cadenceValid": True,
            "dropped": 0,
            "deferredFailed": False,
            "deferredStagedSlots": 72,
            "deferredDrainedSlots": 72,
            "deferredPublishedSlots": 72,
            "endminfAnimatorRequested": True,
            "endminfAnimatorComplete": True,
        }
        (graphics / "summary.json").write_text(
            json.dumps(summary), encoding="utf-8")
        samples = good_samples()
        metadata = {
            "schema": MODULE.EXPECTED_SCHEMA,
            "characterId": MODULE.EXPECTED_CHARACTER,
            "hooksInstalled": True,
            "quiescentCleanup": True,
            "sampleCapacity": 8192,
            "sampleCount": len(samples),
            "originalCalls": 10,
            "candidateCalls": 10,
            "ownerMatches": 8,
            "ownerMismatches": 2,
            "ownerReadFailures": 0,
            "exactOwnerReadFailures": 0,
            "tickNotStarted": 0,
            "invalidAnimator": 0,
            "stateApiFailures": 0,
            "qpcFailures": 0,
            "presentClockFailures": 0,
            "ownershipChanges": 0,
            "identitySegments": 1,
            "sampleOverflow": 0,
            "reentrantCalls": 0,
            "recorderComplete": True,
            "stateHashesValid": True,
            "stableIdentity": True,
            "cadenceValid": True,
            "transitionObserved": True,
            "loopSettled": True,
            "firstWrapObserved": True,
            "sequenceComplete": True,
            "classifiedIdentitySegments": 1,
            "completeIdentitySegments": 1,
            "selectedIdentitySegment": 0,
            "selectedSegmentOffset": 0,
            "selectedSegmentSampleCount": len(samples),
            "indices": {"start": 0, "transitionStart": 2,
                        "transitionEnd": 4, "firstWrap": 7},
            "stateHashes": {"startFullPath": START_HASH,
                            "loopFullPath": LOOP_HASH},
            "samples": samples,
            "complete": True,
        }
        (sidecar / "metadata.json").write_text(
            json.dumps(metadata), encoding="utf-8")
        return observer_hash

    def report(self, mutate=None) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            observer_hash = self.make_capture(capture)
            if mutate:
                mutate(capture)
            return MODULE.build_report(
                capture, expected_observer_sha256=observer_hash)

    @staticmethod
    def metadata(capture: Path) -> tuple[Path, dict[str, object]]:
        path = capture / "graphics/endminf_animator/metadata.json"
        return path, json.loads(path.read_text(encoding="utf-8"))

    def test_success(self) -> None:
        report = self.report()
        self.assertEqual(
            report["status"],
            "validated_endminf_start_transition_loop_wrap_evidence")
        self.assertEqual(report["classification"]["indices"]["firstWrap"], 7)
        self.assertEqual(
            report["controllerStateEvidence"]["start"]["name"],
            "Base Layer.Overview.FromOveview")

    def test_wrong_observer_hash_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            self.make_capture(capture)
            with self.assertRaisesRegex(MODULE.TimelineError,
                                        "observer SHA-256 differs"):
                MODULE.build_report(capture, expected_observer_sha256="00")

    def test_wrong_observer_size_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            observer_hash = self.make_capture(capture)
            observer = capture / "private/EndfieldCapture.dll"
            with self.assertRaisesRegex(MODULE.TimelineError,
                                        "observer byte size differs"):
                MODULE.build_report(
                    capture, expected_observer_sha256=observer_hash,
                    expected_observer_bytes=observer.stat().st_size + 1)

    def test_default_contract_matches_current_release_artifact(self) -> None:
        observer = (HERE.parents[1] /
                    "tools/EndfieldCapture/build-local/Release/EndfieldCapture.dll")
        if not observer.is_file():
            self.skipTest("local Release observer has not been built")
        facts = MODULE.OBSERVER_BUILD.validate_observer_binary(
            observer, build_label="test Release observer")
        self.assertEqual(
            MODULE.OBSERVER_CONTRACT["runtime"]["sha256"], facts["sha256"])
        self.assertEqual(
            MODULE.OBSERVER_CONTRACT["runtime"]["bytes"], facts["bytes"])

    def test_missing_transition_fails(self) -> None:
        def mutate(capture: Path) -> None:
            path, data = self.metadata(capture)
            for index in (2, 3):
                data["samples"][index]["inTransition"] = False
                data["samples"][index]["next"] = None
                data["samples"][index]["transition"] = None
            path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(MODULE.TimelineError,
                                    "transition is absent"):
            self.report(mutate)

    def test_transition_regression_fails(self) -> None:
        def mutate(capture: Path) -> None:
            path, data = self.metadata(capture)
            data["samples"][3]["transition"]["normalizedTime"] = 0.1
            path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(MODULE.TimelineError,
                                    "transition progress regresses"):
            self.report(mutate)

    def test_present_gap_and_duplicate_are_valid_when_pairing_is_monotonic(self) -> None:
        def mutate(capture: Path) -> None:
            path, data = self.metadata(capture)
            # Two ticks may associate with one prior Present.
            data["samples"][5]["priorPresentOrdinal"] = 14
            data["samples"][5]["priorPresentQpc"] = 1300
            # Later samples may skip Present ordinals; the association remains
            # ordered and each new ordinal carries a later Present QPC.
            for index, ordinal in ((6, 18), (7, 20)):
                data["samples"][index]["priorPresentOrdinal"] = ordinal
            data["samples"][6]["ordinal"] += 2
            data["samples"][7]["ordinal"] += 2
            rows = data["samples"]
            for row_index, row in enumerate(rows):
                later = next((candidate for candidate in rows[row_index + 1:]
                              if candidate["priorPresentOrdinal"] >
                              row["priorPresentOrdinal"]), None)
                row["nextObservedPresentOrdinal"] = (None if later is None else
                    later["priorPresentOrdinal"])
                row["nextObservedPresentQpc"] = (None if later is None else
                    later["priorPresentQpc"])
            path.write_text(json.dumps(data), encoding="utf-8")
        report = self.report(mutate)
        self.assertTrue(report["classification"]["cadenceValid"])

    def test_backward_present_pair_fails(self) -> None:
        def mutate(capture: Path) -> None:
            path, data = self.metadata(capture)
            data["samples"][5]["priorPresentOrdinal"] = 13
            path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(MODULE.TimelineError,
                                    "Present ordinal regresses"):
            self.report(mutate)

    def test_wrong_exact_state_fails(self) -> None:
        def mutate(capture: Path) -> None:
            path, data = self.metadata(capture)
            data["samples"][0]["current"] = state(12345, 0.0, 0)
            path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(MODULE.TimelineError,
                                    "unexpected current state hash"):
            self.report(mutate)

    def test_active_failure_counters_fail(self) -> None:
        for field in ("ownerReadFailures", "tickNotStarted", "reentrantCalls"):
            with self.subTest(field=field):
                def mutate(capture: Path, selected=field) -> None:
                    path, data = self.metadata(capture)
                    data[selected] = 1
                    if selected == "ownerReadFailures":
                        data["ownerMismatches"] -= 1
                    path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaisesRegex(MODULE.TimelineError,
                                            f"{field} is nonzero"):
                    self.report(mutate)

    def test_nonpositive_length_fails(self) -> None:
        def mutate(capture: Path) -> None:
            path, data = self.metadata(capture)
            data["samples"][5]["current"]["length"] = 0.0
            path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(MODULE.TimelineError,
                                    "length is not positive"):
            self.report(mutate)

    def test_start_and_loop_time_regressions_fail(self) -> None:
        for index, expected in ((3, "start state time regresses"),
                                (6, "loop.*time regresses")):
            with self.subTest(index=index):
                def mutate(capture: Path, selected=index) -> None:
                    path, data = self.metadata(capture)
                    previous = data["samples"][selected - 1]["current"][
                        "normalizedTime"]
                    data["samples"][selected]["current"] = state(
                        START_HASH if selected == 3 else LOOP_HASH,
                        previous - 0.1, 0 if selected == 3 else 1)
                    path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaisesRegex(MODULE.TimelineError, expected):
                    self.report(mutate)

    def test_fragmented_identities_without_complete_segment_fail(self) -> None:
        def mutate(capture: Path) -> None:
            path, data = self.metadata(capture)
            data["samples"][5]["animator"] = "0x9999"
            path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(MODULE.TimelineError,
                                    "no identity segment contains"):
            self.report(mutate)

    def test_incomplete_identity_then_complete_recreation_passes(self) -> None:
        def mutate(capture: Path) -> None:
            path, data = self.metadata(capture)
            rows = data["samples"]
            for row in rows:
                row["ordinal"] += 1
            prefix = sample(0, state(LOOP_HASH, 0.4, 1))
            prefix["qpcTick"] = 900
            prefix["priorPresentOrdinal"] = 9
            prefix["priorPresentQpc"] = 800
            prefix["nextObservedPresentOrdinal"] = rows[0][
                "priorPresentOrdinal"]
            prefix["nextObservedPresentQpc"] = rows[0]["priorPresentQpc"]
            prefix["owner"] = "0xaaaa"
            prefix["animator"] = "0xbbbb"
            data["samples"] = [prefix, *rows]
            data["sampleCount"] = 9
            data["originalCalls"] = 11
            data["candidateCalls"] = 11
            data["ownerMatches"] = 9
            data["ownershipChanges"] = 1
            data["identitySegments"] = 2
            data["classifiedIdentitySegments"] = 2
            data["completeIdentitySegments"] = 1
            data["selectedIdentitySegment"] = 1
            data["selectedSegmentOffset"] = 1
            data["selectedSegmentSampleCount"] = 8
            data["indices"] = {key: value + 1
                               for key, value in data["indices"].items()}
            path.write_text(json.dumps(data), encoding="utf-8")

        report = self.report(mutate)
        self.assertEqual(report["metadata"]["classifiedIdentitySegments"], 2)
        self.assertEqual(report["metadata"]["selectedIdentitySegment"], 1)
        self.assertEqual(report["classification"]["indices"]["firstWrap"], 8)

    def test_two_complete_sequential_identities_pass_and_select_first(self) -> None:
        def mutate(capture: Path) -> None:
            path, data = self.metadata(capture)
            first = data["samples"]
            second = json.loads(json.dumps(first))
            for row in second:
                row["ordinal"] += len(first)
                row["qpcTick"] += 1000
                row["priorPresentOrdinal"] += 20
                row["priorPresentQpc"] += 1000
                row["owner"] = "0xaaaa"
                row["animator"] = "0xbbbb"
            rows = [*first, *second]
            for row_index, row in enumerate(rows):
                later = next((candidate for candidate in rows[row_index + 1:]
                              if candidate["priorPresentOrdinal"] >
                              row["priorPresentOrdinal"]), None)
                row["nextObservedPresentOrdinal"] = (None if later is None else
                    later["priorPresentOrdinal"])
                row["nextObservedPresentQpc"] = (None if later is None else
                    later["priorPresentQpc"])
            data["samples"] = rows
            data["sampleCount"] = 16
            data["originalCalls"] = 18
            data["candidateCalls"] = 18
            data["ownerMatches"] = 16
            data["ownershipChanges"] = 1
            data["identitySegments"] = 2
            data["classifiedIdentitySegments"] = 2
            data["completeIdentitySegments"] = 2
            path.write_text(json.dumps(data), encoding="utf-8")

        report = self.report(mutate)
        self.assertEqual(report["metadata"]["completeIdentitySegments"], 2)
        self.assertEqual(report["metadata"]["selectedIdentitySegment"], 0)
        self.assertEqual(report["classification"]["indices"]["firstWrap"], 7)

    def test_missing_wrap_fails(self) -> None:
        def mutate(capture: Path) -> None:
            path, data = self.metadata(capture)
            replacement = state(LOOP_HASH, 0.95, 1)
            data["samples"][7]["current"] = replacement
            path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(MODULE.TimelineError,
                                    "adjacent loop wrap is absent"):
            self.report(mutate)

    def test_metadata_index_hash_mismatch_fails(self) -> None:
        def mutate(capture: Path) -> None:
            path, data = self.metadata(capture)
            data["indices"]["firstWrap"] = 6
            path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(MODULE.TimelineError,
                                    "metadata indices disagree"):
            self.report(mutate)

    def test_nonfinite_state_fails(self) -> None:
        def mutate(capture: Path) -> None:
            path, data = self.metadata(capture)
            data["samples"][5]["current"]["normalizedTime"] = float("nan")
            path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(MODULE.TimelineError,
                                    "not a finite number"):
            self.report(mutate)


if __name__ == "__main__":
    unittest.main()

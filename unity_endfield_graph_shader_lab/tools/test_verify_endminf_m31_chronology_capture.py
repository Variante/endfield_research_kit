from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_m31_chronology_capture",
    HERE / "verify_endminf_m31_chronology_capture.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def target(kind: str) -> dict[str, object]:
    common = {"bound": True, "width": 4, "height": 2,
              "viewDimension": 4, "sampleCount": 1,
              "sampleQuality": 0, "flags": 0}
    if kind == "rtv0":
        return common | {"viewId": 10, "resourceId": 11,
                         "textureFormat": 26, "viewFormat": 26}
    if kind == "rtv1":
        return common | {"viewId": 20, "resourceId": 21,
                         "textureFormat": 10, "viewFormat": 10}
    return common | {"viewId": 30, "resourceId": 31,
                     "textureFormat": 19, "viewFormat": 20,
                     "viewDimension": 3, "flags": 3}


class M31ChronologyCaptureTests(unittest.TestCase):
    def make_capture(self, root: Path) -> str:
        graphics = root / "graphics"
        sidecar = graphics / "m31_chronology"
        private = root / "private"
        sidecar.mkdir(parents=True)
        private.mkdir()
        observer = private / "EndfieldCapture.dll"
        observer.write_bytes(b"corrected observer")
        observer_hash = MODULE.sha256(observer)
        summary = {
            "complete": True, "cadenceValid": True, "dropped": 0,
            "deferredFailed": False, "deferredStagedSlots": 72,
            "deferredDrainedSlots": 72, "deferredPublishedSlots": 72,
            "m31ChronologyRequested": True,
            "m31ChronologyTriggered": True,
            "m31ChronologyTriadComplete": True,
            "m31ChronologyGpuComplete": True,
            "m31ChronologyPublished": True,
            "m31ChronologyFailed": False,
            "m31ChronologyCensusCount": 2,
            "m31ChronologyCensusTruncated": False,
            "m31ChronologyStagingBytes": 192,
            "m31ChronologyFailureHresult": 0,
        }
        (graphics / "summary.json").write_text(
            json.dumps(summary), encoding="utf-8")
        names = [f"draw{draw}_{phase}.bin" for draw in range(3)
                 for phase in ("pre", "post")]
        blob_rows = []
        for index, name in enumerate(names):
            data = bytes([index // 2 + (index % 2)]) * 32
            (sidecar / name).write_bytes(data)
            blob_rows.append({"file": name, "drawIndex": index // 2,
                              "afterDraw": index % 2 == 1,
                              "rowPitch": 16, "bytes": 32})
        metadata = {
            "schema": "endfieldCapture.m31Chronology.v1",
            "observationOnly": True,
            "originalCallsForwardedExactlyOnce": True,
            "complete": True,
            "triad": [1082, 443, 32], "presentOrdinal": 9,
            "censusCapacity": 64, "censusCount": 2,
            "censusTruncated": False, "reservedStagingBytes": 192,
            "targets": [{"drawIndex": index,
                         "rtv0": target("rtv0"),
                         "rtv1": target("rtv1"),
                         "dsv": target("dsv")} for index in range(3)],
            "census": [
                {"kind": 3, "afterM31Draw": 1,
                 "arguments": [6, 1, 10, 20, 0]},
                {"kind": 4, "afterM31Draw": 2,
                 "arguments": [8, 8, 1]}],
            "blobs": blob_rows,
        }
        (sidecar / "metadata.json").write_text(
            json.dumps(metadata), encoding="utf-8")
        return observer_hash

    def report(self, mutate=None) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            expected_hash = self.make_capture(capture)
            if mutate:
                mutate(capture)
            return MODULE.build_report(
                capture, expected_observer_sha256=expected_hash,
                expected_width=4, expected_height=2)

    def test_complete_sidecar_passes(self) -> None:
        report = self.report()
        self.assertEqual(report["status"],
                         "validated_m31_three_draw_chronology_boundary_evidence")
        self.assertTrue(all(row["changedBytes"] == 32
                            for row in report["drawDeltas"]))

    def test_wrong_observer_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary)
            self.make_capture(capture)
            with self.assertRaisesRegex(MODULE.ChronologyError,
                                        "observer SHA-256 differs"):
                MODULE.build_report(capture, expected_observer_sha256="00",
                                    expected_width=4, expected_height=2)

    def test_summary_failure_fails_closed(self) -> None:
        def mutate(capture: Path) -> None:
            path = capture / "graphics/summary.json"
            data = json.loads(path.read_text())
            data["m31ChronologyFailed"] = True
            path.write_text(json.dumps(data))
        with self.assertRaisesRegex(MODULE.ChronologyError,
                                    "chronology failure"):
            self.report(mutate)

    def test_malformed_census_call_fails_closed(self) -> None:
        def mutate(capture: Path) -> None:
            path = capture / "graphics/m31_chronology/metadata.json"
            data = json.loads(path.read_text())
            data["census"][0]["arguments"] = [6, 1, 10]
            path.write_text(json.dumps(data))
        with self.assertRaisesRegex(MODULE.ChronologyError,
                                    "arguments do not match"):
            self.report(mutate)

    def test_writable_depth_fails_closed(self) -> None:
        def mutate(capture: Path) -> None:
            path = capture / "graphics/m31_chronology/metadata.json"
            data = json.loads(path.read_text())
            data["targets"][0]["dsv"]["flags"] = 0
            path.write_text(json.dumps(data))
        with self.assertRaisesRegex(MODULE.ChronologyError,
                                    "depth read-only"):
            self.report(mutate)

    def test_unchanged_draw_fails_closed(self) -> None:
        def mutate(capture: Path) -> None:
            root = capture / "graphics/m31_chronology"
            (root / "draw1_post.bin").write_bytes(
                (root / "draw1_pre.bin").read_bytes())
        with self.assertRaisesRegex(MODULE.ChronologyError,
                                    "did not change any RTV0 bytes"):
            self.report(mutate)

    def test_missing_blob_fails_closed(self) -> None:
        def mutate(capture: Path) -> None:
            (capture / "graphics/m31_chronology/draw2_post.bin").unlink()
        with self.assertRaisesRegex(MODULE.ChronologyError,
                                    "blob is absent"):
            self.report(mutate)


if __name__ == "__main__":
    unittest.main()

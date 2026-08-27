from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "verify_endminf_secondary_dynamics_trajectory_capture.py"
SPEC = importlib.util.spec_from_file_location(
    "verify_endminf_secondary_dynamics_trajectory_capture", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write_capture(root: Path, overflow: int = 0, omit_last_coat: bool = False) -> None:
    directory = root / "secondary-dynamics"
    directory.mkdir(parents=True)
    sample_count = sum(MODULE.OWNER_LENGTHS.values()) * 2 - (1 if omit_last_coat else 0)
    window = {
        "windowId": 1,
        "trajectoryComplete": overflow == 0,
        "endminfTrajectoryFourChunkCandidateCoverage": True,
        "endminfTrajectoryFourOwnerCoverage": False,
        "transformWriteUnreadableCalls": 0,
        "transformSampleOverflow": overflow,
        "transformSampleCount": sample_count,
    }
    (directory / "windows.jsonl").write_text(
        json.dumps(window) + "\n", encoding="utf-8")
    with (directory / "trajectories.jsonl").open("w", encoding="utf-8") as output:
        start = 0
        for owner_index, (owner, length) in enumerate(MODULE.OWNER_LENGTHS.items(), 1):
            for writeback in (1, 2):
                for local in range(length):
                    if omit_last_coat and owner == "Coat" and writeback == 2 and local == length - 1:
                        continue
                    output.write(json.dumps({
                        "windowId": 1,
                        "writebackId": writeback,
                        "timestampNs": 1000 + writeback * 100,
                        "transformIndex": start + local,
                        "teamId": owner_index,
                        "componentId": owner_index * 10,
                        "proxyTransformStart": start,
                        "proxyTransformLength": length,
                        "endminfOwnerCandidate": owner,
                        "position": [1.0, 2.0, 3.0],
                        "rotation": [0.0, 0.0, 0.0, 1.0],
                        "localPosition": [0.1, 0.2, 0.3],
                        "localRotation": [0.0, 0.0, 0.0, 1.0],
                    }) + "\n")
            start += length


class TrajectoryCaptureTests(unittest.TestCase):
    def test_complete_four_owner_window_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root)
            report = MODULE.build_report(root, minimum_writebacks=2)
            self.assertEqual(
                report["status"],
                "validated_unique_four_chunk_candidate_trajectory")
            self.assertEqual(report["writebackCount"], 2)
            self.assertEqual(report["sampleCount"], 252)

    def test_overflow_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root, overflow=1)
            with self.assertRaisesRegex(MODULE.VerificationError, "complete trajectory"):
                MODULE.build_report(root, minimum_writebacks=2)

    def test_incomplete_owner_writeback_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_capture(root, omit_last_coat=True)
            with self.assertRaisesRegex(MODULE.VerificationError, "Coat"):
                MODULE.build_report(root, minimum_writebacks=2)


if __name__ == "__main__":
    unittest.main()

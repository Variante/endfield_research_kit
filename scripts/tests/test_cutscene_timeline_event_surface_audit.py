from __future__ import annotations

import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    ROOT
    / "scripts"
    / "story_recovery"
    / "build_cutscene_timeline_event_surface_audit.py"
)
SPEC = importlib.util.spec_from_file_location("cutscene_timeline_event_audit", MODULE_PATH)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def identity(path_id: int = 7) -> dict:
    return {
        "serializedFile": "CAB-test",
        "source": "VFS/AAAA/test.chk",
        "sourceOffset": 123,
        "pathId": path_id,
    }


def reverse_payload() -> dict:
    return {
        "_schema": "reverse-test-v1",
        "nativeEvidence": {"mappingId": "native-test-v1"},
        "directorHosts": [
            {
                "targetObject": identity(),
                "crossStoryPlaybackAliases": [
                    {
                        "rootStoryKey": "cutscene_root",
                        "playableAssetStoryKey": "cutscene_played",
                        "relation": "cutscene_root_director_playable_asset",
                        "edgeStatus": (
                            "exact_root_playback_alias_no_chronology_or_mission_owner"
                        ),
                    }
                ],
            }
        ],
    }


def object_row(
    path_id: int,
    script: str,
    *,
    name: str = "",
    scalars: list | None = None,
) -> dict:
    return {
        "recordType": "object",
        "object": identity(path_id),
        "type": "MonoBehaviour",
        "name": name,
        "decodeStatus": "decoded",
        "typeTreeSource": "serializedType",
        "script": {"fullName": script},
        "scalars": scalars or [],
        "pptrs": [],
    }


class CutsceneTimelineEventSurfaceAuditTests(unittest.TestCase):
    def write_fixture(self, directory: Path, rows: list[dict]) -> tuple[Path, Path]:
        reverse = directory / "reverse.json"
        reverse.write_text(json.dumps(reverse_payload()), encoding="utf-8")
        index = directory / "objects.jsonl.gz"
        with gzip.open(index, "wt", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")
        return reverse, index

    def test_clean_control_timeline_is_closed_negative(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            reverse, index = self.write_fixture(
                Path(raw),
                [
                    object_row(
                        7,
                        "UnityEngine.Timeline.TimelineAsset",
                        name="cutscene_played",
                    ),
                    object_row(8, "UnityEngine.Timeline.ControlTrack", name="Actor"),
                    object_row(9, "UnityEngine.Timeline.ControlPlayableAsset"),
                ],
            )
            report = AUDIT.build_report(reverse, (index,))
        self.assertEqual(report["summary"]["candidateSurfaceCount"], 0)
        self.assertEqual(
            report["summary"]["finding"],
            "no_authored_event_or_mission_surface_in_exact_played_timelines",
        )
        self.assertEqual(report["aliases"][0]["playedTimelineSurface"]["objectCount"], 3)

    def test_event_track_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            reverse, index = self.write_fixture(
                Path(raw),
                [
                    object_row(
                        7,
                        "UnityEngine.Timeline.TimelineAsset",
                        name="cutscene_played",
                    ),
                    object_row(8, "Beyond.Gameplay.View.RaiseLevelEventTrack"),
                ],
            )
            report = AUDIT.build_report(reverse, (index,))
        self.assertEqual(report["summary"]["candidateSurfaceCount"], 1)
        surface = report["aliases"][0]["playedTimelineSurface"]
        self.assertEqual(
            surface["finding"],
            "candidate_surface_requires_manual_native_semantics_review",
        )
        self.assertEqual(surface["surfaceHits"][0]["object"]["pathId"], 8)

    def test_missing_exact_target_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            reverse, index = self.write_fixture(
                Path(raw),
                [object_row(8, "UnityEngine.Timeline.ControlTrack")],
            )
            with self.assertRaises(AUDIT.AuditError):
                AUDIT.build_report(reverse, (index,))


if __name__ == "__main__":
    unittest.main()

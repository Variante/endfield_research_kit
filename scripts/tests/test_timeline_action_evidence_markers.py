from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.story_builder import timeline_action_evidence as evidence


def object_row(script: str, path_id: int, *, name: str, scalars=None, pptrs=None):
    return {
        "recordType": "object",
        "object": {"serializedFile": "CAB-test", "pathId": path_id},
        "name": name,
        "script": {"fullName": script},
        "scalars": scalars or [],
        "pptrs": pptrs or [],
    }


def target(path: str, path_id: int):
    return {
        "path": path,
        "pathId": path_id,
        "expected": {"serializedFile": "CAB-test"},
        "target": {"serializedFile": "CAB-test", "pathId": path_id},
    }


class TimelineActionEvidenceMarkerTests(unittest.TestCase):
    def test_marker_track_timeline_and_story_route_join(self) -> None:
        rows = [
            object_row(
                evidence.LEVEL_EVENT_MARKER_SCRIPT,
                10,
                name="Raise Level Event Marker",
                scalars=[["$.eventName", "s", "TLCall_PlayRadio"]],
            ),
            object_row(
                evidence.LEVEL_EVENT_MARKER_TRACK_SCRIPT,
                20,
                name="Markers",
                pptrs=[
                    target("$.m_Parent", 30),
                    target("$.m_Markers.m_Objects[0]", 10),
                ],
            ),
            object_row(
                evidence.TIMELINE_ASSET_SCRIPT,
                30,
                name="cutscene_test_Actor",
            ),
        ]
        markers, tracks, timelines, count = (
            evidence.collect_level_event_object_roles(
                [json.dumps(row) for row in rows]
            )
        )
        joined = evidence.join_level_event_markers(
            markers, tracks, timelines, "StreamingAssets"
        )
        self.assertEqual(count, 3)
        self.assertEqual(len(joined), 1)
        self.assertEqual(joined[0]["eventName"], "TLCall_PlayRadio")
        self.assertEqual(joined[0]["timeline"]["name"], "cutscene_test_Actor")

        routes = evidence.collect_level_event_story_routes({
            "storyCoverage": {
                "storyTriggerManifest": {
                    "radio_test_1": {
                        "routes": [{
                            "nativePaths": [{
                                "selector": {
                                    "eventKey": "TLCall_PlayRadio",
                                    "listenerHeaderLocalId": 7,
                                },
                                "levelId": "map_test",
                                "scriptId": "1001",
                                "sourceFile": "LevelScriptData/map_test/1001.json",
                                "steps": [{
                                    "actionName": "PlayRadio",
                                    "localId": 8,
                                }],
                            }],
                        }],
                    },
                },
            },
        })
        self.assertEqual(routes["TLCall_PlayRadio"][0]["storyKey"], "radio_test_1")
        self.assertEqual(routes["TLCall_PlayRadio"][0]["listenerHeaderLocalId"], 7)

    def test_unowned_marker_remains_explicit(self) -> None:
        marker = object_row(
            evidence.LEVEL_EVENT_MARKER_SCRIPT,
            11,
            name="Raise Level Event Marker",
            scalars=[["$.eventName", "s", "TLCall_Unowned"]],
        )
        markers, tracks, timelines, _ = evidence.collect_level_event_object_roles(
            [json.dumps(marker)]
        )
        joined = evidence.join_level_event_markers(
            markers, tracks, timelines, "Persistent"
        )
        self.assertEqual(joined[0]["eventName"], "TLCall_Unowned")
        self.assertIsNone(joined[0]["markerTrack"])
        self.assertIsNone(joined[0]["timeline"])

    def test_marker_payload_adds_exact_timeline_time(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "StreamingAssets" / "json_by_type" / "MonoBehaviour"
            folder.mkdir(parents=True)
            path_id = -5
            payload = (
                folder
                / f"Raise Level Event Marker_p{path_id & ((1 << 64) - 1):016X}.json"
            )
            payload.write_text(
                json.dumps({
                    "m_Time": 7.75,
                    "_Retroactive": 1,
                    "_EmitOnce": 1,
                    "paramList": [{"key": "value"}],
                }),
                encoding="utf-8",
            )
            row = {
                "source": "StreamingAssets",
                "marker": {
                    "name": "Raise Level Event Marker",
                    "pathId": path_id,
                },
                "parameters": [],
            }
            evidence.enrich_level_event_marker_payload(row, root)
            self.assertEqual(row["timelineTimeSeconds"], 7.75)
            self.assertEqual(row["retroactive"], 1)
            self.assertEqual(row["emitOnce"], 1)
            self.assertEqual(row["parameters"], [{"key": "value"}])


if __name__ == "__main__":
    unittest.main()

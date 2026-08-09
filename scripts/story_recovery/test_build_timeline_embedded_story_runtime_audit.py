from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from scripts.story_recovery import build_timeline_embedded_story_runtime_audit as audit


def type_row(name: str, fields: list[str]) -> dict:
    return {
        "fullName": name,
        "fields": [{"name": field} for field in fields],
        "methods": [{"name": "CreatePlayable"}, {"name": "_GetText"}],
    }


def body_row(type_name: str, method: str, targets: list[tuple[str, str]]) -> dict:
    return {
        "type": type_name,
        "method": method,
        "methodIndex": 10 if method == "CreatePlayable" else 11,
        "mappingStatus": "mapped",
        "methodPointerVa": "0x1000" if method == "CreatePlayable" else "0x1100",
        "directCalls": [{
            "resolved": [
                {"type": target_type, "method": target_method}
                for target_type, target_method in targets
            ]
        }],
    }


class TimelineEmbeddedStoryRuntimeAuditTests(unittest.TestCase):
    def test_original_path_ids_are_published_as_exact_decimal_strings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "record.json"
            path.write_text(json.dumps({
                "$animestudio": {
                    "pathId": 8802604764156822905,
                    "sourceFile": "CAB-general",
                    "rawDataSha256": "a" * 64,
                }
            }), encoding="utf-8")
            record = audit.original_file_record(str(path), "playable")
        self.assertEqual("8802604764156822905", record["pathId"])

        row = {
            "assetPath": "asset.json", "trackPath": "track.json", "rootPath": "root.json",
            "assetPathId": 8802604764156822905,
            "trackPathId": -3795682753767897735,
            "rootPathId": -110317566135728775,
        }
        with patch.object(audit, "original_file_record", return_value={}):
            enriched = audit.enrich_rows([row])[0]
        self.assertEqual("8802604764156822905", enriched["assetPathId"])
        self.assertEqual("-3795682753767897735", enriched["trackPathId"])
        self.assertEqual("-110317566135728775", enriched["rootPathId"])

    def test_runtime_contract_is_discovered_from_common_shape(self) -> None:
        type_name = "Beyond.Gameplay.Core.AnyTextPlayableAsset"
        catalog = {"matchedTypes": [type_row(type_name, ["_textId_1", "_textId_2"])]}
        body_map = {"bodyTargets": [
            body_row(type_name, "CreatePlayable", [
                ("Beyond.Gameplay.Core.AnyTextPlayableBehaviour", "InitAnyText"),
            ]),
            body_row(type_name, "_GetText", [
                ("Beyond.I18n.I18nUtils", "TryGetText"),
                ("Beyond.Gameplay.GameplayUIUtils", "ResolveOriginalText"),
            ]),
        ]}

        result = audit.analyze_runtime_contract(catalog, body_map)

        self.assertEqual("validated", result["validation"]["status"])
        self.assertEqual("AnyTextPlayableAsset", result["families"][0]["serializedAssetType"])
        self.assertEqual(["_textId_1", "_textId_2"], result["families"][0]["textIdFields"])

    def test_runtime_contract_failure_names_gate_and_actual_calls(self) -> None:
        type_name = "Beyond.Gameplay.Core.AnyTextPlayableAsset"
        catalog = {"matchedTypes": [type_row(type_name, ["_textId"])]}
        body_map = {"bodyTargets": [
            body_row(type_name, "CreatePlayable", [
                ("Beyond.Gameplay.Core.AnyTextPlayableBehaviour", "InitAnyText"),
            ]),
            body_row(type_name, "_GetText", [
                ("Beyond.I18n.I18nUtils", "TryGetText"),
            ]),
        ]}

        result = audit.analyze_runtime_contract(catalog, body_map)

        self.assertEqual("failed", result["validation"]["status"])
        failure = result["validation"]["failures"][0]
        self.assertEqual("timeline_embedded_story_runtime", failure["validator"])
        self.assertEqual("localized_text_resolution", failure["gate"])
        self.assertEqual(type_name, failure["sourceFile"])
        self.assertIn("Beyond.I18n.I18nUtils::TryGetText", failure["actual"])

    def test_local_order_uses_time_not_clip_or_filename_order(self) -> None:
        common = {
            "sourceFile": "CAB-general",
            "timeline": "dlgtl_general_sub_1",
            "trackPathId": 10,
            "clipOptionIndex": 2,
        }
        rows = [
            {**common, "key": "black_second", "textId": "black_second_001",
             "clipIndex": 0, "clipStart": 8.0, "clipDuration": 1.0},
            {**common, "key": "black_first", "textId": "black_first_001",
             "clipIndex": 9, "clipStart": 1.0, "clipDuration": 2.0},
        ]

        edges = audit.local_order_edges(rows)

        self.assertEqual(1, len(edges))
        self.assertEqual(("black_first", "black_second"), (edges[0]["from"], edges[0]["to"]))
        self.assertFalse(edges[0]["missionOrder"])
        self.assertEqual(2, edges[0]["optionIndex"])

    def test_overlapping_clips_do_not_create_order(self) -> None:
        rows = [
            {"sourceFile": "CAB", "timeline": "tl", "trackPathId": 1,
             "clipOptionIndex": 0, "key": "a", "textId": "a_1",
             "clipIndex": 0, "clipStart": 1.0, "clipDuration": 5.0},
            {"sourceFile": "CAB", "timeline": "tl", "trackPathId": 1,
             "clipOptionIndex": 0, "key": "b", "textId": "b_1",
             "clipIndex": 1, "clipStart": 3.0, "clipDuration": 1.0},
        ]
        self.assertEqual([], audit.local_order_edges(rows))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.story_builder.timeline_recovery import (
    path_id_suffix,
    recover_black_timeline_attachments,
    recover_timeline_text_attachments,
)


class TimelineBlackAttachmentTests(unittest.TestCase):
    def test_serialized_asset_track_parent_chain_resolves_exact_dialog_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            extract_dir = root / "timeline_extract"
            mono_dir = extract_dir / "CHK" / "MonoBehaviour"
            mono_dir.mkdir(parents=True)
            source_file = "CAB-test"

            def write_record(name: str, path_id: int, payload: dict) -> Path:
                path = mono_dir / f"{name}_p{path_id_suffix(path_id)}.json"
                path.write_text(
                    json.dumps(
                        {
                            "$animestudio": {
                                "pathId": path_id,
                                "sourceFile": source_file,
                                "name": name,
                            },
                            **payload,
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                return path

            asset_id = -101
            track_id = 202
            group_id = 303
            root_id = 404
            asset_path = write_record(
                "DialogCenterTextPlayableAsset",
                asset_id,
                {"m_Name": "DialogCenterTextPlayableAsset", "_textId": "black_e5m1_1_001"},
            )
            track_path = write_record(
                "Trunk",
                track_id,
                {
                    "m_Name": "Trunk",
                    "m_Parent": {"m_FileID": 0, "m_PathID": group_id},
                    "m_Clips": [
                        {
                            "m_Asset": {"m_FileID": 0, "m_PathID": asset_id},
                            "m_Start": 2.5,
                            "m_Duration": 1.25,
                        }
                    ],
                },
            )
            group_path = write_record(
                "Common",
                group_id,
                {
                    "m_Name": "Common",
                    "m_Parent": {"m_FileID": 0, "m_PathID": root_id},
                },
            )
            root_path = write_record(
                "dlgtl_e5m1_5_sub_1_Actor",
                root_id,
                {
                    "m_Name": "dlgtl_e5m1_5_sub_1_Actor",
                    "m_Tracks": [{"m_FileID": 0, "m_PathID": group_id}],
                },
            )
            line_orders_path = root / "timeline_line_orders.json"
            line_orders_path.write_text(
                json.dumps(
                    {
                        "_meta": {},
                        "dlg_e5m1_5": {
                            "timeline": "dlgtl_e5m1_5_sub_1",
                            "dialogKey": "dlg_e5m1_5",
                            "source": mono_dir.as_posix(),
                            "sourceRoots": [root_path.as_posix()],
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            rows = recover_black_timeline_attachments(
                str(line_orders_path),
                str(extract_dir),
                str(root / "missing_dialog_registry.json"),
            )

            self.assertEqual(1, len(rows))
            self.assertEqual("black_e5m1_1", rows[0]["key"])
            self.assertEqual("dlg_e5m1_5", rows[0]["dialogKey"])
            self.assertEqual("source_timeline_actor_root", rows[0]["dialogJoin"])
            self.assertEqual(asset_path.as_posix(), rows[0]["assetPath"])
            self.assertEqual(track_path.as_posix(), rows[0]["trackPath"])

            general_rows = recover_timeline_text_attachments(
                str(line_orders_path),
                str(extract_dir),
                str(root / "missing_dialog_registry.json"),
                line_id_to_story_key={"black_e5m1_1_001": "scene_general"},
                playable_asset_type_names=("DialogCenterTextPlayableAsset",),
            )
            self.assertEqual(1, len(general_rows))
            self.assertEqual("scene_general", general_rows[0]["key"])
            self.assertEqual(2.5, general_rows[0]["clipStart"])

            registry_path = root / "dialog_id_table_index.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "dlg_e5m1_5": {
                            "registered": True,
                            "usedDialogTimelineIds": ["dlgtl_e5m1_5_sub_1"],
                        }
                    }
                ),
                encoding="utf-8",
            )
            registry_rows = recover_black_timeline_attachments(
                str(line_orders_path),
                str(extract_dir),
                str(registry_path),
            )
            self.assertEqual("dlg_e5m1_5", registry_rows[0]["dialogKey"])
            self.assertEqual(
                "dialog_id_table_used_timeline",
                registry_rows[0]["dialogJoin"],
            )
            self.assertEqual(
                "usedDialogTimelineIds",
                registry_rows[0]["dialogRegistryField"],
            )

            full_mono_dir = (
                extract_dir.parent
                / "StreamingAssets"
                / "json_by_type"
                / "MonoBehaviour"
            )
            full_mono_dir.parent.mkdir(parents=True)
            mono_dir.rename(full_mono_dir)
            fallback_rows = recover_black_timeline_attachments(
                str(line_orders_path),
                str(extract_dir),
                str(registry_path),
            )
            self.assertEqual(1, len(fallback_rows))
            self.assertEqual("black_e5m1_1", fallback_rows[0]["key"])
            self.assertEqual("dlg_e5m1_5", fallback_rows[0]["dialogKey"])
            self.assertEqual(
                "full_monobehaviour_exact_root_fallback",
                fallback_rows[0]["monoBehaviourSourceMode"],
            )
            self.assertEqual(full_mono_dir.as_posix(), fallback_rows[0]["monoBehaviourSource"])

            validation_report = root / "timeline_parent_validation.json"
            moved_group_path = full_mono_dir / group_path.name
            moved_group_path.unlink()
            with self.assertRaisesRegex(
                RuntimeError,
                r"timeline_parent_chain_export_coverage failed: 1 .*"
                r"sourceFile='CAB-test' pathId=303",
            ):
                recover_timeline_text_attachments(
                    str(line_orders_path),
                    str(extract_dir),
                    str(registry_path),
                    line_id_to_story_key={"black_e5m1_1_001": "scene_general"},
                    playable_asset_type_names=("DialogCenterTextPlayableAsset",),
                    validation_report_path_str=str(validation_report),
                )
            validation = json.loads(validation_report.read_text(encoding="utf-8"))
            self.assertEqual("validation_failed", validation["status"])
            self.assertEqual(1, validation["actualMissingCount"])
            self.assertEqual(
                {"sourceFile": "CAB-test", "pathId": 303},
                validation["failures"][0],
            )


if __name__ == "__main__":
    unittest.main()

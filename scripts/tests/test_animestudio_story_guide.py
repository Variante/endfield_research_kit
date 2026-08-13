from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from story_builder import animestudio_story_guide as audit  # noqa: E402
from common import guide_runtime_non_mission_content_keys  # noqa: E402


def object_row(*, owner: bool = False) -> dict:
    prefix = "$.references.RefIds[3]"
    scalars = [
        ["$.m_Name", "s", "guide_blackbox_speedlimit_1_step0"],
        [f"{prefix}.type.class", "s", "FacSetInteractLockedState"],
        [f"{prefix}.type.ns", "s", "Beyond.Gameplay.Actions"],
        [f"{prefix}.type.asm", "s", "Gameplay.Beyond"],
        [
            f"{prefix}.data.layout",
            "s",
            "Beyond.Gameplay.Actions.FacSetInteractLockedState",
        ],
        [f"{prefix}.data.actionBase.actionId.hex", "s", "0x00000003"],
        [f"{prefix}.data.actionBase.key", "s", "action_key"],
        [f"{prefix}.data.actionBase.nextId.hex", "s", "0xffffffff"],
        [f"{prefix}.data.instKey.value", "s", "conditioner_1"],
        [
            f"{prefix}.data.radioId.value",
            "s",
            "radio_blackbox_common_1",
        ],
        [
            "$.references.RefIds[1].data.levelId.value",
            "s",
            "blackbox_speedlimit_1",
        ],
    ]
    if owner:
        scalars.append([
            "$.references.RefIds[8].data.missionId.value",
            "s",
            "e1m1",
        ])
    return {
        "recordType": "object",
        "object": {
            "serializedFile": "CAB-test",
            "source": "VFS/test.chk",
            "sourceOffset": 123,
            "pathId": 456,
        },
        "name": "guide_blackbox_speedlimit_1_step0",
        "script": {
            "fullName": "Beyond.Gameplay.Actions.GuideRuntimeAsset",
        },
        "decodeStatus": "decoded",
        "scalarsTruncated": False,
        "scalars": scalars,
    }


class GuideConsumerAuditTests(unittest.TestCase):
    def test_boolean_scalar_is_accepted_by_object_index_contract(self) -> None:
        row = object_row()
        row["scalars"].append(["$.enabled", "b", True])

        rows = audit.audit_object_row(row, "StreamingAssets")

        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["accepted"])

    def test_malformed_scalar_reports_object_and_expected_type_contract(self) -> None:
        row = object_row()
        row["scalars"].append(["$.enabled", "b", 1])

        with self.assertRaisesRegex(
            audit.AuditError,
            r"source='VFS/test\.chk'.*pathId=456 index=11; expected .*b:boolean",
        ):
            audit.audit_object_row(row, "StreamingAssets")

    def test_exact_typed_factory_guide_action_is_accepted(self) -> None:
        rows = audit.audit_object_row(object_row(), "StreamingAssets")
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["accepted"])
        self.assertEqual(
            rows[0]["guideLevelIds"],
            ["blackbox_speedlimit_1"],
        )
        self.assertEqual(rows[0]["factoryInstanceKey"], "conditioner_1")

    def test_same_object_mission_owner_is_rejected(self) -> None:
        rows = audit.audit_object_row(
            object_row(owner=True),
            "StreamingAssets",
        )
        self.assertFalse(rows[0]["accepted"])
        self.assertIn(
            "same_object_has_owner_or_runtime_identifier",
            rows[0]["rejectionReasons"],
        )

    def test_fresh_report_loader_rejects_source_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output_root = root / "export_full"
            summary_dir = (
                output_root
                / "recovered"
                / "AnimeStudio-cli"
                / "StreamingAssets"
                / "object_index"
            )
            summary_dir.mkdir(parents=True)
            fingerprint = {
                "files": 2,
                "bytes": 3,
                "fingerprint": "b" * 64,
            }
            stage_sha = "a" * 64
            (summary_dir / "summary.json").write_text(
                json.dumps({
                    "complete": True,
                    "stageSignature": {
                        "sha256": stage_sha,
                        "payload": {
                            "source_fingerprint": fingerprint,
                        },
                    },
                }),
                encoding="utf-8",
            )
            export_summary = root / "export_summary.json"
            export_summary.write_text(
                json.dumps({
                    "source_sizes": {
                        "StreamingAssets": fingerprint,
                    },
                }),
                encoding="utf-8",
            )
            report = root / "guide_report.json"
            report.write_text(
                json.dumps({
                    "_schema": audit.SCHEMA,
                    "nativeEvidence": {"validated": True},
                    "sources": [{
                        "source": "StreamingAssets",
                        "stageSignatureSha256": stage_sha,
                        "sourceFingerprint": fingerprint,
                    }],
                    "classifications": [{
                        "storyKey": "radio_blackbox_common_1",
                        "recoveryStatus":
                            "closed_exact_guide_runtime_non_mission_content",
                        "evidenceKind": "guide_runtime_asset",
                        "contentClass":
                            "factory_interaction_lock_guide_radio",
                        "assetType": audit.GUIDE_RUNTIME_ASSET,
                        "consumerClass":
                            "Beyond.Gameplay.Actions."
                            "FacSetInteractLockedState",
                        "assetCount": 10,
                        "actionCount": 13,
                    }],
                }),
                encoding="utf-8",
            )

            loaded = guide_runtime_non_mission_content_keys(
                report,
                export_summary_path=export_summary,
                output_root=output_root,
            )
            self.assertIn("radio_blackbox_common_1", loaded)

            changed = json.loads(export_summary.read_text(encoding="utf-8"))
            changed["source_sizes"]["StreamingAssets"]["bytes"] = 4
            export_summary.write_text(json.dumps(changed), encoding="utf-8")
            self.assertEqual(
                guide_runtime_non_mission_content_keys(
                    report,
                    export_summary_path=export_summary,
                    output_root=output_root,
                ),
                {},
            )


if __name__ == "__main__":
    unittest.main()

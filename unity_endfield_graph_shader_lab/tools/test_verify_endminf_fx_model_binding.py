import json
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parent
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

import verify_endminf_fx_model_binding as verifier


class EndminfFxModelBindingTests(unittest.TestCase):
    def test_unity_crc32_matches_known_avatar_tos_entry(self):
        path = (
            "Root/Bip001/Bip001_Pelvis/Bip001_Spine/Bip001_Spine1/"
            "Bip001_Spine2/Bip001_Neck/Bip001_Head/lipLdn4Joint"
        )
        self.assertEqual(verifier.unity_crc32(path), 2464567722)

    def test_clip_hashes_require_exact_three_transform_bindings(self):
        value = {
            "m_ClipBindingConstant": {
                "genericBindings": [
                    {"path": path_hash, "attribute": attribute, "typeID": "Transform"}
                    for path_hash in verifier.EXPECTED_BINDING_HASHES
                    for attribute in (1, 2, 3)
                ]
            }
        }
        grouped = verifier.clip_binding_hashes(value)
        self.assertEqual(tuple(sorted(grouped)), verifier.EXPECTED_BINDING_HASHES)
        self.assertEqual(sum(len(rows) for rows in grouped.values()), 9)

    def test_clip_hashes_reject_name_only_or_extra_path(self):
        value = {
            "m_ClipBindingConstant": {
                "genericBindings": [
                    {"path": path_hash, "attribute": 1, "typeID": "Transform"}
                    for path_hash in (*verifier.EXPECTED_BINDING_HASHES, 1234)
                    for _ in range(3)
                ]
            }
        }
        with self.assertRaisesRegex(verifier.VerificationError, "expected exactly"):
            verifier.clip_binding_hashes(value)

    def test_container_evidence_keeps_clip_only_identity(self):
        container = "assets/beyond/arts/effects/commonassets/arts/sk_model/sk_fx_endminf_01_ui.fbx"
        source = r"D:\game\FC.chk"
        identity = {
            "name": "A_actor_endminf_ui_overview_02",
            "type": "AnimationClip",
            "pathId": -7,
            "source": source,
            "sourceOffset": 99,
            "container": container,
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "map.json"
            path.write_text(
                json.dumps(
                    {
                        "AssetEntries": [
                            {
                                "Name": identity["name"],
                                "Container": container,
                                "Source": source,
                                "PathID": -7,
                                "Type": "AnimationClip",
                                "Offset": 99,
                            },
                            {
                                "Name": "unrelated",
                                "Container": "assets/other.fbx",
                                "Source": source,
                                "PathID": -8,
                                "Type": "Mesh",
                                "Offset": 100,
                            },
                        ]
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            evidence = verifier._container_evidence(path, identity)
        self.assertEqual(evidence["containerRowCount"], 1)
        self.assertEqual(evidence["containerModelRows"], 0)
        self.assertEqual(evidence["sourceOffsetModelRows"], 0)
        self.assertEqual(evidence["result"], "container_has_animation_clip_only_no_model_closure")

    def test_avatar_tos_requires_crc32_key_match(self):
        path_hash = verifier.EXPECTED_BINDING_HASHES[0]
        authored = "Root/FX/target"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "avatar.json"
            path.write_text(json.dumps({"m_TOS": {str(path_hash): authored}}), encoding="utf-8")
            result = verifier._avatar_evidence(path, [path_hash])
        self.assertEqual(result["targetRows"][0]["keyPresent"], False)
        self.assertEqual(result["invalidKeyCount"], 1)
        self.assertEqual(result["result"], "all_target_hashes_absent_from_exact_avatar_tos")


if __name__ == "__main__":
    unittest.main()

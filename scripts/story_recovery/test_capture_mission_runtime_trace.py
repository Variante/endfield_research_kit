import hashlib
import json
import tempfile
import unittest
from pathlib import Path


from scripts.story_recovery import capture_mission_runtime_trace as capture


class MissionRuntimeCaptureTests(unittest.TestCase):
    def test_hash_locked_file_verification(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        content = b"known game bytes"
        (root / "binary.dat").write_bytes(content)
        manifest = {
            "files": {
                "binary": {
                    "relativePath": "binary.dat",
                    "bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            }
        }

        verified = capture.verify_game_files(root, manifest)

        self.assertEqual(verified["binary"], (root / "binary.dat").resolve())

    def test_changed_file_is_refused(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "binary.dat").write_bytes(b"changed")
        manifest = {
            "files": {
                "binary": {
                    "relativePath": "binary.dat",
                    "bytes": 7,
                    "sha256": hashlib.sha256(b"original").hexdigest(),
                }
            }
        }

        with self.assertRaisesRegex(capture.CaptureConfigurationError, "SHA-256 changed"):
            capture.verify_game_files(root, manifest)

    def test_agent_placeholder_is_replaced_once(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "agent.js"
        path.write_text(
            f"const CONFIG = {capture.AGENT_PLACEHOLDER};\n",
            encoding="utf-8",
        )
        manifest = {
            "gameBuild": "fixture",
            "moduleName": "GameAssembly.dll",
            "hooks": {"test": {"rva": "0x1"}},
        }

        rendered = capture.render_agent_source(path, manifest)

        self.assertNotIn(capture.AGENT_PLACEHOLDER, rendered)
        config_text = rendered.removeprefix("const CONFIG = ").removesuffix(";\n")
        self.assertEqual(json.loads(config_text)["gameBuild"], "fixture")

    def test_current_manifest_uses_final_sns_ui_field_probe(self):
        manifest = capture.load_manifest(capture.DEFAULT_MANIFEST)

        async_probe = manifest["hooks"]["asyncSnsPlayback"]
        self.assertEqual(async_probe["prefixes"], ["sns_"])
        self.assertEqual(async_probe["maxPendingContexts"], 256)
        self.assertEqual(
            async_probe["request"],
            {
                "symbol": "Beyond.Gameplay.Actions.GameAction.StartForceSNS",
                "token": "0x06008049",
                "methodIndex": 32840,
                "rva": "0x75ed938",
            },
        )
        self.assertEqual(
            async_probe["queueBoundary"],
            {
                "symbol": (
                    "Beyond.Gameplay.Actions.GameAction.AddCinematicItem2Queue"
                ),
                "itemChatIdFieldOffset": "0x18",
                "itemStoryKeyFieldOffset": "0x48",
                "itemShowToastFieldOffset": "0x50",
                "token": "0x0600804b",
                "methodIndex": 32842,
                "rva": "0x75dcf58",
            },
        )
        self.assertEqual(
            async_probe["consumer"],
            {
                "symbol": (
                    "Beyond.Gameplay.Core.GameMech."
                    "MainCharForceSNSBrain.StartForceSNS"
                ),
                "handleItemFieldOffset": "0x18",
                "token": "0x060144a7",
                "methodIndex": 83110,
                "rva": "0x70ed65c",
            },
        )
        self.assertEqual(
            async_probe["fieldPlayback"],
            {
                "actionType": "MainCharForceSNSBrain._StartSNSUI",
                "storyKeyFieldOffset": "0x128",
                "contextFieldOffsets": {"chatId": "0x130"},
            },
        )

        probes = manifest["hooks"]["fieldPlayback"]
        self.assertEqual(len(probes), 1)
        probe = probes[0]
        self.assertEqual(
            probe["symbol"],
            "Beyond.Gameplay.Core.GameMech.MainCharForceSNSBrain._StartSNSUI",
        )
        self.assertEqual(probe["playbackType"], "sns")
        self.assertEqual(probe["prefixes"], ["sns_"])
        self.assertEqual(probe["storyKeyFieldOffset"], "0x128")
        self.assertEqual(probe["contextFieldOffsets"]["chatId"], "0x130")
        self.assertEqual(probe["token"], "0x06014493")
        self.assertEqual(probe["methodIndex"], 83090)
        self.assertEqual(probe["rva"], "0x70ef8b4")

    def test_current_manifest_uses_action_backed_black_mask_probe(self):
        manifest = capture.load_manifest(capture.DEFAULT_MANIFEST)

        black_actions = [
            probe
            for probe in manifest["hooks"]["playback"]
            if probe["playbackType"] == "black"
        ]
        self.assertEqual(
            [probe["actionType"] for probe in black_actions],
            [
                "ComplexNarrativeBlackScreenAction",
                "NarrativeBlackScreenAction",
                "StartNarrativeBlackScreenAndTeleport",
            ],
        )
        self.assertEqual(
            [probe["token"] for probe in black_actions],
            ["0x06008ca9", "0x06008ce9", "0x06008d45"],
        )
        self.assertEqual(
            [probe["methodIndex"] for probe in black_actions],
            [36008, 36072, 36164],
        )
        self.assertEqual(
            [probe["rva"] for probe in black_actions],
            ["0x7660bf0", "0x7668c84", "0x766e494"],
        )
        self.assertTrue(
            all(probe["keySource"] == "maskTextList" for probe in black_actions)
        )

        boundary = manifest["hooks"]["maskPlaybackBoundary"]
        self.assertEqual(
            boundary["symbol"],
            "Beyond.Gameplay.Actions.GameAction.ShowNarrativeBlackScreen",
        )
        self.assertEqual(boundary["token"], "0x0600802b")
        self.assertEqual(boundary["methodIndex"], 32810)
        self.assertEqual(boundary["rva"], "0x75ec4b0")
        self.assertEqual(boundary["dataTextListFieldOffset"], "0x70")
        self.assertEqual(boundary["listItemsFieldOffset"], "0x10")
        self.assertEqual(boundary["listSizeFieldOffset"], "0x18")
        self.assertEqual(boundary["arrayDataOffset"], "0x20")
        self.assertEqual(boundary["lineKeyFieldOffset"], "0x10")
        self.assertEqual(boundary["lineIdPattern"], r"^black_.+_\d{3,}$")
        self.assertEqual(boundary["lineSuffixPattern"], r"_\d{3,}$")

    def test_current_manifest_defers_queued_dialogs_to_accepted_boundary(self):
        manifest = capture.load_manifest(capture.DEFAULT_MANIFEST)

        async_probe = manifest["hooks"]["asyncDialogPlayback"]
        self.assertEqual(async_probe["deferToAcceptedPlayback"], "dialog")
        self.assertEqual(async_probe["prefixes"], ["dlg_", "misc_dlg_"])
        self.assertEqual(async_probe["maxPendingContexts"], 256)
        self.assertEqual(
            async_probe["request"],
            {
                "symbol": "Beyond.Gameplay.Actions.GameAction.StartDialog",
                "token": "0x06008038",
                "methodIndex": 32823,
                "rva": "0x75ed524",
            },
        )
        self.assertEqual(
            async_probe["queueBoundary"],
            {
                "symbol": (
                    "Beyond.Gameplay.Actions.GameAction.AddCinematicItem2Queue"
                ),
                "itemStoryKeyFieldOffset": "0x18",
                "token": "0x0600804b",
                "methodIndex": 32842,
                "rva": "0x75dcf58",
            },
        )
        self.assertEqual(
            async_probe["consumer"],
            {
                "symbol": "Beyond.Gameplay.Core.DialogManager.PlayDialogByHandle",
                "handleItemFieldOffset": "0x18",
                "token": "0x0600f777",
                "methodIndex": 63350,
                "rva": "0x6e15e40",
            },
        )
        self.assertEqual(
            async_probe["acceptedPlayback"],
            {
                "symbol": (
                    "Beyond.Gameplay.Core.DialogManager._PlayDialogInternal"
                ),
                "token": "0x0600f84e",
                "methodIndex": 63565,
                "rva": "0x6e28040",
            },
        )

        probes = {
            probe["actionType"]: probe
            for probe in manifest["hooks"]["playback"]
        }
        for action_type in (
            "PlayDialogAndHideSceneObjectAction",
            "StartDialogAction",
            "StartDialogAndTeleportAction",
        ):
            with self.subTest(action_type=action_type):
                self.assertEqual(
                    probes[action_type]["deferToAcceptedPlayback"],
                    "dialog",
                )
        self.assertNotIn(
            "deferToAcceptedPlayback",
            probes["StartContinuousDialog"],
        )

    def test_current_manifest_uses_binary_proved_mission_state_snapshot_layout(self):
        manifest = capture.load_manifest(capture.DEFAULT_MANIFEST)

        snapshot = manifest["hooks"]["mission"]["snapshot"]
        self.assertEqual(snapshot["tick"]["token"], "0x0600522b")
        self.assertEqual(snapshot["tick"]["methodIndex"], 21034)
        self.assertEqual(snapshot["tick"]["rva"], "0x34e3890")
        self.assertEqual(
            snapshot["systemFieldOffsets"],
            {
                "idMap": "0x70",
                "missions": "0xd8",
                "currentQuests": "0xe0",
            },
        )
        self.assertEqual(
            snapshot["dictionaryLayout"],
            {
                "entries": "0x18",
                "usedCount": "0x20",
                "version": "0x2c",
                "arrayLength": "0x18",
                "arrayData": "0x20",
                "entryStride": "0x18",
                "entryHashCode": "0x0",
                "entryKey": "0x8",
                "entryValue": "0x10",
            },
        )
        self.assertEqual(snapshot["missionData"]["idFieldOffset"], "0x10")
        self.assertEqual(snapshot["missionData"]["stateFieldOffset"], "0x18")
        self.assertEqual(snapshot["missionData"]["processingState"], 2)
        self.assertEqual(snapshot["missionData"]["states"]["1"], "Available")
        self.assertEqual(snapshot["questData"]["idFieldOffset"], "0x10")
        self.assertEqual(snapshot["questData"]["stateFieldOffset"], "0x18")
        self.assertEqual(snapshot["questData"]["processingState"], 2)
        self.assertNotIn("1", snapshot["questData"]["states"])

    def test_current_manifest_covers_proved_playback_action_variants(self):
        manifest = capture.load_manifest(capture.DEFAULT_MANIFEST)
        probes = {
            probe["actionType"]: probe for probe in manifest["hooks"]["playback"]
        }

        expected = {
            "PlayCutsceneIgnoreCinematicQueue": (
                "cutscene",
                "0x06008e23",
                36386,
                "0x7676618",
            ),
            "PlayLevelSequenceAction": (
                "cutscene",
                "0x06008e2e",
                36397,
                "0x767713c",
            ),
            "PlayLevelSequenceAndControlSceneObjectsAction": (
                "cutscene",
                "0x06008e3d",
                36412,
                "0x7677b24",
            ),
            "PlayLevelSequenceAndHideSceneObjectsAction": (
                "cutscene",
                "0x06008e4c",
                36427,
                "0x76781bc",
            ),
            "StartCutsceneAndControlSceneObjectAction": (
                "cutscene",
                "0x06008e8b",
                36490,
                "0x767cff4",
            ),
            "StartCutsceneAndHideSceneObjectAction": (
                "cutscene",
                "0x06008ea7",
                36518,
                "0x767dd14",
            ),
            "Play3DRadio": (
                "radio",
                "0x06008e0a",
                36361,
                "0x7675670",
            ),
            "Play3DRadioAndWait": (
                "radio",
                "0x06008e0f",
                36366,
                "0x767514c",
            ),
            "FlushAndPlayRadio": (
                "radio",
                "0x06008dfb",
                36346,
                "0x7672390",
            ),
            "PlayDialogAndHideSceneObjectAction": (
                "dialog",
                "0x06008cf2",
                36081,
                "0x7669a84",
            ),
            "StartContinuousDialog": (
                "dialog",
                "0x06008d39",
                36152,
                "0x766dbb4",
            ),
            "PlayFmvAction": (
                "cutscene",
                "0x06008e2b",
                36394,
                "0x7676be4",
            ),
            "StartCutsceneAndTeleportAction": (
                "cutscene",
                "0x06008ec7",
                36550,
                "0x767e1ec",
            ),
            "StartDialogAndTeleportAction": (
                "dialog",
                "0x06008ede",
                36573,
                "0x767f6b0",
            ),
            "StartRemoteCommAndTeleport": (
                "remotecomm",
                "0x06008eed",
                36588,
                "0x768008c",
            ),
            "StartFmvAndTeleportAction": (
                "cutscene",
                "0x06008ee5",
                36580,
                "0x767fbe8",
            ),
        }
        for action_type, (playback_type, token, method_index, rva) in expected.items():
            with self.subTest(action_type=action_type):
                probe = probes[action_type]
                self.assertEqual(probe["playbackType"], playback_type)
                self.assertEqual(probe["token"], token)
                self.assertEqual(probe["methodIndex"], method_index)
                self.assertEqual(probe["rva"], rva)

        self.assertEqual(
            probes["StartCutsceneAndControlSceneObjectAction"]["symbol"],
            "Beyond.Gameplay.Actions.StartCutsceneAndControlSceneObjectAction.PlayCinematic",
        )
        self.assertEqual(
            probes["StartCutsceneAndHideSceneObjectAction"]["symbol"],
            "Beyond.Gameplay.Actions.StartCutsceneAndHideSceneObjectAction.PlayCinematic",
        )
        self.assertEqual(
            probes["PlayLevelSequenceAndControlSceneObjectsAction"]["symbol"],
            "Beyond.Gameplay.Actions.PlayLevelSequenceAndControlSceneObjectsAction.PlayCinematic",
        )
        self.assertEqual(
            probes["PlayLevelSequenceAndHideSceneObjectsAction"]["symbol"],
            "Beyond.Gameplay.Actions.PlayLevelSequenceAndHideSceneObjectsAction.PlayCinematic",
        )
        self.assertEqual(
            probes["PlayDialogAndHideSceneObjectAction"]["symbol"],
            "Beyond.Gameplay.Actions.PlayDialogAndHideSceneObjectAction.PlayCinematic",
        )
        self.assertEqual(probes["PlayFmvAction"]["keyMap"], "fmv")
        self.assertEqual(probes["StartFmvAndTeleportAction"]["keyMap"], "fmv")
        for rejected in (
            "FacPlayInteractLockedRadio",
            "PlayVoiceNarrative",
            "TravelPoleHandoverToCutscene",
            "PreloadCutsceneAction",
        ):
            with self.subTest(rejected=rejected):
                self.assertNotIn(rejected, probes)

        fmv_map = manifest["hooks"]["playbackKeyMaps"]["fmv"]
        self.assertEqual(len(fmv_map), 22)
        self.assertEqual(fmv_map["cs_video_e9m3_1"], "cutscene_e9m3_1")
        self.assertNotIn("f_cs_video_e9m3_1", fmv_map)
        self.assertNotIn("cs_video_e1m1_1", fmv_map)

    def test_shader_agent_receives_selected_target(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "shader-agent.js"
        path.write_text(
            f"const CONFIG = {capture.SHADER_AGENT_PLACEHOLDER};\n",
            encoding="utf-8",
        )
        manifest = {
            "gameBuild": "fixture",
            "moduleName": "UnityPlayer.dll",
            "hook": {"rva": "0x1"},
            "capture": {"maxPairs": 1},
            "targets": {"wulfa-settled": {"actor": "Wulfa"}},
            "evidenceBoundary": {"classification": "observed_runtime"},
        }

        rendered = capture.render_shader_agent_source(
            path, manifest, "wulfa-settled"
        )

        config_text = rendered.removeprefix("const CONFIG = ").removesuffix(";\n")
        config = json.loads(config_text)
        self.assertEqual(config["targetId"], "wulfa-settled")
        self.assertEqual(config["target"]["actor"], "Wulfa")


if __name__ == "__main__":
    unittest.main()

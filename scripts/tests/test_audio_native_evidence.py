import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.common import InstalledNativeInputs
from scripts.audio_semantics import native_evidence, responsive_voice


class NativeAudioEvidenceTests(unittest.TestCase):
    def test_missing_inputs_fail_closed_with_paths_named(self) -> None:
        context = native_evidence.validate_native_audio_evidence(
            Path("missing-metadata"),
            Path("missing-gameassembly"),
        )
        self.assertEqual(context.status, "missing")
        self.assertFalse(context.validated)
        self.assertIn("global-metadata.dat", context.reason)
        self.assertIn("GameAssembly.dll", context.reason)

    def test_hash_mismatch_reports_expected_and_actual(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = root / "global-metadata.dat"
            gameassembly = root / "GameAssembly.dll"
            metadata.write_bytes(b"metadata")
            gameassembly.write_bytes(b"assembly")
            with patch.object(
                native_evidence,
                "check_installed_native_inputs",
                return_value=InstalledNativeInputs(
                    gameassembly,
                    metadata,
                    "wrong-gameassembly",
                    "wrong-metadata",
                    "mismatched",
                    "fixture mismatch",
                ),
            ):
                context = native_evidence.validate_native_audio_evidence(
                    metadata,
                    gameassembly,
                )
        diagnostic = context.unavailable_contract("fixture")
        self.assertEqual(context.status, "mismatched")
        self.assertEqual(diagnostic["actualMetadataSha256"], "wrong-metadata")
        self.assertEqual(diagnostic["actualGameAssemblySha256"], "wrong-gameassembly")

    def test_exact_hashes_validate_the_supplied_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = root / "custom" / "global-metadata.dat"
            gameassembly = root / "custom-client" / "GameAssembly.dll"
            metadata.parent.mkdir()
            gameassembly.parent.mkdir()
            metadata.write_bytes(b"metadata")
            gameassembly.write_bytes(b"assembly")
            with patch.object(
                native_evidence,
                "check_installed_native_inputs",
                return_value=InstalledNativeInputs(
                    gameassembly,
                    metadata,
                    native_evidence.EXPECTED_GAMEASSEMBLY_SHA256,
                    native_evidence.EXPECTED_METADATA_SHA256,
                    "validated",
                    "",
                ),
            ) as gate:
                context = native_evidence.validate_native_audio_evidence(
                    metadata,
                    gameassembly,
                )
        self.assertTrue(context.validated)
        self.assertEqual(gate.call_args.kwargs["metadata"], metadata)
        self.assertEqual(gate.call_args.kwargs["gameassembly"], gameassembly)

    def test_authored_ai_bark_survives_without_native_dispatch_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            export_root = Path(temporary)
            table_root = export_root / "structured/StreamingAssets/Table"
            table_root.mkdir(parents=True)
            (table_root / "AIBark.json").write_text(json.dumps({
                "bark_fixture": {"array": [{
                    "barkId": "bark_fixture",
                    "triggerKey": ["combat_fighting"],
                }]},
            }), encoding="utf-8")
            (table_root / "ResponsiveDialog.json").write_text(json.dumps({
                "1": {"speakers": {"eny_fixture": {"triggers": {
                    "combat_fighting": {"response": [123], "weight": [100]},
                }}}},
            }), encoding="utf-8")
            context = native_evidence.NativeAudioEvidence(
                None,
                None,
                "missing",
                reason="fixture",
            )
            rows = responsive_voice.collect_ai_bark_trigger_rows(
                export_root,
                native_context=context,
            )
            voices = responsive_voice.collect_responsive_voice_contexts(
                export_root,
                {"audioDialogWwiseEventAliases": [{
                    "eventHash": 123,
                    "voiceId": 123,
                    "name": "eny_fixture_combat_fighting_sv",
                }]},
                native_context=context,
            )
        bark = rows["combat_fighting"][0]
        response = voices["eny_fixture_combat_fighting_sv"][1]
        self.assertNotIn("barkSystemMethodVa", bark)
        self.assertEqual(bark["runtimeActivationStatus"], "nativeAudioEvidenceUnavailable")
        self.assertEqual(
            response["aiBarkRuntimeStatus"],
            "authoredAIBarkTableTriggerNativeRouteUnavailable",
        )
        self.assertIsNone(response["enemyTriggerVoiceAction"])


if __name__ == "__main__":
    unittest.main()

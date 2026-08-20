import json
import hashlib
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.common import InstalledNativeInputs
from scripts.audio_semantics import native_evidence, responsive_voice


def _model_view_fixture_pe(
    path: Path,
    *,
    execute_calls: bool = True,
) -> dict:
    """Write a tiny PE whose one text section contains the three route bodies."""

    image_base = 0x180000000
    section_rva = 0x3281000
    raw_offset = 0x400
    execute_va = int(native_evidence.MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE["consumer"]["virtualAddress"], 0)
    post_va = int(native_evidence.MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE["directCalls"][0]["targetVirtualAddress"], 0)
    register_va = int(native_evidence.MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE["directCalls"][1]["targetVirtualAddress"], 0)
    post_body = b"\x90\xc3"
    register_body = b"\x90\x90\xc3"
    execute = bytearray(b"\x90" * 24)
    if execute_calls:
        for offset, target in ((1, post_va), (8, register_va)):
            execute[offset] = 0xE8
            struct.pack_into("<i", execute, offset + 1, target - (execute_va + offset + 5))
    execute[-1] = 0xC3
    section = bytearray(0x2000)
    for virtual_address, body in (
        (execute_va, bytes(execute)),
        (post_va, post_body),
        (register_va, register_body),
    ):
        start = virtual_address - (image_base + section_rva)
        section[start:start + len(body)] = body
    data = bytearray(raw_offset + len(section))
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", data, 0x84, 0x8664, 1, 0, 0, 0, 0xF0, 0x2022)
    optional = 0x98
    struct.pack_into("<H", data, optional, 0x20B)
    struct.pack_into("<Q", data, optional + 24, image_base)
    struct.pack_into("<II", data, optional + 32, 0x1000, 0x200)
    struct.pack_into("<II", data, optional + 56, section_rva + len(section), 0x200)
    section_header = optional + 0xF0
    data[section_header:section_header + 8] = b".text\0\0\0"
    struct.pack_into("<IIII", data, section_header + 8, len(section), section_rva, len(section), raw_offset)
    data[raw_offset:] = section
    path.write_bytes(data)
    route = {
        **native_evidence.MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE,
        "consumer": {
            **native_evidence.MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE["consumer"],
            "bodySha256": hashlib.sha256(bytes(execute)).hexdigest(),
        },
        "directCalls": [
            {
                **native_evidence.MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE["directCalls"][0],
                "targetBodySha256": hashlib.sha256(post_body).hexdigest(),
            },
            {
                **native_evidence.MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE["directCalls"][1],
                "targetBodySha256": hashlib.sha256(register_body).hexdigest(),
            },
        ],
    }
    return route


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

    def test_required_native_evidence_env_hard_fails_hash_mismatch(self) -> None:
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
            ), patch.dict("os.environ", {"ENDFIELD_REQUIRE_NATIVE_EVIDENCE": "1"}):
                with self.assertRaisesRegex(RuntimeError, "native evidence required"):
                    native_evidence.validate_native_audio_evidence(metadata, gameassembly)

    def test_required_native_evidence_env_hard_fails_missing_input(self) -> None:
        with patch.dict("os.environ", {"ENDFIELD_REQUIRE_NATIVE_EVIDENCE": "1"}):
            with self.assertRaisesRegex(RuntimeError, "native evidence required"):
                native_evidence.validate_native_audio_evidence(
                    Path("missing-metadata"),
                    Path("missing-gameassembly"),
                )

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

    def test_model_view_production_route_audits_pe_bodies_and_direct_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = root / "global-metadata.dat"
            gameassembly = root / "GameAssembly.dll"
            metadata.write_bytes(b"metadata")
            route = _model_view_fixture_pe(gameassembly)
            with patch.object(
                native_evidence,
                "MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE",
                route,
            ), patch.object(
                native_evidence,
                "check_installed_native_inputs",
                return_value=InstalledNativeInputs(
                    gameassembly, metadata,
                    native_evidence.EXPECTED_GAMEASSEMBLY_SHA256,
                    native_evidence.EXPECTED_METADATA_SHA256,
                    "validated", "",
                ),
            ):
                context = native_evidence.validate_native_audio_evidence(metadata, gameassembly)
                audited = native_evidence.audit_model_view_state_audio_native_route(context)
        self.assertEqual(audited["status"], "validated")
        self.assertEqual(audited["checks"]["bodySha256"], "validated")
        self.assertEqual(audited["checks"]["executeDirectCalls"], "validated")

    def test_model_view_production_route_reports_catalog_and_body_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = root / "global-metadata.dat"
            gameassembly = root / "GameAssembly.dll"
            metadata.write_bytes(b"metadata")
            _model_view_fixture_pe(gameassembly)
            base = native_evidence.MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE
            mismatched = {**base, "consumer": {**base["consumer"], "methodIndex": 1}}
            body_drift = {**base, "consumer": {**base["consumer"], "bodySha256": "0" * 64}}
            with patch.object(
                native_evidence,
                "check_installed_native_inputs",
                return_value=InstalledNativeInputs(
                    gameassembly, metadata,
                    native_evidence.EXPECTED_GAMEASSEMBLY_SHA256,
                    native_evidence.EXPECTED_METADATA_SHA256,
                    "validated", "",
                ),
            ):
                context = native_evidence.validate_native_audio_evidence(metadata, gameassembly)
                with patch.object(native_evidence, "MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE", mismatched):
                    catalog_audit = native_evidence.audit_model_view_state_audio_native_route(context)
                with patch.object(native_evidence, "MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE", body_drift):
                    body_audit = native_evidence.audit_model_view_state_audio_native_route(context)
        self.assertEqual(catalog_audit["status"], "mismatched")
        self.assertIn("consumer methodIndex", catalog_audit["reason"])
        self.assertEqual(body_audit["status"], "mismatched")
        self.assertIn("body SHA256 drift", body_audit["reason"])

    def test_model_view_production_route_reports_execute_call_drift_and_hard_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = root / "global-metadata.dat"
            gameassembly = root / "GameAssembly.dll"
            metadata.write_bytes(b"metadata")
            route = _model_view_fixture_pe(gameassembly, execute_calls=False)
            with patch.object(
                native_evidence,
                "MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE",
                route,
            ), patch.object(
                native_evidence,
                "check_installed_native_inputs",
                return_value=InstalledNativeInputs(
                    gameassembly, metadata,
                    native_evidence.EXPECTED_GAMEASSEMBLY_SHA256,
                    native_evidence.EXPECTED_METADATA_SHA256,
                    "validated", "",
                ),
            ):
                context = native_evidence.validate_native_audio_evidence(metadata, gameassembly)
                audit = native_evidence.audit_model_view_state_audio_native_route(context)
                with patch.dict("os.environ", {"ENDFIELD_REQUIRE_NATIVE_EVIDENCE": "1"}):
                    with self.assertRaisesRegex(RuntimeError, "direct-call target drift"):
                        native_evidence.model_view_state_audio_native_route(context)
        self.assertEqual(audit["status"], "mismatched")
        self.assertIn("direct-call target drift", audit["reason"])

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

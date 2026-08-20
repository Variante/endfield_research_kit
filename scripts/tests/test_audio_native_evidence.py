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


def _positioned_model_view_fixture_pe(
    path: Path,
    *,
    execute_calls: bool = True,
    audio_handle_write: bool = True,
    post_and_forget_bridge_call: bool = True,
    bridge_tail_jump: bool = True,
) -> dict:
    """Build a compact multi-section PE for the positioned route audit."""

    image_base = 0x180000000
    route = native_evidence.MODEL_VIEW_POSITIONED_AUDIO_NATIVE_ROUTE
    consumer = route["consumer"]
    endpoint_rows = route["endpointAudits"]

    def body(
        length: int,
        calls: list[dict] | None = None,
        writes: list[tuple[int, bytes]] | None = None,
        jumps: list[dict] | None = None,
        opcode_sites: list[dict] | None = None,
    ) -> bytes:
        result = bytearray(b"\x90" * length)
        for call in calls or ():
            offset = int(call["offset"], 0)
            target = int(call["targetVirtualAddress"], 0)
            result[offset] = 0xE8
            struct.pack_into(
                "<i", result, offset + 1,
                target - (int(call.get("methodVirtualAddress", 0), 0) + offset + 5),
            )
        for jump in jumps or ():
            offset = int(jump["offset"], 0)
            target = int(jump["targetVirtualAddress"], 0)
            result[offset] = int(jump["opcode"], 0)
            struct.pack_into(
                "<i", result, offset + 1,
                target - (int(jump.get("methodVirtualAddress", 0), 0) + offset + 5),
            )
        for site in opcode_sites or ():
            result[int(site["offset"], 0)] = int(site["opcode"], 0)
        for offset, instruction in writes or ():
            result[offset:offset + len(instruction)] = instruction
        result[-1] = 0xC3
        return bytes(result)

    consumer_calls = [] if not execute_calls else [
        {**row, "methodVirtualAddress": consumer["virtualAddress"]}
        for row in route["directCalls"]
    ]
    bodies: dict[int, bytes] = {
        int(consumer["virtualAddress"], 0): body(
            consumer["bodyLength"],
            consumer_calls,
            ([(int(route["fieldContract"]["audioHandleWrite"]["offset"], 0), b"\x89\x46\x28")]
             if audio_handle_write else []),
        ),
    }
    for endpoint in endpoint_rows:
        va = int(endpoint["targetVirtualAddress"], 0)
        calls = [
            {**row, "methodVirtualAddress": endpoint["targetVirtualAddress"]}
            for row in endpoint.get("calls") or ()
        ]
        jumps = [
            {**row, "methodVirtualAddress": endpoint["targetVirtualAddress"]}
            for row in endpoint.get("jumps") or ()
        ]
        bodies[va] = body(
            endpoint["bodyLength"], calls,
            jumps=jumps,
            opcode_sites=endpoint.get("opcodeSites") or (),
        )
    if not post_and_forget_bridge_call:
        post_va = int("0x183b89730", 0)
        post_body = bytearray(bodies[post_va])
        post_body[0x6b] = 0x90
        bodies[post_va] = bytes(post_body)
    if not bridge_tail_jump:
        bridge_va = int("0x18328a150", 0)
        bridge_body = bytearray(bodies[bridge_va])
        bridge_body[0x60] = 0x90
        bodies[bridge_va] = bytes(bridge_body)

    section_header = 0x98 + 0xF0
    raw_offset = 0x1000
    sections: list[tuple[int, int, int, bytes]] = []
    for index, (va, section_body) in enumerate(sorted(bodies.items())):
        aligned = (raw_offset + 0x1FF) & ~0x1FF
        sections.append((va - image_base, aligned, index, section_body))
        raw_offset = aligned + len(section_body)
    data = bytearray(raw_offset)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into(
        "<HHIIIHH", data, 0x84, 0x8664, len(sections), 0, 0, 0, 0xF0, 0x2022
    )
    struct.pack_into("<H", data, 0x98, 0x20B)
    struct.pack_into("<Q", data, 0x98 + 24, image_base)
    struct.pack_into("<II", data, 0x98 + 32, 0x1000, 0x200)
    struct.pack_into("<II", data, 0x98 + 56, max(rva + len(section_body) for rva, _raw, _idx, section_body in sections), 0x200)
    for rva, raw, index, section_body in sections:
        header = section_header + index * 40
        data[header:header + 8] = f".p{index:06d}".encode("ascii")[:8].ljust(8, b"\0")
        struct.pack_into("<IIII", data, header + 8, len(section_body), rva, len(section_body), raw)
        data[raw:raw + len(section_body)] = section_body

    fixture = {
        **route,
        "consumer": {
            **consumer,
            "bodySha256": hashlib.sha256(bodies[int(consumer["virtualAddress"], 0)]).hexdigest(),
        },
        "endpointAudits": [
            {
                **endpoint,
                "bodySha256": hashlib.sha256(bodies[int(endpoint["targetVirtualAddress"], 0)]).hexdigest(),
            }
            for endpoint in endpoint_rows
        ],
    }
    path.write_bytes(data)
    return fixture


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

    def test_positioned_route_catalog_and_endpoint_drift_fail_closed(self) -> None:
        context = native_evidence.NativeAudioEvidence(
            Path("global-metadata.dat"), Path("GameAssembly.dll"), "validated",
            native_evidence.EXPECTED_METADATA_SHA256,
            native_evidence.EXPECTED_GAMEASSEMBLY_SHA256,
        )
        route = native_evidence.MODEL_VIEW_POSITIONED_AUDIO_NATIVE_ROUTE
        self.assertEqual(
            native_evidence.audit_model_view_positioned_audio_native_route(
                context, observed_route=route
            )["status"],
            "validated",
        )
        drifted = {
            **route,
            "endpointAudits": [
                {**route["endpointAudits"][0], "bodySha256": "0" * 64},
                *route["endpointAudits"][1:],
            ],
        }
        audited = native_evidence.audit_model_view_positioned_audio_native_route(
            context, observed_route=drifted
        )
        self.assertEqual(audited["status"], "mismatched")
        self.assertIn("synthetic observed positioned route differs", audited["reason"])

    def test_positioned_production_fixture_audits_body_hashes_and_e8_sites(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = root / "global-metadata.dat"
            gameassembly = root / "GameAssembly.dll"
            metadata.write_bytes(b"metadata")
            route = _positioned_model_view_fixture_pe(gameassembly)
            with patch.object(
                native_evidence,
                "MODEL_VIEW_POSITIONED_AUDIO_NATIVE_ROUTE",
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
                audited = native_evidence.audit_model_view_positioned_audio_native_route(context)
        self.assertEqual(audited["status"], "validated")
        self.assertEqual(audited["checks"]["consumerDirectCalls"], "validated")
        self.assertEqual(audited["checks"]["consumerAudioHandleWrite"], "validated")
        self.assertEqual(audited["checks"]["endpointAuditStatus"], "staticManagedAdapterRouteVerified")
        self.assertEqual(audited["checks"]["postAndForgetToAudioAdapterConnection"], "verified")
        self.assertEqual(audited["checks"]["managedAdapterE9Transfer"], "validated")
        self.assertEqual(audited["checks"]["endpointBodiesAndCalls"], "validated")

    def test_positioned_production_fixture_rejects_execute_e8_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = root / "global-metadata.dat"
            gameassembly = root / "GameAssembly.dll"
            metadata.write_bytes(b"metadata")
            route = _positioned_model_view_fixture_pe(gameassembly, execute_calls=False)
            with patch.object(
                native_evidence,
                "MODEL_VIEW_POSITIONED_AUDIO_NATIVE_ROUTE",
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
                audited = native_evidence.audit_model_view_positioned_audio_native_route(context)
        self.assertEqual(audited["status"], "mismatched")
        self.assertIn("positioned Execute E8 drift", audited["reason"])

    def test_positioned_production_fixture_rejects_audio_handle_write_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = root / "global-metadata.dat"
            gameassembly = root / "GameAssembly.dll"
            metadata.write_bytes(b"metadata")
            route = _positioned_model_view_fixture_pe(gameassembly, audio_handle_write=False)
            with patch.object(
                native_evidence,
                "MODEL_VIEW_POSITIONED_AUDIO_NATIVE_ROUTE",
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
                audited = native_evidence.audit_model_view_positioned_audio_native_route(context)
        self.assertEqual(audited["status"], "mismatched")
        self.assertIn("m_audioHandle write drift", audited["reason"])

    def test_positioned_production_fixture_rejects_post_and_forget_e8_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = root / "global-metadata.dat"
            gameassembly = root / "GameAssembly.dll"
            metadata.write_bytes(b"metadata")
            route = _positioned_model_view_fixture_pe(gameassembly, post_and_forget_bridge_call=False)
            with patch.object(native_evidence, "MODEL_VIEW_POSITIONED_AUDIO_NATIVE_ROUTE", route), patch.object(
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
                audited = native_evidence.audit_model_view_positioned_audio_native_route(context)
        self.assertEqual(audited["status"], "mismatched")
        self.assertIn("PostAndForget E8 drift at +0x6b", audited["reason"])

    def test_positioned_production_fixture_rejects_adapter_bridge_e9_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            metadata = root / "global-metadata.dat"
            gameassembly = root / "GameAssembly.dll"
            metadata.write_bytes(b"metadata")
            route = _positioned_model_view_fixture_pe(gameassembly, bridge_tail_jump=False)
            with patch.object(native_evidence, "MODEL_VIEW_POSITIONED_AUDIO_NATIVE_ROUTE", route), patch.object(
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
                audited = native_evidence.audit_model_view_positioned_audio_native_route(context)
        self.assertEqual(audited["status"], "mismatched")
        self.assertIn("_PostEventBridge jump opcode drift at +0x60", audited["reason"])

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

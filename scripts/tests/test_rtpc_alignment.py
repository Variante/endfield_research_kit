import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_audio_semantics
from scripts.audio_semantics import native_evidence, rtpc_alignment, rtpc_contract


def validated_context() -> native_evidence.NativeAudioEvidence:
    return native_evidence.NativeAudioEvidence(
        Path("selected/global-metadata.dat"),
        Path("selected/GameAssembly.dll"),
        "validated",
        native_evidence.EXPECTED_METADATA_SHA256,
        native_evidence.EXPECTED_GAMEASSEMBLY_SHA256,
        gate_verified=True,
    )


def static_entry(name: str, parameter_id: int) -> dict:
    return {
        "parameterId": parameter_id,
        "parameterIdHex": f"0x{parameter_id:08x}",
        "metadataField": (
            "Beyond.Gameplay.Audio.AudioGameplayConstants+GameParameters."
            + name
        ),
        "nodeRtpcCurveCount": 0,
        "busRtpcCurveCount": 1,
        "serializedHircMatch": True,
    }


CANONICAL_ENTRIES = [
    static_entry(name, parameter_id)
    for name, parameter_id in rtpc_contract.CANONICAL_RTPC_IDS.items()
]


def hirc_index(
    entries: list[dict] | None = None,
    *,
    metadata_sha: str | None = native_evidence.EXPECTED_METADATA_SHA256,
) -> dict:
    evidence = {"entries": copy.deepcopy(entries or CANONICAL_ENTRIES)}
    if metadata_sha is not None:
        evidence["metadataSha256"] = metadata_sha
    return {
        "hircSummary": {
            "postProcessSummary": {
                "gameParameterNameEvidence": evidence,
            },
        },
    }


class StaticRtpcAlignmentTests(unittest.TestCase):
    def test_native_gate_withholds_static_names_and_controls(self) -> None:
        parameter_id = rtpc_contract.CANONICAL_RTPC_IDS[
            "AU_RTPC_GLOBAL_VOL_MASTER_IOS_WORKAROUND"
        ]
        result = rtpc_alignment.build_static_rtpc_alignment(
            hirc_index(),
            [{
                "id": "au_fixture",
                "evidence": [{
                    "actionEvidence": [{
                        "operation": "setGameParameter",
                        "idExt": parameter_id,
                    }],
                }],
            }],
            native_context=native_evidence.NativeAudioEvidence(
                Path("selected/global-metadata.dat"),
                Path("selected/GameAssembly.dll"),
                "mismatched",
                "wrong-metadata",
                "wrong-gameassembly",
                "fingerprint mismatch",
                gate_verified=True,
            ),
        )

        self.assertEqual(result["status"], "mismatched")
        self.assertEqual(result["entries"], [])
        self.assertEqual(result["counts"]["setGameParameterControlCount"], 0)
        self.assertIn("withheld", result["evidenceBoundary"])

    def test_unverified_validated_shape_is_still_withheld(self) -> None:
        result = rtpc_alignment.build_static_rtpc_alignment(
            hirc_index(),
            native_context=native_evidence.NativeAudioEvidence(
                Path("selected/global-metadata.dat"),
                Path("selected/GameAssembly.dll"),
                "validated",
                native_evidence.EXPECTED_METADATA_SHA256,
                native_evidence.EXPECTED_GAMEASSEMBLY_SHA256,
                gate_verified=False,
            ),
        )
        self.assertEqual(result["status"], "unverified")
        self.assertEqual(result["entries"], [])

    def test_stale_serialized_static_source_hash_is_withheld(self) -> None:
        result = rtpc_alignment.build_static_rtpc_alignment(
            hirc_index(metadata_sha="stale-metadata"),
            native_context=validated_context(),
        )
        self.assertEqual(result["status"], "mismatched")
        self.assertEqual(result["entries"], [])
        self.assertIn("metadataSha256", result["nativeGate"]["reason"])

    def test_missing_metadata_hash_is_withheld(self) -> None:
        result = rtpc_alignment.build_static_rtpc_alignment(
            hirc_index(metadata_sha=None),
            native_context=validated_context(),
        )
        self.assertEqual(result["status"], "malformed")
        self.assertEqual(result["entries"], [])

    def test_valid_gate_aligns_curves_properties_and_set_reset_rows(self) -> None:
        parameter_id = rtpc_contract.CANONICAL_RTPC_IDS[
            "AU_RTPC_GLOBAL_VOL_MASTER_IOS_WORKAROUND"
        ]
        result = rtpc_alignment.build_static_rtpc_alignment(
            {
                "hircSummary": {
                    "postProcessSummary": {
                        "gameParameterNameEvidence": {
                            "metadataSha256": native_evidence.EXPECTED_METADATA_SHA256,
                            "entries": copy.deepcopy(CANONICAL_ENTRIES),
                        },
                        "busDefinitions": [{
                            "busId": 7,
                            "serializedStateAndRtpc": {
                                "rtpcCurves": [{
                                    "rtpcId": parameter_id,
                                    "parameterLabel": "BusVolume",
                                    "pointCount": 3,
                                }],
                            },
                        }],
                    },
                },
            },
            [{
                "id": "au_rtpc_fixture",
                "evidence": [{
                    "bankId": 12,
                    "postProcessSummary": {
                        "rtpcIds": [{
                            "rtpcId": parameter_id,
                            "rtpcIdHex": f"0x{parameter_id:08x}",
                            "curveCount": 1,
                        }],
                        "stateRtpcNodes": [{
                            "rtpcCurves": [{
                                "rtpcId": parameter_id,
                                "parameterLabel": "OutputBusVolume",
                                "pointCount": 4,
                            }],
                        }],
                    },
                    "actionEvidence": [
                        {
                            "actionId": 3,
                            "operation": "setGameParameter",
                            "idExt": parameter_id,
                            "actionControlParserStatus": "typedExactV150",
                            "valueRange": {"base": 0.5},
                        },
                        {
                            "actionId": 4,
                            "operation": "resetGameParameter",
                            "idExtHex": f"0x{parameter_id:08x}",
                            "actionControlParserStatus": "typedExactV150",
                        },
                    ],
                }],
            }],
            media=[{
                "eventIds": ["au_rtpc_fixture"],
                "postProcessBusControls": [{
                    "rtpcIds": [f"0x{parameter_id:08x}"],
                }],
            }],
            native_context=validated_context(),
        )

        self.assertEqual(result["status"], "validated")
        self.assertEqual(result["counts"]["staticParameterCount"], 6)
        self.assertEqual(result["counts"]["eventNodeCurveEvidenceCount"], 1)
        self.assertEqual(result["counts"]["busDefinitionCurveEvidenceCount"], 1)
        self.assertEqual(result["counts"]["setGameParameterControlCount"], 1)
        self.assertEqual(result["counts"]["resetGameParameterControlCount"], 1)
        row = next(
            row for row in result["entries"] if row["parameterId"] == parameter_id
        )
        self.assertEqual(row["parameterName"], "AU_RTPC_GLOBAL_VOL_MASTER_IOS_WORKAROUND")
        self.assertEqual(row["parameterIdHex"], "0x3794392f")
        self.assertEqual(row["controlledProperties"], {
            "BusVolume": 1,
            "OutputBusVolume": 1,
        })
        self.assertEqual(
            {control["operation"] for control in row["controlRows"]},
            {"setGameParameter", "resetGameParameter"},
        )
        self.assertTrue(all(
            "initialRtpcJoin" in control for control in row["controlRows"]
        ))
        self.assertEqual(row["evidenceClass"], "authoredStatic")
        self.assertEqual(row["runtimeValueStatus"], "unobserved")
        self.assertEqual(row["targetObjectStatus"], "unresolved")
        self.assertEqual(row["selectedBranchStatus"], "unobserved")
        self.assertEqual(row["dspAudibilityStatus"], "unobserved")
        self.assertTrue(all(
            control["parameterId"] == control["rtpcId"]
            and control["parameterIdHex"] == control["rtpcIdHex"]
            for control in row["controlRows"]
        ))

    def test_paired_numeric_hex_conflicts_never_reassign_to_another_parameter(self) -> None:
        amb_id = rtpc_contract.CANONICAL_RTPC_IDS["AU_RTPC_CINE_CTRL_VOL_AMB"]
        sfx_id = rtpc_contract.CANONICAL_RTPC_IDS["AU_RTPC_CINE_CTRL_VOL_SFX"]
        index = hirc_index()
        index["hircSummary"]["postProcessSummary"]["busDefinitions"] = [{
            "busId": 7,
            "serializedStateAndRtpc": {
                "rtpcCurves": [{
                    "rtpcId": amb_id,
                    "rtpcIdHex": f"0x{sfx_id:08x}",
                    "points": [],
                }],
            },
        }]
        result = rtpc_alignment.build_static_rtpc_alignment(
            index,
            [{
                "id": "conflict_fixture",
                "evidence": [{
                    "postProcessSummary": {
                        "rtpcIds": [{
                            "rtpcId": amb_id,
                            "rtpcIdHex": f"0x{sfx_id:08x}",
                        }],
                        "stateRtpcNodes": [{
                            "rtpcCurves": [{
                                "rtpcId": amb_id,
                                "rtpcIdHex": f"0x{sfx_id:08x}",
                                "points": [],
                            }],
                        }],
                    },
                    "actionEvidence": [{
                        "operation": "setGameParameter",
                        "idExt": amb_id,
                        "idExtHex": f"0x{sfx_id:08x}",
                    }],
                }],
            }],
            native_context=validated_context(),
        )

        self.assertEqual(result["status"], "degraded")
        self.assertGreaterEqual(result["diagnosticCount"], 4)
        self.assertTrue(any("conflicting" in row for row in result["diagnostics"]))
        for row in result["entries"]:
            self.assertEqual(row["eventNodeCurveCount"], 0)
            self.assertEqual(row["busDefinitionCurveCount"], 0)
            self.assertEqual(row["setGameParameterCount"], 0)
            self.assertEqual(row["eventIds"], [])
            self.assertEqual(row["controlRows"], [])

    def test_nested_non_list_shapes_are_degraded_without_association(self) -> None:
        parameter_id = rtpc_contract.CANONICAL_RTPC_IDS[
            "AU_RTPC_GLOBAL_VOL_MASTER_IOS_WORKAROUND"
        ]

        def event_with(post: dict | None = None, actions: object = None) -> list[dict]:
            evidence = {
                "postProcessSummary": post or {},
                "actionEvidence": [] if actions is None else actions,
            }
            return [{"id": "malformed_fixture", "evidence": [evidence]}]

        cases: list[tuple[str, dict, list[dict], list[dict]]] = [
            (
                "event.evidence",
                hirc_index(),
                [{"id": "malformed_fixture", "evidence": {}}],
                [],
            ),
            (
                "stateRtpcNodes",
                hirc_index(),
                event_with({"stateRtpcNodes": {}}),
                [],
            ),
            (
                "rtpcIds",
                hirc_index(),
                event_with({"rtpcIds": {}}),
                [],
            ),
            (
                "curve points",
                hirc_index(),
                event_with({
                    "stateRtpcNodes": [{"rtpcCurves": [{
                        "rtpcId": parameter_id,
                        "points": {},
                    }]}],
                }),
                [],
            ),
            (
                "actionEvidence",
                hirc_index(),
                event_with({}, actions={}),
                [],
            ),
            (
                "busDefinitions",
                {
                    **hirc_index(),
                    "hircSummary": {
                        "postProcessSummary": {
                            "gameParameterNameEvidence": {
                                "metadataSha256": native_evidence.EXPECTED_METADATA_SHA256,
                                "entries": copy.deepcopy(CANONICAL_ENTRIES),
                            },
                            "busDefinitions": {},
                        },
                    },
                },
                [],
                [],
            ),
            (
                "bus rtpcCurves",
                {
                    **hirc_index(),
                    "hircSummary": {
                        "postProcessSummary": {
                            "gameParameterNameEvidence": {
                                "metadataSha256": native_evidence.EXPECTED_METADATA_SHA256,
                                "entries": copy.deepcopy(CANONICAL_ENTRIES),
                            },
                            "busDefinitions": [{
                                "serializedStateAndRtpc": {"rtpcCurves": {}},
                            }],
                        },
                    },
                },
                [],
                [],
            ),
        ]
        for label, index, events, media in cases:
            with self.subTest(shape=label):
                result = rtpc_alignment.build_static_rtpc_alignment(
                    index,
                    events,
                    media,
                    native_context=validated_context(),
                )
                self.assertEqual(result["status"], "degraded")
                self.assertGreater(result["diagnosticCount"], 0)
                self.assertTrue(all(
                    not row["eventIds"] and not row["controlRows"]
                    for row in result["entries"]
                ))

        media_shapes = [
            ("media eventIds", [{"eventIds": {}, "postProcessBusControls": []}]),
            ("media controls", [{"eventIds": [], "postProcessBusControls": {}}]),
            ("media control rtpcIds", [{
                "eventIds": [],
                "postProcessBusControls": [{"rtpcIds": {}}],
            }]),
        ]
        for label, media in media_shapes:
            with self.subTest(shape=label):
                result = rtpc_alignment.build_static_rtpc_alignment(
                    hirc_index(), media=media, native_context=validated_context()
                )
                self.assertEqual(result["status"], "degraded")
                self.assertGreater(result["diagnosticCount"], 0)

    def test_fake_name_wrong_hex_and_duplicate_id_fail_closed(self) -> None:
        fake_name = copy.deepcopy(CANONICAL_ENTRIES)
        fake_name[0]["metadataField"] = fake_name[0]["metadataField"].replace(
            "AU_RTPC_CINE_CTRL_VOL_AMB", "AU_RTPC_FAKE"
        )
        wrong_hex = copy.deepcopy(CANONICAL_ENTRIES)
        wrong_hex[0]["parameterIdHex"] = "0x00000001"
        duplicate_name = copy.deepcopy(CANONICAL_ENTRIES)
        duplicate_name[1]["metadataField"] = duplicate_name[0]["metadataField"]
        duplicate_name[1]["parameterId"] = duplicate_name[0]["parameterId"]
        duplicate_name[1]["parameterIdHex"] = duplicate_name[0]["parameterIdHex"]
        duplicate_name_multi_id = copy.deepcopy(CANONICAL_ENTRIES)
        duplicate_name_multi_id[1]["metadataField"] = duplicate_name_multi_id[0]["metadataField"]
        duplicate_name_multi_id[1]["parameterId"] = rtpc_contract.CANONICAL_RTPC_IDS[
            "AU_RTPC_CINE_CTRL_VOL_SFX"
        ]
        duplicate_name_multi_id[1]["parameterIdHex"] = "0x52aabb05"
        for entries in (
            fake_name,
            wrong_hex,
            duplicate_name,
            duplicate_name_multi_id,
        ):
            with self.subTest(entries=entries):
                result = rtpc_alignment.build_static_rtpc_alignment(
                    hirc_index(entries), native_context=validated_context()
                )
                self.assertEqual(result["status"], "malformed")
                self.assertEqual(result["entries"], [])

    def test_malformed_hirc_shapes_fail_closed_without_throwing(self) -> None:
        malformed_indexes = [
            {"hircSummary": []},
            {"hircSummary": {"postProcessSummary": []}},
            {"hircSummary": {
                "postProcessSummary": {"gameParameterNameEvidence": []},
            }},
        ]
        for index in malformed_indexes:
            with self.subTest(index=index):
                result = rtpc_alignment.build_static_rtpc_alignment(
                    index, native_context=validated_context()
                )
                self.assertEqual(result["status"], "malformed")
                self.assertEqual(result["entries"], [])

    def test_stale_published_hirc_names_are_withheld(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(
                build_audio_semantics.native_evidence,
                "validate_native_audio_evidence",
                return_value=validated_context(),
            ):
                payload = build_audio_semantics.build_audio_semantic_data(
                    hirc_index(metadata_sha="stale-metadata"),
                    language="CN",
                    export_root=root / "export_full",
                    webui_root=root / "webui",
                )
        evidence = (
            payload["hircSummary"]["postProcessSummary"]
            ["gameParameterNameEvidence"]
        )
        self.assertEqual(evidence["entries"], [])
        self.assertEqual(evidence["status"], "mismatched")

    def test_audio_script_cache_bust_is_explicitly_updated(self) -> None:
        html = Path("webui/index.html").read_text(encoding="utf-8")
        lines = [
            line.strip() for line in html.splitlines()
            if "src/features/audio/index.js?v=" in line
        ]
        self.assertEqual(len(lines), 1)
        self.assertNotIn("20260815-audio-player-order1", lines[0])
        self.assertRegex(lines[0], r"src/features/audio/index\.js\?v=20260822-audio-")


if __name__ == "__main__":
    unittest.main()

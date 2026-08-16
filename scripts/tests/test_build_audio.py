import argparse
import base64
import json
import tempfile
import unittest
from pathlib import Path
from struct import pack, pack_into
from unittest import mock

from scripts import build_audio


def sound_source_data(
    media_id: int,
    parent_id: int = 0,
    *,
    plugin_id: int = 0x00040001,
    stream_type: int = 2,
    in_memory_size: int = 0,
    source_bits: int = 0,
    plugin_parameters: bytes = b"",
) -> bytes:
    source = pack(
        "<IBIIB", plugin_id, stream_type, media_id,
        in_memory_size, source_bits,
    )
    if plugin_id & 0x0F == 2:
        source += pack("<I", len(plugin_parameters)) + plugin_parameters
    return source + bytes(4) + pack("<II", 0, parent_id)


def roomverb_parameter_data() -> bytes:
    payload = bytearray(186)
    for offset, value in (
        (0, 1.2), (4, 2.25), (8, 100.0), (12, 180.0),
        (16, -6.0), (20, 300.0), (24, 1.0),
        (28, 3.0), (32, 1000.0), (36, 0.7),
        (40, -2.0), (44, 8000.0), (48, 1.0),
        (52, 0.0), (56, -3.0), (60, -6.0), (64, -96.3),
        (68, -1.0), (72, -20.0), (76, -9.0),
        (85, 25.0), (89, 100.0), (93, 40.0),
        (97, 80.0), (101, 100.0),
        (134, 0.0), (138, -96.3),
        (142, 8.0), (146, 50.0), (150, 2.0), (154, 0.1),
        (158, 0.8), (162, 66.0), (166, 15.0), (170, 5.0),
        (174, 40.0), (178, 100.0), (182, 50.0),
    ):
        pack_into("<f", payload, offset, value)
    payload[80] = 1
    pack_into("<I", payload, 81, 23)
    pack_into("<I", payload, 105, 8)
    payload[109] = 1
    for offset, insert, curve in ((110, 3, 0), (118, 2, 1), (126, 1, 2)):
        pack_into("<II", payload, offset, insert, curve)
    return bytes(payload)


def convolution_reverb_parameter_data() -> bytes:
    return pack(
        "<12fIfB",
        30.0, 0.0,
        180.0, 0.0, -96.3, 0.0,
        0.0, 0.0, -9.0, -96.3,
        -14.3, 3.0,
        0, -60.0, 2,
    )


def guitar_distortion_parameter_data() -> bytes:
    return b"".join((
        pack("<IfffB", 3, 0.0, 1000.0, 1.0, 0),
        pack("<IfffB", 5, 0.0, 476.0, 0.1, 0),
        pack("<IfffB", 4, 0.0, 347.0, 1.0, 1),
        pack("<IfffB", 3, 0.0, 4660.0, 1.0, 1),
        pack("<IfffB", 0, 0.0, 1000.0, 1.0, 0),
        pack("<IfffB", 4, -13.0, 591.0, 1.0, 1),
        pack("<I5f", 3, 61.0, 50.0, 0.0, 0.0, 100.0),
    ))


def mastering_suite_parameter_data() -> bytes:
    payload = bytearray(304)
    payload[0:4] = bytes((1, 1, 0, 1))
    pack_into("<I", payload, 4, 4)
    payload[8:14] = bytes((1, 1, 0, 1, 0, 0))
    eq_bands = (
        (2, 40.0, 0.2469136, 1.0),
        (3, 200.0, -1.5, 1.0),
        (3, 889.3164, 0.0, 1.0),
        (4, 4800.0, 1.2, 0.5),
        (3, 3000.0, 0.0, 1.0),
        (4, 6000.0, -3.0, 1.0),
    )
    for index, band in enumerate(eq_bands):
        pack_into("<Ifff", payload, 14 + index * 16, *band)
    pack_into("<IIf", payload, 110, 1, 1, 0.0)
    payload[122:127] = bytes((0, 1, 0, 0, 0))
    pack_into("<3f", payload, 127, 161.78, 503.9016, 3033.549)
    compressor_bands = (
        (-18.0, 1.8, 0.12, 0.08, 3.0, 0.0),
        (-40.0, 1.5, 0.05, 0.2, 2.4, 3.6),
        (-36.0, 1.2, 0.1, 0.1, 3.0, 0.0),
        (-40.0, 1.5, 0.05, 0.02, 2.4, 3.6),
    )
    for index, band in enumerate(compressor_bands):
        pack_into("<6f", payload, 139 + index * 24, *band)
    pack_into("<f12f", payload, 231, 3.6, *([-0.2] * 12))
    pack_into("<IfffIB", payload, 283, 2, -3.0, 0.0, 0.0, 0, 1)
    return bytes(payload)


class AudioCategoryTests(unittest.TestCase):
    def test_hirc_node_base_recovers_direct_effect_slots_and_output_bus(self) -> None:
        effect_id = 956324002
        bus_id = 0xE611314A
        parent_id = 386813193
        data = (
            bytes([1, 2, 0])
            + bytes([0]) + pack("<I", 0) + bytes([4])
            + bytes([1]) + pack("<I", effect_id) + bytes([0])
            + bytes([0, 0])
            + pack("<II", bus_id, parent_id)
        )

        node, end = build_audio._hirc_v150_node_base(data, 0)

        self.assertEqual(end, len(data))
        self.assertTrue(node["overrideParentFx"])
        self.assertFalse(node["bypassAll"])
        self.assertEqual(node["overrideBusId"], bus_id)
        self.assertEqual(node["parentId"], parent_id)
        self.assertEqual(node["effects"][0]["referenceStatus"], "emptyEffectSlot")
        self.assertEqual(node["effects"][1]["effectId"], effect_id)
        self.assertEqual(node["effects"][1]["flagsRaw"], 0)
        self.assertFalse(node["effects"][1]["effectBypass"])
        self.assertFalse(node["effects"][1]["effectShareSet"])
        self.assertFalse(node["effects"][1]["effectRendered"])
        self.assertEqual(node["effects"][1]["unknownFlagBits"], 0)

    def test_hirc_v150_aux_sends_decode_counted_prefix_and_four_slots(self) -> None:
        bus_ids = [0x10203040, 0, 0x50607080, 0]
        reflections_bus_id = 0x90A0B0C0
        data = (
            bytes([0x21])
            + bytes([1, 8]) + pack("<f", -6.0)
            + bytes([1, 5]) + pack("<ff", -1.0, 1.0)
            + bytes([0])
            + bytes([0x0F])
            + pack("<4I", *bus_ids)
            + pack("<I", reflections_bus_id)
        )

        aux = build_audio._hirc_v150_node_aux_sends(data, 0)

        self.assertEqual(aux["parserStatus"], "typedExactV150NodeAuxParams")
        self.assertEqual(aux["propertyIds"], [8])
        self.assertEqual(aux["properties"][0]["propertyLabel"], "UserAuxSendVolume0")
        self.assertEqual(aux["properties"][0]["floatValue"], -6.0)
        self.assertEqual(aux["properties"][0]["rawHex"], "0xc0c00000")
        self.assertEqual(aux["properties"][0]["valueEncoding"], "float")
        self.assertEqual(aux["rangedPropertyIds"], [5])
        self.assertEqual(aux["rangedProperties"][0]["propertyLabel"], "MakeUpGain")
        self.assertEqual(aux["rangedProperties"][0]["minimumFloat"], -1.0)
        self.assertEqual(aux["rangedProperties"][0]["maximumFloat"], 1.0)
        self.assertEqual(aux["auxParamsOffset"], 18)
        self.assertTrue(aux["overrideGameDefinedAuxSends"])
        self.assertTrue(aux["useGameDefinedAuxSends"])
        self.assertTrue(aux["overrideUserDefinedAuxSends"])
        self.assertTrue(aux["hasUserDefinedAuxSendSlots"])
        self.assertEqual(aux["userDefinedAuxBusIds"], bus_ids)
        self.assertEqual(
            [row["slotIndex"] for row in aux["userDefinedAuxSends"]], [0, 2]
        )
        self.assertEqual(aux["reflectionsAuxBusId"], reflections_bus_id)

    def test_hirc_v150_aux_sends_preserves_integer_union_values(self) -> None:
        data = (
            bytes([0, 1, 0x54]) + pack("<I", 0x14)
            + bytes([0, 0, 0]) + pack("<I", 0)
        )

        aux = build_audio._hirc_v150_node_aux_sends(data, 0)

        self.assertEqual(aux["properties"][0]["propertyLabel"], "Loop")
        self.assertEqual(aux["properties"][0]["rawU32"], 0x14)
        self.assertEqual(aux["properties"][0]["valueEncoding"], "u32Likely")

    def test_hirc_v150_aux_sends_decode_runtime_game_defined_flag_without_ids(self) -> None:
        data = bytes([0, 0, 0, 0, 0x03]) + pack("<I", 0)

        aux = build_audio._hirc_v150_node_aux_sends(data, 0)

        self.assertTrue(aux["overrideGameDefinedAuxSends"])
        self.assertTrue(aux["useGameDefinedAuxSends"])
        self.assertFalse(aux["hasUserDefinedAuxSendSlots"])
        self.assertEqual(aux["userDefinedAuxBusIds"], [])
        self.assertEqual(
            aux["gameDefinedAssignmentBoundary"],
            "runtimeAuxBusIdsAndControlValuesNotSerialized",
        )

    def test_hirc_v150_aux_sends_fail_closed_with_field_diagnostic(self) -> None:
        data = bytes([0, 0, 0, 0, 0x08]) + pack("<I", 0x10203040)

        with self.assertRaisesRegex(
            ValueError,
            r"userDefinedSlots truncated: offset=5 required=16 remaining=4",
        ):
            build_audio._hirc_v150_node_aux_sends(data, 0)

    def test_hirc_v150_node_state_and_rtpc_decode_exact_layout(self) -> None:
        state_group_id = 0xF6699CF4
        first_state_id = 0x1A9FC91F
        second_state_id = 0x1B9ABDB1
        game_parameter_id = 0x2B99882E
        modulator_id = 0x10CE34A1
        data = b"".join((
            pack("<BBHBB", 0x1B, 2, 12, 3, 0x0D),
            bytes([2, 0, 2, 1, 43, 1, 1]),
            bytes([1]),
            pack("<IBB", state_group_id, 0, 2),
            pack("<IH", first_state_id, 2),
            pack("<HHff", 0, 43, -6.0, -3.0),
            pack("<IH", second_state_id, 1),
            pack("<Hf", 3, 45.0),
            pack("<H", 2),
            pack("<IBBBIBH", game_parameter_id, 0, 1, 42, 7, 2, 2),
            pack("<ffIffI", 0.0, -96.0, 4, 1.0, 0.0, 8),
            pack("<IBB", modulator_id, 4, 2),
            bytes([0x82, 0x30]),
            pack("<IBHffI", 8, 0, 1, 0.0, 1.0, 4),
        ))

        parsed = build_audio._hirc_v150_node_state_rtpc(data, 0)

        self.assertEqual(parsed["parserStatus"], "typedExactV150NodeStateAndRtpc")
        self.assertEqual(parsed["nodeBaseEndOffset"], len(data))
        self.assertEqual(parsed["remainingSubtypeByteLength"], 0)
        self.assertEqual(parsed["advSettings"]["virtualQueueBehaviorLabel"], "resume")
        self.assertEqual(parsed["advSettings"]["belowThresholdBehaviorLabel"], "killIfOneShotElseVirtual")
        self.assertEqual(parsed["statePropertyCount"], 2)
        self.assertEqual(parsed["stateProperties"][1]["parameterLabel"], "OutputBusVolume")
        self.assertEqual(parsed["stateGroups"][0]["groupId"], state_group_id)
        self.assertEqual(parsed["stateGroups"][0]["states"][0]["values"][0]["value"], -6.0)
        self.assertEqual(parsed["rtpcCurveCount"], 2)
        self.assertEqual(parsed["rtpcPointCount"], 3)
        self.assertEqual(parsed["rtpcCurves"][0]["rtpcTypeLabel"], "gameParameter")
        self.assertEqual(parsed["rtpcCurves"][0]["parameterLabel"], "UserAuxSendVolume3")
        self.assertEqual(parsed["rtpcCurves"][1]["parameterId"], 6146)
        self.assertEqual(parsed["rtpcCurves"][1]["rtpcTypeLabel"], "modulator")

    def test_hirc_v150_node_state_and_rtpc_fail_closed_with_diagnostic(self) -> None:
        data = pack("<BBHBB", 0, 0, 0, 0, 0) + bytes([0, 0]) + pack("<H", 1)

        with self.assertRaisesRegex(
            ValueError,
            r"rtpcId truncated: offset=10 required=4 remaining=0",
        ):
            build_audio._hirc_v150_node_state_rtpc(data, 0)

    def test_hirc_node_processing_summary_preserves_state_rtpc_curves(self) -> None:
        group_id = 0xF6699CF4
        rtpc_id = 0x2B99882E
        summary = build_audio.summarize_hirc_node_processing({
            7: {
                "objectId": 7,
                "objectType": 2,
                "objectTypeLabel": "sound",
                "rootActionIds": [3],
                "stateAndRtpc": {
                    "parserStatus": "typedExactV150NodeStateAndRtpc",
                    "advSettings": {"virtualQueueBehaviorLabel": "fromBeginning"},
                    "stateProperties": [{"parameterId": 0, "parameterLabel": "Volume"}],
                    "stateGroups": [{
                        "groupId": group_id,
                        "groupIdHex": f"0x{group_id:08x}",
                        "states": [{"values": [{"parameterLabel": "Volume", "value": -6.0}]}],
                    }],
                    "rtpcCurves": [{
                        "rtpcId": rtpc_id,
                        "rtpcIdHex": f"0x{rtpc_id:08x}",
                        "rtpcTypeLabel": "gameParameter",
                        "parameterLabel": "BusVolume",
                        "points": [{"from": 0.0, "to": -96.0}],
                    }],
                    "evidenceBoundary": "runtime values unobserved",
                },
            },
        })

        self.assertEqual(summary["parsedStateRtpcNodeCount"], 1)
        self.assertEqual(summary["failedStateRtpcNodeCount"], 0)
        self.assertEqual(summary["stateGroupReferenceCount"], 1)
        self.assertEqual(summary["stateValueCount"], 1)
        self.assertEqual(summary["rtpcCurveCount"], 1)
        self.assertEqual(summary["rtpcPointCount"], 1)
        self.assertEqual(summary["stateGroups"][0]["groupId"], group_id)
        self.assertEqual(summary["rtpcIds"][0]["rtpcId"], rtpc_id)
        self.assertIn("runtime values unobserved", str(summary["stateRtpcNodes"]))

    def test_hirc_node_processing_summary_counts_authored_effect_flags(self) -> None:
        summary = build_audio.summarize_hirc_node_processing({
            7: {
                "objectId": 7,
                "objectType": 2,
                "objectTypeLabel": "sound",
                "effects": [{
                    "effectId": 1,
                    "effectBypass": True,
                    "effectShareSet": False,
                    "effectRendered": True,
                    "unknownFlagBits": 0,
                }, {
                    "effectId": 2,
                    "effectBypass": False,
                    "effectShareSet": True,
                    "effectRendered": False,
                    "unknownFlagBits": 0,
                }],
            },
        })

        self.assertEqual(summary["effectBypassSlotCount"], 1)
        self.assertEqual(summary["effectShareSetSlotCount"], 1)
        self.assertEqual(summary["effectRenderedSlotCount"], 1)
        self.assertEqual(summary["effectUnknownFlagBitsCount"], 0)

    def test_hirc_node_processing_summary_preserves_authored_aux_boundary(self) -> None:
        bus_id = 0x50607080
        summary = build_audio.summarize_hirc_node_processing({
            7: {
                "objectId": 7,
                "objectType": 2,
                "objectTypeLabel": "sound",
                "rootActionIds": [3],
                "parentId": 9,
                "auxSends": {
                    "parserStatus": "typedExactV150NodeAuxParams",
                    "auxParamsOffset": 4,
                    "auxFlagsRaw": 0x0F,
                    "overrideGameDefinedAuxSends": True,
                    "useGameDefinedAuxSends": True,
                    "overrideUserDefinedAuxSends": True,
                    "hasUserDefinedAuxSendSlots": True,
                    "overrideEarlyReflectionsAuxBus": False,
                    "userDefinedAuxSends": [{
                        "slotIndex": 0,
                        "busId": bus_id,
                        "busIdHex": f"0x{bus_id:08x}",
                    }],
                    "reflectionsAuxBusId": 0,
                    "gameDefinedAssignmentBoundary": (
                        "runtimeAuxBusIdsAndControlValuesNotSerialized"
                    ),
                },
            },
        })

        self.assertEqual(summary["parsedAuxSendNodeCount"], 1)
        self.assertEqual(summary["failedAuxSendNodeCount"], 0)
        self.assertEqual(summary["gameDefinedAuxSendUseBitNodeCount"], 1)
        self.assertEqual(summary["userDefinedAuxSendReferenceCount"], 1)
        self.assertEqual(summary["auxiliaryBuses"][0]["busId"], bus_id)
        self.assertIn(
            "runtimeAuxBusIdsAndControlValuesNotSerialized",
            str(summary["auxSendNodes"]),
        )

    def test_hirc_node_processing_summary_preserves_authored_base_properties(self) -> None:
        summary = build_audio.summarize_hirc_node_processing({
            7: {
                "objectId": 7,
                "objectType": 2,
                "objectTypeLabel": "sound",
                "rootActionIds": [3],
                "parentId": 9,
                "auxSends": {
                    "parserStatus": "typedExactV150NodeAuxParams",
                    "properties": [{
                        "propertyId": 0,
                        "propertyLabel": "Volume",
                        "rawU32": 0xC0C00000,
                        "rawHex": "0xc0c00000",
                        "floatValue": -6.0,
                    }, {
                        "propertyId": 0x0D,
                        "propertyLabel": "OutputBusVolume",
                        "rawU32": 0xC0400000,
                        "rawHex": "0xc0400000",
                        "floatValue": -3.0,
                    }],
                    "rangedProperties": [{
                        "propertyId": 0x02,
                        "propertyLabel": "LPF",
                        "minimumFloat": 0.0,
                        "maximumFloat": 1.0,
                        "minimumRawHex": "0x00000000",
                        "maximumRawHex": "0x3f800000",
                    }],
                },
            },
        })

        self.assertEqual(summary["authoredPropertyNodeCount"], 1)
        self.assertEqual(summary["authoredPropertyValueCount"], 2)
        self.assertEqual(summary["authoredRangedPropertyValueCount"], 1)
        self.assertEqual(summary["authoredPropertyCounts"], {
            "OutputBusVolume": 1,
            "Volume": 1,
        })
        self.assertEqual(summary["authoredRangedPropertyCounts"], {"LPF": 1})
        self.assertEqual(summary["propertyNodes"][0]["properties"][1]["propertyLabel"], "OutputBusVolume")

    def test_hirc_effect_definition_recovers_builtin_plugin_identity(self) -> None:
        data = pack("<II", 0x00690003, 4) + b"abcd" + b"tail"

        definition = build_audio.hirc_v150_effect_definition(17, data)

        self.assertIsNotNone(definition)
        self.assertEqual(definition["pluginTypeLabel"], "effect")
        self.assertEqual(definition["pluginId"], 105)
        self.assertEqual(definition["pluginName"], "Parametric EQ")
        self.assertEqual(definition["parameterByteLength"], 4)
        self.assertEqual(definition["trailingByteLength"], 4)

    def test_hirc_effect_definition_rejects_custom_source_plugin(self) -> None:
        data = pack("<II", 0x00650002, 12) + bytes(12)

        self.assertIsNone(build_audio.hirc_v150_effect_definition(17, data))

    def test_hirc_gain_parameters_decode_exact_shipped_layout(self) -> None:
        decoded = build_audio.decode_hirc_v150_effect_parameters(
            0x008B0003, pack("<ff", -6.0, -96.3)
        )

        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["parameterSchema"], "wwiseGainFxParamsV1")
        self.assertAlmostEqual(decoded["parameterValues"]["fullBandGainDb"], -6.0)
        self.assertAlmostEqual(decoded["parameterValues"]["lfeGainDb"], -96.3, places=3)

    def test_hirc_delay_parameters_decode_exact_shipped_layout(self) -> None:
        decoded = build_audio.decode_hirc_v150_effect_parameters(
            0x006A0003, pack("<ffffBB", 0.25, 15.0, 20.0, -3.0, 1, 0)
        )

        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["parameterValues"]["delayTimeSeconds"], 0.25)
        self.assertEqual(decoded["parameterValues"]["feedbackPercent"], 15.0)
        self.assertTrue(decoded["parameterValues"]["feedbackEnabled"])
        self.assertFalse(decoded["parameterValues"]["processLfe"])

    def test_hirc_dynamics_parameters_decode_shared_shipped_layout(self) -> None:
        payload = pack("<fffffBB", -24.0, 4.0, 0.02, 0.4, 3.0, 1, 1)
        compressor = build_audio.decode_hirc_v150_effect_parameters(
            0x006C0003, payload
        )
        expander = build_audio.decode_hirc_v150_effect_parameters(
            0x006D0003, payload
        )

        self.assertIsNotNone(compressor)
        self.assertIsNotNone(expander)
        self.assertEqual(compressor["parameterValues"], expander["parameterValues"])
        self.assertEqual(compressor["parameterValues"]["ratio"], 4.0)
        self.assertTrue(compressor["parameterValues"]["channelLink"])

    def test_hirc_parametric_eq_parameters_decode_three_packed_bands(self) -> None:
        payload = b"".join((
            pack("<IfffB", 4, -6.0, 120.0, 1.0, 1),
            pack("<IfffB", 6, 3.0, 1000.0, 0.7, 1),
            pack("<IfffB", 5, -2.0, 8000.0, 1.0, 0),
            pack("<fB", 1.5, 1),
        ))

        decoded = build_audio.decode_hirc_v150_effect_parameters(
            0x00690003, payload
        )

        self.assertIsNotNone(decoded)
        values = decoded["parameterValues"]
        self.assertEqual(len(payload), 56)
        self.assertEqual(values["bands"][0]["filterTypeLabel"], "Low Shelf")
        self.assertEqual(values["bands"][1]["filterTypeLabel"], "Peaking")
        self.assertFalse(values["bands"][2]["enabled"])
        self.assertEqual(values["outputGainDb"], 1.5)
        self.assertTrue(values["processLfe"])

    def test_hirc_meter_parameters_decode_mode_scope_and_output_rtpc(self) -> None:
        payload = pack(
            "<fffffBBBBI", 0.0, 0.1, -48.0, 0.0, 0.25,
            0, 1, 0, 1, 0x12345678,
        )

        decoded = build_audio.decode_hirc_v150_effect_parameters(
            0x00810003, payload
        )

        self.assertIsNotNone(decoded)
        values = decoded["parameterValues"]
        self.assertEqual(values["modeLabel"], "RMS")
        self.assertEqual(values["scopeLabel"], "Global")
        self.assertTrue(values["applyDownstreamVolume"])
        self.assertEqual(values["outputGameParameterIdHex"], "0x12345678")

    def test_hirc_pitch_shifter_parameters_decode_exact_shipped_layout(self) -> None:
        payload = (
            pack("<IfffBBfIfff", 0, -96.0, 0.0, 50.0, 1, 0,
                 -1200.0, 7, 2.5, 1800.0, 0.7)
        )

        decoded = build_audio.decode_hirc_v150_effect_parameters(
            0x00880003, payload
        )

        self.assertIsNotNone(decoded)
        self.assertEqual(len(payload), 38)
        self.assertEqual(decoded["parameterSchema"], "wwisePitchShifterFxParamsV1")
        values = decoded["parameterValues"]
        self.assertEqual(values["inputSelectionLabel"], "As Input")
        self.assertEqual(values["pitchShiftCents"], -1200.0)
        self.assertEqual(values["filterTypeLabel"], "Peaking")
        self.assertTrue(values["delayDry"])
        self.assertFalse(values["processLfe"])

    def test_hirc_harmonizer_parameters_decode_two_voice_blocks(self) -> None:
        payload = b"".join((
            pack("<BffIfff", 1, 700.0, -3.0, 0, 0.0, 1000.0, 1.0),
            pack("<BffIfff", 0, -1200.0, -6.0, 6, 2.0, 4000.0, 0.8),
            pack("<IffIBB", 0, -12.0, 1.5, 2048, 1, 1),
        ))

        decoded = build_audio.decode_hirc_v150_effect_parameters(
            0x008A0003, payload
        )

        self.assertIsNotNone(decoded)
        self.assertEqual(len(payload), 68)
        self.assertEqual(decoded["parameterSchema"], "wwiseHarmonizerFxParamsV1")
        values = decoded["parameterValues"]
        self.assertEqual(len(values["voices"]), 2)
        self.assertTrue(values["voices"][0]["enabled"])
        self.assertFalse(values["voices"][1]["enabled"])
        self.assertEqual(values["voices"][1]["filterTypeLabel"], "High Shelf")
        self.assertEqual(values["windowSizeSamples"], 2048)
        self.assertTrue(values["processLfe"])

    def test_hirc_stereo_delay_parameters_decode_exact_shipped_layout(self) -> None:
        payload = pack(
            "<IfffIfffIffffffBB",
            0, 0.9, -12.0, -13.9,
            0, 0.8, -12.0, -14.3,
            3, -8.0, 849.0, 1.0,
            0.0, 3.0, -100.0, 1, 1,
        )

        decoded = build_audio.decode_hirc_v150_effect_parameters(
            0x00870003, payload
        )

        self.assertIsNotNone(decoded)
        self.assertEqual(len(payload), 62)
        self.assertEqual(decoded["parameterSchema"], "wwiseStereoDelayFxParamsV1")
        values = decoded["parameterValues"]
        self.assertEqual(values["filterTypeLabel"], "Band Pass")
        self.assertAlmostEqual(values["leftDelayTimeSeconds"], 0.9, places=5)
        self.assertEqual(values["frontRearBalance"], -100.0)
        self.assertTrue(values["crossfeedEnabled"])
        self.assertTrue(values["feedbackEnabled"])

    def test_hirc_roomverb_parameters_decode_public_authoring_contract(self) -> None:
        payload = roomverb_parameter_data()

        decoded = build_audio.decode_hirc_v150_effect_parameters(
            0x00760003, payload
        )

        self.assertIsNotNone(decoded)
        self.assertEqual(len(payload), 186)
        self.assertEqual(decoded["parameterSchema"], "wwiseRoomVerbFxParamsV1")
        self.assertEqual(
            decoded["parameterBoundary"],
            "typedExactLayoutPartialAuthoredSemantics",
        )
        values = decoded["parameterValues"]
        self.assertEqual(values["earlyReflections"]["patternLabel"], "Large Room")
        self.assertEqual(values["earlyReflections"]["roomSizePercent"], 100.0)
        self.assertEqual(values["earlyReflections"]["rearDelayMilliseconds"], 40.0)
        self.assertEqual(values["reverb"]["preDelayMilliseconds"], 25.0)
        self.assertEqual(values["reverb"]["qualityReverberations"], 8)
        self.assertEqual(values["tone"]["bands"][1]["insertLabel"], "Reverb Only")
        self.assertEqual(values["tone"]["bands"][2]["curveLabel"], "High Shelf")
        self.assertEqual(values["outputLevelsDb"]["reverb"], -9.0)
        self.assertEqual(len(values["internalTuningParameters"]), 11)
        self.assertEqual(
            values["internalTuningParameters"][0]["semanticStatus"],
            "exactValueMeaningUnresolved",
        )
        self.assertEqual(
            values["internalTuningParameters"][0]["nativeUseRole"],
            "earlyReflectionTapPatternSynthesisInputs",
        )
        self.assertEqual(
            values["internalTuningParameters"][4]["nativeConsumerRvas"],
            ["0x00229b60"],
        )
        self.assertIn(
            "seeded per-tap variation",
            values["internalTuningParameters"][0]["nativeUseDetail"],
        )
        self.assertEqual(
            values["internalTuningParameters"][5]["nativeUseStatus"],
            "exactNativeReadBoundaryNoDirectReadObserved",
        )
        self.assertEqual(
            values["internalTuningParameters"][8]["nativeUseRole"],
            "sixChannelCoefficientDerivationInput",
        )
        self.assertEqual(
            values["internalTuningParameters"][10]["nativeConsumerRvas"],
            ["0x00229e20"],
        )
        self.assertIn(
            "secondary ER pattern",
            values["internalTuningParameters"][10]["nativeUseDetail"],
        )
        self.assertIn(
            "six coefficients",
            values["internalTuningParameters"][8]["nativeUseDetail"],
        )

    def test_hirc_roomverb_definition_preserves_partial_semantic_boundary(self) -> None:
        payload = roomverb_parameter_data()
        data = pack("<II", 0x00760003, len(payload)) + payload

        definition = build_audio.hirc_v150_effect_definition(17, data)

        self.assertIsNotNone(definition)
        self.assertEqual(
            definition["parameterBoundary"],
            "typedExactLayoutPartialAuthoredSemantics",
        )
        self.assertIn("IDs 100..110", definition["parameterSemanticBoundary"])

    def test_hirc_guitar_distortion_parameters_decode_full_public_contract(self) -> None:
        payload = guitar_distortion_parameter_data()

        decoded = build_audio.decode_hirc_v150_effect_parameters(
            0x007E0003, payload
        )

        self.assertIsNotNone(decoded)
        self.assertEqual(len(payload), 126)
        self.assertEqual(
            decoded["parameterSchema"], "wwiseGuitarDistortionFxParamsV1"
        )
        self.assertEqual(
            decoded["parameterBoundary"], "typedExactAuthoredBaseValues"
        )
        values = decoded["parameterValues"]
        self.assertEqual(values["distortionTypeLabel"], "Clip")
        self.assertEqual(values["drivePercent"], 61.0)
        self.assertEqual(values["tonePercent"], 50.0)
        self.assertEqual(values["rectificationPercent"], 0.0)
        self.assertEqual(values["outputGainDb"], 0.0)
        self.assertEqual(values["wetDryMixPercent"], 100.0)
        self.assertEqual(len(values["preDistortionEqBands"]), 3)
        self.assertEqual(len(values["postDistortionEqBands"]), 3)
        self.assertEqual(
            values["preDistortionEqBands"][2]["filterTypeLabel"], "Low Shelf"
        )
        self.assertTrue(values["preDistortionEqBands"][2]["enabled"])
        self.assertEqual(values["postDistortionEqBands"][2]["gainDb"], -13.0)

    def test_hirc_convolution_reverb_parameters_decode_public_runtime_contract(self) -> None:
        payload = convolution_reverb_parameter_data()

        decoded = build_audio.decode_hirc_v150_effect_parameters(
            0x007F0003, payload
        )

        self.assertIsNotNone(decoded)
        self.assertEqual(len(payload), 57)
        self.assertEqual(
            decoded["parameterSchema"], "wwiseConvolutionReverbFxParamsV1"
        )
        self.assertEqual(
            decoded["parameterBoundary"],
            "typedExactLayoutPartialAuthoredSemantics",
        )
        values = decoded["parameterValues"]
        self.assertEqual(values["reverbTypeLabel"], "Reverb")
        self.assertEqual(values["preDelayMilliseconds"], 30.0)
        self.assertEqual(values["outputSpreadDegrees"], 180.0)
        self.assertEqual(values["inputSpreadDegrees"], 0.0)
        self.assertEqual(values["reverbLevelsDb"]["center"], -9.0)
        self.assertEqual(values["outputLevelsDb"]["reverb"], 3.0)
        self.assertEqual(values["unresolvedParameters"][0]["setParamId"], 34)
        private_scalar = values["unresolvedParameters"][0]
        self.assertEqual(private_scalar["serializedOffset"], 52)
        self.assertEqual(private_scalar["nativeStructOffset"], 60)
        self.assertEqual(private_scalar["wrapperOffset"], 76)
        self.assertEqual(
            private_scalar["nativeUseRole"],
            "privateRuntimeScalarForwardedToConvolutionEngineProcess",
        )
        self.assertEqual(
            private_scalar["nativeUseStatus"],
            "exactForwardedScalarEngineReadUnobserved",
        )
        self.assertEqual(
            private_scalar["nativeConsumerRvas"],
            ["0x00254a83", "0x00254bd8", "0x00258520"],
        )
        self.assertIn(
            "fifth float",
            private_scalar["nativeUseDetail"],
        )
        private_byte = values["unresolvedParameters"][1]
        self.assertEqual(private_byte["serializedOffset"], 56)
        self.assertEqual(private_byte["nativeStructOffset"], 64)
        self.assertEqual(private_byte["wrapperOffset"], 80)
        self.assertEqual(
            private_byte["nativeUseRole"],
            "serializedByteForwardedToConvolutionRuntimeState",
        )
        self.assertEqual(
            private_byte["nativeConsumerRvas"], ["0x00254d27"]
        )
        self.assertIn(
            "runtime state +0x8c",
            private_byte["nativeUseDetail"],
        )
        self.assertEqual(values["unresolvedParameters"][1]["rawCode"], 2)

    def test_hirc_convolution_contract_pins_private_native_forwarding_boundary(self) -> None:
        contract = build_audio.HIRC_EFFECT_PARAMETER_CONTRACT["schemas"][0x007F0003]
        evidence = contract["privateTuningNativeEvidence"]
        self.assertEqual(
            evidence["status"],
            "exactForwardedPrivateFieldsPublicNamesUnresolved",
        )
        self.assertEqual(evidence["ranges"][0]["wrapperOffsets"], [76])
        self.assertEqual(evidence["ranges"][1]["wrapperOffsets"], [80])
        self.assertIn("does not read", evidence["ranges"][0]["evidenceBoundary"])

    def test_hirc_mastering_suite_parameters_decode_public_module_contract(self) -> None:
        payload = mastering_suite_parameter_data()

        decoded = build_audio.decode_hirc_v150_effect_parameters(
            0x00BA0003, payload
        )

        self.assertIsNotNone(decoded)
        self.assertEqual(len(payload), 304)
        self.assertEqual(
            decoded["parameterSchema"], "wwiseMasteringSuiteFxParamsV1"
        )
        self.assertEqual(
            decoded["parameterBoundary"],
            "typedExactLayoutPartialAuthoredSemantics",
        )
        values = decoded["parameterValues"]
        self.assertTrue(values["moduleEnabled"]["parametricEq"])
        self.assertFalse(values["moduleEnabled"]["masterVolume"])
        self.assertEqual(len(values["parametricEq"]["bands"]), 6)
        self.assertEqual(
            values["parametricEq"]["bands"][0]["filterModeLabel"],
            "High Pass Resonant (Two-Pole)",
        )
        compressor = values["multibandCompressor"]
        self.assertEqual(compressor["channelLinkModeLabel"], "All Channels")
        self.assertEqual(len(compressor["bands"]), 4)
        self.assertTrue(compressor["bands"][0]["enabled"])
        self.assertEqual(compressor["bands"][0]["thresholdDb"], -18.0)
        self.assertAlmostEqual(
            compressor["crossoverFrequenciesHz"][1], 503.9016, places=3
        )
        self.assertAlmostEqual(values["masterVolume"]["gainDb"], 3.6, places=5)
        self.assertEqual(len(values["masterVolume"]["channelGainsDb"]), 12)
        self.assertEqual(
            [row["serializedOffset"] for row in values["masterVolume"]["channelGainsDb"]],
            [235, 239, 243, 247, 251, 255, 259, 263, 267, 271, 275, 279],
        )
        self.assertEqual(
            [row["nativeStructOffset"] for row in values["masterVolume"]["channelGainsDb"]],
            [280, 284, 288, 292, 296, 300, 304, 308, 312, 316, 320, 324],
        )
        self.assertEqual(values["limiter"]["modeLabel"], "Advanced")
        self.assertTrue(values["limiter"]["linkChannels"])
        self.assertEqual(
            [row["setParamId"] for row in values["unresolvedParameters"]],
            [100, 200],
        )
        self.assertEqual(
            [row["nativeStructOffset"] for row in values["unresolvedParameters"]],
            [24, 136],
        )
        self.assertEqual(
            [row["nativeUseStatus"] for row in values["unresolvedParameters"]],
            [
                "nativeSetParamStorageOnlyNoDirectReadObserved",
                "nativeSetParamStorageOnlyNoDirectReadObserved",
            ],
        )
        self.assertEqual(
            [row["nativeConsumerRvas"] for row in values["unresolvedParameters"]],
            [[], []],
        )

    def test_hirc_mastering_suite_contract_pins_storage_only_private_native_boundary(self) -> None:
        contract = build_audio.HIRC_EFFECT_PARAMETER_CONTRACT["schemas"][0x00BA0003]
        evidence = contract["privateTuningNativeEvidence"]
        self.assertEqual(
            evidence["status"],
            "exactSetParamStorageOnlyPublicNamesUnresolved",
        )
        self.assertEqual(evidence["ranges"][0]["nativeStructOffsets"], [24])
        self.assertEqual(evidence["ranges"][1]["nativeStructOffsets"], [136])
        self.assertEqual(evidence["ranges"][0]["consumerRvas"], [])
        self.assertIn("No direct read", evidence["ranges"][0]["evidenceBoundary"])
        self.assertEqual(
            contract["channelGainNativeMapping"]["serializedOffsets"],
            [235, 239, 243, 247, 251, 255, 259, 263, 267, 271, 275, 279],
        )

    def test_hirc_convolution_reverb_definition_recovers_ir_media_dependency(self) -> None:
        payload = convolution_reverb_parameter_data()
        media_id = 0x2F3A77AB
        data = (
            pack("<II", 0x007F0003, len(payload))
            + payload
            + bytes([1, 0])
            + pack("<I", media_id)
            + b"after"
        )

        definition = build_audio.hirc_v150_effect_definition(17, data)

        self.assertIsNotNone(definition)
        self.assertEqual(definition["pluginMediaDependencyCount"], 1)
        self.assertEqual(definition["pluginMediaPrefixByteLength"], 6)
        self.assertEqual(definition["postPluginMediaTrailingByteLength"], 5)
        dependency = definition["pluginMediaDependencies"][0]
        self.assertEqual(dependency["pluginDataIndex"], 0)
        self.assertEqual(dependency["mediaId"], media_id)
        self.assertEqual(dependency["semanticRole"], "impulseResponseMedia")
        self.assertIn("not playable", definition["pluginMediaBoundary"])

    def test_hirc_plugin_media_dependency_prefix_fails_closed_when_truncated(self) -> None:
        truncated = bytes([2, 0]) + pack("<I", 0x2F3A77AB)

        self.assertIsNone(
            build_audio._hirc_v150_plugin_media_dependency_prefix(
                0x007F0003, truncated
            )
        )

    def test_hirc_effect_catalog_keeps_distinct_plugin_media_dependencies(self) -> None:
        payload = convolution_reverb_parameter_data()
        candidates = {}
        for media_id in (0x2F3A77AB, 0x0CB425ED):
            definition = build_audio.hirc_v150_effect_definition(
                17,
                pack("<II", 0x007F0003, len(payload))
                + payload
                + bytes([1, 0])
                + pack("<I", media_id),
            )
            self.assertIsNotNone(definition)
            build_audio.add_hirc_effect_definition_candidate(
                candidates, 1234, definition, bank_id=7
            )

        effects, _buses = build_audio.finalize_hirc_post_process_catalog(
            candidates, {}
        )

        self.assertEqual(
            effects[1234]["resolutionStatus"], "ambiguousPluginDefinitions"
        )
        self.assertEqual(effects[1234]["definitionCount"], 2)

    def test_hirc_matrix_reverb_parameters_decode_custom_delay_array(self) -> None:
        payload = (
            pack("<ffIfffBI", 3.0, 5.5, 8, -96.3, -35.0, 0.02, 1, 1)
            + pack("<8f", 13.62, 15.66, 17.52, 19.02, 20.83, 22.6, 24.05, 24.78)
        )

        decoded = build_audio.decode_hirc_v150_effect_parameters(
            0x00730003, payload
        )

        self.assertIsNotNone(decoded)
        values = decoded["parameterValues"]
        self.assertEqual(len(payload), 61)
        self.assertEqual(values["numberOfDelays"], 8)
        self.assertTrue(values["customDelayTimes"])
        self.assertEqual(len(values["delayTimesMilliseconds"]), 8)

    def test_hirc_effect_parameter_decoders_fail_closed_on_layout_drift(self) -> None:
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x006A0003, pack("<ffffBB", 0.5, 10.0, 50.0, 0.0, 2, 1)
        ))
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x00730003, pack("<ffIfffBI", 3.0, 5.5, 8, -96.3, -35.0, 0.0, 1, 1)
        ))
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x00880003,
            pack("<IfffBBfIfff", 99, -96.0, 0.0, 50.0, 1, 0,
                 0.0, 0, 0.0, 1000.0, 1.0),
        ))
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x008A0003,
            pack("<BffIfffBffIfffIffIBB", 1, 0.0, 0.0, 0, 0.0, 1000.0, 1.0,
                 0, 0.0, 0.0, 0, 0.0, 1000.0, 1.0,
                 0, 0.0, 0.0, 777, 0, 1),
        ))
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x00870003,
            pack("<IfffIfffIffffffBB", 0, 0.5, -12.0, -20.0,
                 0, 0.5, -12.0, -20.0, 0, 0.0, 1000.0, 1.0,
                 0.0, 0.0, -100.0, 2, 1),
        ))
        invalid_roomverb = bytearray(roomverb_parameter_data())
        pack_into("<I", invalid_roomverb, 81, 31)
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x00760003, bytes(invalid_roomverb)
        ))
        invalid_roomverb = bytearray(roomverb_parameter_data())
        pack_into("<I", invalid_roomverb, 110, 4)
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x00760003, bytes(invalid_roomverb)
        ))
        invalid_roomverb = bytearray(roomverb_parameter_data())
        invalid_roomverb[109] = 2
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x00760003, bytes(invalid_roomverb)
        ))
        invalid_convolution = bytearray(convolution_reverb_parameter_data())
        pack_into("<I", invalid_convolution, 48, 2)
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x007F0003, bytes(invalid_convolution)
        ))
        invalid_convolution = bytearray(convolution_reverb_parameter_data())
        pack_into("<f", invalid_convolution, 20, 181.0)
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x007F0003, bytes(invalid_convolution)
        ))
        invalid_convolution = bytearray(convolution_reverb_parameter_data())
        pack_into("<f", invalid_convolution, 12, 1.0)
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x007F0003, bytes(invalid_convolution)
        ))
        invalid_convolution = bytearray(convolution_reverb_parameter_data())
        pack_into("<f", invalid_convolution, 0, 1001.0)
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x007F0003, bytes(invalid_convolution)
        ))
        invalid_convolution = bytearray(convolution_reverb_parameter_data())
        pack_into("<f", invalid_convolution, 52, float("nan"))
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x007F0003, bytes(invalid_convolution)
        ))
        invalid_guitar = bytearray(guitar_distortion_parameter_data())
        pack_into("<I", invalid_guitar, 102, 5)
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x007E0003, bytes(invalid_guitar)
        ))
        invalid_mastering = bytearray(mastering_suite_parameter_data())
        invalid_mastering[2] = 2
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x00BA0003, bytes(invalid_mastering)
        ))
        invalid_mastering = bytearray(mastering_suite_parameter_data())
        pack_into("<I", invalid_mastering, 14, 8)
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x00BA0003, bytes(invalid_mastering)
        ))
        invalid_mastering = bytearray(mastering_suite_parameter_data())
        pack_into("<I", invalid_mastering, 114, 3)
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x00BA0003, bytes(invalid_mastering)
        ))
        invalid_mastering = bytearray(mastering_suite_parameter_data())
        pack_into("<I", invalid_mastering, 283, 3)
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x00BA0003, bytes(invalid_mastering)
        ))
        invalid_guitar = bytearray(guitar_distortion_parameter_data())
        pack_into("<f", invalid_guitar, 8, 19.0)
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x007E0003, bytes(invalid_guitar)
        ))
        invalid_guitar = bytearray(guitar_distortion_parameter_data())
        invalid_guitar[16] = 2
        self.assertIsNone(build_audio.decode_hirc_v150_effect_parameters(
            0x007E0003, bytes(invalid_guitar)
        ))

    def test_hirc_post_process_catalog_resolves_effect_and_audio_bus(self) -> None:
        effect_id = 956324002
        definition = build_audio.hirc_v150_effect_definition(
            17, pack("<II", 0x008B0003, 8) + bytes(8)
        )
        self.assertIsNotNone(definition)
        candidates = {}
        build_audio.add_hirc_effect_definition_candidate(
            candidates, effect_id, definition, bank_id=7
        )
        effects, buses = build_audio.finalize_hirc_post_process_catalog(
            candidates, {0xE611314A: build_audio.Counter({8: 2})}
        )
        summary = {
            "effectNodes": [{"effects": [{"effectId": effect_id}]}],
            "outputBuses": [{"busId": 0xE611314A, "nodeCount": 3}],
        }

        build_audio.resolve_hirc_post_process_summary(summary, effects, buses)

        slot = summary["effectNodes"][0]["effects"][0]
        self.assertEqual(slot["pluginName"], "Gain")
        self.assertEqual(slot["resolutionStatus"], "exactUniquePluginDefinition")
        self.assertEqual(slot["parameterSchema"], "wwiseGainFxParamsV1")
        self.assertIn("full band", slot["parameterSummary"])
        self.assertEqual(summary["decodedEffectParameterReferenceCount"], 1)
        self.assertEqual(summary["exactEffectParameterReferenceCount"], 1)
        self.assertEqual(summary["partialEffectParameterReferenceCount"], 0)
        self.assertEqual(
            summary["outputBuses"][0]["resolutionStatus"],
            "exactGlobalAudioBusDefinition",
        )

    def test_hirc_bus_processing_recovers_parent_and_nonempty_effect_slots(self) -> None:
        first_effect_id = 0x12345678
        second_effect_id = 0x87654321
        data = (
            pack("<I", 0x10203040)
            + bytes([0xAA, 0xBB, 0xCC])
            + bytes([2, 1])
            + bytes([0]) + pack("<I", first_effect_id) + bytes([2])
            + bytes([3]) + pack("<I", second_effect_id) + bytes([1])
            + bytes(5)
        )

        parsed = build_audio.hirc_v150_bus_processing(
            18, data, {first_effect_id, second_effect_id}
        )

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["parentBusId"], 0x10203040)
        self.assertEqual(
            parsed["effectParserStatus"],
            "exactCrossCorrelatedNonEmptyEffectChunk",
        )
        self.assertTrue(parsed["bypassAll"])
        self.assertEqual(
            [row["slotIndex"] for row in parsed["effects"]], [0, 3]
        )
        self.assertEqual(
            [row["effectId"] for row in parsed["effects"]],
            [first_effect_id, second_effect_id],
        )
        self.assertTrue(parsed["effects"][0]["effectShareSet"])
        self.assertFalse(parsed["effects"][0]["effectBypass"])
        self.assertTrue(parsed["effects"][1]["effectBypass"])
        self.assertFalse(parsed["effects"][1]["effectShareSet"])
        self.assertIsNone(parsed["effects"][0]["effectRendered"])

    def test_hirc_bus_processing_does_not_call_missing_chunk_empty(self) -> None:
        parsed = build_audio.hirc_v150_bus_processing(
            8, pack("<I", 0) + bytes(32), {0x12345678}
        )

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["parentBusId"], 0)
        self.assertEqual(parsed["effectParserStatus"], "nonEmptyEffectChunkNotLocated")
        self.assertIsNone(parsed["effectSlotCount"])
        self.assertEqual(parsed["effects"], [])

    def test_hirc_bus_processing_cross_correlates_explicit_zero_effect_chunk(self) -> None:
        effect_id = 0x12345678
        prefix = bytes([0xAA, 0xBB, 0xCC])
        suffix = bytes(5)
        non_empty = (
            pack("<I", 0x10203040)
            + prefix
            + bytes([1, 0, 0])
            + pack("<I", effect_id)
            + bytes([0])
            + suffix
        )
        empty = pack("<I", 0x50607080) + prefix + bytes([0]) + suffix
        schema = {
            "objectType": 18,
            "prefix": prefix,
            "suffix": suffix,
            "fingerprint": "test-schema",
            "siblingCount": 3,
        }

        parsed_non_empty = build_audio.hirc_v150_bus_processing(
            18, non_empty, {effect_id}
        )
        parsed_empty = build_audio.hirc_v150_bus_processing(
            18, empty, {effect_id}, empty_effect_schemas=(schema,)
        )

        self.assertEqual(
            parsed_non_empty["effectParserStatus"],
            "exactCrossCorrelatedNonEmptyEffectChunk",
        )
        self.assertEqual(
            parsed_empty["effectParserStatus"],
            "exactCrossCorrelatedEmptyEffectChunk",
        )
        self.assertEqual(parsed_empty["effectChunkOffset"], 7)
        self.assertEqual(parsed_empty["effectChunkByteLength"], 1)
        self.assertEqual(parsed_empty["effectSlotCount"], 0)
        self.assertEqual(parsed_empty["effects"], [])
        self.assertEqual(parsed_empty["emptyEffectSchemaFingerprint"], "test-schema")
        self.assertEqual(parsed_empty["emptyEffectSchemaSiblingCount"], 3)

    def test_hirc_bus_processing_consumes_typed_v150_bus_layout(self) -> None:
        effect_id = 0x12345678

        def bus_payload(effect_count: int) -> bytes:
            return (
                pack("<I", 0x10203040)  # OverrideBusId / DirectParentID
                + bytes([1, 0x1B])        # one AkPropID: HDR threshold
                + pack("<I", 0)
                + bytes([1, 0x15])        # positioning, Aux flags
                + pack("<I", 0)           # reflections Aux Bus
                + bytes([0])               # bus flags
                + pack("<H", 0)           # max instances
                + pack("<I", 0)           # channel config
                + bytes([2])               # bus state flags
                + pack("<i", 1000)        # recovery time
                + pack("<f", -96.0)       # max duck volume
                + pack("<I", 0)            # duck count
                + bytes([effect_count])
                + (
                    bytes([0])
                    + bytes([0])
                    + pack("<I", effect_id)
                    + bytes([2])
                    if effect_count
                    else b""
                )
                + bytes([0])               # metadata count
                + pack("<H", 1)             # one InitialRTPC curve
                + pack("<I", 0x11223344)   # RTPC ID
                + bytes([0, 0, 0x2B])       # type, accum, OutputBusVolume
                + pack("<I", 0x55667788)   # curve ID
                + bytes([2])                # decibel scaling
                + pack("<H", 1)             # one curve point
                + pack("<ffI", 0.0, 1.0, 4) # linear point
                + bytes([1, 0x2B, 2, 1])    # state prop: OutputBusVolume
                + bytes([1])                # one state group
                + pack("<I", 0x99AABBCC)   # group ID
                + bytes([0, 1])             # immediate, one state
                + pack("<I", 0xDDEEFF00)   # state ID
                + pack("<H", 1)             # one state value
                + pack("<Hf", 0x2B, -6.0)
            )

        parsed_non_empty = build_audio.hirc_v150_bus_processing(
            8, bus_payload(1), {effect_id}
        )
        parsed_empty = build_audio.hirc_v150_bus_processing(
            8, bus_payload(0), {effect_id}
        )

        self.assertEqual(
            parsed_non_empty["effectParserStatus"],
            "exactTypedV150NonEmptyEffectChunk",
        )
        self.assertEqual(parsed_non_empty["serializedBusParserStatus"],
                         "typedExactV150BusInitialValues")
        self.assertEqual(parsed_non_empty["effectChunkOffset"], 36)
        self.assertEqual(parsed_non_empty["serializedRecoveryTimeMs"], 1000)
        self.assertEqual(parsed_non_empty["serializedMaxDuckVolumeDb"], -96.0)
        state_rtpc = parsed_non_empty["serializedStateAndRtpc"]
        self.assertEqual(
            state_rtpc["parserStatus"],
            "typedExactV150BusInitialRtpcAndState",
        )
        self.assertEqual(state_rtpc["rtpcCurveCount"], 1)
        self.assertEqual(state_rtpc["rtpcPointCount"], 1)
        self.assertEqual(state_rtpc["rtpcCurves"][0]["parameterLabel"], "OutputBusVolume")
        self.assertEqual(state_rtpc["stateGroupCount"], 1)
        self.assertEqual(state_rtpc["stateValueCount"], 1)
        self.assertEqual(
            state_rtpc["stateGroups"][0]["states"][0]["values"][0]["value"],
            -6.0,
        )
        self.assertEqual(parsed_non_empty["effectSlotCount"], 1)
        self.assertEqual(
            parsed_empty["effectParserStatus"],
            "exactTypedV150EmptyEffectChunk",
        )
        self.assertEqual(parsed_empty["effectSlotCount"], 0)

    def test_hirc_bus_rtpc_state_suffix_fails_closed_on_truncation(self) -> None:
        parsed = build_audio._hirc_v150_bus_rtpc_state(bytes([0, 0, 1]), 0)

        self.assertEqual(parsed["parserStatus"], "failedClosed")
        self.assertIn("truncated", parsed["diagnostic"])

    def test_hirc_bus_catalog_resolves_parent_path_and_bus_effect_plugin(self) -> None:
        root_bus_id = 0x10203040
        aux_bus_id = 0x50607080
        empty_aux_bus_id = 0x50607081
        effect_id = 0x90A0B0C0
        definition = build_audio.hirc_v150_effect_definition(
            17, pack("<II", 0x008B0003, 8) + bytes(8)
        )
        self.assertIsNotNone(definition)
        effect_candidates = {}
        build_audio.add_hirc_effect_definition_candidate(
            effect_candidates, effect_id, definition, bank_id=7, bank_name="init.pck"
        )
        bus_candidates = {}
        build_audio.add_hirc_bus_definition_candidate(
            bus_candidates,
            root_bus_id,
            8,
            pack("<I", 0) + bytes(20),
            bank_id=7,
            bank_name="init.pck",
        )
        build_audio.add_hirc_bus_definition_candidate(
            bus_candidates,
            aux_bus_id,
            18,
            pack("<I", root_bus_id)
            + bytes([0xAA, 0xBB])
            + bytes([1, 0, 2])
            + pack("<I", effect_id)
            + bytes([2, 0, 0]),
            bank_id=7,
            bank_name="init.pck",
        )
        build_audio.add_hirc_bus_definition_candidate(
            bus_candidates,
            empty_aux_bus_id,
            18,
            pack("<I", root_bus_id)
            + bytes([0xAA, 0xBB])
            + bytes([0, 0, 0]),
            bank_id=7,
            bank_name="init.pck",
        )

        effects, buses = build_audio.finalize_hirc_post_process_catalog(
            effect_candidates,
            {
                root_bus_id: build_audio.Counter({8: 1}),
                aux_bus_id: build_audio.Counter({18: 1}),
                empty_aux_bus_id: build_audio.Counter({18: 1}),
            },
            bus_candidates,
        )
        path = build_audio.hirc_bus_parent_path(aux_bus_id, buses)

        self.assertEqual(
            buses[aux_bus_id]["resolutionStatus"],
            "exactGlobalAuxiliaryBusDefinition",
        )
        self.assertEqual(
            buses[aux_bus_id]["parentResolutionStatus"], "exactGlobalBusParent"
        )
        self.assertEqual(
            buses[empty_aux_bus_id]["effectParserStatus"],
            "exactCrossCorrelatedEmptyEffectChunk",
        )
        self.assertEqual(buses[empty_aux_bus_id]["effectSlotCount"], 0)
        self.assertEqual(
            build_audio.hirc_bus_parent_path(empty_aux_bus_id, buses)[
                "unresolvedBusProcessingIds"
            ],
            [root_bus_id],
        )
        self.assertEqual(buses[aux_bus_id]["effects"][0]["pluginName"], "Gain")
        self.assertEqual(
            buses[aux_bus_id]["effects"][0]["parameterValues"]["fullBandGainDb"],
            0.0,
        )
        self.assertEqual(path["busPathIds"], [aux_bus_id, root_bus_id])
        self.assertEqual(path["busPathResolutionStatus"], "exactGlobalBusParentPath")
        self.assertEqual(path["effectBusIds"], [aux_bus_id])
        self.assertEqual(path["unresolvedBusProcessingIds"], [root_bus_id])

        summary = {
            "effectNodes": [],
            "outputBuses": [],
            "auxiliaryBuses": [{
                "sendKind": "userDefined",
                "busId": aux_bus_id,
                "referenceCount": 2,
            }],
        }
        build_audio.resolve_hirc_post_process_summary(summary, effects, buses)
        send = summary["auxiliaryBuses"][0]
        self.assertEqual(
            send["resolutionStatus"], "exactGlobalAuxiliaryBusDefinition"
        )
        self.assertEqual(send["busPathIds"], [aux_bus_id, root_bus_id])
        self.assertEqual(send["effectBusIds"], [aux_bus_id])
        self.assertEqual(
            summary["auxiliaryBusResolutionCounts"],
            {"exactGlobalAuxiliaryBusDefinition": 2},
        )

    def test_hirc_post_process_catalog_counts_roomverb_as_partial_semantics(self) -> None:
        effect_id = 704228860
        payload = roomverb_parameter_data()
        definition = build_audio.hirc_v150_effect_definition(
            17, pack("<II", 0x00760003, len(payload)) + payload
        )
        self.assertIsNotNone(definition)
        candidates = {}
        build_audio.add_hirc_effect_definition_candidate(
            candidates, effect_id, definition, bank_id=7
        )
        effects, buses = build_audio.finalize_hirc_post_process_catalog(
            candidates, {}
        )
        summary = {
            "effectNodes": [{"effects": [{"effectId": effect_id}]}],
            "outputBuses": [],
        }

        build_audio.resolve_hirc_post_process_summary(summary, effects, buses)

        slot = summary["effectNodes"][0]["effects"][0]
        self.assertEqual(slot["pluginName"], "RoomVerb")
        self.assertIn("IDs 100..110", slot["parameterSemanticBoundary"])
        self.assertEqual(summary["decodedEffectParameterReferenceCount"], 1)
        self.assertEqual(summary["exactEffectParameterReferenceCount"], 0)
        self.assertEqual(summary["partialEffectParameterReferenceCount"], 1)

    def test_hirc_post_process_catalog_prefers_exact_bank_package_definition(self) -> None:
        effect_id = 479364165
        candidates = {}
        for bank_name, payload in (("base.pck", b"first"), ("patch.pck", b"other")):
            definition = build_audio.hirc_v150_effect_definition(
                17, pack("<II", 0x00690003, len(payload)) + payload
            )
            self.assertIsNotNone(definition)
            build_audio.add_hirc_effect_definition_candidate(
                candidates,
                effect_id,
                definition,
                bank_id=7,
                bank_name=bank_name,
            )
        effects, buses = build_audio.finalize_hirc_post_process_catalog(
            candidates, {}
        )
        summary = {
            "effectNodes": [{"effects": [{"effectId": effect_id}]}],
            "outputBuses": [],
        }

        build_audio.resolve_hirc_post_process_summary(
            summary, effects, buses, bank_id=7, bank_name="base.pck"
        )

        slot = summary["effectNodes"][0]["effects"][0]
        self.assertEqual(slot["pluginName"], "Parametric EQ")
        self.assertEqual(
            slot["resolutionStatus"],
            "exactSameBankPackagePluginDefinition",
        )

    def test_hirc_container_parent_decodes_variable_fx_prefix(self) -> None:
        parent_id = 386813193
        # NodeBase: override FX, one authored effect row, metadata header,
        # override-bus id, then DirectParentID.
        data = (
            bytes([1, 1, 0, 4])
            + pack("<I", 0)
            + bytes([0, 0, 0])
            + pack("<II", 0, parent_id)
            + bytes(32)
        )

        self.assertEqual(build_audio.hirc_object_parent_id(9, data), parent_id)

    def test_variable_fx_parent_restores_exact_sequence_layer_event_graph(self) -> None:
        event_id = 0x8A88723C
        container_id = 386813193
        variable_layer_id = 144808260
        ordinary_layer_id = 337304808
        media_by_sound = {
            369109803: (205675749, variable_layer_id),
            723059349: (748608357, variable_layer_id),
            414986928: (475840163, ordinary_layer_id),
            716252337: (594611880, ordinary_layer_id),
        }
        objects = {
            event_id: {"type": 4, "data": bytes.fromhex("01102ef12d")},
            770780688: {"type": 3, "data": bytes.fromhex("0304094d0e17000000043c72888a1e000000")},
            container_id: {"type": 5, "data": bytes.fromhex(
                "0000000000000000e553d01a0001080000c0c20000086d580507000000000000000000000000000000000001000000000000000001000000000000007a440000000000000000010000000112020000004499a108e8dc1a1402004499a10850c30000e8dc1a1450c30000"
            )},
            variable_layer_id: {"type": 9, "data": bytes.fromhex(
                "010100000000000004000000000000094d0e17000400020308000070c10000c041000074420000c0c20000086d580507000000000000000000000000000000000d010200000000000000020000002b2b00169502192b0000000000"
            )},
            ordinary_layer_id: {"type": 9, "data": bytes.fromhex(
                "0000000000000000094d0e170004000203080000b0c10000c041000018420000c0c20000086d580507000000000000000000000000000000000001000000000000000002000000b032bc18b124b12a0000000000"
            )},
        }
        for sound_id, (media_id, parent_id) in media_by_sound.items():
            objects[sound_id] = {
                "type": 2,
                "data": sound_source_data(media_id, parent_id),
            }

        result = build_audio.traverse_hirc_event(
            event_id, objects, {row[0] for row in media_by_sound.values()}, bank_version=150
        )

        self.assertEqual(set(result["mediaIds"]), {205675749, 748608357, 475840163, 594611880})
        self.assertEqual(result["unresolvedNodes"], [])
        self.assertEqual(
            {(row["objectId"], row["edgeKind"]) for row in result["containerEvidence"]},
            {(container_id, "sequenceItem"), (variable_layer_id, "layerChild"), (ordinary_layer_id, "layerChild")},
        )

    def test_link_conversation_audio_marks_exact_story_line_purpose_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            conv_dir = Path(raw_root)
            conv_path = conv_dir / "dlg_fixture.json"
            conv_path.write_text(json.dumps({
                "lines": [{"id": "line_1", "audioId": "au_dlg_fixture"}],
            }), encoding="utf-8")
            entry = {"id": "au_dlg_fixture", "src": "/audio/fixture.flac"}

            stats = build_audio.link_conversation_audio(
                conv_dir, {"au_dlg_fixture": entry}
            )

            self.assertEqual(stats["lineAudioLinked"], 1)
            self.assertEqual(entry["storyLineBindingCount"], 1)
            self.assertEqual(entry["purposeKnowledgeStatus"], "exactStoryLineBinding")

    def test_numeric_audio_entries_recovers_occurrence_key_only_media(self) -> None:
        surviving = {
            "id": "1040066173",
            "storageRoot": "shared",
            "rel": "wwise/voice_events/1040066173.flac",
        }
        entries = build_audio.numeric_audio_entries_by_media_id({
            "1040066173@shared:wwise/voice_events/1040066173.flac": surviving,
            "955778167792087661": {
                "id": "955778167792087661",
                "storageRoot": "CN",
                "rel": "wwise/unknown/955778167792087661.flac",
            },
        })

        self.assertEqual(entries, {1040066173: surviving})

    def test_event_media_inventory_fingerprint_ignores_uint64_external_ids(self) -> None:
        base = {"1": {"id": "1", "storageRoot": "shared", "rel": "wwise/sfx/1.flac", "bytes": 3}}
        with_external = {**base, "external": {
            "id": "955778167792087661", "storageRoot": "CN",
            "rel": "wwise/unknown/955778167792087661.flac", "bytes": 5,
        }}
        self.assertEqual(
            build_audio.event_media_inventory_fingerprint(base),
            build_audio.event_media_inventory_fingerprint(with_external),
        )

    def test_audio_dialog_external_media_id_matches_game_path_hash(self) -> None:
        self.assertEqual(
            build_audio.audio_dialog_external_media_id(
                "v1d4/Narrating/HS_Part04/c35m3/au_dlg_c35m3_12_025.wem",
                "chinese",
            ),
            10012020101098562764,
        )

    def test_collect_hirc_decoded_sound_definitions_keeps_exact_orphan_object(self) -> None:
        objects = {
            10: {"type": 2, "data": sound_source_data(30151934, 20)},
            11: {"type": 2, "data": sound_source_data(999, 20)},
            20: {"type": 5, "data": b""},
        }

        rows = build_audio.collect_hirc_decoded_sound_definitions(
            objects,
            {30151934},
            bank_name="default_banks.pck",
            bank_id=7,
            bank_version=150,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["mediaId"], 30151934)
        self.assertEqual(rows[0]["soundObjectId"], 10)
        self.assertEqual(rows[0]["parentObjectId"], 20)
        self.assertEqual(rows[0]["parentObjectType"], 5)
        self.assertEqual(rows[0]["evidence"], "exactTypedWwiseSoundCodecMediaObject")

    def test_suppress_redundant_unknown_audio_occurrences_drops_identical_copy(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            audio_root = Path(raw_root)
            unknown_path = audio_root / "shared/wwise/unknown/1.flac"
            resolved_path = audio_root / "shared/wwise/sfx/1.flac"
            unknown_path.parent.mkdir(parents=True)
            resolved_path.parent.mkdir(parents=True)
            unknown_path.write_bytes(b"same decoded media")
            resolved_path.write_bytes(b"same decoded media")
            generic = {
                "1": {
                    "id": "1", "storageRoot": "shared", "rel": "wwise/sfx/1.flac",
                    "bytes": resolved_path.stat().st_size, "audioCategory": "sfx",
                },
                "1@shared:wwise/unknown/1.flac": {
                    "id": "1", "storageRoot": "shared", "rel": "wwise/unknown/1.flac",
                    "bytes": unknown_path.stat().st_size, "audioCategory": "unknown",
                },
            }

            stats = build_audio.suppress_redundant_unknown_audio_occurrences(
                audio_root, generic, {}, "CN"
            )

            self.assertEqual(stats["contentIdenticalDuplicateOccurrencesCompared"], 1)
            self.assertEqual(stats["contentIdenticalUnknownOccurrencesSuppressed"], 1)
            self.assertEqual(list(generic), ["1"])
            self.assertTrue(unknown_path.is_file())

    def test_suppress_redundant_unknown_audio_occurrences_preserves_different_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            audio_root = Path(raw_root)
            unknown_path = audio_root / "shared/wwise/unknown/2.flac"
            resolved_path = audio_root / "shared/wwise/sfx/2.flac"
            unknown_path.parent.mkdir(parents=True)
            resolved_path.parent.mkdir(parents=True)
            unknown_path.write_bytes(b"unknown collision")
            resolved_path.write_bytes(b"resolved collision")
            generic = {
                "2": {
                    "id": "2", "storageRoot": "shared", "rel": "wwise/sfx/2.flac",
                    "bytes": resolved_path.stat().st_size, "audioCategory": "sfx",
                },
                "2@shared:wwise/unknown/2.flac": {
                    "id": "2", "storageRoot": "shared", "rel": "wwise/unknown/2.flac",
                    "bytes": unknown_path.stat().st_size, "audioCategory": "unknown",
                },
            }

            stats = build_audio.suppress_redundant_unknown_audio_occurrences(
                audio_root, generic, {}, "CN"
            )

            self.assertEqual(stats["contentIdenticalUnknownOccurrencesSuppressed"], 0)
            self.assertEqual(len(generic), 2)

    def test_suppress_redundant_unknown_audio_occurrences_preserves_cross_storage_rows(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            audio_root = Path(raw_root)
            shared_path = audio_root / "shared/wwise/sfx/3.flac"
            language_path = audio_root / "CN/wwise/unknown/3.flac"
            shared_path.parent.mkdir(parents=True)
            language_path.parent.mkdir(parents=True)
            shared_path.write_bytes(b"same id and bytes")
            language_path.write_bytes(b"same id and bytes")
            generic = {
                "3@shared": {
                    "id": "3", "storageRoot": "shared", "rel": "wwise/sfx/3.flac",
                    "bytes": shared_path.stat().st_size, "audioCategory": "sfx",
                },
                "3@CN": {
                    "id": "3", "storageRoot": "CN", "rel": "wwise/unknown/3.flac",
                    "bytes": language_path.stat().st_size, "audioCategory": "unknown",
                },
            }

            stats = build_audio.suppress_redundant_unknown_audio_occurrences(
                audio_root, generic, {}, "CN"
            )

            self.assertEqual(stats["contentIdenticalDuplicateOccurrencesCompared"], 0)
            self.assertEqual(stats["contentIdenticalUnknownOccurrencesSuppressed"], 0)
            self.assertEqual(len(generic), 2)

    def test_suppress_redundant_audio_dialog_external_path_copy(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            audio_root = Path(raw_root)
            dialog_path = "v1d4/Narrating/HS_Part04/c35m3/au_dlg_fixture.wem"
            external_id = build_audio.audio_dialog_external_media_id(dialog_path, "chinese")
            unknown_path = audio_root / f"CN/wwise/unknown/{external_id}.flac"
            dialog_file = audio_root / "CN/voice/story/hongshan/au_dlg_fixture.flac"
            unknown_path.parent.mkdir(parents=True)
            dialog_file.parent.mkdir(parents=True)
            unknown_path.write_bytes(b"same external voice bytes")
            dialog_file.write_bytes(b"same external voice bytes")
            generic = {str(external_id): {
                "id": str(external_id),
                "storageRoot": "CN",
                "rel": f"wwise/unknown/{external_id}.flac",
                "bytes": unknown_path.stat().st_size,
                "audioCategory": "unknown",
            }}
            dialog = {"au_dlg_fixture": {
                "id": "au_dlg_fixture",
                "storageRoot": "CN",
                "rel": "voice/story/hongshan/au_dlg_fixture.flac",
                "bytes": dialog_file.stat().st_size,
                "audioDialogPath": dialog_path,
            }}

            stats = build_audio.suppress_redundant_unknown_audio_occurrences(
                audio_root, generic, dialog, "CN"
            )

            self.assertEqual(stats["audioDialogExternalCopiesCompared"], 1)
            self.assertEqual(stats["audioDialogExternalCopiesSuppressed"], 1)
            self.assertEqual(generic, {})
            self.assertTrue(unknown_path.is_file())

    def test_suppress_redundant_audio_dialog_external_copy_requires_exact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            audio_root = Path(raw_root)
            dialog_path = "v1d4/Narrating/HS_Part04/c35m3/au_dlg_fixture.wem"
            external_id = build_audio.audio_dialog_external_media_id(dialog_path, "chinese")
            unknown_path = audio_root / f"CN/wwise/unknown/{external_id}.flac"
            dialog_file = audio_root / "CN/voice/story/hongshan/au_dlg_fixture.flac"
            unknown_path.parent.mkdir(parents=True)
            dialog_file.parent.mkdir(parents=True)
            unknown_path.write_bytes(b"external bytes A")
            dialog_file.write_bytes(b"external bytes B")
            generic = {str(external_id): {
                "id": str(external_id), "storageRoot": "CN",
                "rel": f"wwise/unknown/{external_id}.flac", "bytes": 16,
                "audioCategory": "unknown", "sourceBank": "external",
            }}
            dialog = {"au_dlg_fixture": {
                "id": "au_dlg_fixture", "storageRoot": "CN",
                "rel": "voice/story/hongshan/au_dlg_fixture.flac", "bytes": 16,
                "audioDialogPath": dialog_path,
            }}

            stats = build_audio.suppress_redundant_unknown_audio_occurrences(
                audio_root, generic, dialog, "CN"
            )

            self.assertEqual(stats["audioDialogExternalCopiesCompared"], 1)
            self.assertEqual(stats["audioDialogExternalCopiesSuppressed"], 0)
            self.assertEqual(len(generic), 1)

    def test_orphan_external_media_identity_recovers_name_without_trigger(self) -> None:
        external_id = 955778167792087661
        generic = {str(external_id): {
            "id": str(external_id),
            "storageRoot": "CN",
            "rel": f"wwise/unknown/{external_id}.flac",
            "bytes": 1,
            "audioCategory": "unknown",
            "sourceBank": "external",
        }}

        stats = build_audio.suppress_redundant_unknown_audio_occurrences(
            Path("unused"), generic, {}, "CN"
        )

        self.assertEqual(stats["recoveredOrphanExternalMediaIdentities"], 1)
        self.assertEqual(generic[str(external_id)]["externalAuthoredAudioId"], "au_voice_c35m3_3_001")
        self.assertEqual(
            generic[str(external_id)]["identityOnlyPlaybackPlacementStatus"],
            "identityOnlyNoCurrentAudioDialogOrTrigger",
        )
        self.assertEqual(generic[str(external_id)]["audioCategory"], "story_voice")

    def test_audio_dialog_path_recovers_only_exact_current_wwise_event_alias(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            first = root / "StreamingAssets/AudioDialog.json"
            second = root / "Persistent/AudioDialog.json"
            first.parent.mkdir(parents=True)
            second.parent.mkdir(parents=True)
            exact_name = "eny_fixture_combat_taunt_sv"
            exact_hash = build_audio.audio_hash_generator_compute(exact_name)
            signed_hash = exact_hash if exact_hash < (1 << 31) else exact_hash - (1 << 32)
            payload = {
                str(signed_hash): {
                    "path": exact_name,
                    "codec": 4,
                    "speakerChannel": "eny_fixture",
                    "voType": 2,
                },
                "123": {"path": "external_only_voice"},
            }
            first.write_text(json.dumps(payload), encoding="utf-8")
            second.write_text(json.dumps(payload), encoding="utf-8")

            rows = build_audio.collect_audio_dialog_wwise_event_aliases(
                [first, second],
                [{"eventHash": exact_hash}, {"eventHash": 123}],
            )

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["name"], exact_name)
            self.assertEqual(rows[0]["voiceId"], signed_hash)
            self.assertEqual(rows[0]["eventHash"], exact_hash)
            self.assertEqual(len(rows[0]["sources"]), 2)
            self.assertEqual(
                rows[0]["evidence"],
                "audioDialogPathHashEqualsVoiceIdAndWwiseEventId",
            )

    def test_voice_table_event_aliases_accept_only_typed_current_wwise_fields(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            names = {
                "defaultWwiseEvent": "vo_fixture_default",
                "narratingWwiseEvent": "vo_fixture_narrating",
                "radioWwiseEvent": "vo_fixture_radio",
                "overrideWwiseEvent": "vo_fixture_override",
                "eventTemplate": "vo_fixture_response_{0}",
            }
            payloads = {
                "AudioDialogConfigs.json": {"config": {
                    "defaultWwiseEvent": names["defaultWwiseEvent"],
                    "unrelated": "vo_fixture_unrelated",
                }},
                "AudioDialogChannel.json": {"channel": {
                    "narratingWwiseEvent": names["narratingWwiseEvent"],
                    "radioWwiseEvent": names["radioWwiseEvent"],
                }},
                "AudioDialog.json": {"voice": {
                    "overrideWwiseEvent": names["overrideWwiseEvent"],
                }},
                "ResponsiveTriggers.json": {"trigger": {
                    "eventTemplate": names["eventTemplate"],
                    "nested": {"eventTemplate": "not_in_current_inventory"},
                }},
            }
            for source in ("StreamingAssets", "Persistent"):
                table_root = export_root / "structured" / source / "Table"
                table_root.mkdir(parents=True)
                for filename, payload in payloads.items():
                    (table_root / filename).write_text(json.dumps(payload), encoding="utf-8")
            event_names = list(names.values()) + ["vo_fixture_unrelated"]
            inventory = [{"eventHash": build_audio.audio_hash_generator_compute(name)} for name in event_names]

            rows = build_audio.collect_voice_table_wwise_event_aliases(export_root, inventory)

            self.assertEqual({row["name"] for row in rows}, set(names.values()))
            narrating = next(row for row in rows if row["name"] == names["narratingWwiseEvent"])
            self.assertEqual(narrating["usages"][0]["routeKind"], "narratingChannelEvent")
            self.assertEqual(narrating["usages"][0]["occurrenceCount"], 1)
            self.assertEqual(len(narrating["usages"][0]["sources"]), 2)
            self.assertEqual(
                narrating["evidence"],
                "typedVoiceTableEventFieldHashEqualsCurrentWwiseEventId",
            )

    def test_voice_table_event_alias_conflicts_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            table_root = export_root / "structured/StreamingAssets/Table"
            table_root.mkdir(parents=True)
            (table_root / "AudioDialogChannel.json").write_text(json.dumps({
                "channel": {
                    "narratingWwiseEvent": "vo_fixture_a",
                    "radioWwiseEvent": "vo_fixture_b",
                }
            }), encoding="utf-8")
            with mock.patch.object(build_audio, "audio_hash_generator_compute", return_value=123):
                rows = build_audio.collect_voice_table_wwise_event_aliases(
                    export_root,
                    [{"eventHash": 123}],
                )
            self.assertEqual(rows, [])

    def test_typed_ui_table_aliases_require_whitelisted_consumer_fields(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            table_root = export_root / "structured/StreamingAssets/Table"
            table_root.mkdir(parents=True)
            accepted = {
                "audioOnOpen": "Au_UI_Menu_Test_Open",
                "videoAudioKey": "Au_UI_Menu_Test_Video",
            }
            (table_root / "ActivityStaminaRefundBgStateTable.json").write_text(json.dumps({
                "activity": {
                    "audioOnOpen": accepted["audioOnOpen"],
                    "unrelated": "Au_UI_Menu_Unrelated",
                }
            }), encoding="utf-8")
            (table_root / "GachaCharPoolTable.json").write_text(json.dumps({
                "pool": {"videoAudioKey": accepted["videoAudioKey"]}
            }), encoding="utf-8")
            inventory = [{"eventHash": build_audio.audio_hash_generator_compute(name)} for name in (
                *accepted.values(), "Au_UI_Menu_Unrelated",
            )]

            rows = build_audio.collect_typed_ui_table_wwise_event_aliases(export_root, inventory)

            self.assertEqual({row["name"] for row in rows}, set(accepted.values()))
            video = next(row for row in rows if row["name"] == accepted["videoAudioKey"])
            self.assertEqual(video["usages"][0]["routeKind"], "uiVideoAudioEvent")
            self.assertIn("VideoPlayer.PlayAudio", video["usages"][0]["runtimeRoute"])
            self.assertTrue(video["usages"][0]["consumerEvidence"])
            self.assertEqual(
                video["evidence"],
                "typedTableGetterAndLuaAudioConsumerHashEqualsCurrentWwiseEventId",
            )

    def test_sns_voice_aliases_require_voice_content_and_first_parameter(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            table_root = export_root / "structured/StreamingAssets/Table"
            table_root.mkdir(parents=True)
            accepted = "Au_UI_Event_SNS_Fixture_Voice"
            rejected = "Au_UI_Event_SNS_Fixture_Image"
            (table_root / "SNSDialogTable.json").write_text(json.dumps({
                "dialog_fixture": {
                    "dialogId": "dialog_fixture",
                    "dialogContentData": {
                        "1": {"contentId": 1, "contentType": 5, "contentParam": [accepted, "4"], "speaker": "fixture"},
                        "2": {"contentId": 2, "contentType": 2, "contentParam": [rejected]},
                    },
                },
            }), encoding="utf-8")
            inventory = [{"eventHash": build_audio.audio_hash_generator_compute(name)} for name in (accepted, rejected)]

            rows = build_audio.collect_sns_voice_wwise_event_aliases(export_root, inventory)

            self.assertEqual([row["name"] for row in rows], [accepted])
            usage = rows[0]["usages"][0]
            self.assertEqual(usage["contentTypeName"], "Voice")
            self.assertEqual(usage["contentParamIndex"], 0)
            self.assertEqual(usage["durationSeconds"], "4")

    def test_skill_id_dictionary_alias_is_identity_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            accepted = "eny_fixture_skill_audio_identity"
            rejected = "eny_fixture_missing_skill_data"
            for source_root in ("StreamingAssets", "Persistent"):
                table_root = export_root / "structured" / source_root / "Table"
                table_root.mkdir(parents=True)
                (table_root / "NumIdStrTable.json").write_text(json.dumps({
                    "skill_id": {"dic": {"7": accepted, "8": rejected}},
                }), encoding="utf-8")
                skill_root = export_root / "structured" / source_root / "Data/Json/SkillData"
                skill_root.mkdir(parents=True)
                (skill_root / f"{accepted}.json").write_bytes(b"fixture-skill-data")
            inventory = [{"eventHash": build_audio.audio_hash_generator_compute(name)} for name in (accepted, rejected)]

            rows = build_audio.collect_skill_id_dictionary_wwise_event_aliases(export_root, inventory)

            self.assertEqual([row["name"] for row in rows], [accepted])
            self.assertEqual(rows[0]["dictionaryKind"], "skill_id")
            self.assertEqual(rows[0]["numericSkillIds"], ["7"])
            self.assertEqual(rows[0]["playbackPlacementStatus"], "identityOnlyNoAudioConsumer")

    def test_lua_audio_references_separate_events_rtpc_cues_and_literals(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            path = root / "Data/LuaScripts/Test.lua"
            path.parent.mkdir(parents=True)
            path.write_text(
                '\n'.join((
                    'AudioAdapter.PostEvent(flag and "Au_UI_Test_A" or "au_ui_test_b")',
                    'AudioAdapter.SetRtpc("au_rtpc_test", value)',
                    'AudioManager.PostAudioCue("au_cue_test")',
                    'local fallback = "au_ui_indirect"',
                )),
                encoding="utf-8",
            )

            rows = build_audio.collect_lua_audio_references(root)

            self.assertEqual(len(rows), 5)
            self.assertEqual(
                {row["kind"] for row in rows},
                {"luaPostEvent", "luaRtpcParameter", "luaAudioCue", "luaAudioLiteral"},
            )
            post_names = {row["name"] for row in rows if row["kind"] == "luaPostEvent"}
            self.assertEqual(post_names, {"au_ui_test_a", "au_ui_test_b"})
            for row in rows:
                self.assertEqual(row["hash"], build_audio.fnv1_32(row["name"]))

    def test_lua_audio_references_keep_source_root_and_selected_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            selected = root / "Data/Selected.lua"
            skipped = root / "Data/Skipped.lua"
            selected.parent.mkdir(parents=True)
            selected.write_text('AudioAdapter.PostEvent("au_ui_selected")', encoding="utf-8")
            skipped.write_text('AudioAdapter.PostEvent("au_ui_skipped")', encoding="utf-8")

            rows = build_audio.collect_lua_audio_references(
                root,
                "Persistent",
                {"Data/Selected.lua"},
            )

            self.assertEqual([row["name"] for row in rows], ["au_ui_selected"])
            self.assertEqual(
                rows[0]["source"],
                "structured/Persistent/Lua/Data/Selected.lua",
            )

    def test_event_bank_filter_includes_named_banks_and_hotfix_pcks(self) -> None:
        import re

        pattern = re.compile(build_audio.EVENT_BANK_FILE_REGEX, re.IGNORECASE)
        self.assertTrue(pattern.search("Data/Audio/PCK/Windows/Main/default_banks.pck"))
        self.assertTrue(pattern.search("Data/Audio/PCK/Windows/Hotfix/hotfix_main.pck"))
        self.assertFalse(pattern.search("Data/Audio/PCK/Windows/Main/default_media.pck"))

    def test_event_bank_stream_enumerates_streaming_and_persistent_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            cli = root / "AnimeStudio.CLI.exe"
            streaming = root / "StreamingAssets"
            persistent = root / "Persistent"
            cli.write_bytes(b"")
            streaming.mkdir()
            persistent.mkdir()
            calls = []

            def run(command, **kwargs):
                calls.append(command)
                source = Path(command[command.index("--streaming-assets") + 1]).name
                data = b"streaming-bank" if source == "StreamingAssets" else b"persistent-hotfix"
                row = {
                    "blockType": "audio" if source == "StreamingAssets" else "hotfix-audio",
                    "fileName": "default_banks.pck" if source == "StreamingAssets" else "hotfix_main.pck",
                    "dataBase64": base64.b64encode(data).decode("ascii"),
                }
                return mock.Mock(stdout=json.dumps(row), stderr="")

            args = argparse.Namespace(
                audio_dumper=cli,
                streaming_assets=streaming,
                fallback_assets=persistent,
            )
            with mock.patch.object(build_audio.subprocess, "run", side_effect=run):
                payloads = build_audio.event_bank_payloads_from_vfs(args)

            self.assertEqual(len(calls), 2)
            self.assertEqual({Path(call[call.index("--streaming-assets") + 1]).name for call in calls}, {"StreamingAssets", "Persistent"})
            self.assertEqual({Path(name).name for name, _ in payloads}, {"default_banks.pck", "hotfix_main.pck"})

    def test_current_interactive_audio_union_tag_and_complete_rows(self) -> None:
        from scripts.game_data.memorypack import interactive as memorypack_interactive

        def string(value: str) -> bytes:
            raw = value.encode("utf-8")
            return pack("<I", len(raw)) + raw

        body = b"".join([
            pack("<I", 0),
            bytes([13]),
            pack("<I", 1),
            pack("<iI", 13, 1),
            string("au_int_fixture_break"),
            pack("<I", 1),
            bytes([3]),
            string("au_int_fixture_open"),
            string("panel_open"),
            string("Open panel"),
            bytes([1] + [0] * 10),
        ])

        self.assertEqual(memorypack_interactive.INTERACTIVE_AUDIO_COMPONENT_TAG, 0x005D)
        self.assertEqual(
            memorypack_interactive.BASE_COMPONENT_UNION_TAGS[0x005D],
            "Core_InteractiveAudioData",
        )
        decoded, end = memorypack_interactive.parse_interactive_audio_component(body, 0, 2)
        self.assertEqual(end, len(body))
        self.assertEqual(decoded["audioRows"][0]["stateName"], "Destroy")
        self.assertEqual(decoded["audioRows"][0]["events"], ["au_int_fixture_break"])
        self.assertEqual(decoded["customRows"][0]["name"], "panel_open")

    def test_current_interactive_model_union_tag_is_0x0126(self) -> None:
        from scripts.game_data.memorypack import interactive as memorypack_interactive

        self.assertEqual(
            memorypack_interactive.BASE_COMPONENT_UNION_TAGS[0x0126],
            "View_InteractiveModelComponentData",
        )

    def test_current_interactive_trigger_zone_audio_property_map_is_exact(self) -> None:
        from scripts.game_data.memorypack import interactive as memorypack_interactive

        def string(value: str) -> bytes:
            raw = value.encode("utf-8")
            return pack("<I", len(raw)) + raw

        event_id = "au_int_fixture_start"
        property_map = b"".join((
            pack("<I", 1),
            bytes((2,)),
            string("audio_key_start"),
            bytes((2,)),
            pack("<iI", 7, 1),
            bytes((2,)),
            pack("<q", 0),
            string(event_id),
        ))
        body = b"".join((
            pack("<I", 0xFFFFFFFF),
            pack("<I", 1),
            bytes((20,)),
            bytes(60),
            property_map,
            bytes((0, 0)),
        ))

        decoded, end = memorypack_interactive.parse_interactive_trigger_zone_audio_property_component(
            body,
            0,
            3,
        )

        self.assertEqual(end, len(body) - 2)
        self.assertEqual(decoded["tag"], "0x00f5")
        self.assertEqual(decoded["type"], "Core_TriggerZoneComponentForIntData")
        self.assertEqual(decoded["audioPropertyRows"], [{
            "key": "audio_key_start",
            "events": [event_id],
            "valueType": 7,
            "identityKind": "wwiseEvent",
        }])
        self.assertEqual(decoded["runtimePropertyConsumerStatus"], "unresolved")
        self.assertEqual(decoded["runtimeEventPostingStatus"], "notObserved")

        found = memorypack_interactive.find_interactive_audio_property_maps(body)
        self.assertEqual(found[0]["audioPropertyRows"][0]["events"], [event_id])
        self.assertEqual(found[0]["componentResolutionStatus"], "containingComponentUnresolved")

    def test_interactive_template_config_audio_property_has_exact_field_boundary(self) -> None:
        from scripts.game_data.memorypack import interactive as memorypack_interactive

        def string(value: str) -> bytes:
            raw = value.encode("utf-8")
            return pack("<I", len(raw)) + raw

        event_id = "au_int_fixture_escape"
        config_map = b"".join((
            pack("<I", 2),
            bytes((2,)), string("audio_escape"),
            bytes((2,)), pack("<iI", 7, 1), bytes((2,)), pack("<q", 0), string(event_id),
            bytes((2,)), string("label"),
            bytes((2,)), pack("<iI", 28, 1), bytes((2,)), pack("<q", 0), string("lang_fixture"),
        ))
        tail = b"".join((
            pack("<ff", 0.0, 0.0), bytes((0,)), pack("<f", 1.0), bytes((0,)),
            pack("<I", 0), pack("<I", 0), pack("<i", 0), config_map,
        ))

        decoded, end = memorypack_interactive.parse_interactive_template_config_properties(
            tail, 0
        )

        self.assertEqual(end, len(tail))
        self.assertEqual(decoded["configPropertyCount"], 2)
        self.assertEqual(decoded["audioPropertyRows"], [{
            "key": "audio_escape",
            "events": [event_id],
            "valueType": 7,
            "identityKind": "wwiseEvent",
        }])
        self.assertEqual(decoded["configPropertiesOffset"], "0x1a")

    def test_current_play_sound_union_tag_matches_binary_formatter_audit(self) -> None:
        from scripts.game_data.memorypack import buff as memorypack_buff

        self.assertEqual(memorypack_buff.BUFF_PLAY_SOUND_ACTION_TAG, 0x010D)
        self.assertEqual(
            memorypack_buff.BUFF_ABILITY_ACTION_TAG_NAMES[0x010D],
            "Core_PlaySoundAction_PlaySoundActionData",
        )
        self.assertEqual(memorypack_buff.BUFF_ABILITY_ACTION_TAG_MEMBER_COUNTS[0x010D], 22)

    def test_play_sound_target_settings_uses_typed_memorypack_reader_when_exact(self) -> None:
        from scripts.game_data.memorypack import buff as memorypack_buff

        # Real CN BuffData PlaySoundActionData payloads: the 67-byte default
        # TargetSettings and the 79-byte smart_target variant.  The latter
        # proves the variable string slot and exact nested SelectorData end.
        base = b"".join((
            bytes((13, 8, 1, 0)), pack("<i", 0), bytes((0, 0xFF)), pack("<i", 0),
            bytes((0xFF,)), pack("<i", 0),
            pack("<I", 0), bytes((0,)), pack("<i", 0), bytes((0,)),
            pack("<I", 0),
            bytes((3, 0xFF)), pack("<II", 0, 0),
            pack("<iiii", 0, 1, 0, 0), pack("<I", 0), pack("<i", 4),
        ))
        self.assertEqual(len(base), 67)
        raw = base[:59] + pack("<I", 12) + b"smart_target" + base[63:]
        decoded, end = memorypack_buff.read_buff_target_settings_full_or_partial(
            raw, 0, len(raw), "fixture.targetSettings"
        )

        self.assertEqual(end, len(raw))
        self.assertEqual(decoded["status"], "exact")
        self.assertEqual(decoded["semanticStatus"], "exact-target-settings-selector-data")
        self.assertEqual(decoded["targetGroupKey"], "smart_target")
        self.assertEqual(decoded["targetSource"], 4)
        self.assertEqual(decoded["selectorOwner"], 1)
        self.assertEqual(decoded["selectorData"], {
            "finderData": None,
            "postProcessorData": [],
            "validatorData": [],
        })

    def test_play_sound_target_settings_rejects_unknown_tail_fail_closed(self) -> None:
        from scripts.game_data.memorypack import buff as memorypack_buff

        raw = bytearray(b"".join((
            bytes((13, 8, 1, 0)), pack("<i", 0), bytes((0, 0xFF)), pack("<i", 0),
            bytes((0xFF,)), pack("<i", 0),
            pack("<I", 0), bytes((0,)), pack("<i", 0), bytes((0,)),
            pack("<I", 0),
            bytes((3, 0xFF)), pack("<II", 0, 0),
            pack("<iiii", 0, 1, 0, 0), pack("<I", 0), pack("<i", 4),
        )))
        self.assertEqual(len(raw), 67)
        # Keep the byte layout valid but use an unrecognized candidate tail.
        raw[-4:] = (99).to_bytes(4, "little")
        with self.assertRaises(ValueError):
            memorypack_buff.read_buff_target_settings_full_or_partial(
                bytes(raw), 0, len(raw), "fixture.targetSettings"
            )

    def test_collects_and_merges_decoded_buff_play_sound_actions(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            sources = [
                "structured/StreamingAssets/Data/Json/BuffData/buff_timed.json",
                "structured/Persistent/Data/Json/BuffData/buff_timed.json",
            ]
            for source in sources:
                path = export_root / source
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"fixture")
            decoded = [(
                {
                    "index": 2,
                    "startFrame": 17,
                    "endFrame": 34,
                },
                {
                    "onlyExecuteWhenSourceIsGuard": False,
                    "onlyExecuteWhenSourceIsMainChar": True,
                },
                {
                    "soundEvent": "au_test_timed",
                    "prefix": {"isEnable": True, "serverActionIndex": 9},
                    "stopOnEnd": True,
                    "stopFadeDurationMs": 300,
                    "targetSettingsEnvelopePartial": {
                        "semanticStatus": "partial-target-settings-envelope-opaque",
                        "shape": "string-slot",
                        "stringSlotValue": "smart_target",
                    },
                },
            )]
            result = build_audio.collect_buff_play_sound_actions(
                export_root,
                {"buff_timed": {"sources": set(sources)}},
                decoder=lambda *_args: decoded,
            )

            rows = result["byBuffEvent"]["buff_timed"]["au_test_timed"]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["startFrame"], 17)
            self.assertEqual(rows[0]["endFrame"], 34)
            self.assertTrue(rows[0]["onlyExecuteWhenSourceIsMainChar"])
            self.assertTrue(rows[0]["stopOnEnd"])
            self.assertEqual(rows[0]["targetSelector"], "smart_target")
            self.assertEqual(rows[0]["sourcePaths"], sources[::-1])
            self.assertEqual(result["counts"]["buffPlaySoundActionOccurrences"], 1)

    def test_audio_cli_has_one_flac_output_contract(self) -> None:
        args = build_audio.parse_args([])
        for removed_option in (
            "format", "audio_format", "ffmpeg", "audio_conversion_jobs",
        ):
            self.assertFalse(hasattr(args, removed_option))
        self.assertEqual(build_audio.AUDIO_OUTPUT_FORMAT, "flac")
        for option, value in (
            ("--format", "wav"),
            ("--audio-format", "wem"),
            ("--ffmpeg", "ffmpeg.exe"),
            ("--fluffy", "fluffy.exe"),
            ("--audio-conversion-jobs", "4"),
        ):
            with self.subTest(option=option), mock.patch("sys.stderr"), self.assertRaises(SystemExit):
                build_audio.parse_args([option, value])
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            build_audio.parse_args(["--refresh-hirc"])
        refreshed = build_audio.parse_args(["--skip-decode", "--refresh-hirc"])
        self.assertTrue(refreshed.skip_decode)
        self.assertTrue(refreshed.refresh_hirc)

    def test_dialog_path_uses_requested_browser_extension(self) -> None:
        self.assertEqual(
            build_audio.audio_rel_for_dialog_path("v1d3/line.wem", ".flac"),
            "voice/other/line.flac",
        )

    def test_voice_categories_keep_useful_story_detail(self) -> None:
        self.assertEqual(
            build_audio.audio_category_for_rel("voice/story/main_episodes/line.wav"),
            ("story_voice", "main_episodes"),
        )
        self.assertEqual(
            build_audio.audio_category_for_rel("voice/characters/avywen/line.wav"),
            ("character_voice", "avywen"),
        )

    def test_event_category_handles_voice_alias(self) -> None:
        self.assertEqual(build_audio.event_audio_category("au_voice_test"), "au_vo")
        self.assertEqual(
            build_audio.audio_category_for_rel("wwise/unknown/1.wav", "au_music"),
            ("music", ""),
        )

    def test_combined_decode_retains_shared_bank_provenance(self) -> None:
        self.assertEqual(
            build_audio.combined_decode_source_block(
                "shared", "CN", "unmapped/initial/123.wav"
            ),
            "initial-audio",
        )
        self.assertEqual(
            build_audio.combined_decode_source_block("CN", "CN", "voice/line.wav"),
            "voice",
        )

    def test_hirc_summary_keeps_raw_types_and_marks_runtime_selectors(self) -> None:
        counts, labels, selectors = build_audio.summarize_hirc_object_types(
            {
                1: {"type": 4},
                2: {"type": 3},
                3: {"type": 6},
                4: {"type": 99},
            },
            {1, 2, 3, 4, 5},
        )
        self.assertEqual(counts, {"3": 1, "4": 1, "6": 1, "99": 1})
        self.assertEqual(labels["6"], "switchContainer")
        self.assertEqual(labels["99"], "type99")
        self.assertEqual(selectors, [6])

    def test_v150_play_action_decodes_properties_ranges_and_exact_tail(self) -> None:
        data = b"".join([
            pack("<HI", 0x0403, 1234),
            bytes([0x01]),
            bytes([4, 0x39, 0x3A, 0x3B, 0x7F]),
            pack("<ii", 350, 500),
            pack("<f", 25.0),
            b"\x01\x02\x03\x04",
            bytes([2, 0x39, 0x3B]),
            pack("<ii", -25, 50),
            pack("<ff", 5.0, 10.0),
            bytes([0xA6]),
            pack("<II", 9876, 30),
        ])

        result = build_audio.hirc_v150_playback_action(data, 150)

        self.assertEqual(result["actionParserStatus"], "typedExactV150")
        self.assertEqual(result["targetFlagsRaw"], 1)
        self.assertTrue(result["targetIsBus"])
        self.assertEqual(
            [row["propertyName"] for row in result["properties"]],
            ["delayTime", "transitionTime", "probability", "property0x7f"],
        )
        self.assertEqual(result["properties"][0]["value"], 350)
        self.assertEqual(result["properties"][1]["value"], 500)
        self.assertAlmostEqual(result["properties"][2]["value"], 25.0)
        self.assertEqual(result["properties"][3]["encoding"], "rawUnion32")
        self.assertEqual(result["properties"][3]["rawHex"], "01020304")
        self.assertNotIn("value", result["properties"][3])
        self.assertEqual(result["delay"], {
            "serializationStatus": "explicitBaseAndRange",
            "baseValuesMs": [350],
            "modifierRangesMs": [{"minimum": -25, "maximum": 50}],
            "runtimeSelection": "boundedModifierUnresolved",
        })
        self.assertEqual(result["transition"]["baseValuesMs"], [500])
        self.assertEqual(result["probability"]["baseValuesPercent"], [25.0])
        self.assertEqual(
            result["probability"]["modifierRangesPercent"],
            [{"minimum": 5.0, "maximum": 10.0}],
        )
        self.assertEqual(result["probability"]["runtimeSelection"], "actionGateNotEvaluated")
        self.assertEqual(result["fade"], {
            "flagsRaw": 0xA6,
            "curveId": 6,
            "curveLabel": "Exp1",
            "bankId": 9876,
            "bankType": 30,
            "bankTypeLabel": "Event",
        })

    def test_v150_play_event_accepts_zero_tail_and_rejects_extra_bytes(self) -> None:
        data = b"".join([
            pack("<HI", 0x2103, 1234),
            bytes([0]),
            bytes([1, 0x39]),
            pack("<i", 100),
            bytes([0]),
        ])

        result = build_audio.hirc_v150_playback_action(data, 150)
        self.assertEqual(result["actionParserStatus"], "typedExactV150")
        self.assertEqual(result["delay"]["baseValuesMs"], [100])
        self.assertNotIn("fade", result)

        failed = build_audio.hirc_v150_playback_action(data + b"\x00", 150)
        self.assertEqual(failed["actionParserStatus"], "failedClosed")
        self.assertEqual(
            failed["actionParserFailure"]["reason"],
            "unexpectedPlayEventTrailingBytes",
        )
        self.assertNotIn("delay", failed)

    def test_v150_control_actions_decode_state_switch_and_game_parameter_tails(self) -> None:
        state = b"".join([
            pack("<HI", 0x1204, 1234),
            bytes([0, 0, 0]),
            pack("<II", 0x11223344, 0x55667788),
        ])
        state_result = build_audio.hirc_v150_control_action(state, 150)
        self.assertEqual(state_result["actionControlParserStatus"], "typedExactV150")
        self.assertEqual(state_result["groupIdHex"], "0x11223344")
        self.assertEqual(state_result["stateIdHex"], "0x55667788")

        switch = b"".join([
            pack("<HI", 0x1901, 1234),
            bytes([0, 0, 0]),
            pack("<II", 0x01020304, 0x05060708),
        ])
        switch_result = build_audio.hirc_v150_control_action(switch, 150)
        self.assertEqual(switch_result["actionControlParserStatus"], "typedExactV150")
        self.assertEqual(switch_result["groupIdHex"], "0x01020304")
        self.assertEqual(switch_result["switchIdHex"], "0x05060708")

        game_parameter = b"".join([
            pack("<HI", 0x1302, 1234),
            bytes([0, 0, 0]),
            bytes([0x04, 0x01, 0x02]),
            pack("<fff", 1.5, -2.0, 3.25),
            bytes([0]),
        ])
        game_parameter_result = build_audio.hirc_v150_control_action(game_parameter, 150)
        self.assertEqual(game_parameter_result["actionControlParserStatus"], "typedExactV150")
        self.assertEqual(game_parameter_result["fadeCurveId"], 4)
        self.assertTrue(game_parameter_result["bypassTransition"])
        self.assertEqual(game_parameter_result["valueMeaningLabel"], "offset")
        self.assertEqual(game_parameter_result["valueRange"]["base"], 1.5)
        self.assertEqual(game_parameter_result["exceptions"], [])

    def test_v150_control_actions_decode_active_flags_and_fail_closed(self) -> None:
        stop = b"".join([
            pack("<HI", 0x0103, 1234),
            bytes([0, 0, 0]),
            bytes([0x06, 0x06]),
            bytes([0]),
        ])
        result = build_audio.hirc_v150_control_action(stop, 150)
        self.assertEqual(result["actionControlParserStatus"], "typedExactV150")
        self.assertTrue(result["applyToStateTransitions"])
        self.assertTrue(result["applyToDynamicSequence"])
        self.assertEqual(result["exceptions"], [])

        failed = build_audio.hirc_v150_control_action(stop[:-1], 150)
        self.assertEqual(failed["actionControlParserStatus"], "failedClosed")
        self.assertEqual(failed["actionControlParserFailure"]["reason"], "truncatedExceptionCount")
        self.assertNotIn("actionControlEvidenceBoundary", failed)

    def test_v150_playback_action_failures_are_bounded_and_claim_no_timing(self) -> None:
        valid_empty_play = b"".join([
            pack("<HI", 0x0403, 1234),
            bytes([0, 0, 0, 4]),
            pack("<II", 123, 30),
        ])
        cases = {
            "unsupportedBankVersion": (valid_empty_play, 154),
            "truncatedActionHeader": (pack("<HI", 0x0403, 1234), 150),
            "truncatedScalarPropertyIds": (
                pack("<HI", 0x0403, 1234) + bytes([0, 2, 0x39]),
                150,
            ),
            "truncatedScalarPropertyValues": (
                pack("<HI", 0x0403, 1234) + bytes([0, 1, 0x39, 1, 2]),
                150,
            ),
            "truncatedRangePropertyValues": (
                pack("<HI", 0x0403, 1234)
                + bytes([0, 0, 1, 0x39])
                + pack("<i", 1),
                150,
            ),
            "truncatedPlayTail": (valid_empty_play[:-1], 150),
            "unexpectedPlayTrailingBytes": (valid_empty_play + b"\x00", 150),
        }
        for reason, (data, version) in cases.items():
            with self.subTest(reason=reason):
                result = build_audio.hirc_v150_playback_action(data, version)
                self.assertEqual(result["actionParserStatus"], "failedClosed")
                self.assertEqual(result["actionParserFailure"]["reason"], reason)
                self.assertGreaterEqual(result["actionParserFailure"]["remainingBytes"], 0)
                self.assertNotIn("properties", result)
                self.assertNotIn("delay", result)

    def test_action_dispatch_preserves_ordinals_and_classifies_timing_conservatively(self) -> None:
        def play(target_id: int, delay_ms: int | None = None) -> bytes:
            property_bundle = bytes([0])
            if delay_ms is not None:
                property_bundle = bytes([1, 0x39]) + pack("<i", delay_ms)
            return b"".join([
                pack("<HI", 0x0403, target_id),
                bytes([0]),
                property_bundle,
                bytes([0, 4]),
                pack("<II", 99, 30),
            ])

        sound = sound_source_data(777)
        objects = {
            1: {"type": 4, "data": bytes([2]) + pack("<II", 2, 3)},
            2: {"type": 3, "data": play(4)},
            3: {"type": 3, "data": play(4)},
            4: {"type": 2, "data": sound},
        }

        result = build_audio.traverse_hirc_event(1, objects, {777}, bank_version=150)
        self.assertEqual(result["mediaIds"], [777])
        self.assertEqual(
            [row["eventActionOrdinal"] for row in result["actionEvidence"]],
            [0, 1],
        )
        self.assertEqual(
            [row["dispatchEventId"] for row in result["actionEvidence"]],
            [1, 1],
        )
        self.assertEqual(
            result["actionDispatchEvidence"]["timingClass"],
            "coDispatchNoExplicitDelay",
        )
        self.assertEqual(result["actionDispatchEvidence"]["typedPlaybackActionCount"], 2)
        self.assertEqual(result["actionDispatchEvidence"]["failedPlaybackActionCount"], 0)
        self.assertTrue(result["actionDispatchEvidence"]["simultaneityCandidate"])
        self.assertEqual(result["actionEvidence"][0]["serializedPathIds"], [1, 2])
        self.assertEqual(
            result["actionEvidence"][0]["serializedPathTypeLabels"],
            ["event", "action"],
        )
        self.assertEqual(result["actionEvidence"][0]["targetTypeLabel"], "sound")
        self.assertEqual(result["actionEvidence"][0]["serializedPathRelations"], [])

        objects[3] = {"type": 3, "data": play(4, 350)}
        staggered = build_audio.traverse_hirc_event(1, objects, {777}, bank_version=150)
        self.assertEqual(staggered["mediaIds"], [777])
        self.assertEqual(
            staggered["actionDispatchEvidence"]["timingClass"],
            "coDispatchWithAuthoredDelayDifference",
        )
        self.assertFalse(staggered["actionDispatchEvidence"]["simultaneityCandidate"])
        self.assertEqual(staggered["actionDispatchEvidence"]["explicitDelayActionCount"], 1)

    def test_failed_action_evidence_does_not_change_target_reachability(self) -> None:
        sound = sound_source_data(777)
        objects = {
            1: {"type": 4, "data": bytes([1]) + pack("<I", 2)},
            # The legacy typed target prefix is valid, but the evidence bundle is truncated.
            2: {"type": 3, "data": pack("<HI", 0x0403, 3)},
            3: {"type": 2, "data": sound},
        }

        result = build_audio.traverse_hirc_event(1, objects, {777}, bank_version=150)
        self.assertEqual(result["mediaIds"], [777])
        self.assertEqual(result["traversalStatus"], "complete")
        self.assertEqual(result["actionDispatchEvidence"]["failedPlaybackActionCount"], 1)
        self.assertTrue(result["actionEvidence"][0]["traversed"])
        self.assertEqual(result["actionEvidence"][0]["actionParserStatus"], "failedClosed")
        self.assertEqual(
            result["actionEvidence"][0]["actionParserFailure"]["reason"],
            "truncatedActionHeader",
        )

    def test_typed_hirc_traversal_uses_reciprocal_children_and_sound_source(self) -> None:
        event_id = 100
        play_action = 101
        stop_action = 102
        container_id = 200
        sound_a = 301
        sound_b = 302
        unrelated_sound = 303

        event_data = bytes([2]) + pack("<II", play_action, stop_action)
        play_data = pack("<HI", 0x0403, container_id)
        stop_data = pack("<HI", 0x0103, unrelated_sound)
        children_offset = 40
        container_data = bytearray(children_offset - 24)
        container_data[8:12] = pack("<I", 999)
        # Incidental object/media-looking integers are not typed child edges.
        container_data[12:16] = pack("<I", unrelated_sound)
        container_data.extend(pack("<HHHfffHBBBB", 1, 0, 0, 0.0, 0.0, 0.0, 1, 0, 0, 0, 0x12))
        container_data.extend(pack("<III", 2, sound_a, sound_b))
        container_data.extend(pack("<H", 2))
        container_data.extend(pack("<II", sound_b, 50000))
        container_data.extend(pack("<II", sound_a, 25000))

        def sound_data(media_id: int, parent_id: int) -> bytes:
            return sound_source_data(media_id, parent_id)

        objects = {
            event_id: {"type": 4, "data": event_data},
            play_action: {"type": 3, "data": play_data},
            stop_action: {"type": 3, "data": stop_data},
            container_id: {"type": 5, "data": bytes(container_data)},
            sound_a: {"type": 2, "data": sound_data(401, container_id)},
            sound_b: {"type": 2, "data": sound_data(402, container_id)},
            unrelated_sound: {"type": 2, "data": sound_data(499, 777)},
        }

        result = build_audio.traverse_hirc_event(
            event_id, objects, {401, 402, 499}, bank_version=150
        )
        self.assertTrue(objects[sound_a]["_typedParentIdParsed"])
        self.assertEqual(objects[sound_a]["_typedParentId"], container_id)
        self.assertEqual(result["mediaIds"], [401, 402])
        self.assertEqual(result["rootPlayActionCount"], 1)
        self.assertEqual(result["rootStopActionCount"], 1)
        self.assertEqual(result["containerEvidence"][0]["childrenOffset"], children_offset)
        self.assertEqual(result["containerEvidence"][0]["modeLabel"], "random")
        self.assertEqual(
            result["containerEvidence"][0]["selectorParserStatus"],
            "typedExactV150PlaylistWeights",
        )
        self.assertEqual(
            result["containerEvidence"][0]["playlistChildOrder"],
            [sound_b, sound_a],
        )
        self.assertFalse(result["containerEvidence"][0]["childrenOrderMatchesPlaylist"])
        self.assertEqual(result["containerEvidence"][0]["nonDefaultWeightCount"], 1)
        self.assertEqual(result["containerEvidence"][0]["flagLabels"], [
            "resetPlaylistAtEachPlay", "global",
        ])
        self.assertEqual(
            {tuple(row["relationTypes"]) for row in result["mediaEvidence"]},
            {("randomAlternative",)},
        )
        self.assertNotIn(unrelated_sound, result["visitedObjectIds"])

    def test_state_and_game_parameter_actions_are_control_only(self) -> None:
        objects = {
            1: {"type": 4, "data": bytes([2]) + pack("<II", 2, 3)},
            2: {"type": 3, "data": pack("<HI", 0x1204, 100)},
            3: {"type": 3, "data": pack("<HI", 0x1402, 200)},
        }
        result = build_audio.traverse_hirc_event(1, objects, set(), bank_version=150)
        self.assertEqual(
            [row["operation"] for row in result["actionEvidence"]],
            ["setState", "resetGameParameter"],
        )
        self.assertEqual(result["rootPlayActionCount"], 0)
        self.assertEqual(result["mediaIds"], [])
        self.assertTrue(all(not row["traversed"] for row in result["actionEvidence"]))

    def test_named_v150_control_action_operations_are_not_playback_edges(self) -> None:
        operation_types = [0x0203, 0x0303, 0x0602, 0x0702, 0x1302, 0x1902, 0x1B02]
        objects = {
            1: {"type": 4, "data": bytes([len(operation_types)]) + b"".join(
                pack("<I", index + 2) for index in range(len(operation_types))
            )},
            **{
                index + 2: {"type": 3, "data": pack("<HI", action_type, 100 + index)}
                for index, action_type in enumerate(operation_types)
            },
        }

        result = build_audio.traverse_hirc_event(1, objects, set(), bank_version=150)

        self.assertEqual(
            [row["operation"] for row in result["actionEvidence"]],
            ["pause", "resume", "mute", "unmute", "setGameParameter", "setSwitch", "trigger"],
        )
        self.assertEqual(result["rootPlayActionCount"], 0)
        self.assertTrue(all(not row["traversed"] for row in result["actionEvidence"]))

    def test_v150_random_sequence_policy_preserves_playlist_order_weights_and_fail_closed_tail(self) -> None:
        children_offset = 24
        child_ids = [10, 20, 30]
        data = bytearray()
        data.extend(pack(
            "<HHHfffHBBBB",
            2, 1, 3, 125.0, 25.0, 50.0, 4, 3, 1, 1, 0x1A,
        ))
        data.extend(pack("<I", len(child_ids)))
        data.extend(b"".join(pack("<I", child_id) for child_id in child_ids))
        data.extend(pack("<H", len(child_ids)))
        for child_id, weight in ((30, 50000), (10, 25000), (20, 75000)):
            data.extend(pack("<II", child_id, weight))

        policy = build_audio.hirc_v150_random_sequence_properties(
            bytes(data), children_offset, child_ids, bank_version=150
        )

        self.assertEqual(policy["selectorParserStatus"], "typedExactV150PlaylistWeights")
        self.assertEqual(policy["modeLabel"], "sequence")
        self.assertEqual(policy["randomModeLabel"], "shuffle")
        self.assertEqual(policy["transitionModeLabel"], "delay")
        self.assertEqual(policy["playlistChildOrder"], [30, 10, 20])
        self.assertEqual(policy["playlistMembershipStatus"], "playlistCoversOwnedChildren")
        self.assertEqual(policy["duplicatePlaylistItemCount"], 0)
        self.assertEqual(policy["ownedChildIdsNotInPlaylist"], [])
        self.assertFalse(policy["childrenOrderMatchesPlaylist"])
        self.assertEqual(policy["loopCount"], 2)
        self.assertEqual(policy["avoidRepeatCount"], 4)
        self.assertEqual(policy["nonDefaultWeightCount"], 2)
        self.assertFalse(policy["uniformWeights"])
        self.assertNotIn("usesWeight", policy["flagLabels"])

        truncated = build_audio.hirc_v150_random_sequence_properties(
            bytes(data[:-8]), children_offset, child_ids, bank_version=150
        )
        self.assertEqual(
            truncated["selectorParserStatus"],
            "unresolvedV150RandomSequenceTail",
        )
        self.assertEqual(truncated["selectorParserFailureReason"], "unexpectedPlaylistTailLength")
        self.assertEqual(truncated["modeLabel"], "sequence")

        repeated = bytearray(data[:children_offset + 4 + len(child_ids) * 4])
        repeated.extend(pack("<H", 2))
        repeated.extend(pack("<II", 10, 50000))
        repeated.extend(pack("<II", 10, 25000))
        repeated_policy = build_audio.hirc_v150_random_sequence_properties(
            bytes(repeated), children_offset, child_ids, bank_version=150
        )
        self.assertEqual(
            repeated_policy["selectorParserStatus"],
            "typedExactV150PlaylistWeights",
        )
        self.assertEqual(
            repeated_policy["playlistMembershipStatus"],
            "playlistWithRepeatedOwnedChildren",
        )
        self.assertEqual(repeated_policy["duplicatePlaylistItemCount"], 1)
        self.assertEqual(repeated_policy["ownedChildIdsNotInPlaylist"], [20, 30])

        empty = bytearray(data[:children_offset + 4 + len(child_ids) * 4])
        empty.extend(pack("<H", 0))
        empty_policy = build_audio.hirc_v150_random_sequence_properties(
            bytes(empty), children_offset, child_ids, bank_version=150
        )
        self.assertEqual(
            empty_policy["playlistMembershipStatus"],
            "emptyPlaylistOwnedChildrenPreserved",
        )
        self.assertEqual(empty_policy["ownedChildIdsNotInPlaylist"], child_ids)

    def test_v150_layer_tail_preserves_rtpc_child_curves(self) -> None:
        child_id = 0x11223344
        tail = bytes.fromhex(
            "01000000"
            "ddccbbaa"
            "0000"
            "78563412"
            "00"
            "01000000"
            "44332211"
            "01000000"
            "00000000"
            "0000803f"
            "09000000"
            "00"
        )

        result = build_audio.hirc_v150_layer_tail(
            tail, 0, [child_id], bank_version=150
        )

        self.assertEqual(result["layerTailParserStatus"], "typedExactV150LayerTail")
        self.assertEqual(result["layerAssignmentStatus"], "nonEmptyCurves")
        self.assertEqual(result["layerCount"], 1)
        self.assertEqual(result["associationCount"], 1)
        self.assertEqual(result["curvePointCount"], 1)
        layer = result["layers"][0]
        self.assertEqual(layer["layerId"], 0xAABBCCDD)
        self.assertEqual(layer["rtpcId"], 0x12345678)
        self.assertEqual(layer["rtpcTypeLabel"], "gameParameter")
        self.assertEqual(layer["associations"][0]["childId"], child_id)
        self.assertEqual(
            layer["associations"][0]["curvePoints"][0]["interpolationLabel"],
            "Constant",
        )
        self.assertFalse(result["continuousValidation"])

        trailing = build_audio.hirc_v150_layer_tail(
            tail + b"\x00", 0, [child_id], bank_version=150
        )
        self.assertEqual(trailing["layerTailParserStatus"], "unresolvedV150LayerTail")
        self.assertEqual(trailing["layerTailFailureReason"], "unexpectedTrailingBytes")

    def test_v150_layer_candidate_without_parent_proof_remains_partial(self) -> None:
        event_id = 100
        action_id = 101
        layer_id = 200
        sound_id = 0x11223344
        media_id = 401
        children_offset = 20
        tail = bytes.fromhex(
            "01000000ddccbbaa00007856341200010000004433221101000000"
            "000000000000803f0900000000"
        )
        layer_data = bytes(children_offset) + pack("<II", 1, sound_id) + tail

        sound_data = sound_source_data(media_id, 999)  # Deliberately not reciprocal.
        objects = {
            event_id: {"type": 4, "data": bytes([1]) + pack("<I", action_id)},
            action_id: {"type": 3, "data": pack("<HI", 0x0403, layer_id)},
            layer_id: {"type": 9, "data": layer_data},
            sound_id: {"type": 2, "data": sound_data},
        }

        result = build_audio.traverse_hirc_event(
            event_id, objects, {media_id}, bank_version=150
        )

        self.assertEqual(result["mediaIds"], [media_id])
        self.assertEqual(result["traversalStatus"], "partial")
        layer = result["containerEvidence"][0]
        self.assertEqual(
            layer["parserConfidence"],
            "typedExactV150CandidateWithoutParentProof",
        )
        self.assertEqual(
            layer["layerTailEvidence"]["layerAssignmentStatus"],
            "nonEmptyCurves",
        )
        self.assertEqual(
            result["unresolvedNodes"][0]["reason"],
            "layerChildrenCandidateWithoutParentProof",
        )

        canonical_empty = bytes(31) + bytes.fromhex("000000000000000000")
        candidate = build_audio.hirc_v150_layer_child_candidate(
            canonical_empty, {}, bank_version=150
        )
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate[0], [])
        self.assertEqual(candidate[1], 31)
        self.assertEqual(candidate[3], "typedExactV150CanonicalEmpty")

    def test_v150_switch_mapping_preserves_flat_value_packages_without_pruning(self) -> None:
        event_id = 100
        action_id = 101
        switch_id = 200
        sound_a = 301
        sound_b = 302
        group_id = 0x3C9C2C56
        default_value_id = 0x8D36849F
        value_id = 0xF44F784A
        children_offset = 40

        switch_data = bytearray(children_offset - 10)
        switch_data.append(0)
        switch_data.extend(pack("<II", group_id, default_value_id))
        switch_data.append(1)
        switch_data.extend(pack("<III", 2, sound_a, sound_b))
        switch_data.extend(pack("<I", 2))
        switch_data.extend(pack("<III", value_id, 1, sound_a))
        switch_data.extend(pack("<II", default_value_id, 0))
        switch_data.extend(pack("<I", 2))
        switch_data.extend(pack("<IBBii", sound_a, 3, 1, 500, -250))
        switch_data.extend(pack("<IBBii", sound_b, 0, 0, 1, 0))

        def sound_data(media_id: int) -> bytes:
            return sound_source_data(media_id, switch_id)

        objects = {
            event_id: {"type": 4, "data": bytes([1]) + pack("<I", action_id)},
            action_id: {"type": 3, "data": pack("<HI", 0x0403, switch_id)},
            switch_id: {"type": 6, "data": bytes(switch_data)},
            sound_a: {"type": 2, "data": sound_data(401)},
            sound_b: {"type": 2, "data": sound_data(402)},
        }

        result = build_audio.traverse_hirc_event(
            event_id, objects, {401, 402}, bank_version=150
        )

        self.assertEqual(result["mediaIds"], [401, 402])
        self.assertEqual(result["traversalStatus"], "complete")
        switch = result["containerEvidence"][0]["switchMappingEvidence"]
        self.assertEqual(switch["parserStatus"], "typedExactV150FlatPackages")
        self.assertEqual(switch["selectionStructure"], "flatValuePackages")
        self.assertEqual(switch["groupType"], "switch")
        self.assertEqual(switch["groupTypeRaw"], 0)
        self.assertEqual(switch["groupId"], group_id)
        self.assertEqual(switch["defaultValueId"], default_value_id)
        self.assertTrue(switch["continuousValidation"])
        self.assertEqual(switch["packages"][0], {
            "packageIndex": 0,
            "valueId": value_id,
            "isDefaultValue": False,
            "mappedChildCount": 1,
            "childIds": [sound_a],
        })
        self.assertTrue(switch["packages"][1]["isDefaultValue"])
        self.assertEqual(switch["unmappedChildIds"], [sound_b])
        self.assertTrue(switch["associations"][0]["isFirstOnly"])
        self.assertTrue(switch["associations"][0]["continuePlayback"])
        self.assertEqual(switch["associations"][0]["onSwitchMode"], "stop")
        self.assertEqual(switch["associations"][0]["fadeOutTimeMs"], 500)
        self.assertEqual(switch["associations"][0]["fadeInTimeMs"], -250)
        self.assertEqual(switch["associations"][1]["onSwitchMode"], "playToEnd")
        self.assertEqual(
            switch["runtimeSelection"],
            "groupValueUnobservedAllChildrenRemainPossible",
        )

        state_data = bytearray(switch_data)
        state_data[children_offset - 10] = 1
        state_mapping = build_audio.hirc_v150_switch_mapping(
            bytes(state_data), children_offset, 2, bank_version=150
        )
        self.assertEqual(state_mapping["groupType"], "state")
        self.assertEqual(state_mapping["groupTypeRaw"], 1)

        no_package_data = bytearray(children_offset - 10)
        no_package_data.append(1)
        no_package_data.extend(pack("<II", 0x3C9C2C56, 0x8D36849F))
        no_package_data.append(0)
        no_package_data.extend(pack("<III", 2, sound_a, sound_b))
        no_package_data.extend(pack("<I", 0))
        no_package = build_audio.hirc_v150_switch_mapping(
            bytes(no_package_data),
            children_offset,
            2,
            bank_version=150,
        )
        self.assertEqual(no_package["parserStatus"], "unresolvedV150SwitchTail")
        self.assertEqual(no_package["failureReason"], "noValuePackages")

    def test_v150_switch_mapping_marks_distinct_layout_unresolved_without_pruning(self) -> None:
        switch_id = 200
        sound_a = 301
        sound_b = 302
        children_offset = 40
        switch_data = bytearray(children_offset - 10)
        # Current distinct-layout objects do not have the flat selector header
        # at C-9; interpreting their final header byte as continuous-validation
        # yields a non-boolean value and must fail before package claims.
        switch_data.extend(bytes.fromhex("0000949cee04bb233163"))
        switch_data.extend(pack("<III", 2, sound_a, sound_b))
        switch_data.extend(pack("<I", 2))
        switch_data.extend(pack("<IBBii", sound_a, 0, 1, 0, 0))
        switch_data.extend(pack("<IBBii", sound_b, 0, 1, 0, 0))

        def sound_data(media_id: int) -> bytes:
            return sound_source_data(media_id, switch_id)

        objects = {
            100: {"type": 4, "data": bytes([1]) + pack("<I", 101)},
            101: {"type": 3, "data": pack("<HI", 0x0403, switch_id)},
            switch_id: {"type": 6, "data": bytes(switch_data)},
            sound_a: {"type": 2, "data": sound_data(401)},
            sound_b: {"type": 2, "data": sound_data(402)},
        }

        result = build_audio.traverse_hirc_event(
            100, objects, {401, 402}, bank_version=150
        )

        self.assertEqual(result["mediaIds"], [401, 402])
        self.assertEqual(result["traversalStatus"], "complete")
        switch = result["containerEvidence"][0]["switchMappingEvidence"]
        self.assertEqual(switch["parserStatus"], "unresolvedV150SwitchTail")
        self.assertEqual(switch["failureReason"], "invalidContinuousValidation")
        self.assertGreater(switch["unresolvedTailByteLength"], 0)
        self.assertEqual(
            switch["runtimeSelection"],
            "groupValueUnobservedAllChildrenRemainPossible",
        )

    def test_typed_hirc_traversal_resolves_v150_music_graph_and_track_media(self) -> None:
        def node_base(parent_id: int) -> bytes:
            return bytes(4) + pack("<II", 0, parent_id)

        def common_music_prefix(parent_id: int, child_ids: list[int]) -> bytes:
            return b"".join([
                bytes([0]),
                node_base(parent_id),
                bytes(7),
                pack("<I", len(child_ids)),
                *(pack("<I", child_id) for child_id in child_ids),
                pack("<ddfBBBI", 1.0, 0.0, 120.0, 4, 4, 0, 0),
            ])

        event_id = 1
        action_id = 2
        switch_id = 10
        ranseq_id = 11
        segment_id = 12
        track_id = 13
        media_id = 777

        switch_data = b"".join([
            common_music_prefix(0, [ranseq_id]),
            pack("<I", 0),  # transition rules
            bytes([1]),
            pack("<II", 1, 0x12345678),
            bytes([0]),
            pack("<I", 24),
            bytes([0]),
            pack("<IIHH", 0, 0x00010001, 1, 100),
            pack("<IIHH", 0x87654321, ranseq_id, 1, 100),
        ])
        ranseq_data = b"".join([
            common_music_prefix(switch_id, [segment_id]),
            pack("<I", 0),  # transition rules
            pack("<I", 2),
            pack("<IIIIhhhIHBB", 0, 100, 1, 0, 1, 1, 1, 50, 0, 1, 0),
            pack("<IIIIhhhIHBB", segment_id, 101, 0, 0xFFFFFFFF, 1, 1, 1, 50, 0, 0, 0),
        ])
        segment_data = b"".join([
            common_music_prefix(ranseq_id, [track_id]),
            pack("<dI", 3000.0, 1),
            pack("<Id", 1, 0.0),
            b"Entry\x00",
        ])
        track_data = b"".join([
            bytes([0]),
            pack("<I", 1),
            pack("<IBIIB", 0x00040001, 2, media_id, 2048, 0x80),
            pack("<I", 1),
            pack("<III4d", 0, media_id, 0, 0.0, 0.0, 0.0, 3000.0),
            pack("<I", 1),  # subtracks
            pack("<I", 0),  # automation items
            node_base(segment_id),
        ])
        objects = {
            event_id: {"type": 4, "data": bytes([1]) + pack("<I", action_id)},
            action_id: {"type": 3, "data": pack("<HI", 0x0403, switch_id)},
            switch_id: {"type": 12, "data": switch_data},
            ranseq_id: {"type": 13, "data": ranseq_data},
            segment_id: {"type": 10, "data": segment_data},
            track_id: {"type": 11, "data": track_data},
        }

        result = build_audio.traverse_hirc_event(event_id, objects, {media_id}, bank_version=150)
        self.assertEqual(result["mediaIds"], [media_id])
        self.assertEqual(result["traversalStatus"], "complete")
        self.assertEqual(result["unresolvedNodes"], [])
        self.assertEqual(
            [row["objectType"] for row in result["musicNodeEvidence"]],
            [12, 13, 10, 11],
        )
        switch = result["musicNodeEvidence"][0]
        self.assertEqual(switch["treeDepth"], 1)
        self.assertEqual(switch["treeLeaves"][0]["audioNodeId"], ranseq_id)
        self.assertEqual(switch["selectorValidation"], {
            "status": "reciprocalChildrenCovered",
            "treeLeafIds": [ranseq_id],
            "reciprocalChildIds": [ranseq_id],
            "treeLeafIdsOutsideReciprocalChildren": [],
            "reciprocalChildrenWithoutTreeLeaf": [],
            "recursiveOwnedDescendantIds": [],
            "zeroUnboundLeafIds": [],
            "sameBankMissingLeafIds": [],
            "localOtherParentLeafIds": [],
            "ownedDirectChildIdsNotInTreeLeaves": [],
            "runtimeBranchStatus": "groupValuesAndActiveLeafNotObserved",
        })
        mismatched_switch = build_audio.hirc_v150_music_switch_structure(
            switch_data,
            1 + 12 + 7,
            1,
            [ranseq_id + 1],
        )
        self.assertEqual(
            mismatched_switch["selectorValidation"]["status"],
            "treeLeafOutsideReciprocalChildren",
        )
        self.assertEqual(
            mismatched_switch["selectorValidation"]["treeLeafIdsOutsideReciprocalChildren"],
            [ranseq_id],
        )
        subset_switch = build_audio.hirc_v150_music_switch_structure(
            switch_data,
            1 + 12 + 7,
            1,
            [ranseq_id, ranseq_id + 1],
        )
        self.assertEqual(
            subset_switch["selectorValidation"]["status"],
            "decisionTreeSubsetOfReciprocalChildren",
        )
        self.assertEqual(
            subset_switch["selectorValidation"]["reciprocalChildrenWithoutTreeLeaf"],
            [ranseq_id + 1],
        )
        ranseq = result["musicNodeEvidence"][1]
        self.assertEqual(ranseq["selectionTypeLabels"], ["continuousSequence", "none"])
        self.assertEqual(ranseq["selectorValidation"], {
            "status": "reciprocalChildrenCovered",
            "playlistTerminalSegmentIds": [segment_id],
            "reciprocalChildIds": [segment_id],
            "playlistTerminalSegmentIdsOutsideReciprocalChildren": [],
            "reciprocalChildrenWithoutPlaylistTerminal": [],
            "terminalPlaylistItemCount": 1,
            "terminalItemsWithSentinelSegmentId": 0,
        })
        mismatched_ranseq = build_audio.hirc_v150_music_random_sequence_structure(
            ranseq_data,
            1 + 12 + 7,
            1,
            [segment_id, segment_id + 1],
        )
        self.assertEqual(
            mismatched_ranseq["selectorValidation"]["status"],
            "playlistSubsetOfReciprocalChildren",
        )
        self.assertEqual(
            mismatched_ranseq["selectorValidation"]["reciprocalChildrenWithoutPlaylistTerminal"],
            [segment_id + 1],
        )
        self.assertEqual(ranseq["playlistItems"][1]["segmentId"], segment_id)
        track = result["musicNodeEvidence"][3]
        self.assertEqual(track["sources"][0]["mediaId"], media_id)
        self.assertEqual(result["mediaEvidence"][0]["musicTrackObjectIds"], [track_id])
        self.assertEqual(result["mediaEvidence"][0]["selectionPaths"], [[
            "musicSwitchCandidate",
            "musicPlaylistCandidate",
            "musicTrack",
            "musicTrackSource",
        ]])

    def test_v150_empty_music_children_require_unique_typed_tail(self) -> None:
        node_base = bytes(4) + pack("<II", 0, 0)
        segment_data = b"".join([
            bytes([0]),
            node_base,
            bytes(7),
            pack("<I", 0),
            pack("<ddfBBBI", 1.0, 0.0, 120.0, 4, 4, 0, 0),
            pack("<dI", 0.0, 0),
        ])
        objects = {
            1: {"type": 4, "data": bytes([1]) + pack("<I", 2)},
            2: {"type": 3, "data": pack("<HI", 0x0403, 3)},
            3: {"type": 10, "data": segment_data},
        }

        result = build_audio.traverse_hirc_event(1, objects, set(), bank_version=150)
        self.assertEqual(result["traversalStatus"], "complete")
        self.assertEqual(result["mediaIds"], [])
        self.assertEqual(result["containerEvidence"][0]["childCount"], 0)
        self.assertEqual(result["containerEvidence"][0]["parserConfidence"], "typedTailExactEmpty")

    def test_music_switch_leaf_ownership_distinguishes_recursive_unbound_and_missing(self) -> None:
        def music_node(parent_id: int) -> dict[str, object]:
            return {
                "type": 10,
                "data": bytes([0]) + bytes(4) + pack("<II", 0, parent_id),
            }

        switch_id = 10
        direct_child = 20
        recursive_leaf = 21
        other_parent_leaf = 22
        missing_leaf = 99
        objects = {
            direct_child: music_node(switch_id),
            recursive_leaf: music_node(direct_child),
            other_parent_leaf: music_node(777),
        }
        structure = {
            "treeLeaves": [
                {"audioNodeId": direct_child},
                {"audioNodeId": recursive_leaf},
                {"audioNodeId": 0},
                {"audioNodeId": missing_leaf},
                {"audioNodeId": other_parent_leaf},
            ],
            "transitionRules": [{
                "sourceIds": [recursive_leaf],
                "destinationIds": [0, missing_leaf],
            }],
            "selectorValidation": {
                "status": "treeLeafOutsideReciprocalChildren",
                "treeLeafIds": [0, direct_child, recursive_leaf, other_parent_leaf, missing_leaf],
                "reciprocalChildIds": [direct_child],
                "treeLeafIdsOutsideReciprocalChildren": [
                    0, recursive_leaf, other_parent_leaf, missing_leaf,
                ],
                "reciprocalChildrenWithoutTreeLeaf": [],
            },
        }

        refined = build_audio.refine_hirc_v150_music_switch_selector_ownership(
            structure, switch_id, objects
        )
        validation = refined["selectorValidation"]
        self.assertEqual(validation["status"], "decisionTreeLeafOwnershipUnresolved")
        self.assertEqual(validation["recursiveOwnedDescendantIds"], [recursive_leaf])
        self.assertEqual(validation["zeroUnboundLeafIds"], [0])
        self.assertEqual(validation["sameBankMissingLeafIds"], [missing_leaf])
        self.assertEqual(validation["localOtherParentLeafIds"], [other_parent_leaf])
        by_id = {row["audioNodeId"]: row for row in refined["treeLeaves"]}
        self.assertEqual(by_id[recursive_leaf]["ownershipParentChain"], [direct_child, switch_id])
        self.assertEqual(
            by_id[recursive_leaf]["transitionReferenceRoles"],
            ["transitionSource"],
        )
        self.assertEqual(
            by_id[0]["transitionReferenceRoles"],
            ["transitionDestination"],
        )

        resolved = build_audio.refine_hirc_v150_music_switch_selector_ownership(
            {
                "treeLeaves": [
                    {"audioNodeId": direct_child},
                    {"audioNodeId": recursive_leaf},
                    {"audioNodeId": 0},
                ],
                "transitionRules": [],
                "selectorValidation": {
                    "status": "treeLeafOutsideReciprocalChildren",
                    "reciprocalChildIds": [direct_child],
                    "reciprocalChildrenWithoutTreeLeaf": [],
                },
            },
            switch_id,
            objects,
        )
        self.assertEqual(
            resolved["selectorValidation"]["status"],
            "decisionTreeIndirectAndUnboundLeavesResolved",
        )

    def test_typed_hirc_traversal_fails_closed_on_truncated_music_track(self) -> None:
        objects = {
            1: {"type": 4, "data": bytes([1]) + pack("<I", 2)},
            2: {"type": 3, "data": pack("<HI", 0x0403, 3)},
            # A media-looking U32 in a malformed MusicTrack is not a source edge.
            3: {"type": 11, "data": pack("<II", 1, 777)},
        }
        result = build_audio.traverse_hirc_event(1, objects, {777})
        self.assertEqual(result["mediaIds"], [])
        self.assertEqual(result["traversalStatus"], "partial")
        self.assertEqual(result["unresolvedNodes"][0]["reason"], "musicTrackPrefixUnresolved")

    def test_typed_hirc_traversal_rejects_music_nodes_from_non_v150_bank(self) -> None:
        objects = {
            1: {"type": 4, "data": bytes([1]) + pack("<I", 2)},
            2: {"type": 3, "data": pack("<HI", 0x0403, 3)},
            3: {"type": 11, "data": bytes(64)},
        }
        result = build_audio.traverse_hirc_event(1, objects, set(), bank_version=154)
        self.assertEqual(result["mediaIds"], [])
        self.assertEqual(result["unresolvedNodes"][0]["reason"], "unsupportedMusicBankVersion")

    def test_play_event_follows_nested_event_actions(self) -> None:
        sound = sound_source_data(99)
        objects = {
            1: {"type": 4, "data": bytes([1]) + pack("<I", 2)},
            2: {"type": 3, "data": pack("<HI", 0x2103, 3)},
            3: {"type": 4, "data": bytes([1]) + pack("<I", 4)},
            4: {"type": 3, "data": pack("<HI", 0x0403, 5)},
            5: {"type": 2, "data": sound},
        }
        result = build_audio.traverse_hirc_event(1, objects, {99})
        self.assertEqual(result["mediaIds"], [99])
        self.assertEqual([row["operation"] for row in result["actionEvidence"]], ["playEvent", "play"])
        self.assertEqual(
            [
                (row["dispatchEventId"], row["eventActionOrdinal"], row["isRootEventAction"])
                for row in result["actionEvidence"]
            ],
            [(1, 0, True), (3, 0, False)],
        )

    def test_shared_sound_keeps_every_play_root_without_duplicate_media(self) -> None:
        sound = sound_source_data(99)
        objects = {
            1: {"type": 4, "data": bytes([2]) + pack("<II", 2, 3)},
            2: {"type": 3, "data": pack("<HI", 0x0403, 4)},
            3: {"type": 3, "data": pack("<HI", 0x0403, 4)},
            4: {"type": 2, "data": sound},
        }
        result = build_audio.traverse_hirc_event(1, objects, {99})
        self.assertEqual(result["mediaIds"], [99])
        self.assertEqual(result["rootPlayActionCount"], 2)
        self.assertEqual(result["mediaEvidence"], [{
            "mediaId": 99,
            "decoded": True,
            "soundObjectCount": 1,
            "soundObjectIds": [4],
            "rootActionIds": [2, 3],
            "relationTypes": ["directSound"],
            "selectionPaths": [["directSound"]],
            "sourceKinds": ["codecMedia"],
            "pluginIds": [0x00040001],
            "pluginNames": ["Wwise Vorbis"],
            "streamTypes": [{"value": 2, "label": "streamedZeroLatency"}],
            "sourceBits": [0],
        }])
        self.assertEqual(result["sourceObjectSummary"]["sourceReferenceCount"], 2)
        self.assertEqual(result["sourceObjectSummary"]["uniqueSourceObjectCount"], 1)
        self.assertEqual(result["sourceObjectSummary"]["sourceKindCounts"], {"codecMedia": 2})
        self.assertEqual(result["nonMediaSourceEvidence"], [])

    def test_v150_sound_sources_separate_codec_external_and_synthesized_audio(self) -> None:
        codec = sound_source_data(
            101, 900, stream_type=1, in_memory_size=4096, source_bits=0x09,
        )
        external = sound_source_data(
            202, 901, plugin_id=0x00080001, stream_type=2,
            in_memory_size=0, source_bits=0,
        )
        synthesized = sound_source_data(
            303, 902, plugin_id=0x00650002, stream_type=0,
            plugin_parameters=b"\x01\x02\x03",
        )

        codec_row = build_audio.hirc_v150_sound_source(codec)
        self.assertEqual(codec_row["sourceKind"], "codecMedia")
        self.assertEqual(codec_row["pluginName"], "Wwise Vorbis")
        self.assertEqual(codec_row["streamTypeLabel"], "streamed")
        self.assertTrue(codec_row["sourceFlags"]["isLanguageSpecific"])
        self.assertTrue(codec_row["sourceFlags"]["nonCachable"])
        self.assertEqual(codec_row["parentId"], 900)

        external_row = build_audio.hirc_v150_sound_source(external)
        self.assertEqual(external_row["sourceKind"], "externalSourceCodec")
        self.assertEqual(external_row["pluginName"], "Wwise External Source")

        synth_row = build_audio.hirc_v150_sound_source(synthesized)
        self.assertEqual(synth_row["sourceKind"], "synthesizedSource")
        self.assertEqual(synth_row["pluginParameterSize"], 3)
        self.assertEqual(synth_row["nodeBaseOffset"], 21)
        self.assertEqual(build_audio.hirc_object_parent_id(2, synthesized), 902)

        objects = {
            1: {"type": 4, "data": bytes([2]) + pack("<II", 2, 3)},
            2: {"type": 3, "data": pack("<HI", 0x0403, 4)},
            3: {"type": 3, "data": pack("<HI", 0x0403, 5)},
            4: {"type": 2, "data": external},
            5: {"type": 2, "data": synthesized},
        }
        result = build_audio.traverse_hirc_event(1, objects, {202, 303})
        self.assertEqual(result["mediaIds"], [])
        self.assertEqual(result["sourceMediaIds"], [])
        self.assertEqual(result["traversalStatus"], "complete")
        self.assertEqual(result["sourceObjectSummary"]["sourceKindCounts"], {
            "externalSourceCodec": 1,
            "synthesizedSource": 1,
        })
        self.assertEqual(
            [row["mediaLocationStatus"] for row in result["nonMediaSourceEvidence"]],
            ["unresolvedExternalSource", "synthesizedSource"],
        )


class GameParameterEvidenceTests(unittest.TestCase):
    def test_metadata_game_parameter_catalog_is_pinned_and_cross_matchable(self) -> None:
        catalog = build_audio.HIRC_GAME_PARAMETER_NAME_EVIDENCE
        self.assertEqual(
            catalog["source"],
            "il2cpp_data/Metadata/global-metadata.dat",
        )
        self.assertEqual(len(catalog["metadataSha256"]), 64)
        entries = {row["parameterIdHex"]: row for row in catalog["entries"]}
        self.assertEqual(
            entries["0x590f4cd1"]["metadataField"].split(".")[-1],
            "AU_RTPC_CINE_CTRL_VOL_MU",
        )
        self.assertEqual(
            entries["0x52aabb05"]["metadataField"].split(".")[-1],
            "AU_RTPC_CINE_CTRL_VOL_SFX",
        )
        self.assertIn("6146/6148", catalog["evidenceBoundary"])


class AudioDumperTests(unittest.TestCase):
    def test_all_mode_runs_primary_once_and_adds_persistent_hotfix_pass(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            executable = root / "AnimeStudio.CLI.exe"
            streaming = root / "StreamingAssets"
            persistent = root / "Persistent"
            audio_root = root / "Audio"
            executable.touch()
            streaming.mkdir()
            persistent.mkdir()
            args = argparse.Namespace(
                skip_decode=False,
                audio_dumper=executable,
                streaming_assets=streaming,
                fallback_assets=persistent,
                audio_root=audio_root,
                block="all",
            )

            with mock.patch.object(build_audio.subprocess, "run") as run:
                build_audio.run_audio_dumper(args, "CN", build_audio.LANGUAGES["CN"])

            self.assertEqual(run.call_count, 2)
            primary = run.call_args_list[0].args[0]
            hotfix = run.call_args_list[1].args[0]
            self.assertEqual(primary[primary.index("--block") + 1], "all")
            self.assertEqual(primary[primary.index("--format") + 1], "flac")
            self.assertEqual(Path(primary[primary.index("--streaming-assets") + 1]), streaming)
            self.assertIn("--shared-output", primary)
            self.assertEqual(hotfix[hotfix.index("--block") + 1], "hotfix-audio")
            self.assertEqual(Path(hotfix[hotfix.index("--streaming-assets") + 1]), persistent)
            self.assertNotIn("--shared-output", hotfix)

    def test_explicit_hotfix_mode_uses_persistent_as_primary(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            executable = root / "AnimeStudio.CLI.exe"
            streaming = root / "StreamingAssets"
            persistent = root / "Persistent"
            executable.touch()
            streaming.mkdir()
            persistent.mkdir()
            args = argparse.Namespace(
                skip_decode=False,
                audio_dumper=executable,
                streaming_assets=streaming,
                fallback_assets=persistent,
                audio_root=root / "Audio",
                block="hotfix-audio",
            )

            with mock.patch.object(build_audio.subprocess, "run") as run:
                build_audio.run_audio_dumper(args, "CN", build_audio.LANGUAGES["CN"])

            self.assertEqual(run.call_count, 1)
            command = run.call_args.args[0]
            self.assertEqual(command[command.index("--block") + 1], "hotfix-audio")
            self.assertEqual(command[command.index("--format") + 1], "flac")
            self.assertEqual(Path(command[command.index("--streaming-assets") + 1]), persistent)
            self.assertEqual(Path(command[command.index("--fallback-assets") + 1]), streaming)

    def test_event_media_inventory_fingerprint_tracks_numeric_media(self) -> None:
        media = {
            "42": {"id": "42", "storageRoot": "shared", "rel": "wwise/42.flac", "bytes": 10},
            "dialog": {"id": "dialog", "storageRoot": "CN", "rel": "voice/dialog.flac", "bytes": 20},
        }
        initial = build_audio.event_media_inventory_fingerprint(media)
        media["42"]["bytes"] = 11
        self.assertNotEqual(initial, build_audio.event_media_inventory_fingerprint(media))

    def test_audio_file_priority_prefers_flac_over_legacy_wav(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            (root / "same.wav").write_bytes(b"wav")
            (root / "same.flac").write_bytes(b"flac")
            files = build_audio.iter_audio_files(root)
            self.assertEqual([path.suffix for path in files], [".flac", ".wav"])

    def test_flac_file_metrics_read_duration_and_average_bitrate(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            path = Path(raw_root) / "test.flac"
            sample_rate = 48_000
            total_samples = 96_000
            packed_stream_info = (
                (sample_rate << 44)
                | (1 << 41)
                | (15 << 36)
                | total_samples
            )
            stream_info = bytes(10) + packed_stream_info.to_bytes(8, "big") + bytes(16)
            path.write_bytes(b"fLaC" + bytes((0x80, 0, 0, 34)) + stream_info + bytes(958))

            metrics = build_audio.audio_file_metrics(path)

            self.assertEqual(metrics["duration"], 2.0)
            self.assertEqual(metrics["bitrate"], path.stat().st_size * 4)

    def test_media_id_collisions_preserve_distinct_physical_occurrences(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            source = root / "Audio/shared"
            (source / "wwise/sfx").mkdir(parents=True)
            (source / "wwise/unknown").mkdir(parents=True)
            (source / "wwise/sfx/42.flac").write_bytes(b"preferred")
            (source / "wwise/sfx/42.wav").write_bytes(b"legacy")
            (source / "wwise/unknown/42.flac").write_bytes(b"other occurrence")

            index = build_audio.collect_audio_files(
                root / "Audio",
                root,
                source,
                "shared",
                "CN",
                build_audio.LANGUAGES["CN"],
            )

            self.assertEqual(len(index), 2)
            self.assertEqual({row["format"] for row in index.values()}, {"flac"})
            self.assertEqual(
                {row["rel"] for row in index.values()},
                {"wwise/sfx/42.flac", "wwise/unknown/42.flac"},
            )

    def test_cross_scope_merge_keeps_later_lookup_priority_and_both_files(self) -> None:
        shared = {"42": {"id": "42", "storageRoot": "shared", "rel": "wwise/42.flac"}}
        language = {"42": {"id": "42", "storageRoot": "CN", "rel": "voice/42.flac"}}
        merged = build_audio.merge_audio_file_indexes(shared, language)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged["42"]["storageRoot"], "CN")
        self.assertIn("42@shared:wwise/42.flac", merged)


class ProjectileAudioLinkTests(unittest.TestCase):
    def test_writes_projectile_audio_sidecar_without_mutating_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root)
            projectile_path = webui_root / "data" / "gameplay" / "projectiles.json"
            projectile_path.parent.mkdir(parents=True)
            projectile_payload = {
                "schemaVersion": 3,
                "entries": [{
                    "id": "projectile_test",
                    "sounds": {"launchSound": {"value": -1, "hex": "0xffffffff"}},
                }],
            }
            projectile_path.write_text(json.dumps(projectile_payload), encoding="utf-8")
            original_projectile_bytes = projectile_path.read_bytes()
            key = "au_projectile_named_event"
            stats = build_audio.write_projectile_audio_sidecar(
                webui_root,
                "CN",
                {key: [{
                    "src": "/export_full/structured/Audio/shared/wwise/sfx/7.flac",
                    "mediaId": 7,
                    "format": "flac",
                    "bytes": 120,
                    "audioScope": "shared",
                    "bankId": 9,
                }]},
                [{"eventId": key, "eventHash": 0xFFFFFFFF, "source": "wwiseHirc"}],
            )

            self.assertEqual(projectile_path.read_bytes(), original_projectile_bytes)
            sidecar_path = webui_root / "data/lang/CN/gameplay/projectile_audio.json"
            payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
            launch = payload["links"][0]
            self.assertEqual(stats["projectileSoundRefsLinked"], 1)
            self.assertEqual(payload["schemaVersion"], 1)
            self.assertEqual(launch["projectileId"], "projectile_test")
            self.assertEqual(launch["field"], "launchSound")
            self.assertEqual(launch["eventHash"], 0xFFFFFFFF)
            self.assertTrue(launch["event"]["foundInWwise"])
            self.assertEqual(launch["event"]["runtimeSelection"], "singleCandidate")
            self.assertEqual(launch["event"]["canonicalEventIds"], [key])
            self.assertEqual(launch["audio"][0]["mediaId"], 7)


class GameplayAudioLinkTests(unittest.TestCase):
    @staticmethod
    def memorypack_strings(member_count: int, *values: str) -> bytes:
        return bytes([member_count]) + b"".join(
            pack("<I", len(value.encode("utf-8"))) + value.encode("utf-8")
            for value in values
        )

    def test_length_prefixed_scan_rejects_incidental_ascii(self) -> None:
        valid = self.memorypack_strings(47, "au_skill_test")
        incidental = b"\x00xxxxau_incidental"
        self.assertEqual(
            build_audio.length_prefixed_matches(
                valid + incidental,
                build_audio.GAMEPLAY_AUDIO_EVENT_BYTES_RE,
            ),
            {"au_skill_test"},
        )

    def test_animation_collection_normalizes_event_identity_and_preserves_authored_case(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            clip_root = export_root / "recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/AnimationClip"
            clip_root.mkdir(parents=True)
            (clip_root / "A_actor_test_battle_walk_p0000000000000001.anim").write_text(
                """%YAML 1.1
AnimationClip:
  m_Name: A_actor_test_battle_walk
  m_Events:
  - time: 0.25
    functionName: OnCustomFootStep
    data: Player_FOL_FS_Walk
    floatParameter: 0.5
    intParameter: 0
  - time: 0.75
    functionName: OnCustomFootStep
    data: player_fol_fs_walk
    floatParameter: 0.5
    intParameter: 1
""",
                encoding="utf-8",
            )
            (clip_root / "A_actor_unknown_ui_generic_p0000000000000002.anim").write_text(
                """%YAML 1.1
AnimationClip:
  m_Name: A_actor_unknown_ui_generic
  m_Events:
  - time: 0.5
    functionName: PostAudioEvent
    data: au_ui_generic
    floatParameter: 0
    intParameter: 0
""",
                encoding="utf-8",
            )
            result = build_audio.collect_gameplay_animation_audio(
                export_root,
                [{"kind": "character", "id": "chr_0001_test", "skillGroups": []}],
                [],
            )

            owner = result["owners"][0]
            self.assertEqual(set(owner["events"]), {"player_fol_fs_walk"})
            self.assertEqual(
                [row["authoredEventId"] for row in owner["events"]["player_fol_fs_walk"]],
                ["Player_FOL_FS_Walk", "player_fol_fs_walk"],
            )
            self.assertEqual({row["clipContext"] for row in owner["events"]["player_fol_fs_walk"]}, {"battle"})
            self.assertEqual({row["clipReachability"] for row in owner["events"]["player_fol_fs_walk"]}, {"unresolved"})
            self.assertEqual(set(result["unownedEvents"]), {"au_ui_generic"})
            self.assertEqual(result["unownedEvents"]["au_ui_generic"][0]["ownerStatus"], "unresolved")
            self.assertEqual(result["counts"]["animationAudioClipsScanned"], 2)
            self.assertEqual(result["counts"]["animationAudioClipsOwnerUnresolved"], 1)

    def test_animation_controller_index_is_fail_closed_and_annotates_direct_clip_refs(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            clip_root = export_root / "recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/AnimationClip"
            controller_root = export_root / "recovered/AnimeStudio-cli/StreamingAssets/json_by_type/AnimatorController"
            clip_root.mkdir(parents=True)
            controller_root.mkdir(parents=True)
            clip_template = """%YAML 1.1
AnimationClip:
  m_Name: {clip_name}
  m_Events:
  - time: 0.25
    functionName: PostAudioEvent
    data: {event_id}
"""
            (clip_root / "A_actor_test_battle_direct_p0000000000000001.anim").write_text(
                clip_template.format(
                    clip_name="A_actor_test_battle_direct",
                    event_id="au_direct_controller",
                ),
                encoding="utf-8",
            )
            (clip_root / "A_actor_test_battle_unresolved_p0000000000000002.anim").write_text(
                clip_template.format(
                    clip_name="A_actor_test_battle_unresolved",
                    event_id="au_unresolved_controller",
                ),
                encoding="utf-8",
            )
            (controller_root / "AnimatorController#fixture_p0000000000000003.json").write_text(
                json.dumps({
                    "$animestudio": {
                        "type": "AnimatorController",
                        "pathId": 3,
                        "sourceFile": "CAB-controller-fixture",
                        "pptrReferences": [
                            {
                                "targetType": "AnimationClip",
                                "targetPathId": 1,
                                "targetSourceFile": "CAB-clip-fixture",
                                "resolutionStatus": "resolved",
                            },
                            {
                                # An unresolved PPtr must not become a name/path guess.
                                "targetType": "AnimationClip",
                                "targetPathId": 2,
                                "targetSourceFile": "CAB-clip-fixture",
                                "resolutionStatus": "unresolved",
                            },
                            {
                                "targetType": "AnimatorController",
                                "targetPathId": 2,
                                "targetSourceFile": "CAB-clip-fixture",
                                "resolutionStatus": "resolved",
                            },
                        ],
                    },
                    "m_Name": "AC_fixture_direct",
                }),
                encoding="utf-8",
            )
            # Missing exporter identity is fail-closed and cannot contribute an index row.
            (controller_root / "malformed.json").write_text(
                json.dumps({"m_Name": "AC_should_not_match"}),
                encoding="utf-8",
            )

            result = build_audio.collect_gameplay_animation_audio(
                export_root,
                [{"kind": "character", "id": "chr_0001_test", "skillGroups": []}],
                [],
            )

            owner = result["owners"][0]
            direct = owner["events"]["au_direct_controller"][0]
            unresolved = owner["events"]["au_unresolved_controller"][0]
            self.assertEqual(direct["clipReachability"], "directAnimatorController")
            self.assertEqual(direct["animatorControllerCount"], 1)
            self.assertEqual(
                direct["animatorControllerContexts"][0]["name"],
                "AC_fixture_direct",
            )
            self.assertEqual(unresolved["clipReachability"], "unresolved")
            self.assertEqual(unresolved["animatorControllerCount"], 0)
            self.assertEqual(unresolved["animatorControllerContexts"], [])
            self.assertEqual(result["counts"]["animationAudioControllerReachableClips"], 1)
            self.assertEqual(result["counts"]["animationAudioControllerUnresolvedClips"], 1)
            self.assertEqual(
                result["counts"]["animationAudioControllerReachableCallbackRows"],
                1,
            )
            self.assertEqual(
                result["animationControllerIndex"]["directReferenceCount"],
                1,
            )
            self.assertEqual(result["animationControllerIndex"]["status"], "partial")

    def test_animation_audio_scans_persistent_and_scopes_controller_path_ids(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            streaming_clip_root = (
                export_root
                / "recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/AnimationClip"
            )
            persistent_clip_root = (
                export_root
                / "recovered/AnimeStudio-cli/Persistent/convert_by_type/AnimationClip"
            )
            persistent_controller_root = (
                export_root
                / "recovered/AnimeStudio-cli/Persistent/json_by_type/AnimatorController"
            )
            streaming_clip_root.mkdir(parents=True)
            persistent_clip_root.mkdir(parents=True)
            persistent_controller_root.mkdir(parents=True)
            clip_template = """%YAML 1.1
AnimationClip:
  m_Name: {clip_name}
  m_Events:
  - time: 0.25
    functionName: PostAudioEvent
    data: {event_id}
"""
            # PathIDs are serialized-file identities, not global identities.
            # A Persistent controller reference must not annotate the same
            # numeric PathID under StreamingAssets.
            (streaming_clip_root / "A_actor_test_battle_stream_p0000000000000001.anim").write_text(
                clip_template.format(
                    clip_name="A_actor_test_battle_stream",
                    event_id="au_stream_unresolved",
                ),
                encoding="utf-8",
            )
            (persistent_clip_root / "A_actor_test_battle_patch_p0000000000000001.anim").write_text(
                clip_template.format(
                    clip_name="A_actor_test_battle_patch",
                    event_id="au_persistent_direct",
                ),
                encoding="utf-8",
            )
            (persistent_controller_root / "AnimatorController#fixture_p0000000000000003.json").write_text(
                json.dumps({
                    "$animestudio": {
                        "type": "AnimatorController",
                        "pathId": 3,
                        "sourceFile": "CAB-persistent-controller",
                        "pptrReferences": [{
                            "targetType": "AnimationClip",
                            "targetPathId": 1,
                            "targetSourceFile": "CAB-persistent-clip",
                            "resolutionStatus": "resolved",
                        }],
                    },
                    "m_Name": "AC_persistent_fixture",
                }),
                encoding="utf-8",
            )

            result = build_audio.collect_gameplay_animation_audio(
                export_root,
                [{"kind": "character", "id": "chr_0001_test", "skillGroups": []}],
                [],
            )

            events = result["owners"][0]["events"]
            self.assertEqual(
                events["au_persistent_direct"][0]["clipReachability"],
                "directAnimatorController",
            )
            self.assertEqual(
                events["au_persistent_direct"][0]["animatorControllerContexts"][0]["storageRoot"],
                "Persistent",
            )
            self.assertEqual(
                events["au_stream_unresolved"][0]["clipReachability"],
                "unresolved",
            )
            self.assertEqual(result["counts"]["animationAudioClipsScanned"], 2)
            self.assertEqual(result["counts"]["animationAudioControllerReachableClips"], 1)
            self.assertEqual(
                result["animationControllerIndex"]["availableSourceRoots"],
                ["recovered/AnimeStudio-cli/Persistent/json_by_type/AnimatorController"],
            )

    def test_animator_controller_state_clip_refs_are_bounded_authored_membership(self) -> None:
        payload = {
            "m_AnimationClips": [
                {"m_FileID": 2, "m_PathID": 101},
                {"m_FileID": 2, "m_PathID": 102},
            ],
            "m_Controller": {
                "m_LayerArray": [{"data": {"m_StateMachineIndex": 0}}],
                "m_StateMachineArray": [{"data": {
                    "m_StateConstantArray": [{"data": {
                        "m_NameID": 11,
                        "m_FullPathID": 22,
                        "m_TagID": 33,
                        "m_BlendTreeConstantArray": [{"data": {
                            "m_NodeArray": [{"data": {
                                "m_ClipID": 1,
                                "m_BlendType": 0,
                            }}],
                        }}],
                    }}],
                }}],
            },
        }
        refs = build_audio.animator_controller_state_clip_refs(payload)
        self.assertEqual(list(refs), [1])
        self.assertEqual(refs[1][0]["clipSlot"], 1)
        self.assertEqual(refs[1][0]["stateMachineLayerIndices"], [0])
        self.assertTrue(refs[1][0]["stateMachineReferencedByLayer"])
        self.assertEqual(refs[1][0]["reachability"], "authoredStateMembership")
        self.assertEqual(refs[1][0]["runtimeExecution"], "unobserved")

        malformed = dict(payload)
        malformed["m_Controller"] = {"m_LayerArray": "not-a-list"}
        self.assertEqual(build_audio.animator_controller_state_clip_refs(malformed), {})

    def test_animator_override_index_keeps_corpus_unique_mapping_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root) / "export_full"
            clip_root = export_root / "recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/AnimationClip"
            controller_root = export_root / "recovered/AnimeStudio-cli/StreamingAssets/json_by_type/AnimatorController"
            override_root = export_root / "recovered/AnimeStudio-cli/StreamingAssets/json_by_type/AnimatorOverrideController"
            clip_root.mkdir(parents=True)
            controller_root.mkdir(parents=True)
            override_root.mkdir(parents=True)
            clip_text = """%YAML 1.1
AnimationClip:
  m_Name: A_actor_test_battle_override
  m_Events:
  - time: 0.25
    functionName: PostAudioEvent
    data: au_override_fixture
"""
            (clip_root / "A_actor_test_battle_override_p0000000000000002.anim").write_text(
                clip_text,
                encoding="utf-8",
            )
            (controller_root / "AnimatorController#fixture_p0000000000000003.json").write_text(
                json.dumps({
                    "$animestudio": {
                        "type": "AnimatorController",
                        "pathId": 3,
                        "sourceFile": "CAB-controller-fixture",
                    },
                    "m_Name": "AC_fixture_override",
                }),
                encoding="utf-8",
            )
            (override_root / "AC_eny_0001_fixture_p0000000000000004.json").write_text(
                json.dumps({
                    "m_Controller": {"m_FileID": 0, "m_PathID": 3, "IsNull": False},
                    "m_Clips": [{
                        "m_OriginalClip": {"m_FileID": 0, "m_PathID": 1, "IsNull": False},
                        "m_OverrideClip": {"m_FileID": 0, "m_PathID": 2, "IsNull": False},
                    }],
                }),
                encoding="utf-8",
            )

            result = build_audio.collect_animation_override_index(export_root)
            self.assertEqual(result["summary"]["overrideControllerCount"], 1)
            self.assertEqual(result["summary"]["replacementReferenceCount"], 1)
            self.assertEqual(result["summary"]["controllerPathIdCorpusUnique"], 1)
            self.assertEqual(result["summary"]["effectiveClipCorpusUniqueReferences"], 1)
            context = result["byClipPathId"][2][0]
            self.assertEqual(context["mappingKind"], "replacement")
            self.assertEqual(context["controllerJoinStatus"], "corpusUniqueControllerPathId")
            self.assertEqual(context["clipJoinStatus"], "corpusUniqueAnimationClipPathId")
            self.assertEqual(context["assetIdentityToken"], "eny_0001_fixture")
            self.assertEqual(context["runtimeActivation"], "unobserved")

            # A missing base controller must remain partial rather than being
            # guessed from the override filename.
            payload = json.loads(
                (override_root / "AC_eny_0001_fixture_p0000000000000004.json").read_text(
                    encoding="utf-8"
                )
            )
            payload["m_Controller"]["m_PathID"] = 99
            (override_root / "AC_eny_0001_fixture_p0000000000000004.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
            partial = build_audio.collect_animation_override_index(export_root)
            self.assertEqual(partial["summary"]["status"], "partial")
            self.assertEqual(partial["summary"]["controllerPathIdUnresolved"], 1)
            self.assertEqual(
                partial["byClipPathId"][2][0]["controllerJoinStatus"],
                "missingControllerPathId",
            )

    def test_collects_direct_character_and_bounded_enemy_audio(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            webui_root = root / "webui"
            export_root = root / "export_full"
            gameplay_path = webui_root / "data/lang/CN/gameplay/index.json"
            gameplay_path.parent.mkdir(parents=True)
            gameplay_path.write_text(json.dumps({"entries": [
                {
                    "kind": "character",
                    "id": "chr_0001_test",
                    "skillGroups": [{"id": "normal", "skills": [{"id": "chr_0001_test_normal"}]}],
                },
                {
                    "kind": "enemy",
                    "id": "eny_0001_test",
                    "variantIds": ["eny_0001_test_elite"],
                    "bornBuffs": ["buff_enemy_spawn"],
                },
            ]}), encoding="utf-8")
            skill_root = export_root / "structured/StreamingAssets/Data/Json/SkillData"
            buff_root = export_root / "structured/StreamingAssets/Data/Json/BuffData"
            skill_root.mkdir(parents=True)
            buff_root.mkdir(parents=True)
            (skill_root / "chr_0001_test_normal.json").write_bytes(
                self.memorypack_strings(47, "au_character_attack", "buff_character_hit")
            )
            (buff_root / "buff_character_hit.json").write_bytes(
                self.memorypack_strings(30, "au_character_hit")
            )
            (skill_root / "eny_0001_test_elite_attack.json").write_bytes(
                self.memorypack_strings(47, "au_enemy_attack")
            )
            (buff_root / "buff_enemy_spawn.json").write_bytes(
                self.memorypack_strings(30, "au_enemy_spawn")
            )

            result = build_audio.collect_gameplay_audio_references(webui_root, export_root, "CN")
            owners = result["owners"]
            character = next(row for row in owners if row["ownerKind"] == "character")
            enemy_skill = next(row for row in owners if row["ownerKind"] == "enemy" and row["skillId"])
            enemy_spawn = next(row for row in owners if row["ownerKind"] == "enemy" and not row["skillId"])
            self.assertEqual(character["confidence"], "direct")
            self.assertEqual(set(character["events"]), {"au_character_attack", "au_character_hit"})
            self.assertEqual(enemy_skill["confidence"], "inferred")
            self.assertEqual(set(enemy_skill["events"]), {"au_enemy_attack"})
            self.assertEqual(enemy_spawn["confidence"], "direct")
            self.assertEqual(set(enemy_spawn["events"]), {"au_enemy_spawn"})

    def test_collects_owner_unresolved_exact_gameplay_config_audio_references(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            webui_root = root / "webui"
            export_root = root / "export_full"
            gameplay_path = webui_root / "data/lang/CN/gameplay/index.json"
            gameplay_path.parent.mkdir(parents=True)
            gameplay_path.write_text(json.dumps({"entries": []}), encoding="utf-8")
            skill_root = export_root / "structured/StreamingAssets/Data/Json/SkillData"
            buff_root = export_root / "structured/Persistent/Data/Json/BuffData"
            skill_root.mkdir(parents=True)
            buff_root.mkdir(parents=True)
            (skill_root / "skill_orphan.json").write_bytes(
                self.memorypack_strings(47, "au_skill_orphan_exact")
            )
            (buff_root / "buff_orphan.json").write_bytes(
                self.memorypack_strings(30, "au_buff_orphan_exact")
            )

            result = build_audio.collect_gameplay_audio_references(
                webui_root,
                export_root,
                "CN",
            )

            references = {
                row["eventId"]: row
                for row in result["authoredConfigEventReferences"]
            }
            self.assertEqual(
                set(references),
                {"au_skill_orphan_exact", "au_buff_orphan_exact"},
            )
            self.assertEqual(references["au_skill_orphan_exact"]["configKind"], "SkillData")
            self.assertEqual(references["au_skill_orphan_exact"]["configId"], "skill_orphan")
            self.assertEqual(references["au_buff_orphan_exact"]["configKind"], "BuffData")
            self.assertEqual(references["au_buff_orphan_exact"]["ownerLinkStatus"], "unresolved")
            self.assertEqual(
                references["au_buff_orphan_exact"]["evidence"],
                "exactMemoryPackLengthPrefixedAudioEventString",
            )
            self.assertEqual(result["counts"]["authoredConfigEventReferences"], 2)
            self.assertEqual(result["counts"]["authoredConfigEventReferenceEvents"], 2)

    def test_exact_play_sound_event_seeds_buff_traversal_and_keeps_owner_gap(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            webui_root = root / "webui"
            export_root = root / "export_full"
            gameplay_path = webui_root / "data/lang/CN/gameplay/index.json"
            gameplay_path.parent.mkdir(parents=True)
            gameplay_path.write_text(json.dumps({"entries": [{
                "kind": "character",
                "id": "chr_test",
                "skillGroups": [{"id": "normal", "skills": [{"id": "chr_test_normal"}]}],
            }]}), encoding="utf-8")
            skill_root = export_root / "structured/StreamingAssets/Data/Json/SkillData"
            buff_root = export_root / "structured/StreamingAssets/Data/Json/BuffData"
            skill_root.mkdir(parents=True)
            buff_root.mkdir(parents=True)
            # The generic inventory sees the BuffData dependency, but not the
            # typed PlaySoundActionData Event string supplied by the decoder.
            (skill_root / "chr_test_normal.json").write_bytes(
                self.memorypack_strings(47, "buff_test_timed")
            )
            (buff_root / "buff_test_timed.json").write_bytes(
                self.memorypack_strings(30, "buff_test_timed")
            )
            (buff_root / "buff_orphan.json").write_bytes(
                self.memorypack_strings(30, "buff_orphan")
            )
            linked_action = {
                "buffId": "buff_test_timed",
                "eventId": "au_test_timed",
                "timelineActionIndex": 0,
                "actionDataIndex": 0,
                "startFrame": 17,
                "endFrame": 34,
                "serverActionIndex": 9,
                "runtimeConditionStatus": "unresolved",
            }
            orphan_action = {
                "buffId": "buff_orphan",
                "eventId": "au_test_orphan",
                "timelineActionIndex": 0,
                "actionDataIndex": 0,
                "startFrame": 2,
                "endFrame": 8,
                "serverActionIndex": 10,
                "runtimeConditionStatus": "unresolved",
            }
            decoded = {
                "byBuffEvent": {
                    "buff_test_timed": {"au_test_timed": [linked_action]},
                    "buff_orphan": {"au_test_orphan": [orphan_action]},
                },
                "counts": {
                    "buffPlaySoundActionOccurrences": 2,
                    "buffPlaySoundUniqueEvents": 2,
                },
            }

            with mock.patch.object(
                build_audio,
                "collect_buff_play_sound_actions",
                return_value=decoded,
            ):
                result = build_audio.collect_gameplay_audio_references(
                    webui_root,
                    export_root,
                    "CN",
                )

            owner = next(row for row in result["owners"] if row["ownerKind"] == "character")
            self.assertEqual(set(owner["events"]), {"au_test_timed"})
            evidence = owner["events"]["au_test_timed"][0]
            self.assertEqual(evidence["buffIds"], ["buff_test_timed"])
            self.assertEqual(evidence["playSoundActions"][0]["startFrame"], 17)
            self.assertEqual(
                evidence["playSoundActions"][0]["runtimeConditionStatus"],
                "unresolved",
            )
            catalog = {row["eventId"]: row for row in result["authoredPlaySoundActions"]}
            self.assertEqual(
                catalog["au_test_timed"]["ownerLinkStatus"],
                "linkedThroughBuffDependency",
            )
            self.assertEqual(catalog["au_test_orphan"]["ownerLinkStatus"], "unresolved")
            self.assertEqual(result["counts"]["buffPlaySoundSeededEventRefs"], 2)
            self.assertEqual(
                result["counts"]["buffPlaySoundActionsLinkedToGameplayOwner"],
                1,
            )
            self.assertEqual(result["counts"]["buffPlaySoundActionsOwnerUnresolved"], 1)

    def test_exact_skill_play_sound_event_seeds_direct_skill_owner(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            webui_root = root / "webui"
            export_root = root / "export_full"
            gameplay_path = webui_root / "data/lang/CN/gameplay/index.json"
            gameplay_path.parent.mkdir(parents=True)
            gameplay_path.write_text(json.dumps({"entries": [{
                "kind": "character",
                "id": "chr_test",
                "skillGroups": [{"id": "normal", "skills": [{"id": "chr_test_normal"}]}],
            }]}), encoding="utf-8")
            skill_path = (
                export_root
                / "structured/StreamingAssets/Data/Json/SkillData/chr_test_normal.json"
            )
            skill_path.parent.mkdir(parents=True)
            skill_path.write_bytes(b"fixture-without-generic-au-prefix")
            skill_action = {
                "buffId": "chr_test_normal",
                "eventId": "eny_fixture_direct_event",
                "timelineActionIndex": 0,
                "actionDataIndex": 0,
                "startFrame": 4,
                "endFrame": 9,
                "serverActionIndex": 2,
                "runtimeConditionStatus": "unresolved",
            }
            skill_decoded = {
                "byBuffEvent": {
                    "chr_test_normal": {"eny_fixture_direct_event": [skill_action]},
                },
                "counts": {
                    "buffPlaySoundActionOccurrences": 1,
                    "buffPlaySoundUniqueEvents": 1,
                },
            }
            empty_decoded = {"byBuffEvent": {}, "counts": {}}

            with mock.patch.object(
                build_audio,
                "collect_buff_play_sound_actions",
                side_effect=[skill_decoded, empty_decoded],
            ):
                result = build_audio.collect_gameplay_audio_references(
                    webui_root,
                    export_root,
                    "CN",
                )

            owner = next(row for row in result["owners"] if row["ownerKind"] == "character")
            evidence = owner["events"]["eny_fixture_direct_event"][0]
            self.assertEqual(evidence["kind"], "skillData")
            self.assertEqual(evidence["playSoundActions"][0]["skillId"], "chr_test_normal")
            self.assertNotIn("buffId", evidence["playSoundActions"][0])
            self.assertEqual(result["counts"]["skillPlaySoundSeededEventRefs"], 1)
            self.assertEqual(result["counts"]["skillPlaySoundActionOccurrences"], 1)

    def test_collects_enemy_template_skill_authored_under_another_enemy(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            webui_root = root / "webui"
            export_root = root / "export_full"
            gameplay_path = webui_root / "data/lang/CN/gameplay/index.json"
            gameplay_path.parent.mkdir(parents=True)
            gameplay_path.write_text(json.dumps({"entries": [{
                "kind": "enemy",
                "id": "eny_0101_variant",
                "templateId": "eny_0101_variant",
                "variantIds": ["eny_0101_variant"],
                "bornBuffs": [],
            }]}), encoding="utf-8")
            skill_root = export_root / "structured/StreamingAssets/Data/Json/SkillData"
            skill_root.mkdir(parents=True)
            (skill_root / "eny_0001_base_attack.json").write_bytes(
                self.memorypack_strings(47, "au_enemy_base_attack")
            )
            template_root = (
                export_root
                / "recovered/AnimeStudio-cli/Persistent/json_by_type/MonoBehaviour"
            )
            template_root.mkdir(parents=True)
            (template_root / "data_eny_0101_variant_p1234.json").write_text(json.dumps({
                "references": {"RefIds": [{
                    "type": {"class": "AbilitySystemData"},
                    "data": {"remainingStringHints": [
                        {"offset": 24, "value": "eny_0001_base_attack"},
                    ]},
                }]},
            }), encoding="utf-8")

            result = build_audio.collect_gameplay_audio_references(
                webui_root,
                export_root,
                "CN",
            )
            owner = next(row for row in result["owners"] if row["skillId"])
            self.assertEqual(owner["ownerId"], "eny_0101_variant")
            self.assertEqual(owner["confidence"], "inferred")
            self.assertEqual(owner["ownershipMethod"], "enemyTemplateAbilitySystemSkill")
            self.assertEqual(set(owner["events"]), {"au_enemy_base_attack"})
            self.assertEqual(result["counts"]["enemyTemplatesWithSkillReferences"], 1)
            self.assertEqual(result["counts"]["enemyTemplateSkillReferences"], 1)

    def test_collects_exact_animation_clip_audio_callback(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            webui_root = root / "webui"
            export_root = root / "export_full"
            gameplay_path = webui_root / "data/lang/CN/gameplay/index.json"
            gameplay_path.parent.mkdir(parents=True)
            gameplay_path.write_text(json.dumps({"entries": [{
                "kind": "character",
                "id": "chr_0001_test",
                "skillGroups": [{
                    "id": "chr_0001_test_NormalAttack",
                    "actionSkillIds": ["chr_0001_test_attack1"],
                }],
            }]}), encoding="utf-8")
            clip_root = (
                export_root
                / "recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/AnimationClip"
            )
            clip_root.mkdir(parents=True)
            (clip_root / "A_actor_test_battle_attack1_p0123456789ABCDEF.anim").write_text(
                "\n".join([
                    "%YAML 1.1",
                    "AnimationClip:",
                    "  m_Name: A_actor_test_battle_attack1",
                    "  m_Events:",
                    "  - time: 0.25",
                    "    functionName: PostAudioEvent",
                    "    data: player_test_attack_foley",
                    "  - time: 0.5",
                    "    functionName: NotAudio",
                    "    data: ignored",
                ]),
                encoding="utf-8",
            )

            result = build_audio.collect_gameplay_audio_references(
                webui_root,
                export_root,
                "CN",
            )
            self.assertIn("player_test_attack_foley", result["eventNames"])
            animation_owner = result["animationOwners"][0]
            self.assertEqual(animation_owner["ownerId"], "chr_0001_test")
            evidence = animation_owner["events"]["player_test_attack_foley"][0]
            self.assertEqual(evidence["actionKind"], "attack")
            self.assertEqual(evidence["function"], "PostAudioEvent")
            self.assertEqual(evidence["time"], 0.25)

    def test_collects_direct_combat_profile_voice_and_bark_trigger(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            export_root = root / "export_full"
            table_root = export_root / "structured/StreamingAssets/Table"
            table_root.mkdir(parents=True)
            (table_root / "CharacterTable.json").write_text(json.dumps({
                "chr_0001_test": {
                    "profileVoice": [{
                        "voId": "chr_0001_test_combat_intobattle_01",
                        "voiceIndex": 7,
                    }, {
                        "voId": "chr_0001_test_chrbark_join_01",
                        "voiceIndex": 8,
                    }],
                },
            }), encoding="utf-8")
            (table_root / "AIBark.json").write_text(json.dumps({
                "bark_test": {"array": [{"triggerKey": ["combat_intobattle"]}]},
            }), encoding="utf-8")
            result = build_audio.collect_gameplay_profile_voices(export_root, [{
                "kind": "character",
                "id": "chr_0001_test",
                "skillGroups": [],
            }])

            self.assertEqual(result["counts"]["profileVoiceRefs"], 1)
            voice = result["owners"][0]["voices"][0]
            self.assertEqual(voice["id"], "chr_0001_test_combat_intobattle_01")
            self.assertEqual(voice["triggerKey"], "combat_intobattle")
            self.assertEqual(voice["actionKind"], "combatVoice")

    def test_writes_only_playable_gameplay_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root)
            references = {
                "eventNames": {"au_yes", "au_no"},
                "owners": [{
                    "ownerKind": "character",
                    "ownerId": "chr_test",
                    "groupId": "normal",
                    "skillId": "chr_test_normal",
                    "confidence": "direct",
                    "ownershipMethod": "gameplaySkillId",
                    "events": {"au_yes": [{"kind": "skillData"}], "au_no": [{"kind": "skillData"}]},
                }, {
                    "ownerKind": "enemy",
                    "ownerId": "eny_test",
                    "groupId": "",
                    "skillId": "eny_test_attack",
                    "confidence": "inferred",
                    "ownershipMethod": "enemyIdPrefix",
                    "events": {"au_yes": [{"kind": "skillData"}]},
                }],
                "animationOwners": [{
                    "ownerKind": "enemy",
                    "ownerId": "eny_animation",
                    "ownershipSources": ["animation config"],
                    "events": {"au_yes": [{
                        "kind": "animationClipEvent",
                        "clip": "A_monster_test_battle_attack1",
                        "actionKind": "attack",
                        "time": 0.25,
                        "function": "PostAudioEvent",
                    }]},
                }],
                "unownedAnimationEvents": {
                    "au_owner_unresolved": [{
                        "kind": "animationClipEvent",
                        "authoredEventId": "au_owner_unresolved",
                        "clip": "UI_Generic",
                        "clipSource": "AnimationClip/UI_Generic.anim",
                        "actionKind": "action",
                        "clipContext": "ui",
                        "function": "PostAudioEvent",
                        "time": 0.5,
                        "ownerStatus": "unresolved",
                    }],
                },
                "profileVoiceOwners": [{
                    "ownerId": "chr_voice",
                    "voices": [{
                        "id": "chr_voice_mono_attack_01",
                        "actionKind": "attackVoice",
                        "characterId": "chr_voice",
                        "profileVoiceIndex": 1,
                        "triggerKey": "",
                        "source": "CharacterTable.json",
                    }],
                }],
                "counts": {},
            }
            stats = build_audio.link_gameplay_audio(
                webui_root,
                "CN",
                references,
                {"au_yes": [{"src": "data/audio/shared/yes.wav", "mediaId": 1}]},
                [{"eventId": "au_yes"}],
                {"chr_voice_mono_attack_01": {
                    "src": "data/audio/CN/voice.wav",
                    "id": "chr_voice_mono_attack_01",
                    "format": "wav",
                }},
            )
            payload = json.loads((webui_root / "data/lang/CN/gameplay/sound_effects.json").read_text(encoding="utf-8"))
            events = payload["characters"]["chr_test"]["groups"]["normal"]["events"]
            self.assertEqual(stats["gameplayAudioRefsLinked"], 4)
            self.assertEqual(stats["gameplaySerializedAudioRefs"], 5)
            self.assertEqual(stats["gameplayReferenceOnlyAudioRefs"], 1)
            self.assertEqual(stats["animationAudioRefsLinked"], 1)
            self.assertEqual(stats["profileVoiceRefsLinked"], 1)
            self.assertEqual([row["id"] for row in events], ["au_no", "au_yes"])
            unresolved, resolved = events
            self.assertFalse(unresolved["foundInWwise"])
            self.assertFalse(unresolved["hasPlayableMedia"])
            self.assertEqual(unresolved["runtimeSelection"], "eventNotFoundInWwise")
            self.assertEqual(resolved["triggerBindingStatus"], "exactSkillConfig")
            self.assertEqual(resolved["triggerRelationTypes"], ["skillDataEventReference"])
            self.assertEqual(resolved["triggerBindings"][0]["ownershipMethod"], "gameplaySkillId")
            enemy = payload["enemies"]["eny_test"]
            self.assertEqual(enemy["ownershipConfidence"], "inferred")
            self.assertEqual(enemy["skillIds"], ["eny_test_attack"])
            self.assertEqual([row["id"] for row in enemy["events"]], ["au_yes"])
            self.assertEqual(enemy["events"][0]["triggerBindingStatus"], "inferredSkillConfigOwner")
            animation = payload["enemies"]["eny_animation"]
            self.assertEqual(animation["animationOwnershipConfidence"], "inferred")
            self.assertEqual(animation["animationEvents"][0]["actionKinds"], ["attack"])
            self.assertNotIn("audio", animation["animationEvents"][0])
            catalog = json.loads(
                (webui_root / "data/lang/CN/gameplay/sound_effects_animation_catalog.json")
                .read_text(encoding="utf-8")
            )
            self.assertEqual(catalog["events"]["au_yes"]["audio"][0]["mediaId"], 1)
            self.assertEqual(
                animation["animationEvents"][0]["sourceAnimationClips"],
                ["A_monster_test_battle_attack1"],
            )
            animation_evidence = json.loads(
                (webui_root / "data/lang/CN/gameplay/sound_effects_animation_evidence.json")
                .read_text(encoding="utf-8")
            )
            unresolved_animation = animation_evidence["ownerUnresolved"][0]
            self.assertEqual(unresolved_animation["id"], "au_owner_unresolved")
            self.assertEqual(unresolved_animation["ownerStatus"], "unresolved")
            self.assertEqual(unresolved_animation["animationClipContexts"], ["ui"])
            self.assertEqual(
                payload["characters"]["chr_voice"]["profileVoices"][0]["actionKinds"],
                ["attackVoice"],
            )

    def test_animation_events_mark_shared_owner_scope_and_merge_case_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root)
            callback = {
                "kind": "animationClipEvent",
                "clip": "A_actor_test_battle_walk",
                "actionKind": "movement",
                "function": "OnCustomFootStep",
            }
            references = {
                "eventNames": {"player_fol_fs_walk"},
                "owners": [],
                "animationOwners": [{
                    "ownerKind": "character",
                    "ownerId": "chr_a",
                    "events": {
                        "Player_FOL_FS_Walk": [callback],
                        "player_fol_fs_walk": [{**callback, "clip": "A_actor_test_battle_walk_b"}],
                    },
                }, {
                    "ownerKind": "character",
                    "ownerId": "chr_b",
                    "events": {"player_fol_fs_walk": [callback]},
                }],
                "profileVoiceOwners": [],
                "counts": {},
            }
            media = [{"src": "data/audio/shared/walk_1.wav", "mediaId": 1}, {
                "src": "data/audio/shared/walk_2.wav", "mediaId": 2,
            }]
            stats = build_audio.link_gameplay_audio(
                webui_root,
                "CN",
                references,
                {"player_fol_fs_walk": media},
                [{
                    "eventId": "player_fol_fs_walk",
                    "bankId": 100,
                    "bankVersion": 150,
                    "traversalStatus": "complete",
                    "rootStopActionCount": 1,
                    "actionDispatchEvidence": {
                        "timingClass": "coDispatchWithAuthoredDelayDifference",
                        "playbackActionCount": 2,
                        "typedPlaybackActionCount": 2,
                        "failedPlaybackActionCount": 0,
                        "multiPlayback": True,
                        "simultaneityCandidate": False,
                        "explicitDelayActionCount": 1,
                        "explicitTransitionActionCount": 0,
                        "probabilityGatedActionCount": 1,
                        "evidenceBoundary": "serialized membership only",
                    },
                    "actionEvidence": [{
                        "actionId": 101,
                        "eventActionOrdinal": 0,
                        "operation": "play",
                        "actionParserStatus": "typedExactV150",
                        "delay": {
                            "serializationStatus": "implicitDefaultNotSerialized",
                            "baseValuesMs": [],
                            "modifierRangesMs": [],
                        },
                        "transition": {},
                        "probability": {},
                    }, {
                        "actionId": 102,
                        "eventActionOrdinal": 1,
                        "operation": "play",
                        "actionParserStatus": "typedExactV150",
                        "delay": {
                            "serializationStatus": "explicitBase",
                            "baseValuesMs": [350],
                            "modifierRangesMs": [],
                        },
                        "transition": {},
                        "probability": {
                            "serializationStatus": "explicitBase",
                            "baseValuesPercent": [5.0],
                            "modifierRangesPercent": [],
                            "runtimeSelection": "actionGateNotEvaluated",
                        },
                    }, {
                        "actionId": 103,
                        "eventActionOrdinal": 2,
                        "operation": "stop",
                        "actionParserStatus": "unsupportedActionKind",
                    }],
                    "containerEvidence": [{
                        "objectId": 10,
                        "objectType": 5,
                        "mode": 0,
                        "childCount": 12,
                    }, {
                        "objectId": 20,
                        "objectType": 6,
                        "childCount": 4,
                    }, {
                        # The same node can be reached from more than one Play root;
                        # compact evidence counts the graph node only once.
                        "objectId": 20,
                        "objectType": 6,
                        "childCount": 4,
                    }],
                }],
            )

            payload = json.loads(
                (webui_root / "data/lang/CN/gameplay/sound_effects.json")
                .read_text(encoding="utf-8")
            )
            event_a = payload["characters"]["chr_a"]["animationEvents"][0]
            event_b = payload["characters"]["chr_b"]["animationEvents"][0]
            self.assertEqual(len(payload["characters"]["chr_a"]["animationEvents"]), 1)
            self.assertEqual(event_a["animationOwnerCount"], 2)
            self.assertEqual(event_b["animationOwnerCount"], 2)
            self.assertEqual(event_a["animationOwnershipScope"], "sharedPlayableCharacters")
            self.assertEqual(event_a["possibleMediaScope"], "sharedEventGraph")
            self.assertEqual(event_a["animationFunctions"], ["OnCustomFootStep"])
            self.assertEqual(event_a["id"], "player_fol_fs_walk")
            self.assertEqual(event_a["authoredEventIds"], ["Player_FOL_FS_Walk", "player_fol_fs_walk"])
            self.assertEqual(event_a["eventAliases"], ["Player_FOL_FS_Walk"])
            self.assertEqual(event_a["selectorEvidence"]["bankDefinitionCount"], 1)
            self.assertEqual(event_a["selectorEvidence"]["rootStopActionCount"], 1)
            self.assertEqual(event_a["selectorEvidence"]["containers"], {
                "randomAlternative": {"nodeCount": 1, "childEdgeCount": 12},
                "switchCandidate": {"nodeCount": 1, "childEdgeCount": 4},
            })
            self.assertEqual(payload["schemaVersion"], 5)
            dispatch = event_a["actionDispatchEvidence"][0]
            self.assertEqual(dispatch["bankId"], 100)
            self.assertEqual(dispatch["bankVersion"], 150)
            self.assertEqual(dispatch["timingClass"], "coDispatchWithAuthoredDelayDifference")
            self.assertEqual(dispatch["playbackActionCount"], 2)
            self.assertEqual(dispatch["explicitDelayActionCount"], 1)
            self.assertEqual(dispatch["probabilityGatedActionCount"], 1)
            self.assertEqual([row["actionId"] for row in dispatch["actions"]], [101, 102])
            self.assertEqual(dispatch["actions"][1]["delay"]["baseValuesMs"], [350])
            self.assertEqual(dispatch["actions"][1]["probability"]["baseValuesPercent"], [5.0])
            self.assertEqual(payload["characters"]["chr_a"]["metrics"]["sharedAnimationEventCount"], 1)
            self.assertEqual(payload["characters"]["chr_a"]["metrics"]["uniqueEventMediaPairCount"], 2)
            self.assertEqual(stats["characterAnimationUniqueEvents"], 1)
            self.assertEqual(stats["characterAnimationSharedEvents"], 1)
            self.assertEqual(stats["characterAnimationSharedEventAssociations"], 2)
            self.assertEqual(stats["characterAnimationSingleOwnerPossibleMediaAssociations"], 0)
            self.assertEqual(stats["characterAnimationSharedGraphPossibleMedia"], 2)
            self.assertEqual(stats["gameplayAudioRefsLinked"], 2)
            self.assertEqual(stats["gameplayPossibleMediaAssociations"], 4)
            self.assertEqual(stats["gameplayRawPossibleMediaAssociations"], 4)

    def test_published_counts_follow_serialized_skill_event_merges(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root)
            references = {
                "eventNames": {"au_shared_buff"},
                "owners": [{
                    "ownerKind": "character",
                    "ownerId": "chr_test",
                    "groupId": "normal",
                    "skillId": "chr_test_normal_1",
                    "events": {"au_shared_buff": [{"kind": "buffData"}]},
                }, {
                    "ownerKind": "character",
                    "ownerId": "chr_test",
                    "groupId": "normal",
                    "skillId": "chr_test_normal_2",
                    "events": {"au_shared_buff": [{"kind": "buffData"}]},
                }],
                "animationOwners": [],
                "profileVoiceOwners": [],
                "counts": {},
            }
            media = [{"src": "data/audio/shared/buff_1.wav", "mediaId": 1}, {
                "src": "data/audio/shared/buff_2.wav", "mediaId": 2,
            }]
            stats = build_audio.link_gameplay_audio(
                webui_root,
                "CN",
                references,
                {"au_shared_buff": media},
                [{"eventId": "au_shared_buff", "traversalStatus": "complete"}],
            )

            payload = json.loads(
                (webui_root / "data/lang/CN/gameplay/sound_effects.json").read_text(encoding="utf-8")
            )
            group = payload["characters"]["chr_test"]["groups"]["normal"]
            self.assertEqual(len(group["events"]), 1)
            self.assertEqual(group["events"][0]["sourceSkillIds"], ["chr_test_normal_1", "chr_test_normal_2"])
            self.assertEqual(stats["gameplayRawAudioRefsLinked"], 2)
            self.assertEqual(stats["gameplayAudioRefsLinked"], 1)
            self.assertEqual(stats["gameplayRawPossibleMediaAssociations"], 4)
            self.assertEqual(stats["gameplayPossibleMediaAssociations"], 2)
            self.assertEqual(payload["characters"]["chr_test"]["metrics"]["skillEventAssociationCount"], 1)

    def test_exact_and_inferred_trigger_statuses_remain_per_event(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root)
            references = {
                "eventNames": {"au_exact", "au_inferred"},
                "owners": [{
                    "ownerKind": "character",
                    "ownerId": "chr_test",
                    "groupId": "normal",
                    "skillId": "chr_test_normal",
                    "confidence": "direct",
                    "ownershipMethod": "gameplaySkillId",
                    "sources": ["SkillData/chr_test_normal.json"],
                    "events": {"au_exact": [{"kind": "skillData", "skillId": "chr_test_normal"}]},
                }, {
                    "ownerKind": "character",
                    "ownerId": "chr_test",
                    "groupId": "normal",
                    "skillId": "chr_test_normal_followup",
                    "confidence": "inferred",
                    "ownershipMethod": "playableSkillFamilyPrefix",
                    "sources": ["SkillData/chr_test_normal_followup.json"],
                    "events": {"au_inferred": [{"kind": "skillBuffData", "buffIds": ["buff_followup"]}]},
                }],
                "animationOwners": [],
                "profileVoiceOwners": [],
                "counts": {},
            }
            build_audio.link_gameplay_audio(
                webui_root,
                "CN",
                references,
                {
                    "au_exact": [{"src": "data/audio/shared/exact.wav", "mediaId": 1}],
                    "au_inferred": [{"src": "data/audio/shared/inferred.wav", "mediaId": 2}],
                },
                [{"eventId": "au_exact"}, {"eventId": "au_inferred"}],
            )

            payload = json.loads(
                (webui_root / "data/lang/CN/gameplay/sound_effects.json").read_text(encoding="utf-8")
            )
            group = payload["characters"]["chr_test"]["groups"]["normal"]
            events = {event["id"]: event for event in group["events"]}
            self.assertEqual(group["ownershipConfidence"], "inferred")
            self.assertEqual(events["au_exact"]["triggerBindingStatus"], "exactSkillConfig")
            self.assertEqual(events["au_exact"]["triggerBindings"][0]["requestEvidence"], "exactAuthoredDependency")
            self.assertEqual(events["au_exact"]["triggerBindings"][0]["runtimeActivationStatus"], "conditionAndTimingUnresolved")
            self.assertEqual(events["au_inferred"]["triggerBindingStatus"], "inferredSkillConfigOwner")
            self.assertEqual(events["au_inferred"]["triggerRelationTypes"], ["skillBuffChain"])
            self.assertEqual(events["au_inferred"]["triggerBindings"][0]["buffIds"], ["buff_followup"])
            self.assertEqual(group.get("skillIds"), ["chr_test_normal", "chr_test_normal_followup"])
            self.assertEqual(payload["characters"]["chr_test"]["metrics"]["exactSkillTriggerEventCount"], 1)
            self.assertEqual(payload["characters"]["chr_test"]["metrics"]["inferredSkillTriggerEventCount"], 1)
            self.assertEqual(payload["counts"]["exactSkillConfigTriggerRefs"], 1)
            self.assertEqual(payload["counts"]["inferredSkillConfigOwnerRefs"], 1)

    def test_play_sound_action_binding_preserves_frame_window_and_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root)
            play_sound = {
                "buffId": "buff_test_timed",
                "eventId": "au_exact_timed",
                "startFrame": 17,
                "endFrame": 34,
                "stopOnEnd": True,
                "stopFadeDurationMs": 300,
                "targetSettingsStatus": "partial-target-settings-envelope-opaque",
                "targetSelector": "smart_target",
                "sourcePaths": ["structured/StreamingAssets/Data/Json/BuffData/buff_test_timed.json"],
                "runtimeConditionStatus": "unresolved",
            }
            references = {
                "eventNames": {"au_exact_timed"},
                "authoredPlaySoundActions": [play_sound],
                "owners": [{
                    "ownerKind": "character",
                    "ownerId": "chr_test",
                    "groupId": "normal",
                    "skillId": "chr_test_normal",
                    "confidence": "direct",
                    "ownershipMethod": "gameplaySkillId",
                    "sources": ["SkillData/chr_test_normal.json"],
                    "events": {"au_exact_timed": [{
                        "kind": "skillBuffData",
                        "skillId": "chr_test_normal",
                        "buffIds": ["buff_test_timed"],
                        "playSoundActions": [play_sound],
                    }]},
                }],
                "animationOwners": [],
                "profileVoiceOwners": [],
                "counts": {},
            }
            build_audio.link_gameplay_audio(
                webui_root,
                "CN",
                references,
                {"au_exact_timed": [{"src": "data/audio/shared/timed.wav", "mediaId": 3}]},
                [{"eventId": "au_exact_timed"}],
            )

            payload = json.loads(
                (webui_root / "data/lang/CN/gameplay/sound_effects.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["schemaVersion"], 5)
            self.assertEqual(payload["authoredPlaySoundActions"][0]["startFrame"], 17)
            event = payload["characters"]["chr_test"]["groups"]["normal"]["events"][0]
            binding = event["triggerBindings"][0]
            self.assertEqual(event["triggerBindingStatus"], "exactSkillConfig")
            self.assertEqual(event["triggerRelationTypes"], ["buffPlaySoundAction", "skillBuffChain"])
            self.assertEqual(binding["requestEvidence"], "exactAuthoredPlaySoundAction")
            self.assertEqual(
                binding["runtimeActivationStatus"],
                "authoredFrameWindowRecoveredConditionUnresolved",
            )
            self.assertEqual(binding["playSoundActions"][0]["startFrame"], 17)
            self.assertEqual(binding["playSoundActions"][0]["endFrame"], 34)
            self.assertTrue(binding["playSoundActions"][0]["stopOnEnd"])
            self.assertTrue(any(path.endswith("buff_test_timed.json") for path in binding["sourcePaths"]))


if __name__ == "__main__":
    unittest.main()

"""Wwise v150 bank parsing: objects, nodes, buses, effects, and actions.

Reads the shipped HIRC layout for the selected bank version. Everything here is
serialized structure -- a decoded property or reference is authored evidence, not
proof of playback, selection, or audibility."""

from __future__ import annotations

import hashlib
import math
import struct
from collections import Counter, deque
from typing import Any
from .event_projection import HIRC_OBJECT_TYPE_LABELS

from struct import unpack_from
from .context_utils import SELECTION_HIRC_TYPES

HIRC_ACTION_OPERATION_LABELS = {
    0x0100: "stop",
    0x0200: "pause",
    0x0300: "resume",
    0x0400: "play",
    0x0800: "setPitch",
    0x0900: "resetPitch",
    0x0A00: "setVolume",
    0x0B00: "resetVolume",
    0x0C00: "setBusVolume",
    0x0D00: "resetBusVolume",
    0x0E00: "setLPF",
    0x0F00: "resetLPF",
    0x1000: "useState",
    0x1100: "unuseState",
    0x0600: "mute",
    0x0700: "unmute",
    0x1200: "setState",
    0x1300: "setGameParameter",
    0x1400: "resetGameParameter",
    0x1900: "setSwitch",
    0x1A00: "break",
    0x1B00: "trigger",
    0x1E00: "seek",
    0x1F00: "release",
    0x2100: "playEvent",
    0x2200: "resetPlaylist",
    0x2000: "setHPF",
    0x3000: "resetHPF",
    0x3100: "setFX",
    0x3200: "resetFX",
    0x3300: "setBypassFXSlot",
    0x3400: "resetBypassFXSlot",
    0x3500: "setBypassAllFX",
    0x3600: "resetBypassAllFX",
    0x3700: "resetAllBypassFX",
}

HIRC_PLAYBACK_ACTION_OPERATIONS = frozenset({0x0400, 0x2100})

HIRC_ACTION_PROPERTY_LABELS = {
    0x39: "delayTime",
    0x3A: "transitionTime",
    0x3B: "probability",
}

HIRC_FADE_CURVE_LABELS = {
    0: "Log3",
    1: "Sine",
    2: "Log1",
    3: "InvSCurve",
    4: "Linear",
    5: "SCurve",
    6: "Exp1",
    7: "SineRecip",
    8: "Exp3",
    9: "Constant",
}

HIRC_BANK_TYPE_LABELS = {
    0: "User",
    30: "Event",
    31: "Bus",
}

HIRC_MUSIC_NODE_TYPES = frozenset({10, 11, 12, 13})

HIRC_MUSIC_PARENT_NODE_TYPES = frozenset({10, 12, 13})

HIRC_MUSIC_CHILD_TYPES = {
    10: frozenset({11}),
    12: frozenset({10, 12, 13}),
    13: frozenset({10, 12, 13}),
}

HIRC_TYPED_CHILD_CONTAINER_TYPES = frozenset({5, 6, 7, 9, *HIRC_MUSIC_PARENT_NODE_TYPES})

HIRC_AUDIO_NODE_TYPES = frozenset({2, 5, 6, 7, 9, *HIRC_MUSIC_NODE_TYPES})

HIRC_RTPC_TYPE_LABELS = {
    0: "gameParameter",
    1: "midiParameter",
    2: "switch",
    3: "state",
    4: "modulator",
}

HIRC_ACTION_VALUE_MEANING_LABELS = {
    0: "default",
    1: "independent",
    2: "offset",
}

HIRC_RTPC_ACCUM_LABELS = {
    0: "none",
    1: "exclusive",
    2: "additive",
    3: "multiply",
    4: "boolean",
    5: "maximum",
    6: "filter",
}

HIRC_RTPC_SCALING_LABELS = {
    0: "none",
    2: "decibel",
    3: "logarithmic",
    4: "decibelToLinear",
}

HIRC_STATE_SYNC_TYPE_LABELS = {
    0: "immediate",
    1: "nextGrid",
    2: "nextBar",
    3: "nextBeat",
    4: "nextMarker",
    5: "nextUserMarker",
    6: "entryMarker",
    7: "exitMarker",
    8: "exitNever",
    9: "lastExitPosition",
}

HIRC_RTPC_PARAMETER_LABELS = {
    0x00: "Volume",
    0x01: "LFE",
    0x02: "Pitch",
    0x03: "LPF",
    0x04: "HPF",
    0x05: "BusVolume",
    0x06: "InitialDelay",
    0x07: "MakeUpGain",
    0x08: "DeprecatedFeedbackVolume",
    0x09: "DeprecatedFeedbackLowpass",
    0x0A: "DeprecatedFeedbackPitch",
    0x0B: "MidiTransposition",
    0x0C: "MidiVelocityOffset",
    0x0D: "PlaybackSpeed",
    0x0E: "MuteRatio",
    0x0F: "PlayMechanismSpecialTransitionsValue",
    0x10: "MaxNumInstances",
    0x11: "Priority",
    0x12: "PositionPanX2D",
    0x13: "PositionPanY2D",
    0x14: "PositionPanX3D",
    0x15: "PositionPanY3D",
    0x16: "PositionPanZ3D",
    0x17: "PositioningTypeBlend",
    0x18: "PositioningDivergenceCenterPercent",
    0x19: "PositioningConeAttenuationOnOff",
    0x1A: "PositioningConeAttenuation",
    0x1B: "PositioningConeLPF",
    0x1C: "PositioningConeHPF",
    0x1D: "BypassFX0",
    0x1E: "BypassFX1",
    0x1F: "BypassFX2",
    0x20: "BypassFX3",
    0x21: "BypassAllFX",
    0x22: "HDRBusThreshold",
    0x23: "HDRBusReleaseTime",
    0x24: "HDRBusRatio",
    0x25: "HDRActiveRange",
    0x26: "GameAuxSendVolume",
    0x27: "UserAuxSendVolume0",
    0x28: "UserAuxSendVolume1",
    0x29: "UserAuxSendVolume2",
    0x2A: "UserAuxSendVolume3",
    0x2B: "OutputBusVolume",
    0x2C: "OutputBusHPF",
    0x2D: "OutputBusLPF",
    0x2E: "PositioningEnableAttenuation",
    0x2F: "ReflectionsVolume",
    0x30: "UserAuxSendLPF0",
    0x31: "UserAuxSendLPF1",
    0x32: "UserAuxSendLPF2",
    0x33: "UserAuxSendLPF3",
    0x34: "UserAuxSendHPF0",
    0x35: "UserAuxSendHPF1",
    0x36: "UserAuxSendHPF2",
    0x37: "UserAuxSendHPF3",
    0x38: "GameAuxSendLPF",
    0x39: "GameAuxSendHPF",
    0x3A: "PositionPanZ2D",
    0x3B: "BypassAllMetadata",
}

HIRC_INITIAL_PROPERTY_LABELS = {
    0x00: "Volume",
    0x01: "Pitch",
    0x02: "LPF",
    0x03: "HPF",
    0x04: "BusVolume",
    0x05: "MakeUpGain",
    0x06: "Priority",
    0x07: "MuteRatio",
    0x08: "UserAuxSendVolume0",
    0x09: "UserAuxSendVolume1",
    0x0A: "UserAuxSendVolume2",
    0x0B: "UserAuxSendVolume3",
    0x0C: "GameAuxSendVolume",
    0x0D: "OutputBusVolume",
    0x0E: "OutputBusHPF",
    0x0F: "OutputBusLPF",
    0x10: "UserAuxSendLPF0",
    0x11: "UserAuxSendLPF1",
    0x12: "UserAuxSendLPF2",
    0x13: "UserAuxSendLPF3",
    0x14: "UserAuxSendHPF0",
    0x15: "UserAuxSendHPF1",
    0x16: "UserAuxSendHPF2",
    0x17: "UserAuxSendHPF3",
    0x18: "GameAuxSendLPF",
    0x19: "GameAuxSendHPF",
    0x1A: "ReflectionBusVolume",
    0x1B: "HDRBusThreshold",
    0x1C: "HDRBusRatio",
    0x1D: "HDRBusReleaseTime",
    0x1E: "HDRActiveRange",
    0x1F: "MidiTransposition",
    0x20: "MidiVelocityOffset",
    0x21: "PlaybackSpeed",
    0x22: "InitialDelay",
    0x23: "PositionPanX2D",
    0x24: "PositionPanY2D",
    0x25: "PositionPanZ2D",
    0x26: "PositionPanX3D",
    0x27: "PositionPanY3D",
    0x28: "PositionPanZ3D",
    0x29: "PositioningCenterPercent",
    0x2A: "PositioningTypeBlend",
    0x2B: "PositioningEnableAttenuation",
    0x2C: "PositioningConeAttenuationOnOff",
    0x2D: "PositioningConeAttenuation",
    0x2E: "PositioningConeLPF",
    0x2F: "PositioningConeHPF",
    0x30: "BypassFX",
    0x31: "BypassAllFX",
    0x32: "Available0",
    0x33: "Available1",
    0x34: "Available2",
    0x35: "MaxNumInstances",
    0x36: "BypassAllMetadata",
    0x37: "PlayMechanismSpecialTransitionsValue",
    0x38: "PriorityDistanceOffset",
    0x39: "DelayTime",
    0x3A: "TransitionTime",
    0x3B: "Probability",
    0x3C: "DialogueMode",
    0x3D: "HDRBusGameParam",
    0x3E: "HDRBusGameParamMin",
    0x3F: "HDRBusGameParamMax",
    0x40: "LoopStart",
    0x41: "LoopEnd",
    0x42: "TrimInTime",
    0x43: "TrimOutTime",
    0x44: "FadeInTime",
    0x45: "FadeOutTime",
    0x46: "FadeInCurve",
    0x47: "FadeOutCurve",
    0x48: "LoopCrossfadeDuration",
    0x49: "CrossfadeUpCurve",
    0x4A: "CrossfadeDownCurve",
    0x4B: "MidiTrackingRootNote",
    0x4C: "MidiPlayOnNoteType",
    0x4D: "MidiKeyRangeMin",
    0x4E: "MidiKeyRangeMax",
    0x4F: "MidiVelocityRangeMin",
    0x50: "MidiVelocityRangeMax",
    0x51: "MidiChannelMask",
    0x52: "MidiTempoSource",
    0x53: "MidiTargetNode",
    0x54: "Loop",
    0x55: "AttenuationID",
}

HIRC_INITIAL_PROPERTY_U32_LABELS = frozenset({"AttenuationID"})

HIRC_BUILTIN_EFFECT_PLUGIN_LABELS = {
    0x00690003: "Parametric EQ",
    0x006A0003: "Delay",
    0x006C0003: "Compressor",
    0x006D0003: "Expander",
    0x006E0003: "Peak Limiter",
    0x00730003: "Matrix Reverb",
    0x00760003: "RoomVerb",
    0x007D0003: "Flanger",
    0x007E0003: "Guitar Distortion",
    0x007F0003: "Convolution Reverb",
    0x00810003: "Meter",
    0x00820003: "Time Stretch",
    0x00830003: "Tremolo",
    0x00840003: "Recorder",
    0x00870003: "Stereo Delay",
    0x00880003: "Pitch Shifter",
    0x008A0003: "Harmonizer",
    0x008B0003: "Gain",
    0x00AB0003: "Reflect",
    0x00BA0003: "Mastering Suite",
    0x00BE0003: "3D Audio Bed Mixer",
}

HIRC_EFFECT_PARAMETER_CONTRACT = {
    "akSoundEngineSha256": "b33c3c71e44c305fb1c3903942308f2ab55a7854d68c719fe55e7de323e7dba2",
    "akSoundEngineFileSize": 3586536,
    "evidence": "shippedAkSoundEngineSetParamsBlockDisassembly",
    "schemas": {
        0x00690003: {
            "schema": "wwiseParametricEqFxParamsV1",
            "parameterByteLengths": [56],
            "setParamsBlockRva": "0x00218860",
        },
        0x006A0003: {
            "schema": "wwiseDelayFxParamsV1",
            "parameterByteLengths": [18],
            "setParamsBlockRva": "0x001ed030",
        },
        0x006C0003: {
            "schema": "wwiseCompressorFxParamsV1",
            "parameterByteLengths": [22],
            "setParamsBlockRva": "0x001eb650",
        },
        0x006D0003: {
            "schema": "wwiseExpanderFxParamsV1",
            "parameterByteLengths": [22],
            "setParamsBlockRva": "0x001eb650",
        },
        0x00760003: {
            "schema": "wwiseRoomVerbFxParamsV1",
            "parameterByteLengths": [186],
            "setParamsBlockRva": "0x00231d50",
            "setParamRva": "0x00231590",
            "defaultInitRva": "0x00231430",
            "runtimeErUpdateRva": "0x0022b070",
            "privateTuningNativeEvidence": {
                "status": "exactNativeUseRolesPublicNamesUnresolved",
                "nativeStructOffsetDelta": 14,
                "ranges": [
                    {
                        "setParamIds": [100, 101, 102, 103, 104],
                        "serializedOffsets": [142, 146, 150, 154, 158],
                        "nativeStructOffsets": [156, 160, 164, 168, 172],
                        "role": "earlyReflectionTapPatternSynthesisInputs",
                        "detail": (
                            "0x00229b60 reads the five contiguous floats as two "
                            "endpoint pairs plus a middle variation input, applies "
                            "linear interpolation and seeded per-tap variation, "
                            "then 0x0022a010 normalizes the generated values into "
                            "the ER grid used by per-unit setup."
                        ),
                        "consumerRvas": ["0x00229b60"],
                        "evidenceBoundary": (
                            "RuntimeErUpdate calls the native pattern generator with "
                            "the five contiguous values as bounded/randomized tap "
                            "inputs; the public authoring names remain unresolved."
                        ),
                    },
                    {
                        "setParamIds": [105, 106, 107],
                        "serializedOffsets": [162, 166, 170],
                        "nativeStructOffsets": [176, 180, 184],
                        "role": "nativeRoleUnobservedInAuditedRoomVerbPath",
                        "consumerRvas": [],
                        "evidenceBoundary": (
                            "The current RoomVerb native region shows exact SetParam, "
                            "default-initialization, and copy accesses for these fields "
                            "but no direct read in the audited update helpers."
                        ),
                    },
                    {
                        "setParamIds": [108],
                        "serializedOffsets": [174],
                        "nativeStructOffsets": [188],
                        "role": "sixChannelCoefficientDerivationInput",
                        "detail": (
                            "0x0022ab2e scales the value by 2*pi and a native "
                            "divisor, then writes six coefficients of the form "
                            "1 - (2*pi * value / divisor) for ER/reverb unit "
                            "initialization."
                        ),
                        "consumerRvas": ["0x0022ab2e"],
                        "evidenceBoundary": (
                            "Runtime initialization multiplies this value by a native "
                            "constant and derives six channel coefficients; no public "
                            "parameter name is inferred."
                        ),
                    },
                    {
                        "setParamIds": [109, 110],
                        "serializedOffsets": [178, 182],
                        "nativeStructOffsets": [192, 196],
                        "role": "earlyReflectionSecondaryPatternInputs",
                        "detail": (
                            "0x00229e20 reads the two values as a secondary ER "
                            "pattern range/spread, builds seeded four-lane values "
                            "per unit, and the caller converts them into the "
                            "secondary per-unit pattern before allocation."
                        ),
                        "consumerRvas": ["0x00229e20"],
                        "evidenceBoundary": (
                            "RuntimeErUpdate calls a second native pattern generator "
                            "that reads these two values; the public authoring names "
                            "remain unresolved."
                        ),
                    },
                ],
            },
            "semanticBoundary": (
                "all 37 public authoring properties are identified; exact "
                "SetParam IDs 100..110 retain exact values; native update-role "
                "evidence is available for three groups, while public names remain "
                "unresolved"
            ),
        },
        0x007E0003: {
            "schema": "wwiseGuitarDistortionFxParamsV1",
            "parameterByteLengths": [126],
            "setParamsBlockRva": "0x001f6650",
            "setParamRva": "0x001f6270",
            "defaultInitRva": "0x001f5f70",
            "semanticBoundary": (
                "all six pre/post EQ bands and six public distortion/output "
                "properties are identified"
            ),
        },
        0x007F0003: {
            "schema": "wwiseConvolutionReverbFxParamsV1",
            "parameterByteLengths": [57],
            "setParamsBlockRva": "0x00258340",
            "setParamRva": "0x00257fd0",
            "defaultInitRva": "0x00257f10",
            "privateTuningNativeEvidence": {
                "status": "exactForwardedPrivateFieldsPublicNamesUnresolved",
                "ranges": [
                    {
                        "setParamIds": [34],
                        "serializedOffsets": [52],
                        "nativeStructOffsets": [60],
                        "wrapperOffsets": [76],
                        "role": "privateRuntimeScalarForwardedToConvolutionEngineProcess",
                        "detail": (
                            "SetParam ID 34 writes native +0x3c; wrapper code copies "
                            "it to +0x4c and passes it as the fifth float to the "
                            "convolution processor's virtual method."
                        ),
                        "consumerRvas": [
                            "0x00254a83",
                            "0x00254bd8",
                            "0x00258520",
                        ],
                        "status": "exactForwardedScalarEngineReadUnobserved",
                        "evidenceBoundary": (
                            "SetParam ID 34 writes native +0x3c; the wrapper copies it "
                            "to +0x4c and forwards it as the fifth floating-point "
                            "argument on both convolution processing paths. The "
                            "current CPU engine method at 0x00258520 does not read "
                            "that register in the audited body, so no public name or "
                            "DSP effect is inferred."
                        ),
                    },
                    {
                        "setParamIds": [None],
                        "serializedOffsets": [56],
                        "nativeStructOffsets": [64],
                        "wrapperOffsets": [80],
                        "role": "serializedByteForwardedToConvolutionRuntimeState",
                        "detail": (
                            "Serialized byte 56 is copied through native +0x40 and "
                            "wrapper +0x50 into runtime state +0x8c before the "
                            "convolution state update."
                        ),
                        "consumerRvas": ["0x00254d27"],
                        "status": "exactForwardedRolePublicNameUnresolved",
                        "evidenceBoundary": (
                            "The final serialized byte is copied to native +0x40, "
                            "then to wrapper +0x50 and onward to wrapper state +0x8c. "
                            "The current binary does not expose a stable public "
                            "parameter name for this byte."
                        ),
                    },
                ],
            },
            "semanticBoundary": (
                "13 public runtime properties are identified; SetParam ID 34 "
                "and serialized byte 56 retain exact values with native forwarding "
                "evidence, but their public names and final DSP roles remain "
                "unresolved"
            ),
        },
        0x00BA0003: {
            "schema": "wwiseMasteringSuiteFxParamsV1",
            "parameterByteLengths": [304],
            "setParamsBlockRva": "0x00249fd0",
            "setParamRva": "0x00249a50",
            "defaultInitRva": "0x00249630",
            "channelGainNativeMapping": {
                "serializedOffsets": [235, 239, 243, 247, 251, 255, 259, 263, 267, 271, 275, 279],
                "nativeStructOffsets": [280, 284, 288, 292, 296, 300, 304, 308, 312, 316, 320, 324],
                "status": "exactSetParamsBlockSlotMappingSpeakerNamesUnresolved",
            },
            "privateTuningNativeEvidence": {
                "status": "exactSetParamStorageOnlyPublicNamesUnresolved",
                "ranges": [
                    {
                        "setParamIds": [100],
                        "serializedOffsets": [4],
                        "nativeStructOffsets": [24],
                        "role": "privateUint32StoredAtNativeStructOffset",
                        "consumerRvas": [],
                        "nativeUseStatus": (
                            "nativeSetParamStorageOnlyNoDirectReadObserved"
                        ),
                        "evidenceBoundary": (
                            "SetParam 100 copies the exact uint32 from serialized "
                            "offset 4 to native +0x18; SetParamsBlock and the "
                            "parameter copy path preserve the same field. No "
                            "direct read was observed in the audited Mastering "
                            "Suite runtime region, so its public name and DSP "
                            "role remain unresolved."
                        ),
                    },
                    {
                        "setParamIds": [200],
                        "serializedOffsets": [110],
                        "nativeStructOffsets": [136],
                        "role": "privateUint32StoredAtNativeStructOffset",
                        "consumerRvas": [],
                        "nativeUseStatus": (
                            "nativeSetParamStorageOnlyNoDirectReadObserved"
                        ),
                        "evidenceBoundary": (
                            "SetParam 200 copies the exact uint32 from serialized "
                            "offset 110 to native +0x88; SetParamsBlock and the "
                            "parameter copy path preserve the same field. No "
                            "direct read was observed in the audited Mastering "
                            "Suite runtime region, so its public name and DSP "
                            "role remain unresolved."
                        ),
                    },
                ],
            },
            "semanticBoundary": (
                "the four public modules, six EQ bands, four compressor bands, "
                "master/channel gains, and limiter controls are identified; "
                "SetParam IDs 100 and 200 retain exact unnamed codes with "
                "storage-only native evidence"
            ),
        },
        0x00730003: {
            "schema": "wwiseMatrixReverbFxParamsV1",
            "parameterByteLengths": [29, 45, 61, 77, 93],
            "setParamsBlockRva": "0x002158f0",
        },
        0x00810003: {
            "schema": "wwiseMeterFxParamsV1",
            "parameterByteLengths": [28],
            "setParamsBlockRva": "0x00216f90",
        },
        0x00870003: {
            "schema": "wwiseStereoDelayFxParamsV1",
            "parameterByteLengths": [62],
            "setParamsBlockRva": "0x002350c0",
        },
        0x00880003: {
            "schema": "wwisePitchShifterFxParamsV1",
            "parameterByteLengths": [38],
            "setParamsBlockRva": "0x0021b520",
        },
        0x008A0003: {
            "schema": "wwiseHarmonizerFxParamsV1",
            "parameterByteLengths": [68],
            "setParamsBlockRva": "0x001fa760",
        },
        0x008B0003: {
            "schema": "wwiseGainFxParamsV1",
            "parameterByteLengths": [8],
            "setParamsBlockRva": "0x001f5560",
        },
    },
}

HIRC_PARAMETRIC_EQ_FILTER_LABELS = {
    0: "Low Pass",
    1: "High Pass",
    2: "Band Pass",
    3: "Notch",
    4: "Low Shelf",
    5: "High Shelf",
    6: "Peaking",
}

HIRC_METER_MODE_LABELS = {0: "Peak", 1: "RMS"}

HIRC_METER_SCOPE_LABELS = {0: "Global", 1: "Game Object"}

HIRC_EFFECT_FILTER_LABELS = {
    0: "None",
    1: "Low Pass",
    2: "High Pass",
    3: "Band Pass",
    4: "Notch",
    5: "Low Shelf",
    6: "High Shelf",
    7: "Peaking",
}

HIRC_PITCH_INPUT_LABELS = {
    0: "As Input",
    1: "Mono - Center",
    2: "Stereo",
    3: "L-R-C",
    4: "L-R-Ls-Rs",
    5: "L-R-C-Ls-Rs",
}

HIRC_HARMONIZER_INPUT_LABELS = {
    **HIRC_PITCH_INPUT_LABELS,
    6: "Left Only",
}

HIRC_STEREO_DELAY_INPUT_LABELS = {
    0: "Left/Right",
    1: "Center",
    2: "Left/Right + Center",
    3: "None",
}

HIRC_ROOMVERB_ER_PATTERN_LABELS = {
    0: "Bright Chamber",
    1: "Dark Chamber",
    2: "Concrete Venue 1",
    3: "Concrete Venue 2",
    4: "Night Club",
    5: "Warehouse",
    6: "Small Church",
    7: "Medium Church",
    8: "Large Church",
    9: "Cathedral",
    10: "Short Dark Hall",
    11: "Long Dark Hall",
    12: "Bright Hall",
    13: "Small Hall",
    14: "Medium Hall",
    15: "Large Hall",
    16: "Lecture Hall",
    17: "Recital Hall",
    18: "Small Plate",
    19: "Medium Plate",
    20: "Large Plate",
    21: "Vocal Plate",
    22: "Small Room",
    23: "Large Room",
    24: "Bathroom",
    25: "Bedroom",
    26: "Tiled Room",
    27: "Phone Booth",
    28: "Pool",
    29: "Gym",
    30: "Garage",
}

HIRC_ROOMVERB_TONE_INSERT_LABELS = {
    0: "Off",
    1: "ER Only",
    2: "Reverb Only",
    3: "ER + Reverb",
}

HIRC_ROOMVERB_TONE_CURVE_LABELS = {
    0: "Low Shelf",
    1: "Peaking",
    2: "High Shelf",
}

HIRC_CONVOLUTION_REVERB_TYPE_LABELS = {0: "Reverb", 1: "Filter"}

HIRC_GUITAR_DISTORTION_TYPE_LABELS = {
    0: "None",
    1: "Overdrive",
    2: "Heavy",
    3: "Clip",
    4: "Fuzz",
}

HIRC_MASTERING_EQ_FILTER_LABELS = {
    0: "Off",
    1: "Low Pass Resonant (Two-Pole)",
    2: "High Pass Resonant (Two-Pole)",
    3: "Peak (Notch)",
    4: "High Shelf",
    5: "Low Shelf",
    6: "Low Pass (One-Pole)",
    7: "High Pass (One-Pole)",
}

HIRC_MASTERING_COMPRESSOR_LINK_LABELS = {
    0: "No Link",
    1: "All Channels",
    2: "Partial Link",
}

HIRC_MASTERING_LIMITER_MODE_LABELS = {
    0: "Soft-Knee",
    1: "Hard-Knee",
    2: "Advanced",
}

def iter_bnk_sections(bank_payload: bytes) -> list[tuple[bytes, bytes]]:
    sections: list[tuple[bytes, bytes]] = []
    pos = 0
    while pos + 8 <= len(bank_payload):
        tag = bank_payload[pos : pos + 4]
        size = unpack_from("<I", bank_payload, pos + 4)[0]
        body_start = pos + 8
        body_end = body_start + size
        if body_end > len(bank_payload) or not tag.isalpha():
            break
        sections.append((tag, bank_payload[body_start:body_end]))
        pos = body_end
    return sections

def parse_hirc_objects(bank_payload: bytes) -> dict[int, dict[str, Any]]:
    objects: dict[int, dict[str, Any]] = {}
    for tag, body in iter_bnk_sections(bank_payload):
        if tag != b"HIRC" or len(body) < 4:
            continue
        count = unpack_from("<I", body, 0)[0]
        pos = 4
        for _ in range(count):
            if pos + 9 > len(body):
                break
            object_type = body[pos]
            object_size = unpack_from("<I", body, pos + 1)[0]
            object_id = unpack_from("<I", body, pos + 5)[0]
            data_start = pos + 9
            data_end = pos + 1 + 4 + object_size
            if data_end > len(body):
                break
            objects[object_id] = {
                "type": object_type,
                "data": body[data_start:data_end],
            }
            pos = data_end
    return objects

def hirc_event_action_ids(data: bytes) -> list[int]:
    if not data:
        return []
    count = data[0]
    ids: list[int] = []
    pos = 1
    for _ in range(count):
        if pos + 4 > len(data):
            break
        ids.append(unpack_from("<I", data, pos)[0])
        pos += 4
    return ids

def hirc_action_target_id(data: bytes) -> int | None:
    if len(data) < 6:
        return None
    return unpack_from("<I", data, 2)[0]

def hirc_action_type(data: bytes) -> int | None:
    if len(data) < 2:
        return None
    return unpack_from("<H", data, 0)[0]

def _hirc_v150_action_property_value(property_id: int, raw: bytes) -> dict[str, Any]:
    row: dict[str, Any] = {
        "rawHex": raw.hex(),
        "rawU32": unpack_from("<I", raw, 0)[0],
    }
    if property_id in {0x39, 0x3A}:
        row.update({
            "encoding": "signedInt32Milliseconds",
            "value": unpack_from("<i", raw, 0)[0],
            "unit": "ms",
        })
    elif property_id == 0x3B:
        row.update({
            "encoding": "float32Percent",
            "value": unpack_from("<f", raw, 0)[0],
            "unit": "percent",
        })
    else:
        row["encoding"] = "rawUnion32"
    return row

def _hirc_v150_action_property_summary(
    property_id: int,
    properties: list[dict[str, Any]],
    ranged_modifiers: list[dict[str, Any]],
) -> dict[str, Any]:
    scalar_values = [
        row["value"]
        for row in properties
        if row["propertyId"] == property_id and "value" in row
    ]
    modifier_ranges = [
        {
            "minimum": row["minimum"]["value"],
            "maximum": row["maximum"]["value"],
        }
        for row in ranged_modifiers
        if row["propertyId"] == property_id
        and "value" in row["minimum"]
        and "value" in row["maximum"]
    ]
    if scalar_values and modifier_ranges:
        status = "explicitBaseAndRange"
    elif scalar_values:
        status = "explicitBase"
    elif modifier_ranges:
        status = "explicitRangeOnly"
    else:
        status = "implicitDefaultNotSerialized"
    suffix = "Percent" if property_id == 0x3B else "Ms"
    summary: dict[str, Any] = {
        "serializationStatus": status,
        f"baseValues{suffix}": scalar_values,
        f"modifierRanges{suffix}": modifier_ranges,
    }
    if modifier_ranges:
        summary["runtimeSelection"] = "boundedModifierUnresolved"
    if property_id == 0x3B:
        summary["runtimeSelection"] = "actionGateNotEvaluated"
    return summary

def hirc_v150_playback_action(data: bytes, bank_version: int | None) -> dict[str, Any]:
    """Decode exact v150 Play/PlayEvent Action evidence without creating edges.

    The target helpers above deliberately remain independent: a failed evidence
    parse must never suppress an otherwise valid typed playback target.  This
    decoder returns no property/timing claims unless the complete Action body is
    consumed according to its operation-specific v150 layout.
    """

    def failed(reason: str, offset: int = 0, expected_bytes: int | None = None) -> dict[str, Any]:
        failure: dict[str, Any] = {
            "reason": reason,
            "offset": offset,
            "dataSize": len(data),
            "remainingBytes": max(0, len(data) - offset),
        }
        if expected_bytes is not None:
            failure["expectedBytes"] = expected_bytes
        return {
            "actionParserStatus": "failedClosed",
            "actionParserFailure": failure,
        }

    if bank_version != 150:
        result = failed("unsupportedBankVersion")
        result["actionParserFailure"]["bankVersion"] = bank_version
        return result
    if len(data) < 7:
        return failed("truncatedActionHeader", 0, 7)

    action_type = unpack_from("<H", data, 0)[0]
    operation = action_type & 0xFF00
    if operation not in HIRC_PLAYBACK_ACTION_OPERATIONS:
        result = failed("unsupportedPlaybackOperation")
        result["actionParserFailure"]["operation"] = operation
        return result

    def read_count(offset: int, reason: str) -> tuple[int, int] | dict[str, Any]:
        if offset >= len(data):
            return failed(reason, offset, 1)
        return data[offset], offset + 1

    pos = 7
    scalar_count_row = read_count(pos, "truncatedScalarPropertyCount")
    if isinstance(scalar_count_row, dict):
        return scalar_count_row
    scalar_count, pos = scalar_count_row
    if pos + scalar_count > len(data):
        return failed("truncatedScalarPropertyIds", pos, scalar_count)
    scalar_ids = list(data[pos : pos + scalar_count])
    pos += scalar_count
    scalar_bytes = scalar_count * 4
    if pos + scalar_bytes > len(data):
        return failed("truncatedScalarPropertyValues", pos, scalar_bytes)
    properties: list[dict[str, Any]] = []
    for property_id in scalar_ids:
        value = _hirc_v150_action_property_value(property_id, data[pos : pos + 4])
        properties.append({
            "propertyId": property_id,
            "propertyName": HIRC_ACTION_PROPERTY_LABELS.get(
                property_id, f"property0x{property_id:02x}"
            ),
            **value,
        })
        pos += 4

    range_count_row = read_count(pos, "truncatedRangePropertyCount")
    if isinstance(range_count_row, dict):
        return range_count_row
    range_count, pos = range_count_row
    if pos + range_count > len(data):
        return failed("truncatedRangePropertyIds", pos, range_count)
    range_ids = list(data[pos : pos + range_count])
    pos += range_count
    range_bytes = range_count * 8
    if pos + range_bytes > len(data):
        return failed("truncatedRangePropertyValues", pos, range_bytes)
    ranged_modifiers: list[dict[str, Any]] = []
    for property_id in range_ids:
        minimum = _hirc_v150_action_property_value(property_id, data[pos : pos + 4])
        maximum = _hirc_v150_action_property_value(property_id, data[pos + 4 : pos + 8])
        ranged_modifiers.append({
            "propertyId": property_id,
            "propertyName": HIRC_ACTION_PROPERTY_LABELS.get(
                property_id, f"property0x{property_id:02x}"
            ),
            "encoding": minimum["encoding"],
            "minimum": minimum,
            "maximum": maximum,
            "runtimeSelection": "boundedModifierUnresolved",
        })
        pos += 8

    evidence: dict[str, Any] = {
        "actionParserStatus": "typedExactV150",
        "targetFlagsRaw": data[6],
        "targetIsBus": bool(data[6] & 0x01),
        "properties": properties,
        "rangedModifiers": ranged_modifiers,
        "delay": _hirc_v150_action_property_summary(0x39, properties, ranged_modifiers),
        "transition": _hirc_v150_action_property_summary(0x3A, properties, ranged_modifiers),
        "probability": _hirc_v150_action_property_summary(0x3B, properties, ranged_modifiers),
    }
    remaining = len(data) - pos
    if operation == 0x0400:
        if remaining < 9:
            return failed("truncatedPlayTail", pos, 9)
        if remaining > 9:
            return failed("unexpectedPlayTrailingBytes", pos + 9, 0)
        fade_flags = data[pos]
        curve_id = fade_flags & 0x1F
        bank_id = unpack_from("<I", data, pos + 1)[0]
        bank_type = unpack_from("<I", data, pos + 5)[0]
        evidence["fade"] = {
            "flagsRaw": fade_flags,
            "curveId": curve_id,
            "curveLabel": HIRC_FADE_CURVE_LABELS.get(curve_id, f"curve{curve_id}"),
            "bankId": bank_id,
            "bankType": bank_type,
            "bankTypeLabel": HIRC_BANK_TYPE_LABELS.get(bank_type, f"bankType{bank_type}"),
        }
    elif remaining:
        return failed("unexpectedPlayEventTrailingBytes", pos, 0)
    return evidence

def hirc_v150_control_action(data: bytes, bank_version: int | None) -> dict[str, Any]:
    """Decode v150 non-playback Action payloads as authored control evidence.

    Action headers and the two property bundles are shared by every v150
    Action.  The operation-specific tails below follow the bank reader layout
    (state/switch IDs, GameParameter values, active-action flags, FX slots and
    exception lists).  A tail is published only when it consumes the complete
    object; otherwise the result is fail-closed with a bounded offset.
    """

    def failed(reason: str, offset: int = 0, expected_bytes: int | None = None) -> dict[str, Any]:
        failure: dict[str, Any] = {
            "reason": reason,
            "offset": offset,
            "dataSize": len(data),
            "remainingBytes": max(0, len(data) - offset),
        }
        if expected_bytes is not None:
            failure["expectedBytes"] = expected_bytes
        return {
            "actionControlParserStatus": "failedClosed",
            "actionControlParserFailure": failure,
        }

    if bank_version != 150:
        result = failed("unsupportedBankVersion")
        result["actionControlParserFailure"]["bankVersion"] = bank_version
        return result
    if len(data) < 7:
        return failed("truncatedActionHeader", 0, 7)

    action_type = unpack_from("<H", data, 0)[0]
    operation = action_type & 0xFF00
    if operation in HIRC_PLAYBACK_ACTION_OPERATIONS:
        return failed("playbackOperationHandledByPlaybackParser", 0)
    supported_operations = {
        0x0100, 0x0200, 0x0300, 0x0600, 0x0700,
        0x0800, 0x0900, 0x0A00, 0x0B00, 0x0C00, 0x0D00,
        0x0E00, 0x0F00, 0x1000, 0x1100, 0x1200, 0x1300,
        0x1400, 0x1900, 0x1A00, 0x1B00, 0x1E00, 0x1F00,
        0x2000, 0x2200, 0x3000, 0x3100, 0x3200, 0x3300,
        0x3400, 0x3500, 0x3600, 0x3700, 0x6100,
    }
    if operation not in supported_operations:
        result = failed("unsupportedControlOperation")
        result["actionControlParserFailure"]["operation"] = operation
        return result

    def read_count(offset: int, reason: str) -> tuple[int, int] | dict[str, Any]:
        if offset >= len(data):
            return failed(reason, offset, 1)
        return data[offset], offset + 1

    pos = 7
    scalar_count_row = read_count(pos, "truncatedScalarPropertyCount")
    if isinstance(scalar_count_row, dict):
        return scalar_count_row
    scalar_count, pos = scalar_count_row
    if pos + scalar_count > len(data):
        return failed("truncatedScalarPropertyIds", pos, scalar_count)
    scalar_ids = list(data[pos : pos + scalar_count])
    pos += scalar_count
    scalar_bytes = scalar_count * 4
    if pos + scalar_bytes > len(data):
        return failed("truncatedScalarPropertyValues", pos, scalar_bytes)
    properties: list[dict[str, Any]] = []
    for property_id in scalar_ids:
        value = _hirc_v150_action_property_value(property_id, data[pos : pos + 4])
        properties.append({
            "propertyId": property_id,
            "propertyName": HIRC_ACTION_PROPERTY_LABELS.get(
                property_id, f"property0x{property_id:02x}"
            ),
            **value,
        })
        pos += 4

    range_count_row = read_count(pos, "truncatedRangePropertyCount")
    if isinstance(range_count_row, dict):
        return range_count_row
    range_count, pos = range_count_row
    if pos + range_count > len(data):
        return failed("truncatedRangePropertyIds", pos, range_count)
    range_ids = list(data[pos : pos + range_count])
    pos += range_count
    range_bytes = range_count * 8
    if pos + range_bytes > len(data):
        return failed("truncatedRangePropertyValues", pos, range_bytes)
    ranged_modifiers: list[dict[str, Any]] = []
    for property_id in range_ids:
        minimum = _hirc_v150_action_property_value(property_id, data[pos : pos + 4])
        maximum = _hirc_v150_action_property_value(property_id, data[pos + 4 : pos + 8])
        ranged_modifiers.append({
            "propertyId": property_id,
            "propertyName": HIRC_ACTION_PROPERTY_LABELS.get(
                property_id, f"property0x{property_id:02x}"
            ),
            "encoding": minimum["encoding"],
            "minimum": minimum,
            "maximum": maximum,
            "runtimeSelection": "boundedModifierUnresolved",
        })
        pos += 8

    def read_u8(offset: int, reason: str) -> tuple[int, int] | dict[str, Any]:
        if offset >= len(data):
            return failed(reason, offset, 1)
        return data[offset], offset + 1

    def read_u32(offset: int, reason: str) -> tuple[int, int] | dict[str, Any]:
        if offset + 4 > len(data):
            return failed(reason, offset, 4)
        return unpack_from("<I", data, offset)[0], offset + 4

    def read_f32(offset: int, reason: str) -> tuple[float, int] | dict[str, Any]:
        if offset + 4 > len(data):
            return failed(reason, offset, 4)
        return unpack_from("<f", data, offset)[0], offset + 4

    def read_varuint(offset: int, reason: str) -> tuple[int, int] | dict[str, Any]:
        value = 0
        shift = 0
        for _ in range(5):
            if offset >= len(data):
                return failed(reason, offset, 1)
            byte = data[offset]
            offset += 1
            value |= (byte & 0x7F) << shift
            if not byte & 0x80:
                return value, offset
            shift += 7
        return failed("invalidVarUInt", offset, 1)

    def read_exceptions(offset: int) -> tuple[list[dict[str, Any]], int] | dict[str, Any]:
        count_row = read_varuint(offset, "truncatedExceptionCount")
        if isinstance(count_row, dict):
            return count_row
        count, offset = count_row
        if count > (len(data) - offset) // 5:
            return failed("truncatedExceptionRows", offset, count * 5)
        rows: list[dict[str, Any]] = []
        for _ in range(count):
            exception_id = unpack_from("<I", data, offset)[0]
            is_bus = bool(data[offset + 4])
            rows.append({
                "id": exception_id,
                "idHex": f"0x{exception_id:08x}",
                "isBus": is_bus,
            })
            offset += 5
        return rows, offset

    evidence: dict[str, Any] = {
        "actionControlParserStatus": "typedExactV150",
        "idExt": unpack_from("<I", data, 2)[0],
        "idExtHex": f"0x{unpack_from('<I', data, 2)[0]:08x}",
        "targetFlagsRaw": data[6],
        "targetIsBus": bool(data[6] & 0x01),
        "properties": properties,
        "rangedModifiers": ranged_modifiers,
    }

    # State and Switch carry two FNV IDs and no exception list.
    if operation in {0x1200, 0x1900}:
        ids = []
        for name in ("groupId", "stateId") if operation == 0x1200 else ("groupId", "switchId"):
            value_row = read_u32(pos, f"truncated{name}")
            if isinstance(value_row, dict):
                return value_row
            value, pos = value_row
            ids.append((name, value))
        for name, value in ids:
            evidence[name] = value
            evidence[f"{name}Hex"] = f"0x{value:08x}"

    elif operation in {0x1300, 0x1400}:
        # Set/ResetGameParameter uses SetValue's fade byte followed by the
        # GameParameter-specific bypass/value-meaning/ranged float tuple.
        fade_row = read_u8(pos, "truncatedFadeFlags")
        if isinstance(fade_row, dict):
            return fade_row
        fade_flags, pos = fade_row
        bypass_row = read_u8(pos, "truncatedBypassTransition")
        if isinstance(bypass_row, dict):
            return bypass_row
        bypass_transition, pos = bypass_row
        meaning_row = read_u8(pos, "truncatedValueMeaning")
        if isinstance(meaning_row, dict):
            return meaning_row
        meaning, pos = meaning_row
        floats: list[float] = []
        for label in ("base", "minimum", "maximum"):
            value_row = read_f32(pos, f"truncated{label.title()}Value")
            if isinstance(value_row, dict):
                return value_row
            value, pos = value_row
            floats.append(value)
        evidence["fadeFlagsRaw"] = fade_flags
        evidence["fadeCurveId"] = fade_flags & 0x1F
        evidence["fadeCurveLabel"] = HIRC_FADE_CURVE_LABELS.get(
            fade_flags & 0x1F, f"curve{fade_flags & 0x1F}"
        )
        evidence["bypassTransition"] = bool(bypass_transition)
        evidence["bypassTransitionRaw"] = bypass_transition
        evidence["valueMeaning"] = meaning
        evidence["valueMeaningLabel"] = HIRC_ACTION_VALUE_MEANING_LABELS.get(
            meaning, f"meaning{meaning}"
        )
        evidence["valueRange"] = {
            "base": floats[0], "minimum": floats[1], "maximum": floats[2],
        }
        exceptions_row = read_exceptions(pos)
        if isinstance(exceptions_row, dict):
            return exceptions_row
        evidence["exceptions"], pos = exceptions_row

    elif operation == 0x6100:
        rtpc_row = read_u32(pos, "truncatedRtpcId")
        if isinstance(rtpc_row, dict):
            return rtpc_row
        rtpc_id, pos = rtpc_row
        value_row = read_f32(pos, "truncatedRtpcValue")
        if isinstance(value_row, dict):
            return value_row
        value, pos = value_row
        evidence.update({
            "rtpcId": rtpc_id,
            "rtpcIdHex": f"0x{rtpc_id:08x}",
            "rtpcValue": value,
        })

    elif operation in {0x0100, 0x0200, 0x0300}:
        fade_row = read_u8(pos, "truncatedFadeFlags")
        if isinstance(fade_row, dict):
            return fade_row
        fade_flags, pos = fade_row
        bit_row = read_u8(pos, "truncatedActionBitVector")
        if isinstance(bit_row, dict):
            return bit_row
        bits, pos = bit_row
        evidence["fadeFlagsRaw"] = fade_flags
        evidence["fadeCurveId"] = fade_flags & 0x1F
        evidence["fadeCurveLabel"] = HIRC_FADE_CURVE_LABELS.get(
            fade_flags & 0x1F, f"curve{fade_flags & 0x1F}"
        )
        evidence["actionBitVectorRaw"] = bits
        if operation == 0x0100:
            evidence["applyToStateTransitions"] = bool(bits & 0x02)
            evidence["applyToDynamicSequence"] = bool(bits & 0x04)
        elif operation == 0x0200:
            evidence["includePendingResume"] = bool(bits & 0x01)
            evidence["applyToStateTransitions"] = bool(bits & 0x02)
            evidence["applyToDynamicSequence"] = bool(bits & 0x04)
        else:
            evidence["isMasterResume"] = bool(bits & 0x01)
            evidence["applyToStateTransitions"] = bool(bits & 0x02)
            evidence["applyToDynamicSequence"] = bool(bits & 0x04)
        exceptions_row = read_exceptions(pos)
        if isinstance(exceptions_row, dict):
            return exceptions_row
        evidence["exceptions"], pos = exceptions_row

    elif operation in {
        0x0600, 0x0700, 0x0800, 0x0900, 0x0A00, 0x0B00,
        0x0C00, 0x0D00, 0x0E00, 0x0F00, 0x2000, 0x3000,
    }:
        fade_row = read_u8(pos, "truncatedFadeFlags")
        if isinstance(fade_row, dict):
            return fade_row
        fade_flags, pos = fade_row
        evidence["fadeFlagsRaw"] = fade_flags
        evidence["fadeCurveId"] = fade_flags & 0x1F
        evidence["fadeCurveLabel"] = HIRC_FADE_CURVE_LABELS.get(
            fade_flags & 0x1F, f"curve{fade_flags & 0x1F}"
        )
        if operation not in {0x0600, 0x0700}:
            meaning_row = read_u8(pos, "truncatedValueMeaning")
            if isinstance(meaning_row, dict):
                return meaning_row
            meaning, pos = meaning_row
            values: list[float] = []
            for label in ("base", "minimum", "maximum"):
                value_row = read_f32(pos, f"truncated{label.title()}Value")
                if isinstance(value_row, dict):
                    return value_row
                value, pos = value_row
                values.append(value)
            evidence["valueMeaning"] = meaning
            evidence["valueMeaningLabel"] = HIRC_ACTION_VALUE_MEANING_LABELS.get(
                meaning, f"meaning{meaning}"
            )
            evidence["valueRange"] = {
                "base": values[0], "minimum": values[1], "maximum": values[2],
            }
        exceptions_row = read_exceptions(pos)
        if isinstance(exceptions_row, dict):
            return exceptions_row
        evidence["exceptions"], pos = exceptions_row

    elif operation in {0x3100, 0x3200}:
        rows = []
        for label, size in (("isAudioDeviceElement", 1), ("slotIndex", 1), ("fxId", 4), ("isShared", 1)):
            if size == 1:
                value_row = read_u8(pos, f"truncated{label.title()}")
            else:
                value_row = read_u32(pos, f"truncated{label.title()}")
            if isinstance(value_row, dict):
                return value_row
            value, pos = value_row
            rows.append((label, value))
        for label, value in rows:
            evidence[label] = bool(value) if label.startswith("is") else value
            if label == "fxId":
                evidence["fxIdHex"] = f"0x{value:08x}"
        exceptions_row = read_exceptions(pos)
        if isinstance(exceptions_row, dict):
            return exceptions_row
        evidence["exceptions"], pos = exceptions_row

    elif operation in {0x3300, 0x3400, 0x3500, 0x3600, 0x3700}:
        bypass_row = read_u8(pos, "truncatedBypassValue")
        if isinstance(bypass_row, dict):
            return bypass_row
        bypass, pos = bypass_row
        slot_row = read_u8(pos, "truncatedFxSlot")
        if isinstance(slot_row, dict):
            return slot_row
        slot, pos = slot_row
        evidence.update({
            "bypass": bool(bypass),
            "bypassRaw": bypass,
            "fxSlot": slot,
        })
        exceptions_row = read_exceptions(pos)
        if isinstance(exceptions_row, dict):
            return exceptions_row
        evidence["exceptions"], pos = exceptions_row

    elif operation == 0x1E00:
        relative_row = read_u8(pos, "truncatedSeekRelative")
        if isinstance(relative_row, dict):
            return relative_row
        relative, pos = relative_row
        values: list[float] = []
        for label in ("seekValue", "seekMinimum", "seekMaximum"):
            value_row = read_f32(pos, f"truncated{label.title()}")
            if isinstance(value_row, dict):
                return value_row
            value, pos = value_row
            values.append(value)
        snap_row = read_u8(pos, "truncatedSeekSnap")
        if isinstance(snap_row, dict):
            return snap_row
        snap, pos = snap_row
        evidence.update({
            "seekRelativeToDuration": bool(relative),
            "seekRelativeRaw": relative,
            "seekValue": values[0], "seekMinimum": values[1], "seekMaximum": values[2],
            "snapToNearestMarker": bool(snap), "snapToNearestMarkerRaw": snap,
        })
        exceptions_row = read_exceptions(pos)
        if isinstance(exceptions_row, dict):
            return exceptions_row
        evidence["exceptions"], pos = exceptions_row

    elif operation in {0x2200}:
        fade_row = read_u8(pos, "truncatedFadeFlags")
        if isinstance(fade_row, dict):
            return fade_row
        fade_flags, pos = fade_row
        evidence.update({
            "fadeFlagsRaw": fade_flags,
            "fadeCurveId": fade_flags & 0x1F,
            "fadeCurveLabel": HIRC_FADE_CURVE_LABELS.get(
                fade_flags & 0x1F, f"curve{fade_flags & 0x1F}"
            ),
        })
        exceptions_row = read_exceptions(pos)
        if isinstance(exceptions_row, dict):
            return exceptions_row
        evidence["exceptions"], pos = exceptions_row

    elif operation in {0x1000, 0x1100, 0x1A00, 0x1B00, 0x1F00}:
        # These actions carry only the common header/property bundles in v150.
        pass

    if pos != len(data):
        return failed("unexpectedControlTrailingBytes", pos, 0)
    evidence["actionControlEvidenceBoundary"] = (
        "authoredActionControlPayload; state/switch/parameter values are triggers, "
        "not evaluated runtime state or effective DSP"
    )
    return evidence

HIRC_PLUGIN_TYPE_LABELS = {
    0: "none",
    1: "codec",
    2: "source",
    3: "effect",
    6: "mixer",
    7: "sink",
    8: "globalExtension",
    9: "metadata",
}

HIRC_STREAM_TYPE_LABELS = {
    0: "memory",
    1: "streamed",
    2: "streamedZeroLatency",
}

HIRC_SOURCE_PLUGIN_LABELS = {
    0x00040001: "Wwise Vorbis",
    0x00140001: "Wwise Opus",
    0x00080001: "Wwise External Source",
    0x00640002: "Wwise Sine",
    0x00650002: "Wwise Silence",
    0x01990002: "Wwise Motion Source",
    0x00940002: "Wwise Synth One",
}

def _hirc_v150_source_kind(plugin_id: int, plugin_type: int) -> str:
    if plugin_id == 0x00080001:
        return "externalSourceCodec"
    if plugin_type == 1:
        return "codecMedia"
    if plugin_type == 2:
        return "synthesizedSource"
    return "unsupportedPluginSource"

def _hirc_v150_bank_source_data(
    data: bytes,
    offset: int = 0,
) -> tuple[dict[str, Any], int] | None:
    """Decode one bounded v150 AkBankSourceData record.

    ``streamType`` is a Wwise buffering policy, not a physical PCK-location
    proof.  Source plugins carry a length-prefixed parameter blob; the blob is
    consumed but intentionally not interpreted without a plugin-specific
    writer fingerprint.
    """

    try:
        if offset < 0 or offset + 14 > len(data):
            raise ValueError("truncated v150 AkBankSourceData")
        plugin_id = unpack_from("<I", data, offset)[0]
        stream_type = data[offset + 4]
        source_id = unpack_from("<I", data, offset + 5)[0]
        in_memory_media_size = unpack_from("<I", data, offset + 9)[0]
        source_bits = data[offset + 13]
        offset += 14
        plugin_type = plugin_id & 0x0F
        plugin_parameter_size = 0
        if plugin_type == 2:
            plugin_parameter_size, offset = _hirc_v150_u32(data, offset)
            if offset + plugin_parameter_size > len(data):
                raise ValueError("truncated v150 source plugin parameters")
            offset += plugin_parameter_size
        known_source_bits = 0x01 | 0x02 | 0x08 | 0x80
        row = {
            "sourceParserStatus": "typedExactV150AkBankSourceData",
            "pluginId": plugin_id,
            "pluginIdHex": f"0x{plugin_id:08x}",
            "pluginName": HIRC_SOURCE_PLUGIN_LABELS.get(plugin_id),
            "pluginType": plugin_type,
            "pluginTypeLabel": HIRC_PLUGIN_TYPE_LABELS.get(
                plugin_type, f"pluginType{plugin_type}"
            ),
            "streamType": stream_type,
            "streamTypeLabel": HIRC_STREAM_TYPE_LABELS.get(
                stream_type, f"streamType{stream_type}"
            ),
            "sourceId": source_id,
            "inMemoryMediaSize": in_memory_media_size,
            "sourceBits": source_bits,
            "sourceFlags": {
                "isLanguageSpecific": bool(source_bits & 0x01),
                "prefetch": bool(source_bits & 0x02),
                "nonCachable": bool(source_bits & 0x08),
                "hasSource": bool(source_bits & 0x80),
                "unknownBits": source_bits & ~known_source_bits,
            },
            "pluginParameterSize": plugin_parameter_size,
            "sourceKind": _hirc_v150_source_kind(plugin_id, plugin_type),
            "streamTypeBoundary": "bufferingPolicyNotPhysicalMediaLocation",
        }
        return row, offset
    except (ValueError, OverflowError):
        return None

def hirc_v150_sound_source(data: bytes) -> dict[str, Any] | None:
    """Decode a Sound's source record and exact NodeBase parent prefix."""

    parsed = _hirc_v150_bank_source_data(data, 0)
    if not parsed:
        return None
    source, node_base_offset = parsed
    try:
        parent_id, _parent_end = _hirc_v150_node_base_parent(data, node_base_offset)
    except (ValueError, OverflowError):
        return None
    return {**source, "nodeBaseOffset": node_base_offset, "parentId": parent_id}

def collect_hirc_decoded_sound_definitions(
    objects: dict[int, dict[str, Any]],
    decoded_media_ids: set[int],
    *,
    bank_name: str,
    bank_id: int,
    bank_version: int | None,
) -> list[dict[str, Any]]:
    """Keep exact decoded Sound objects even when no Event reaches them."""

    rows: list[dict[str, Any]] = []
    for object_id, obj in objects.items():
        if int(obj.get("type") or 0) != 2:
            continue
        data = obj.get("data") or b""
        source = hirc_v150_sound_source(data)
        if not source or source.get("sourceKind") != "codecMedia":
            continue
        try:
            media_id = int(source.get("sourceId") or 0)
        except (TypeError, ValueError):
            continue
        if media_id not in decoded_media_ids:
            continue
        parent_id = hirc_object_parent_id(2, data)
        parent = objects.get(parent_id) if parent_id is not None else None
        parent_type = int((parent or {}).get("type") or 0)
        rows.append({
            "mediaId": media_id,
            "soundObjectId": int(object_id),
            "parentObjectId": parent_id,
            "parentObjectType": parent_type or None,
            "parentObjectTypeLabel": (
                HIRC_OBJECT_TYPE_LABELS.get(parent_type, f"type{parent_type}")
                if parent_type else None
            ),
            "bank": bank_name,
            "bankId": int(bank_id),
            "bankVersion": bank_version,
            "sourceParserStatus": source.get("sourceParserStatus"),
            "pluginIdHex": source.get("pluginIdHex"),
            "pluginName": source.get("pluginName"),
            "streamType": source.get("streamType"),
            "streamTypeLabel": source.get("streamTypeLabel"),
            "evidence": "exactTypedWwiseSoundCodecMediaObject",
        })
    return rows

def _hirc_v150_u32(data: bytes, offset: int) -> tuple[int, int]:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError("truncated v150 U32")
    return unpack_from("<I", data, offset)[0], offset + 4

def _hirc_v150_effect_slot_flags(
    flags_raw: int,
    *,
    include_rendered: bool,
) -> dict[str, Any]:
    """Decode the v150 FX-slot bit vector without inferring runtime audibility.

    ``AkParameterNode`` stores bypass/share-set/rendered in bits 0/1/2.  Owned
    Audio/Aux Bus slots use bits 0/1; bit 2 is retained as an unknown/reserved
    value there.  These are authored slot flags, distinct from NodeBase's
    ``bypassAll`` and from runtime RTPC/State bypass controls.
    """

    flags_raw = int(flags_raw) & 0xFF
    known_mask = 0x07 if include_rendered else 0x03
    return {
        "flagsRaw": flags_raw,
        "effectBypass": bool(flags_raw & 0x01),
        "effectShareSet": bool(flags_raw & 0x02),
        "effectRendered": bool(flags_raw & 0x04) if include_rendered else None,
        "unknownFlagBits": flags_raw & ~known_mask,
        "flagSemanticBoundary": (
            "typedExactV150NodeEffectFlags: bit0=bypass, bit1=shareSet, "
            "bit2=rendered"
            if include_rendered
            else
            "typedExactV150BusEffectFlags: bit0=bypass, bit1=shareSet; "
            "bit2=reservedOrUnknown"
        ),
    }

def _hirc_v150_node_base(
    data: bytes,
    offset: int,
) -> tuple[dict[str, Any], int]:
    """Decode the v150 NodeBase prefix through DirectParentID.

    This common prefix is also the authored direct-processing boundary for a
    Sound/container node: inherited-FX override, ordered effect slots, metadata
    plug-ins, explicit output-bus override, and the hierarchy parent.  Effect
    slot flag bits are preserved raw because the current corpus proves their
    correlation with custom/ShareSet objects but not every individual runtime
    meaning.  A zero effect object ID remains an explicit empty slot.
    """

    start = offset
    if offset < 0 or offset + 2 > len(data):
        raise ValueError("truncated v150 initial FX header")
    override_parent_fx_raw = data[offset]
    effect_count = data[offset + 1]
    offset += 2
    if override_parent_fx_raw not in (0, 1):
        raise ValueError("invalid v150 override-parent-FX flag")

    bypass_all_raw: int | None = None
    effects: list[dict[str, Any]] = []
    if effect_count:
        if offset >= len(data):
            raise ValueError("truncated v150 FX bypass flag")
        bypass_all_raw = data[offset]
        offset += 1
        effect_bytes = effect_count * 6  # U8 slot + U32 object ID + U8 flags
        if offset + effect_bytes > len(data):
            raise ValueError("truncated v150 initial FX list")
        for ordinal in range(effect_count):
            slot_index = data[offset]
            effect_id = unpack_from("<I", data, offset + 1)[0]
            flags_raw = data[offset + 5]
            effects.append({
                "ordinal": ordinal,
                "slotIndex": slot_index,
                "effectId": effect_id,
                "effectIdHex": f"0x{effect_id:08x}",
                **_hirc_v150_effect_slot_flags(
                    flags_raw, include_rendered=True
                ),
                "referenceStatus": (
                    "authoredEffectObjectId" if effect_id else "emptyEffectSlot"
                ),
            })
            offset += 6

    if offset + 2 > len(data):
        raise ValueError("truncated v150 metadata header")
    override_parent_metadata_raw = data[offset]
    metadata_count = data[offset + 1]
    offset += 2
    if override_parent_metadata_raw not in (0, 1):
        raise ValueError("invalid v150 override-parent-metadata flag")
    metadata: list[dict[str, Any]] = []
    metadata_bytes = metadata_count * 6  # U8 slot + U32 ID + U8 share-set flag
    if offset + metadata_bytes > len(data):
        raise ValueError("truncated v150 metadata list")
    for ordinal in range(metadata_count):
        slot_index = data[offset]
        metadata_id = unpack_from("<I", data, offset + 1)[0]
        share_set_raw = data[offset + 5]
        metadata.append({
            "ordinal": ordinal,
            "slotIndex": slot_index,
            "metadataId": metadata_id,
            "metadataIdHex": f"0x{metadata_id:08x}",
            "shareSetRaw": share_set_raw,
        })
        offset += 6

    override_bus_id, offset = _hirc_v150_u32(data, offset)
    parent_id, offset = _hirc_v150_u32(data, offset)
    return {
        "parserStatus": "typedExactV150NodeBaseProcessingPrefix",
        "prefixOffset": start,
        "prefixByteLength": offset - start,
        "overrideParentFxRaw": override_parent_fx_raw,
        "overrideParentFx": bool(override_parent_fx_raw),
        "effectSlotCount": effect_count,
        "bypassAllRaw": bypass_all_raw,
        "bypassAll": bool(bypass_all_raw) if bypass_all_raw is not None else None,
        "effects": effects,
        "overrideParentMetadataRaw": override_parent_metadata_raw,
        "overrideParentMetadata": bool(override_parent_metadata_raw),
        "metadataSlotCount": metadata_count,
        "metadata": metadata,
        "overrideBusId": override_bus_id,
        "overrideBusIdHex": f"0x{override_bus_id:08x}" if override_bus_id else None,
        "parentId": parent_id,
    }, offset

def _hirc_v150_node_base_parent(data: bytes, offset: int) -> tuple[int, int]:
    node_base, end = _hirc_v150_node_base(data, offset)
    return int(node_base["parentId"]), end

def _hirc_effect_float(data: bytes, offset: int) -> float:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError("truncated effect float")
    value = float(unpack_from("<f", data, offset)[0])
    if not math.isfinite(value):
        raise ValueError("non-finite effect float")
    return value

def _hirc_effect_bool(data: bytes, offset: int) -> bool:
    if offset < 0 or offset >= len(data) or data[offset] not in (0, 1):
        raise ValueError("invalid effect boolean")
    return bool(data[offset])

def _hirc_effect_float_range(
    data: bytes,
    offset: int,
    minimum: float,
    maximum: float,
    label: str,
) -> float:
    value = _hirc_effect_float(data, offset)
    if value < minimum - 0.0001 or value > maximum + 0.0001:
        raise ValueError(f"invalid {label}")
    return value

def _hirc_effect_number(value: float) -> str:
    return f"{value:.6g}"

def decode_hirc_v150_effect_parameters(
    plugin_class_id: int,
    parameter_data: bytes,
) -> dict[str, Any] | None:
    """Decode current shipped Wwise effect parameter blocks fail-closed.

    Field offsets and primitive widths are pinned by each parameter class's
    SetParamsBlock implementation in the shipped AkSoundEngine.dll.  The
    returned values are authored bank base values; runtime RTPC/State changes,
    slot bypass, platform DSP, and audibility are intentionally not inferred.
    """

    contract = HIRC_EFFECT_PARAMETER_CONTRACT["schemas"].get(plugin_class_id)
    if not contract or len(parameter_data) not in contract["parameterByteLengths"]:
        return None
    parser_status = "typedExactShippedAkSoundEngineSetParamsBlock"
    parameter_boundary = "typedExactAuthoredBaseValues"
    semantic_boundary = ""
    try:
        values: dict[str, Any]
        summary: str
        if plugin_class_id == 0x008B0003:  # Gain
            values = {
                "fullBandGainDb": _hirc_effect_float(parameter_data, 0),
                "lfeGainDb": _hirc_effect_float(parameter_data, 4),
            }
            summary = (
                f"full band {_hirc_effect_number(values['fullBandGainDb'])} dB; "
                f"LFE {_hirc_effect_number(values['lfeGainDb'])} dB"
            )
        elif plugin_class_id == 0x006A0003:  # Delay
            values = {
                "delayTimeSeconds": _hirc_effect_float(parameter_data, 0),
                "feedbackPercent": _hirc_effect_float(parameter_data, 4),
                "wetDryMixPercent": _hirc_effect_float(parameter_data, 8),
                "outputLevelDb": _hirc_effect_float(parameter_data, 12),
                "feedbackEnabled": _hirc_effect_bool(parameter_data, 16),
                "processLfe": _hirc_effect_bool(parameter_data, 17),
            }
            summary = (
                f"{_hirc_effect_number(values['delayTimeSeconds'])} s; "
                f"feedback {_hirc_effect_number(values['feedbackPercent'])}% "
                f"{'on' if values['feedbackEnabled'] else 'off'}; wet/dry "
                f"{_hirc_effect_number(values['wetDryMixPercent'])}%; output "
                f"{_hirc_effect_number(values['outputLevelDb'])} dB; LFE "
                f"{'on' if values['processLfe'] else 'off'}"
            )
        elif plugin_class_id in (0x006C0003, 0x006D0003):
            values = {
                "thresholdDb": _hirc_effect_float(parameter_data, 0),
                "ratio": _hirc_effect_float(parameter_data, 4),
                "attackSeconds": _hirc_effect_float(parameter_data, 8),
                "releaseSeconds": _hirc_effect_float(parameter_data, 12),
                "outputGainDb": _hirc_effect_float(parameter_data, 16),
                "processLfe": _hirc_effect_bool(parameter_data, 20),
                "channelLink": _hirc_effect_bool(parameter_data, 21),
            }
            summary = (
                f"threshold {_hirc_effect_number(values['thresholdDb'])} dB; "
                f"ratio {_hirc_effect_number(values['ratio'])}:1; attack "
                f"{_hirc_effect_number(values['attackSeconds'])} s; release "
                f"{_hirc_effect_number(values['releaseSeconds'])} s; output "
                f"{_hirc_effect_number(values['outputGainDb'])} dB; LFE "
                f"{'on' if values['processLfe'] else 'off'}; channels "
                f"{'linked' if values['channelLink'] else 'independent'}"
            )
        elif plugin_class_id == 0x00690003:  # Parametric EQ
            bands: list[dict[str, Any]] = []
            band_summaries: list[str] = []
            for index in range(3):
                offset = index * 17
                filter_type = unpack_from("<I", parameter_data, offset)[0]
                if filter_type not in HIRC_PARAMETRIC_EQ_FILTER_LABELS:
                    raise ValueError("invalid Parametric EQ filter type")
                band = {
                    "band": index + 1,
                    "filterType": filter_type,
                    "filterTypeLabel": HIRC_PARAMETRIC_EQ_FILTER_LABELS[filter_type],
                    "gainDb": _hirc_effect_float(parameter_data, offset + 4),
                    "frequencyHz": _hirc_effect_float(parameter_data, offset + 8),
                    "qualityFactor": _hirc_effect_float(parameter_data, offset + 12),
                    "enabled": _hirc_effect_bool(parameter_data, offset + 16),
                }
                bands.append(band)
                band_summaries.append(
                    f"B{index + 1} "
                    + (
                        f"{band['filterTypeLabel']} "
                        f"{_hirc_effect_number(band['frequencyHz'])} Hz "
                        f"{_hirc_effect_number(band['gainDb'])} dB "
                        f"Q {_hirc_effect_number(band['qualityFactor'])}"
                        if band["enabled"] else "off"
                    )
                )
            output_gain = _hirc_effect_float(parameter_data, 51)
            process_lfe = _hirc_effect_bool(parameter_data, 55)
            values = {
                "bands": bands,
                "outputGainDb": output_gain,
                "processLfe": process_lfe,
            }
            summary = (
                "; ".join(band_summaries)
                + f"; output {_hirc_effect_number(output_gain)} dB; LFE "
                + ("on" if process_lfe else "off")
            )
        elif plugin_class_id == 0x00810003:  # Meter
            mode = parameter_data[21]
            scope = parameter_data[22]
            if mode not in HIRC_METER_MODE_LABELS or scope not in HIRC_METER_SCOPE_LABELS:
                raise ValueError("invalid Meter mode or scope")
            output_game_parameter_id = unpack_from("<I", parameter_data, 24)[0]
            values = {
                "attackSeconds": _hirc_effect_float(parameter_data, 0),
                "releaseSeconds": _hirc_effect_float(parameter_data, 4),
                "minimumDb": _hirc_effect_float(parameter_data, 8),
                "maximumDb": _hirc_effect_float(parameter_data, 12),
                "holdSeconds": _hirc_effect_float(parameter_data, 16),
                "infiniteHold": _hirc_effect_bool(parameter_data, 20),
                "mode": mode,
                "modeLabel": HIRC_METER_MODE_LABELS[mode],
                "scope": scope,
                "scopeLabel": HIRC_METER_SCOPE_LABELS[scope],
                "applyDownstreamVolume": _hirc_effect_bool(parameter_data, 23),
                "outputGameParameterId": output_game_parameter_id,
                "outputGameParameterIdHex": f"0x{output_game_parameter_id:08x}",
            }
            summary = (
                f"{values['modeLabel']} / {values['scopeLabel']}; attack "
                f"{_hirc_effect_number(values['attackSeconds'])} s; release "
                f"{_hirc_effect_number(values['releaseSeconds'])} s; hold "
                f"{'infinite' if values['infiniteHold'] else _hirc_effect_number(values['holdSeconds']) + ' s'}; "
                f"range {_hirc_effect_number(values['minimumDb'])}.."
                f"{_hirc_effect_number(values['maximumDb'])} dB; output RTPC "
                f"{values['outputGameParameterIdHex']}"
            )
        elif plugin_class_id == 0x00880003:  # Pitch Shifter
            input_selection = unpack_from("<I", parameter_data, 0)[0]
            filter_type = unpack_from("<I", parameter_data, 22)[0]
            if input_selection not in HIRC_PITCH_INPUT_LABELS:
                raise ValueError("invalid Pitch Shifter input selection")
            if filter_type not in HIRC_EFFECT_FILTER_LABELS:
                raise ValueError("invalid Pitch Shifter filter type")
            values = {
                "inputSelection": input_selection,
                "inputSelectionLabel": HIRC_PITCH_INPUT_LABELS[input_selection],
                "dryLevelDb": _hirc_effect_float(parameter_data, 4),
                "wetLevelDb": _hirc_effect_float(parameter_data, 8),
                "delayTimeMilliseconds": _hirc_effect_float(parameter_data, 12),
                "delayDry": _hirc_effect_bool(parameter_data, 16),
                "processLfe": _hirc_effect_bool(parameter_data, 17),
                "pitchShiftCents": _hirc_effect_float(parameter_data, 18),
                "filterType": filter_type,
                "filterTypeLabel": HIRC_EFFECT_FILTER_LABELS[filter_type],
                "filterGainDb": _hirc_effect_float(parameter_data, 26),
                "filterFrequencyHz": _hirc_effect_float(parameter_data, 30),
                "filterQualityFactor": _hirc_effect_float(parameter_data, 34),
            }
            summary = (
                f"pitch {_hirc_effect_number(values['pitchShiftCents'])} cents; "
                f"{values['inputSelectionLabel']}; dry "
                f"{_hirc_effect_number(values['dryLevelDb'])} dB; wet "
                f"{_hirc_effect_number(values['wetLevelDb'])} dB; delay "
                f"{_hirc_effect_number(values['delayTimeMilliseconds'])} ms"
                + (" with dry aligned" if values["delayDry"] else "")
                + f"; {values['filterTypeLabel']} filter; LFE "
                + ("on" if values["processLfe"] else "off")
            )
        elif plugin_class_id == 0x008A0003:  # Harmonizer
            voices: list[dict[str, Any]] = []
            voice_summaries: list[str] = []
            for index, offset in enumerate((0, 25), start=1):
                filter_type = unpack_from("<I", parameter_data, offset + 9)[0]
                if filter_type not in HIRC_EFFECT_FILTER_LABELS:
                    raise ValueError("invalid Harmonizer filter type")
                voice = {
                    "voice": index,
                    "enabled": _hirc_effect_bool(parameter_data, offset),
                    "pitchShiftCents": _hirc_effect_float(parameter_data, offset + 1),
                    "gainDb": _hirc_effect_float(parameter_data, offset + 5),
                    "filterType": filter_type,
                    "filterTypeLabel": HIRC_EFFECT_FILTER_LABELS[filter_type],
                    "filterGainDb": _hirc_effect_float(parameter_data, offset + 13),
                    "filterFrequencyHz": _hirc_effect_float(parameter_data, offset + 17),
                    "filterQualityFactor": _hirc_effect_float(parameter_data, offset + 21),
                }
                voices.append(voice)
                voice_summaries.append(
                    f"V{index} "
                    + (
                        f"{_hirc_effect_number(voice['pitchShiftCents'])} cents, "
                        f"{_hirc_effect_number(voice['gainDb'])} dB"
                        if voice["enabled"] else "off"
                    )
                )
            input_selection = unpack_from("<I", parameter_data, 50)[0]
            window_size_samples = unpack_from("<I", parameter_data, 62)[0]
            if input_selection not in HIRC_HARMONIZER_INPUT_LABELS:
                raise ValueError("invalid Harmonizer input selection")
            if window_size_samples not in (256, 512, 1024, 2048, 4096):
                raise ValueError("invalid Harmonizer window size")
            values = {
                "voices": voices,
                "inputSelection": input_selection,
                "inputSelectionLabel": HIRC_HARMONIZER_INPUT_LABELS[input_selection],
                "dryLevelDb": _hirc_effect_float(parameter_data, 54),
                "wetLevelDb": _hirc_effect_float(parameter_data, 58),
                "windowSizeSamples": window_size_samples,
                "processLfe": _hirc_effect_bool(parameter_data, 66),
                "delayDry": _hirc_effect_bool(parameter_data, 67),
            }
            summary = (
                "; ".join(voice_summaries)
                + f"; {values['inputSelectionLabel']}; dry "
                f"{_hirc_effect_number(values['dryLevelDb'])} dB; wet "
                f"{_hirc_effect_number(values['wetLevelDb'])} dB; window "
                f"{window_size_samples} samples"
                + ("; dry aligned" if values["delayDry"] else "")
                + "; LFE " + ("on" if values["processLfe"] else "off")
            )
        elif plugin_class_id == 0x00870003:  # Stereo Delay
            left_input = unpack_from("<I", parameter_data, 0)[0]
            right_input = unpack_from("<I", parameter_data, 16)[0]
            filter_type = unpack_from("<I", parameter_data, 32)[0]
            if left_input not in HIRC_STEREO_DELAY_INPUT_LABELS:
                raise ValueError("invalid Stereo Delay left input")
            if right_input not in HIRC_STEREO_DELAY_INPUT_LABELS:
                raise ValueError("invalid Stereo Delay right input")
            if filter_type not in HIRC_EFFECT_FILTER_LABELS:
                raise ValueError("invalid Stereo Delay filter type")
            values = {
                "leftInput": left_input,
                "leftInputLabel": HIRC_STEREO_DELAY_INPUT_LABELS[left_input],
                "leftDelayTimeSeconds": _hirc_effect_float(parameter_data, 4),
                "leftFeedbackDb": _hirc_effect_float(parameter_data, 8),
                "leftCrossfeedDb": _hirc_effect_float(parameter_data, 12),
                "rightInput": right_input,
                "rightInputLabel": HIRC_STEREO_DELAY_INPUT_LABELS[right_input],
                "rightDelayTimeSeconds": _hirc_effect_float(parameter_data, 20),
                "rightFeedbackDb": _hirc_effect_float(parameter_data, 24),
                "rightCrossfeedDb": _hirc_effect_float(parameter_data, 28),
                "filterType": filter_type,
                "filterTypeLabel": HIRC_EFFECT_FILTER_LABELS[filter_type],
                "filterGainDb": _hirc_effect_float(parameter_data, 36),
                "filterFrequencyHz": _hirc_effect_float(parameter_data, 40),
                "filterQualityFactor": _hirc_effect_float(parameter_data, 44),
                "dryLevelDb": _hirc_effect_float(parameter_data, 48),
                "wetLevelDb": _hirc_effect_float(parameter_data, 52),
                "frontRearBalance": _hirc_effect_float(parameter_data, 56),
                "crossfeedEnabled": _hirc_effect_bool(parameter_data, 60),
                "feedbackEnabled": _hirc_effect_bool(parameter_data, 61),
            }
            summary = (
                f"L {_hirc_effect_number(values['leftDelayTimeSeconds'])} s / "
                f"R {_hirc_effect_number(values['rightDelayTimeSeconds'])} s; feedback "
                f"{'on' if values['feedbackEnabled'] else 'off'}; crossfeed "
                f"{'on' if values['crossfeedEnabled'] else 'off'}; "
                f"{values['filterTypeLabel']} "
                f"{_hirc_effect_number(values['filterFrequencyHz'])} Hz; dry "
                f"{_hirc_effect_number(values['dryLevelDb'])} dB; wet "
                f"{_hirc_effect_number(values['wetLevelDb'])} dB; front/rear "
                f"{_hirc_effect_number(values['frontRearBalance'])}"
            )
        elif plugin_class_id == 0x00760003:  # RoomVerb
            er_pattern = unpack_from("<I", parameter_data, 81)[0]
            quality = unpack_from("<I", parameter_data, 105)[0]
            if er_pattern not in HIRC_ROOMVERB_ER_PATTERN_LABELS:
                raise ValueError("invalid RoomVerb ER pattern")
            if quality not in (2, 4, 6, 8, 10, 12, 14, 16):
                raise ValueError("invalid RoomVerb quality")

            tone_bands: list[dict[str, Any]] = []
            tone_summaries: list[str] = []
            for index, (value_offset, enum_offset) in enumerate(
                ((16, 110), (28, 118), (40, 126)), start=1
            ):
                insert = unpack_from("<I", parameter_data, enum_offset)[0]
                curve = unpack_from("<I", parameter_data, enum_offset + 4)[0]
                if insert not in HIRC_ROOMVERB_TONE_INSERT_LABELS:
                    raise ValueError("invalid RoomVerb tone insertion")
                if curve not in HIRC_ROOMVERB_TONE_CURVE_LABELS:
                    raise ValueError("invalid RoomVerb tone curve")
                band = {
                    "band": index,
                    "insert": insert,
                    "insertLabel": HIRC_ROOMVERB_TONE_INSERT_LABELS[insert],
                    "curve": curve,
                    "curveLabel": HIRC_ROOMVERB_TONE_CURVE_LABELS[curve],
                    "gainDb": _hirc_effect_float(parameter_data, value_offset),
                    "frequencyHz": _hirc_effect_float(
                        parameter_data, value_offset + 4
                    ),
                    "qualityFactor": _hirc_effect_float(
                        parameter_data, value_offset + 8
                    ),
                }
                tone_bands.append(band)
                tone_summaries.append(
                    f"B{index} "
                    + (
                        f"{band['insertLabel']} {band['curveLabel']} "
                        f"{_hirc_effect_number(band['frequencyHz'])} Hz "
                        f"{_hirc_effect_number(band['gainDb'])} dB "
                        f"Q {_hirc_effect_number(band['qualityFactor'])}"
                        if insert else "off"
                    )
                )

            private_native_ranges = (
                (0, 5, "earlyReflectionTapPatternSynthesisInputs", ["0x00229b60"],
                 "exactNativeUseRolePublicNameUnresolved",
                 "0x00229b60 reads the five contiguous floats as two endpoint pairs plus a middle variation input, applies linear interpolation and seeded per-tap variation, then 0x0022a010 normalizes the generated values into the ER grid used by per-unit setup."),
                (5, 3, "nativeRoleUnobservedInAuditedRoomVerbPath", [],
                 "exactNativeReadBoundaryNoDirectReadObserved", ""),
                (8, 1, "sixChannelCoefficientDerivationInput", ["0x0022ab2e"],
                 "exactNativeUseRolePublicNameUnresolved",
                 "0x0022ab2e scales the value by 2*pi and a native divisor, then writes six coefficients of the form 1 - (2*pi * value / divisor) for ER/reverb unit initialization."),
                (9, 2, "earlyReflectionSecondaryPatternInputs", ["0x00229e20"],
                 "exactNativeUseRolePublicNameUnresolved",
                 "0x00229e20 reads the two values as a secondary ER pattern range/spread, builds seeded four-lane values per unit, and the caller converts them into the secondary per-unit pattern before allocation."),
            )
            private_native_rows: dict[int, dict[str, Any]] = {}
            for start_index, count, role, consumers, native_status, detail in private_native_ranges:
                for index in range(start_index, start_index + count):
                    private_native_rows[index] = {
                        "nativeStructOffset": 0x9C + index * 4,
                        "nativeUseRole": role,
                        "nativeUseStatus": native_status,
                        "nativeUseDetail": detail,
                        "nativeConsumerRvas": consumers,
                    }
            internal_tuning = []
            for index in range(11):
                serialized_offset = 142 + index * 4
                internal_tuning.append({
                    "setParamId": 100 + index,
                    "serializedOffset": serialized_offset,
                    "value": _hirc_effect_float(parameter_data, serialized_offset),
                    "semanticStatus": "exactValueMeaningUnresolved",
                    **private_native_rows[index],
                })
            values = {
                "reverb": {
                    "preDelayMilliseconds": _hirc_effect_float(parameter_data, 85),
                    "decayTimeSeconds": _hirc_effect_float(parameter_data, 0),
                    "highFrequencyDamping": _hirc_effect_float(parameter_data, 4),
                    "densityPercent": _hirc_effect_float(parameter_data, 97),
                    "roomShapePercent": _hirc_effect_float(parameter_data, 101),
                    "qualityReverberations": quality,
                    "diffusionPercent": _hirc_effect_float(parameter_data, 8),
                    "stereoWidthDegrees": _hirc_effect_float(parameter_data, 12),
                },
                "earlyReflections": {
                    "enabled": _hirc_effect_bool(parameter_data, 80),
                    "patternId": er_pattern,
                    "patternLabel": HIRC_ROOMVERB_ER_PATTERN_LABELS[er_pattern],
                    "roomSizePercent": _hirc_effect_float(parameter_data, 89),
                    "rearDelayMilliseconds": _hirc_effect_float(parameter_data, 93),
                },
                "tone": {
                    "enabled": _hirc_effect_bool(parameter_data, 109),
                    "bands": tone_bands,
                },
                "inputLevelsDb": {
                    "center": _hirc_effect_float(parameter_data, 134),
                    "lfe": _hirc_effect_float(parameter_data, 138),
                },
                "reverbLevelsDb": {
                    "front": _hirc_effect_float(parameter_data, 52),
                    "rear": _hirc_effect_float(parameter_data, 56),
                    "center": _hirc_effect_float(parameter_data, 60),
                    "lfe": _hirc_effect_float(parameter_data, 64),
                },
                "outputLevelsDb": {
                    "dry": _hirc_effect_float(parameter_data, 68),
                    "earlyReflections": _hirc_effect_float(parameter_data, 72),
                    "reverb": _hirc_effect_float(parameter_data, 76),
                },
                "internalTuningParameters": internal_tuning,
            }
            reverb = values["reverb"]
            early_reflections = values["earlyReflections"]
            output_levels = values["outputLevelsDb"]
            summary = (
                f"decay {_hirc_effect_number(reverb['decayTimeSeconds'])} s; "
                f"HF damping {_hirc_effect_number(reverb['highFrequencyDamping'])}; "
                f"density {_hirc_effect_number(reverb['densityPercent'])}%; "
                f"diffusion {_hirc_effect_number(reverb['diffusionPercent'])}%; "
                f"stereo {_hirc_effect_number(reverb['stereoWidthDegrees'])} deg; "
                f"pre-delay {_hirc_effect_number(reverb['preDelayMilliseconds'])} ms; ER "
                + (
                    f"{early_reflections['patternLabel']}, size "
                    f"{_hirc_effect_number(early_reflections['roomSizePercent'])}%, rear "
                    f"{_hirc_effect_number(early_reflections['rearDelayMilliseconds'])} ms"
                    if early_reflections["enabled"] else "off"
                )
                + f"; dry {_hirc_effect_number(output_levels['dry'])} dB; ER "
                f"{_hirc_effect_number(output_levels['earlyReflections'])} dB; reverb "
                f"{_hirc_effect_number(output_levels['reverb'])} dB; tone "
                + (
                    ", ".join(tone_summaries)
                    if values["tone"]["enabled"] else "off"
                )
            )
            parser_status = (
                "typedExactLayoutPartialSemanticsShippedAkSoundEngineSetParamsBlock"
            )
            parameter_boundary = "typedExactLayoutPartialAuthoredSemantics"
            semantic_boundary = (
                "All 37 public RoomVerb authoring properties are identified from "
                "SetParam dispatch plus runtime use. Native update-role evidence "
                "classifies IDs 100..104, 108, and 109..110 by exact consumer "
                "functions, while IDs 105..107 have no direct read in the audited "
                "RoomVerb update helpers; IDs 100..110 retain exact values and "
                "public parameter names remain unresolved."
            )
        elif plugin_class_id == 0x007E0003:  # Guitar Distortion
            eq_bands: list[dict[str, Any]] = []
            eq_summaries: dict[str, list[str]] = {
                "preDistortion": [],
                "postDistortion": [],
            }
            for index in range(6):
                offset = index * 17
                filter_type = unpack_from("<I", parameter_data, offset)[0]
                if filter_type not in HIRC_PARAMETRIC_EQ_FILTER_LABELS:
                    raise ValueError("invalid Guitar Distortion EQ filter type")
                section = "preDistortion" if index < 3 else "postDistortion"
                band_number = index + 1 if index < 3 else index - 2
                band = {
                    "section": section,
                    "band": band_number,
                    "filterType": filter_type,
                    "filterTypeLabel": HIRC_PARAMETRIC_EQ_FILTER_LABELS[
                        filter_type
                    ],
                    "gainDb": _hirc_effect_float_range(
                        parameter_data, offset + 4, -48.0, 48.0,
                        "Guitar Distortion EQ gain",
                    ),
                    "frequencyHz": _hirc_effect_float_range(
                        parameter_data, offset + 8, 20.0, 20000.0,
                        "Guitar Distortion EQ frequency",
                    ),
                    "qualityFactor": _hirc_effect_float_range(
                        parameter_data, offset + 12, 0.1, 20.0,
                        "Guitar Distortion EQ quality factor",
                    ),
                    "enabled": _hirc_effect_bool(parameter_data, offset + 16),
                }
                eq_bands.append(band)
                eq_summaries[section].append(
                    f"B{band_number} "
                    + (
                        f"{band['filterTypeLabel']} "
                        f"{_hirc_effect_number(band['frequencyHz'])} Hz "
                        f"{_hirc_effect_number(band['gainDb'])} dB "
                        f"Q {_hirc_effect_number(band['qualityFactor'])}"
                        if band["enabled"] else "off"
                    )
                )

            distortion_type = unpack_from("<I", parameter_data, 102)[0]
            if distortion_type not in HIRC_GUITAR_DISTORTION_TYPE_LABELS:
                raise ValueError("invalid Guitar Distortion type")
            values = {
                "preDistortionEqBands": eq_bands[:3],
                "postDistortionEqBands": eq_bands[3:],
                "distortionType": distortion_type,
                "distortionTypeLabel": HIRC_GUITAR_DISTORTION_TYPE_LABELS[
                    distortion_type
                ],
                "drivePercent": _hirc_effect_float_range(
                    parameter_data, 106, 0.0, 100.0,
                    "Guitar Distortion drive",
                ),
                "tonePercent": _hirc_effect_float_range(
                    parameter_data, 110, 0.0, 100.0,
                    "Guitar Distortion tone",
                ),
                "rectificationPercent": _hirc_effect_float_range(
                    parameter_data, 114, 0.0, 100.0,
                    "Guitar Distortion rectification",
                ),
                "outputGainDb": _hirc_effect_float_range(
                    parameter_data, 118, -24.0, 24.0,
                    "Guitar Distortion output gain",
                ),
                "wetDryMixPercent": _hirc_effect_float_range(
                    parameter_data, 122, 0.0, 100.0,
                    "Guitar Distortion wet/dry mix",
                ),
            }
            summary = (
                f"{values['distortionTypeLabel']}; drive "
                f"{_hirc_effect_number(values['drivePercent'])}%; tone "
                f"{_hirc_effect_number(values['tonePercent'])}%; rectification "
                f"{_hirc_effect_number(values['rectificationPercent'])}%; output "
                f"{_hirc_effect_number(values['outputGainDb'])} dB; wet/dry "
                f"{_hirc_effect_number(values['wetDryMixPercent'])}%; pre EQ "
                + ", ".join(eq_summaries["preDistortion"])
                + "; post EQ "
                + ", ".join(eq_summaries["postDistortion"])
            )
        elif plugin_class_id == 0x007F0003:  # Convolution Reverb
            pre_delay_ms = _hirc_effect_float_range(
                parameter_data, 0, 0.0, 1000.0,
                "Convolution Reverb pre-delay",
            )
            rear_delay_ms = _hirc_effect_float_range(
                parameter_data, 4, 0.0, 200.0,
                "Convolution Reverb rear delay",
            )
            reverb_type = unpack_from("<I", parameter_data, 48)[0]
            if reverb_type not in HIRC_CONVOLUTION_REVERB_TYPE_LABELS:
                raise ValueError("invalid Convolution Reverb type")
            private_native_rows = [
                {
                    "setParamId": 34,
                    "serializedOffset": 52,
                    "nativeStructOffset": 60,
                    "wrapperOffset": 76,
                    "value": _hirc_effect_float(parameter_data, 52),
                    "semanticStatus": "exactValueMeaningUnresolved",
                    "nativeUseRole": (
                        "privateRuntimeScalarForwardedToConvolutionEngineProcess"
                    ),
                    "nativeUseDetail": (
                        "SetParam ID 34 writes native +0x3c; wrapper code copies it "
                        "to +0x4c and passes it as the fifth float to the "
                        "convolution processor's virtual method."
                    ),
                    "nativeUseStatus": "exactForwardedScalarEngineReadUnobserved",
                    "nativeConsumerRvas": [
                        "0x00254a83",
                        "0x00254bd8",
                        "0x00258520",
                    ],
                },
                {
                    "setParamId": None,
                    "serializedOffset": 56,
                    "nativeStructOffset": 64,
                    "wrapperOffset": 80,
                    "rawCode": parameter_data[56],
                    "semanticStatus": "exactValueMeaningUnresolved",
                    "nativeUseRole": "serializedByteForwardedToConvolutionRuntimeState",
                    "nativeUseDetail": (
                        "Serialized byte 56 is copied through native +0x40 and "
                        "wrapper +0x50 into runtime state +0x8c before the "
                        "convolution state update."
                    ),
                    "nativeUseStatus": "exactForwardedRolePublicNameUnresolved",
                    "nativeConsumerRvas": ["0x00254d27"],
                },
            ]
            values = {
                "preDelayMilliseconds": pre_delay_ms,
                "rearDelayMilliseconds": rear_delay_ms,
                "inputLevelsDb": {
                    "center": _hirc_effect_float_range(
                        parameter_data, 12, -96.3, 0.0,
                        "Convolution Reverb center input level",
                    ),
                    "lfe": _hirc_effect_float_range(
                        parameter_data, 16, -96.3, 0.0,
                        "Convolution Reverb LFE input level",
                    ),
                },
                "inputSpreadDegrees": _hirc_effect_float_range(
                    parameter_data, 20, 0.0, 180.0,
                    "Convolution Reverb input spread",
                ),
                "reverbLevelsDb": {
                    "front": _hirc_effect_float_range(
                        parameter_data, 24, -96.3, 0.0,
                        "Convolution Reverb front level",
                    ),
                    "rear": _hirc_effect_float_range(
                        parameter_data, 28, -96.3, 0.0,
                        "Convolution Reverb rear level",
                    ),
                    "center": _hirc_effect_float_range(
                        parameter_data, 32, -96.3, 0.0,
                        "Convolution Reverb center level",
                    ),
                    "lfe": _hirc_effect_float_range(
                        parameter_data, 36, -96.3, 0.0,
                        "Convolution Reverb LFE level",
                    ),
                },
                "outputLevelsDb": {
                    "dry": _hirc_effect_float_range(
                        parameter_data, 40, -96.3, 24.0,
                        "Convolution Reverb dry level",
                    ),
                    "reverb": _hirc_effect_float_range(
                        parameter_data, 44, -96.3, 24.0,
                        "Convolution Reverb output level",
                    ),
                },
                "outputSpreadDegrees": _hirc_effect_float_range(
                    parameter_data, 8, 0.0, 180.0,
                    "Convolution Reverb output spread",
                ),
                "reverbType": reverb_type,
                "reverbTypeLabel": HIRC_CONVOLUTION_REVERB_TYPE_LABELS[reverb_type],
                "unresolvedParameters": private_native_rows,
            }
            input_levels = values["inputLevelsDb"]
            reverb_levels = values["reverbLevelsDb"]
            output_levels = values["outputLevelsDb"]
            summary = (
                f"{values['reverbTypeLabel']}; pre-delay "
                f"{_hirc_effect_number(pre_delay_ms)} ms; rear delay "
                f"{_hirc_effect_number(rear_delay_ms)} ms; input spread "
                f"{_hirc_effect_number(values['inputSpreadDegrees'])} deg; "
                f"input C {_hirc_effect_number(input_levels['center'])} dB / LFE "
                f"{_hirc_effect_number(input_levels['lfe'])} dB; reverb F "
                f"{_hirc_effect_number(reverb_levels['front'])} / R "
                f"{_hirc_effect_number(reverb_levels['rear'])} / C "
                f"{_hirc_effect_number(reverb_levels['center'])} / LFE "
                f"{_hirc_effect_number(reverb_levels['lfe'])} dB; dry "
                f"{_hirc_effect_number(output_levels['dry'])} dB; reverb "
                f"{_hirc_effect_number(output_levels['reverb'])} dB; output spread "
                f"{_hirc_effect_number(values['outputSpreadDegrees'])} deg"
            )
            parser_status = (
                "typedExactLayoutPartialSemanticsShippedAkSoundEngineSetParamsBlock"
            )
            parameter_boundary = "typedExactLayoutPartialAuthoredSemantics"
            semantic_boundary = (
                "The 13 public Convolution Reverb runtime properties are identified "
                "from the shipped SetParamsBlock/SetParam layout, property groups, "
                "and enforced ranges. SetParam ID 34 and serialized byte 56 retain "
                "exact values with native forwarding roles: the scalar is forwarded "
                "to both convolution processing paths while the current CPU engine "
                "body does not expose a read of that argument, and the final byte is "
                "copied into runtime state; public names and final DSP roles remain "
                "unresolved."
            )
        elif plugin_class_id == 0x00BA0003:  # Mastering Suite
            module_names = (
                "parametricEq", "multibandCompressor", "masterVolume", "limiter"
            )
            module_enabled = {
                name: _hirc_effect_bool(parameter_data, index)
                for index, name in enumerate(module_names)
            }

            eq_bands: list[dict[str, Any]] = []
            eq_summaries: list[str] = []
            for index in range(6):
                offset = 14 + index * 16
                filter_mode = unpack_from("<I", parameter_data, offset)[0]
                if filter_mode not in HIRC_MASTERING_EQ_FILTER_LABELS:
                    raise ValueError("invalid Mastering Suite EQ filter mode")
                band = {
                    "band": index + 1,
                    "enabled": _hirc_effect_bool(parameter_data, 8 + index),
                    "filterMode": filter_mode,
                    "filterModeLabel": HIRC_MASTERING_EQ_FILTER_LABELS[filter_mode],
                    "frequencyHz": _hirc_effect_float(parameter_data, offset + 4),
                    "gainDb": _hirc_effect_float(parameter_data, offset + 8),
                    "qualityFactor": _hirc_effect_float(parameter_data, offset + 12),
                }
                if band["frequencyHz"] <= 0.0 or band["qualityFactor"] <= 0.0:
                    raise ValueError("invalid Mastering Suite EQ frequency or Q")
                eq_bands.append(band)
                eq_summaries.append(
                    f"B{index + 1} "
                    + (
                        f"{band['filterModeLabel']} "
                        f"{_hirc_effect_number(band['frequencyHz'])} Hz "
                        f"{_hirc_effect_number(band['gainDb'])} dB "
                        f"Q {_hirc_effect_number(band['qualityFactor'])}"
                        if band["enabled"] else "off"
                    )
                )

            compressor_link_mode = unpack_from("<I", parameter_data, 114)[0]
            if compressor_link_mode not in HIRC_MASTERING_COMPRESSOR_LINK_LABELS:
                raise ValueError("invalid Mastering Suite compressor link mode")
            link_strength = _hirc_effect_float_range(
                parameter_data, 118, 0.0, 100.0,
                "Mastering Suite compressor link strength",
            )
            crossover_frequencies = [
                _hirc_effect_float(parameter_data, 127 + index * 4)
                for index in range(3)
            ]
            if (
                any(value <= 0.0 for value in crossover_frequencies)
                or crossover_frequencies != sorted(crossover_frequencies)
            ):
                raise ValueError("invalid Mastering Suite compressor crossovers")

            compressor_bands: list[dict[str, Any]] = []
            compressor_summaries: list[str] = []
            for index in range(4):
                offset = 139 + index * 24
                band = {
                    "band": index + 1,
                    "enabled": _hirc_effect_bool(parameter_data, 123 + index),
                    "thresholdDb": _hirc_effect_float(parameter_data, offset),
                    "ratio": _hirc_effect_float(parameter_data, offset + 4),
                    "attackSeconds": _hirc_effect_float(parameter_data, offset + 8),
                    "releaseSeconds": _hirc_effect_float(parameter_data, offset + 12),
                    "knee": _hirc_effect_float(parameter_data, offset + 16),
                    "makeupGainDb": _hirc_effect_float(parameter_data, offset + 20),
                }
                if (
                    band["ratio"] <= 0.0
                    or band["attackSeconds"] < 0.0
                    or band["releaseSeconds"] < 0.0
                    or band["knee"] < 0.0
                ):
                    raise ValueError("invalid Mastering Suite compressor band")
                compressor_bands.append(band)
                compressor_summaries.append(
                    f"B{index + 1} "
                    + (
                        f"{_hirc_effect_number(band['thresholdDb'])} dB, "
                        f"{_hirc_effect_number(band['ratio'])}:1"
                        if band["enabled"] else "off"
                    )
                )

            channel_gains = [
                {
                    "channelIndex": index,
                    "serializedOffset": 235 + index * 4,
                    "nativeStructOffset": 0x118 + index * 4,
                    "gainDb": _hirc_effect_float(parameter_data, 235 + index * 4),
                }
                for index in range(12)
            ]
            limiter_mode = unpack_from("<I", parameter_data, 283)[0]
            if limiter_mode not in HIRC_MASTERING_LIMITER_MODE_LABELS:
                raise ValueError("invalid Mastering Suite limiter mode")
            values = {
                "moduleEnabled": module_enabled,
                "parametricEq": {
                    "bands": eq_bands,
                },
                "multibandCompressor": {
                    "channelLinkMode": compressor_link_mode,
                    "channelLinkModeLabel": HIRC_MASTERING_COMPRESSOR_LINK_LABELS[
                        compressor_link_mode
                    ],
                    "linkStrengthPercent": link_strength,
                    "stereoLink": _hirc_effect_bool(parameter_data, 122),
                    "crossoverFrequenciesHz": crossover_frequencies,
                    "bands": compressor_bands,
                },
                "masterVolume": {
                    "gainDb": _hirc_effect_float(parameter_data, 231),
                    "channelGainsDb": channel_gains,
                    "channelOrderStatus": "serializedWwiseChannelIndex",
                },
                "limiter": {
                    "mode": limiter_mode,
                    "modeLabel": HIRC_MASTERING_LIMITER_MODE_LABELS[limiter_mode],
                    "thresholdDb": _hirc_effect_float(parameter_data, 287),
                    "attackSeconds": _hirc_effect_float(parameter_data, 291),
                    "releaseSeconds": _hirc_effect_float(parameter_data, 295),
                    "outputGainDb": _hirc_effect_float(parameter_data, 299),
                    "linkChannels": _hirc_effect_bool(parameter_data, 303),
                },
                "unresolvedParameters": [
                    {
                        "setParamId": 100,
                        "serializedOffset": 4,
                        "nativeStructOffset": 24,
                        "rawCode": unpack_from("<I", parameter_data, 4)[0],
                        "semanticStatus": "exactValueMeaningUnresolved",
                        "nativeUseRole": "privateUint32StoredAtNativeStructOffset",
                        "nativeUseStatus": (
                            "nativeSetParamStorageOnlyNoDirectReadObserved"
                        ),
                        "nativeConsumerRvas": [],
                    },
                    {
                        "setParamId": 200,
                        "serializedOffset": 110,
                        "nativeStructOffset": 136,
                        "rawCode": unpack_from("<I", parameter_data, 110)[0],
                        "semanticStatus": "exactValueMeaningUnresolved",
                        "nativeUseRole": "privateUint32StoredAtNativeStructOffset",
                        "nativeUseStatus": (
                            "nativeSetParamStorageOnlyNoDirectReadObserved"
                        ),
                        "nativeConsumerRvas": [],
                    },
                ],
            }
            enabled_modules = [
                name for name, enabled in module_enabled.items() if enabled
            ]
            compressor = values["multibandCompressor"]
            master_volume = values["masterVolume"]
            limiter = values["limiter"]
            summary = (
                "modules " + ", ".join(enabled_modules or ["all bypassed"])
                + "; EQ " + ", ".join(eq_summaries)
                + "; compressor " + ", ".join(compressor_summaries)
                + f"; {compressor['channelLinkModeLabel']}, strength "
                f"{_hirc_effect_number(compressor['linkStrengthPercent'])}%, stereo "
                + ("linked" if compressor["stereoLink"] else "independent")
                + f"; master {_hirc_effect_number(master_volume['gainDb'])} dB; "
                f"limiter {limiter['modeLabel']} at "
                f"{_hirc_effect_number(limiter['thresholdDb'])} dB, channels "
                + ("linked" if limiter["linkChannels"] else "independent")
            )
            parser_status = (
                "typedExactLayoutPartialSemanticsShippedAkSoundEngineSetParamsBlock"
            )
            parameter_boundary = "typedExactLayoutPartialAuthoredSemantics"
            semantic_boundary = (
                "The four public Mastering Suite modules, six EQ bands, four "
                "multiband-compressor bands, master/channel gains, and limiter "
                "controls are identified from the shipped SetParamsBlock/SetParam "
                "layout and public module contract. SetParam IDs 100 and 200 "
                "retain exact uint32 values with exact native storage-only evidence "
                "but no direct read observed in the audited runtime; their private "
                "meanings remain unresolved. SetParamsBlock maps serialized channel "
                "gains 235..279 to native +0x118..+0x144 with stride 4, but speaker "
                "names are not inferred for those 12 slots."
            )
        elif plugin_class_id == 0x00730003:  # Matrix Reverb
            number_of_delays = unpack_from("<I", parameter_data, 8)[0]
            if number_of_delays not in (4, 8, 12, 16):
                raise ValueError("invalid Matrix Reverb delay count")
            custom_delay_times_raw = unpack_from("<I", parameter_data, 25)[0]
            if custom_delay_times_raw not in (0, 1):
                raise ValueError("invalid Matrix Reverb custom-delay flag")
            expected_size = 29 + (number_of_delays * 4 if custom_delay_times_raw else 0)
            if len(parameter_data) != expected_size:
                raise ValueError("Matrix Reverb parameter size does not match delay mode")
            delay_times_ms = [
                _hirc_effect_float(parameter_data, 29 + index * 4)
                for index in range(number_of_delays)
            ] if custom_delay_times_raw else []
            values = {
                "reverbTimeSeconds": _hirc_effect_float(parameter_data, 0),
                "highFrequencyRatio": _hirc_effect_float(parameter_data, 4),
                "numberOfDelays": number_of_delays,
                "dryLevelDb": _hirc_effect_float(parameter_data, 12),
                "wetLevelDb": _hirc_effect_float(parameter_data, 16),
                "preDelaySeconds": _hirc_effect_float(parameter_data, 20),
                "processLfe": _hirc_effect_bool(parameter_data, 24),
                "customDelayTimes": bool(custom_delay_times_raw),
                "delayTimesMilliseconds": delay_times_ms,
            }
            summary = (
                f"reverb {_hirc_effect_number(values['reverbTimeSeconds'])} s; HF ratio "
                f"{_hirc_effect_number(values['highFrequencyRatio'])}; "
                f"{number_of_delays} delays"
                + (" custom" if custom_delay_times_raw else " built-in")
                + f"; dry {_hirc_effect_number(values['dryLevelDb'])} dB; wet "
                f"{_hirc_effect_number(values['wetLevelDb'])} dB; pre-delay "
                f"{_hirc_effect_number(values['preDelaySeconds'])} s; LFE "
                + ("on" if values["processLfe"] else "off")
            )
        else:
            return None
    except (ValueError, IndexError):
        return None

    return {
        "parameterParserStatus": parser_status,
        "parameterSchema": contract["schema"],
        "parameterValues": values,
        "parameterSummary": summary,
        "parameterSetParamsBlockRva": contract["setParamsBlockRva"],
        "parameterBoundary": parameter_boundary,
        **({"parameterSemanticBoundary": semantic_boundary} if semantic_boundary else {}),
        "parameterRuntimeBoundary": (
            "authoredBaseValuesOnly; live RTPC/State changes, bypass, platform "
            "DSP, and audibility are not observed"
        ),
    }

def _hirc_v150_plugin_media_dependency_prefix(
    plugin_class_id: int,
    trailing_data: bytes,
) -> dict[str, Any] | None:
    """Decode the bounded v150 plug-in media dependency prefix.

    Each row is one U8 plug-in data index followed by one U32 media ID.  These
    IDs are plug-in inputs (for example, a Convolution Reverb impulse response),
    not Sound-source WEM leaves and therefore never enter playable media links.
    """

    if not trailing_data:
        return None
    dependency_count = trailing_data[0]
    prefix_byte_length = 1 + dependency_count * 5
    if prefix_byte_length > len(trailing_data):
        return None
    semantic_role = (
        "impulseResponseMedia"
        if plugin_class_id == 0x007F0003
        else "pluginDataMedia"
    )
    dependencies = []
    for index in range(dependency_count):
        offset = 1 + index * 5
        plugin_data_index = trailing_data[offset]
        media_id = unpack_from("<I", trailing_data, offset + 1)[0]
        dependencies.append({
            "pluginDataIndex": plugin_data_index,
            "mediaId": media_id,
            "mediaIdHex": f"0x{media_id:08x}",
            "semanticRole": semantic_role,
        })
    return {
        "pluginMediaParserStatus": "typedExactV150PluginMediaDependencyPrefix",
        "pluginMediaDependencyCount": dependency_count,
        "pluginMediaDependencies": dependencies,
        "pluginMediaPrefixByteLength": prefix_byte_length,
        "postPluginMediaTrailingByteLength": (
            len(trailing_data) - prefix_byte_length
        ),
        "pluginMediaBoundary": (
            "Exact bank plug-in data dependencies; IDs are not playable Sound "
            "WEM leaves, and runtime loading, DSP use, and audibility are not observed."
        ),
    }

def hirc_v150_effect_definition(
    object_type: int,
    data: bytes,
) -> dict[str, Any] | None:
    """Decode exact class, parameter, and bounded media-dependency prefixes.

    HIRC types 16 and 17 use the same bounded plug-in class ID plus parameter
    blob prefix.  Parameter bytes stay fingerprinted until a plug-in-specific
    writer contract is available.  A valid trailing media prefix is kept as
    plug-in data and never promoted to a playable Sound-source leaf.
    """

    if object_type not in (16, 17) or len(data) < 8:
        return None
    plugin_class_id = unpack_from("<I", data, 0)[0]
    parameter_size = unpack_from("<I", data, 4)[0]
    if parameter_size > len(data) - 8:
        return None
    parameter_data = data[8 : 8 + parameter_size]
    trailing_data = data[8 + parameter_size :]
    plugin_type = plugin_class_id & 0x0F
    if plugin_type != 3:
        # HIRC type 17 also carries custom source plug-ins in the current
        # corpus.  They are playback sources, not post-processing effects, and
        # must not pollute the direct-FX definition catalog.
        return None
    company_id = (plugin_class_id >> 4) & 0x0FFF
    plugin_id = plugin_class_id >> 16
    if plugin_class_id in HIRC_BUILTIN_EFFECT_PLUGIN_LABELS:
        plugin_name = HIRC_BUILTIN_EFFECT_PLUGIN_LABELS[plugin_class_id]
        name_evidence = "shippedAkSoundEngineRegistrationClassId"
    else:
        plugin_name = HIRC_SOURCE_PLUGIN_LABELS.get(plugin_class_id)
        name_evidence = "knownWwiseSourceClassId" if plugin_name else None
    definition = {
        "parserStatus": "typedExactV150PluginParameterPrefix",
        "objectType": object_type,
        "objectTypeLabel": HIRC_OBJECT_TYPE_LABELS.get(
            object_type, f"type{object_type}"
        ),
        "pluginClassId": plugin_class_id,
        "pluginClassIdHex": f"0x{plugin_class_id:08x}",
        "pluginType": plugin_type,
        "pluginTypeLabel": HIRC_PLUGIN_TYPE_LABELS.get(
            plugin_type, f"pluginType{plugin_type}"
        ),
        "companyId": company_id,
        "pluginId": plugin_id,
        "pluginName": plugin_name,
        "pluginNameEvidence": name_evidence,
        "parameterByteLength": parameter_size,
        "parameterSha256": hashlib.sha256(parameter_data).hexdigest(),
        "trailingByteLength": len(trailing_data),
        "parameterBoundary": "opaquePluginSpecificPayload",
    }
    plugin_media = _hirc_v150_plugin_media_dependency_prefix(
        plugin_class_id, trailing_data
    )
    if plugin_media is not None:
        definition.update(plugin_media)
    decoded_parameters = decode_hirc_v150_effect_parameters(
        plugin_class_id, parameter_data
    )
    if decoded_parameters is not None:
        definition.update(decoded_parameters)
        definition["parameterBoundary"] = decoded_parameters.get(
            "parameterBoundary", "typedExactAuthoredBaseValues"
        )
    return definition

def hirc_v150_music_track(data: bytes) -> dict[str, Any] | None:
    """Decode the typed prefix of a v150 MusicTrack.

    This reaches every AkBankSourceData row and the NodeBase parent without
    interpreting the later property/RTPC payload.  Every variable-length list
    is bounded against the enclosing HIRC object's bytes and failures return
    ``None`` rather than searching for media-looking integers.
    """

    try:
        if len(data) < 5:
            raise ValueError("truncated v150 MusicTrack header")
        flags = data[0]
        source_count, offset = _hirc_v150_u32(data, 1)
        sources: list[dict[str, Any]] = []
        for _ in range(source_count):
            parsed_source = _hirc_v150_bank_source_data(data, offset)
            if not parsed_source:
                raise ValueError("truncated v150 MusicTrack source")
            source, offset = parsed_source
            sources.append({**source, "mediaId": source["sourceId"]})

        playlist_count, offset = _hirc_v150_u32(data, offset)
        playlist_items: list[dict[str, Any]] = []
        for _ in range(playlist_count):
            if offset + 44 > len(data):
                raise ValueError("truncated v150 MusicTrack playlist")
            playlist_items.append({
                "trackId": unpack_from("<I", data, offset)[0],
                "mediaId": unpack_from("<I", data, offset + 4)[0],
                "eventId": unpack_from("<I", data, offset + 8)[0],
            })
            offset += 44  # IDs above + four F64 clip timing values.
        subtrack_count = None
        if playlist_count:
            subtrack_count, offset = _hirc_v150_u32(data, offset)

        automation_count, offset = _hirc_v150_u32(data, offset)
        automation_point_count = 0
        for _ in range(automation_count):
            if offset + 12 > len(data):
                raise ValueError("truncated v150 MusicTrack automation header")
            point_count = unpack_from("<I", data, offset + 8)[0]
            offset += 12
            point_bytes = point_count * 12  # F32 From + F32 To + U32 interpolation.
            if offset + point_bytes > len(data):
                raise ValueError("truncated v150 MusicTrack automation points")
            offset += point_bytes
            automation_point_count += point_count

        node_base_offset = offset
        parent_id, _parent_end = _hirc_v150_node_base_parent(data, node_base_offset)
        return {
            "flags": flags,
            "parentId": parent_id,
            "nodeBaseOffset": node_base_offset,
            "sourceCount": source_count,
            "sources": sources,
            "playlistItemCount": playlist_count,
            "playlistItems": playlist_items,
            "subtrackCount": subtrack_count,
            "automationCount": automation_count,
            "automationPointCount": automation_point_count,
        }
    except (ValueError, OverflowError):
        return None

def _hirc_v150_music_parent_id(data: bytes) -> int | None:
    try:
        # v150 MusicSegment/Switch/RanSeq begin with a U8 MIDI override flag,
        # followed by the common NodeBase prefix.
        parent_id, _offset = _hirc_v150_node_base_parent(data, 1)
        return parent_id
    except (ValueError, OverflowError):
        return None

def hirc_object_parent_id(object_type: int, data: bytes) -> int | None:
    if object_type == 2:
        source = hirc_v150_sound_source(data)
        return int(source["parentId"]) if source else None
    elif object_type == 11:
        track = hirc_v150_music_track(data)
        return int(track["parentId"]) if track else None
    elif object_type in HIRC_MUSIC_PARENT_NODE_TYPES:
        return _hirc_v150_music_parent_id(data)
    elif object_type in HIRC_TYPED_CHILD_CONTAINER_TYPES:
        try:
            parent_id, _offset = _hirc_v150_node_base_parent(data, 0)
            return parent_id
        except (ValueError, OverflowError):
            return None
    else:
        return None

def _hirc_v150_node_base_offset(
    object_type: int,
    data: bytes,
) -> int | None:
    """Return the type-defined NodeBase offset for a v150 audio node."""

    if object_type == 2:
        source = hirc_v150_sound_source(data)
        return int(source["nodeBaseOffset"]) if source else None
    if object_type == 11:
        track = hirc_v150_music_track(data)
        return int(track["nodeBaseOffset"]) if track else None
    if object_type in HIRC_MUSIC_PARENT_NODE_TYPES:
        return 1
    if object_type in HIRC_TYPED_CHILD_CONTAINER_TYPES:
        return 0
    return None

def _hirc_v150_node_aux_sends(
    data: bytes,
    node_base_end: int,
) -> dict[str, Any]:
    """Decode v150 NodeBase fields through authored Auxiliary Sends.

    The variable prefix is bounded by its own serialized counts.  Field-level
    diagnostics deliberately identify the failed gate and byte offset so a
    layout drift cannot silently turn arbitrary node-tail bytes into routes.
    """

    offset = node_base_end
    if offset >= len(data):
        raise ValueError(
            f"v150 Aux Send gate priorityFlags truncated at offset {offset}"
        )
    priority_flags_raw = data[offset]
    offset += 1

    if offset >= len(data):
        raise ValueError(
            f"v150 Aux Send gate propertyCount truncated at offset {offset}"
        )
    property_count = data[offset]
    offset += 1
    property_bytes = property_count * 5
    if offset + property_bytes > len(data):
        raise ValueError(
            "v150 Aux Send gate propertyBundle truncated: "
            f"count={property_count} offset={offset} "
            f"required={property_bytes} remaining={len(data) - offset}"
        )
    property_id_offset = offset
    property_ids = list(data[offset:offset + property_count])
    property_value_offset = property_id_offset + property_count
    properties: list[dict[str, Any]] = []
    for index, property_id in enumerate(property_ids):
        raw = unpack_from("<I", data, property_value_offset + index * 4)[0]
        float_value = unpack_from("<f", data, property_value_offset + index * 4)[0]
        property_label = HIRC_INITIAL_PROPERTY_LABELS.get(
            property_id, f"property{property_id}"
        )
        value_encoding = "float"
        if property_label in HIRC_INITIAL_PROPERTY_U32_LABELS:
            value_encoding = "u32Id"
        elif raw <= 0x00100000 and math.isfinite(float_value) and abs(float_value) < 1e-20:
            value_encoding = "u32Likely"
        properties.append({
            "propertyIndex": index,
            "propertyId": property_id,
            "propertyIdHex": f"0x{property_id:02x}",
            "propertyLabel": property_label,
            "rawU32": raw,
            "rawHex": f"0x{raw:08x}",
            "floatValue": float_value if math.isfinite(float_value) else None,
            "valueEncoding": value_encoding,
        })
    offset += property_count + property_count * 4

    if offset >= len(data):
        raise ValueError(
            f"v150 Aux Send gate rangedPropertyCount truncated at offset {offset}"
        )
    ranged_property_count = data[offset]
    offset += 1
    ranged_property_bytes = ranged_property_count * 9
    if offset + ranged_property_bytes > len(data):
        raise ValueError(
            "v150 Aux Send gate rangedPropertyBundle truncated: "
            f"count={ranged_property_count} offset={offset} "
            f"required={ranged_property_bytes} remaining={len(data) - offset}"
        )
    ranged_property_id_offset = offset
    ranged_property_ids = list(data[offset:offset + ranged_property_count])
    ranged_property_value_offset = ranged_property_id_offset + ranged_property_count
    ranged_properties: list[dict[str, Any]] = []
    for index, property_id in enumerate(ranged_property_ids):
        minimum_raw = unpack_from(
            "<I", data, ranged_property_value_offset + index * 8
        )[0]
        maximum_raw = unpack_from(
            "<I", data, ranged_property_value_offset + index * 8 + 4
        )[0]
        minimum_float = unpack_from(
            "<f", data, ranged_property_value_offset + index * 8
        )[0]
        maximum_float = unpack_from(
            "<f", data, ranged_property_value_offset + index * 8 + 4
        )[0]
        ranged_properties.append({
            "propertyIndex": index,
            "propertyId": property_id,
            "propertyIdHex": f"0x{property_id:02x}",
            "propertyLabel": HIRC_INITIAL_PROPERTY_LABELS.get(
                property_id, f"property{property_id}"
            ),
            "minimumRawU32": minimum_raw,
            "minimumRawHex": f"0x{minimum_raw:08x}",
            "minimumFloat": minimum_float if math.isfinite(minimum_float) else None,
            "maximumRawU32": maximum_raw,
            "maximumRawHex": f"0x{maximum_raw:08x}",
            "maximumFloat": maximum_float if math.isfinite(maximum_float) else None,
            "valueEncoding": "floatOrTypedUnionRawU32",
        })
    offset += ranged_property_count + ranged_property_count * 8

    positioning_offset = offset
    if offset >= len(data):
        raise ValueError(
            f"v150 Aux Send gate positioningBits truncated at offset {offset}"
        )
    positioning_bits_raw = data[offset]
    offset += 1
    override_positioning = bool(positioning_bits_raw & 0x01)
    listener_relative_routing = bool(positioning_bits_raw & 0x02)
    positioning_3d_bits_raw: int | None = None
    automation_vertex_count = 0
    automation_playlist_item_count = 0
    if override_positioning and listener_relative_routing:
        if offset >= len(data):
            raise ValueError(
                f"v150 Aux Send gate positioning3dBits truncated at offset {offset}"
            )
        positioning_3d_bits_raw = data[offset]
        offset += 1
        position_type = (positioning_bits_raw >> 5) & 0x03
        if position_type:
            fixed_automation_bytes = 1 + 4 + 4
            if offset + fixed_automation_bytes > len(data):
                raise ValueError(
                    "v150 Aux Send gate positioningAutomationHeader truncated: "
                    f"offset={offset} required={fixed_automation_bytes} "
                    f"remaining={len(data) - offset}"
                )
            offset += 1 + 4
            automation_vertex_count = unpack_from("<I", data, offset)[0]
            offset += 4
            vertex_bytes = automation_vertex_count * 16
            if offset + vertex_bytes + 4 > len(data):
                raise ValueError(
                    "v150 Aux Send gate positioningVertices truncated: "
                    f"count={automation_vertex_count} offset={offset} "
                    f"requiredWithPlaylistCount={vertex_bytes + 4} "
                    f"remaining={len(data) - offset}"
                )
            offset += vertex_bytes
            automation_playlist_item_count = unpack_from("<I", data, offset)[0]
            offset += 4
            playlist_bytes = automation_playlist_item_count * 20
            if offset + playlist_bytes > len(data):
                raise ValueError(
                    "v150 Aux Send gate positioningPlaylist truncated: "
                    f"count={automation_playlist_item_count} offset={offset} "
                    f"required={playlist_bytes} remaining={len(data) - offset}"
                )
            offset += playlist_bytes

    aux_params_offset = offset
    if offset >= len(data):
        raise ValueError(
            f"v150 Aux Send gate auxFlags truncated at offset {offset}"
        )
    aux_flags_raw = data[offset]
    offset += 1
    unknown_aux_flag_bits = aux_flags_raw & ~0x1F
    if unknown_aux_flag_bits:
        raise ValueError(
            "v150 Aux Send gate auxFlags unknown bits: "
            f"offset={aux_params_offset} value=0x{aux_flags_raw:02x} "
            f"unknown=0x{unknown_aux_flag_bits:02x}"
        )

    has_user_aux_slots = bool(aux_flags_raw & 0x08)
    user_aux_bus_ids: list[int] = []
    user_defined_aux_sends: list[dict[str, Any]] = []
    if has_user_aux_slots:
        required = 4 * 4
        if offset + required > len(data):
            raise ValueError(
                "v150 Aux Send gate userDefinedSlots truncated: "
                f"offset={offset} required={required} remaining={len(data) - offset}"
            )
        user_aux_bus_ids = [
            unpack_from("<I", data, offset + slot_index * 4)[0]
            for slot_index in range(4)
        ]
        user_defined_aux_sends = [
            {
                "slotIndex": slot_index,
                "busId": bus_id,
                "busIdHex": f"0x{bus_id:08x}",
                "serializationStatus": "exactAuthoredUserDefinedAuxBusId",
            }
            for slot_index, bus_id in enumerate(user_aux_bus_ids)
            if bus_id
        ]
        offset += required

    reflections_aux_bus_id, offset = _hirc_v150_u32(data, offset)
    return {
        "parserStatus": "typedExactV150NodeAuxParams",
        "priorityFlagsRaw": priority_flags_raw,
        "propertyCount": property_count,
        "propertyIds": property_ids,
        "properties": properties,
        "rangedPropertyCount": ranged_property_count,
        "rangedPropertyIds": ranged_property_ids,
        "rangedProperties": ranged_properties,
        "positioningOffset": positioning_offset,
        "positioningBitsRaw": positioning_bits_raw,
        "overridePositioning": override_positioning,
        "listenerRelativeRouting": listener_relative_routing,
        "positioning3dBitsRaw": positioning_3d_bits_raw,
        "automationVertexCount": automation_vertex_count,
        "automationPlaylistItemCount": automation_playlist_item_count,
        "auxParamsOffset": aux_params_offset,
        "auxParamsByteLength": offset - aux_params_offset,
        "auxParamsEndOffset": offset,
        "auxFlagsRaw": aux_flags_raw,
        "overrideGameDefinedAuxSends": bool(aux_flags_raw & 0x01),
        "useGameDefinedAuxSends": bool(aux_flags_raw & 0x02),
        "overrideUserDefinedAuxSends": bool(aux_flags_raw & 0x04),
        "hasUserDefinedAuxSendSlots": has_user_aux_slots,
        "overrideEarlyReflectionsAuxBus": bool(aux_flags_raw & 0x10),
        "userDefinedAuxBusIds": user_aux_bus_ids,
        "userDefinedAuxBusIdHexes": [
            f"0x{bus_id:08x}" if bus_id else None for bus_id in user_aux_bus_ids
        ],
        "userDefinedAuxSends": user_defined_aux_sends,
        "reflectionsAuxBusId": reflections_aux_bus_id,
        "reflectionsAuxBusIdHex": (
            f"0x{reflections_aux_bus_id:08x}" if reflections_aux_bus_id else None
        ),
        "gameDefinedAssignmentBoundary": (
            "runtimeAuxBusIdsAndControlValuesNotSerialized"
            if aux_flags_raw & 0x02 else "gameDefinedAuxSendsDisabledAtThisNode"
        ),
        "flagSemanticBoundary": (
            "bits2To4ExactCurrentLayout;Bits0To1NamedByLegacyFieldOrderContinuity"
        ),
    }

def _hirc_v150_node_state_rtpc(
    data: bytes,
    post_aux_offset: int,
) -> dict[str, Any]:
    """Decode v150 AdvSettings, StateChunk, and InitialRTPC fail-closed."""

    offset = post_aux_offset

    def need(size: int, label: str) -> None:
        if offset + size > len(data):
            raise ValueError(
                f"v150 State/RTPC gate {label} truncated: offset={offset} "
                f"required={size} remaining={len(data) - offset}"
            )

    def take_u8(label: str) -> int:
        nonlocal offset
        need(1, label)
        value = data[offset]
        offset += 1
        return value

    def take_u16(label: str) -> int:
        nonlocal offset
        need(2, label)
        value = unpack_from("<H", data, offset)[0]
        offset += 2
        return value

    def take_u32(label: str) -> int:
        nonlocal offset
        need(4, label)
        value = unpack_from("<I", data, offset)[0]
        offset += 4
        return value

    def take_f32(label: str) -> float:
        nonlocal offset
        need(4, label)
        value = float(unpack_from("<f", data, offset)[0])
        value_offset = offset
        offset += 4
        if not math.isfinite(value):
            raise ValueError(
                f"v150 State/RTPC gate {label} non-finite at offset {value_offset}"
            )
        return value

    def take_varuint(label: str) -> int:
        start = offset
        value = 0
        for index in range(5):
            byte = take_u8(label)
            value |= (byte & 0x7F) << (index * 7)
            if not byte & 0x80:
                return value
        raise ValueError(
            f"v150 State/RTPC gate {label} invalid varuint at offset {start}"
        )

    adv_settings_offset = offset
    adv_flags_raw = take_u8("advFlags")
    virtual_queue_behavior = take_u8("virtualQueueBehavior")
    max_num_instances = take_u16("maxNumInstances")
    below_threshold_behavior = take_u8("belowThresholdBehavior")
    analysis_flags_raw = take_u8("analysisFlags")
    if virtual_queue_behavior > 2:
        raise ValueError(
            "v150 State/RTPC gate virtualQueueBehavior invalid: "
            f"offset={adv_settings_offset + 1} value={virtual_queue_behavior}"
        )
    if below_threshold_behavior > 3:
        raise ValueError(
            "v150 State/RTPC gate belowThresholdBehavior invalid: "
            f"offset={adv_settings_offset + 4} value={below_threshold_behavior}"
        )
    adv_settings = {
        "offset": adv_settings_offset,
        "byteLength": 6,
        "flagsRaw": adv_flags_raw,
        "killNewest": bool(adv_flags_raw & 0x01),
        "useVirtualBehavior": bool(adv_flags_raw & 0x02),
        "ignoreParentMaxNumInstances": bool(adv_flags_raw & 0x08),
        "overrideParentVirtualVoiceBehavior": bool(adv_flags_raw & 0x10),
        "unknownFlagBits": adv_flags_raw & ~0x1B,
        "virtualQueueBehavior": virtual_queue_behavior,
        "virtualQueueBehaviorLabel": {
            0: "fromBeginning", 1: "fromElapsedTime", 2: "resume",
        }[virtual_queue_behavior],
        "maxNumInstances": max_num_instances,
        "belowThresholdBehavior": below_threshold_behavior,
        "belowThresholdBehaviorLabel": {
            0: "continueToPlay",
            1: "killVoice",
            2: "setAsVirtualVoice",
            3: "killIfOneShotElseVirtual",
        }[below_threshold_behavior],
        "analysisFlagsRaw": analysis_flags_raw,
        "overrideHdrEnvelope": bool(analysis_flags_raw & 0x01),
        "overrideAnalysis": bool(analysis_flags_raw & 0x02),
        "normalizeLoudness": bool(analysis_flags_raw & 0x04),
        "enableEnvelope": bool(analysis_flags_raw & 0x08),
        "unknownAnalysisFlagBits": analysis_flags_raw & ~0x0F,
    }

    state_chunk_offset = offset
    state_property_count = take_varuint("statePropertyCount")
    state_properties: list[dict[str, Any]] = []
    for property_index in range(state_property_count):
        parameter_id = take_varuint("statePropertyId")
        accum = take_u8("statePropertyAccum")
        in_db_raw = take_u8("statePropertyInDb")
        if accum not in HIRC_RTPC_ACCUM_LABELS or in_db_raw not in (0, 1):
            raise ValueError(
                "v150 State/RTPC gate stateProperty invalid: "
                f"index={property_index} parameterId={parameter_id} "
                f"accum={accum} inDb={in_db_raw} offset={offset - 2}"
            )
        state_properties.append({
            "propertyIndex": property_index,
            "parameterId": parameter_id,
            "parameterLabel": HIRC_RTPC_PARAMETER_LABELS.get(
                parameter_id, f"parameter{parameter_id}"
            ),
            "accum": accum,
            "accumLabel": HIRC_RTPC_ACCUM_LABELS[accum],
            "inDb": bool(in_db_raw),
            "inDbRaw": in_db_raw,
        })

    state_group_count = take_varuint("stateGroupCount")
    state_groups: list[dict[str, Any]] = []
    state_count = 0
    state_value_count = 0
    for group_index in range(state_group_count):
        group_id = take_u32("stateGroupId")
        sync_type = take_u8("stateGroupSyncType")
        if sync_type not in HIRC_STATE_SYNC_TYPE_LABELS:
            raise ValueError(
                "v150 State/RTPC gate stateGroupSyncType invalid: "
                f"groupIndex={group_index} value={sync_type} offset={offset - 1}"
            )
        group_state_count = take_varuint("stateCount")
        states: list[dict[str, Any]] = []
        for state_index in range(group_state_count):
            state_id = take_u32("stateId")
            value_count = take_u16("stateValueCount")
            need(value_count * 6, "stateValues")
            property_ids = [
                take_u16("stateValuePropertyId") for _ in range(value_count)
            ]
            values = [take_f32("stateValue") for _ in range(value_count)]
            state_values = [
                {
                    "valueIndex": value_index,
                    "parameterId": parameter_id,
                    "parameterLabel": HIRC_RTPC_PARAMETER_LABELS.get(
                        parameter_id, f"parameter{parameter_id}"
                    ),
                    "value": values[value_index],
                }
                for value_index, parameter_id in enumerate(property_ids)
            ]
            states.append({
                "stateIndex": state_index,
                "stateId": state_id,
                "stateIdHex": f"0x{state_id:08x}",
                "valueCount": value_count,
                "values": state_values,
            })
            state_value_count += value_count
        state_groups.append({
            "groupIndex": group_index,
            "groupId": group_id,
            "groupIdHex": f"0x{group_id:08x}",
            "syncType": sync_type,
            "syncTypeLabel": HIRC_STATE_SYNC_TYPE_LABELS[sync_type],
            "stateCount": group_state_count,
            "states": states,
        })
        state_count += group_state_count

    initial_rtpc_offset = offset
    rtpc_curve_count = take_u16("rtpcCurveCount")
    rtpc_curves: list[dict[str, Any]] = []
    rtpc_point_count = 0
    for curve_index in range(rtpc_curve_count):
        rtpc_id = take_u32("rtpcId")
        rtpc_type = take_u8("rtpcType")
        accum = take_u8("rtpcAccum")
        parameter_id = take_varuint("rtpcParameterId")
        curve_id = take_u32("rtpcCurveId")
        scaling = take_u8("rtpcScaling")
        point_count = take_u16("rtpcPointCount")
        if (
            rtpc_type not in HIRC_RTPC_TYPE_LABELS
            or accum not in HIRC_RTPC_ACCUM_LABELS
            or scaling not in HIRC_RTPC_SCALING_LABELS
        ):
            raise ValueError(
                "v150 State/RTPC gate rtpcHeader invalid: "
                f"curveIndex={curve_index} rtpcType={rtpc_type} accum={accum} "
                f"parameterId={parameter_id} scaling={scaling} offset={offset - 3}"
            )
        points: list[dict[str, Any]] = []
        for point_index in range(point_count):
            from_value = take_f32("rtpcPointFrom")
            to_value = take_f32("rtpcPointTo")
            interpolation = take_u32("rtpcPointInterpolation")
            if interpolation not in HIRC_FADE_CURVE_LABELS:
                raise ValueError(
                    "v150 State/RTPC gate rtpcPointInterpolation invalid: "
                    f"curveIndex={curve_index} pointIndex={point_index} "
                    f"value={interpolation} offset={offset - 4}"
                )
            points.append({
                "pointIndex": point_index,
                "from": from_value,
                "to": to_value,
                "interpolation": interpolation,
                "interpolationLabel": HIRC_FADE_CURVE_LABELS[interpolation],
            })
        rtpc_curves.append({
            "curveIndex": curve_index,
            "rtpcId": rtpc_id,
            "rtpcIdHex": f"0x{rtpc_id:08x}",
            "rtpcType": rtpc_type,
            "rtpcTypeLabel": HIRC_RTPC_TYPE_LABELS[rtpc_type],
            "accum": accum,
            "accumLabel": HIRC_RTPC_ACCUM_LABELS[accum],
            "parameterId": parameter_id,
            "parameterLabel": HIRC_RTPC_PARAMETER_LABELS.get(
                parameter_id, f"parameter{parameter_id}"
            ),
            "curveId": curve_id,
            "curveIdHex": f"0x{curve_id:08x}",
            "scaling": scaling,
            "scalingLabel": HIRC_RTPC_SCALING_LABELS[scaling],
            "pointCount": point_count,
            "points": points,
        })
        rtpc_point_count += point_count

    return {
        "parserStatus": "typedExactV150NodeStateAndRtpc",
        "advSettings": adv_settings,
        "stateChunkOffset": state_chunk_offset,
        "statePropertyCount": state_property_count,
        "stateProperties": state_properties,
        "stateGroupCount": state_group_count,
        "stateCount": state_count,
        "stateValueCount": state_value_count,
        "stateGroups": state_groups,
        "initialRtpcOffset": initial_rtpc_offset,
        "rtpcCurveCount": rtpc_curve_count,
        "rtpcPointCount": rtpc_point_count,
        "rtpcCurves": rtpc_curves,
        "nodeBaseEndOffset": offset,
        "remainingSubtypeByteLength": len(data) - offset,
        "evidenceBoundary": (
            "Exact authored StateChunk values and InitialRTPC curves. Runtime State/"
            "GameParameter/Modulator values, inherited effective properties, effect "
            "bypass decisions, and the audible result are not observed."
        ),
    }

def hirc_v150_node_processing(
    object_type: int,
    data: bytes,
) -> dict[str, Any] | None:
    """Return the common direct-processing prefix for one audio node."""

    try:
        offset = _hirc_v150_node_base_offset(object_type, data)
        if offset is None:
            return None
        node_base, node_base_end = _hirc_v150_node_base(data, offset)
        try:
            node_base["auxSends"] = _hirc_v150_node_aux_sends(
                data, node_base_end
            )
        except (ValueError, OverflowError, TypeError) as exc:
            node_base["auxSends"] = {
                "parserStatus": "failedClosed",
                "diagnostic": str(exc),
                "nodeBaseEndOffset": node_base_end,
                "payloadByteLength": len(data),
            }
        aux_sends = node_base["auxSends"]
        if aux_sends.get("parserStatus") == "typedExactV150NodeAuxParams":
            try:
                node_base["stateAndRtpc"] = _hirc_v150_node_state_rtpc(
                    data, int(aux_sends["auxParamsEndOffset"])
                )
            except (ValueError, OverflowError, TypeError) as exc:
                node_base["stateAndRtpc"] = {
                    "parserStatus": "failedClosed",
                    "diagnostic": str(exc),
                    "postAuxOffset": aux_sends.get("auxParamsEndOffset"),
                    "payloadByteLength": len(data),
                }
        return node_base
    except (ValueError, OverflowError, TypeError):
        return None

def summarize_hirc_node_processing(
    rows_by_object_id: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Compact exact NodeBase processing rows without losing effect chains."""

    rows = [rows_by_object_id[key] for key in sorted(rows_by_object_id)]
    output_bus_counts: Counter[int] = Counter()
    node_type_counts: Counter[int] = Counter()
    effect_nodes: list[dict[str, Any]] = []
    metadata_nodes: list[dict[str, Any]] = []
    aux_send_nodes: list[dict[str, Any]] = []
    aux_send_failures: list[dict[str, Any]] = []
    auxiliary_bus_counts: Counter[tuple[str, int]] = Counter()
    parsed_aux_send_node_count = 0
    state_rtpc_nodes: list[dict[str, Any]] = []
    state_rtpc_failures: list[dict[str, Any]] = []
    property_nodes: list[dict[str, Any]] = []
    property_counts: Counter[str] = Counter()
    ranged_property_counts: Counter[str] = Counter()
    state_group_counts: Counter[int] = Counter()
    state_value_counts: Counter[int] = Counter()
    rtpc_id_counts: Counter[int] = Counter()
    rtpc_type_counts: Counter[str] = Counter()
    rtpc_parameter_counts: Counter[str] = Counter()
    parsed_state_rtpc_node_count = 0
    for row in rows:
        object_type = int(row.get("objectType") or 0)
        node_type_counts[object_type] += 1
        bus_id = int(row.get("overrideBusId") or 0)
        if bus_id:
            output_bus_counts[bus_id] += 1
        if row.get("effects"):
            effect_nodes.append({
                key: row[key]
                for key in (
                    "objectId", "objectType", "objectTypeLabel", "rootActionIds",
                    "overrideParentFxRaw", "overrideParentFx", "bypassAllRaw",
                    "bypassAll", "overrideBusId", "overrideBusIdHex", "effects",
                )
                if row.get(key) not in (None, "", [])
            })
        if row.get("metadata"):
            metadata_nodes.append({
                key: row[key]
                for key in (
                    "objectId", "objectType", "objectTypeLabel", "rootActionIds",
                    "overrideParentMetadataRaw", "overrideParentMetadata", "metadata",
                )
                if row.get(key) not in (None, "", [])
            })
        aux_sends = row.get("auxSends") or {}
        if aux_sends.get("parserStatus") == "typedExactV150NodeAuxParams":
            parsed_aux_send_node_count += 1
            if aux_sends.get("properties") or aux_sends.get("rangedProperties"):
                for prop in aux_sends.get("properties") or []:
                    property_counts[str(prop.get("propertyLabel") or "unknown")] += 1
                for prop in aux_sends.get("rangedProperties") or []:
                    ranged_property_counts[
                        str(prop.get("propertyLabel") or "unknown")
                    ] += 1
                property_nodes.append({
                    key: value
                    for key, value in {
                        "objectId": row.get("objectId"),
                        "objectType": row.get("objectType"),
                        "objectTypeLabel": row.get("objectTypeLabel"),
                        "rootActionIds": row.get("rootActionIds"),
                        "parentId": row.get("parentId"),
                        "properties": aux_sends.get("properties"),
                        "rangedProperties": aux_sends.get("rangedProperties"),
                    }.items()
                    if value not in (None, "", [])
                })
            for send in aux_sends.get("userDefinedAuxSends") or []:
                auxiliary_bus_counts[
                    ("userDefined", int(send.get("busId") or 0))
                ] += 1
            reflections_bus_id = int(
                aux_sends.get("reflectionsAuxBusId") or 0
            )
            if reflections_bus_id:
                auxiliary_bus_counts[("earlyReflections", reflections_bus_id)] += 1
            if int(aux_sends.get("auxFlagsRaw") or 0):
                aux_send_nodes.append({
                    key: value
                    for key, value in {
                        "objectId": row.get("objectId"),
                        "objectType": row.get("objectType"),
                        "objectTypeLabel": row.get("objectTypeLabel"),
                        "rootActionIds": row.get("rootActionIds"),
                        "parentId": row.get("parentId"),
                        "auxParamsOffset": aux_sends.get("auxParamsOffset"),
                        "auxFlagsRaw": aux_sends.get("auxFlagsRaw"),
                        "overrideGameDefinedAuxSends": aux_sends.get(
                            "overrideGameDefinedAuxSends"
                        ),
                        "useGameDefinedAuxSends": aux_sends.get(
                            "useGameDefinedAuxSends"
                        ),
                        "overrideUserDefinedAuxSends": aux_sends.get(
                            "overrideUserDefinedAuxSends"
                        ),
                        "hasUserDefinedAuxSendSlots": aux_sends.get(
                            "hasUserDefinedAuxSendSlots"
                        ),
                        "overrideEarlyReflectionsAuxBus": aux_sends.get(
                            "overrideEarlyReflectionsAuxBus"
                        ),
                        "userDefinedAuxSends": aux_sends.get(
                            "userDefinedAuxSends"
                        ),
                        "reflectionsAuxBusId": reflections_bus_id,
                        "reflectionsAuxBusIdHex": aux_sends.get(
                            "reflectionsAuxBusIdHex"
                        ),
                        "gameDefinedAssignmentBoundary": aux_sends.get(
                            "gameDefinedAssignmentBoundary"
                        ),
                        "flagSemanticBoundary": aux_sends.get(
                            "flagSemanticBoundary"
                        ),
                    }.items()
                    if value not in (None, "", [])
                })
        elif aux_sends:
            aux_send_failures.append({
                key: value
                for key, value in {
                    "objectId": row.get("objectId"),
                    "objectType": row.get("objectType"),
                    "objectTypeLabel": row.get("objectTypeLabel"),
                    "diagnostic": aux_sends.get("diagnostic"),
                    "nodeBaseEndOffset": aux_sends.get("nodeBaseEndOffset"),
                    "payloadByteLength": aux_sends.get("payloadByteLength"),
                }.items()
                if value not in (None, "", [])
            })
        state_rtpc = row.get("stateAndRtpc") or {}
        if state_rtpc.get("parserStatus") == "typedExactV150NodeStateAndRtpc":
            parsed_state_rtpc_node_count += 1
            for group in state_rtpc.get("stateGroups") or []:
                group_id = int(group.get("groupId") or 0)
                state_group_counts[group_id] += 1
                state_value_counts[group_id] += sum(
                    len(state.get("values") or [])
                    for state in group.get("states") or []
                )
            for curve in state_rtpc.get("rtpcCurves") or []:
                rtpc_id_counts[int(curve.get("rtpcId") or 0)] += 1
                rtpc_type_counts[str(curve.get("rtpcTypeLabel") or "unknown")] += 1
                rtpc_parameter_counts[
                    str(curve.get("parameterLabel") or "unknown")
                ] += 1
            if state_rtpc.get("stateGroups") or state_rtpc.get("rtpcCurves"):
                state_rtpc_nodes.append({
                    key: value
                    for key, value in {
                        "objectId": row.get("objectId"),
                        "objectType": row.get("objectType"),
                        "objectTypeLabel": row.get("objectTypeLabel"),
                        "rootActionIds": row.get("rootActionIds"),
                        "advSettings": state_rtpc.get("advSettings"),
                        "stateProperties": state_rtpc.get("stateProperties"),
                        "stateGroups": state_rtpc.get("stateGroups"),
                        "rtpcCurves": state_rtpc.get("rtpcCurves"),
                        "evidenceBoundary": state_rtpc.get("evidenceBoundary"),
                    }.items()
                    if value not in (None, "", [])
                })
        elif state_rtpc:
            state_rtpc_failures.append({
                key: value
                for key, value in {
                    "objectId": row.get("objectId"),
                    "objectType": row.get("objectType"),
                    "objectTypeLabel": row.get("objectTypeLabel"),
                    "diagnostic": state_rtpc.get("diagnostic"),
                    "postAuxOffset": state_rtpc.get("postAuxOffset"),
                    "payloadByteLength": state_rtpc.get("payloadByteLength"),
                }.items()
                if value not in (None, "", [])
            })
    effect_slots = [
        slot
        for row in effect_nodes
        for slot in row.get("effects") or []
        if isinstance(slot, dict)
    ]
    effect_bypass_slot_count = sum(
        bool(slot.get("effectBypass")) for slot in effect_slots
    )
    effect_share_set_slot_count = sum(
        bool(slot.get("effectShareSet")) for slot in effect_slots
    )
    effect_rendered_slot_count = sum(
        bool(slot.get("effectRendered")) for slot in effect_slots
    )
    effect_unknown_flag_bits = sum(
        bool(int(slot.get("unknownFlagBits") or 0)) for slot in effect_slots
    )
    return {
        "parserStatus": "typedExactV150NodeBaseProcessingPrefix",
        "parsedNodeCount": len(rows),
        "nodeTypeCounts": {
            str(key): value for key, value in sorted(node_type_counts.items())
        },
        "overrideParentFxNodeCount": sum(bool(row.get("overrideParentFx")) for row in rows),
        "effectNodeCount": len(effect_nodes),
        "effectSlotCount": len(effect_slots),
        "effectReferenceCount": sum(bool(int(row.get("effectId") or 0)) for row in effect_slots),
        "emptyEffectSlotCount": sum(not int(row.get("effectId") or 0) for row in effect_slots),
        "effectBypassSlotCount": effect_bypass_slot_count,
        "effectShareSetSlotCount": effect_share_set_slot_count,
        "effectRenderedSlotCount": effect_rendered_slot_count,
        "effectUnknownFlagBitsCount": effect_unknown_flag_bits,
        "bypassAllNodeCount": sum(bool(row.get("bypassAll")) for row in rows),
        "overrideParentMetadataNodeCount": sum(
            bool(row.get("overrideParentMetadata")) for row in rows
        ),
        "metadataNodeCount": len(metadata_nodes),
        "metadataSlotCount": sum(len(row.get("metadata") or []) for row in metadata_nodes),
        "parsedAuxSendNodeCount": parsed_aux_send_node_count,
        "failedAuxSendNodeCount": len(aux_send_failures),
        "authoredAuxFlagNodeCount": len(aux_send_nodes),
        "gameDefinedAuxSendUseBitNodeCount": sum(
            bool(row.get("useGameDefinedAuxSends")) for row in aux_send_nodes
        ),
        "userDefinedAuxSendReferenceCount": sum(
            count
            for (send_kind, _bus_id), count in auxiliary_bus_counts.items()
            if send_kind == "userDefined"
        ),
        "earlyReflectionsAuxSendReferenceCount": sum(
            count
            for (send_kind, _bus_id), count in auxiliary_bus_counts.items()
            if send_kind == "earlyReflections"
        ),
        "authoredPropertyNodeCount": len(property_nodes),
        "authoredPropertyValueCount": sum(property_counts.values()),
        "authoredRangedPropertyValueCount": sum(ranged_property_counts.values()),
        "authoredPropertyCounts": dict(sorted(property_counts.items())),
        "authoredRangedPropertyCounts": dict(sorted(ranged_property_counts.items())),
        "parsedStateRtpcNodeCount": parsed_state_rtpc_node_count,
        "failedStateRtpcNodeCount": len(state_rtpc_failures),
        "stateRtpcNodeCount": len(state_rtpc_nodes),
        "stateGroupReferenceCount": sum(state_group_counts.values()),
        "uniqueStateGroupIds": len(state_group_counts),
        "stateValueCount": sum(state_value_counts.values()),
        "rtpcCurveCount": sum(rtpc_id_counts.values()),
        "rtpcPointCount": sum(
            len(curve.get("points") or [])
            for node in state_rtpc_nodes
            for curve in node.get("rtpcCurves") or []
        ),
        "uniqueRtpcIds": len(rtpc_id_counts),
        "rtpcTypeCounts": dict(sorted(rtpc_type_counts.items())),
        "rtpcParameterCounts": dict(sorted(rtpc_parameter_counts.items())),
        "stateGroups": [
            {
                "groupId": group_id,
                "groupIdHex": f"0x{group_id:08x}",
                "nodeCount": count,
                "valueCount": state_value_counts[group_id],
            }
            for group_id, count in sorted(state_group_counts.items())
        ],
        "rtpcIds": [
            {
                "rtpcId": rtpc_id,
                "rtpcIdHex": f"0x{rtpc_id:08x}",
                "curveCount": count,
            }
            for rtpc_id, count in sorted(rtpc_id_counts.items())
        ],
        "auxiliaryBuses": [
            {
                "sendKind": send_kind,
                "busId": bus_id,
                "busIdHex": f"0x{bus_id:08x}",
                "referenceCount": count,
            }
            for (send_kind, bus_id), count in sorted(auxiliary_bus_counts.items())
            if bus_id
        ],
        "outputBusNodeCount": sum(output_bus_counts.values()),
        "outputBuses": [
            {
                "busId": bus_id,
                "busIdHex": f"0x{bus_id:08x}",
                "nodeCount": count,
            }
            for bus_id, count in sorted(output_bus_counts.items())
        ],
        "effectNodes": effect_nodes,
        "metadataNodes": metadata_nodes,
        "auxSendNodes": aux_send_nodes,
        "auxSendFailures": aux_send_failures,
        "propertyNodes": property_nodes,
        "stateRtpcNodes": state_rtpc_nodes,
        "stateRtpcFailures": state_rtpc_failures,
        "evidenceBoundary": (
            "Exact direct NodeBase effect slots and output-bus IDs. Supported "
            "plug-in schemas expose authored base values from shipped "
            "AkSoundEngine SetParamsBlock layouts; unsupported payloads remain "
            "opaque. Authored User Aux slots and Game-Defined use/override bits "
            "are direct; live Game-Defined bus assignments and control values, "
            "authored StateChunk values and InitialRTPC curves are exact; live "
            "control values, inherited effective properties, bypass decisions, "
            "platform DSP, and audibility are unresolved."
        ),
    }

def add_hirc_effect_definition_candidate(
    candidates: dict[int, dict[tuple[Any, ...], dict[str, Any]]],
    effect_id: int,
    definition: dict[str, Any],
    *,
    bank_id: int,
    bank_name: str = "",
) -> None:
    """Merge byte-identical plug-in definitions while retaining ambiguity."""

    signature = (
        int(definition.get("objectType") or 0),
        int(definition.get("pluginClassId") or 0),
        int(definition.get("parameterByteLength") or 0),
        str(definition.get("parameterSha256") or ""),
        int(definition.get("trailingByteLength") or 0),
        tuple(
            (
                int(dependency.get("pluginDataIndex") or 0),
                int(dependency.get("mediaId") or 0),
            )
            for dependency in definition.get("pluginMediaDependencies") or []
            if isinstance(dependency, dict)
        ),
    )
    row = candidates.setdefault(effect_id, {}).setdefault(signature, {
        **definition,
        "effectId": effect_id,
        "effectIdHex": f"0x{effect_id:08x}",
        "definitionOccurrenceCount": 0,
        "bankIds": set(),
        "bankScopes": set(),
    })
    row["definitionOccurrenceCount"] += 1
    row["bankIds"].add(bank_id)
    row["bankScopes"].add((bank_name, bank_id))

def add_hirc_bus_definition_candidate(
    candidates: dict[int, dict[tuple[int, str], dict[str, Any]]],
    bus_id: int,
    object_type: int,
    data: bytes,
    *,
    bank_id: int,
    bank_name: str = "",
) -> None:
    """Retain one exact type-8/type-18 payload per unique bank signature."""

    if object_type not in (8, 18) or len(data) < 4:
        return
    digest = hashlib.sha256(data).hexdigest()
    signature = (object_type, digest)
    row = candidates.setdefault(bus_id, {}).setdefault(signature, {
        "busId": bus_id,
        "busIdHex": f"0x{bus_id:08x}",
        "objectType": object_type,
        "objectTypeLabel": HIRC_OBJECT_TYPE_LABELS[object_type],
        "payloadByteLength": len(data),
        "payloadSha256": digest,
        "definitionOccurrenceCount": 0,
        "bankIds": set(),
        "bankScopes": set(),
        "_payload": data,
    })
    row["definitionOccurrenceCount"] += 1
    row["bankIds"].add(bank_id)
    row["bankScopes"].add((bank_name, bank_id))

def _hirc_v150_bus_rtpc_state(
    data: bytes,
    offset: int,
) -> dict[str, Any]:
    """Decode the v150 CAkBus InitialRTPC and StateChunk suffix.

    ``CAkBus::SetInitialValues`` writes the RTPC curves before the
    ``CAkStateAware`` state chunk.  The common NodeBase parser has the inverse
    order, so Bus payloads need their own bounded reader.  Returning an
    explicit failed-closed row keeps the exact InitialValues prefix useful for
    synthetic or future-version fixtures without promoting an unverified tail.
    """

    start_offset = int(offset)

    def require(length: int, label: str) -> None:
        if length < 0 or offset + length > len(data):
            raise ValueError(
                f"v150 Bus RTPC/State {label} truncated at offset {offset}: "
                f"need={length} remaining={len(data) - offset}"
            )

    def take_u8(label: str) -> int:
        nonlocal offset
        require(1, label)
        value = data[offset]
        offset += 1
        return value

    def take_u16(label: str) -> int:
        nonlocal offset
        require(2, label)
        value = unpack_from("<H", data, offset)[0]
        offset += 2
        return value

    def take_u32(label: str) -> int:
        nonlocal offset
        require(4, label)
        value = unpack_from("<I", data, offset)[0]
        offset += 4
        return value

    def take_f32(label: str) -> float:
        nonlocal offset
        require(4, label)
        value = float(unpack_from("<f", data, offset)[0])
        value_offset = offset
        offset += 4
        if not math.isfinite(value):
            raise ValueError(
                f"v150 Bus RTPC/State {label} non-finite at offset "
                f"{value_offset}"
            )
        return value

    def take_varuint(label: str) -> int:
        start = offset
        value = 0
        for index in range(5):
            byte = take_u8(label)
            value |= (byte & 0x7F) << (index * 7)
            if not byte & 0x80:
                return value
        raise ValueError(
            f"v150 Bus RTPC/State {label} invalid varuint at offset {start}"
        )

    try:
        initial_rtpc_offset = offset
        rtpc_curve_count = take_u16("rtpcCurveCount")
        rtpc_curves: list[dict[str, Any]] = []
        rtpc_point_count = 0
        for curve_index in range(rtpc_curve_count):
            rtpc_id = take_u32("rtpcId")
            rtpc_type = take_u8("rtpcType")
            accum = take_u8("rtpcAccum")
            parameter_id = take_varuint("rtpcParameterId")
            curve_id = take_u32("rtpcCurveId")
            scaling = take_u8("rtpcScaling")
            point_count = take_u16("rtpcPointCount")
            if (
                rtpc_type not in HIRC_RTPC_TYPE_LABELS
                or accum not in HIRC_RTPC_ACCUM_LABELS
                or scaling not in HIRC_RTPC_SCALING_LABELS
            ):
                raise ValueError(
                    "v150 Bus RTPC/State rtpcHeader invalid: "
                    f"curveIndex={curve_index} rtpcType={rtpc_type} "
                    f"accum={accum} scaling={scaling} offset={offset - 3}"
                )
            points: list[dict[str, Any]] = []
            for point_index in range(point_count):
                from_value = take_f32("rtpcPointFrom")
                to_value = take_f32("rtpcPointTo")
                interpolation = take_u32("rtpcPointInterpolation")
                if interpolation not in HIRC_FADE_CURVE_LABELS:
                    raise ValueError(
                        "v150 Bus RTPC/State rtpcPointInterpolation invalid: "
                        f"curveIndex={curve_index} pointIndex={point_index} "
                        f"value={interpolation} offset={offset - 4}"
                    )
                points.append({
                    "pointIndex": point_index,
                    "from": from_value,
                    "to": to_value,
                    "interpolation": interpolation,
                    "interpolationLabel": HIRC_FADE_CURVE_LABELS[interpolation],
                })
            rtpc_curves.append({
                "curveIndex": curve_index,
                "rtpcId": rtpc_id,
                "rtpcIdHex": f"0x{rtpc_id:08x}",
                "rtpcType": rtpc_type,
                "rtpcTypeLabel": HIRC_RTPC_TYPE_LABELS[rtpc_type],
                "accum": accum,
                "accumLabel": HIRC_RTPC_ACCUM_LABELS[accum],
                "parameterId": parameter_id,
                "parameterLabel": HIRC_RTPC_PARAMETER_LABELS.get(
                    parameter_id, f"parameter{parameter_id}"
                ),
                "curveId": curve_id,
                "curveIdHex": f"0x{curve_id:08x}",
                "scaling": scaling,
                "scalingLabel": HIRC_RTPC_SCALING_LABELS[scaling],
                "pointCount": point_count,
                "points": points,
            })
            rtpc_point_count += point_count

        state_chunk_offset = offset
        state_property_count = take_varuint("statePropertyCount")
        state_properties: list[dict[str, Any]] = []
        for property_index in range(state_property_count):
            parameter_id = take_varuint("statePropertyId")
            accum = take_u8("statePropertyAccum")
            in_db_raw = take_u8("statePropertyInDb")
            if accum not in HIRC_RTPC_ACCUM_LABELS or in_db_raw not in (0, 1):
                raise ValueError(
                    "v150 Bus RTPC/State stateProperty invalid: "
                    f"index={property_index} parameterId={parameter_id} "
                    f"accum={accum} inDb={in_db_raw} offset={offset - 2}"
                )
            state_properties.append({
                "propertyIndex": property_index,
                "parameterId": parameter_id,
                "parameterLabel": HIRC_RTPC_PARAMETER_LABELS.get(
                    parameter_id, f"parameter{parameter_id}"
                ),
                "accum": accum,
                "accumLabel": HIRC_RTPC_ACCUM_LABELS[accum],
                "inDb": bool(in_db_raw),
                "inDbRaw": in_db_raw,
            })

        state_group_count = take_varuint("stateGroupCount")
        state_groups: list[dict[str, Any]] = []
        state_count = 0
        state_value_count = 0
        for group_index in range(state_group_count):
            group_id = take_u32("stateGroupId")
            sync_type = take_u8("stateGroupSyncType")
            if sync_type not in HIRC_STATE_SYNC_TYPE_LABELS:
                raise ValueError(
                    "v150 Bus RTPC/State stateGroupSyncType invalid: "
                    f"groupIndex={group_index} value={sync_type} "
                    f"offset={offset - 1}"
                )
            group_state_count = take_varuint("stateCount")
            states: list[dict[str, Any]] = []
            for state_index in range(group_state_count):
                state_id = take_u32("stateId")
                value_count = take_u16("stateValueCount")
                property_ids = [
                    take_u16("stateValuePropertyId")
                    for _ in range(value_count)
                ]
                values = [
                    take_f32("stateValue") for _ in range(value_count)
                ]
                state_values = [
                    {
                        "valueIndex": value_index,
                        "parameterId": parameter_id,
                        "parameterLabel": HIRC_RTPC_PARAMETER_LABELS.get(
                            parameter_id, f"parameter{parameter_id}"
                        ),
                        "value": values[value_index],
                    }
                    for value_index, parameter_id in enumerate(property_ids)
                ]
                states.append({
                    "stateIndex": state_index,
                    "stateId": state_id,
                    "stateIdHex": f"0x{state_id:08x}",
                    "valueCount": value_count,
                    "values": state_values,
                })
                state_value_count += value_count
            state_groups.append({
                "groupIndex": group_index,
                "groupId": group_id,
                "groupIdHex": f"0x{group_id:08x}",
                "syncType": sync_type,
                "syncTypeLabel": HIRC_STATE_SYNC_TYPE_LABELS[sync_type],
                "stateCount": group_state_count,
                "states": states,
            })
            state_count += group_state_count

        if offset != len(data):
            raise ValueError(
                "v150 Bus RTPC/State suffix has unknown trailing bytes: "
                f"offset={offset} length={len(data)}"
            )
        return {
            "parserStatus": "typedExactV150BusInitialRtpcAndState",
            "initialRtpcOffset": initial_rtpc_offset,
            "rtpcCurveCount": rtpc_curve_count,
            "rtpcPointCount": rtpc_point_count,
            "rtpcCurves": rtpc_curves,
            "stateChunkOffset": state_chunk_offset,
            "statePropertyCount": state_property_count,
            "stateProperties": state_properties,
            "stateGroupCount": state_group_count,
            "stateCount": state_count,
            "stateValueCount": state_value_count,
            "stateGroups": state_groups,
            "endOffset": offset,
            "remainingByteLength": 0,
            "evidenceBoundary": (
                "Exact authored Bus InitialRTPC curves and StateChunk values. "
                "Runtime GameParameter/State values, inherited effective "
                "properties, effect bypass decisions, platform DSP, and the "
                "audible result are not observed."
            ),
        }
    except (ValueError, OverflowError, struct.error) as exc:
        return {
            "parserStatus": "failedClosed",
            "diagnostic": str(exc),
            "startOffset": start_offset,
            "endOffset": offset,
            "remainingByteLength": max(0, len(data) - offset),
        }

def _hirc_v150_bus_serialized_layout(
    data: bytes,
) -> dict[str, Any] | None:
    """Decode the current v150 ``CAkBus`` layout through InitialFX.

    Wwise Bus objects do not put ``InitialFX`` immediately after the parent
    ID.  The current client serializes the property bundle, positioning and
    auxiliary flags, bus limits, duck records, and only then the owned effect
    slots.  A byte scanner therefore mistakes duck/state data for effect
    counts on a large subset of otherwise valid Bus objects.  This parser is
    deliberately bounded to the v150 field order and returns ``None`` on any
    gate failure so the older correlation scanner can remain as a fixture and
    fallback for synthetic/non-v150 payloads.
    """

    if len(data) < 4:
        return None
    offset = 0

    def require(length: int, label: str) -> None:
        if length < 0 or offset + length > len(data):
            raise ValueError(
                f"v150 Bus {label} truncated at offset {offset}: "
                f"need={length} remaining={len(data) - offset}"
            )

    def take_u8(label: str) -> int:
        nonlocal offset
        require(1, label)
        value = data[offset]
        offset += 1
        return value

    def take_u16(label: str) -> int:
        nonlocal offset
        require(2, label)
        value = unpack_from("<H", data, offset)[0]
        offset += 2
        return value

    def take_u32(label: str) -> int:
        nonlocal offset
        require(4, label)
        value = unpack_from("<I", data, offset)[0]
        offset += 4
        return value

    def take_s32(label: str) -> int:
        nonlocal offset
        require(4, label)
        value = unpack_from("<i", data, offset)[0]
        offset += 4
        return value

    def take_f32(label: str) -> float:
        nonlocal offset
        require(4, label)
        value = float(unpack_from("<f", data, offset)[0])
        offset += 4
        if not math.isfinite(value):
            raise ValueError(f"v150 Bus {label} is non-finite")
        return value

    def skip(count: int, label: str) -> None:
        nonlocal offset
        require(count, label)
        offset += count

    try:
        parent_bus_id = take_u32("OverrideBusId")
        device_share_set_id: int | None = None
        if parent_bus_id == 0:
            # v127+ root buses carry a device ShareSet ID in this slot.
            device_share_set_id = take_u32("deviceShareSetId")

        property_count = take_u8("propertyCount")
        property_ids = [
            take_u8("propertyId") for _ in range(property_count)
        ]
        if any(property_id not in HIRC_INITIAL_PROPERTY_LABELS for property_id in property_ids):
            raise ValueError("v150 Bus property bundle contains an unknown AkPropID")
        property_values: list[dict[str, Any]] = []
        for index, property_id in enumerate(property_ids):
            raw_value = take_u32("propertyValue")
            float_value = unpack_from("<f", data, offset - 4)[0]
            property_label = HIRC_INITIAL_PROPERTY_LABELS[property_id]
            value_encoding = "float"
            if property_label in HIRC_INITIAL_PROPERTY_U32_LABELS:
                value_encoding = "u32Id"
            elif (
                raw_value <= 0x00100000
                and math.isfinite(float_value)
                and abs(float_value) < 1e-20
            ):
                value_encoding = "u32Likely"
            property_values.append({
                "propertyIndex": index,
                "propertyId": property_id,
                "propertyIdHex": f"0x{property_id:02x}",
                "propertyLabel": property_label,
                "rawU32": raw_value,
                "rawHex": f"0x{raw_value:08x}",
                "floatValue": float_value if math.isfinite(float_value) else None,
                "valueEncoding": value_encoding,
            })

        positioning_bits_raw = take_u8("positioningBits")
        positioning_3d_bits_raw: int | None = None
        if positioning_bits_raw & 0x01 and positioning_bits_raw & 0x02:
            positioning_3d_bits_raw = take_u8("positioning3dBits")
            position_type = (positioning_bits_raw >> 5) & 0x03
            if position_type:
                take_u8("automationPathMode")
                take_s32("automationTransitionTime")
                vertex_count = take_u32("automationVertexCount")
                skip(vertex_count * 16, "automationVertices")
                playlist_count = take_u32("automationPlaylistCount")
                skip(playlist_count * 8, "automationPlaylist")
                # v150 stores one automation-parameter triplet per playlist
                # item in this path representation.
                skip(playlist_count * 12, "automationParameters")

        aux_flags_raw = take_u8("auxFlags")
        if aux_flags_raw & ~0x1F:
            raise ValueError(
                f"v150 Bus Aux flags contain unknown bits: 0x{aux_flags_raw:02x}"
            )
        user_aux_bus_ids: list[int] = []
        if aux_flags_raw & 0x08:
            user_aux_bus_ids = [take_u32("userAuxBusId") for _ in range(4)]
        reflections_aux_bus_id = take_u32("reflectionsAuxBusId")

        bus_flags_raw = take_u8("busFlags")
        max_instances = take_u16("maxInstances")
        channel_config = take_u32("channelConfig")
        bus_state_flags_raw = take_u8("busStateFlags")
        recovery_time_ms = take_s32("recoveryTime")
        max_duck_volume_db = take_f32("maxDuckVolume")
        duck_count = take_u32("duckCount")
        ducks: list[dict[str, Any]] = []
        for index in range(duck_count):
            duck_bus_id = take_u32("duckBusId")
            duck_volume_db = take_f32("duckVolume")
            fade_out_ms = take_s32("duckFadeOut")
            fade_in_ms = take_s32("duckFadeIn")
            fade_curve = take_u8("duckFadeCurve")
            target_property = take_u8("duckTargetProperty")
            ducks.append({
                "duckIndex": index,
                "busId": duck_bus_id,
                "busIdHex": f"0x{duck_bus_id:08x}",
                "duckVolumeDb": duck_volume_db,
                "fadeOutMs": fade_out_ms,
                "fadeInMs": fade_in_ms,
                "fadeCurve": fade_curve,
                "targetPropertyId": target_property,
                "targetPropertyIdHex": f"0x{target_property:02x}",
                "targetPropertyLabel": HIRC_INITIAL_PROPERTY_LABELS.get(
                    target_property, f"property{target_property}"
                ),
            })

        effect_chunk_offset = offset
        effect_slot_count = take_u8("initialFxCount")
        bypass_all_raw: int | None = None
        effects: list[dict[str, Any]] = []
        if effect_slot_count:
            bypass_all_raw = take_u8("initialFxBypassAll")
            for ordinal in range(effect_slot_count):
                slot_index = take_u8("initialFxSlotIndex")
                effect_id = take_u32("initialFxObjectId")
                flags_raw = take_u8("initialFxFlags")
                effects.append({
                    "ordinal": ordinal,
                    "slotIndex": slot_index,
                    "effectId": effect_id,
                    "effectIdHex": f"0x{effect_id:08x}",
                    **_hirc_v150_effect_slot_flags(
                        flags_raw, include_rendered=False
                    ),
                    "referenceStatus": "authoredEffectObjectId",
                })
        effect_chunk_end_offset = offset

        metadata_chunk_offset = offset
        metadata_count = take_u8("metadataCount")
        metadata: list[dict[str, Any]] = []
        for ordinal in range(metadata_count):
            metadata.append({
                "ordinal": ordinal,
                "slotIndex": take_u8("metadataSlotIndex"),
                "metadataId": take_u32("metadataObjectId"),
                "shareSetRaw": take_u8("metadataShareSet"),
            })
        serialized_state_rtpc = _hirc_v150_bus_rtpc_state(data, offset)

        return {
            "serializedBusParserStatus": "typedExactV150BusInitialValues",
            "serializedDeviceShareSetId": device_share_set_id,
            "serializedDeviceShareSetIdHex": (
                f"0x{device_share_set_id:08x}"
                if device_share_set_id else None
            ),
            "serializedPropertyCount": property_count,
            "serializedProperties": property_values,
            "serializedPositioningBitsRaw": positioning_bits_raw,
            "serializedPositioning3dBitsRaw": positioning_3d_bits_raw,
            "serializedAuxFlagsRaw": aux_flags_raw,
            "serializedUserAuxBusIds": user_aux_bus_ids,
            "serializedUserAuxBusIdHexes": [
                f"0x{bus_id:08x}" if bus_id else None
                for bus_id in user_aux_bus_ids
            ],
            "serializedReflectionsAuxBusId": reflections_aux_bus_id,
            "serializedReflectionsAuxBusIdHex": (
                f"0x{reflections_aux_bus_id:08x}"
                if reflections_aux_bus_id else None
            ),
            "serializedBusFlagsRaw": bus_flags_raw,
            "serializedMaxInstances": max_instances,
            "serializedChannelConfig": channel_config,
            "serializedBusStateFlagsRaw": bus_state_flags_raw,
            "serializedRecoveryTimeMs": recovery_time_ms,
            "serializedMaxDuckVolumeDb": max_duck_volume_db,
            "serializedDuckCount": duck_count,
            "serializedDucks": ducks,
            "effectChunkOffset": effect_chunk_offset,
            "effectChunkByteLength": effect_chunk_end_offset - effect_chunk_offset,
            "effectChunkEndOffset": effect_chunk_end_offset,
            "effectChunkCandidateCount": 1,
            "nestedSuffixCandidateCount": 0,
            "bypassAllRaw": bypass_all_raw,
            "bypassAll": bool(bypass_all_raw) if bypass_all_raw is not None else None,
            "effectSlotCount": effect_slot_count,
            "effects": effects,
            "metadataChunkOffset": metadata_chunk_offset,
            "metadataSlotCount": metadata_count,
            "metadata": metadata,
            "remainingSubtypeByteLength": len(data) - offset,
            "serializedStateAndRtpc": serialized_state_rtpc,
            "parentBusId": parent_bus_id,
            "parentBusIdHex": f"0x{parent_bus_id:08x}" if parent_bus_id else None,
            "parentParserStatus": "typedExactV150BusFirstU32",
        }
    except (ValueError, OverflowError, struct.error):
        return None

def hirc_v150_bus_processing(
    object_type: int,
    data: bytes,
    effect_ids: set[int] | frozenset[int],
    *,
    empty_effect_schemas: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any] | None:
    """Recover a v150 bus parent and its authored InitialFX slots.

    The first U32 is accepted as DirectParentID only for type 8/18. Across the
    current corpus every nonzero value resolves to another bus definition and
    the three zero values are hierarchy roots. Current bank version 150 Bus
    payloads are first consumed with the typed ``CAkBus`` field order through
    InitialFX. That direct layout proves both zero-count and non-empty chunks;
    effect IDs that have no complete HIRC plug-in definition remain visible as
    unresolved references. Synthetic/non-v150 payloads use the older bounded
    correlation scanner, and an absent candidate there still does not prove an
    empty effect list unless a separate exact sibling-payload schema matches.
    """

    if object_type not in (8, 18) or len(data) < 4:
        return None
    typed_layout = _hirc_v150_bus_serialized_layout(data)
    if typed_layout is not None:
        effect_ids_in_layout = {
            int(row.get("effectId") or 0)
            for row in typed_layout.get("effects") or []
        }
        if not typed_layout.get("effectSlotCount"):
            typed_layout.update({
                "parserStatus": (
                    "typedExactV150BusParentAndSerializedEmptyEffects"
                ),
                "effectParserStatus": "exactTypedV150EmptyEffectChunk",
                "effectEvidenceBoundary": (
                    "The current bank is v150 and the complete typed CAkBus InitialValues layout reaches an explicit InitialFX count byte of zero. This proves the bus-local serialized FX list is empty; parent inheritance and runtime processing remain unresolved."
                ),
            })
        elif effect_ids_in_layout <= set(effect_ids):
            typed_layout.update({
                "parserStatus": (
                    "typedExactV150BusParentAndSerializedEffects"
                ),
                "effectParserStatus": "exactTypedV150NonEmptyEffectChunk",
                "effectEvidenceBoundary": (
                    "The current bank is v150 and the complete typed CAkBus InitialValues layout reaches an ordered non-empty InitialFX array. Every serialized effect object ID cross-correlates to an exact HIRC plug-in definition; authored base parameters remain distinct from live runtime changes."
                ),
            })
        else:
            typed_layout.update({
                "parserStatus": (
                    "typedExactV150BusParentAndSerializedEffects"
                ),
                "effectParserStatus": (
                    "exactTypedV150EffectChunkWithUnresolvedReferences"
                ),
                "effectEvidenceBoundary": (
                    "The current bank is v150 and the complete typed CAkBus InitialValues layout reaches an ordered non-empty InitialFX array, but at least one serialized effect object ID has no complete HIRC plug-in definition in the streamed corpus. The slot identity and flags are exact; plug-in parameters remain unresolved."
                ),
            })
        return typed_layout
    parent_id = unpack_from("<I", data, 0)[0]
    candidates: list[dict[str, Any]] = []
    for offset in range(4, max(4, len(data) - 7)):
        effect_count = data[offset]
        if not 1 <= effect_count <= 16 or data[offset + 1] not in (0, 1):
            continue
        end = offset + 2 + effect_count * 6
        if end > len(data):
            continue
        effects: list[dict[str, Any]] = []
        slots: list[int] = []
        for ordinal in range(effect_count):
            row_offset = offset + 2 + ordinal * 6
            slot_index = data[row_offset]
            effect_id = unpack_from("<I", data, row_offset + 1)[0]
            flags_raw = data[row_offset + 5]
            if slot_index > 15 or effect_id not in effect_ids:
                effects = []
                break
            slots.append(slot_index)
            effects.append({
                "ordinal": ordinal,
                "slotIndex": slot_index,
                "effectId": effect_id,
                "effectIdHex": f"0x{effect_id:08x}",
                **_hirc_v150_effect_slot_flags(
                    flags_raw, include_rendered=False
                ),
                "referenceStatus": "authoredEffectObjectId",
            })
        if not effects or slots != sorted(set(slots)):
            continue
        candidates.append({
            "effectChunkOffset": offset,
            "effectChunkByteLength": end - offset,
            "effectChunkEndOffset": end,
            "bypassAllRaw": data[offset + 1],
            "bypassAll": bool(data[offset + 1]),
            "effectSlotCount": effect_count,
            "effects": effects,
        })

    base = {
        "parentBusId": parent_id,
        "parentBusIdHex": f"0x{parent_id:08x}" if parent_id else None,
        "parentParserStatus": "typedExactV150BusFirstU32",
    }
    if not candidates:
        empty_matches: list[dict[str, Any]] = []
        for schema in empty_effect_schemas:
            if int(schema.get("objectType") or 0) != object_type:
                continue
            prefix = schema.get("prefix")
            suffix = schema.get("suffix")
            if not isinstance(prefix, bytes) or not isinstance(suffix, bytes):
                continue
            effect_offset = 4 + len(prefix)
            if (
                effect_offset >= len(data)
                or data[4:effect_offset] != prefix
                or data[effect_offset] != 0
                or data[effect_offset + 1:] != suffix
            ):
                continue
            empty_matches.append(schema)
        if len(empty_matches) == 1:
            schema = empty_matches[0]
            effect_offset = 4 + len(schema["prefix"])
            return {
                **base,
                "parserStatus": (
                    "typedExactV150BusParentAndCrossCorrelatedEmptyEffects"
                ),
                "effectParserStatus": "exactCrossCorrelatedEmptyEffectChunk",
                "effectChunkOffset": effect_offset,
                "effectChunkByteLength": 1,
                "effectChunkEndOffset": effect_offset + 1,
                "effectChunkCandidateCount": 1,
                "nestedSuffixCandidateCount": 0,
                "effectSlotCount": 0,
                "effects": [],
                "emptyEffectSchemaFingerprint": schema.get("fingerprint"),
                "emptyEffectSchemaSiblingCount": int(
                    schema.get("siblingCount") or 0
                ),
                "effectEvidenceBoundary": (
                    "The serialized InitialFX count byte is explicitly zero, and "
                    "the complete prefix/suffix layout exactly matches a sibling "
                    "bus payload whose non-empty FX slots were decoded. This proves "
                    "the bus-local serialized FX list is empty for this layout; "
                    "parent inheritance and runtime processing remain unresolved."
                ),
            }
        return {
            **base,
            "parserStatus": "typedExactV150BusParentOnly",
            "effectParserStatus": "nonEmptyEffectChunkNotLocated",
            "effectSlotCount": None,
            "effects": [],
            "effectEvidenceBoundary": (
                "No cross-correlated non-empty InitialFX chunk was located; "
                "this does not prove that the authored bus has zero effects."
            ),
        }
    candidates.sort(key=lambda row: (
        int(row["effectChunkOffset"]), -int(row["effectChunkByteLength"])
    ))
    chosen = candidates[0]
    chosen_start = int(chosen["effectChunkOffset"])
    chosen_end = int(chosen["effectChunkEndOffset"])
    nested_suffixes = all(
        chosen_start <= int(candidate["effectChunkOffset"])
        and int(candidate["effectChunkEndOffset"]) == chosen_end
        for candidate in candidates
    )
    if not nested_suffixes:
        return {
            **base,
            "parserStatus": "typedExactV150BusParentOnly",
            "effectParserStatus": "ambiguousCrossCorrelatedEffectChunks",
            "effectSlotCount": None,
            "effects": [],
            "effectChunkCandidateCount": len(candidates),
            "effectEvidenceBoundary": (
                "Multiple non-nested serialized effect-chunk candidates resolve "
                "to HIRC effect definitions; no bus effect list was selected."
            ),
        }
    return {
        **base,
        **chosen,
        "parserStatus": "typedExactV150BusParentAndCrossCorrelatedEffects",
        "effectParserStatus": "exactCrossCorrelatedNonEmptyEffectChunk",
        "effectChunkCandidateCount": len(candidates),
        "nestedSuffixCandidateCount": len(candidates) - 1,
        "effectEvidenceBoundary": (
            "Ordered non-empty bus effect slots are cross-correlated against "
            "exact HIRC effect definitions. A missing chunk remains unresolved "
            "rather than being classified as an empty effect list."
        ),
    }

def _hirc_v150_bus_effect_schemas(
    bus_candidates: dict[int, dict[tuple[int, str], dict[str, Any]]],
    effect_ids: set[int] | frozenset[int],
) -> tuple[dict[str, Any], ...]:
    """Collect exact prefix/suffix schemas that contain non-empty FX slots.

    A zero-count bus is classified only when its payload has the same complete
    bytes before and after InitialFX as a known non-empty sibling schema. The
    raw prefix/suffix bytes stay internal; the public catalog receives only a
    fingerprint and sibling count.
    """

    schemas: dict[tuple[int, bytes, bytes], dict[str, Any]] = {}
    for bus_id, candidates in bus_candidates.items():
        for candidate in candidates.values():
            object_type = int(candidate.get("objectType") or 0)
            data = candidate.get("_payload")
            if object_type not in (8, 18) or not isinstance(data, bytes):
                continue
            processing = hirc_v150_bus_processing(
                object_type, data, effect_ids
            )
            if not processing or processing.get("effectParserStatus") not in {
                "exactCrossCorrelatedNonEmptyEffectChunk",
                "exactTypedV150NonEmptyEffectChunk",
            }:
                continue
            effect_offset = int(processing["effectChunkOffset"])
            effect_end = int(processing["effectChunkEndOffset"])
            prefix = data[4:effect_offset]
            suffix = data[effect_end:]
            key = (object_type, prefix, suffix)
            row = schemas.setdefault(key, {
                "objectType": object_type,
                "prefix": prefix,
                "suffix": suffix,
                "fingerprint": hashlib.sha256(
                    bytes([object_type]) + prefix + suffix
                ).hexdigest(),
                "siblingBusIds": set(),
            })
            row["siblingBusIds"].add(int(bus_id))
    output: list[dict[str, Any]] = []
    for row in schemas.values():
        output.append({
            key: value
            for key, value in row.items()
            if key != "siblingBusIds"
        } | {
            "siblingCount": len(row["siblingBusIds"]),
        })
    output.sort(key=lambda row: (
        int(row["objectType"]), str(row["fingerprint"])
    ))
    return tuple(output)

def finalize_hirc_post_process_catalog(
    effect_candidates: dict[int, dict[tuple[Any, ...], dict[str, Any]]],
    bus_definition_types: dict[int, Counter[int]],
    bus_candidates: dict[int, dict[tuple[int, str], dict[str, Any]]] | None = None,
) -> tuple[dict[int, dict[str, Any]], dict[int, dict[str, Any]]]:
    effect_catalog: dict[int, dict[str, Any]] = {}
    for effect_id, definitions in sorted(effect_candidates.items()):
        choices = []
        for row in definitions.values():
            choices.append({
                **row,
                "bankIds": sorted(row.get("bankIds") or []),
                "bankScopes": [
                    {"bank": bank_name, "bankId": bank_id}
                    for bank_name, bank_id in sorted(row.get("bankScopes") or [])
                ],
            })
        choices.sort(key=lambda row: (
            int(row.get("objectType") or 0),
            int(row.get("pluginClassId") or 0),
            str(row.get("parameterSha256") or ""),
        ))
        if len(choices) == 1:
            effect_catalog[effect_id] = {
                **choices[0],
                "resolutionStatus": "exactUniquePluginDefinition",
            }
        else:
            effect_catalog[effect_id] = {
                "effectId": effect_id,
                "effectIdHex": f"0x{effect_id:08x}",
                "resolutionStatus": "ambiguousPluginDefinitions",
                "definitionCount": len(choices),
                "definitions": choices,
            }

    bus_candidates = bus_candidates or {}
    empty_effect_schemas = _hirc_v150_bus_effect_schemas(
        bus_candidates, frozenset(effect_catalog)
    )
    bus_catalog: dict[int, dict[str, Any]] = {}
    for bus_id, type_counts in sorted(bus_definition_types.items()):
        object_types = sorted(type_counts)
        base = {
            "busId": bus_id,
            "busIdHex": f"0x{bus_id:08x}",
            "objectTypes": object_types,
            "objectTypeLabels": [
                HIRC_OBJECT_TYPE_LABELS.get(value, f"type{value}")
                for value in object_types
            ],
            "definitionOccurrenceCount": sum(type_counts.values()),
            "resolutionStatus": (
                "exactGlobalAudioBusDefinition"
                if object_types == [8]
                else "ambiguousBusDefinitions"
            ),
        }
        definitions = []
        for candidate in bus_candidates.get(bus_id, {}).values():
            processing = hirc_v150_bus_processing(
                int(candidate["objectType"]),
                candidate["_payload"],
                frozenset(effect_catalog),
                empty_effect_schemas=empty_effect_schemas,
            )
            definitions.append({
                **{
                    key: value for key, value in candidate.items()
                    if key != "_payload"
                },
                "bankIds": sorted(candidate.get("bankIds") or []),
                "bankScopes": [
                    {"bank": bank_name, "bankId": bank_id}
                    for bank_name, bank_id in sorted(
                        candidate.get("bankScopes") or []
                    )
                ],
                **(processing or {}),
            })
        definitions.sort(key=lambda row: (
            int(row.get("objectType") or 0), str(row.get("payloadSha256") or "")
        ))
        if len(definitions) == 1:
            definition = definitions[0]
            base.update(definition)
            base["resolutionStatus"] = (
                "exactGlobalAudioBusDefinition"
                if object_types == [8]
                else "exactGlobalAuxiliaryBusDefinition"
                if object_types == [18]
                else "ambiguousBusDefinitions"
            )
        elif definitions:
            base.update({
                "resolutionStatus": "ambiguousBusDefinitions",
                "definitionCount": len(definitions),
                "definitions": definitions,
            })
        bus_catalog[bus_id] = base

    for definition in bus_catalog.values():
        parent_id = int(definition.get("parentBusId") or 0)
        if definition.get("resolutionStatus") == "ambiguousBusDefinitions":
            definition["parentResolutionStatus"] = "ambiguousBusDefinition"
        elif not parent_id:
            definition["parentResolutionStatus"] = "exactRootBus"
        elif parent_id in bus_catalog:
            definition["parentResolutionStatus"] = "exactGlobalBusParent"
        else:
            definition["parentResolutionStatus"] = "parentBusDefinitionNotFound"
        for slot in definition.get("effects") or []:
            effect_id = int(slot.get("effectId") or 0)
            effect_definition = effect_catalog.get(effect_id)
            status = str(
                (effect_definition or {}).get("resolutionStatus")
                or "effectDefinitionNotFound"
            )
            slot["resolutionStatus"] = status
            if status != "exactUniquePluginDefinition":
                continue
            for key in (
                "objectType", "objectTypeLabel", "pluginClassId",
                "pluginClassIdHex", "pluginType", "pluginTypeLabel",
                "companyId", "pluginId", "pluginName", "pluginNameEvidence",
                "parameterByteLength", "parameterSha256", "parameterParserStatus",
                "parameterSchema", "parameterSummary", "parameterBoundary",
                "parameterSemanticBoundary", "parameterRuntimeBoundary",
                "pluginMediaDependencies", "pluginMediaDependencyCount",
                "parameterValues", "parameterSetParamsBlockRva",
            ):
                if effect_definition.get(key) not in (None, "", []):
                    slot[key] = effect_definition[key]
    return effect_catalog, bus_catalog

def hirc_bus_parent_path(
    bus_id: int,
    bus_catalog: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Follow one globally resolved bus hierarchy to a root, fail-closed."""

    path_ids: list[int] = []
    effect_bus_ids: list[int] = []
    unresolved_processing_ids: list[int] = []
    seen: set[int] = set()
    current_id = bus_id
    status = "exactGlobalBusParentPath"
    while current_id:
        if current_id in seen:
            status = "busParentCycle"
            break
        seen.add(current_id)
        definition = bus_catalog.get(current_id)
        if not definition:
            path_ids.append(current_id)
            status = "busDefinitionNotFoundInParentPath"
            break
        path_ids.append(current_id)
        if definition.get("effects"):
            effect_bus_ids.append(current_id)
        if definition.get("effectParserStatus") not in {
            "exactCrossCorrelatedNonEmptyEffectChunk",
            "exactCrossCorrelatedEmptyEffectChunk",
            "exactTypedV150NonEmptyEffectChunk",
            "exactTypedV150EmptyEffectChunk",
            "exactTypedV150EffectChunkWithUnresolvedReferences",
        }:
            unresolved_processing_ids.append(current_id)
        if definition.get("resolutionStatus") == "ambiguousBusDefinitions":
            status = "ambiguousBusDefinitionInParentPath"
            break
        parent_status = str(definition.get("parentResolutionStatus") or "")
        if parent_status == "exactRootBus":
            break
        if parent_status != "exactGlobalBusParent":
            status = parent_status or "unresolvedBusParent"
            break
        current_id = int(definition.get("parentBusId") or 0)
        if len(path_ids) > len(bus_catalog):
            status = "busParentPathExceededCatalog"
            break
    return {
        "busPathIds": path_ids,
        "busPathIdHexes": [f"0x{value:08x}" for value in path_ids],
        "busPathResolutionStatus": status,
        "effectBusIds": effect_bus_ids,
        "effectBusIdHexes": [f"0x{value:08x}" for value in effect_bus_ids],
        "unresolvedBusProcessingIds": unresolved_processing_ids,
        "unresolvedBusProcessingIdHexes": [
            f"0x{value:08x}" for value in unresolved_processing_ids
        ],
    }

def resolve_hirc_post_process_summary(
    summary: dict[str, Any],
    effect_catalog: dict[int, dict[str, Any]],
    bus_catalog: dict[int, dict[str, Any]],
    *,
    bank_id: int | None = None,
    bank_name: str = "",
) -> None:
    """Attach global plug-in/bus definitions to one Event's exact IDs."""

    plugin_reference_counts: Counter[str] = Counter()
    parameter_schema_reference_counts: Counter[str] = Counter()
    resolution_counts: Counter[str] = Counter()
    for node in summary.get("effectNodes") or []:
        for slot in node.get("effects") or []:
            effect_id = int(slot.get("effectId") or 0)
            if not effect_id:
                slot["resolutionStatus"] = "emptyEffectSlot"
                resolution_counts["emptyEffectSlot"] += 1
                continue
            definition = effect_catalog.get(effect_id)
            if not definition:
                slot["resolutionStatus"] = "effectDefinitionNotFound"
                resolution_counts["effectDefinitionNotFound"] += 1
                continue
            status = str(definition.get("resolutionStatus") or "unknown")
            if status == "ambiguousPluginDefinitions" and bank_id is not None:
                same_bank = [
                    row
                    for row in definition.get("definitions") or []
                    if any(
                        int(scope.get("bankId") or 0) == bank_id
                        and str(scope.get("bank") or "") == bank_name
                        for scope in row.get("bankScopes") or []
                        if isinstance(scope, dict)
                    )
                ]
                if len(same_bank) == 1:
                    definition = {
                        **same_bank[0],
                        "resolutionStatus": "exactSameBankPackagePluginDefinition",
                    }
                    status = "exactSameBankPackagePluginDefinition"
            slot["resolutionStatus"] = status
            resolution_counts[status] += 1
            if status not in {
                "exactUniquePluginDefinition",
                "exactSameBankPackagePluginDefinition",
            }:
                slot["definitionCount"] = int(definition.get("definitionCount") or 0)
                continue
            for key in (
                "objectType", "objectTypeLabel", "pluginClassId",
                "pluginClassIdHex", "pluginType", "pluginTypeLabel",
                "companyId", "pluginId", "pluginName", "pluginNameEvidence",
                "parameterByteLength", "parameterSha256", "trailingByteLength",
                "pluginMediaParserStatus", "pluginMediaDependencyCount",
                "pluginMediaDependencies", "pluginMediaPrefixByteLength",
                "postPluginMediaTrailingByteLength", "pluginMediaBoundary",
                "parameterBoundary", "parameterParserStatus", "parameterSchema",
                "parameterValues", "parameterSummary", "parameterSetParamsBlockRva",
                "parameterSemanticBoundary", "parameterRuntimeBoundary",
                "definitionOccurrenceCount",
            ):
                if definition.get(key) not in (None, "", []):
                    slot[key] = definition[key]
            plugin_key = str(
                definition.get("pluginName")
                or definition.get("pluginClassIdHex")
                or "unknown"
            )
            plugin_reference_counts[plugin_key] += 1
            parameter_schema = str(definition.get("parameterSchema") or "")
            if parameter_schema:
                parameter_schema_reference_counts[parameter_schema] += 1

    bus_resolution_counts: Counter[str] = Counter()
    for output_bus in summary.get("outputBuses") or []:
        bus_id = int(output_bus.get("busId") or 0)
        definition = bus_catalog.get(bus_id)
        if not definition:
            output_bus["resolutionStatus"] = "audioBusDefinitionNotFound"
            bus_resolution_counts["audioBusDefinitionNotFound"] += 1
            continue
        output_bus.update({
            key: definition[key]
            for key in (
                "objectTypes", "objectTypeLabels", "definitionOccurrenceCount",
                "resolutionStatus",
            )
            if definition.get(key) not in (None, "", [])
        })
        output_bus.update(hirc_bus_parent_path(bus_id, bus_catalog))
        bus_resolution_counts[str(definition.get("resolutionStatus") or "unknown")] += 1
    aux_bus_resolution_counts: Counter[str] = Counter()
    for auxiliary_bus in summary.get("auxiliaryBuses") or []:
        bus_id = int(auxiliary_bus.get("busId") or 0)
        definition = bus_catalog.get(bus_id)
        if not definition:
            auxiliary_bus["resolutionStatus"] = "auxiliaryBusDefinitionNotFound"
            aux_bus_resolution_counts["auxiliaryBusDefinitionNotFound"] += int(
                auxiliary_bus.get("referenceCount") or 1
            )
            continue
        auxiliary_bus.update({
            key: definition[key]
            for key in (
                "objectTypes", "objectTypeLabels", "definitionOccurrenceCount",
                "resolutionStatus",
            )
            if definition.get(key) not in (None, "", [])
        })
        auxiliary_bus.update(hirc_bus_parent_path(bus_id, bus_catalog))
        aux_bus_resolution_counts[
            str(definition.get("resolutionStatus") or "unknown")
        ] += int(auxiliary_bus.get("referenceCount") or 1)
    summary["effectResolutionCounts"] = dict(sorted(resolution_counts.items()))
    summary["effectPluginReferenceCounts"] = dict(
        sorted(plugin_reference_counts.items())
    )
    summary["decodedEffectParameterReferenceCount"] = sum(
        parameter_schema_reference_counts.values()
    )
    summary["partialEffectParameterReferenceCount"] = sum(
        1
        for node in summary.get("effectNodes") or []
        for slot in node.get("effects") or []
        if str(slot.get("parameterParserStatus") or "").startswith(
            "typedExactLayoutPartialSemantics"
        )
    )
    summary["exactEffectParameterReferenceCount"] = (
        summary["decodedEffectParameterReferenceCount"]
        - summary["partialEffectParameterReferenceCount"]
    )
    summary["effectParameterSchemaReferenceCounts"] = dict(
        sorted(parameter_schema_reference_counts.items())
    )
    summary["outputBusResolutionCounts"] = dict(
        sorted(bus_resolution_counts.items())
    )
    summary["auxiliaryBusResolutionCounts"] = dict(
        sorted(aux_bus_resolution_counts.items())
    )
    summary["evidenceBoundary"] = (
        "Exact direct NodeBase effect slots and explicit output-bus IDs are "
        "combined with the reciprocal global Audio/Aux Bus parent path. "
        "Serialized User-Defined Aux slots and Early Reflections bus IDs use "
        "the same catalog paths; Game-Defined use/override bits are authored, "
        "but their runtime bus IDs and control values are not serialized. "
        "Current v150 Bus objects are consumed through the typed CAkBus field "
        "order through InitialFX, proving explicit zero-count and non-empty "
        "serialized arrays; the legacy bounded correlation path is retained "
        "for non-v150/synthetic payloads. Supported plug-in schemas expose "
        "authored base values, and the v150 AkPropID bundle preserves each "
        "property ID, raw U32, and finite-float interpretation. Initial "
        "BypassFX/BypassAllFX property IDs are absent in the current corpus; "
        "the direct NodeBase bypass flag is separate. Effective inherited "
        "sends, live bypass/RTPC/State values, platform DSP, and audibility "
        "are not observed."
    )

def hirc_reciprocal_child_list(
    object_id: int,
    object_type: int,
    data: bytes,
    objects: dict[int, dict[str, Any]],
) -> tuple[list[int], int] | None:
    """Locate one v150 Children array and prove it through parent backlinks.

    Parameter-node headers have variable-length property blocks, so the child
    count is not at one fixed byte offset.  We scan only for a bounded
    ``U32 count`` + contiguous ``count * U32 child IDs`` structure, then
    require every referenced same-bank HIRC object to expose the reciprocal
    parent ID at its type-defined field.  The earliest reciprocal block is the
    authored Children array; later repetitions are switch maps/playlists.
    """

    if object_type not in HIRC_TYPED_CHILD_CONTAINER_TYPES:
        return None
    allowed_child_types = HIRC_MUSIC_CHILD_TYPES.get(object_type, HIRC_AUDIO_NODE_TYPES)

    def cached_parent_id(child_id: int) -> int | None:
        child = objects[child_id]
        if child.get("_typedParentIdParsed"):
            value = child.get("_typedParentId")
            return int(value) if value is not None else None
        value = hirc_object_parent_id(
            int(child.get("type") or 0), child.get("data") or b""
        )
        child["_typedParentIdParsed"] = True
        child["_typedParentId"] = value
        return value

    for offset in range(0, max(0, len(data) - 7)):
        count = unpack_from("<I", data, offset)[0]
        if count <= 0 or count > (len(data) - offset - 4) // 4:
            continue
        children = [
            unpack_from("<I", data, offset + 4 + index * 4)[0]
            for index in range(count)
        ]
        if any(child_id not in objects for child_id in children):
            continue
        if any(
            int(objects[child_id].get("type") or 0) not in allowed_child_types
            or cached_parent_id(child_id) != object_id
            for child_id in children
        ):
            continue
        return children, offset
    return None

def hirc_v150_switch_mapping(
    data: bytes,
    children_offset: int,
    child_count: int,
    *,
    bank_version: int | None,
) -> dict[str, Any]:
    """Decode the bounded flat mapping tail of a v150 type-6 container.

    The current flat layout places ``groupType``, ``groupId``,
    ``defaultValueId``, and the continuous-validation byte immediately before
    the already-proven Children array. Children are followed by variable value
    packages and fixed-size 14-byte association rows containing child id,
    flags, switch mode, fade-out time, and fade-in time. Some current type-6
    objects use a distinct tail; those fail closed with offsets while normal
    child traversal remains unchanged.
    """

    tail_start = children_offset + 4 + child_count * 4

    def unresolved(reason: str, offset: int) -> dict[str, Any]:
        bounded_offset = max(0, min(offset, len(data)))
        return {
            "parserStatus": "unresolvedV150SwitchTail",
            "failureReason": reason,
            "unresolvedTailOffset": bounded_offset,
            "unresolvedTailByteLength": len(data) - bounded_offset,
            "runtimeSelection": "groupValueUnobservedAllChildrenRemainPossible",
        }

    if bank_version != 150:
        return {
            "parserStatus": "unsupportedBankVersion",
            "bankVersion": bank_version,
            "unresolvedTailOffset": tail_start,
            "unresolvedTailByteLength": max(0, len(data) - tail_start),
            "runtimeSelection": "groupValueUnobservedAllChildrenRemainPossible",
        }
    if children_offset < 10:
        return unresolved("selectorHeaderBeforeObjectStart", children_offset)
    if tail_start + 4 > len(data):
        return unresolved("truncatedPackageCount", tail_start)

    group_type_raw = data[children_offset - 10]
    if group_type_raw not in (0, 1):
        return unresolved("invalidGroupType", children_offset - 10)
    group_id = unpack_from("<I", data, children_offset - 9)[0]
    default_value_id = unpack_from("<I", data, children_offset - 5)[0]
    continuous_raw = data[children_offset - 1]
    if continuous_raw not in (0, 1):
        return unresolved("invalidContinuousValidation", children_offset - 1)

    package_count = unpack_from("<I", data, tail_start)[0]
    if package_count == 0:
        return unresolved("noValuePackages", tail_start)
    offset = tail_start + 4
    if package_count > (len(data) - offset) // 8:
        return unresolved("invalidPackageCount", tail_start)
    packages: list[dict[str, Any]] = []
    mapped_child_ids: set[int] = set()
    for package_index in range(package_count):
        if offset + 8 > len(data):
            return unresolved("truncatedPackageHeader", offset)
        value_id, mapped_child_count = unpack_from("<II", data, offset)
        offset += 8
        if mapped_child_count > (len(data) - offset) // 4:
            return unresolved("invalidMappedChildCount", offset - 4)
        child_ids = [
            unpack_from("<I", data, offset + index * 4)[0]
            for index in range(mapped_child_count)
        ]
        offset += mapped_child_count * 4
        mapped_child_ids.update(child_ids)
        packages.append({
            "packageIndex": package_index,
            "valueId": value_id,
            "isDefaultValue": value_id == default_value_id,
            "mappedChildCount": mapped_child_count,
            "childIds": child_ids,
        })

    if offset + 4 > len(data):
        return unresolved("truncatedAssociationCount", offset)
    association_count = unpack_from("<I", data, offset)[0]
    offset += 4
    association_bytes = association_count * 14
    if association_count > (len(data) - offset) // 14:
        return unresolved("invalidAssociationCount", offset - 4)
    if offset + association_bytes != len(data):
        return unresolved("unexpectedAssociationTrailingBytes", offset + association_bytes)
    associations: list[dict[str, Any]] = []
    for association_index in range(association_count):
        child_id = unpack_from("<I", data, offset)[0]
        flags_raw = data[offset + 4]
        switch_mode_byte = data[offset + 5]
        switch_mode_raw = switch_mode_byte & 0x07
        fade_out_time = unpack_from("<i", data, offset + 6)[0]
        fade_in_time = unpack_from("<i", data, offset + 10)[0]
        associations.append({
            "associationIndex": association_index,
            "childId": child_id,
            "flagsRaw": flags_raw,
            "isFirstOnly": bool(flags_raw & 0x01),
            "continuePlayback": bool(flags_raw & 0x02),
            "flagsUnknownMask": flags_raw & 0xFC,
            "onSwitchMode": {0: "playToEnd", 1: "stop"}.get(
                switch_mode_raw, "unknown"
            ),
            "onSwitchModeRaw": switch_mode_raw,
            "onSwitchModeRawByte": switch_mode_byte,
            "onSwitchModeUnknownMask": switch_mode_byte & 0xF8,
            "fadeOutTimeMs": fade_out_time,
            "fadeInTimeMs": fade_in_time,
        })
        offset += 14

    authored_children = {
        unpack_from("<I", data, children_offset + 4 + index * 4)[0]
        for index in range(child_count)
    }
    association_child_ids = {row["childId"] for row in associations}
    return {
        "parserStatus": "typedExactV150FlatPackages",
        "selectionStructure": "flatValuePackages",
        "groupType": "switch" if group_type_raw == 0 else "state",
        "groupTypeRaw": group_type_raw,
        "groupId": group_id,
        "defaultValueId": default_value_id,
        "continuousValidation": bool(continuous_raw),
        "continuousValidationRaw": continuous_raw,
        "packageCount": package_count,
        "packages": packages,
        "associationCount": association_count,
        "associations": associations,
        "mappedChildIdsOutsideChildren": sorted(mapped_child_ids - authored_children),
        "unmappedChildIds": sorted(authored_children - mapped_child_ids),
        "associationChildIdsOutsideChildren": sorted(
            association_child_ids - authored_children
        ),
        "decisionTreeStatus": "noSeparateBytesAfterTypedFlatPackagesAndAssociations",
        "runtimeSelection": "groupValueUnobservedAllChildrenRemainPossible",
    }

def _hirc_v150_music_common_tail(
    data: bytes,
    children_offset: int,
    child_count: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode the fixed v150 music meter/stinger tail after Children."""

    try:
        offset = children_offset + 4 + child_count * 4
        if offset + 27 > len(data):
            raise ValueError("truncated v150 music meter")
        grid_period = unpack_from("<d", data, offset)[0]
        grid_offset = unpack_from("<d", data, offset + 8)[0]
        tempo = unpack_from("<f", data, offset + 16)[0]
        time_signature_numerator = data[offset + 20]
        time_signature_beat = data[offset + 21]
        meter_override = bool(data[offset + 22])
        stinger_count = unpack_from("<I", data, offset + 23)[0]
        offset += 27
        stinger_bytes = stinger_count * 24
        if offset + stinger_bytes > len(data):
            raise ValueError("truncated v150 music stingers")
        stingers = [
            {
                "triggerId": unpack_from("<I", data, offset + index * 24)[0],
                "segmentId": unpack_from("<I", data, offset + index * 24 + 4)[0],
                "syncType": unpack_from("<I", data, offset + index * 24 + 8)[0],
                "cueFilterHash": unpack_from("<I", data, offset + index * 24 + 12)[0],
            }
            for index in range(stinger_count)
        ]
        offset += stinger_bytes
        return ({
            "gridPeriod": grid_period,
            "gridOffset": grid_offset,
            "tempo": tempo,
            "timeSignatureNumerator": time_signature_numerator,
            "timeSignatureBeat": time_signature_beat,
            "meterOverride": meter_override,
            "stingerCount": stinger_count,
            "stingers": stingers,
        }, offset)
    except (ValueError, OverflowError):
        return None

def _hirc_v150_music_transition_tail(
    data: bytes,
    offset: int,
) -> tuple[dict[str, Any], int] | None:
    """Decode v150 MusicTransAware rules far enough to reach selector data."""

    try:
        rule_count, offset = _hirc_v150_u32(data, offset)
        rules: list[dict[str, Any]] = []
        for _ in range(rule_count):
            source_count, offset = _hirc_v150_u32(data, offset)
            source_bytes = source_count * 4
            if offset + source_bytes > len(data):
                raise ValueError("truncated v150 music transition sources")
            source_ids = [unpack_from("<I", data, offset + index * 4)[0] for index in range(source_count)]
            offset += source_bytes
            destination_count, offset = _hirc_v150_u32(data, offset)
            destination_bytes = destination_count * 4
            if offset + destination_bytes > len(data):
                raise ValueError("truncated v150 music transition destinations")
            destination_ids = [
                unpack_from("<I", data, offset + index * 4)[0]
                for index in range(destination_count)
            ]
            offset += destination_bytes
            if offset + 48 > len(data):
                raise ValueError("truncated v150 music transition rule")
            # Source rule is 21 bytes; destination rule is 26 bytes in v150.
            offset += 47
            has_transition_segment = bool(data[offset])
            offset += 1
            transition_segment_id = None
            if has_transition_segment:
                if offset + 30 > len(data):
                    raise ValueError("truncated v150 music transition segment")
                transition_segment_id = unpack_from("<I", data, offset)[0]
                offset += 30
            rules.append({
                "sourceIds": source_ids,
                "destinationIds": destination_ids,
                "transitionSegmentId": transition_segment_id,
            })
        return ({"transitionRuleCount": rule_count, "transitionRules": rules}, offset)
    except (ValueError, OverflowError):
        return None

def hirc_v150_music_segment_structure(
    data: bytes,
    children_offset: int,
    child_count: int,
) -> dict[str, Any] | None:
    common = _hirc_v150_music_common_tail(data, children_offset, child_count)
    if not common:
        return None
    common_row, offset = common
    try:
        if offset + 12 > len(data):
            raise ValueError("truncated v150 MusicSegment")
        duration = unpack_from("<d", data, offset)[0]
        marker_count = unpack_from("<I", data, offset + 8)[0]
        offset += 12
        markers: list[dict[str, Any]] = []
        for _ in range(marker_count):
            if offset + 12 > len(data):
                raise ValueError("truncated v150 MusicSegment marker")
            marker_id = unpack_from("<I", data, offset)[0]
            position = unpack_from("<d", data, offset + 4)[0]
            offset += 12
            name_end = data.find(b"\x00", offset)
            if name_end < 0:
                raise ValueError("unterminated v150 MusicSegment marker")
            marker_name = data[offset:name_end].decode("utf-8", errors="replace")
            offset = name_end + 1
            markers.append({"id": marker_id, "position": position, "name": marker_name})
        if offset != len(data):
            raise ValueError("unexpected v150 MusicSegment trailing bytes")
        return {**common_row, "duration": duration, "markerCount": marker_count, "markers": markers}
    except (ValueError, OverflowError):
        return None

def hirc_v150_music_switch_structure(
    data: bytes,
    children_offset: int,
    child_count: int,
    child_ids: list[int] | None = None,
) -> dict[str, Any] | None:
    """Decode a v150 MusicSwitch decision tree and check its child backlinks."""
    common = _hirc_v150_music_common_tail(data, children_offset, child_count)
    if not common:
        return None
    common_row, offset = common
    transitions = _hirc_v150_music_transition_tail(data, offset)
    if not transitions:
        return None
    transition_row, offset = transitions
    try:
        if offset + 5 > len(data):
            raise ValueError("truncated v150 MusicSwitch header")
        continue_playback = bool(data[offset])
        tree_depth = unpack_from("<I", data, offset + 1)[0]
        offset += 5
        argument_bytes = tree_depth * 4
        if offset + argument_bytes + tree_depth > len(data):
            raise ValueError("truncated v150 MusicSwitch arguments")
        group_ids = [unpack_from("<I", data, offset + index * 4)[0] for index in range(tree_depth)]
        offset += argument_bytes
        group_types = list(data[offset:offset + tree_depth])
        offset += tree_depth
        tree_size, offset = _hirc_v150_u32(data, offset)
        if offset + 1 + tree_size != len(data) or tree_size % 12:
            raise ValueError("invalid v150 MusicSwitch decision tree size")
        tree_mode = data[offset]
        offset += 1
        tree_data = data[offset:offset + tree_size]
        raw_nodes = [
            {
                "key": unpack_from("<I", tree_data, index)[0],
                "value": unpack_from("<I", tree_data, index + 4)[0],
                "weight": unpack_from("<H", tree_data, index + 8)[0],
                "probability": unpack_from("<H", tree_data, index + 10)[0],
            }
            for index in range(0, tree_size, 12)
        ]
        leaves: list[dict[str, Any]] = []
        visited: set[int] = set()

        def visit(index: int, depth: int, path: tuple[int, ...]) -> None:
            if index < 0 or index >= len(raw_nodes) or index in visited:
                raise ValueError("invalid v150 MusicSwitch tree topology")
            visited.add(index)
            node = raw_nodes[index]
            current_path = (*path, int(node["key"]))
            if depth >= tree_depth:
                leaves.append({
                    "audioNodeId": int(node["value"]),
                    "pathKeys": list(current_path),
                    "weight": int(node["weight"]),
                    "probability": int(node["probability"]),
                })
                return
            child_index = int(node["value"]) & 0xFFFF
            child_count_value = (int(node["value"]) >> 16) & 0xFFFF
            if not child_count_value or child_index + child_count_value > len(raw_nodes):
                raise ValueError("invalid v150 MusicSwitch child range")
            for child in range(child_index, child_index + child_count_value):
                visit(child, depth + 1, current_path)

        if raw_nodes:
            visit(0, 0, ())
        if len(visited) != len(raw_nodes):
            raise ValueError("unreachable v150 MusicSwitch tree nodes")
        tree_leaf_ids = [int(row["audioNodeId"]) for row in leaves]
        if child_ids is None:
            selector_validation = {
                "status": "notCheckedNoReciprocalChildren",
                "treeLeafIds": sorted(set(tree_leaf_ids)),
                "reciprocalChildIds": None,
                "treeLeafIdsOutsideReciprocalChildren": [],
                "reciprocalChildrenWithoutTreeLeaf": [],
            }
        else:
            tree_leaf_id_set = set(tree_leaf_ids)
            reciprocal_child_id_set = set(int(child_id) for child_id in child_ids)
            outside = sorted(tree_leaf_id_set - reciprocal_child_id_set)
            missing = sorted(reciprocal_child_id_set - tree_leaf_id_set)
            if outside:
                status = "treeLeafOutsideReciprocalChildren"
            elif missing:
                status = "decisionTreeSubsetOfReciprocalChildren"
            else:
                status = "reciprocalChildrenCovered"
            selector_validation = {
                "status": status,
                "treeLeafIds": sorted(tree_leaf_id_set),
                "reciprocalChildIds": sorted(reciprocal_child_id_set),
                "treeLeafIdsOutsideReciprocalChildren": outside,
                "reciprocalChildrenWithoutTreeLeaf": missing,
            }
        return {
            **common_row,
            **transition_row,
            "continuePlayback": continue_playback,
            "treeDepth": tree_depth,
            "arguments": [
                {"groupId": group_id, "groupType": group_types[index]}
                for index, group_id in enumerate(group_ids)
            ],
            "treeMode": tree_mode,
            "treeNodeCount": len(raw_nodes),
            "treeLeafCount": len(leaves),
            "treeLeaves": leaves,
            "selectorValidation": selector_validation,
        }
    except (ValueError, OverflowError):
        return None

def refine_hirc_v150_music_switch_selector_ownership(
    structure: dict[str, Any],
    object_id: int,
    objects: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Classify decision-tree leaves without equating them to direct Children.

    MusicSwitch trees may target a recursively owned descendant or an explicit
    zero/unbound branch.  Neither case is a direct reciprocal Child, but both
    are structurally bounded.  A nonzero object missing from this embedded bank
    or owned by another parent remains unresolved and is never traversed here.
    """

    validation = dict(structure.get("selectorValidation") or {})
    direct_child_ids = {
        int(value) for value in validation.get("reciprocalChildIds") or []
    }
    recursive_ids: set[int] = set()
    zero_ids: set[int] = set()
    same_bank_missing_ids: set[int] = set()
    local_other_parent_ids: set[int] = set()

    transition_sources = {
        int(value)
        for rule in structure.get("transitionRules") or []
        if isinstance(rule, dict)
        for value in rule.get("sourceIds") or []
    }
    transition_destinations = {
        int(value)
        for rule in structure.get("transitionRules") or []
        if isinstance(rule, dict)
        for value in rule.get("destinationIds") or []
    }

    def parent_id(node_id: int) -> int | None:
        node = objects.get(node_id)
        if not isinstance(node, dict):
            return None
        if node.get("_typedParentIdParsed"):
            value = node.get("_typedParentId")
            return int(value) if value is not None else None
        value = hirc_object_parent_id(
            int(node.get("type") or 0), node.get("data") or b""
        )
        node["_typedParentIdParsed"] = True
        node["_typedParentId"] = value
        return value

    for leaf in structure.get("treeLeaves") or []:
        if not isinstance(leaf, dict):
            continue
        leaf_id = int(leaf.get("audioNodeId") or 0)
        roles: list[str] = []
        if leaf_id in transition_sources:
            roles.append("transitionSource")
        if leaf_id in transition_destinations:
            roles.append("transitionDestination")
        leaf["transitionReferenceRoles"] = roles
        if leaf_id in direct_child_ids:
            leaf["ownershipStatus"] = "directReciprocalChild"
            leaf["ownershipParentChain"] = [object_id]
            continue
        if leaf_id == 0:
            zero_ids.add(leaf_id)
            leaf["ownershipStatus"] = "explicitUnboundLeaf"
            leaf["ownershipParentChain"] = []
            continue
        if leaf_id not in objects:
            same_bank_missing_ids.add(leaf_id)
            leaf["ownershipStatus"] = "sameBankObjectMissing"
            leaf["ownershipParentChain"] = []
            continue

        chain: list[int] = []
        seen = {leaf_id}
        cursor = leaf_id
        recursive = False
        for _ in range(64):
            parent = parent_id(cursor)
            if parent is None or parent == 0 or parent in seen:
                break
            chain.append(parent)
            if parent == object_id:
                recursive = True
                break
            seen.add(parent)
            cursor = parent
        leaf["ownershipParentChain"] = chain
        if recursive:
            recursive_ids.add(leaf_id)
            leaf["ownershipStatus"] = "recursiveOwnedDescendant"
        else:
            local_other_parent_ids.add(leaf_id)
            leaf["ownershipStatus"] = "sameBankOtherParent"

    validation.update({
        "recursiveOwnedDescendantIds": sorted(recursive_ids),
        "zeroUnboundLeafIds": sorted(zero_ids),
        "sameBankMissingLeafIds": sorted(same_bank_missing_ids),
        "localOtherParentLeafIds": sorted(local_other_parent_ids),
        "ownedDirectChildIdsNotInTreeLeaves": list(
            validation.get("reciprocalChildrenWithoutTreeLeaf") or []
        ),
        "runtimeBranchStatus": "groupValuesAndActiveLeafNotObserved",
    })
    unresolved_ids = same_bank_missing_ids | local_other_parent_ids
    if unresolved_ids:
        validation["status"] = "decisionTreeLeafOwnershipUnresolved"
    elif recursive_ids or zero_ids:
        validation["status"] = "decisionTreeIndirectAndUnboundLeavesResolved"
    structure["selectorValidation"] = validation
    return structure

def hirc_v150_music_random_sequence_structure(
    data: bytes,
    children_offset: int,
    child_count: int,
    child_ids: list[int] | None = None,
) -> dict[str, Any] | None:
    common = _hirc_v150_music_common_tail(data, children_offset, child_count)
    if not common:
        return None
    common_row, offset = common
    transitions = _hirc_v150_music_transition_tail(data, offset)
    if not transitions:
        return None
    transition_row, offset = transitions
    try:
        playlist_count, offset = _hirc_v150_u32(data, offset)
        items: list[dict[str, Any]] = []

        def read_item(depth: int, parent_index: int | None) -> None:
            nonlocal offset
            if len(items) >= playlist_count or offset + 30 > len(data):
                raise ValueError("truncated v150 MusicRanSeq playlist")
            segment_id = unpack_from("<I", data, offset)[0]
            playlist_item_id = unpack_from("<I", data, offset + 4)[0]
            nested_count = unpack_from("<I", data, offset + 8)[0]
            selection_type = unpack_from("<I", data, offset + 12)[0]
            row = {
                "index": len(items),
                "parentIndex": parent_index,
                "depth": depth,
                "segmentId": segment_id,
                "playlistItemId": playlist_item_id,
                "childCount": nested_count,
                "selectionType": selection_type,
                "selectionTypeLabel": {
                    0: "continuousSequence",
                    1: "stepSequence",
                    2: "continuousRandom",
                    3: "stepRandom",
                    0xFFFFFFFF: "none",
                }.get(selection_type, f"type{selection_type}"),
                "loop": unpack_from("<h", data, offset + 16)[0],
                "loopMin": unpack_from("<h", data, offset + 18)[0],
                "loopMax": unpack_from("<h", data, offset + 20)[0],
                "weight": unpack_from("<I", data, offset + 22)[0],
                "avoidRepeatCount": unpack_from("<H", data, offset + 26)[0],
                "usesWeight": bool(data[offset + 28]),
                "shuffle": bool(data[offset + 29]),
            }
            offset += 30
            item_index = len(items)
            items.append(row)
            for _ in range(nested_count):
                read_item(depth + 1, item_index)

        if playlist_count:
            read_item(0, None)
        if len(items) != playlist_count or offset != len(data):
            raise ValueError("invalid v150 MusicRanSeq playlist size")
        terminal_items = [
            row for row in items if int(row.get("childCount") or 0) == 0
        ]
        terminal_segment_ids = [
            int(row["segmentId"])
            for row in terminal_items
            if int(row.get("segmentId") or 0) not in {0, 0xFFFFFFFF}
        ]
        if child_ids is None:
            selector_validation = {
                "status": "notCheckedNoReciprocalChildren",
                "playlistTerminalSegmentIds": sorted(set(terminal_segment_ids)),
                "reciprocalChildIds": None,
                "playlistTerminalSegmentIdsOutsideReciprocalChildren": [],
                "reciprocalChildrenWithoutPlaylistTerminal": [],
                "terminalPlaylistItemCount": len(terminal_items),
                "terminalItemsWithSentinelSegmentId": len(terminal_items) - len(terminal_segment_ids),
            }
        else:
            terminal_segment_id_set = set(terminal_segment_ids)
            reciprocal_child_id_set = set(int(child_id) for child_id in child_ids)
            outside = sorted(terminal_segment_id_set - reciprocal_child_id_set)
            missing = sorted(reciprocal_child_id_set - terminal_segment_id_set)
            if outside:
                status = "terminalSegmentOutsideReciprocalChildren"
            elif missing:
                status = "playlistSubsetOfReciprocalChildren"
            else:
                status = "reciprocalChildrenCovered"
            selector_validation = {
                "status": status,
                "playlistTerminalSegmentIds": sorted(terminal_segment_id_set),
                "reciprocalChildIds": sorted(reciprocal_child_id_set),
                "playlistTerminalSegmentIdsOutsideReciprocalChildren": outside,
                "reciprocalChildrenWithoutPlaylistTerminal": missing,
                "terminalPlaylistItemCount": len(terminal_items),
                "terminalItemsWithSentinelSegmentId": len(terminal_items) - len(terminal_segment_ids),
            }
        return {
            **common_row,
            **transition_row,
            "playlistItemCount": playlist_count,
            "playlistItems": items,
            "selectionTypeLabels": sorted({str(row["selectionTypeLabel"]) for row in items}),
            "selectorValidation": selector_validation,
        }
    except (ValueError, OverflowError, RecursionError):
        return None

def hirc_v150_music_structure(
    object_type: int,
    data: bytes,
    children_offset: int,
    child_count: int,
    child_ids: list[int] | None = None,
) -> dict[str, Any] | None:
    parser = {
        10: hirc_v150_music_segment_structure,
        12: hirc_v150_music_switch_structure,
        13: hirc_v150_music_random_sequence_structure,
    }.get(object_type)
    if not parser:
        return None
    if object_type in {12, 13}:
        return parser(data, children_offset, child_count, child_ids)
    return parser(data, children_offset, child_count)

def hirc_v150_empty_music_children(
    object_type: int,
    data: bytes,
) -> tuple[list[int], int, dict[str, Any]] | None:
    """Prove an empty music Children array through a unique typed tail parse.

    Empty lists have no child parent backlinks.  A zero count is accepted only
    when exactly one offset lets the complete type-specific meter/transition/
    selector tail consume the HIRC object to its exact end.
    """

    matches: list[tuple[list[int], int, dict[str, Any]]] = []
    for offset in range(0, max(0, len(data) - 3)):
        if unpack_from("<I", data, offset)[0] != 0:
            continue
        structure = hirc_v150_music_structure(object_type, data, offset, 0, [])
        if structure:
            matches.append(([], offset, structure))
            if len(matches) > 1:
                return None
    return matches[0] if len(matches) == 1 else None

def hirc_v150_random_sequence_properties(
    data: bytes,
    children_offset: int,
    child_ids: list[int],
    *,
    bank_version: int | None,
) -> dict[str, Any]:
    """Decode a bounded v150 Random/Sequence container policy and playlist.

    The fixed 24-byte policy block precedes the reciprocal Children array. A
    U16 playlist count and ``childId, weight`` rows follow Children. Playlist
    order is authored selection order and may differ from Children order, so
    Sequence semantics must never be reconstructed from Children alone.
    """

    tail_start = children_offset + 4 + len(child_ids) * 4
    policy: dict[str, Any] = {}

    def unresolved(reason: str, offset: int) -> dict[str, Any]:
        bounded_offset = max(0, min(offset, len(data)))
        return {
            **policy,
            "selectorParserStatus": "unresolvedV150RandomSequenceTail",
            "selectorParserFailureReason": reason,
            "selectorUnresolvedOffset": bounded_offset,
            "selectorUnresolvedByteLength": len(data) - bounded_offset,
            "runtimeSelection": "randomHistoryOrSequenceCursorUnobservedAllChildrenRemainPossible",
        }

    if bank_version != 150:
        return {
            "selectorParserStatus": "unsupportedBankVersion",
            "bankVersion": bank_version,
            "selectorUnresolvedOffset": max(0, tail_start),
            "selectorUnresolvedByteLength": max(0, len(data) - tail_start),
            "runtimeSelection": "randomHistoryOrSequenceCursorUnobservedAllChildrenRemainPossible",
        }
    if children_offset < 24:
        return unresolved("selectorHeaderBeforeObjectStart", children_offset)
    if tail_start + 2 > len(data):
        return unresolved("truncatedPlaylistCount", tail_start)

    loop_count, loop_min, loop_max = unpack_from("<HHH", data, children_offset - 24)
    transition_time, transition_min, transition_max = unpack_from(
        "<fff", data, children_offset - 18
    )
    avoid_repeat_count = unpack_from("<H", data, children_offset - 6)[0]
    transition_mode = data[children_offset - 4]
    random_mode = data[children_offset - 3]
    mode = data[children_offset - 2]
    flags = data[children_offset - 1]
    if mode not in (0, 1):
        return unresolved("invalidRandomSequenceMode", children_offset - 2)
    if random_mode not in (0, 1):
        return unresolved("invalidRandomMode", children_offset - 3)
    if transition_mode not in range(6):
        return unresolved("invalidTransitionMode", children_offset - 4)
    transition_labels = {
        0: "disabled",
        1: "crossFadeAmplitude",
        2: "crossFadePower",
        3: "delay",
        4: "sampleAccurate",
        5: "triggerRate",
    }
    policy.update({
        "mode": mode,
        "modeLabel": "random" if mode == 0 else "sequence",
        "randomMode": random_mode,
        "randomModeLabel": "standard" if random_mode == 0 else "shuffle",
        "loopCount": loop_count,
        "loopModifierMin": loop_min,
        "loopModifierMax": loop_max,
        "transitionTime": transition_time,
        "transitionModifierMin": transition_min,
        "transitionModifierMax": transition_max,
        "avoidRepeatCount": avoid_repeat_count,
        "transitionMode": transition_mode,
        "transitionModeLabel": transition_labels[transition_mode],
        "flags": flags,
        "weightFlagRaw": bool(flags & 0x01),
        "resetPlaylistAtEachPlay": bool(flags & 0x02),
        "restartBackward": bool(flags & 0x04),
        "continuous": bool(flags & 0x08),
        "globalScope": bool(flags & 0x10),
        "flagsUnknownMask": flags & 0xE0,
        "flagLabels": [
            label
            for bit, label in (
                (0, "weightFlagSet"),
                (1, "resetPlaylistAtEachPlay"),
                (2, "restartBackward"),
                (3, "continuous"),
                (4, "global"),
            )
            if flags & (1 << bit)
        ],
    })

    playlist_count = unpack_from("<H", data, tail_start)[0]
    playlist_offset = tail_start + 2
    playlist_bytes = playlist_count * 8
    if playlist_offset + playlist_bytes != len(data):
        return unresolved("unexpectedPlaylistTailLength", playlist_offset + playlist_bytes)
    playlist_items = [
        {
            "playlistOrdinal": index,
            "childId": unpack_from("<I", data, playlist_offset + index * 8)[0],
            "weight": unpack_from("<I", data, playlist_offset + index * 8 + 4)[0],
        }
        for index in range(playlist_count)
    ]
    playlist_child_ids = [row["childId"] for row in playlist_items]
    playlist_child_id_set = set(playlist_child_ids)
    reciprocal_child_id_set = set(child_ids)
    outside = sorted(playlist_child_id_set - reciprocal_child_id_set)
    owned_not_in_playlist = sorted(reciprocal_child_id_set - playlist_child_id_set)
    if outside:
        return unresolved("playlistChildOutsideReciprocalChildren", playlist_offset)
    duplicate_count = len(playlist_child_ids) - len(playlist_child_id_set)
    if not playlist_items:
        membership_status = "emptyPlaylistOwnedChildrenPreserved"
    elif duplicate_count:
        membership_status = "playlistWithRepeatedOwnedChildren"
    elif owned_not_in_playlist:
        membership_status = "playlistSubsetOfOwnedChildren"
    else:
        membership_status = "playlistCoversOwnedChildren"
    weights = [row["weight"] for row in playlist_items]
    return {
        **policy,
        "selectorParserStatus": "typedExactV150PlaylistWeights",
        "playlistItemCount": playlist_count,
        "playlistItems": playlist_items,
        "playlistChildOrder": playlist_child_ids,
        "childrenOrderMatchesPlaylist": playlist_child_ids == child_ids,
        "playlistMembershipStatus": membership_status,
        "playlistUniqueChildCount": len(playlist_child_id_set),
        "duplicatePlaylistItemCount": duplicate_count,
        "playlistChildIdsOutsideChildren": outside,
        "ownedChildIdsNotInPlaylist": owned_not_in_playlist,
        "nonDefaultWeightCount": sum(weight != 50000 for weight in weights),
        "uniformWeights": len(set(weights)) <= 1,
        "weightUsageStatus": "playlistWeightsPreservedWeightFlagNotUsedAsGate",
        "runtimeSelection": "randomHistoryOrSequenceCursorUnobservedAllChildrenRemainPossible",
    }

def hirc_v150_layer_tail(
    data: bytes,
    tail_offset: int,
    child_ids: list[int],
    *,
    bank_version: int | None,
) -> dict[str, Any]:
    """Decode the bounded v150 CAkLayerCntr tail after Children.

    A Layer container is a blend surface, not a one-child selector. Each Layer
    binds an RTPC to child-specific curves. Static bank data therefore proves
    possible blends/crossfades, while the live RTPC value and audible child
    gains remain unknown.
    """

    def unresolved(reason: str, offset: int) -> dict[str, Any]:
        bounded = max(0, min(offset, len(data)))
        return {
            "layerTailParserStatus": "unresolvedV150LayerTail",
            "layerTailFailureReason": reason,
            "layerTailUnresolvedOffset": bounded,
            "layerTailUnresolvedByteLength": len(data) - bounded,
            "runtimeSelection": "layerRtpcValueUnobservedAllChildrenRemainPossible",
        }

    if bank_version != 150:
        return {
            "layerTailParserStatus": "unsupportedBankVersion",
            "bankVersion": bank_version,
            "layerTailUnresolvedOffset": max(0, min(tail_offset, len(data))),
            "layerTailUnresolvedByteLength": max(0, len(data) - tail_offset),
            "runtimeSelection": "layerRtpcValueUnobservedAllChildrenRemainPossible",
        }

    offset = tail_offset

    def take_u8(label: str) -> int:
        nonlocal offset
        if offset + 1 > len(data):
            raise ValueError(f"truncated{label}")
        value = data[offset]
        offset += 1
        return value

    def take_u16(label: str) -> int:
        nonlocal offset
        if offset + 2 > len(data):
            raise ValueError(f"truncated{label}")
        value = unpack_from("<H", data, offset)[0]
        offset += 2
        return value

    def take_u32(label: str) -> int:
        nonlocal offset
        if offset + 4 > len(data):
            raise ValueError(f"truncated{label}")
        value = unpack_from("<I", data, offset)[0]
        offset += 4
        return value

    def take_f32(label: str) -> float:
        nonlocal offset
        if offset + 4 > len(data):
            raise ValueError(f"truncated{label}")
        value = unpack_from("<f", data, offset)[0]
        offset += 4
        return value

    def take_varuint(label: str) -> int:
        nonlocal offset
        value = 0
        for index in range(10):
            byte = take_u8(label)
            value |= (byte & 0x7F) << (index * 7)
            if not byte & 0x80:
                return value
        raise ValueError(f"invalid{label}Varint")

    def take_curve_points(count: int, label: str) -> list[dict[str, Any]]:
        if count > (len(data) - offset) // 12:
            raise ValueError(f"{label}PointCountTooLarge")
        points: list[dict[str, Any]] = []
        for point_index in range(count):
            from_value = take_f32(f"{label}PointFrom")
            to_value = take_f32(f"{label}PointTo")
            interpolation = take_u32(f"{label}PointInterpolation")
            points.append({
                "pointIndex": point_index,
                "from": from_value,
                "to": to_value,
                "interpolation": interpolation,
                "interpolationLabel": HIRC_FADE_CURVE_LABELS.get(
                    interpolation, f"curve{interpolation}"
                ),
            })
        return points

    rtpc_type_labels = {
        0: "gameParameter",
        1: "midiParameter",
        2: "switch",
        3: "state",
        4: "modulator",
    }
    rtpc_accum_labels = {
        0: "none",
        1: "exclusive",
        2: "additive",
        3: "multiply",
        4: "boolean",
        5: "maximum",
        6: "filter",
    }
    scaling_labels = {0: "none", 2: "decibel", 3: "log", 4: "decibelToLinear"}

    try:
        layer_count = take_u32("LayerCount")
        if layer_count > max(0, (len(data) - offset - 1) // 15):
            raise ValueError("layerCountTooLarge")
        layers: list[dict[str, Any]] = []
        association_child_ids: set[int] = set()
        initial_curve_total = 0
        association_total = 0
        point_total = 0
        for layer_index in range(layer_count):
            layer_id = take_u32("LayerId")
            initial_curve_count = take_u16("InitialRtpcCurveCount")
            initial_curves: list[dict[str, Any]] = []
            for curve_index in range(initial_curve_count):
                rtpc_id = take_u32("InitialRtpcId")
                rtpc_type = take_u8("InitialRtpcType")
                rtpc_accum = take_u8("InitialRtpcAccum")
                param_id = take_varuint("InitialParamId")
                curve_id = take_u32("InitialRtpcCurveId")
                scaling = take_u8("InitialRtpcScaling")
                point_count = take_u16("InitialRtpcPointCount")
                points = take_curve_points(point_count, "InitialRtpc")
                initial_curves.append({
                    "curveIndex": curve_index,
                    "rtpcId": rtpc_id,
                    "rtpcType": rtpc_type,
                    "rtpcTypeLabel": rtpc_type_labels.get(rtpc_type, f"type{rtpc_type}"),
                    "rtpcAccum": rtpc_accum,
                    "rtpcAccumLabel": rtpc_accum_labels.get(rtpc_accum, f"mode{rtpc_accum}"),
                    "paramId": param_id,
                    "curveId": curve_id,
                    "scaling": scaling,
                    "scalingLabel": scaling_labels.get(scaling, f"scaling{scaling}"),
                    "pointCount": point_count,
                    "points": points,
                })
                point_total += point_count
            layer_rtpc_id = take_u32("LayerRtpcId")
            layer_rtpc_type = take_u8("LayerRtpcType")
            association_count = take_u32("LayerAssociationCount")
            if association_count > (len(data) - offset) // 8:
                raise ValueError("layerAssociationCountTooLarge")
            associations: list[dict[str, Any]] = []
            for association_index in range(association_count):
                child_id = take_u32("LayerAssociationChildId")
                curve_point_count = take_u32("LayerAssociationCurvePointCount")
                points = take_curve_points(curve_point_count, "LayerAssociation")
                association_child_ids.add(child_id)
                associations.append({
                    "associationIndex": association_index,
                    "childId": child_id,
                    "curvePointCount": curve_point_count,
                    "curvePoints": points,
                })
                point_total += curve_point_count
            layers.append({
                "layerIndex": layer_index,
                "layerId": layer_id,
                "initialRtpcCurveCount": initial_curve_count,
                "initialRtpcCurves": initial_curves,
                "rtpcId": layer_rtpc_id,
                "rtpcType": layer_rtpc_type,
                "rtpcTypeLabel": rtpc_type_labels.get(
                    layer_rtpc_type, f"type{layer_rtpc_type}"
                ),
                "associationCount": association_count,
                "associations": associations,
            })
            initial_curve_total += initial_curve_count
            association_total += association_count
        continuous_raw = take_u8("ContinuousValidation")
        if continuous_raw not in (0, 1):
            raise ValueError("invalidContinuousValidation")
        if offset != len(data):
            raise ValueError("unexpectedTrailingBytes")
    except (ValueError, OverflowError) as exc:
        return unresolved(str(exc), offset)

    child_set = set(child_ids)
    outside_children = sorted(association_child_ids - child_set)
    return {
        "layerTailParserStatus": "typedExactV150LayerTail",
        "layerAssignmentStatus": (
            "nonEmptyCurves" if layer_count else "zeroLayerAssignments"
        ),
        "layerCount": layer_count,
        "layers": layers,
        "initialRtpcCurveCount": initial_curve_total,
        "associationCount": association_total,
        "curvePointCount": point_total,
        "associationChildIdsOutsideChildren": outside_children,
        "continuousValidation": bool(continuous_raw),
        "continuousValidationRaw": continuous_raw,
        "runtimeSelection": "layerRtpcValueUnobservedAllChildrenRemainPossible",
    }

def hirc_v150_layer_child_candidate(
    data: bytes,
    objects: dict[int, dict[str, Any]],
    *,
    bank_version: int | None,
) -> tuple[list[int], int, dict[str, Any], str] | None:
    """Find one structurally exact type-9 Children+tail candidate.

    This is deliberately weaker than reciprocal-parent proof. Non-empty
    candidates require same-bank audio-node children, an exact Layer-tail
    parse, association children within the candidate Children set, and a
    unique matching byte offset. Canonical empty objects are accepted only at
    the current v150 offset/length fingerprint.
    """

    if bank_version != 150:
        return None
    matches: list[tuple[list[int], int, dict[str, Any], str]] = []
    for children_offset in range(0, max(0, len(data) - 7)):
        child_count = unpack_from("<I", data, children_offset)[0]
        if child_count <= 0 or child_count > (len(data) - children_offset - 4) // 4:
            continue
        child_ids = [
            unpack_from("<I", data, children_offset + 4 + index * 4)[0]
            for index in range(child_count)
        ]
        if any(child_id not in objects for child_id in child_ids):
            continue
        if any(
            int(objects[child_id].get("type") or 0) not in HIRC_AUDIO_NODE_TYPES
            for child_id in child_ids
        ):
            continue
        tail_offset = children_offset + 4 + child_count * 4
        tail = hirc_v150_layer_tail(
            data, tail_offset, child_ids, bank_version=bank_version
        )
        if tail.get("layerTailParserStatus") != "typedExactV150LayerTail":
            continue
        if tail.get("associationChildIdsOutsideChildren"):
            continue
        matches.append((
            child_ids,
            children_offset,
            tail,
            "typedExactV150CandidateWithoutParentProof",
        ))
    if len(matches) == 1:
        return matches[0]
    if matches:
        return None

    canonical_offset = 31
    if len(data) == 40 and unpack_from("<I", data, canonical_offset)[0] == 0:
        tail = hirc_v150_layer_tail(
            data, canonical_offset + 4, [], bank_version=bank_version
        )
        if tail.get("layerTailParserStatus") == "typedExactV150LayerTail":
            return (
                [],
                canonical_offset,
                tail,
                "typedExactV150CanonicalEmpty",
            )
    return None

def summarize_hirc_action_dispatch(
    event_id: int,
    root_action_ids: list[int],
    action_evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """Describe serialized Event dispatch without claiming runtime sequence."""

    root_rows = sorted(
        (
            row
            for row in action_evidence
            if row.get("dispatchEventId") == event_id and row.get("isRootEventAction")
        ),
        key=lambda row: int(row.get("eventActionOrdinal") or 0),
    )
    playback_rows = [
        row
        for row in root_rows
        if row.get("operation") in {"play", "playEvent"}
    ]
    control_rows = [
        row
        for row in root_rows
        if row.get("operation") not in {"play", "playEvent"}
    ]
    playback_count = len(playback_rows)
    if not playback_count:
        timing_class = "noPlayback"
    elif playback_count == 1:
        timing_class = "singlePlayback"
    elif any(row.get("actionParserStatus") != "typedExactV150" for row in playback_rows):
        timing_class = "coDispatchActionTimingUnresolved"
    elif any(
        (row.get("delay") or {}).get("modifierRangesMs")
        for row in playback_rows
    ):
        timing_class = "dynamicDelayRangeUnresolved"
    else:
        delay_signatures = {
            tuple((row.get("delay") or {}).get("baseValuesMs") or [])
            for row in playback_rows
        }
        if delay_signatures == {()}:
            timing_class = "coDispatchNoExplicitDelay"
        elif len(delay_signatures) > 1:
            timing_class = "coDispatchWithAuthoredDelayDifference"
        else:
            timing_class = "coDispatchUniformExplicitDelay"

    def explicit_property_count(name: str) -> int:
        return sum(
            (row.get(name) or {}).get("serializationStatus")
            not in {None, "implicitDefaultNotSerialized"}
            for row in playback_rows
        )

    return {
        "serializedActionCount": len(root_action_ids),
        "serializedActionIds": root_action_ids,
        "playbackActionCount": playback_count,
        "playbackActionOrdinals": [row["eventActionOrdinal"] for row in playback_rows],
        "typedPlaybackActionCount": sum(
            row.get("actionParserStatus") == "typedExactV150" for row in playback_rows
        ),
        "failedPlaybackActionCount": sum(
            row.get("actionParserStatus") == "failedClosed" for row in playback_rows
        ),
        "multiPlayback": playback_count > 1,
        "timingClass": timing_class,
        "simultaneityCandidate": timing_class == "coDispatchNoExplicitDelay",
        "explicitDelayActionCount": explicit_property_count("delay"),
        "explicitTransitionActionCount": explicit_property_count("transition"),
        "probabilityGatedActionCount": explicit_property_count("probability"),
        "controlActionCount": len(control_rows),
        "typedControlActionCount": sum(
            row.get("actionControlParserStatus") == "typedExactV150"
            for row in control_rows
        ),
        "failedControlActionCount": sum(
            row.get("actionControlParserStatus") == "failedClosed"
            for row in control_rows
        ),
        "controlOperationCounts": dict(sorted(
            Counter(str(row.get("operation") or "unknown") for row in control_rows).items()
        )),
        "evidenceBoundary": (
            "Action ordinals prove serialized Event membership, not sequential "
            "execution or sample-accurate simultaneous audible onset; typed control "
            "payloads prove authored trigger parameters, not evaluated runtime state."
        ),
    }

def traverse_hirc_event(
    event_id: int,
    objects: dict[int, dict[str, Any]],
    decoded_media_ids: set[int] | None = None,
    bank_version: int | None = 150,
) -> dict[str, Any]:
    """Traverse one Event using only typed, downward v150 HIRC edges."""

    decoded_media_ids = decoded_media_ids or set()
    event_object = objects.get(event_id) or {}
    root_action_ids = hirc_event_action_ids(event_object.get("data") or b"")
    queue: deque[
        tuple[int, int, tuple[int, ...], tuple[int, ...], tuple[str, ...], int | None, int | None]
    ] = deque(
        (action_id, action_id, (event_id,), (4,), (), ordinal, event_id)
        for ordinal, action_id in enumerate(root_action_ids)
    )
    visited: set[int] = {event_id}
    visited_paths: set[tuple[int, int, int | None, int | None]] = set()
    source_media_ids: list[int] = []
    resolved_media_ids: list[int] = []
    media_evidence_by_id: dict[int, dict[str, Any]] = {}
    action_evidence: list[dict[str, Any]] = []
    container_evidence: list[dict[str, Any]] = []
    music_node_evidence: list[dict[str, Any]] = []
    source_object_evidence: list[dict[str, Any]] = []
    node_processing_by_object_id: dict[int, dict[str, Any]] = {}
    unresolved_nodes: list[dict[str, Any]] = []

    def record_media(
        media_id: int,
        object_id: int,
        object_type: int,
        root_action_id: int,
        relations: tuple[str, ...],
        source: dict[str, Any] | None = None,
    ) -> None:
        if media_id not in source_media_ids:
            source_media_ids.append(media_id)
        if media_id in decoded_media_ids and media_id not in resolved_media_ids:
            resolved_media_ids.append(media_id)
        media_row = media_evidence_by_id.setdefault(media_id, {
            "mediaId": media_id,
            "decoded": media_id in decoded_media_ids,
            "soundObjectIds": set(),
            "musicTrackObjectIds": set(),
            "rootActionIds": set(),
            "relationTypes": set(),
            "selectionPaths": set(),
            "sourceKinds": set(),
            "pluginIds": set(),
            "streamTypes": set(),
            "sourceBits": set(),
        })
        if object_type == 2:
            media_row["soundObjectIds"].add(object_id)
        elif object_type == 11:
            media_row["musicTrackObjectIds"].add(object_id)
        media_row["rootActionIds"].add(root_action_id)
        media_row["relationTypes"].update(relations)
        media_row["selectionPaths"].add(relations)
        if source:
            media_row["sourceKinds"].add(str(source.get("sourceKind") or "unknown"))
            media_row["pluginIds"].add(int(source.get("pluginId") or 0))
            media_row["streamTypes"].add(int(source.get("streamType") or 0))
            media_row["sourceBits"].add(int(source.get("sourceBits") or 0))

    def record_source(
        source: dict[str, Any],
        object_id: int,
        object_type: int,
        root_action_id: int,
        relations: tuple[str, ...],
        serialized_path_ids: tuple[int, ...],
        serialized_path_types: tuple[int, ...],
    ) -> None:
        source_kind = str(source.get("sourceKind") or "unsupportedPluginSource")
        source_id = int(source.get("sourceId") or 0)
        decoded_match = source_kind == "codecMedia" and source_id in decoded_media_ids
        if decoded_match:
            location_status = "decodedMediaIndexMatch"
        elif source_kind == "codecMedia":
            location_status = "unresolvedCodecMedia"
        elif source_kind == "externalSourceCodec":
            location_status = "unresolvedExternalSource"
        elif source_kind == "synthesizedSource":
            location_status = "synthesizedSource"
        else:
            location_status = "unsupportedPluginSource"
        source_object_evidence.append({
            **source,
            "objectId": object_id,
            "objectType": object_type,
            "rootActionId": root_action_id,
            "relationTypes": list(relations),
            "serializedPathIds": list(serialized_path_ids),
            "serializedPathTypeLabels": [
                HIRC_OBJECT_TYPE_LABELS.get(value, f"type{value}")
                for value in serialized_path_types
            ],
            "decodedMediaMatch": decoded_match,
            "mediaLocationStatus": location_status,
            "playbackBoundary": (
                "sourceRecordProvesAuthoredWwiseSourceNotRuntimeInstantiationOrAudibility"
            ),
        })

    while queue:
        (
            object_id,
            root_action_id,
            path_ids,
            path_types,
            path_relations,
            event_action_ordinal,
            dispatch_event_id,
        ) = queue.popleft()
        visit_key = (object_id, root_action_id, dispatch_event_id, event_action_ordinal)
        if visit_key in visited_paths:
            continue
        visited_paths.add(visit_key)
        visited.add(object_id)
        obj = objects.get(object_id)
        if not obj:
            unresolved_nodes.append({
                "objectId": object_id,
                "rootActionId": root_action_id,
                "reason": "missingSameBankObject",
            })
            continue
        object_type = int(obj.get("type") or 0)
        data = obj.get("data") or b""
        current_path_ids = (*path_ids, object_id)
        current_path_types = (*path_types, object_type)

        node_processing = hirc_v150_node_processing(object_type, data)
        if node_processing is not None:
            processing_row = node_processing_by_object_id.setdefault(object_id, {
                **node_processing,
                "objectId": object_id,
                "objectType": object_type,
                "objectTypeLabel": HIRC_OBJECT_TYPE_LABELS.get(
                    object_type, f"type{object_type}"
                ),
                "rootActionIds": set(),
            })
            processing_row["rootActionIds"].add(root_action_id)

        if object_type in HIRC_MUSIC_NODE_TYPES and bank_version != 150:
            unresolved_nodes.append({
                "objectId": object_id,
                "objectType": object_type,
                "rootActionId": root_action_id,
                "reason": "unsupportedMusicBankVersion",
                "bankVersion": bank_version,
            })
            continue

        if object_type == 4:
            for ordinal, action_id in enumerate(hirc_event_action_ids(data)):
                queue.append((
                    action_id,
                    root_action_id,
                    current_path_ids,
                    current_path_types,
                    path_relations,
                    ordinal,
                    object_id,
                ))
            continue

        if object_type == 3:
            action_type = hirc_action_type(data)
            operation = (action_type & 0xFF00) if action_type is not None else None
            target_id = hirc_action_target_id(data)
            target_type = int((objects.get(target_id) or {}).get("type") or 0) if target_id is not None else 0
            traversed = operation in HIRC_PLAYBACK_ACTION_OPERATIONS and target_id is not None
            action_row = {
                "actionId": object_id,
                "rootActionId": root_action_id,
                "dispatchEventId": dispatch_event_id,
                "eventActionOrdinal": event_action_ordinal,
                "isRootEventAction": len(path_ids) == 1 and dispatch_event_id == event_id,
                "actionType": action_type,
                "operation": HIRC_ACTION_OPERATION_LABELS.get(operation, f"operation0x{operation:04x}" if operation is not None else "truncated"),
                "scope": (action_type & 0x00FF) if action_type is not None else None,
                "targetId": target_id,
                "targetType": target_type or None,
                "targetTypeLabel": (
                    HIRC_OBJECT_TYPE_LABELS.get(target_type, f"type{target_type}")
                    if target_type else None
                ),
                "serializedPathIds": list(current_path_ids),
                "serializedPathTypeLabels": [
                    HIRC_OBJECT_TYPE_LABELS.get(value, f"type{value}")
                    for value in current_path_types
                ],
                "serializedPathRelations": list(path_relations),
                "traversed": traversed,
            }
            if operation in HIRC_PLAYBACK_ACTION_OPERATIONS:
                action_row.update(hirc_v150_playback_action(data, bank_version))
            else:
                action_row.update(hirc_v150_control_action(data, bank_version))
            action_evidence.append(action_row)
            if traversed:
                queue.append((
                    target_id,
                    root_action_id,
                    current_path_ids,
                    current_path_types,
                    path_relations,
                    event_action_ordinal,
                    dispatch_event_id,
                ))
            continue

        if object_type == 2:
            source = hirc_v150_sound_source(data)
            if source is None:
                unresolved_nodes.append({
                    "objectId": object_id,
                    "objectType": object_type,
                    "rootActionId": root_action_id,
                    "reason": "truncatedSoundSource",
                })
                continue
            relations = tuple(path_relations) or ("directSound",)
            record_source(
                source, object_id, object_type, root_action_id, relations,
                current_path_ids, current_path_types,
            )
            if source.get("sourceKind") == "codecMedia":
                record_media(
                    int(source["sourceId"]), object_id, object_type,
                    root_action_id, relations, source,
                )
            continue

        if object_type == 11:
            track = hirc_v150_music_track(data)
            if not track:
                unresolved_nodes.append({
                    "objectId": object_id,
                    "objectType": object_type,
                    "rootActionId": root_action_id,
                    "reason": "musicTrackPrefixUnresolved",
                })
                continue
            music_node_evidence.append({
                "objectId": object_id,
                "objectType": object_type,
                "rootActionId": root_action_id,
                "nodeKind": "musicTrack",
                "parentId": track["parentId"],
                "sourceCount": track["sourceCount"],
                "sources": track["sources"],
                "playlistItemCount": track["playlistItemCount"],
                "playlistItems": track["playlistItems"],
                "subtrackCount": track["subtrackCount"],
                "automationCount": track["automationCount"],
                "automationPointCount": track["automationPointCount"],
                "parserConfidence": "typedExactV150",
            })
            relations = (*path_relations, "musicTrackSource")
            for source in track["sources"]:
                record_source(
                    source, object_id, object_type, root_action_id, relations,
                    current_path_ids, current_path_types,
                )
                media_id = int(source.get("sourceId") or 0)
                if media_id and source.get("sourceKind") == "codecMedia":
                    record_media(
                        media_id, object_id, object_type, root_action_id,
                        relations, source,
                    )
            continue

        if object_type in HIRC_TYPED_CHILD_CONTAINER_TYPES:
            parsed = hirc_reciprocal_child_list(object_id, object_type, data, objects)
            structure = None
            parser_confidence = "reciprocalParentExact"
            layer_tail = None
            layer_candidate_without_parent = False
            if not parsed and object_type == 9:
                layer_candidate = hirc_v150_layer_child_candidate(
                    data,
                    objects,
                    bank_version=bank_version,
                )
                if layer_candidate:
                    child_ids, offset, layer_tail, parser_confidence = layer_candidate
                    parsed = (child_ids, offset)
                    layer_candidate_without_parent = (
                        parser_confidence == "typedExactV150CandidateWithoutParentProof"
                    )
            if not parsed and object_type in HIRC_MUSIC_PARENT_NODE_TYPES:
                empty_music = hirc_v150_empty_music_children(object_type, data)
                if empty_music:
                    child_ids, offset, structure = empty_music
                    parsed = (child_ids, offset)
                    parser_confidence = "typedTailExactEmpty"
            if not parsed:
                unresolved_nodes.append({
                    "objectId": object_id,
                    "objectType": object_type,
                    "rootActionId": root_action_id,
                    "reason": "childrenListUnresolved",
                })
                continue
            child_ids, offset = parsed
            container_row = {
                "objectId": object_id,
                "objectType": object_type,
                "rootActionId": root_action_id,
                "childrenOffset": offset,
                "childCount": len(child_ids),
                "parserConfidence": parser_confidence,
            }
            if object_type == 5:
                container_row.update(hirc_v150_random_sequence_properties(
                    data,
                    offset,
                    child_ids,
                    bank_version=bank_version,
                ))
                relation = "sequenceItem" if container_row.get("mode") == 1 else "randomAlternative"
            elif object_type == 6:
                container_row["switchMappingEvidence"] = hirc_v150_switch_mapping(
                    data,
                    offset,
                    len(child_ids),
                    bank_version=bank_version,
                )
                relation = "switchCandidate"
            elif object_type == 9:
                relation = "layerChild"
                if layer_tail is None:
                    layer_tail = hirc_v150_layer_tail(
                        data,
                        offset + 4 + len(child_ids) * 4,
                        child_ids,
                        bank_version=bank_version,
                    )
                container_row["layerTailEvidence"] = layer_tail
                if layer_tail.get("layerTailParserStatus") != "typedExactV150LayerTail":
                    unresolved_nodes.append({
                        "objectId": object_id,
                        "objectType": object_type,
                        "rootActionId": root_action_id,
                        "reason": "layerTailUnresolved",
                        "detail": layer_tail.get("layerTailFailureReason")
                        or layer_tail.get("layerTailParserStatus"),
                    })
                elif layer_candidate_without_parent:
                    unresolved_nodes.append({
                        "objectId": object_id,
                        "objectType": object_type,
                        "rootActionId": root_action_id,
                        "reason": "layerChildrenCandidateWithoutParentProof",
                        "childrenOffset": offset,
                        "childCount": len(child_ids),
                    })
            elif object_type == 10:
                relation = "musicTrack"
                structure = structure or hirc_v150_music_structure(
                    object_type, data, offset, len(child_ids), child_ids
                )
                node_kind = "musicSegment"
            elif object_type == 12:
                relation = "musicSwitchCandidate"
                structure = structure or hirc_v150_music_structure(
                    object_type, data, offset, len(child_ids), child_ids
                )
                if structure:
                    structure = refine_hirc_v150_music_switch_selector_ownership(
                        structure, object_id, objects
                    )
                node_kind = "musicSwitchContainer"
            elif object_type == 13:
                relation = "musicPlaylistCandidate"
                structure = structure or hirc_v150_music_structure(
                    object_type, data, offset, len(child_ids), child_ids
                )
                node_kind = "musicRandomSequenceContainer"
            else:
                relation = "groupChild"
            container_row["edgeKind"] = relation
            container_evidence.append(container_row)
            if object_type in HIRC_MUSIC_PARENT_NODE_TYPES:
                music_row = {
                    **container_row,
                    "nodeKind": node_kind,
                    "childIds": child_ids,
                }
                if structure:
                    music_row.update(structure)
                    selector_status = (structure.get("selectorValidation") or {}).get("status")
                    exact_selector_statuses = {
                        None,
                        "reciprocalChildrenCovered",
                        "decisionTreeSubsetOfReciprocalChildren",
                        "playlistSubsetOfReciprocalChildren",
                        "decisionTreeIndirectAndUnboundLeavesResolved",
                    }
                    music_row["structureStatus"] = (
                        "typedExactV150SelectorSubset"
                        if selector_status in {
                            "decisionTreeSubsetOfReciprocalChildren",
                            "playlistSubsetOfReciprocalChildren",
                            "decisionTreeIndirectAndUnboundLeavesResolved",
                        }
                        else "typedExactV150"
                        if selector_status in exact_selector_statuses
                        else "typedExactV150SelectorBoundaryUnresolved"
                    )
                    if selector_status not in exact_selector_statuses:
                        unresolved_nodes.append({
                            "objectId": object_id,
                            "objectType": object_type,
                            "rootActionId": root_action_id,
                            "reason": "musicSelectorReciprocalMismatch",
                            "selectorValidation": structure["selectorValidation"],
                        })
                else:
                    music_row["structureStatus"] = "structureTailUnresolved"
                    unresolved_nodes.append({
                        "objectId": object_id,
                        "objectType": object_type,
                        "rootActionId": root_action_id,
                        "reason": "musicStructureTailUnresolved",
                    })
                music_node_evidence.append(music_row)
                if not structure:
                    # Reciprocal parent proof identifies a likely Children block,
                    # but music edges are traversed only when the serialized tail
                    # starting at that exact boundary also parses to object end.
                    continue
            child_relations = (*path_relations, relation)
            for child_id in child_ids:
                queue.append((
                    child_id,
                    root_action_id,
                    current_path_ids,
                    current_path_types,
                    child_relations,
                    event_action_ordinal,
                    dispatch_event_id,
                ))
            continue

        unresolved_nodes.append({
            "objectId": object_id,
            "objectType": object_type,
            "rootActionId": root_action_id,
            "reason": "unsupportedTypedNode",
        })

    media_evidence = [
        {
            "mediaId": media_id,
            "decoded": bool(row["decoded"]),
            **({
                "soundObjectCount": len(row["soundObjectIds"]),
                "soundObjectIds": sorted(row["soundObjectIds"]),
            } if row["soundObjectIds"] else {}),
            **({
                "musicTrackObjectCount": len(row["musicTrackObjectIds"]),
                "musicTrackObjectIds": sorted(row["musicTrackObjectIds"]),
            } if row["musicTrackObjectIds"] else {}),
            "rootActionIds": sorted(row["rootActionIds"]),
            "relationTypes": sorted(row["relationTypes"]),
            "selectionPaths": [list(path) for path in sorted(row["selectionPaths"])],
            "sourceKinds": sorted(row["sourceKinds"]),
            "pluginIds": sorted(row["pluginIds"]),
            "pluginNames": [
                HIRC_SOURCE_PLUGIN_LABELS.get(plugin_id, f"plugin0x{plugin_id:08x}")
                for plugin_id in sorted(row["pluginIds"])
            ],
            "streamTypes": [
                {
                    "value": stream_type,
                    "label": HIRC_STREAM_TYPE_LABELS.get(
                        stream_type, f"streamType{stream_type}"
                    ),
                }
                for stream_type in sorted(row["streamTypes"])
            ],
            "sourceBits": sorted(row["sourceBits"]),
        }
        for media_id, row in sorted(media_evidence_by_id.items())
    ]
    source_kind_counts = Counter(
        str(row.get("sourceKind") or "unknown") for row in source_object_evidence
    )
    plugin_counts = Counter(
        f"0x{int(row.get('pluginId') or 0):08x}" for row in source_object_evidence
    )
    stream_type_counts = Counter(
        str(row.get("streamTypeLabel") or "unknown") for row in source_object_evidence
    )
    source_flag_counts = Counter()
    for row in source_object_evidence:
        for flag, enabled in (row.get("sourceFlags") or {}).items():
            if flag != "unknownBits" and enabled:
                source_flag_counts[flag] += 1
        if int((row.get("sourceFlags") or {}).get("unknownBits") or 0):
            source_flag_counts["unknownBitsNonzero"] += 1
    source_object_summary = {
        "sourceReferenceCount": len(source_object_evidence),
        "uniqueSourceObjectCount": len({
            (int(row.get("objectType") or 0), int(row.get("objectId") or 0))
            for row in source_object_evidence
        }),
        "sourceKindCounts": dict(sorted(source_kind_counts.items())),
        "pluginCounts": dict(sorted(plugin_counts.items())),
        "streamTypeCounts": dict(sorted(stream_type_counts.items())),
        "sourceFlagCounts": dict(sorted(source_flag_counts.items())),
        "decodedCodecSourceCount": sum(
            row.get("sourceKind") == "codecMedia" and row.get("decodedMediaMatch")
            for row in source_object_evidence
        ),
        "unresolvedCodecSourceCount": sum(
            row.get("sourceKind") == "codecMedia" and not row.get("decodedMediaMatch")
            for row in source_object_evidence
        ),
        "runtimeSelection": "sourceInstantiationAndAudibilityNotObserved",
    }
    non_media_source_evidence = [
        row for row in source_object_evidence
        if row.get("sourceKind") != "codecMedia"
    ]
    action_dispatch_evidence = summarize_hirc_action_dispatch(
        event_id, root_action_ids, action_evidence
    )
    for processing_row in node_processing_by_object_id.values():
        processing_row["rootActionIds"] = sorted(processing_row["rootActionIds"])
    post_process_summary = summarize_hirc_node_processing(
        node_processing_by_object_id
    )
    return {
        "actionIds": root_action_ids,
        "rootPlayActionCount": action_dispatch_evidence["playbackActionCount"],
        "rootStopActionCount": sum(
            row.get("isRootEventAction") and row.get("operation") == "stop"
            for row in action_evidence
        ),
        "visitedObjectIds": sorted(visited),
        "sourceMediaIds": source_media_ids,
        "mediaIds": resolved_media_ids,
        "mediaEvidence": media_evidence,
        "actionEvidence": action_evidence,
        "actionDispatchEvidence": action_dispatch_evidence,
        "containerEvidence": container_evidence,
        "musicNodeEvidence": music_node_evidence,
        "postProcessSummary": post_process_summary,
        "sourceObjectSummary": source_object_summary,
        "nonMediaSourceEvidence": non_media_source_evidence,
        "unresolvedNodes": unresolved_nodes,
        "traversalStatus": "partial" if unresolved_nodes else "complete",
    }

def summarize_hirc_object_types(
    objects: dict[int, dict[str, Any]],
    visited: set[int],
) -> tuple[dict[str, int], dict[str, str], list[int]]:
    """Return raw HIRC family counts plus labels and selection containers.

    Raw type numbers remain authoritative.  Names are presentation labels for
    the families observed in Endfield's current banks; their presence proves a
    possible runtime selector, not which branch was selected.
    """

    counts = Counter(
        int(objects[object_id].get("type") or 0)
        for object_id in visited
        if object_id in objects
    )
    return (
        {str(object_type): count for object_type, count in sorted(counts.items())},
        {
            str(object_type): HIRC_OBJECT_TYPE_LABELS.get(object_type, f"type{object_type}")
            for object_type in sorted(counts)
        },
        sorted(object_type for object_type in counts if object_type in SELECTION_HIRC_TYPES),
    )

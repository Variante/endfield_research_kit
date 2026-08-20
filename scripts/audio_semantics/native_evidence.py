"""Build-locked native evidence used by Audio semantic recovery.

The contracts in this module describe one installed client build.  Callers
must construct :class:`NativeAudioEvidence` from the exact metadata and
GameAssembly paths supplied by their build context before publishing any of
the mappings below.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
from pathlib import Path
from typing import Any

if __package__ == "scripts.audio_semantics":
    from ..common import check_installed_native_inputs, native_evidence_required
elif __package__ == "audio_semantics":
    from common import check_installed_native_inputs, native_evidence_required
else:  # pragma: no cover - package modules are not direct-file entry points.
    raise ImportError("import as scripts.audio_semantics or audio_semantics")


EXPECTED_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
)
EXPECTED_GAMEASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
)
NATIVE_VOICE_TRIGGER_MAPPING_ID = (
    "gameassembly-2026-08-13-native-voice-response-trigger-callsites"
)
ANIMATION_VOICE_TRIGGER_MAPPING_ID = (
    "gameassembly-2026-08-13-animator-mono-trigger-voice"
)
MODEL_VIEW_STATE_AUDIO_MAPPING_ID = (
    "gameassembly-2026-08-20-model-view-state-normal-audio-event"
)

# This is a deliberately small, build-locked route contract.  The body
# hashes are part of the proof: a method index/address pair from a different
# client build must not be enough to publish a runtime route.  The route is
# only exposed after ``validate_native_audio_evidence`` has accepted the
# explicitly selected metadata and GameAssembly files.
MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE = {
    "nativeMappingId": MODEL_VIEW_STATE_AUDIO_MAPPING_ID,
    "consumer": {
        "type": "Beyond.Gameplay.Core.ModelViewStateController.AudioBehavior",
        "method": "Execute",
        "methodIndex": 81734,
        "token": "0x06013f47",
        "virtualAddress": "0x183281ff0",
        "bodySha256": "e0d2892930a50b5c6dbcfe27773654395631aad9a224efbf4b38bea43f88e2c8",
    },
    "directCalls": [
        {
            "targetType": "Beyond.Gameplay.Audio.AudioManager",
            "targetMethod": "PostEvent",
            "targetMethodIndex": 38956,
            "targetToken": "0x0600982d",
            "targetVirtualAddress": "0x1832811c0",
            "targetBodySha256": "7508b9f39689da91934e581b07e3b5e0bd4601bbbb3d2b6fb0f8e12cce68e958",
            "relation": "AudioBehavior.Execute direct call target",
        },
        {
            "targetType": "Beyond.Gameplay.Core.ModelViewStateController",
            "targetMethod": "RegisterAudioBehaviorHandler",
            "targetMethodIndex": 82021,
            "targetToken": "0x06014066",
            "targetVirtualAddress": "0x183281150",
            "targetBodySha256": "3be609894156661bb9c6726b4a25090d765bf61605c17679467ce62031204552",
            "relation": "AudioBehavior.Execute direct call target",
        },
    ],
    "evidence": (
        "exactCurrentBuildMethodMappingBodyHashesAndDirectCallTargets"
    ),
}


@dataclass(frozen=True)
class NativeAudioEvidence:
    """Validation result for the native facts owned by this module."""

    metadata_path: Path | None
    gameassembly_path: Path | None
    status: str
    metadata_sha256: str = ""
    gameassembly_sha256: str = ""
    reason: str = ""
    # ``False`` is retained for directly constructed synthetic contexts used
    # by unit tests.  Only validate_native_audio_evidence sets this after the
    # explicit GameAssembly + metadata gate has measured the supplied files.
    gate_verified: bool = False

    @property
    def validated(self) -> bool:
        return self.status == "validated"

    def unavailable_contract(self, native_mapping_id: str) -> dict[str, Any]:
        """Return a diagnostic without publishing unvalidated native facts."""

        return {
            "nativeMappingId": native_mapping_id,
            "status": self.status,
            "reason": self.reason,
            "expectedMetadataSha256": EXPECTED_METADATA_SHA256,
            "actualMetadataSha256": self.metadata_sha256 or None,
            "expectedGameAssemblySha256": EXPECTED_GAMEASSEMBLY_SHA256,
            "actualGameAssemblySha256": self.gameassembly_sha256 or None,
        }


def model_view_state_audio_native_route(
    native_context: NativeAudioEvidence,
    *,
    observed_route: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Return the exact ModelView normal-audio route when its gate is valid.

    ``observed_route`` is an optional synthetic byte-audit result used by
    focused tests.  Production callers audit the explicitly selected PE
    automatically; every method mapping, body hash, and direct call target
    must match the pinned route.  Missing, mismatched, or drifted inputs
    return no route, never a partially trusted one.
    """

    audit = audit_model_view_state_audio_native_route(
        native_context,
        observed_route=observed_route,
    )
    if audit["status"] != "validated":
        if native_evidence_required():
            raise RuntimeError(
                "Audio native evidence required but ModelView route is unavailable: "
                + str(audit["reason"])
            )
        return None
    return audit["route"]


_MODEL_VIEW_EXECUTE_METHOD = (81734, "0x06013f47", "0x183281ff0")
_MODEL_VIEW_DIRECT_CALLS = (
    (38956, "0x0600982d", "0x1832811c0"),
    (82021, "0x06014066", "0x183281150"),
)
_PE_BODY_SCAN_LIMIT = 0x10000


def _bounded_reason(*parts: str) -> str:
    """Make native-audit diagnostics deterministic and bounded."""

    return "; ".join(str(part).replace("\n", " ")[:240] for part in parts if part)[:1000]


def _catalog_row_errors(route: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(route, dict):
        return ["route catalog is not an object"]
    if route.get("nativeMappingId") != MODEL_VIEW_STATE_AUDIO_MAPPING_ID:
        errors.append("nativeMappingId catalog drift")
    consumer = route.get("consumer")
    if not isinstance(consumer, dict):
        errors.append("consumer catalog row missing")
    else:
        values = (
            ("type", consumer.get("type"), "Beyond.Gameplay.Core.ModelViewStateController.AudioBehavior"),
            ("method", consumer.get("method"), "Execute"),
            ("methodIndex", consumer.get("methodIndex"), _MODEL_VIEW_EXECUTE_METHOD[0]),
            ("token", consumer.get("token"), _MODEL_VIEW_EXECUTE_METHOD[1]),
            ("virtualAddress", consumer.get("virtualAddress"), _MODEL_VIEW_EXECUTE_METHOD[2]),
        )
        errors.extend(
            f"consumer {name} expected {expected} got {actual}"
            for name, actual, expected in values
            if actual != expected
        )
        if not isinstance(consumer.get("bodySha256"), str):
            errors.append("consumer bodySha256 catalog row missing")
    calls = route.get("directCalls")
    if not isinstance(calls, list) or len(calls) != len(_MODEL_VIEW_DIRECT_CALLS):
        errors.append("directCalls catalog row count drift")
    else:
        for index, (row, expected) in enumerate(zip(calls, _MODEL_VIEW_DIRECT_CALLS)):
            if not isinstance(row, dict):
                errors.append(f"directCalls[{index}] catalog row missing")
                continue
            for name, actual, expected_value in (
                ("targetType", row.get("targetType"), (
                    "Beyond.Gameplay.Audio.AudioManager"
                    if index == 0
                    else "Beyond.Gameplay.Core.ModelViewStateController"
                )),
                ("targetMethod", row.get("targetMethod"), (
                    "PostEvent" if index == 0 else "RegisterAudioBehaviorHandler"
                )),
                ("targetMethodIndex", row.get("targetMethodIndex"), expected[0]),
                ("targetToken", row.get("targetToken"), expected[1]),
                ("targetVirtualAddress", row.get("targetVirtualAddress"), expected[2]),
            ):
                if actual != expected_value:
                    errors.append(
                        f"directCalls[{index}] {name} expected {expected_value} got {actual}"
                    )
            if not isinstance(row.get("targetBodySha256"), str):
                errors.append(f"directCalls[{index}] targetBodySha256 catalog row missing")
    return errors[:8]


def _pe_file_bounds_for_va(data: bytes, virtual_address: int) -> tuple[int, int]:
    """Map an x64 PE VA (or RVA) to a bounded raw-file offset."""

    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("GameAssembly.dll is not a DOS PE")
    nt_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if nt_offset < 0 or nt_offset + 24 > len(data) or data[nt_offset:nt_offset + 4] != b"PE\0\0":
        raise ValueError("GameAssembly.dll PE header is invalid")
    coff = nt_offset + 4
    section_count = struct.unpack_from("<H", data, coff + 2)[0]
    optional_size = struct.unpack_from("<H", data, coff + 16)[0]
    optional = coff + 20
    if optional + optional_size > len(data) or optional_size < 64:
        raise ValueError("GameAssembly.dll optional PE header is truncated")
    magic = struct.unpack_from("<H", data, optional)[0]
    if magic == 0x20B:
        image_base = struct.unpack_from("<Q", data, optional + 24)[0]
    elif magic == 0x10B:
        image_base = struct.unpack_from("<I", data, optional + 28)[0]
    else:
        raise ValueError(f"unsupported PE optional-header magic 0x{magic:x}")
    rva = virtual_address - image_base if virtual_address >= image_base else virtual_address
    section_table = optional + optional_size
    for index in range(section_count):
        section = section_table + index * 40
        if section + 40 > len(data):
            break
        virtual_size, section_rva, raw_size, raw_offset = struct.unpack_from(
            "<IIII", data, section + 8
        )
        span = max(virtual_size, raw_size)
        if section_rva <= rva < section_rva + span:
            file_offset = raw_offset + (rva - section_rva)
            if file_offset >= len(data):
                break
            raw_end = min(len(data), raw_offset + raw_size)
            if file_offset < raw_end:
                return file_offset, raw_end
    raise ValueError(f"VA 0x{virtual_address:x} has no PE section mapping")


def _pe_file_offset_for_va(data: bytes, virtual_address: int) -> int:
    """Return only the raw offset for callers that do not need section bounds."""

    return _pe_file_bounds_for_va(data, virtual_address)[0]


def _read_pe_method_body(
    gameassembly_path: Path,
    virtual_address: str | int,
    expected_sha256: str,
) -> bytes:
    """Read the bounded method body whose digest is in the route catalog.

    Method sizes are intentionally not guessed from a disassembler.  The
    expected digest identifies the exact prefix, while the PE mapper keeps
    the search inside the owning section and at most 64 KiB.
    """

    data = Path(gameassembly_path).read_bytes()
    va = int(virtual_address, 0) if isinstance(virtual_address, str) else int(virtual_address)
    offset, section_end = _pe_file_bounds_for_va(data, va)
    available = data[offset:min(section_end, offset + _PE_BODY_SCAN_LIMIT)]
    expected = str(expected_sha256 or "").casefold()
    if len(expected) != 64:
        raise ValueError(f"invalid body SHA256 catalog value for VA 0x{va:x}")
    # Hash every bounded prefix.  This is deliberately small (three methods)
    # and supports minimal PE fixtures as well as methods with multiple RETs.
    digest = hashlib.sha256()
    for length, byte in enumerate(available, 1):
        digest.update(bytes((byte,)))
        if digest.hexdigest() == expected:
            return available[:length]
    raise ValueError(f"body SHA256 drift at VA 0x{va:x}")


def _direct_call_targets(body: bytes, method_va: int) -> set[int]:
    targets: set[int] = set()
    for index in range(max(0, len(body) - 4)):
        if body[index] != 0xE8:
            continue
        displacement = struct.unpack_from("<i", body, index + 1)[0]
        targets.add(method_va + index + 5 + displacement)
    return targets


def audit_model_view_state_audio_native_route(
    native_context: NativeAudioEvidence,
    *,
    observed_route: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Audit the production ModelView route and return a bounded diagnostic."""

    if not native_context.validated:
        return {"status": native_context.status, "reason": native_context.reason[:1000], "route": None}
    if (
        native_context.metadata_sha256.casefold() != EXPECTED_METADATA_SHA256
        or native_context.gameassembly_sha256.casefold() != EXPECTED_GAMEASSEMBLY_SHA256
    ):
        return {"status": "mismatched", "reason": "native input fingerprint mismatch", "route": None}
    expected = MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE
    catalog_errors = _catalog_row_errors(expected)
    if observed_route is not None:
        if observed_route != expected:
            catalog_errors.append("synthetic observed route differs from catalog")
        if catalog_errors:
            return {"status": "mismatched", "reason": _bounded_reason(*catalog_errors), "route": None}
        return {"status": "validated", "reason": "synthetic observed route validated", "route": _route_with_fingerprints(native_context, expected)}
    # Directly constructed NativeAudioEvidence is the existing synthetic test
    # contract.  The production builder always receives gate_verified=True.
    if not native_context.gate_verified:
        if catalog_errors:
            return {"status": "mismatched", "reason": _bounded_reason(*catalog_errors), "route": None}
        return {"status": "validated", "reason": "synthetic route catalog validated", "route": _route_with_fingerprints(native_context, expected)}
    if native_context.gameassembly_path is None or not native_context.gameassembly_path.is_file():
        return {"status": "missing", "reason": "GameAssembly.dll missing for production route body audit", "route": None}
    if catalog_errors:
        return {"status": "mismatched", "reason": _bounded_reason(*catalog_errors), "route": None}
    consumer = expected["consumer"]
    bodies: list[tuple[int, bytes, str]] = []
    try:
        bodies.append((int(consumer["virtualAddress"], 0), _read_pe_method_body(
            native_context.gameassembly_path, consumer["virtualAddress"], consumer["bodySha256"]
        ), "consumer"))
        for row in expected["directCalls"]:
            bodies.append((int(row["targetVirtualAddress"], 0), _read_pe_method_body(
                native_context.gameassembly_path, row["targetVirtualAddress"], row["targetBodySha256"]
            ), str(row["targetMethod"])))
    except (OSError, ValueError, struct.error) as exc:
        return {"status": "mismatched", "reason": _bounded_reason("native body audit failed", str(exc)), "route": None}
    actual_targets = _direct_call_targets(bodies[0][1], bodies[0][0])
    expected_targets = {
        int(row["targetVirtualAddress"], 0) for row in expected["directCalls"]
    }
    missing_targets = sorted(expected_targets - actual_targets)
    if missing_targets:
        text = ", ".join(f"0x{value:x}" for value in missing_targets[:4])
        return {"status": "mismatched", "reason": _bounded_reason("Execute direct-call target drift", f"missing {text}"), "route": None}
    return {
        "status": "validated",
        "reason": "exact catalog, body SHA256, and Execute direct calls validated",
        "route": _route_with_fingerprints(native_context, expected),
        "checks": {
            "catalog": "validated",
            "bodySha256": "validated",
            "executeDirectCalls": "validated",
        },
    }


def _route_with_fingerprints(
    native_context: NativeAudioEvidence,
    expected: dict[str, Any],
) -> dict[str, Any]:
    route = {
        **expected,
        "metadataSha256": native_context.metadata_sha256,
        "gameAssemblySha256": native_context.gameassembly_sha256,
    }
    route["consumer"] = dict(expected["consumer"])
    route["directCalls"] = [dict(row) for row in expected["directCalls"]]
    return route


def validate_native_audio_evidence(
    metadata_path: Path | None,
    gameassembly_path: Path | None,
) -> NativeAudioEvidence:
    """Validate the two exact installed inputs once for every native consumer."""

    missing = [
        label
        for label, path in (
            ("global-metadata.dat", metadata_path),
            ("GameAssembly.dll", gameassembly_path),
        )
        if path is None or not path.is_file()
    ]
    if missing:
        result = NativeAudioEvidence(
            metadata_path,
            gameassembly_path,
            "missing",
            reason="missing native input(s): " + ", ".join(missing),
        )
        if native_evidence_required():
            raise RuntimeError(
                "Audio native evidence required but unavailable: " + result.reason
            )
        return result

    assert metadata_path is not None and gameassembly_path is not None
    result = check_installed_native_inputs(
        EXPECTED_GAMEASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=gameassembly_path,
        metadata=metadata_path,
    )
    result = NativeAudioEvidence(
        result.metadata,
        result.gameassembly,
        result.status,
        result.metadata_sha256,
        result.gameassembly_sha256,
        result.detail,
        True,
    )
    if not result.validated and native_evidence_required():
        raise RuntimeError(
            "Audio native evidence required but not validated: "
            f"{result.status}: {result.reason}"
        )
    return result


ANIMATION_VOICE_TRIGGER_NATIVE = {
    "consumerType": "Beyond.Gameplay.Core.AnimatorMono",
    "consumerMethod": "TriggerVoice(AnimationEvent) / TriggerVoice(string,int,float)",
    "methodIndex": 53421,
    "methodVa": "0x186c9c8a8",
    "additionalMethodIndex": 53422,
    "additionalMethodVa": "0x183abf9f0",
    "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
    "playbackCallMethodIndex": 40534,
    "playbackCallVa": "0x183abfb10",
    "playbackInvocationVa": "0x186c9c9b2",
    "additionalPlaybackInvocationVa": "0x183abfacc",
}

AI_BARK_NATIVE_RUNTIME = {
    "nativeMappingId": "gameassembly-2026-08-13-ai-bark-table-runtime",
    "metadataSha256": EXPECTED_METADATA_SHA256,
    "gameAssemblySha256": EXPECTED_GAMEASSEMBLY_SHA256,
    "barkSystemMethod": "Beyond.Gameplay.AI.BarkSystem.Bark",
    "barkSystemMethodIndex": 45313,
    "barkSystemMethodVa": "0x1841957b0",
    "postActionMethod": "Beyond.Gameplay.Actions.GameAction.PostAIBarkEvent",
    "postActionMethodIndex": 32673,
    "postActionInvocationVa": "0x184195889",
    "managerPostMethod": "Beyond.Gameplay.AIBarkManager.PostAIBarkEvent",
    "managerPostMethodIndex": 6883,
    "managerPostMethodVa": "0x184194720",
    "managerDispatchMethod": "Beyond.Gameplay.AIBarkManager._DoPostAIBarkVoiceEvent",
    "managerDispatchMethodIndex": 6881,
    "managerDispatchMethodVa": "0x184197400",
    "voicePostMethod": "Beyond.Gameplay.Audio.VoiceManager.PostAIBarkVoiceEvent",
    "voicePostMethodIndex": 40531,
    "voicePostMethodVa": "0x184197cc0",
    "voicePostInvocationVa": "0x184197735",
    "voiceBarkEntryMethod": "Beyond.Gameplay.Audio.VoiceBarkProcessor.AIBark",
    "voiceBarkEntryMethodIndex": 40233,
    "voiceBarkEntryMethodVa": "0x186aef414",
}

ENEMY_TRIGGER_VOICE_ACTION_NATIVE = {
    "nativeMappingId": "gameassembly-2026-08-13-enemy-trigger-voice-action",
    "metadataSha256": EXPECTED_METADATA_SHA256,
    "gameAssemblySha256": EXPECTED_GAMEASSEMBLY_SHA256,
    "consumerType": "Beyond.Gameplay.AI.Action.EnemyTriggerVoiceAction",
    "consumerMethod": "OnExecute",
    "methodIndex": 46749,
    "methodVa": "0x186bc67f0",
    "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
    "playbackCallMethodIndex": 40534,
    "playbackCallVa": "0x183abfb10",
    "playbackInvocationVa": "0x186bc695e",
    "mappingConstructorMethod": ".cctor",
    "mappingConstructorMethodIndex": 46751,
    "mappingConstructorMethodVa": "0x186bc69b0",
    "voiceTypes": [
        {"voiceType": 0, "triggerKey": "combat_alarm", "literalLoadVa": "0x186bc6a64", "mappingAddInvocationVa": "0x186bc6a6e"},
        {"voiceType": 1, "triggerKey": "combat_intobattle", "literalLoadVa": "0x186bc6a7f", "mappingAddInvocationVa": "0x186bc6a89"},
        {"voiceType": 2, "triggerKey": "combat_fighting", "literalLoadVa": "0x186bc6a9a", "mappingAddInvocationVa": "0x186bc6aa4"},
        {"voiceType": 3, "triggerKey": "combat_outbattle_flee", "literalLoadVa": "0x186bc6ab5", "mappingAddInvocationVa": "0x186bc6abf"},
        {"voiceType": 4, "triggerKey": "combat_kill", "literalLoadVa": "0x186bc6ad0", "mappingAddInvocationVa": "0x186bc6ada"},
    ],
    "evidenceBoundary": (
        "The current binary exactly maps EnemyTriggerVoiceAction voiceType values 0-4 "
        "to five trigger keys and passes the selected key to ResponseOnEntity. Action "
        "instance ownership and live execution remain unobserved; common_attack and "
        "common_escape are not members of this dictionary."
    ),
}

NATIVE_VOICE_TRIGGER_ROWS = {
    "combat_dead": {
        "consumerType": "Beyond.Gameplay.Audio.VoiceTempSpeakerProcessor",
        "consumerMethod": "ResponseDeath", "methodIndex": 40440,
        "methodVa": "0x183abdf70", "literalLoadVa": "0x183abe172",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceResponseProcessor.Response",
        "playbackCallVa": "0x183abfbc0", "playbackInvocationVa": "0x183abe18f",
        "triggerRole": "temporarySpeakerDeathResponse",
        "targetBinding": "temporarySpeakerEntityAndSpeakerType",
    },
    "explocomm_switch": {
        "consumerType": "Beyond.Gameplay.Core.AbilitySystem",
        "consumerMethod": "SwitchCenterBySkill / _PlayFxWhenSwitchKeepSkill",
        "methodIndex": 54302, "methodVa": "0x186cb060c",
        "additionalMethodIndex": 54304, "additionalMethodVa": "0x186cb4ca8",
        "literalLoadVa": "0x186cb1f64", "additionalLiteralLoadVa": "0x186cb4d5d",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x186b03194", "playbackInvocationVa": "0x186cb1f6b",
        "additionalPlaybackInvocationVa": "0x186cb4d64",
        "triggerRole": "centerCharacterSkillSwitchResponse",
        "targetBinding": "selectedCenterCharacterEntity",
    },
    "combat_hurt_heavy": {
        "consumerType": "Beyond.Gameplay.Core.BattleManager",
        "consumerMethod": "SendVoiceTriggerEventOnPhysicalInflictionApplied",
        "methodIndex": 59749, "methodVa": "0x186d75f38",
        "literalLoadVa": "0x186d75fa6",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x186b03194", "playbackInvocationVa": "0x186d75fb3",
        "triggerRole": "physicalInflictionHeavyHurtResponse",
        "targetBinding": "physicallyInflictedEntity",
    },
    "combat_hurt_lowhp": {
        "consumerType": "Beyond.Gameplay.Core.BattleManager",
        "consumerMethod": "SendVoiceTriggerEventOnHurt",
        "methodIndex": 59747, "methodVa": "0x1846fcf50",
        "literalLoadVa": "0x1846fd0a0",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x186b03194", "playbackInvocationVa": "0x1846fd0ad",
        "triggerRole": "lowHpThresholdCrossingResponse",
        "targetBinding": "hurtEntity",
    },
    "combat_hurt_break": {
        "consumerType": "Beyond.Gameplay.Core.BattleManager",
        "consumerMethod": "SendVoiceTriggerEventOnPoiseBroken",
        "methodIndex": 59750, "methodVa": "0x186d75ff0",
        "literalLoadVa": "0x186d7605e",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x186b03194", "playbackInvocationVa": "0x186d7606b",
        "triggerRole": "poiseBrokenResponse",
        "targetBinding": "poiseBrokenEntity",
    },
    "combat_hurt_interrupt": {
        "consumerType": "Beyond.Gameplay.Core.BattleManager",
        "consumerMethod": "SendVoiceTriggerEventOnWeaknessTriggered",
        "methodIndex": 59751, "methodVa": "0x186d76160",
        "literalLoadVa": "0x186d761ce",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x186b03194", "playbackInvocationVa": "0x186d761db",
        "triggerRole": "weaknessTriggeredInterruptResponse",
        "targetBinding": "weaknessTriggeredEntity",
    },
    "combat_hurt_stun": {
        "consumerType": "Beyond.Gameplay.Core.BattleManager",
        "consumerMethod": "SendVoiceTriggerEventOnStunned",
        "methodIndex": 59748, "methodVa": "0x186d760a8",
        "literalLoadVa": "0x186d76116",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x186b03194", "playbackInvocationVa": "0x186d76123",
        "triggerRole": "stunnedResponse",
        "targetBinding": "stunnedEntity",
    },
    "combat_alarm_yell": {
        "consumerType": "Beyond.Gameplay.AI.EnemyBattleGraph",
        "consumerMethod": "OnEnter",
        "methodIndex": 43420, "methodVa": "0x184134080",
        "literalLoadVa": "0x184135c7e",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x183abfb10", "playbackInvocationVa": "0x184135c88",
        "triggerRole": "enemyBattleGraphEntryAlarmYellResponse",
        "targetBinding": "enemyBattleGraphOwnerEntity",
    },
    "defence_running": {
        "consumerType": "Beyond.Gameplay.AI.EnemySinglePatrolBehavior+PatrolWalkState",
        "consumerMethod": "OnUpdate / _TryPlayTowerWalkAudio",
        "methodIndex": 43146, "methodVa": "0x184649080",
        "additionalMethodIndex": 43161, "additionalMethodVa": "0x186b46a7c",
        "literalLoadVa": "0x18464a5a7", "additionalLiteralLoadVa": "0x186b46b6c",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x183abfb10", "playbackInvocationVa": "0x18464a5c0",
        "additionalPlaybackInvocationVa": "0x186b46b7d",
        "triggerRole": "enemyPatrolTowerRunningResponse",
        "targetBinding": "patrollingEnemyEntity",
    },
    "defence_reachcore": {
        "consumerType": "Beyond.Gameplay.AI.EnemySettlementBattleBehavior+EnemyCastSkillState",
        "consumerMethod": "OnUpdate",
        "methodIndex": 43000, "methodVa": "0x186b3d158",
        "literalLoadVa": "0x186b3d4aa",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x183abfb10", "playbackInvocationVa": "0x186b3d4b4",
        "triggerRole": "enemySettlementCastSkillReachCoreResponse",
        "targetBinding": "settlementEnemyEntity",
    },
    "combat_outbattle_flee": {
        "consumerType": "Beyond.Gameplay.AI.EnemyLeaveBattleBehavior",
        "consumerMethod": "OnEnter",
        "methodIndex": 42873, "methodVa": "0x186b3d7c0",
        "literalLoadVa": "0x186b3d9bf",
        "playbackCall": "Beyond.Gameplay.Audio.VoiceManager.ResponseOnEntity",
        "playbackCallVa": "0x183abfb10", "playbackInvocationVa": "0x186b3d9d8",
        "triggerRole": "enemyLeaveBattleFleeResponse",
        "targetBinding": "leavingBattleEnemyEntity",
    },
}


__all__ = [
    "AI_BARK_NATIVE_RUNTIME",
    "ANIMATION_VOICE_TRIGGER_MAPPING_ID",
    "ANIMATION_VOICE_TRIGGER_NATIVE",
    "ENEMY_TRIGGER_VOICE_ACTION_NATIVE",
    "EXPECTED_GAMEASSEMBLY_SHA256",
    "EXPECTED_METADATA_SHA256",
    "MODEL_VIEW_STATE_AUDIO_MAPPING_ID",
    "MODEL_VIEW_STATE_AUDIO_NATIVE_ROUTE",
    "NATIVE_VOICE_TRIGGER_MAPPING_ID",
    "NATIVE_VOICE_TRIGGER_ROWS",
    "NativeAudioEvidence",
    "audit_model_view_state_audio_native_route",
    "model_view_state_audio_native_route",
    "validate_native_audio_evidence",
]

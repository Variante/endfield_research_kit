"""Build-locked native evidence used by Audio semantic recovery.

The contracts in this module describe one installed client build.  Callers
must construct :class:`NativeAudioEvidence` from the exact metadata and
GameAssembly paths supplied by their build context before publishing any of
the mappings below.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ == "scripts.audio_semantics":
    from ..common import check_installed_native_inputs
elif __package__ == "audio_semantics":
    from common import check_installed_native_inputs
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


@dataclass(frozen=True)
class NativeAudioEvidence:
    """Validation result for the native facts owned by this module."""

    metadata_path: Path | None
    gameassembly_path: Path | None
    status: str
    metadata_sha256: str = ""
    gameassembly_sha256: str = ""
    reason: str = ""

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
        return NativeAudioEvidence(
            metadata_path,
            gameassembly_path,
            "missing",
            reason="missing native input(s): " + ", ".join(missing),
        )

    assert metadata_path is not None and gameassembly_path is not None
    result = check_installed_native_inputs(
        EXPECTED_GAMEASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=gameassembly_path,
        metadata=metadata_path,
    )
    return NativeAudioEvidence(
        result.metadata,
        result.gameassembly,
        result.status,
        result.metadata_sha256,
        result.gameassembly_sha256,
        result.detail,
    )


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
    "NATIVE_VOICE_TRIGGER_MAPPING_ID",
    "NATIVE_VOICE_TRIGGER_ROWS",
    "NativeAudioEvidence",
    "validate_native_audio_evidence",
]

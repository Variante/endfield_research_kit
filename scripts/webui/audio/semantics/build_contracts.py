"""Per-build declarations the Audio lane reads: tokens, addresses, state groups.

These are data, not algorithm. Every token and address here describes one
selected client build and is replaced wholesale by a client update, so keep
declarations in this module and logic in the collectors that read them. See
``memory/game_data/audio_overview.md`` for what they establish.
"""

from __future__ import annotations

from scripts.webui.audio.semantics import native_evidence


TIMELINE_AUDIO_RUNTIME_CONTRACTS = {
    "DialogAudioEventPlayableAsset": {
        "id": "timelineAudioId.dialogAudioEvent",
        "type": "Beyond.Gameplay.Core.DialogAudioEventPlayableAsset",
        "behaviourType": "Beyond.Gameplay.Core.DialogAudioEventPlayableBehaviour",
        "assetToken": "0x020027eb",
        "behaviourToken": "0x0200282d",
        "requestMethods": [
            {"name": "CreatePlayable", "token": "0x0600f08d"},
            {"name": "ProcessFrame", "token": "0x0600f20e"},
        ],
        "stopMethods": [
            {"name": "OnClipDisable", "token": "0x0600f20d"},
            {"name": "_StopPlaying", "token": "0x0600f20f"},
        ],
        "serializedControls": ["audioEvent", "stopOnDisable"],
        "nativeEvidence": {
            "createPlayableVa": "0x186dcb008",
            "processFrameVa": "0x186dd6d98",
            "stopPlayingVa": "0x186dd7028",
            "processFrameAudioObjectResolver": "Beyond.Audio.AudioPlayableUtil.GetBindObjectAudioObjectId",
            "onClipDisableCallsStopPlaying": True,
        },
        "evidenceBoundary": "currentIl2CppMetadataAndMappedNativePlayableBodies; runtimeDirectorEvaluationUnobserved",
    },
    "AudioDlgEventPlayable": {
        "id": "timelineStringEventKey.audioDlg",
        "type": "Beyond.Audio.AudioDlgEventPlayable",
        "behaviourType": "Beyond.Audio.AudioDlgEventPlayableBehaviour",
        "assetToken": "0x02000102",
        "behaviourToken": "0x02000101",
        "requestMethods": [
            {"name": "OnManualFixBehaviourPlay", "token": "0x06000612"},
            {"name": "ShouldPlay", "token": "0x06000617"},
            {"name": "_DoPlayEvent", "token": "0x06000619"},
        ],
        "stopMethods": [
            {"name": "OnManualFixBehaviourPause", "token": "0x06000613"},
            {"name": "OnGraphStop", "token": "0x06000614"},
            {"name": "_DoPlayStopEvent", "token": "0x0600061a"},
            {"name": "_TryStop", "token": "0x0600061c"},
        ],
        "seekMethods": [
            {"name": "MarkForStop", "token": "0x0600060f"},
            {"name": "_TrySeek", "token": "0x06000618"},
        ],
        "serializedControls": [
            "_audioEventKey", "_isCue", "_stopEventAtClipEnd",
            "_stopEventAtClipEndKey", "_fadeOutTime", "_enableSeek",
            "_useBindingObj", "_is2D", "_emitter",
        ],
        "evidenceBoundary": "staticManagedPlayableMethodMetadataOnly",
    },
    "AudioEventPlayable": {
        "id": "timelineStringEventKey.audioEvent",
        "type": "Beyond.Audio.AudioEventPlayable",
        "behaviourType": "Beyond.Audio.AudioEventPlayableBehaviour",
        "assetToken": "0x02000104",
        "behaviourToken": "0x02000103",
        "requestMethods": [
            {"name": "OnBehaviourPlay", "token": "0x0600062b"},
            {"name": "ShouldPlay", "token": "0x06000630"},
            {"name": "_DoPlayEvent", "token": "0x06000632"},
        ],
        "stopMethods": [
            {"name": "OnBehaviourPause", "token": "0x0600062c"},
            {"name": "OnGraphStop", "token": "0x0600062d"},
            {"name": "_TryPostExitEvent", "token": "0x06000634"},
            {"name": "_TryStop", "token": "0x06000635"},
        ],
        "seekMethods": [
            {"name": "MarkSkip", "token": "0x06000628"},
            {"name": "_TrySeek", "token": "0x06000631"},
        ],
        "serializedControls": [
            "_audioEventKey", "_stopEventAtClipEnd", "_fadeOutWhenStop",
            "_fadeOutTime", "_enableSeek", "_useBindingObj", "_is2D",
            "_emitter", "_exitAudioEvent",
        ],
        "evidenceBoundary": "staticManagedPlayableMethodMetadataOnly",
    },
    "AudioMusicPlayable": {
        "id": "timelineMusicEventKey.audioMusic",
        "type": "Beyond.Gameplay.Audio.AudioMusicPlayable",
        "behaviourType": "Beyond.Gameplay.Audio.AudioMusicPlayableBehaviour",
        "assetToken": "0x02001abc",
        "behaviourToken": "0x02001abb",
        "requestMethods": [
            {"name": "OnBehaviourPlay", "token": "0x06009c63"},
            {"name": "_ShouldPlay", "token": "0x06009c66"},
            {"name": "_TriggerEvent", "token": "0x06009c67"},
        ],
        "skipMethods": [
            {"name": "OnTimelineSkip", "token": "0x06009c62"},
        ],
        "serializedControls": [
            "_audioEventKey", "musicActionType", "triggerOnSkip",
        ],
        "behaviourStateFields": [
            "eventKey", "musicActionType", "triggerOnSkip",
            "m_isMusicEventTriggered", "m_requiredActions",
        ],
        "serializedControlValueLabels": {
            "musicActionType": {
                "0": "DIALOG_MUSIC",
                "1": "NORMAL_MUSIC",
                "2": "CUSTOM_MUSIC",
            },
            "triggerOnSkip": {
                "0": "notTriggeredOnSkip",
                "1": "triggeredOnSkip",
            },
        },
        "controlValueEvidence": (
            "musicActionType labels match the current metadata enum "
            "Beyond.Gameplay.Core.DialogMusicAction+EDialogMusicActionType; "
            "triggerOnSkip is serialized as a current bool field"
        ),
        "evidenceBoundary": "staticManagedPlayableMethodMetadataOnly",
    },
}


AUDIO_MUSIC_NATIVE_STATE_GROUPS = (
    {
        "role": "topLevelMusicMode",
        "field": "MUSIC_STATE_GROUP_ID",
        "groupId": 0xE414D158,
        "groupIdHex": "0xe414d158",
        "recoveredName": "music_state",
        "nameEvidence": "exactFNV1HashMatch",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseMusicState",
        "setterMethod": "_SetWwiseMusicState",
        "methodIndex": 39631,
        "token": "0x06009ad0",
        "virtualAddress": "0x183a0cb00",
    },
    {
        "role": "worldMap",
        "field": "MUSIC_MAP_STATE_GROUP_ID",
        "groupId": 0xB3D78A5D,
        "groupIdHex": "0xb3d78a5d",
        "recoveredName": "music_map",
        "nameEvidence": "exactFNV1HashMatch",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseMusicMapState",
        "setterMethod": "_SetWwiseMusicMapState",
        "methodIndex": 39634,
        "token": "0x06009ad3",
        "virtualAddress": "0x186adc08c",
    },
    {
        "role": "battlePhase",
        "field": "BATTLE_MUSIC_STATE_GROUP_ID",
        "groupId": 0x4D9E8C28,
        "groupIdHex": "0x4d9e8c28",
        "nameEvidence": "groupHashExactAuthoredNameUnrecovered",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseBattleMusicState",
        "setterMethod": "_SetWwiseBattleMusicState",
        "methodIndex": 39636,
        "token": "0x06009ad5",
        "virtualAddress": "0x1846ab390",
    },
    {
        "role": "battleIntensity",
        "field": "BATTLE_MUSIC_INTENSITY_STATE_GROUP_ID",
        "groupId": 0x2560A0EE,
        "groupIdHex": "0x2560a0ee",
        "nameEvidence": "groupHashExactAuthoredNameUnrecovered",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseBattleMusicIntensityState",
        "setterMethod": "_SetWwiseBattleMusicIntensityState",
        "methodIndex": 39638,
        "token": "0x06009ad7",
        "virtualAddress": "0x183a0ca90",
    },
    {
        "role": "mission",
        "field": "MISSION_MUSIC_STATE_GROUP_ID",
        "groupId": 0x3B650E3D,
        "groupIdHex": "0x3b650e3d",
        "recoveredName": "music_mission",
        "nameEvidence": "exactFNV1HashMatch",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseMissionMusicState",
        "setterMethod": "_SetWwiseMissionMusicState",
        "methodIndex": 39640,
        "token": "0x06009ad9",
        "virtualAddress": "0x186adc004",
    },
    {
        "role": "dialog",
        "field": "DIALOG_MUSIC_STATE_GROUP_ID",
        "groupId": 0xA4C62908,
        "groupIdHex": "0xa4c62908",
        "nameEvidence": "groupHashExactAuthoredNameUnrecovered",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseDialogMusicState",
        "setterMethod": "_SetWwiseDialogMusicState",
        "methodIndex": 39642,
        "token": "0x06009adb",
        "virtualAddress": "0x186adbef4",
    },
    {
        "role": "cutscene",
        "field": "CUTSCENE_MUSIC_STATE_GROUP_ID",
        "groupId": 0x75C98B29,
        "groupIdHex": "0x75c98b29",
        "recoveredName": "music_cutscene",
        "nameEvidence": "exactFNV1HashMatch",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseCutsceneMusicState",
        "setterMethod": "_SetWwiseCutsceneMusicState",
        "methodIndex": 39644,
        "token": "0x06009add",
        "virtualAddress": "0x186adbe6c",
    },
    {
        "role": "login",
        "field": "LOGIN_MUSIC_STATE_GROUP_ID",
        "groupId": 0x6401EC38,
        "groupIdHex": "0x6401ec38",
        "nameEvidence": "groupHashExactAuthoredNameUnrecovered",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseLoginMusicState",
        "setterMethod": "_SetWwiseLoginMenuMusicState",
        "methodIndex": 39646,
        "token": "0x06009adf",
        "virtualAddress": "0x186adbf7c",
    },
    {
        "role": "meta",
        "field": "META_MUSIC_STATE_GROUP_ID",
        "groupId": 0x654423EE,
        "groupIdHex": "0x654423ee",
        "recoveredName": "music_meta",
        "nameEvidence": "exactFNV1HashMatch",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseMetaMusicState",
        "setterMethod": "_SetWwiseMetaMusicState",
        "methodIndex": 39648,
        "token": "0x06009ae1",
        "virtualAddress": "0x184491300",
    },
    {
        "role": "remoteCommunication",
        "field": "REMOTE_COMM_MUSIC_STATE_GROUP_ID",
        "groupId": 0xC52AA6BC,
        "groupIdHex": "0xc52aa6bc",
        "nameEvidence": "groupHashExactAuthoredNameUnrecovered",
        "enumType": "Beyond.Gameplay.Audio.AudioMusicSystem+EWwiseRemoteCommMusicState",
        "setterMethod": "_SetWwiseRemoteCommMusicState",
        "methodIndex": 39650,
        "token": "0x06009ae3",
        "virtualAddress": "0x186adc19c",
    },
)


MODEL_VIEW_NATIVE_ANCHOR_METADATA_SHA256 = native_evidence.EXPECTED_METADATA_SHA256


CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256 = native_evidence.EXPECTED_GAMEASSEMBLY_SHA256


_AUDIO_MUSIC_ENUM_VALUES = {
    "topLevelMusicMode": (
        ("UNKNOWN", 0xF9D3523D),
        ("MISSION", 0x166521A5),
        ("LOADING", 0xD505DEBB),
        ("EXPLORING", 0x6CB31EE7),
        ("COMBAT_GENERAL", 0x525E00A0),
        ("COMBAT_BOSS", 0x271CB603),
        ("CUTSCENE", 0x468283E1),
        ("DIALOGUE", 0xEA41209F),
        ("FACTORY", 0x51FBB249),
        ("BASE_MODE_DEFENSE", 0x00FC4659),
        ("DUNGEON", 0x244B0EC9),
        ("NARRATING", 0x36752FA3),
    ),
    "worldMap": (
        ("UNKNOWN", 0xF9D3523D),
        ("TUNDRA", 0x9B54723D),
        ("HONGSHAN", 0xFF51B103),
    ),
    "battlePhase": (
        ("UNKNOWN", 0xF9D3523D),
        ("MAIN_LOOP", 0xE34AF54B),
        ("ENDING", 0xEC675524),
    ),
    "battleIntensity": (
        ("UNKNOWN", 0xF9D3523D),
        ("LOW", 0x2081B4E5),
        ("HIGH", 0xD3A50981),
    ),
    "mission": (("NONE", 0x2CA33BDB),),
    "dialog": (("NONE", 0x2CA33BDB),),
    "cutscene": (("NONE", 0x2CA33BDB),),
    "login": (
        ("NONE", 0x2CA33BDB),
        ("INTRO", 0x4315C729),
        ("THEME", 0x4E9E9BB0),
        ("ENDING", 0xEC675524),
    ),
    "meta": (
        ("NONE", 0x2CA33BDB),
        ("GACHA_CUTSCENE", 0x73A7133C),
        ("GACHA_INTERFACE", 0x854CEF1D),
    ),
    "remoteCommunication": (
        ("NONE", 0x2CA33BDB),
        ("LOOP", 0x292FEA37),
        ("ENDING", 0xEC675524),
    ),
}


def _audio_music_enum_value(member: str, value_id: int) -> dict[str, Any]:
    return {
        "member": member,
        "hashInput": member.lower(),
        "valueId": value_id,
        "valueIdHex": f"0x{value_id:08x}",
        "resolution": "exactCurrentMetadataEnumMemberFNV1Utf16Hash",
    }


_AUDIO_MUSIC_STATIC_VALUE_CALLSITES = {
    "topLevelMusicMode": (
        {
            "callerMethod": "_StartBattleMusic",
            "callerMethodIndex": 39483,
            "callVirtualAddress": "0x1846ab06f",
            "valueMember": "COMBAT_GENERAL",
            "valueId": 0x525E00A0,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
        {
            "callerMethod": "OnEnterMainGame",
            "callerMethodIndex": 39513,
            "callVirtualAddress": "0x18449113e",
            "valueMember": "LOADING",
            "valueId": 0xD505DEBB,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
        {
            "callerMethod": "_TurnToLoadingIfInLoading",
            "callerMethodIndex": 39581,
            "callVirtualAddress": "0x186adc919",
            "valueMember": "LOADING",
            "valueId": 0xD505DEBB,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
        {
            "callerMethod": "SwitchToDialogMusic",
            "callerMethodIndex": 39590,
            "callVirtualAddress": "0x186ad9f58",
            "valueMember": "DIALOGUE",
            "valueId": 0xEA41209F,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
    ),
    "worldMap": (
        {
            "callerMethod": None,
            "callerMethodIndex": None,
            "callVirtualAddress": "0x18538585d",
            "valueMember": "TUNDRA",
            "valueId": 0x9B54723D,
            "valueRegister": "edx",
            "ownerResolution": "unresolvedSharedGenericBody",
            "ownerGap": "Direct call target and immediate value are exact; the shared/generated body has no safe metadata owner join.",
        },
    ),
    "battlePhase": (
        {
            "callerMethod": "_StartBattleMusic",
            "callerMethodIndex": 39483,
            "callVirtualAddress": "0x1846ab05f",
            "valueMember": "MAIN_LOOP",
            "valueId": 0xE34AF54B,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
    ),
    "battleIntensity": (
        {
            "callerMethod": "_StartBattleMusic",
            "callerMethodIndex": 39483,
            "callVirtualAddress": "0x1846ab04f",
            "valueMember": "HIGH",
            "valueId": 0xD3A50981,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
        {
            "callerMethod": "_CheckLeaveFight",
            "callerMethodIndex": 39486,
            "callVirtualAddress": "0x183a0d06c",
            "valueMember": "LOW",
            "valueId": 0x2081B4E5,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
        {
            "callerMethod": "_OnEscapeFromFight",
            "callerMethodIndex": 39491,
            "callVirtualAddress": "0x186adb46c",
            "valueMember": "LOW",
            "valueId": 0x2081B4E5,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
    ),
    "dialog": (
        {
            "callerMethod": "SwitchToDialogMusic",
            "callerMethodIndex": 39590,
            "callVirtualAddress": "0x186ad9f2a",
            "valueMember": "NONE",
            "valueId": 0x2CA33BDB,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
    ),
    "remoteCommunication": (
        {
            "callerMethod": "EndRemoteComm",
            "callerMethodIndex": 39599,
            "callVirtualAddress": "0x186ad8240",
            "valueMember": "ENDING",
            "valueId": 0xEC675524,
            "valueRegister": "edx",
            "ownerResolution": "exactMetadataBodyTarget",
        },
    ),
}


_AUDIO_MUSIC_RUNTIME_VALUE_CALLSITES = {
    "topLevelMusicMode": (
        {
            "callerMethod": "ManualSetMusicState",
            "callerMethodIndex": 39582,
            "callVirtualAddress": "0x186ad890f",
            "valueRegister": "edx<-ebx",
            "inputStatus": "runtimeParameterValueUnobserved",
        },
    ),
    "battlePhase": (
        {
            "callerMethod": "ManualSetBattleMusicState",
            "callerMethodIndex": 39583,
            "callVirtualAddress": "0x186ad88a7",
            "valueRegister": "edx<-ebx",
            "inputStatus": "runtimeParameterValueUnobserved",
        },
    ),
    "battleIntensity": (
        {
            "callerMethod": "ManualSetBattleMusicIntensityState",
            "callerMethodIndex": 39584,
            "callVirtualAddress": "0x186ad883f",
            "valueRegister": "edx<-ebx",
            "inputStatus": "runtimeParameterValueUnobserved",
        },
    ),
}


AUDIO_MUSIC_NATIVE_STATE_GROUPS = tuple(
    {
        **row,
        "values": tuple(
            _audio_music_enum_value(member, value_id)
            for member, value_id in _AUDIO_MUSIC_ENUM_VALUES[row["role"]]
        ),
        "staticValueCallsites": tuple(
            dict(value) for value in _AUDIO_MUSIC_STATIC_VALUE_CALLSITES.get(row["role"], ())
        ),
        "runtimeValueCallsites": tuple(
            dict(value) for value in _AUDIO_MUSIC_RUNTIME_VALUE_CALLSITES.get(row["role"], ())
        ),
        "binaryEvidence": {
            "status": "exactCurrentBuildStaticEvidence",
            "gameAssemblySha256": CUSTOM_FOOTSTEP_GAME_ASSEMBLY_SHA256,
            "metadataSha256": MODEL_VIEW_NATIVE_ANCHOR_METADATA_SHA256,
        },
    }
    for row in AUDIO_MUSIC_NATIVE_STATE_GROUPS
)


# These ids are joined twice: first to the typed v150 type-6 selector tails in
# the shipped banks, then to exact current GameAssembly setter callsites.  A
# semantic role is deliberately not an authored Wwise group name.  The three
# inferred rows remain visibly weaker than the two exact runtime setter rows.
AUDIO_RUNTIME_SELECTOR_GROUPS = (
    {
        "groupId": 0x7ACDACAF,
        "groupIdHex": "0x7acdacaf",
        "groupType": "switch",
        "semanticRole": "factoryRemoteNodeMode",
        "semanticLabel": "Factory remote node mode",
        "semanticEvidence": "exactNativeSetterAndValueMapping",
        "authoredGroupNameStatus": "unrecovered",
        "runtimeScope": "audioObject",
        "runtimeSetter": {
            "callerType": "Beyond.Gameplay.Audio.AudioRemoteFactoryBridge",
            "callerMethod": "UpdateNodeMode",
            "callerMethodIndex": 39714,
            "callerToken": "0x06009b23",
            "setSwitchCallVirtualAddress": "0x1850ffa6d",
            "setter": "Beyond.Audio.AudioAdapter.SetSwitch(uint,uint,ulong)",
            "audioObjectIdSource": {
                "method": "Beyond.Audio.AudioObject.get_audioObjectId",
                "methodIndex": 39038,
                "token": "0x0600987f",
                "virtualAddress": "0x1832d2360",
            },
        },
        "valueResolver": {
            "method": "GetAudioStateValueFromNodeMode",
            "methodIndex": 39759,
            "token": "0x06009b50",
            "virtualAddress": "0x186ae7b18",
        },
        "values": (
            # UpdateNodeMode receives the bit-valued NodeMode input, then
            # GetAudioStateValueFromNodeMode returns the Wwise value hash. The
            # mapping is literal in the current GameAssembly body; these are
            # not merely guessed FNV names. Keep both ids so the UI cannot
            # mistake the managed input for the Wwise branch value.
            {
                "valueId": 1,
                "valueIdHex": "0x00000001",
                "semanticName": "Normal",
                "resolvedValueId": 0x4527C498,
                "resolvedValueIdHex": "0x4527c498",
                "resolvedValueName": "normal",
                "resolutionEvidence": "exactNativeResolverReturnHash",
            },
            {
                "valueId": 2,
                "valueIdHex": "0x00000002",
                "semanticName": "Liquid",
                "resolvedValueId": 0xF3A9ACD5,
                "resolvedValueIdHex": "0xf3a9acd5",
                "resolvedValueName": "liquid",
                "resolutionEvidence": "exactNativeResolverReturnHash",
            },
            {
                "valueId": 4,
                "valueIdHex": "0x00000004",
                "semanticName": "Gas",
                "resolvedValueId": 0x228CF0D8,
                "resolvedValueIdHex": "0x228cf0d8",
                "resolvedValueName": "gas",
                "resolutionEvidence": "exactNativeResolverReturnHash",
            },
            {
                "valueId": 8,
                "valueIdHex": "0x00000008",
                "semanticName": "GasLiquid",
                "resolvedValueId": 0xFB9CA5C8,
                "resolvedValueIdHex": "0xfb9ca5c8",
                "resolvedValueName": "gasliquid",
                "resolutionEvidence": "exactNativeResolverReturnHash",
            },
            {
                "valueId": 16,
                "valueIdHex": "0x00000010",
                "semanticName": "GasTransition",
                "resolvedValueId": 0x59A68236,
                "resolvedValueIdHex": "0x59a68236",
                "resolvedValueName": "gastrans",
                "resolutionEvidence": "exactNativeResolverReturnHash",
            },
            {
                "valueId": 32,
                "valueIdHex": "0x00000020",
                "semanticName": "LiquidTransition",
                "resolvedValueId": 0x2F715D31,
                "resolvedValueIdHex": "0x2f715d31",
                "resolvedValueName": "liquidtrans",
                "resolutionEvidence": "exactNativeResolverReturnHash",
            },
            {
                "valueId": 64,
                "valueIdHex": "0x00000040",
                "semanticName": "SolidTransition",
                "resolvedValueId": 0x8353CA3C,
                "resolvedValueIdHex": "0x8353ca3c",
                "resolvedValueName": "solidtrans",
                "resolutionEvidence": "exactNativeResolverReturnHash",
            },
        ),
        "valueResolverStatus": "exactAllSevenInputsMapToWwiseValueHashes",
        "valueResolverZeroResultStatus": "unknownOrZeroNodeModeReturnsZeroAndCallerSkipsSetSwitch",
        "runtimeObservationStatus": "staticSetterCallsiteExactLiveValueNotObserved",
    },
    {
        "groupId": 0xF6699CF4,
        "groupIdHex": "0xf6699cf4",
        "groupType": "state",
        "semanticRole": "gamepadMotionBackend",
        "semanticLabel": "Gamepad motion-output backend",
        "semanticEvidence": "exactNativeStateSetterCallsites",
        "authoredGroupNameStatus": "unrecovered",
        "runtimeScope": "global",
        "runtimeSetter": {
            "callerType": "Beyond.Gameplay.Audio.AudioGamePadManager",
            "calls": (
                {
                    "method": "_TryAddXInputMotionOutput",
                    "setStateCallVirtualAddress": "0x186ad04e2",
                    "valueId": 0x1A9FC91F,
                    "semanticName": "XInput",
                },
                {
                    "method": "_TryRefreshScePadHandle",
                    "setStateCallVirtualAddress": "0x186ad069c",
                    "valueId": 0x1B9ABDB1,
                    "semanticName": "ScePad",
                },
            ),
            "setterHelperVirtualAddress": "0x183a0cb70",
            "setterMethodIndex": 446543,
            "setterToken": "0x06000ac9",
            "setterVirtualAddress": "0x183a0cbd0",
            "setter": "AkSoundEngine.SetState(uint,uint)",
        },
        "values": (
            {"valueId": 0x1A9FC91F, "valueIdHex": "0x1a9fc91f", "semanticName": "XInput", "semanticEvidence": "exactNativeCallConstant"},
            {"valueId": 0x1B9ABDB1, "valueIdHex": "0x1b9abdb1", "semanticName": "ScePad", "semanticEvidence": "exactNativeCallConstant"},
            {"valueId": 0x2CA33BDB, "valueIdHex": "0x2ca33bdb", "semanticNameStatus": "unresolved"},
            {"valueId": 0xE59CC828, "valueIdHex": "0xe59cc828", "semanticNameStatus": "unresolved"},
        ),
        "runtimeObservationStatus": "staticSetterCallsitesExactLiveBackendNotObserved",
    },
    {
        "groupId": 0x706B5267,
        "groupIdHex": "0x706b5267",
        "semanticRole": "voiceIdentitySelector",
        "semanticLabel": "Character / NPC voice identity selector",
        "semanticEvidence": "highConfidenceEventAndNpcWwiseIdCorrelation",
        "authoredGroupNameStatus": "unrecovered",
        "eventCount": 1601,
        "voiceEventCount": 1442,
        "runtimeObservationStatus": "setterAndLiveValueUnresolved",
    },
    {
        "groupId": 0xDFF0BCCC,
        "groupIdHex": "0xdff0bccc",
        "semanticRole": "surfaceMaterialSelector",
        "semanticLabel": "Surface / material selector",
        "semanticEvidence": "highConfidenceHashedValueVocabularyCorrelation",
        "authoredGroupNameStatus": "unrecovered",
        "runtimeObservationStatus": "setterAndLiveValueUnresolved",
    },
    {
        "groupId": 0x3C9C2C56,
        "groupIdHex": "0x3c9c2c56",
        "semanticRole": "localRemoteRoutingSelector",
        "semanticLabel": "Local / remote audio routing selector",
        "semanticEvidence": "highConfidenceExactLocalRemoteValueHashMatches",
        "authoredGroupNameStatus": "unrecovered",
        "runtimeObservationStatus": "setterAndLiveValueUnresolved",
    },
)

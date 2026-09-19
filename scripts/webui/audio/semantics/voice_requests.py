"""Exact native and AnimationClip voice-response requests."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from .context_utils import append_context as _append_context
from .context_utils import normalize_posix as _normalize_posix
from .native_evidence import (
    ANIMATION_VOICE_TRIGGER_MAPPING_ID,
    ANIMATION_VOICE_TRIGGER_NATIVE,
    NATIVE_VOICE_TRIGGER_MAPPING_ID,
    NATIVE_VOICE_TRIGGER_ROWS,
    NativeAudioEvidence,
)

ANIMATION_VOICE_CLIP_RELS = (
    Path("recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/AnimationClip"),
    Path("recovered/AnimeStudio-cli/Persistent/convert_by_type/AnimationClip"),
)

ANIMATION_VOICE_CLIP_RE = re.compile(
    r"^A_(?P<kind>actor|monster)_(?P<token>[^_]+)_", re.IGNORECASE
)

ANIMATION_VOICE_EVENT_RE = re.compile(
    r"^(?P<owner>(?P<prefix>chr|eny)_\d{4}_(?P<token>[a-z0-9]+))_"
    r"(?P<trigger>[a-z0-9_]+)_sv$",
    re.IGNORECASE,
)


def collect_native_voice_trigger_contexts(
    audio_index: dict[str, Any],
    native_context: NativeAudioEvidence,
) -> dict[str, list[dict[str, Any]]]:
    """Attach fingerprint-locked native response requests to voice definitions.

    These callsites load the trigger literal directly into the trigger-key
    argument immediately before ``VoiceManager.ResponseOnEntity`` (or the
    equivalent ``VoiceResponseProcessor.Response`` death path).  The selected
    speaker response and live execution remain unobserved, so matching is
    limited to current AudioDialog/Wwise identities ending in the exact
    ``_<triggerKey>_sv`` suffix.
    """

    if not native_context.validated:
        return {}
    aliases = [
        row for row in audio_index.get("audioDialogWwiseEventAliases") or []
        if isinstance(row, dict) and str(row.get("name") or "").strip()
    ]
    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for trigger_key, native in NATIVE_VOICE_TRIGGER_ROWS.items():
        suffix = f"_{trigger_key}_sv"
        for alias in aliases:
            event_name = str(alias.get("name") or "").strip()
            if not event_name.casefold().endswith(suffix.casefold()):
                continue
            _append_context(contexts, seen, event_name, {
                "kind": "nativeVoiceTriggerCallsite",
                "confidence": "direct",
                "semanticRole": "nativeVoiceResponseTriggerRequest",
                "playbackPlacementStatus": "exactNativeTriggerCompatibleVoiceDefinition",
                "triggerBindingStatus": "exactCurrentBuildLiteralArgumentAndAudioDialogEventSuffix",
                "triggerKey": trigger_key,
                "eventName": event_name,
                "eventHash": alias.get("eventHash"),
                "eventNameEvidence": alias.get("evidence"),
                "nativeMappingId": NATIVE_VOICE_TRIGGER_MAPPING_ID,
                "runtimeRoute": " -> ".join((
                    f"{native['consumerType']}.{native['consumerMethod']}",
                    str(native["playbackCall"]),
                    *(() if native["playbackCall"].endswith("VoiceResponseProcessor.Response")
                      else ("VoiceResponseProcessor",)),
                    "VoiceSpeakChannelProcessor._PlayVoice",
                    "VoicePlayer.PlayVoice",
                )),
                "runtimeActivationStatus": "nativeBranchAndLiveResponseSelectionUnobserved",
                "runtimeSelectionStatus": "speakerCooldownProbabilityToneAndLiveChoiceUnobserved",
                "triggerRequestEvidence": [
                    "fingerprintLockedCurrentMetadataStringLiteralHandle",
                    "exactNativeLiteralLoadIntoTriggerArgument",
                    "exactDirectVoiceResponseCall",
                    "exactAudioDialogPathHashEqualsVoiceIdAndWwiseEventId",
                ],
                **native,
            })
    return dict(contexts)


def _animation_voice_trigger_rows(data: bytes) -> list[dict[str, Any]]:
    """Read only Unity AnimationEvent ``TriggerVoice`` scalar arguments."""

    rows: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_events = False
    event_index = -1

    def finish() -> None:
        nonlocal current
        if (
            current
            and current.get("function") == "TriggerVoice"
            and str(current.get("triggerKey") or "").strip()
        ):
            rows.append(current)
        current = None

    for raw_line in data.splitlines():
        line = raw_line.decode("utf-8", errors="replace")
        if line == "  m_Events:":
            in_events = True
        elif in_events and line.startswith("  - time: "):
            finish()
            event_index += 1
            raw_value = line.removeprefix("  - time: ").strip()
            try:
                time_value: float | str = float(raw_value)
            except ValueError:
                time_value = raw_value
            current = {"eventIndex": event_index, "time": time_value}
        elif current is not None and line.startswith("    functionName: "):
            current["function"] = line.removeprefix("    functionName: ").strip().strip("'\"")
        elif current is not None and line.startswith("    data: "):
            current["triggerKey"] = line.removeprefix("    data: ").strip().strip("'\"")
        elif current is not None and line.startswith("    floatParameter: "):
            raw_value = line.removeprefix("    floatParameter: ").strip()
            try:
                current["floatParameter"] = float(raw_value)
            except ValueError:
                current["floatParameter"] = raw_value
        elif current is not None and line.startswith("    intParameter: "):
            raw_value = line.removeprefix("    intParameter: ").strip()
            try:
                current["intParameter"] = int(raw_value)
            except ValueError:
                current["intParameter"] = raw_value
    finish()
    return rows


def collect_animation_voice_trigger_contexts(
    export_root: Path,
    audio_index: dict[str, Any],
    native_context: NativeAudioEvidence,
) -> dict[str, list[dict[str, Any]]]:
    """Join exact AnimationClip voice requests to exact voice Event identities.

    ``AnimatorMono.TriggerVoice(AnimationEvent)`` forwards ``data`` as the
    response trigger key and ``intParameter`` as the response integer argument.
    This is not a direct Wwise Event post.  A voice definition is admitted only
    when its actor/enemy kind, identity token, and trigger key exactly match the
    current AudioDialog/Wwise Event name.  When multiple numbered definitions
    reuse one animation identity token, all exact candidates remain visibly
    shared instead of inventing a unique template owner.
    """

    if not native_context.validated:
        return {}

    aliases: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for raw_alias in audio_index.get("audioDialogWwiseEventAliases") or []:
        if not isinstance(raw_alias, dict):
            continue
        event_name = str(raw_alias.get("name") or "").strip()
        match = ANIMATION_VOICE_EVENT_RE.fullmatch(event_name)
        if match is None:
            continue
        aliases[(
            match.group("prefix").casefold(),
            match.group("token").casefold(),
            match.group("trigger").casefold(),
        )].append(raw_alias)

    contexts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for rel_root in ANIMATION_VOICE_CLIP_RELS:
        root = export_root / rel_root
        if not root.is_dir():
            continue
        for path in sorted(root.glob("A_*.anim"), key=lambda item: item.name):
            clip_match = ANIMATION_VOICE_CLIP_RE.match(path.stem)
            if clip_match is None:
                continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            if b"functionName: TriggerVoice" not in data:
                continue
            prefix = "chr" if clip_match.group("kind").casefold() == "actor" else "eny"
            identity_token = clip_match.group("token").casefold()
            source_path = _normalize_posix(path.relative_to(export_root))
            source_layer = (
                "Persistent" if "/Persistent/" in source_path else "StreamingAssets"
            )
            for row in _animation_voice_trigger_rows(data):
                trigger_key = str(row.get("triggerKey") or "").strip().casefold()
                candidates = aliases.get((prefix, identity_token, trigger_key)) or []
                candidates_by_name = {
                    str(alias.get("name") or "").strip(): alias
                    for alias in candidates
                    if str(alias.get("name") or "").strip()
                }
                if not candidates_by_name:
                    continue
                owner_candidate_ids = sorted(
                    match.group("owner")
                    for event_name in candidates_by_name
                    if (match := ANIMATION_VOICE_EVENT_RE.fullmatch(event_name)) is not None
                )
                for event_name, alias in sorted(candidates_by_name.items()):
                    owner_match = ANIMATION_VOICE_EVENT_RE.fullmatch(event_name)
                    if owner_match is None:
                        continue
                    shared_owner = len(owner_candidate_ids) > 1
                    _append_context(contexts, seen, event_name, {
                        "kind": "animationVoiceTrigger",
                        "confidence": (
                            "exactSharedIdentityTokenCandidate" if shared_owner else "direct"
                        ),
                        "semanticRole": "authoredAnimationVoiceResponseTrigger",
                        "playbackPlacementStatus": "exactAnimationVoiceTriggerCompatibleDefinition",
                        "triggerBindingStatus": (
                            "exactAnimationOwnerTokenTriggerKeyAndAudioDialogEventIdentity"
                        ),
                        "ownerKind": "character" if prefix == "chr" else "enemy",
                        "ownerId": owner_match.group("owner"),
                        "ownerCandidateIds": owner_candidate_ids,
                        "animationOwnerCandidateCount": len(owner_candidate_ids),
                        "animationOwnershipScope": (
                            "sharedIdentityToken" if shared_owner else "singleDefinitionIdentityToken"
                        ),
                        "identityToken": identity_token,
                        "triggerKey": trigger_key,
                        "eventName": event_name,
                        "eventHash": alias.get("eventHash"),
                        "eventNameEvidence": alias.get("evidence"),
                        "clip": path.stem,
                        "clipSource": source_path,
                        "sourceLayer": source_layer,
                        "eventIndex": row.get("eventIndex"),
                        "time": row.get("time"),
                        "function": row.get("function"),
                        "intParameter": row.get("intParameter"),
                        "floatParameter": row.get("floatParameter"),
                        "nativeMappingId": ANIMATION_VOICE_TRIGGER_MAPPING_ID,
                        "runtimeRoute": (
                            "AnimationClip TriggerVoice -> AnimatorMono.TriggerVoice -> "
                            "VoiceManager.ResponseOnEntity -> VoiceResponseProcessor -> "
                            "VoiceSpeakChannelProcessor._PlayVoice -> VoicePlayer.PlayVoice"
                        ),
                        "runtimeActivationStatus": "animationPlaybackAndLiveResponseSelectionUnobserved",
                        "runtimeSelectionStatus": "speakerCooldownProbabilityToneAndLiveChoiceUnobserved",
                        "triggerRequestEvidence": [
                            "exactUnityAnimationEventTriggerVoiceArguments",
                            "exactAnimationClipAndVoiceDefinitionIdentityToken",
                            "fingerprintLockedCurrentBuildAnimatorMonoNativeForwarder",
                            "exactAudioDialogPathHashEqualsVoiceIdAndWwiseEventId",
                        ],
                        **ANIMATION_VOICE_TRIGGER_NATIVE,
                    })
    return dict(contexts)

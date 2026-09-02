#!/usr/bin/env python3
"""Fail-closed contract check for Endminf overview-02 runtime post state."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
AUDIT = REPO / "reports/assets/endminf_overview_02_post_curve_native_audit.json"
UBER_AUDIT = REPO / "reports/assets/endminf_overview_02_uber_post_native_audit.json"
CLOCK = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
    / "EndfieldEndminfVisualCompatibilityClock.cs"
)
SOURCE_CURVES = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Resources/EndfieldEndminfSourcePost"
    / "endminf_overview_02_source_post_curves.json"
)
SOURCE_CURVE_RUNTIME = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
    / "EndfieldRecoveredEndminfSourcePostCurves.cs"
)
PIPELINE = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/HGCompatRenderPipeline.cs"
)
SHADER = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Shaders/HGRPCompat"
    / "EndfieldHGRPExposureTonemap.shader"
)
CAPTURE = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
    / "EndfieldEndminfViewerPlayModeCapture.cs"
)
OPEN_WRAPPER = LAB / "open_character_recovery_lab.bat"
PLAYBACK = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Runtime/Animation/EndfieldOverviewPlayback.cs"
)
TRIGGER_CONTRACT = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects"
    / "endminf_effect_nanguan_trigger_contract.json"
)

EXPECTED_CLIP_SHA256 = (
    "9814b9de92d5af7902b1967c295f98d29327824bdd7b478984527c5ccccd076c"
)
EXPECTED_SOURCE_CURVE_PAYLOAD_SHA256 = (
    "044017968e8d7cfe1f291274f29700a9d7bffc2bc18e333fa262d961b5385ace"
)
EXPECTED_COMBINED_FRAGMENT_DXBC_SHA256 = (
    "3f490e1504c435541769ee03e881583df554e652df155e5b942a3a410d8e086b"
)
EXPECTED_ACTIVE_FRAGMENT_DXBC_SHA256 = (
    "86a732cef7eedb150cbcafb35a994c1e3f7b1ef837dc618131a95e9dfe030c97"
)
EXPECTED_KEYS = (
    ((0.0, 0.12700000405311584), (0.1666666716337204, 0.0),
     (4.400000095367432, 0.0), (4.433333396911621, 0.10100000351667404),
     (4.599999904632568, 0.0)),
    ((0.0, 0.15199999511241913), (0.1666666716337204, 0.0),
     (4.400000095367432, 0.0), (4.433333396911621, 0.10899999737739563),
     (4.599999904632568, 0.0)),
    ((0.0, 1.0),),
)


def require_tokens(text: str, tokens: tuple[str, ...], label: str) -> None:
    missing = [token for token in tokens if token not in text]
    if missing:
        raise RuntimeError(f"{label} contract missing tokens: {missing}")


def verify() -> dict[str, object]:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    uber_audit = json.loads(UBER_AUDIT.read_text(encoding="utf-8"))
    if audit["inputs"]["clipSha256"] != EXPECTED_CLIP_SHA256:
        raise RuntimeError("overview-02 clip hash mismatch")
    if audit["targetPath"] != {"name": "post (1)", "crc32": 669740077}:
        raise RuntimeError("overview-02 animated target path mismatch")
    bindings = audit["bindings"]
    if len(bindings) != 3:
        raise RuntimeError(f"expected three overview-02 scalar curves, got {len(bindings)}")
    for index, (binding, expected) in enumerate(zip(bindings, EXPECTED_KEYS)):
        actual = tuple((row["time"], row["value"]) for row in binding["keys"])
        if actual != expected:
            raise RuntimeError(f"overview-02 curve {index} key mismatch: {actual!r}")
    combined_variant = uber_audit["recovered_shader"]["endminf_combined_variant"]
    if combined_variant["keywords"] != [
        "BLOOM",
        "RADIAL_BLUR_CHROMATIC_ABERRATION",
    ]:
        raise RuntimeError("Endminf combined Uber keyword pair mismatch")
    if (
        combined_variant["fragment_dxbc_sha256"]
        != EXPECTED_COMBINED_FRAGMENT_DXBC_SHA256
    ):
        raise RuntimeError("Endminf combined Uber fragment hash mismatch")

    source_curve_text = SOURCE_CURVES.read_text(encoding="utf-8")
    normalized_source_curve_text = source_curve_text.replace("\r\n", "\n").replace(
        "\r", "\n"
    )
    source_curve_payload_hash = hashlib.sha256(
        normalized_source_curve_text.encode("utf-8")
    ).hexdigest()
    if source_curve_payload_hash != EXPECTED_SOURCE_CURVE_PAYLOAD_SHA256:
        raise RuntimeError(
            "generated overview-02 source-curve payload hash mismatch: "
            f"{source_curve_payload_hash}"
        )
    source_curves = json.loads(normalized_source_curve_text)
    if source_curves["schema"] != "endfield.endminf-overview-02-source-post-curves.v1":
        raise RuntimeError("generated overview-02 source-curve schema mismatch")
    if source_curves["sourceClip"]["sha256"] != EXPECTED_CLIP_SHA256:
        raise RuntimeError("generated overview-02 source-curve clip hash mismatch")
    if source_curves["target"] != {"name": "post (1)", "pathCrc32": 669740077}:
        raise RuntimeError("generated overview-02 source-curve target mismatch")
    if [row["role"] for row in source_curves["curves"]] != [
        "chromaticIntensity",
        "radialIntensity",
        "radialPower",
    ]:
        raise RuntimeError("generated overview-02 source-curve role order mismatch")
    runtime_boundary = source_curves.get("runtimeBoundary", "")
    require_tokens(runtime_boundary, (
        "conditional pinned unpatched route",
        "recorded installed local IFix snapshot excludes those route targets",
        "retail EffectInstance tick domain",
        "SceneColor chronology",
        "retail-equivalent Unity presentation path remain outside this payload",
    ), "source-curve non-equivalence boundary")

    trigger = json.loads(TRIGGER_CONTRACT.read_text(encoding="utf-8"))
    if trigger.get("schema") != "endfield.endminf-effect-nanguan-trigger.v5":
        raise RuntimeError("Endminf effect trigger contract is not v5")
    evidence = trigger.get("evidence", {})
    if evidence.get("nativeBuildGate", {}).get("status") != "validated":
        raise RuntimeError("Endminf trigger native build gate is not validated")
    join = evidence.get("overviewSourceJoin", {})
    if join.get("state") != {
        "path": "Base Layer.Overview.FromOveview",
        "fullPathId": 1560421867,
        "pathCrc32": "0x5d0225eb",
        "layerIndex": 0,
    }:
        raise RuntimeError("exact FromOveview state join is not proven")
    behaviour = join.get("stateMachineBehaviour", {})
    if (
        behaviour.get("pathId") != -5549677297504648584 or
        behaviour.get("rangeStart") != 3 or
        behaviour.get("rangeCount") != 1 or
        behaviour.get("behaviourIndex") != 3
    ):
        raise RuntimeError("exact FromOveview behaviour join is not proven")
    ordered_effects = behaviour.get("orderedEffects", [])
    if [row.get("effectName") for row in ordered_effects] != [
        "P_fxui_endminm003_overview_01",
        "P_fxui_endminm003_overview_02",
        "P_fxui_endminm003_overview_03",
        "P_fxui_endminm003_overview_04",
    ]:
        raise RuntimeError("FromOveview ordered effect ownership drifted")
    if ordered_effects[0] != {
        "effectName": "P_fxui_endminm003_overview_01",
        "isScreenFx": 0,
        "mountPoint": "",
        "finishWhenExit": 1,
        "finishWhenTransition": 0,
        "isStationaryPosition": 1,
        "shouldFollowScale": 0,
        "shouldFollowRotation": 1,
        "shouldFollowMainObjRotation": 0,
    }:
        raise RuntimeError("overview_01 source owner flags drifted")
    if join.get("overview01PostHierarchy") != {
        "rootTransformPathId": 8425642429156191353,
        "postTransformPathId": 8592508268722613369,
        "postGameObject": "post (1)",
        "postLocalPosition": [0.0, 1.266, 0.0],
        "postLocalRotation": [0.0, 0.0, 0.0, 1.0],
        "postLocalScale": [1.0, 1.0, 1.0],
    }:
        raise RuntimeError("overview_01 post hierarchy drifted")
    ifix = join.get("recordedInstalledIfixSnapshot", {})
    if (
        ifix.get("sourceBuildMatchesPinnedNative") is not True or
        ifix.get("patchSha256") !=
            "baa28ae497e64d94e152886622bbe5fb391199bcbf8366e2df91591c9a9f172c" or
        ifix.get("targetCount") != 32 or
        ifix.get("relevantRouteTargetsPresent") != [] or
        ifix.get("runtimeOrRemotePatchStateProven") is not False
    ):
        raise RuntimeError("recorded local IFix route exclusion drifted")
    route = trigger.get("conclusions", {}).get(
        "overviewStateToEffectInstanceStart", {})
    if (
        route.get("serializedOwnerSourceClosed") is not True or
        route.get("pinnedUnpatchedNativeRouteSourceClosed") is not True or
        route.get("recordedIfixSnapshotNonreplacement") is not True or
        route.get("currentRuntimeRouteSourceClosed") is not False or
        route.get("status") != "conditional_pinned_unpatched_route_only"
    ):
        raise RuntimeError("conditional pinned unpatched trigger route drifted")
    require_tokens(route.get("nonclaim", ""), (
        "runtime slot ownership",
        "remote/downloaded or memory-only patches",
        "No absolute capture/video timeline offset",
        "continuously sampled body-Animator clock",
    ), "conditional trigger-route boundary")
    control_flow_names = {
        row.get("name") for row in evidence.get("native", {}).get(
            "controlFlow", [])
    }
    required_seed_edges = {
        "overview_state_enter_load_immediately",
        "overview_state_enter_sync_same_effect_instance",
        "sync_effect_time_valid_positive_elapsed_gate",
        "sync_effect_time_elapsed_product",
        "sync_child_animator_update_zero",
        "sync_child_animator_update_elapsed",
        "sync_effect_instance_manual_time",
        "load_immediately_to_load_finish",
        "load_finish_to_start",
        "start_set_active_true_internal_core",
        "set_active_to_play_effect",
        "play_effect_to_lod_play",
        "lod_play_to_animator_play",
    }
    if not required_seed_edges.issubset(control_flow_names):
        raise RuntimeError("one-shot native seed control-flow proof is incomplete")
    child_route = trigger.get("conclusions", {}).get(
        "lodOwnedChildAnimatorDefinitionAndPlayCodePath", {})
    display_route = trigger.get("conclusions", {}).get(
        "effectSettingLodGameObjectActivation", {})
    if (
        child_route.get("runtimeInvocationForThisLodRowSourceClosed") is not True or
        child_route.get("clipStartRelativeToEffectInstanceStartSourceClosed") is not True or
        "activation latch" not in str(child_route.get("sourceClosedScope") or "") or
        display_route.get("sourceClosed") is not False or
        display_route.get("status") !=
            "animator_play_closed_gameobject_display_unresolved"
    ):
        raise RuntimeError("conditional Start-to-child-Animator route drifted")
    validity_rows = [
        row for row in evidence.get("native", {}).get("controlFlow", [])
        if row.get("name") == "sync_effect_time_valid_positive_elapsed_gate"
    ]
    if (
        len(validity_rows) != 1 or
        validity_rows[0].get("target") !=
            "Beyond.Gameplay.EffectInstance.get_isValid" or
        "active-state semantics are not claimed" not in
            str(validity_rows[0].get("semantic") or "")
    ):
        raise RuntimeError("_SyncEffectTime validity-gate proof drifted")
    if len(evidence.get("native", {}).get(
            "syncEffectTimeDirectCallers", [])) != 1:
        raise RuntimeError("_SyncEffectTime direct-caller proof drifted")
    scanned_sections = evidence.get("native", {}).get(
        "syncEffectTimeDirectCallerExecutableSectionsScanned", [])
    if [row.get("name") for row in scanned_sections] != [
            ".text", "il2cpp", ".tvm0"]:
        raise RuntimeError("_SyncEffectTime executable-section census drifted")
    lab_playback = trigger.get("conclusions", {}).get("labPlayback", {})
    if (
        lab_playback.get("sourceOwner") !=
            "FromOveview AnimatorBehaviourPlayEffect" or
        lab_playback.get("sourceTriggerOwnerExact") is not True or
        lab_playback.get("oneShotSeedExact") is not True or
        lab_playback.get("retailOwnerExact") is not False or
        lab_playback.get("retailEffectInstanceTransportExact") is not False or
        lab_playback.get("retailTimingExact") is not False
    ):
        raise RuntimeError("one-shot lab/retail timing boundary drifted")
    require_tokens(lab_playback.get("labStartPolicy", ""), (
        "enter exact FromOveview",
        "instantiate/activate/start overview_01",
        "single captured length*normalizedTime seed",
        "without re-polling the body Animator",
    ), "one-shot source seed policy")

    source_curve_runtime = SOURCE_CURVE_RUNTIME.read_text(encoding="utf-8")
    require_tokens(source_curve_runtime, (
        'ExpectedSchema =\n            "endfield.endminf-overview-02-source-post-curves.v1"',
        EXPECTED_CLIP_SHA256,
        EXPECTED_SOURCE_CURVE_PAYLOAD_SHA256,
        'Resources.Load<TextAsset>(ResourceName)',
        '.Replace("\\r\\n", "\\n")',
        'sha.ComputeHash(Encoding.UTF8.GetBytes(normalizedPayload))',
        'JsonUtility.FromJson<SourcePostContract>(normalizedPayload)',
        'Mathf.Clamp(',
        'contract.sourceClip.startSeconds',
        'contract.sourceClip.stopSeconds',
        'return ((key.a * delta + key.b) * delta + key.c) * delta + key.d;',
        'curve.keys.Length != keyCount',
        'curve.pathCrc32 != 669740077L',
        'curve.attributeCrc32 != attributeCrc32',
    ), "exact source-curve runtime")

    clock = CLOCK.read_text(encoding="utf-8")
    require_tokens(clock, (
        "ClearOverview02(Transform effectRoot)",
        "ClearSourcePost()",
        '"ENDFIELD_RECOVERED_ENDMINF_SOURCE_POST"',
        "public static bool SourcePostSeedAuthenticated =>",
        "TryGetAuthenticatedSourcePostElapsed(out _)",
        "if (!SourcePostRequested)",
        "sourcePostRoot != null",
        "RecoveredPostGameObjectPathId =\n            8953141407210302585L",
        "RecoveredPostTransformPathId =\n            8592508268722613369L",
        "TryResolveRecoveredPostCenter(",
        "sourcePostCenter = resolvedPostCenter;",
        "sourcePostSeedSeconds = sourceElapsed;",
        "sourcePostBindTime = Time.timeAsDouble;",
        "double delta = Time.timeAsDouble - sourcePostBindTime;",
        "elapsed = sourcePostSeedSeconds + (float)delta;",
        "boundSourcePostGeneration == sourcePostGeneration",
        "IsSourceOwnerLive(overview02SourceOwner,",
        "overview02SourcePlaybackGeneration",
        "owner.AnimatorContractActive",
        "animator.runtimeAnimatorController != null",
        "public static bool RetailEffectTickDomainExact => false;",
        '"P_fxui_endminm003_overview_01__OverviewRuntime"',
        '"P_fxui_endminm003_overview_02__OverviewRuntime"',
        "MarkOverview02CompatibilityStart(Transform effectRoot)",
        "compatibilityOverview02Root",
        "compatibilityStartTime",
        "!TryGetAuthenticatedSourcePostElapsed(out float elapsed)",
        "private static bool TryGetAuthenticatedSourcePostElapsed(",
        "elapsed = 0.0f;\n            return false;",
        "EndfieldRecoveredEndminfSourcePostCurves.TryEvaluate(",
        "out float animatedRadialPower",
        '"Recovered Endminf source post failed closed: "',
        "Mathf.Lerp(",
        "1.0f,",
        "Mathf.Clamp01(radial / chromatic)",
        "(chromaticActive && radial > 0.01f ? 6 : 3)",
        "camera.WorldToViewportPoint(",
        "sourcePostCenter.position",
        "Vector2 center = new Vector2(viewport.x, viewport.y)",
        "viewport.x * 2.0f - 1.0f",
        "viewport.y * 2.0f - 1.0f",
        "signedCenter.magnitude > 1.414f",
        "(signedCenter.normalized + Vector2.one) * 0.5f",
        "Mathf.Clamp01(center.x)",
        "Mathf.Clamp01(center.y)",
    ), "runtime clock")
    forbidden_clock_tokens = (
        "EvaluateSourceCurve(",
        "initialPeak * 0.45f",
        "lateStartSeconds = 4.3166667f",
        "latePeakSeconds = 4.35f",
        "lateEndSeconds = 4.5166667f",
    )
    leaked = [token for token in forbidden_clock_tokens if token in clock]
    leaked.extend(token for token in (
        "RecoveredPostCenterLocal",
        "new Vector3(0.0f, 1.266f, 0.0f)",
    ) if token in clock)
    if leaked:
        raise RuntimeError(f"video-fitted source-curve substitute remains: {leaked}")
    evaluator = clock[
        clock.index("public static bool TryEvaluateRecoveredPost("):
        clock.index("private static bool TryGetAuthenticatedSourcePostElapsed(")
    ]
    if "TryGetElapsed(" in evaluator:
        raise RuntimeError("source post still consumes the unauthenticated compatibility clock")

    pipeline = PIPELINE.read_text(encoding="utf-8")
    require_tokens(pipeline, (
        "TryEvaluateRecoveredPost(",
        "endminfPost.radialIntensity",
        "endminfPost.chromaticIntensity",
        "endminfPost.mode",
        "endminfPost.effectivePower",
        "endminfPost.centerViewport",
        "GraphicsFormat.R16G16B16A16_SFloat",
        "LastRecoveredEndminfPostSourceGraphicsFormat",
        "LastRecoveredEndminfBloomGraphicsFormat",
        "RecoveredEndminfPostSourceId",
        "? new Vector4(\n                        endminfPost.radialIntensity,",
        "endminfPost.chromaticIntensity,",
    ), "render-pipeline packing")
    if "EvaluateEndminfVisualCompatibility(" in pipeline:
        raise RuntimeError("retired empirical Effect-02 evaluator is still present")
    if "EndminfCompatibilityUberIntensityScale" in pipeline:
        raise RuntimeError("video-fitted Endminf Uber intensity scale remains")

    capture = CAPTURE.read_text(encoding="utf-8")
    require_tokens(capture, (
        'private const string RecordingVisualPostPreRollSeconds = "0";',
        "IncludeCharInfoBackground = true",
        "IncludeBackgroundPortrait = true",
        "charInfoBackgroundRequested = IncludeCharInfoBackground",
        "backgroundPortraitRequested = IncludeBackgroundPortrait",
        "public Vector2 endminfPostCenterViewport",
        "endminfPostCenterViewport = endminfPostState.centerViewport",
        "public string endminfPostSourceGraphicsFormat",
        "observedEndminfPostSourceRgba16",
        "observedEndminfBloomR11",
        "retail R16G16B16A16_FLOAT Uber source handoff",
        "retail R11G11B10_FLOAT Uber bloom handoff",
        "IsEndminfSourceBackgroundActive()",
        "IsEndminfSourceForwardOverlayActive()",
        "IsBackgroundPortraitActive()",
        "if (!requiredCaptureContractReady)",
        "foregroundUiOverlayIncluded = false",
        "EndfieldEndminfVisualCompatibilityClock.SourcePostEnvironmentVariable",
        "public bool endminfPostEvaluated;",
        "bool endminfPostEvaluated =",
        "? endminfPostState.elapsed",
        "endminfPostEvaluated = endminfPostEvaluated",
        "value.endminfPostEvaluated && Mathf.Abs(",
        "authenticated Endminf overview_01 source-post clock",
        "public bool endminfSourceBackgroundIncluded;",
        "public bool endminfSourceForwardOverlayRequested;",
        "public bool sourceFloorGridOverlayIncluded;",
        "public bool fittedCompatibilityPlateActive;",
        "IsEndminfSourceBackgroundActive()",
        "value.EndminfSourceBackgroundActive",
        "value.EndminfSourceForwardOverlayActive",
        "value.sourceContent.activeInHierarchy",
        "value.farGridRenderer.enabled",
        "value.shadowPlaneRenderer.enabled",
        "!value.compatibilityBackdropRenderer.enabled",
        "IsFittedCompatibilityPlateActive()",
        "fitted Endminf compatibility plate remained active",
        '"ENDFIELD_RECOVERED_CHARINFO_BACKGROUND_PORTRAIT"',
        "EndminfSourceForwardOverlayEnvironmentVariable",
        "sourceFloorGridOverlayIncluded",
        "value.floorRenderQueue == 2000",
        "value.farGridRenderQueue == 2950",
        "!value.sphereOutsidePresentationReady",
        "!value.deferredExactConsumerReady",
    ), "August 24 capture scope and phase")
    if (
        "EndfieldEndminfVisualCompatibilityClock.TryGetElapsed(\n"
        "                out float endminfPostSeconds);"
    ) in capture:
        raise RuntimeError("capture still reports the broad compatibility clock")
    selector_default = re.search(
        r"if \(string\.IsNullOrWhiteSpace\(Environment\.GetEnvironmentVariable\(\s*"
        r"EndfieldEndminfVisualCompatibilityClock\.SourcePostEnvironmentVariable\)\)\)\s*"
        r"\{\s*Environment\.SetEnvironmentVariable\(\s*"
        r"EndfieldEndminfVisualCompatibilityClock\.SourcePostEnvironmentVariable,\s*"
        r'"1"\);\s*\}',
        capture,
        re.DOTALL,
    )
    if selector_default is None:
        raise RuntimeError(
            "capture no longer defaults source post only when selector is absent")
    require_tokens(capture, (
        'sourceBackgroundSelection = "0";',
        'sourceForwardOverlaySelection = "1";',
        ".EndminfSourceBackgroundEnvironmentVariable,\n                    \"0\"",
        ".EndminfSourceForwardOverlayEnvironmentVariable,\n                    \"1\"",
        "SphereOutsidePresentationEnvironment",
    ), "canonical neutral-clear plus source Floor/Far overlay policy")
    for selector in (
        "EndminfBackdropVisualCompatibilityEnvironmentVariable",
        "ReadySubsetEnvironmentVariable",
    ):
        if re.search(
            r"Environment\.SetEnvironmentVariable\(\s*"
            r"EndfieldRecoveredCharInfoPresentation\s*\." +
            re.escape(selector) + r',\s*"0"\);',
            capture,
            re.DOTALL,
        ) is None:
            raise RuntimeError(
                f"canonical capture no longer disables fitted selector {selector}")
    require_tokens(OPEN_WRAPPER.read_text(encoding="utf-8"), (
        'set "ENDFIELD_ENDMINF_VISUAL_COMPATIBILITY_PREROLL_SECONDS=0"',
        'set "ENDFIELD_RECOVERED_ENDMINF_SOURCE_POST=1"',
        'set "ENDFIELD_RECOVERED_CHARINFO_BACKGROUND_PORTRAIT=1"',
        'set "ENDFIELD_ENDMINF_SOURCE_BACKGROUND=0"',
        'set "ENDFIELD_ENDMINF_SOURCE_FORWARD_OVERLAY=1"',
    ), "August 24 interactive reproduction profile")

    playback = PLAYBACK.read_text(encoding="utf-8")
    require_tokens(playback, (
        "public struct EndfieldOverviewEffectSourceClock",
        "internal int playbackGeneration;",
        "EndfieldOverviewEffectSourceClock sourceClock);",
        "seconds = current.length * current.normalizedTime;",
        "current.fullPathHash != SourceOverviewStartFullPathHash",
        'animator.SetTrigger("EnableSwitch")',
        "animator.Update(0f);",
        "TryGetAutomaticOverviewStartSeconds(out float sourceElapsed)",
        "new EndfieldOverviewEffectSourceClock",
        "playbackGeneration = playbackGeneration",
        "stateFullPathHash = SourceOverviewStartFullPathHash",
        "elapsedSeconds = sourceElapsed",
        "valid = true",
        "FinishAllEntranceEffects();",
        "StopOverviewAudio();",
        "RestoreRecoveredParameters();",
    ), "authenticated FromOveview elapsed owner")
    restart = playback[
        playback.index("private bool TryRestartRecoveredAnimator()"):
        playback.index("private void OnAnimatorMove()")
    ]
    if restart.index('animator.SetTrigger("EnableSwitch")') > restart.index(
            "PublishEntranceEffects(new"):
        raise RuntimeError("effects publish before exact FromOveview state entry")
    restart_entry = playback[
        playback.index("public void RestartOverview()"):
        playback.index("public void RestartOverviewFromSelection()")
    ]
    required_failure = restart_entry[
        restart_entry.index("if (requireAnimatorContract)"):
        restart_entry.index("Animation animation =", restart_entry.index(
            "if (requireAnimatorContract)"))
    ]
    require_tokens(required_failure, (
        "playbackGeneration++;",
        "AnimatorContractActive = false;",
        "FinishAllEntranceEffects();",
        "StopOverviewAudio();",
        "RestoreRecoveredParameters();",
    ), "all automatic Animator restart failures unwind prior ownership")

    spawner = (
        LAB
        / "Assets/EndfieldGraphShaderLab/Runtime/Rendering"
        / "EndfieldRecoveredCharEffectSpawner.cs"
    ).read_text(encoding="utf-8")
    require_tokens(spawner, (
        "EndfieldOverviewEffectSourceClock sourceClock)",
        "SpawnAfterDelay(binding, request, mount, sourceClock)",
        "CreateEffect(binding, request, mount, sourceClock)",
        "PlayRecoveredParticleSystems(systems)",
        '"P_fxui_endminm003_overview_01"',
        "BindOverview02SourceClock(",
        "MarkOverview02CompatibilityStart(instance.transform)",
        "source_post_effect_startup_failed",
        "source_post_clock_bind_rejected",
        "reportedFailureKeys.Add(key)",
        "Keep particle delays on the selection/body timeline",
        "system.Play(true)",
    ), "overview-02 split post/particle clocks")
    for forbidden in (
        "EndminfSmoke20PresentationAdvanceSeconds",
        "EndminfSmoke20MaterialName",
        "IsEndminfSmoke20(",
        "system.Simulate(",
    ):
        if forbidden in spawner:
            raise RuntimeError(
                "video-fitted M20 particle timing remains in runtime: " +
                forbidden
            )
    if spawner.count("system.Play(true)") != 1:
        raise RuntimeError(
            "recovered particle startup no longer follows one authored-time path"
        )
    create = spawner[
        spawner.index("private void CreateEffect("):
        spawner.index("private bool StartRecoveredLegacyAnimations(")
    ]
    if not (
        create.index("instance.SetActive(true);") <
        create.index("StartRecoveredLegacyAnimations(") <
        create.index("PlayRecoveredParticleSystems(systems);") <
        create.index("BindOverview02SourceClock(")
    ):
        raise RuntimeError(
            "source post seed is not bound after recovered effect startup")
    elapsed_evaluator = clock[
        clock.index("private static bool TryGetAuthenticatedSourcePostElapsed("):
        clock.index("public static bool TryEvaluateOpeningStrip(")
    ]
    if "TryGetAutomaticOverviewStartSeconds" in elapsed_evaluator:
        raise RuntimeError(
            "source post evaluator re-polls the body Animator instead of "
            "advancing the one-shot EffectInstance seed")
    shader = SHADER.read_text(encoding="utf-8")
    require_tokens(shader, (
        EXPECTED_ACTIVE_FRAGMENT_DXBC_SHA256,
        "float4 SampleEndminfSceneLod0(float2 uv)",
        "float effectivePower)",
        "radialIntensity * 0.5",
        "radialIntensity * 1.5",
        "radialIntensity * 2.0",
        "radialIntensity * 2.5",
        "accumulated * 0.166666672",
        "_EndminfVisualCompatibilityParams.w",
        "float3 bloom = max(tex2D(_BloomTex, presentUv).rgb, 0.0)",
        "source.rgb + bloom * bloomIntensity",
    ), "presentation shader")
    helper = re.search(
        r"float3 SampleEndminfRecoveredRadial\(.*?\n\s*}\n\n\s*float3 DecodeEndminfUberBloomInput",
        shader,
        re.DOTALL,
    )
    if helper is None:
        raise RuntimeError("could not isolate Effect-02 scene-warp helper")
    if "_BloomTex" in helper.group(0):
        raise RuntimeError("Effect-02 warped taps incorrectly resample bloom")
    if "chromaticIntensity" in helper.group(0):
        raise RuntimeError("active radial-only Uber helper still splits RGB taps")

    return {
        "status": (
            "verified_exact_serialized_source_curves_native_apply_center_"
            "and_active_radial_uber_kernel_source_seed_authenticated"
        ),
        "clipSha256": EXPECTED_CLIP_SHA256,
        "sourceCurvePayloadSha256": EXPECTED_SOURCE_CURVE_PAYLOAD_SHA256,
        "combinedFragmentDxbcSha256": EXPECTED_COMBINED_FRAGMENT_DXBC_SHA256,
        "activeFragmentDxbcSha256": EXPECTED_ACTIVE_FRAGMENT_DXBC_SHA256,
        "curveCount": len(bindings),
        "runtime": {
            "radialPower": "serialized_constant_curve_1.0",
            "combinedPowerBase": 1.0,
            "combinedMode": 6,
            "singleMode": 3,
            "ordinaryCenterSpace": "viewport_0_to_1",
            "farOffscreenCenterTestSpace": "signed_viewport",
            "postSourceGraphicsFormat": "R16G16B16A16_SFloat",
            "bloomGraphicsFormat": "B10G11R11_UFloatPack32",
            "averageSteps": [0, 0],
            "publicUnityCurveTransport": "unscaled_serialized_values",
            "sourcePostSeedAuthenticated": True,
            "triggerContractSchema": trigger["schema"],
            "sourcePostProgressionTransport": (
                "one-shot raw length*normalizedTime seed plus scaled Unity "
                "Time.timeAsDouble delta while the started effect root remains alive"
            ),
            "retailEffectTickDomainExact": False,
            "retailSceneColorChronologyExact": False,
            "retailPresentationExact": False,
            "presentationAdmitted": True,
            "particleClock": "authored source delay and selection/body timeline",
        },
        "boundary": (
            "The exact serialized cubic scalar curves, constant radial-power "
            "curve, native MonoBehaviour field/apply identities, ordinary/"
            "far-offscreen native center packing, "
            "native mode/power packing, the captured active radial-only Uber "
            "kernel, source-only warp, separate bloom sampling order, exact "
            "FromOveview state entry, post-start binding order, and one-shot "
            "raw length*normalizedTime seed are verified. The exact curves "
            "are admitted only behind their own selector and a live, "
            "generation-guarded effect root. The older combined "
            "radial/chromatic variant remains asset evidence, not the active "
            "peak presentation. The lab uses Unity's scaled public engine "
            "clock after the exact seed; the retail EffectInstance tick "
            "domain, SceneColor chronology, and complete presentation/binding "
            "ABI remain unresolved. This does not claim full retail clock or "
            "render-pipeline equivalence."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))

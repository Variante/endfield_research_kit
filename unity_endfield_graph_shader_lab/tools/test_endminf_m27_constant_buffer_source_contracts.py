from __future__ import annotations

import hashlib
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BYTECODE = ROOT / "tools" / "original_dxbc_exact" / "bytecode"
TRANSFORM = (
    ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Runtime"
    / "Rendering"
    / "EndfieldRecoveredDeferredTransformVariablesContract.cs"
)
TRANSFORM_OWNER = TRANSFORM.with_name(
    "EndfieldRecoveredDeferredTransformVariables.cs"
)
GLOBALS = TRANSFORM.with_name(
    "EndfieldRecoveredShaderVariablesGlobalContract.cs"
)
GLOBALS_OWNER = TRANSFORM.with_name(
    "EndfieldRecoveredShaderVariablesGlobal.cs"
)
GENERATIVE = TRANSFORM.with_name(
    "EndfieldRecoveredEndminfM27GenerativeExactRuntime.cs"
)
PIPELINE = TRANSFORM.with_name("HGCompatRenderPipeline.cs")
GLOBALS_VERIFIER = (
    ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Editor"
    / "CharacterRecovery"
    / "EndfieldRecoveredShaderVariablesGlobalBatchVerifier.cs"
)
BINDING_POLICY = TRANSFORM.with_name(
    "EndfieldRecoveredDeferredResolverBindingPolicy.cs"
)

EXPECTED_HASHES = {
    "endminf_m27_hgbuffer_vs.dxbc":
        "c0266e7fac0046c18ef9ce4ca229873284198d3b2202af0e2db86d073dd57c3c",
    "endminf_m27_hgbuffer_ps.dxbc":
        "92d80a93add9c714daeb265a66d3fe6e841c32825728d6af4268cede13c0c44e",
}

EXPECTED_READS = {
    "endminf_m27_hgbuffer_vs.dxbc": {
        (0, 32): "xyzw",
        (0, 33): "xyzw",
        (0, 34): "xyzw",
        (0, 35): "xyzw",
        (0, 44): "xyz",
        (0, 57): "xyw",
        (0, 58): "xyw",
        (0, 59): "xyw",
        (0, 60): "xyw",
        (0, 81): "xyz",
        (1, 19): "zw",
    },
    "endminf_m27_hgbuffer_ps.dxbc": {
        (0, 0): "z",
        (0, 1): "z",
        (0, 2): "z",
        (0, 24): "xyzw",
        (0, 25): "xyzw",
        (0, 26): "xyzw",
        (0, 27): "xyzw",
        (0, 44): "xyz",
        (1, 0): "zw",
        (1, 4): "w",
        (1, 26): "xy",
        (1, 27): "y",
        (1, 103): "xyzw",
        (1, 105): "xyzw",
        (3, 0): "xzw",
        (3, 1): "xw",
        (3, 2): "w",
        (3, 3): "xyw",
        (3, 4): "xyz",
        (3, 7): "xz",
        (3, 8): "xyzw",
        (3, 11): "xyzw",
        (3, 12): "xyzw",
        (3, 22): "x",
        (3, 24): "xyzw",
        (3, 25): "xyzw",
        (3, 26): "xyzw",
        (3, 27): "xyz",
        (3, 28): "yw",
        (3, 29): "xyz",
        (3, 30): "xyz",
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _find_fxc() -> Path | None:
    kits = Path(r"C:\Program Files (x86)\Windows Kits\10\bin")
    candidates = sorted(
        kits.glob("*/x64/fxc.exe"),
        reverse=True,
    )
    return candidates[0] if candidates else None


def _read_set(disassembly: str) -> dict[tuple[int, int], str]:
    lanes: dict[tuple[int, int], set[str]] = {}
    for match in re.finditer(r"cb([013])\[(\d+)\]\.([xyzw]+)", disassembly):
        key = (int(match.group(1)), int(match.group(2)))
        lanes.setdefault(key, set()).update(match.group(3))
    order = "xyzw"
    return {
        key: "".join(component for component in order if component in value)
        for key, value in lanes.items()
    }


class EndminfM27ConstantBufferSourceContractsTest(unittest.TestCase):
    def test_hash_pinned_dxbc_read_inventory(self) -> None:
        fxc = _find_fxc()
        if fxc is None:
            self.skipTest("Windows SDK fxc.exe is unavailable")
        for name, expected in EXPECTED_READS.items():
            path = BYTECODE / name
            self.assertEqual(_sha256(path), EXPECTED_HASHES[name])
            result = subprocess.run(
                [str(fxc), "/dumpbin", "/nologo", str(path)],
                check=True,
                capture_output=True,
                text=True,
                errors="replace",
            )
            self.assertEqual(_read_set(result.stdout), expected)

    def test_b0_source_math_and_temporal_gate_are_explicit(self) -> None:
        source = TRANSFORM.read_text(encoding="utf-8")
        for token in (
            "camera.nonJitteredProjectionMatrix",
            "viewNoTranslation.m03 = 0.0f",
            "viewNoTranslation.m13 = 0.0f",
            "viewNoTranslation.m23 = 0.0f",
            "nonJitteredGpuProjection * viewNoTranslation",
            "PreviousNonJitteredViewNoTranslationProjectionFirstVector",
            "PreviousCameraPositionVector",
            "previousFrameHistoryReady",
            "previous rows from the current frame",
            "public static bool TryEvaluateHistory(",
            "history.lastPublishedFrame == frame - 1",
            "public static void CommitHistory(",
        ):
            self.assertIn(token, source)

        owner = TRANSFORM_OWNER.read_text(encoding="utf-8")
        for token in (
            ".CameraHistoryState>",
            ".TryEvaluateHistory(",
            "CommitHistory(",
            "history.nonJitteredViewNoTranslationProjection",
            "history.cameraPosition",
            "currentM27SourceReady = true",
            "currentM27SourceReady = false",
        ):
            self.assertIn(token, owner)

        pipeline = PIPELINE.read_text(encoding="utf-8")
        publish = pipeline.index(
            "if (EndfieldRecoveredDeferredTransformVariables.IsRequested)"
        )
        owner_gate = pipeline.index(
            "if (recoveredEndminfLitEffectOwnerActive", publish
        )
        self.assertIn("PrepareAndPublish", pipeline[publish:owner_gate])

        policy = BINDING_POLICY.read_text(encoding="utf-8")
        self.assertIn(
            "EndfieldRecoveredEndminfM27GenerativeExactRuntime",
            policy,
        )

    def test_b1_source_equations_and_missing_registers_are_explicit(self) -> None:
        source = GLOBALS.read_text(encoding="utf-8")
        for token in (
            "destination[ScreenSizeVector] = new Vector4(",
            "camera.orthographic ? 1.0f : 0.0f",
            "Mathf.Pow(",
            "1.0f / m27Inputs.exposureAdaptation",
            "m27Inputs.vfxClockSeconds % 1024.0f",
            "M27 b1 c0.zw",
            "M27 b1 c4.w",
            "M27 b1 c19.zw",
            "M27 b1 c26.xy",
            "M27 b1 c27.y",
            "M27 b1 c103.xyzw",
            "M27 b1 c105.xyzw",
            "TryValidateM27SourceReadiness",
        ):
            self.assertIn(token, source)
        for readiness in (
            "targetDimensionsReady",
            "perspectiveCameraReady",
            "taaJitterReady",
            "physicalCameraMaterialMipBiasReady",
            "exposureReady",
            "vfxParams0Ready",
            "vfxParams2Ready",
        ):
            self.assertIn(f"public readonly bool {readiness};", source)

        owner = GLOBALS_OWNER.read_text(encoding="utf-8")
        self.assertIn(
            ".M27SourceInputs.CurrentTargetAndPerspectiveCameraOnly",
            owner,
        )
        self.assertIn(
            "CurrentM27SourceReady => currentM27SourceReady",
            owner,
        )
        self.assertNotIn("CurrentM27SourceReady => false", owner)

        for token in (
            "CurrentTargetPerspectiveExposureAndVFXPlayer(",
            "exposureAdaptation,",
            "exposureReady,",
            "vfxPlayerPosition,",
            "vfxClockSeconds,",
            "vfxParams0Ready,",
        ):
            self.assertIn(token, source)

        pipeline = PIPELINE.read_text(encoding="utf-8")
        for token in (
            "recoveredSourceClosedManualExposureRequested",
            "recoveredCurrentCameraExposureReady",
            "!recoveredLiveCharInfoAutoExposureRequested",
            "state.AdvanceSourceClosedNeutralProfile(deltaTime);",
            "TryResolveRecoveredVFXPlayerCenter",
            "recoveredVFXPlayerPosition",
            "recoveredVFXClockSeconds",
            "recoveredVFXParams0Ready",
            ".CurrentTargetPerspectiveExposureAndVFXPlayer(",
            "m27SourceInputs,",
        ):
            self.assertIn(token, pipeline)

        join = pipeline.index(
            ".CurrentTargetPerspectiveExposureAndVFXPlayer("
        )
        publish = pipeline.index(
            "recoveredShaderVariablesGlobal.PrepareAndPublish(", join
        )
        self.assertLess(join, publish)
        self.assertIn(
            "m27SourceInputs,",
            pipeline[publish:publish + 1200],
        )

        verifier = GLOBALS_VERIFIER.read_text(encoding="utf-8")
        for token in (
            "VerifyPartialM27OwnedSources(camera)",
            "exposureC27Populated",
            "vfxParams0C103Populated",
            "unresolvedTaaC19Zero",
            "unresolvedMipBiasC26Zero",
            "unresolvedAnchorC105Zero",
            "m27AdmissionRejected",
            '"c19.zw"',
        ):
            self.assertIn(token, verifier)

        static_audit = (
            ROOT / "tools" / "verify_endminf_m27_live_exact_abi.py"
        ).read_text(encoding="utf-8")
        for token in (
            "_unique_compact_assignment",
            "sourceClosedManualExposureReturnAudited",
            "sourceClosedManualExposureGateAudited",
            "uniqueAssignmentShapesAudited",
            "assignmentOrderAudited",
            "vfxLiveLabCarrierLaneAudited",
            "retail_selected_frame_HGVFX_player_identity_unproven",
        ):
            self.assertIn(token, static_audit)

    def test_generative_gate_checks_source_closure_before_binding(self) -> None:
        source = GENERATIVE.read_text(encoding="utf-8")
        gate = source.index("if (!transformVariablesM27SourceReady")
        bind = source.index("command.SetGlobalConstantBuffer")
        self.assertLess(gate, bind)
        self.assertIn(
            "M27 generative constant-buffer source closure failed",
            source,
        )
        self.assertIn("if (!destination.HasProperty(property))", source)
        self.assertIn("destination.SetTextureScale(", source)
        self.assertIn("destination.SetTextureOffset(", source)
        self.assertIn(
            'destination.SetInteger("_ParallaxMarchNum", marchCount)',
            source,
        )
        self.assertIn("Mathf.Floor(marchValue) != marchValue", source)
        self.assertIn(
            "_ParallaxMarchNum must be an exact non-negative uint",
            source,
        )


if __name__ == "__main__":
    unittest.main()

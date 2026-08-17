#!/usr/bin/env python3
"""Focused source gates for Li Zhiyan peak-particle clock and COLOR0 evidence."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldLiZhiyanActorComposedVisualCaptureHarness.cs"
)


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    required = (
        "endfield.lizhiyan-actor-composed-diagnostic-capture.v4",
        "float peakLocalSeconds = localSeconds - marker.sourceEffectDelay;",
        "peakLocalSeconds <= marker.sourceEffectDuration + ActiveEndpointEpsilon",
        "system.Simulate(Mathf.Max(0f, peakLocalSeconds), false, true, true);",
        "BuildPeakParticleColorSamples(bundle, localSeconds)",
        "public long particleRendererPathId;",
        "public int bakedColorCount;",
        "public float colorAlphaMin;",
        "public float colorAlphaMax;",
        "public float colorAlphaMean;",
    )
    for token in required:
        assert token in text, f"missing peak timing/COLOR0 gate: {token}"

    stale = "system.Simulate(Mathf.Max(0f, localSeconds), false, true, true);"
    assert stale not in text, "peak particles still sample the actor-local clock directly"
    print("Li Zhiyan actor-composed peak timing source gates passed: 1")


if __name__ == "__main__":
    main()

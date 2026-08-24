#!/usr/bin/env python3
"""Build the bounded 60 Hz reference-window contract for Endminf M28.

This deliberately separates exact authored particle clocks from provisional
retail-video frame ownership.  The recordings contain several overlapping
amber consumers, so a raw pixel in the authored interval is not M28 evidence.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "unity_endfield_graph_shader_lab"
REPORT = ROOT / "reports/assets/character_recovery/endminf_m28_reference_windows.json"
REFERENCE_CONFIG = LAB / "config/reference_video_sequences.json"
OVERVIEW_ROOT = (
    LAB
    / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Effects/Overview"
)

TARGETS = (
    {
        "id": "overview03_glow_particle10",
        "prefab": "P_fxui_endminm003_overview_03.prefab",
        "hierarchy": "all/glow/Particle System (10)",
        "name": "Particle System (10)",
        "expectedDelay": 2.9,
        "expectedLifetime": 0.35,
        "expectedStartSize": 0.13,
        "captureStartTick": 168,
        "captureEndTickInclusive": 200,
    },
    {
        "id": "overview02_particle9",
        "prefab": "P_fxui_endminm003_overview_02.prefab",
        "hierarchy": "all/Particle System (9)",
        "name": "Particle System (9)",
        "expectedDelay": 4.4,
        "expectedLifetime": 1.0,
        "expectedStartSize": 0.3,
        "captureStartTick": 258,
        "captureEndTickInclusive": 330,
    },
)

RECORDINGS = (
    (
        "endminf_overview_2026-08-21",
        "endminf_overview_start_and_loop",
        "scratch/character_recovery/reference_sequences/endminf_overview_2026-08-21/endminf/endminf_overview_start_and_loop/sequence.json",
        False,
    ),
    (
        "endminf_overview_no_framegen_2026-08-24",
        "endminf_overview_start_and_loop_no_framegen",
        "scratch/character_recovery/reference_sequences/endminf_overview_no_framegen_2026-08-24/endminf/endminf_overview_start_and_loop_no_framegen/sequence.json",
        True,
    ),
)


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root must be an object: {path}")
    return value


def scalar(block: str, section: str, field: str) -> float:
    section_match = re.search(
        rf"(?m)^  {re.escape(section)}:\s*$([\s\S]*?)(?=^  [A-Za-z][^\n]*:\s*$|\Z)",
        block,
    )
    require(section_match is not None, f"missing section {section}")
    field_match = re.search(
        rf"(?m)^    {re.escape(field)}:\s*$([\s\S]*?)(?=^    [A-Za-z_][^\n]*:\s*$|\Z)",
        section_match.group(1),
    )
    require(field_match is not None, f"missing field {section}.{field}")
    value_match = re.search(r"(?m)^      scalar: ([^\s]+)\s*$", field_match.group(1))
    require(value_match is not None, f"missing scalar {section}.{field}")
    return float(value_match.group(1))


def simple_number(block: str, field: str) -> float:
    match = re.search(rf"(?m)^  {re.escape(field)}: ([^\s]+)\s*$", block)
    require(match is not None, f"missing field {field}")
    return float(match.group(1))


def parse_target(target: dict) -> dict:
    path = OVERVIEW_ROOT / target["prefab"]
    text = path.read_text(encoding="utf-8-sig")
    headers = list(re.finditer(r"(?m)^--- !u!(\d+) &(\d+)\s*$", text))
    documents: dict[int, tuple[int, str]] = {}
    for index, header in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        documents[int(header.group(2))] = (int(header.group(1)), text[header.end() : end])

    game_objects = [
        (file_id, body)
        for file_id, (type_id, body) in documents.items()
        if type_id == 1
        and re.search(rf"(?m)^  m_Name: {re.escape(target['name'])}\s*$", body)
    ]
    require(len(game_objects) == 1, f"target GameObject is not unique: {target['hierarchy']}")
    game_object_id, game_object = game_objects[0]
    component_ids = [int(value) for value in re.findall(r"component: \{fileID: (\d+)\}", game_object)]
    particles = [(file_id, documents[file_id][1]) for file_id in component_ids if documents[file_id][0] == 198]
    renderers = [(file_id, documents[file_id][1]) for file_id in component_ids if documents[file_id][0] == 199]
    require(len(particles) == 1 and len(renderers) == 1, "particle/renderer component tuple drifted")
    particle_id, particle = particles[0]
    renderer_id, renderer = renderers[0]

    delay_match = re.search(r"(?ms)^  startDelay:\s*.*?^    scalar: ([^\s]+)\s*$", particle)
    require(delay_match is not None, "missing startDelay scalar")
    delay = float(delay_match.group(1))
    lifetime = scalar(particle, "InitialModule", "startLifetime")
    start_size = scalar(particle, "InitialModule", "startSize")
    require(math.isclose(delay, target["expectedDelay"], abs_tol=1e-7), "startDelay drifted")
    require(math.isclose(lifetime, target["expectedLifetime"], abs_tol=1e-7), "lifetime drifted")
    require(math.isclose(start_size, target["expectedStartSize"], abs_tol=1e-7), "startSize drifted")

    emission = re.search(r"(?ms)^  EmissionModule:\s*(.*?)(?=^  SizeModule:)", particle)
    require(emission is not None, "missing EmissionModule")
    emission_text = emission.group(1)
    checks = {
        "rateOverTime": r"(?ms)^    rateOverTime:\s*.*?^      scalar: 0\s*$",
        "rateOverDistance": r"(?ms)^    rateOverDistance:\s*.*?^      scalar: 0\s*$",
        "singleBurst": r"(?m)^    m_BurstCount: 1\s*$",
        "burstTimeZero": r"(?m)^      time: 0\s*$",
        "burstCountOne": r"(?ms)^      countCurve:\s*.*?^        scalar: 1\s*$",
        "oneCycle": r"(?m)^      cycleCount: 1\s*$",
        "probabilityOne": r"(?m)^      probability: 1\s*$",
    }
    require(all(re.search(pattern, emission_text) for pattern in checks.values()), "burst tuple drifted")

    source_enabled_match = re.search(r"(?m)^  m_Enabled: (\d+)\s*$", renderer)
    require(source_enabled_match is not None, "renderer m_Enabled missing")
    vertex_streams = re.search(r"(?m)^  m_VertexStreams: ([0-9A-Fa-f]+)\s*$", renderer)
    require(vertex_streams is not None, "renderer vertex streams missing")

    start_tick = round(delay * 60)
    lifetime_ticks = round(lifetime * 60)
    require(math.isclose(delay * 60, start_tick, abs_tol=1e-5), "delay is not integral at 60 Hz")
    require(math.isclose(lifetime * 60, lifetime_ticks, abs_tol=1e-5), "lifetime is not integral at 60 Hz")
    return {
        "id": target["id"],
        "effectRoot": Path(target["prefab"]).stem,
        "hierarchy": target["hierarchy"],
        "retainedPrefab": str(path.relative_to(ROOT)).replace("\\", "/"),
        "retainedPrefabSha256": sha256(path),
        "retainedComponentIds": {
            "gameObject": game_object_id,
            "particleSystem": particle_id,
            "particleSystemRenderer": renderer_id,
        },
        "authoredParticleClock": {
            "fps": 60,
            "startDelaySeconds": delay,
            "startDelayTick": start_tick,
            "lifetimeSeconds": lifetime,
            "lifetimeTicks": lifetime_ticks,
            "liveIntervalSecondsHalfOpen": [delay, delay + lifetime],
            "liveTicksInclusive": [start_tick, start_tick + lifetime_ticks - 1],
            "firstExpiredTick": start_tick + lifetime_ticks,
            "durationSeconds": simple_number(particle, "lengthInSec"),
            "simulationSpeed": simple_number(particle, "simulationSpeed"),
            "moveWithTransform": int(simple_number(particle, "moveWithTransform")),
            "looping": bool(simple_number(particle, "looping")),
            "playOnAwake": bool(simple_number(particle, "playOnAwake")),
            "randomSeed": int(simple_number(particle, "randomSeed")),
            "startSpeed": scalar(particle, "InitialModule", "startSpeed"),
            "startSize": start_size,
            "emission": {
                "rateOverTime": 0,
                "rateOverDistance": 0,
                "burstTimeSeconds": 0,
                "burstCount": 1,
                "cycleCount": 1,
                "probability": 1,
            },
        },
        "retainedRenderer": {
            "enabledAfterFailClosedAdmission": bool(int(source_enabled_match.group(1))),
            "renderMode": int(simple_number(renderer, "m_RenderMode")),
            "gpuInstancing": bool(simple_number(renderer, "m_EnableGPUInstancing")),
            "vertexStreamsHex": vertex_streams.group(1).lower(),
        },
        "captureSweep": {
            "ticksInclusive": [target["captureStartTick"], target["captureEndTickInclusive"]],
            "secondsInclusive": [
                target["captureStartTick"] / 60,
                target["captureEndTickInclusive"] / 60,
            ],
            "writtenFrameCount": target["captureEndTickInclusive"] - target["captureStartTick"] + 1,
            "guardTicks": [start_tick - 1, start_tick + lifetime_ticks],
        },
    }


def main() -> int:
    targets = [parse_target(target) for target in TARGETS]
    config = load(REFERENCE_CONFIG)
    recordings_by_id = {row["id"]: row for row in config["recordings"]}
    references = []
    for recording_id, segment_id, sequence_rel, frame_generation_disabled in RECORDINGS:
        recording = recordings_by_id[recording_id]
        segment = next(row for row in recording["segments"] if row["id"] == segment_id)
        comparison = segment["comparison"]
        sequence_path = LAB / sequence_rel
        sequence = load(sequence_path)
        source_path = (LAB / recording["source"]).resolve()
        require(sequence["source"]["sha256"] == sha256(source_path), f"video hash drifted: {recording_id}")
        body_anchor = int(comparison["bodyClipStartSourceFrame"])
        extracted_first = int(sequence["output"]["firstSourceFrame"])
        uncertainty = max(1, int(comparison.get("anchorUncertaintyFrames") or 0))
        windows = []
        for target in targets:
            first_tick, last_tick = target["authoredParticleClock"]["liveTicksInclusive"]
            first_source = body_anchor + first_tick
            last_source = body_anchor + last_tick
            windows.append(
                {
                    "target": target["id"],
                    "nominalSourceFramesOneBasedInclusive": [first_source, last_source],
                    "nominalExtractedFramesOneBasedInclusive": [
                        first_source - extracted_first + 1,
                        last_source - extracted_first + 1,
                    ],
                    "reviewBracketSourceFramesOneBasedInclusive": [
                        first_source - uncertainty,
                        last_source + uncertainty,
                    ],
                    "reviewBracketExtractedFramesOneBasedInclusive": [
                        first_source - extracted_first + 1 - uncertainty,
                        last_source - extracted_first + 1 + uncertainty,
                    ],
                }
            )
        references.append(
            {
                "recordingId": recording_id,
                "segmentId": segment_id,
                "frameGenerationDisabled": frame_generation_disabled,
                "source": recording["source"],
                "sourceSha256": sequence["source"]["sha256"],
                "resolution": recording["resolution"],
                "fps": 60,
                "bodyClipAnchorSourceFrameOneBased": body_anchor,
                "effectRootCoStartUncertaintyFrames": uncertainty,
                "firstExtractedSourceFrameOneBased": extracted_first,
                "windows": windows,
            }
        )

    report = {
        "schema": "endfield.endminf-m28-reference-windows.v1",
        "status": "authored_clocks_closed_reference_pixel_ownership_open",
        "scope": "The two M_fx_endminm_gfx_28 VFXRefract consumers only",
        "evidenceBoundary": {
            "closed": [
                "Both retained particle payloads use one deterministic burst particle, integral 60 Hz delay/lifetime clocks, zero speed, growth over lifetime, and the same mesh renderer stream.",
                "Both recordings are hash-pinned 60 Hz sources; the 2026-08-24 recording is the primary frame-generation-off reference.",
                "The capture sweeps and guard ticks are fixed independently of any observed pixel amplitude.",
            ],
            "open": [
                "The exact AnimeStudio four-root source stage is absent, so current exact source component PathIDs, serialized source m_Enabled, and material/mesh PPtr tuples are not revalidated here.",
                "No retail telemetry exposes the M28 effect-root clock. Mapping its authored ticks onto the body anchor is therefore a candidate pairing with the stated review uncertainty, not source ownership proof.",
                "No M28-only exact-vs-control render exists yet; raw reference pixels cannot establish M28 visibility or amplitude.",
            ],
        },
        "targets": targets,
        "referenceMappings": references,
        "fixedControlProtocol": {
            "simulationFps": 60,
            "captureEverySimulationTick": True,
            "comparisons": [
                "Run overview_03/all/glow/Particle System (10) exact versus only that renderer disabled over ticks 168..200.",
                "Run overview_02/all/Particle System (9) exact versus only that renderer disabled over ticks 258..330.",
            ],
            "mustRemainBitIdenticalAcrossEachPair": [
                "camera and 1920x1080 render target",
                "selection edge, body/effect clocks, and temporal-history reset",
                "all particle random seeds and simulation stepping",
                "overview_02/all/shitou (1) M21 exact small crystal",
                "overview_02/all/suikuai (1) admitted exact VFXRefract shards",
                "overview_02/all/suikuai (2) M27 LitEffect consumer",
                "every other renderer, post stage, exposure, bloom, TAA, and backdrop input",
            ],
            "admissionRule": "A changed pixel is attributable to one M28 consumer only inside its one-renderer exact-vs-control pair after deterministic equality of all fixed controls is proven. Reference similarity alone is insufficient.",
        },
        "pixelOwnershipCautions": [
            "The M28 mesh is a transparent distortion carrier; its retail contribution is displaced scene color, not an independently colored object that can be segmented from a still frame.",
            "The overview_03 interval overlaps the moving amber crystal/rock actor effect and bloom. The overview_02 interval overlaps M21 plus the 4.49-second suikuai (1) and M27 bursts. Bright amber pixels, rings, stones, and trails therefore do not identify M28.",
            "Disabling frame generation removes synthesized display frames but does not remove retail TAA, bloom, motion blur, exposure, body motion, or overlapping authored particles. The 2026-08-24 video is the preferred temporal reference, not a clean M28 layer.",
            "Never resize, brighten, retime, disable, or otherwise tune M21 overview_02/all/shitou (1) to compensate for an M28 mismatch.",
            "Do not subtract the two retail recordings from one another: their resolution, camera/body phase, UI sampling, and temporal histories differ, so the residual is not an M28 matte.",
        ],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"audit_endminf_m28_reference_windows: OK targets={len(targets)} recordings={len(references)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

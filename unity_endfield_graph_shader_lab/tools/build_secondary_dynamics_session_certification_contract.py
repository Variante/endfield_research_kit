#!/usr/bin/env python3
"""Build the pinned Endminf secondary-dynamics live-session contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "endfield.charinfo.secondary-dynamics-session-certification.v1"
SESSION_ID = "20260825T125815Z"
EXPECTED_GAME_BUILD = "endfield-2026-07-11-gameassembly-0c557367"
EXPECTED_TARGET_SHA256 = (
    "a9726459d9ab90cf01d7536a4250315e85ebfe12da493ac16f7bad3b68e7df99"
)
EXPECTED_GAME_ASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def build(session_root: Path) -> dict:
    required = {
        "session": session_root / "session.json",
        "writerSummary": session_root / "collected" / "summary.json",
        "inventory": session_root / "collected" / "inventory.json",
        "providerSummary": session_root / "secondary-dynamics" / "summary.json",
        "window": session_root / "secondary-dynamics" / "windows.jsonl",
    }
    missing = [str(path) for path in required.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing capture evidence: " + ", ".join(missing))
    if (session_root / "runtime.error").exists():
        raise ValueError("capture contains runtime.error")

    session = load_json(required["session"])
    writer = load_json(required["writerSummary"])
    provider = load_json(required["providerSummary"])
    inventory = load_json(required["inventory"])
    lines = [line for line in required["window"].read_text(encoding="utf-8").splitlines()
             if line.strip()]
    if len(lines) != 1:
        raise ValueError("capture must contain exactly one secondary-dynamics window")
    window = json.loads(lines[0])

    if session.get("sessionId") != SESSION_ID:
        raise ValueError("session ID differs from the pinned evidence")
    if session.get("providers") != 4:
        raise ValueError("capture did not select only the secondary-dynamics provider")
    if session.get("gameBuild") != EXPECTED_GAME_BUILD:
        raise ValueError("capture game build differs")
    if session.get("targetSha256") != EXPECTED_TARGET_SHA256:
        raise ValueError("capture Endfield.exe hash differs")
    if writer.get("complete") is not True or writer.get("dropped") != 0 or \
            writer.get("invalidRecords") != 0 or writer.get("writerError") is not False:
        raise ValueError("bounded writer did not complete cleanly")
    if provider.get("complete") is not True or provider.get("hooksInstalled") is not True or \
            provider.get("quiescentCleanup") is not True or provider.get("windowsCompleted") != 1:
        raise ValueError("secondary-dynamics provider did not complete cleanly")

    expected_window = {
        "windowId": 1,
        "clothUpdateCalls": 700,
        "crossFrameFalseCalls": 0,
        "crossFrameTrueCalls": 700,
        "crossFrameUnreadableCalls": 0,
        "crossFrameStable": True,
        "crossFrameValue": True,
        "teamDataGetterCalls": 2772,
        "relativeSlotOverflow": 0,
        "teamCount": 93,
        "allObservedRelativeFalse": True,
        "endminfFourOwnerCertification": False,
        "boundedComplete": True,
    }
    for key, expected in expected_window.items():
        if window.get(key) != expected:
            raise ValueError(f"window {key} differs: {window.get(key)!r} != {expected!r}")
    observations = window.get("observations")
    if not isinstance(observations, list) or len(observations) != 93:
        raise ValueError("window must contain 93 bounded TeamData observations")
    if any(row.get("falseCalls", 0) <= 0 or row.get("trueCalls") != 0
           for row in observations):
        raise ValueError("one or more TeamData lanes was not exclusively false")
    false_call_sum = sum(row["falseCalls"] for row in observations)
    if false_call_sum != window["teamDataGetterCalls"]:
        raise ValueError("TeamData observation counts do not sum to getter calls")
    warmup_calls = window["clothUpdateCalls"] - false_call_sum // 4
    if false_call_sum % 4 != 0 or warmup_calls != 7:
        raise ValueError("capture does not close the four-active-team cadence")

    artifacts = {row["path"]: row for row in inventory.get("artifacts", [])}
    for relative in (
        "session.json",
        "collected/summary.json",
        "secondary-dynamics/summary.json",
        "secondary-dynamics/windows.jsonl",
    ):
        if relative not in artifacts:
            raise ValueError(f"inventory omits {relative}")
        path = session_root / Path(relative)
        if artifacts[relative].get("sha256") != sha256(path):
            raise ValueError(f"inventory hash differs for {relative}")

    duration_ns = window["endNs"] - window["startNs"]
    if duration_ns <= 0:
        raise ValueError("window duration is not positive")

    return {
        "schema": SCHEMA,
        "status": "settings_observed_owner_identity_unresolved",
        "targetReady": False,
        "target": {
            "actorKey": "endminf",
            "sequence": "ui_overview_start_and_loop",
            "reference": "videos/2026-08-24_06-37-22.mkv",
            "sessionId": SESSION_ID,
            "gameBuild": EXPECTED_GAME_BUILD,
            "endfieldExeSha256": EXPECTED_TARGET_SHA256,
            "gameAssemblySha256": EXPECTED_GAME_ASSEMBLY_SHA256,
        },
        "artifactEvidence": {
            key: {
                "path": str(path.relative_to(session_root)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for key, path in required.items()
        },
        "window": {
            "startNs": window["startNs"],
            "endNs": window["endNs"],
            "durationNs": duration_ns,
            "clothUpdateCalls": window["clothUpdateCalls"],
            "crossFrameTrueCalls": window["crossFrameTrueCalls"],
            "crossFrameUnreadableCalls": window["crossFrameUnreadableCalls"],
            "teamDataGetterCalls": window["teamDataGetterCalls"],
            "uniqueTeamDataAddresses": window["teamCount"],
            "activeTeamLanesPerSettledCall": 4,
            "warmupClothUpdateCalls": warmup_calls,
            "relativeTrueCalls": 0,
            "relativeFalseCalls": false_call_sum,
            "relativeSlotOverflow": window["relativeSlotOverflow"],
        },
        "certification": {
            "certified": False,
            "useRelativeTransform": False,
            "useCrossFrameJob": True,
            "useAnimatorTransform": False,
            "writebackRoute": "TransformAccess",
        },
        "interpretation": {
            "crossFrame": (
                "All 700 ClothUpdate entry samples read MagicaManager "
                "UseCrossFrameJob=true with zero unreadable samples."
            ),
            "relativeTransform": (
                "After seven warm-up ClothUpdate calls, 2,772 reads equal four active "
                "TeamData lanes across 693 calls. Every one of the 93 addresses rotated "
                "through those active lanes remained false. The capture does not bind "
                "those rotating addresses to the four Endminf owners, so this observation "
                "cannot certify the target actor's useRelativeTransform value."
            ),
            "route": (
                "UseAnimatorTransform=false and TransformAccess writeback remain closed "
                "by the hash-gated transform-read native contract, not inferred from this capture."
            ),
        },
        "boundary": {
            "readOnly": True,
            "forcedD3D11": True,
            "frameGeneration": False,
            "operatorLabeledTargetWindow": True,
            "endminfFourOwnerCertification": False,
            "runtimeHookInstalled": True,
            "gameBehaviorModified": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    repo = Path(__file__).resolve().parents[2]
    parser.add_argument(
        "--session-root",
        type=Path,
        default=repo / "scratch" / "reverse_engineering" / "endfield_capture" / SESSION_ID,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo / "unity_endfield_graph_shader_lab" / "Assets" /
        "EndfieldGraphShaderLab" / "Generated" / "OriginalData" /
        "CharInfoPresentation" /
        "secondary_dynamics_session_certification_contract.json",
    )
    args = parser.parse_args()
    contract = build(args.session_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

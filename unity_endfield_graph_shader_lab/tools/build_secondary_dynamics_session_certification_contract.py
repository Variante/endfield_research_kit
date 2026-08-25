#!/usr/bin/env python3
"""Build an Endminf secondary-dynamics live-session contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
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
SESSION_ID_PATTERN = re.compile(r"^\d{8}T\d{6}Z$")


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


def require_schema(value: dict, expected: str, label: str) -> None:
    if value.get("schema") != expected:
        raise ValueError(
            f"{label} schema differs: {value.get('schema')!r} != {expected!r}"
        )


def build(session_root: Path, require_certified: bool = False) -> dict:
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
    if not isinstance(window, dict):
        raise ValueError("secondary-dynamics window must be one JSON object")

    require_schema(session, "endfieldCapture.session.v1", "session")
    require_schema(writer, "endfieldCapture.summary.v1", "writer summary")
    require_schema(provider, "endfieldCapture.secondaryDynamicsSummary.v1",
                   "secondary-dynamics summary")
    require_schema(inventory, "endfieldCapture.collection.v1", "inventory")
    require_schema(window, "endfieldCapture.secondaryDynamicsWindow.v1", "window")

    session_id = session.get("sessionId")
    if not isinstance(session_id, str) or not SESSION_ID_PATTERN.fullmatch(session_id):
        raise ValueError("session ID is not a UTC EndfieldCapture identifier")
    if session_root.name != session_id:
        raise ValueError("session directory and recorded session ID differ")
    if inventory.get("session") != session_id:
        raise ValueError("inventory session ID differs")
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

    if window.get("windowId") != 1:
        raise ValueError("capture must contain window 1")
    cloth_update_calls = window.get("clothUpdateCalls")
    if not isinstance(cloth_update_calls, int) or cloth_update_calls <= 0:
        raise ValueError("window has no ClothUpdate observations")
    if window.get("crossFrameFalseCalls") != 0 or \
            window.get("crossFrameTrueCalls") != cloth_update_calls or \
            window.get("crossFrameUnreadableCalls") != 0 or \
            window.get("crossFrameStable") is not True or \
            window.get("crossFrameValue") is not True:
        raise ValueError("window does not certify stable UseCrossFrameJob=true")
    if window.get("relativeSlotOverflow") != 0:
        raise ValueError("window overflowed the bounded TeamData observation table")
    if window.get("boundedComplete") is not True:
        raise ValueError("window is not bounded-complete")
    if window.get("allObservedRelativeFalse") is not True:
        raise ValueError("window observed useRelativeTransform=true")

    team_count = window.get("teamCount")
    getter_calls = window.get("teamDataGetterCalls")
    if not isinstance(team_count, int) or team_count < 4:
        raise ValueError("window observed fewer than four TeamData addresses")
    if not isinstance(getter_calls, int) or getter_calls <= 0:
        raise ValueError("window has no TeamData getter observations")
    observations = window.get("observations")
    if not isinstance(observations, list) or len(observations) != team_count:
        raise ValueError("TeamData observation count differs from teamCount")
    if any(not isinstance(row, dict) or row.get("falseCalls", 0) <= 0 or
           row.get("trueCalls") != 0 for row in observations):
        raise ValueError("one or more TeamData lanes was not exclusively false")
    addresses = [row.get("teamData") for row in observations]
    if any(not isinstance(address, str) or not address.startswith("0x")
           for address in addresses) or len(set(addresses)) != team_count:
        raise ValueError("TeamData addresses are missing or duplicated")
    false_call_sum = sum(row["falseCalls"] for row in observations)
    if false_call_sum != getter_calls:
        raise ValueError("TeamData observation counts do not sum to getter calls")
    warmup_calls = cloth_update_calls - false_call_sum // 4
    if false_call_sum % 4 != 0 or not 0 <= warmup_calls < cloth_update_calls:
        raise ValueError("capture does not close the four-active-team cadence")

    four_owner_certified = window.get("endminfFourOwnerCertification") is True
    universal_false = window.get("endminfCoveredByUniversalFalse") is True
    if four_owner_certified and team_count > 4 and not universal_false:
        raise ValueError(
            "multi-team certification lacks bounded universal-false coverage"
        )
    certification_mode = (
        "direct_four_owner_isolation"
        if four_owner_certified and team_count == 4
        else "bounded_universal_false"
        if four_owner_certified
        else "owner_identity_unresolved"
    )
    if require_certified and not four_owner_certified:
        raise ValueError("capture did not certify Endminf's four-owner target window")

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

    start_ns = window.get("startNs")
    end_ns = window.get("endNs")
    if not isinstance(start_ns, int) or not isinstance(end_ns, int):
        raise ValueError("window timestamps are missing")
    duration_ns = end_ns - start_ns
    if duration_ns <= 0:
        raise ValueError("window duration is not positive")

    return {
        "schema": SCHEMA,
        "status": (
            "target_session_certified"
            if four_owner_certified
            else "settings_observed_owner_identity_unresolved"
        ),
        "targetReady": four_owner_certified,
        "target": {
            "actorKey": "endminf",
            "sequence": "ui_overview_start_and_loop",
            "reference": "videos/2026-08-24_06-37-22.mkv",
            "sessionId": session_id,
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
            "startNs": start_ns,
            "endNs": end_ns,
            "durationNs": duration_ns,
            "clothUpdateCalls": cloth_update_calls,
            "crossFrameTrueCalls": window["crossFrameTrueCalls"],
            "crossFrameUnreadableCalls": window["crossFrameUnreadableCalls"],
            "teamDataGetterCalls": getter_calls,
            "uniqueTeamDataAddresses": team_count,
            "activeTeamLanesPerSettledCall": 4,
            "warmupClothUpdateCalls": warmup_calls,
            "relativeTrueCalls": 0,
            "relativeFalseCalls": false_call_sum,
            "relativeSlotOverflow": window["relativeSlotOverflow"],
        },
        "certification": {
            "certified": four_owner_certified,
            "useRelativeTransform": False,
            "useCrossFrameJob": True,
            "useAnimatorTransform": False,
            "writebackRoute": "TransformAccess",
        },
        "interpretation": {
            "crossFrame": (
                f"All {cloth_update_calls} ClothUpdate entry samples read "
                "MagicaManager UseCrossFrameJob=true with zero unreadable samples."
            ),
            "relativeTransform": (
                f"After {warmup_calls} warm-up ClothUpdate calls, {false_call_sum} reads "
                f"equal four active TeamData lanes across "
                f"{cloth_update_calls - warmup_calls} calls. Every one of the "
                f"{team_count} observed addresses remained false. Certification mode: "
                f"{certification_mode}."
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
            "endminfFourOwnerCertification": four_owner_certified,
            "certificationMode": certification_mode,
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
    parser.add_argument(
        "--require-certified",
        action="store_true",
        help="refuse to publish unless the target window certifies Endminf",
    )
    args = parser.parse_args()
    try:
        contract = build(
            args.session_root.resolve(), require_certified=args.require_certified
        )
    except (OSError, ValueError) as exc:
        print(f"error: session certification failed: {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build the fail-closed Endminf M28 offline-recovery boundary report."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
OUTPUT = REPO / "reports/assets/character_recovery/endminf_offline_recovery_boundary.json"
DEFAULT_LOG = REPO / "scratch/character_recovery/endminf_d3d11_renderdoc_lab/player_m28_03_census.log"
DEFAULT_CAPTURE = REPO / (
    "scratch/character_recovery/endminf_d3d11_renderdoc_lab/captures/"
    "endminf_m28_03_census_frame276.rdc"
)
INPUT_REPORTS = {
    "d3d11Migration": REPO / "reports/assets/character_recovery/endminf_d3d11_migration.json",
    "referenceWindows": REPO / "reports/assets/character_recovery/endminf_m28_reference_windows.json",
    "sourceContract": REPO / "reports/assets/character_recovery/endminf_m28_source_contract.json",
    "programContract": REPO / "reports/assets/character_recovery/endminf_m28_refract_program.json",
    "nativeInstancing": REPO / "reports/assets/character_recovery/endminf_m28_native_instancing.json",
    "consumerBoundary": REPO / "reports/assets/character_recovery/endminf_m28_consumer_boundary.json",
}
CENSUS_PATTERN = re.compile(
    r"^\[Endfield capture census\] path=(?P<path>.+); "
    r"material=(?P<material>.+); active=(?P<active>True|False); "
    r"enabled=(?P<enabled>True|False); particleTime=(?P<time>[0-9.]+); "
    r"particleCount=(?P<count>[0-9]+)$"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def parse_census(text: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in text.splitlines():
        match = CENSUS_PATTERN.match(line.strip())
        if not match:
            continue
        values = match.groupdict()
        rows.append({
            "path": values["path"],
            "material": values["material"],
            "active": values["active"] == "True",
            "enabled": values["enabled"] == "True",
            "particleTime": float(values["time"]),
            "particleCount": int(values["count"]),
        })
    return rows


def require_row(rows: list[dict[str, object]], suffix: str, material: str) -> dict[str, object]:
    matches = [row for row in rows if str(row["path"]).endswith(suffix)]
    if len(matches) != 1:
        raise ValueError(f"expected one census row ending {suffix!r}, found {len(matches)}")
    row = matches[0]
    if row["material"] != material:
        raise ValueError(f"{suffix}: expected material {material!r}, found {row['material']!r}")
    return row


def build(log_path: Path, capture_path: Path) -> dict[str, object]:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    required_log_lines = (
        "graphics=Direct3D11",
        "Applied source-recovered CharInfo presentation: Endministrator (endminf)",
        "Endfield lab RenderDoc capture completed: capture index 0.",
    )
    for line in required_log_lines:
        if line not in text:
            raise ValueError(f"capture log is missing {line!r}")
    count_match = re.search(
        r"\[Endfield capture census\] Endminf effect renderer count=(\d+), graphics=Direct3D11\.",
        text,
    )
    if count_match is None or int(count_match.group(1)) != 70:
        raise ValueError("expected the 70-renderer Endminf D3D11 census")

    rows = parse_census(text)
    if len(rows) != 70:
        raise ValueError(f"expected 70 parsed census rows, found {len(rows)}")
    m28_02 = require_row(rows, "overview_02__OverviewRuntime/all/Particle System (9)", "<null>")
    m28_03 = require_row(rows, "overview_03__OverviewRuntime/all/glow/Particle System (10)", "<null>")
    m21 = require_row(rows, "overview_02__OverviewRuntime/all/shitou (1)", "M_fx_endminm_gfx_21")
    shards = require_row(rows, "overview_02__OverviewRuntime/all/suikuai (1)", "M_fx_common_teleport_03")
    m27 = require_row(rows, "overview_02__OverviewRuntime/all/suikuai (2)", "<null>")

    if not (m28_03["active"] is True and m28_03["enabled"] is False
            and m28_03["particleCount"] == 1
            and 0.30 <= float(m28_03["particleTime"]) <= 0.35):
        raise ValueError("M28 overview_03 timing/fail-closed census drifted")
    if not (m28_02["active"] is True and m28_02["enabled"] is False):
        raise ValueError("M28 overview_02 fail-closed census drifted")
    if not (m21["active"] is True and m21["enabled"] is True):
        raise ValueError("protected M21 crystal control drifted")
    if not (shards["active"] is True and shards["enabled"] is True):
        raise ValueError("protected exact suikuai (1) control drifted")
    if not (m27["active"] is True and m27["enabled"] is False):
        raise ValueError("protected fail-closed M27 control drifted")

    report_inputs: dict[str, object] = {}
    payloads: dict[str, dict[str, object]] = {}
    for name, path in INPUT_REPORTS.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        payloads[name] = payload
        report_inputs[name] = {
            "path": relative(path),
            "sha256": sha256(path),
            "schema": payload.get("schema"),
            "status": payload.get("status"),
        }
    if payloads["nativeInstancing"].get("selection", {}).get("admitted") is not False:
        raise ValueError("native M28 selection unexpectedly became admitted")
    if payloads["programContract"].get("admissionDecision", {}).get("admitted") is not False:
        raise ValueError("M28 program unexpectedly became admitted")
    if payloads["consumerBoundary"].get("admissionDecision", {}).get("admitted") is not False:
        raise ValueError("M28 consumer unexpectedly became admitted")

    return {
        "schema": "endfield.endminf-offline-recovery-boundary.v1",
        "status": "offline_wall_reached_m28_remains_fail_closed",
        "scope": {
            "runtime": "local Unity standalone only",
            "graphicsDeviceType": "Direct3D11",
            "retailRuntimeAccess": "excluded_by_user_scope",
            "retailInjectionOrAttachment": "not_performed",
        },
        "inputs": report_inputs,
        "localCapture": {
            "role": "timing, instantiation, and fail-closed gate diagnostic only",
            "notRetailDrawEvidence": True,
            "log": {"path": relative(log_path), "bytes": log_path.stat().st_size, "sha256": sha256(log_path)},
            "renderDocCapture": {"path": relative(capture_path), "bytes": capture_path.stat().st_size, "sha256": sha256(capture_path)},
            "rendererCount": len(rows),
            "m28": {
                "overview02": m28_02,
                "overview03": m28_03,
                "conclusion": (
                    "The overview_03 M28 particle is instantiated and alive in its authored window, "
                    "while the renderer stays disabled with no material. The lab gate, rather than "
                    "missing timing or instantiation, prevents the draw."
                ),
            },
            "protectedControls": {
                "overview_02/all/shitou (1)": m21,
                "overview_02/all/suikuai (1)": shards,
                "overview_02/all/suikuai (2)": m27,
            },
            "knownStandaloneGaps": [
                "shared CharEffect stage parent unavailable",
                "owned physical-HDR/post scene-color chain disabled, so SceneMV fails closed",
                "post-Uber CharInfo world UI fails closed",
                "ShadowPlane temporary _EndfieldHGCameraColor target unavailable",
            ],
        },
        "closedOffline": [
            "exact M28 material and both serialized source tuples",
            "authored clocks and fixed-control reference windows",
            "both complete D3D11 program pairs and fixed-material fragment equivalences",
            "native built-in keyword identity, registry boundary, and instance-record shape",
            "local D3D11 timing and one-particle instantiation for overview_03",
            "continued fail-closed admission and unchanged protected controls",
        ],
        "irreducibleWithoutRetailDrawEvidence": [
            "which M28 D3D11 program pair the retail draw selects",
            "retail ParserBindChannels/default BLEND and TEXCOORD4 publication",
            "VertexSkinMatrices and unnamed per-object or per-instance record publication",
            "selected-frame LOD, time, frame, SceneColor, SceneMV, and depth descriptors",
            "retail render-target attachments, blend/depth/raster state, and complete PSO",
            "selected M28 pixels in both fixed-control 60 Hz windows",
        ],
        "decision": {
            "offlineWallReached": True,
            "m28Admitted": False,
            "projectMayContinueUsingD3D11": True,
            "stopReason": (
                "Static binaries, serialized assets, recovered shader programs, reference video, "
                "and the local Unity D3D11 player cannot establish retail draw-time state. The "
                "remaining discriminator requires retail D3D11 draw evidence, which is outside "
                "the permitted offline-only scope."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(args.log.resolve(), args.capture.resolve()), indent=2) + "\n"
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != payload:
            raise SystemExit(f"stale or missing report: {OUTPUT}")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(payload, encoding="utf-8")
    print(f"PASS Endminf offline recovery boundary: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

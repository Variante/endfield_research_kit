#!/usr/bin/env python3
"""Publish the fail-closed Endminf CharInfo start-camera/motion boundary."""
from __future__ import annotations
import json, sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
sys.path.insert(0, str(REPO))
from scripts.common import check_installed_native_inputs

GAME = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
META = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
ROOT = LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData"
OUT = REPO / "reports/assets/endminf_start_camera_motion_audit.json"

def load(path): return json.loads(path.read_text(encoding="utf-8-sig"))
def require(v, m):
    if not v: raise RuntimeError(m)

def main():
    native = check_installed_native_inputs(GAME, META); require(native.validated, native.detail)
    camera = load(ROOT / "CharInfoPresentation/charinfo_camera_track_contract.json")
    overview = load(ROOT / "CharInfoPresentation/charinfo_overview_camera_contract.json")
    gyro = load(ROOT / "CharInfoGyroscope/source_manifest.json")
    entry = next(x for x in camera["characters"] if x["actor"] == "endminf")
    static = overview["characters"]["chr_0003_endmin"]
    require(entry["endpoint_validation"]["ok"] and entry["tracked_dolly"]["m_PathPosition"] == 1.0, "Endminf dolly endpoint drifted")
    require(entry["path"]["waypoints"] == [
        {"position": [1.35, .519, 1.948], "roll": 0.0},
        {"position": [.5971327, .8897201, 2.4992352], "roll": 0.0},
        {"position": [0.0, .998, 3.5], "roll": 0.0}], "Endminf path drifted")
    require(gyro["actors"]["Endminf"]["serialized_entry_offsets_xy"] == [.24835543, -.1448596], "Endminf gyro entry drifted")
    motion = (REPO / "reports/assets/character_recovery/gacha_scene_mv_motion_contract.md").read_text(encoding="utf-8")
    for token in ("A2B10G10R10_UNormPack32", "DepthOfField, MotionBlur", "HorizontalBlurPreTAAU", "current/previous non-jittered camera constants"):
        require(token in motion, "motion contract missing " + token)
    report = {
      "schema":"endfield.endminf-start-camera-motion.v1", "status":"source_closed_endpoints_transition_unresolved",
      "native_gate":{"status":native.status,"gameassembly_sha256":native.gameassembly_sha256,"metadata_sha256":native.metadata_sha256},
      "camera_producer":{"track":entry["track_root"],"component":"CinemachineTrackedDolly","path":entry["path"],"authored_path_position":1.0,"settled_vcam":static["vcamOverview"],"look_at":static["lookAtOverview"],"lens":static["lens"]},
      "gyroscope_producer":{"driver":"Beyond.UI.UIGyroscopeEffect.PreLate","extension":"Beyond.UI.CinemachineGyroscopeEffect.Finalize","serialized_entry_offsets_xy":[.24835543,-.1448596],"replacement":"2-second OutQuad toward live cursor/controller input"},
      "motion_post":{"scene_mv_format":"A2B10G10R10_UNormPack32","scene_mv_clear":[.5,.5,0,0],"order":["opaque/CharacterNPR SceneMV writers","transparent VFX","DepthOfField","MotionBlur","optional HorizontalBlurPreTAAU","phase-2 post"],"history":"current/previous non-jittered camera constants; no fabricated history texture"},
      "play_mode":{"implemented_endpoint":True,"mode":"ENDFIELD_RECOVERED_CHARINFO_GYROSCOPE_MODE=serialized-entry","transition_implemented":False,"reason":"No source records the capture-time cursor/controller samples or the runtime driver that moves TrackedDolly.m_PathPosition from the near waypoint to 1.0. MotionBlur/TAA also require the original SceneMV MRT producers and history scheduling, which the lab does not implement."},
      "conclusion":"The extreme near-camera start is camera-side, not a fourth particle root: the exact three-waypoint weapon_overview dolly plus gyroscope entry/input transition feeds native SceneMV/MotionBlur/TAA. Only the authored endpoint is safe to reproduce currently."
    }
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2)); return 0
if __name__ == "__main__": raise SystemExit(main())

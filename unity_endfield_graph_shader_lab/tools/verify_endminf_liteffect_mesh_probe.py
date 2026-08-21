"""Fail-closed verifier for the exact LitEffect material-closure Mesh probe."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

REPORT = Path(__file__).resolve().parents[1] / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/ExternalUiEffects/endminf_liteffect_mesh_probe_evidence.json"
EXPECTED = {"name":"S_rock_small_1_017_02_lod2", "pathID":-8157825361227167527, "pathIDHex":"8EC9950E5461C8D9", "containerOffset":247138057, "vertexCount":29, "indexCount":72, "sha256":"55dd5a73380a0b64b8fc173cb636f58b0178e377e7fd4445362a4a6c0de2f58d"}
CHANNELS = {"POSITION3":87, "NORMAL3":87, "TANGENT4":116, "UV0_2":58, "UV1_2":58, "COLOR":None, "UV2_UV7":None, "skinning":None}
SOURCE = {"source":"StreamingAssets/maps/endfield_streamingassets_assets.json", "type":"Mesh", "name":EXPECTED["name"], "pathID":EXPECTED["pathID"], "offset":EXPECTED["containerOffset"], "sourceHash":"eb09b25a6c2dea5b"}

def verify(path: Path) -> dict:
    if not path.is_file(): raise RuntimeError(f"mesh export missing: {path}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != EXPECTED["sha256"]: raise RuntimeError("mesh export hash mismatch")
    d=json.loads(path.read_text(encoding="utf-8"))
    if d.get("m_Name",d.get("Name")) != EXPECTED["name"] or d.get("m_VertexCount") != 29 or len(d.get("m_Indices",[])) != 72: raise RuntimeError("mesh identity/count mismatch")
    lengths={"POSITION3":len(d.get("m_Vertices",[])),"NORMAL3":len(d.get("m_Normals",[])),"TANGENT4":len(d.get("m_Tangents",[])),"UV0_2":len(d.get("m_UV0",[])),"UV1_2":len(d.get("m_UV1",[]))}
    if lengths != {k:CHANNELS[k] for k in lengths}: raise RuntimeError("mesh channel width mismatch")
    if d.get("m_Colors") is not None or any(d.get(f"m_UV{i}") is not None for i in range(2,8)) or d.get("m_Skin") is not None or d.get("m_BindPose") or d.get("m_BoneNameHashes"): raise RuntimeError("unexpected absent channel or skinning evidence")
    return {"status":"verified","mesh":EXPECTED,"channels":CHANNELS,"source":SOURCE,"scope":"One exact Mesh in the LitEffect material closure; does not prove complete shader BindChannels. b3/b4 and BindChannels remain gaps.","nativeGate":"unavailable"}

def verify_report(report_path: Path, mesh_path: Path | None = None) -> dict:
    r=json.loads(report_path.read_text(encoding="utf-8"))
    actual=verify(mesh_path) if mesh_path else None
    if r.get("status")!="verified" or r.get("nativeGate")!="unavailable" or r.get("mesh")!=EXPECTED or r.get("channels")!=CHANNELS: raise RuntimeError("durable report pin mismatch")
    if r.get("source")!=SOURCE or "complete shader BindChannels" not in r.get("scope","") or "b3/b4" not in r["scope"]: raise RuntimeError("durable report scope/source mismatch")
    return actual or r

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("mesh_json",type=Path); ap.add_argument("--report",type=Path,default=REPORT); a=ap.parse_args()
    try: print(json.dumps(verify_report(a.report,a.mesh_json),indent=2,sort_keys=True)); return 0
    except (OSError,RuntimeError,ValueError,json.JSONDecodeError) as e: print(f"verification_failed: {e}"); return 1
if __name__ == "__main__": raise SystemExit(main())

"""Fail-closed verifier for the exact LitEffect material-closure Mesh probe."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

EXPECTED = {
    "name": "S_rock_small_1_017_02_lod2",
    "pathID": -8157825361227167527,
    "containerOffset": 247138057,
    "vertexCount": 29,
    "indexCount": 72,
    "sha256": "55dd5a73380a0b64b8fc173cb636f58b0178e377e7fd4445362a4a6c0de2f58d",
}

def verify(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError(f"mesh export missing: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != EXPECTED["sha256"]:
        raise RuntimeError(f"mesh export hash mismatch: expected {EXPECTED['sha256']}, got {digest}")
    data = json.loads(path.read_text(encoding="utf-8"))
    checks = {"name": data.get("m_Name", data.get("Name")), "vertexCount": data.get("m_VertexCount"),
              "indexCount": len(data.get("m_Indices", []))}
    if checks != {k: EXPECTED[k] for k in checks}:
        raise RuntimeError(f"mesh schema mismatch: expected { {k: EXPECTED[k] for k in checks} }, got {checks}")
    lengths = {"POSITION3": len(data.get("m_Vertices", [])), "NORMAL3": len(data.get("m_Normals", [])),
               "TANGENT4": len(data.get("m_Tangents", [])), "UV0_2": len(data.get("m_UV0", [])),
               "UV1_2": len(data.get("m_UV1", []))}
    expected = {"POSITION3": 87, "NORMAL3": 87, "TANGENT4": 116, "UV0_2": 58, "UV1_2": 58}
    if lengths != expected or data.get("m_Colors") is not None or any(data.get(f"m_UV{i}") is not None for i in range(2, 8)) or data.get("m_Skin") is not None or data.get("m_BindPose"):
        raise RuntimeError(f"mesh channel contract mismatch: {lengths}")
    return {"status": "verified", "mesh": EXPECTED, "channels": {**lengths, "COLOR": None, "UV2_UV7": None, "skinning": None},
            "scope": "one exact Mesh in the LitEffect material closure; does not prove complete shader BindChannels"}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mesh_json", type=Path)
    args = ap.parse_args()
    try: print(json.dumps(verify(args.mesh_json), indent=2, sort_keys=True)); return 0
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc: print(f"verification_failed: {exc}"); return 1

if __name__ == "__main__": raise SystemExit(main())

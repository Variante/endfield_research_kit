"""Regenerate the EC semantic-role contract and guarded formatter projection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
from scripts.game_data.levelscript_two_routes_native import open_selected_build
from scripts.game_data.memorypack.buff_ec_profiles_native import (
    CONTRACT_PATH, PROJECTION_PATH, derive,
)
from scripts.repo_paths import REPO_ROOT


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False).replace("\n", "\r\n") + "\r\n").encode("utf-8")


def regenerate(*, write=False, candidate_dir=None, opener=open_selected_build):
    if candidate_dir is not None:
        candidate_dir = Path(candidate_dir).resolve()
        if not any(candidate_dir.is_relative_to((REPO_ROOT / root).resolve()) for root in ("reports", "scratch", "tmp")):
            raise ValueError("buffEcProfiles.candidate-dir:must-be-local-generated-root")
    paths = [CONTRACT_PATH, PROJECTION_PATH]
    original = [p.read_bytes() for p in paths]
    reviewed, projection = map(json.loads, original)
    image, inputs = opener()
    current, projected = derive(image, inputs, reviewed, projection)
    _publication_gate(image, inputs)
    if [p.read_bytes() for p in paths] != original:
        raise ValueError("buffEcProfiles.publication:reviewed-inputs-changed-during-derivation")
    if write:
        CONTRACT_PATH.write_bytes(encoded(current))
        PROJECTION_PATH.write_bytes(encoded(projected))
    if candidate_dir is not None:
        candidate_dir.mkdir(parents=True, exist_ok=True)
        (candidate_dir / CONTRACT_PATH.name).write_bytes(encoded(current))
        (candidate_dir / PROJECTION_PATH.name).write_bytes(encoded(projected))
    return {"status": "regenerated", "written": bool(write),
            "profiles": {p["profile"]: len(p["events"]) for p in current["proof"]["profiles"]},
            "windowCount": len(projected["codeWindows"]),
            "projectionSchemaVersion": projected["schemaVersion"],
            "requiredRoleContract": CONTRACT_PATH.name}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--candidate-dir", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(regenerate(write=args.write, candidate_dir=args.candidate_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

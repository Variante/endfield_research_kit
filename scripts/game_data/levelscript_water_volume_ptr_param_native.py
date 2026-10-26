"""Authenticate the actual buffered raw-uint64 Param<WaterVolumePtr> child."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack import scalar_param_native as proof

SCHEMA = "endfield.levelscript-water-volume-ptr-param-native.v2"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_water_volume_ptr_param_native.json"


SOURCE_PROOF = proof.uint64_source


def validate_water_volume_ptr_param_native_contract(*, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None) -> dict[str, Any]:
    return proof.validate(Path(contract_path), schema=SCHEMA, type_name="Beyond.Gameplay.Core.WaterVolumePtr", codec_kind="Param<WaterVolumePtr>", game_root=game_root, prove_source=SOURCE_PROOF)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--game-root", type=Path)
    args = parser.parse_args()
    result = validate_water_volume_ptr_param_native_contract(contract_path=args.contract, game_root=args.game_root)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())

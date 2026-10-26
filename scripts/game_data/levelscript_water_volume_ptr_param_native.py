"""Authenticate the actual buffered raw-uint64 Param<WaterVolumePtr> child."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack import scalar_param_native as proof

SCHEMA = "endfield.levelscript-water-volume-ptr-param-native.v1"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_water_volume_ptr_param_native.json"


def _source(image: Any, source: dict[str, Any], offsets: dict[str, int]) -> None:
    label = "levelscriptWaterVolumePtrParam.source"
    cur, rem = offsets["currentPtr"], offsets["bufferLength"]
    expected = [b"\x48\x89\x5c\x24\x08", b"\x57", b"\x48\x83\xec\x20", b"\x83\x79" + bytes((rem, 8)), b"\x48\x8b\xf9", None,
                b"\x48\x8b\x5f" + bytes((cur,)), b"\xba\x08\x00\x00\x00", b"\x48\x8b\xcf", b"\x48\x8b\x1b", None,
                b"\x48\x8b\xc3", b"\x48\x8b\x5c\x24\x30", b"\x48\x83\xc4\x20", b"\x5f", b"\xc3"]
    proof.program(image, source["instructions"], expected, label)
    raw = bytes.fromhex(source["instructions"][5][1])
    proof.need(label, "guardOpcode", b"\x0f\x8c", raw[:2])
    proof.need(label, "guardSize", 6, len(raw))
    proof.call(image, [source["instructions"][10][0], source["instructions"][10][1], source["advance"]["pointerRva"]], label + ".advanceCall")
    proof.advance_source(image, source["advance"], offsets, label + ".advance")


def validate_water_volume_ptr_param_native_contract(*, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None) -> dict[str, Any]:
    return proof.validate(Path(contract_path), schema=SCHEMA, type_name="Beyond.Gameplay.Core.WaterVolumePtr", codec_kind="Param<WaterVolumePtr>", game_root=game_root, prove_source=_source)


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

"""Authenticate the actual buffered raw-int32 Param<GameplayTag> child."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack import scalar_param_native as proof

SCHEMA = "endfield.levelscript-gameplay-tag-param-native.v1"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_gameplay_tag_param_native.json"


def _source(image: Any, source: dict[str, Any], offsets: dict[str, int]) -> None:
    label = "levelscriptGameplayTagParam.source"
    cur, rem, adv, used = (offsets[name] for name in ("currentPtr", "bufferLength", "advancedCount", "consumed"))
    expected = [b"\x48\x89\x5c\x24\x08", b"\x48\x89\x74\x24\x10", b"\x57", b"\x48\x83\xec\x20", b"\x83\x79" + bytes((rem, 4)), b"\x48\x8b\xf9", None,
                b"\x48\x8b\x5f" + bytes((cur,)), b"\x8b\x1b", b"\x8b\x77" + bytes((rem,)), b"\x83\xee\x04", None,
                b"\x48\x83\x47" + bytes((cur, 4)), b"\x83\x47" + bytes((adv, 4)), b"\x83\x47" + bytes((used, 4)), b"\x89\x77" + bytes((rem,)),
                b"\x48\x8b\x74\x24\x38", b"\x8b\xc3", b"\x48\x8b\x5c\x24\x30", b"\x48\x83\xc4\x20", b"\x5f", b"\xc3"]
    proof.program(image, source["instructions"], expected, label)
    for index, opcode in ((6, b"\x0f\x8c"), (11, b"\x0f\x88")):
        raw = bytes.fromhex(source["instructions"][index][1])
        proof.need(label, "guardOpcode", opcode, raw[:2])
        proof.need(label, "guardSize", 6, len(raw))
    proof.need(label, "advanceAbsent", False, "advance" in source)


def validate_gameplay_tag_param_native_contract(*, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None) -> dict[str, Any]:
    return proof.validate(Path(contract_path), schema=SCHEMA, type_name="Beyond.Gameplay.Core.GameplayTag", codec_kind="Param<GameplayTag>", game_root=game_root, prove_source=_source)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--game-root", type=Path)
    args = parser.parse_args()
    result = validate_gameplay_tag_param_native_contract(contract_path=args.contract, game_root=args.game_root)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "validated" else 2


if __name__ == "__main__":
    raise SystemExit(main())

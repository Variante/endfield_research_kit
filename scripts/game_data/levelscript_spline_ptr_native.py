"""Authenticate the stored raw-Int32 SplinePtr Param and pooled path."""
from __future__ import annotations
if __name__=='__main__' and not __package__:
    raise SystemExit('Run python -m scripts.game_data.levelscript_spline_ptr_native')
import argparse,json
from pathlib import Path
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack import scalar_param_native as proof

SCHEMA='endfield.levelscript-spline-ptr-native.v3'
DEFAULT_CONTRACT=CONTRACTS_DIR/'levelscript_spline_ptr_native.json'
SOURCE_PROOF=proof.int32_advanced_source


def validate_spline_ptr_native_contract(*,contract_path=DEFAULT_CONTRACT,game_root=None,gameassembly=None,metadata=None):
    return proof.validate(Path(contract_path),schema=SCHEMA,type_name='Beyond.Gameplay.Core.SplinePtr',
        codec_kind='Param<SplinePtr>',game_root=game_root,prove_source=SOURCE_PROOF,gameassembly=gameassembly,metadata=metadata)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract',type=Path,default=DEFAULT_CONTRACT);parser.add_argument('--game-root',type=Path)
    parser.add_argument('--gameassembly',type=Path);parser.add_argument('--metadata',type=Path)
    args=parser.parse_args();result=validate_spline_ptr_native_contract(contract_path=args.contract,game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata)
    print(json.dumps(result,indent=2));return 0 if result['status']=='validated' else 2


if __name__=='__main__':raise SystemExit(main())

"""Authenticate the current Vector2 Param's source, stack and owned transfers."""
from __future__ import annotations
if not __package__:
    raise SystemExit('Run with python -m scripts.game_data.levelscript_vector2_param_native')

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack import primitive_param as proof

SCHEMA='endfield.levelscript-vector2-param-native.v1'
CONTRACT_PATH=CONTRACTS_DIR/'levelscript_vector2_param_native.json'
LABEL='levelscriptVector2ParamNative'


def validate_vector2_param_native_contract(*,contract_path=CONTRACT_PATH,game_root=None,gameassembly=None,metadata=None):
    return proof.validate_contract(contract_path=contract_path,schema=SCHEMA,primitive='vector2',label=LABEL,
        game_root=game_root,gameassembly=gameassembly,metadata=metadata)


def main():return proof.run_cli(validate_vector2_param_native_contract,CONTRACT_PATH)


if __name__=='__main__':raise SystemExit(main())

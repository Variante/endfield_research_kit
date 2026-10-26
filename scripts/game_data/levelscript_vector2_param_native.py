"""Authenticate the current Vector2 Param's source, stack and owned transfers.

Evidence and admission boundary:

Conditional Vector2 proof independently checks two Single loads, low-lane
packing, full QWORD return and both SIMD restores in actual/registered
readers. Matching live MethodInfo and typed setter split the same XY bits
into owned fields; vector extent alone supplies no source program or
default/provider/owner admission.
"""
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

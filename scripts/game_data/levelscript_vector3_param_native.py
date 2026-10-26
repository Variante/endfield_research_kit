"""Authenticate the current Vector3 Param's source, stack and owned transfers.

Evidence and admission boundary:

Conditional Vector3 component joins actual MethodInfo/raw typed reader to
disjoint hidden twelve-byte result and both owned copies, then pooled tail.
It admits no PosRot list/default path or enclosing owner solely from shared
vector layout.
"""
from __future__ import annotations
if not __package__:
    raise SystemExit('Run with python -m scripts.game_data.levelscript_vector3_param_native')

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack import primitive_param as proof

SCHEMA='endfield.levelscript-vector3-param-native.v1'
CONTRACT_PATH=CONTRACTS_DIR/'levelscript_vector3_param_native.json'
LABEL='levelscriptVector3ParamNative'


def validate_vector3_param_native_contract(*,contract_path=CONTRACT_PATH,game_root=None,gameassembly=None,metadata=None):
    return proof.validate_contract(contract_path=contract_path,schema=SCHEMA,primitive='vector3',label=LABEL,
        game_root=game_root,gameassembly=gameassembly,metadata=metadata)


def main():return proof.run_cli(validate_vector3_param_native_contract,CONTRACT_PATH)


if __name__=='__main__':raise SystemExit(main())

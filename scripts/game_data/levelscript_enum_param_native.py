"""Authenticate reviewed closed signed-Int32 enum Param components."""
from __future__ import annotations
if __name__=='__main__' and not __package__:
    raise SystemExit('Run python -m scripts.game_data.levelscript_enum_param_native')
import json
from pathlib import Path
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import native_validation_failure
from scripts.game_data.memorypack import primitive_param as proof

SCHEMA='endfield.levelscript-enum-param-native.v1'
LABEL='levelscriptEnumParamNative'
DEFAULT_CONTRACT=CONTRACTS_DIR/'levelscript_enum_param_native.json'


def validate_enum_param_native_contract(*,codec_kind=None,contract_path=DEFAULT_CONTRACT,game_root=None,gameassembly=None,metadata=None):
    component=codec_kind
    try:
        path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw);rows=fact['components']
        if (not rows or any(set(row)!={'codecKind','wrappedType','proof'} or not row['codecKind'].startswith('Param<')
                or not row['codecKind'].endswith('>') or not row['wrappedType'].startswith('Beyond.Gameplay.Actions.Param`1<')
                or not row['wrappedType'].endswith('>') for row in rows)
                or len({r['codecKind'] for r in rows})!=len(rows) or len({r['wrappedType'] for r in rows})!=len(rows)):
            raise ValueError(LABEL+'.contract:component-scope')
        selected=[row for row in rows if codec_kind is None or row['codecKind']==codec_kind]
        if not selected:raise ValueError(LABEL+'.contract:unproved-codec='+str(codec_kind))
        for row in selected:
            component=row['codecKind']
            audit=proof.validate_contract(contract_path=path,schema=SCHEMA,primitive='int',label=LABEL,
                codec_kind=component,value_type=row['wrappedType'][len('Beyond.Gameplay.Actions.Param`1<'):-1],
                game_root=game_root,gameassembly=gameassembly,metadata=metadata)
            if audit.get('status')!='validated':return {k:v for k,v in audit.items() if k not in ('codecKind','codecKinds')}
        if path.read_bytes()!=raw:raise ValueError(LABEL+'.contract:declaration changed during validation')
        return {**{k:v for k,v in audit.items() if k!='codecKind'},'codecKinds':[row['codecKind'] for row in selected],'memberCount':4}
    except (ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError) as error:
        audit=native_validation_failure(error,label=LABEL,source_path=contract_path);audit['component']=component
        return audit


if __name__=='__main__':raise SystemExit(proof.run_cli(validate_enum_param_native_contract,DEFAULT_CONTRACT))

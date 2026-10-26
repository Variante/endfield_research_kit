"""Authenticate reviewed one-byte null capabilities; positive Params stay separate."""
from __future__ import annotations
if __name__=='__main__' and not __package__:raise SystemExit('Run python -m scripts.game_data.levelscript_null_param_native')
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.memorypack.pooled_source_helper import check_unity_input
from scripts.game_data.memorypack import null_param as proof
SCHEMA='endfield.levelscript-null-param-native.v1'
LABEL='levelscriptNullParamNative'
DEFAULT_CONTRACT=CONTRACTS_DIR/'levelscript_null_param_native.json'

def _check_contract(fact):
    rows=fact['components']
    if (set(fact)!={'schema','status','nativeInputs','components'} or (fact['schema'],fact['status'])!=(SCHEMA,'exact-current-build')
            or set(fact['nativeInputs'])!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'} or not rows
            or any(set(r)!={'codecKind','valueType','proof'} or r['codecKind']!='Param<'+r['valueType'].rsplit('.',1)[-1]+'>' for r in rows)
            or len({r['codecKind'] for r in rows})!=len(rows) or len({r['valueType'] for r in rows})!=len(rows)):
        raise ValueError(LABEL+'.contract:component-shape')
    return fact

def _contract(path):return _check_contract(json.loads(Path(path).read_bytes()))


def _validate_native(image,fact,codec_kind=None):
    rows=[r for r in fact['components'] if codec_kind is None or r['codecKind']==codec_kind]
    if not rows:raise ValueError(LABEL+'.contract:unproved-codec='+str(codec_kind))
    for row in rows:
        actual=proof.derive(image,fact['nativeInputs'],row['valueType'])
        validate_claims(row['proof'],actual,label=LABEL+'.proof:'+row['codecKind']);validate_claims(actual,row['proof'],label=LABEL+'.declaration:'+row['codecKind'])
    return rows

def validate_null_param_native_contract(*,codec_kind=None,contract_path=DEFAULT_CONTRACT,game_root=None,gameassembly=None,metadata=None):
    try:
        path=Path(contract_path);raw=path.read_bytes();fact=_contract(path);pins=fact['nativeInputs']
        if (gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.native:both paths required')
        root=Path(game_root) if game_root is not None else None
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll' if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
        if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
        failed=check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        rows=_validate_native(open_native_image(gate.gameassembly,gate.metadata),fact,codec_kind)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail)
        failed=check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        if raw!=path.read_bytes():raise ValueError(LABEL+'.contract:declaration changed during validation')
        return dict(status='validated',codecKinds=[r['codecKind'] for r in rows],nullableMarker=255,positiveAdmitted=False,wireBytes=1,nativeInputs=pins,
            evidenceBoundary={r['codecKind']:r['proof']['evidenceBoundary'] for r in rows})
    except (ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError) as error:return native_validation_failure(error,label=LABEL,source_path=contract_path)

if __name__=='__main__':
    from scripts.game_data.memorypack.primitive_param import run_cli
    raise SystemExit(run_cli(validate_null_param_native_contract,DEFAULT_CONTRACT))

"""Authenticate closed ParamOutput storage components on the selected build.

Evidence and admission boundary:

Conditional closed outputs serialize signed Int32 paramTarget and pooled
path only, with independent complete callers, typed setters and null exits
before any shortcut. No T value is stored. Specialized event headers retain
their own native root/pool and enum gates; source destinations prove no
delivered output or runtime selection.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.memorypack.output_param import derive_output
from scripts.game_data.memorypack import pooled_source_helper

SCHEMA='endfield.levelscript-param-output-native.v1'
LABEL='levelscriptParamOutputNative'
DEFAULT_CONTRACT=CONTRACTS_DIR/'levelscript_param_output_native.json'


def validate_param_output_native_contract(*,codec_kind=None,contract_path=DEFAULT_CONTRACT,game_root=None,gameassembly=None,metadata=None):
    component=codec_kind
    try:
        path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw);pins=fact['nativeInputs'];components=fact['components']
        if (set(fact)!={'schema','status','nativeInputs','components','evidenceBoundary'}
                or (fact['schema'],fact['status'])!=(SCHEMA,'exact-current-build')
                or set(pins)!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'} or not components
                or any(set(row)!={'codecKind','wrappedType','proof'} or not row['codecKind'].startswith('ParamOutput<') for row in components)
                or len({row['codecKind'] for row in components})!=len(components)
                or len({row['wrappedType'] for row in components})!=len(components)):
            raise ValueError(LABEL+'.contract:identity-or-component-scope')
        selected=[row for row in components if codec_kind is None or row['codecKind']==codec_kind]
        if not selected:raise ValueError(LABEL+'.contract:unproved-codec='+str(codec_kind))
        if (gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.native:both paths required')
        root=Path(game_root) if game_root is not None else None
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
            gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll' if root else None,
            metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
        if gate.status!='validated':return {'status':gate.status,'detail':gate.detail}
        failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        dependency=pooled_source_helper.CONTRACT_PATH.read_bytes();image=open_native_image(gate.gameassembly,gate.metadata)
        for row in selected:
            component=row['codecKind']
            actual=derive_output(image,pins,row['wrappedType'])
            validate_claims(row['proof'],actual,label=LABEL+'.proof');validate_claims(actual,row['proof'],label=LABEL+'.declaration')
            if fact['evidenceBoundary']!=actual['evidenceBoundary']:raise ValueError(LABEL+'.contract:evidence-boundary')
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status!='validated':return {'status':after.status,'detail':'native inputs changed during validation: '+after.detail}
        failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        if path.read_bytes()!=raw or pooled_source_helper.CONTRACT_PATH.read_bytes()!=dependency:raise ValueError(LABEL+'.contract:declaration changed during validation')
        return {'status':'validated','codecKinds':[row['codecKind'] for row in selected],'pathEncoding':'int32-pool-index',
            'memberCount':2,'integerField':'paramTarget','nativeInputs':pins,'evidenceBoundary':fact['evidenceBoundary']}
    except (KeyError,IndexError,TypeError,ValueError,OSError,RuntimeError) as error:
        failure=native_validation_failure(error,label=LABEL,source_path=contract_path)
        failure['component']=component
        return failure


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codec-kind')
    for name in ('contract','game-root','gameassembly','metadata'):parser.add_argument('--'+name,type=Path,default=DEFAULT_CONTRACT if name=='contract' else None)
    args=parser.parse_args();audit=validate_param_output_native_contract(codec_kind=args.codec_kind,contract_path=args.contract,
        game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata)
    print(json.dumps(audit,indent=2));return 0 if audit['status']=='validated' else 2

if __name__=='__main__':raise SystemExit(main())

"""Authenticate independently typed Int32/UInt32/Single list Params and pooled paths."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import native_validation_failure, open_native_image
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.levelscript_reader_inputs import (
    reader_input_changes, snapshot_complete_reader_inputs, snapshot_string_pool_inputs,
)
from scripts.game_data import levelscript_int_list_native as int_list_native
from scripts.game_data.memorypack import numeric_list_sources as source, pooled_source_helper
from scripts.game_data.memorypack.reference_param_profile import derive_profile
from scripts.repo_paths import REPO_ROOT

SCHEMA = 'endfield.levelscript-numeric-list-param-native.v1'
LABEL = 'levelscriptNumericListParamNative'
CONTRACT_PATH = CONTRACTS_DIR/'levelscript_numeric_list_param_native.json'
DEPENDENCIES = ('levelscript_int_list_native.json', 'memorypack_pooled_string_reader_native.json',
                'memorypack_reader_clones_native.json', 'memorypack_utf8_source_helper_native.json')


def _contract(path):
    fact=json.loads(Path(path).read_bytes())
    if (set(fact)!={'schema','status','nativeInputs','components','evidenceBoundary'}
            or (fact['schema'],fact['status'])!=(SCHEMA,'exact-current-build')
            or set(fact['nativeInputs'])!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}
            or not isinstance(fact['components'],list) or not fact['components']):
        raise ValueError(LABEL+'.contract:identity-or-components')
    kinds=[]
    for row in fact['components']:
        if (set(row)!={'codecKind','elementType','profile','proof'}
                or row['elementType'] not in source.ELEMENTS
                or row['codecKind']!=source.ELEMENTS[row['elementType']][0]
                or set(row['profile'])-{'registration','composition','integerSlots','initializedHeader'}
                or not {'registration','composition','integerSlots'}<=row['profile'].keys()):
            raise ValueError(LABEL+'.contract:component-shape')
        kinds.append(row['codecKind'])
    if len(kinds)!=len(set(kinds)):
        raise ValueError(LABEL+'.contract:duplicate-codec')
    return fact


def _validate_native(image, fact, rows, dependency):
    if dependency['nativeInputs']!=fact['nativeInputs']:
        raise ValueError(LABEL+'.native:child-build-mismatch')
    # Int32 source and shared typed factory/provider/array/context programs are
    # authenticated once on this SAME opened image, not inferred from a name.
    int_list_native._validate_native(image,dependency)
    for row in rows:
        actual=source.derive(image,fact['nativeInputs'],row,dependency)
        validate_claims(row['proof'],actual,label=LABEL+'.proof:'+row['codecKind'])
        validate_claims(actual,row['proof'],label=LABEL+'.declaration:'+row['codecKind'])
        validate_claims(fact['evidenceBoundary'],actual['evidenceBoundary'],label=LABEL+'.boundary')
        validate_claims(actual['evidenceBoundary'],fact['evidenceBoundary'],label=LABEL+'.boundary-declaration')


def _gate(pins, *, game_root=None, gameassembly=None, metadata=None):
    if (gameassembly is None)!=(metadata is None):
        raise ValueError(LABEL+'.native:both-native-paths-required')
    root=Path(game_root)if game_root is not None else None
    return check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
        gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll'if root else None,
        metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat'if root else None)


def validate_numeric_list_param_native_contract(*, codec_kind=None, contract_path=CONTRACT_PATH,
                                                game_root=None, gameassembly=None, metadata=None):
    try:
        path=Path(contract_path);raw=path.read_bytes();fact=_contract(path);pins=fact['nativeInputs']
        rows=[r for r in fact['components']if codec_kind is None or r['codecKind']==codec_kind]
        if not rows:raise ValueError(LABEL+'.contract:unproved-codec='+str(codec_kind))
        gate=_gate(pins,game_root=game_root,gameassembly=gameassembly,metadata=metadata)
        if gate.status!='validated':
            return dict(status=gate.status,codecKinds=[],failedCheck='installed-native-inputs',detail=gate.detail)
        if failed:=pooled_source_helper.check_unity_input(gate.gameassembly,pins):
            return dict(codecKinds=[],failedCheck='UnityPlayer.dll',**failed)
        dependencies={name:(CONTRACTS_DIR/name).read_bytes()for name in DEPENDENCIES}
        dependency=json.loads(dependencies['levelscript_int_list_native.json'])
        _validate_native(open_native_image(gate.gameassembly,gate.metadata),fact,rows,dependency)
        after=_gate(pins,gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status!='validated':
            return dict(status=after.status,codecKinds=[],failedCheck='installed-native-inputs-bookend',detail=after.detail)
        if failed:=pooled_source_helper.check_unity_input(gate.gameassembly,pins):
            return dict(codecKinds=[],failedCheck='UnityPlayer.dll-bookend',**failed)
        if raw!=path.read_bytes()or any(body!=(CONTRACTS_DIR/name).read_bytes()for name,body in dependencies.items()):
            raise ValueError(LABEL+'.contract:declaration-or-dependency-changed-during-validation')
        return dict(status='validated',codecKinds=[r['codecKind']for r in rows],memberCount=4,rawSize=8,
                    pathEncoding='int32-pool-index',collectionCountEncoding='int32',constantNullCount=-1,
                    elementEncodings={r['codecKind']:source.ENCODINGS[r['elementType']]for r in rows},
                    wholeParamNullAdmitted=True,positiveConstantsAdmitted=True,nativeInputs=pins,
                    nativeSources={'GameAssembly.dll':str(Path(gate.gameassembly).resolve()),
                                   'global-metadata.dat':str(Path(gate.metadata).resolve())},
                    evidenceBoundary=fact['evidenceBoundary'])
    except (ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError)as error:
        return dict(codecKinds=[],**native_validation_failure(error,label=LABEL,source_path=contract_path))


class NumericListOperationError(ValueError):
    def __init__(self,detail):
        self.diagnostic=dict(validator=LABEL,gate='current-operation',
            expected='active selected-root/pool operation with fresh unchanged entry/exit proof',actual=str(detail)[:1400])
        super().__init__(str(detail))


class _CurrentNumericListParams:
    def __init__(self,proof,game_root,strings):
        self._proof=proof;self.game_root=Path(game_root).resolve();self.strings=strings;self.active=True
    def audit(self,kind,game_root,strings):
        if not self.active:raise NumericListOperationError('numeric-list.operation:closed')
        if game_root is None or Path(game_root).resolve()!=self.game_root or strings is not self.strings:
            raise NumericListOperationError('numeric-list.operation:wrong-root-or-pool')
        if kind is not None and kind not in self._proof['codecKinds']:
            raise NumericListOperationError('numeric-list.operation:unproved-codec='+str(kind))
        result=json.loads(json.dumps(self._proof))
        if kind is not None:
            result['codecKinds']=[kind]
            result['elementEncodings']={kind:result['elementEncodings'][kind]}
        return result


def prepared_numeric_list_audit(operation, *, codec_kind, game_root, strings):
    if not isinstance(operation,_CurrentNumericListParams):
        raise NumericListOperationError('numeric-list.operation:invalid-capability')
    return operation.audit(codec_kind,game_root,strings)


@contextmanager
def current_numeric_list_params(*,game_root,strings):
    if game_root is None or strings is None or not hasattr(strings,'root'):
        raise NumericListOperationError('numeric-list.operation:explicit-root-and-export-pool-required')
    root=Path(game_root).resolve();sources=snapshot_complete_reader_inputs()
    pool_root=Path(strings.root).parent;pool=snapshot_string_pool_inputs(pool_root)
    proof=validate_numeric_list_param_native_contract(game_root=root)
    if proof.get('status')!='validated' or set(proof.get('codecKinds',[]))!=set(r[0]for r in source.ELEMENTS.values()):
        raise NumericListOperationError('numeric-list.operation:enter:'+str(proof)[:1400])
    selected=proof['nativeSources']
    if (Path(selected['GameAssembly.dll']).resolve()!=root.parent/'GameAssembly.dll'
            or Path(selected['global-metadata.dat']).resolve()!=root/'il2cpp_data/Metadata/global-metadata.dat'):
        raise NumericListOperationError('numeric-list.operation:selected-pair-differs')
    operation=_CurrentNumericListParams(proof,root,strings)
    try:yield operation
    finally:
        operation.active=False
        after=validate_numeric_list_param_native_contract(gameassembly=Path(selected['GameAssembly.dll']),metadata=Path(selected['global-metadata.dat']))
        if proof!=after:raise NumericListOperationError('numeric-list.operation:exit-proof-drift:'+str(after)[:1400])
        current=snapshot_complete_reader_inputs()
        if sources!=current:
            raise NumericListOperationError('numeric-list.operation:reader-source-drift:'+str(reader_input_changes(sources,current)))
        if pool!=snapshot_string_pool_inputs(pool_root):
            raise NumericListOperationError('numeric-list.operation:string-pool-drift')


def derive_on_image(image,pins,dependency):
    """Re-derive every supported component on the caller's selected image.

    This returns a candidate. The caller owns input/source/declaration bookends
    before publication; it never opens an additional image.
    """
    if dependency['nativeInputs']!=pins:raise ValueError(LABEL+'.regenerate:child-build-mismatch')
    int_list_native._validate_native(image,dependency)
    rows=[]
    for element,(codec,*_)in source.ELEMENTS.items():
        row=dict(elementType=element,codecKind=codec,profile=derive_profile(image,
            'System.Collections.Generic.List`1<'+element+'>',initialized_header=element=='float'))
        row['proof']=source.derive(image,pins,row,dependency);rows.append(row)
    return dict(schema=SCHEMA,status='exact-current-build',nativeInputs=pins,components=rows,evidenceBoundary=source.BOUNDARY)


def regenerate(*,game_root=None,gameassembly=None,metadata=None,contract_path=CONTRACT_PATH,write=False):
    path=Path(contract_path);original=path.read_bytes()if path.is_file()else None
    pins=(_contract(path)['nativeInputs']if original is not None else json.loads(pooled_source_helper.CONTRACT_PATH.read_bytes())['nativeInputs'])
    gate=_gate(pins,game_root=game_root,gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':raise ValueError(LABEL+'.regenerate:'+gate.status+':'+gate.detail)
    if failed:=pooled_source_helper.check_unity_input(gate.gameassembly,pins):raise ValueError(str(failed))
    sources=snapshot_complete_reader_inputs()
    raw_deps={name:(CONTRACTS_DIR/name).read_bytes()for name in DEPENDENCIES}
    dependency=json.loads(raw_deps['levelscript_int_list_native.json'])
    image=open_native_image(gate.gameassembly,gate.metadata)
    if (Path(image.gameassembly).resolve()!=Path(gate.gameassembly).resolve()
            or Path(image.metadata_path).resolve()!=Path(gate.metadata).resolve()):
        raise ValueError(LABEL+'.regenerate:selected-image-differs')
    result=derive_on_image(image,pins,dependency)
    after=_gate(pins,gameassembly=image.gameassembly,metadata=image.metadata_path)
    if after.status!='validated'or pooled_source_helper.check_unity_input(image.gameassembly,pins):raise ValueError(LABEL+'.regenerate:native-input-drift')
    if any(body!=(CONTRACTS_DIR/name).read_bytes()for name,body in raw_deps.items()):raise ValueError(LABEL+'.regenerate:dependency-drift')
    if sources!=snapshot_complete_reader_inputs():raise ValueError(LABEL+'.regenerate:reader-source-drift')
    if original!=(path.read_bytes()if path.is_file()else None):raise ValueError(LABEL+'.regenerate:declaration-drift')
    if write:
        temporary=path.with_suffix(path.suffix+'.writing')
        temporary.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');temporary.replace(path)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-root',type=Path);parser.add_argument('--contract',type=Path,default=CONTRACT_PATH)
    parser.add_argument('--gameassembly',type=Path);parser.add_argument('--metadata',type=Path)
    parser.add_argument('--codec-kind');parser.add_argument('--regenerate',action='store_true');parser.add_argument('--write',action='store_true')
    parser.add_argument('--output-json',type=Path)
    args=parser.parse_args(argv)
    if args.write and not args.regenerate:parser.error('--write requires --regenerate')
    if args.output_json and not args.output_json.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):
        parser.error('--output-json must be below the repository reports/ directory')
    if args.regenerate:
        result=regenerate(game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata,contract_path=args.contract,write=args.write)
        audit=dict(status='validated',schema=result['schema'],codecKinds=[r['codecKind']for r in result['components']],written=args.write)
    else:audit=validate_numeric_list_param_native_contract(game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata,contract_path=args.contract,codec_kind=args.codec_kind)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True,exist_ok=True);args.output_json.write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(audit,indent=2));return 0 if audit['status']=='validated'else 2


if __name__=='__main__':raise SystemExit(main())

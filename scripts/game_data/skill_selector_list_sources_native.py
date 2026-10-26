"""Current null/empty selector-list parents, independent of action admission."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import native_validation_failure, open_native_image
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.memorypack import pooled_source_helper
from scripts.game_data.memorypack.skill_shared_sequence_sources import derive_selector_lists
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs
from scripts.repo_paths import REPO_ROOT

SCHEMA='endfield.skill-selector-list-sources-native.v2'
LABEL='skillSelectorListSourcesNative'
CONTRACT_PATH=CONTRACTS_DIR/'skill_selector_list_sources_native.json'
ELEMENTS={
    'target-postprocessor-list':'Beyond.Gameplay.Core.Selector+PostProcessor+Data',
    'target-validator-list':'Beyond.Gameplay.Core.Selector+Validator+Data',
}
BOUNDARY={
    'exact':'Selected EC member3 source joins each exact closed ReadPackable list request to the actual current reference source and canonical ListFormatter VAR/ABI/factory/provider/count/output programs for counts -1 and zero.',
    'conditional':'Initialized coherent closed reference-sharing contexts, successful selected provider/cache probes, normal helper/collector ABI, buffered disjoint storage; fresh allocations return the selected zeroed typed objects, or existing lists start empty with sufficient capacity.',
    'unresolved':'Positive list counts and every selector element grammar, live provider/default/override choice, runtime inflation, malformed/refill parity and whole enclosing actions remain unadmitted.',
}


def _contract(path=CONTRACT_PATH):
    fact=json.loads(Path(path).read_bytes())
    if (set(fact)!={'schema','status','nativeInputs','capabilities','proof','evidenceBoundary'}
            or (fact['schema'],fact['status'])!=(SCHEMA,'exact-current-build')
            or set(fact['nativeInputs'])!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}
            or fact['capabilities']!=capabilities(fact['proof']['referenceReader']['targetRva'],fact['proof']['referenceReader']['equivalentMethod'][0],fact['proof']['components'])
            or fact['evidenceBoundary']!=BOUNDARY):
        raise ValueError(LABEL+'.contract:identity-or-scope')
    return fact


def capabilities(reference_target,reference_definition,components):
    if (type(reference_target)is not int or not 0<reference_target<1<<32
            or type(reference_definition)is not int or reference_definition<0):
        raise ValueError(LABEL+'.capability:reference-reader-target-required')
    result={}
    for name,element in ELEMENTS.items():
        component=components[name];target=component['callTargetRva'];definition=component['typedRequest']['methodSpec'][0]
        if type(target)is not int or not 0<target<1<<32 or type(definition)is not int or definition<0:
            raise ValueError(LABEL+'.capability:exact-packable-reader-source-required')
        result[name]=dict(elementType=element,collectionCounts=[-1,0],nullable=True,
        closedListType='System.Collections.Generic.List`1<'+element+'>',
        referenceReaderTargetRva=reference_target,
        referenceReaderMethodDefinition=reference_definition,
        packableReaderTargetRva=target,packableReaderMethodDefinition=definition,
        positiveCountsAdmitted=False,elementCapability=None,elementGrammarAdmitted=False)
    return result


def derive(image,inputs):
    proof=derive_selector_lists(image,inputs)
    # Match the complete reviewed JSON value, including nested BytesPath
    # tuples and symbolic integer dictionary keys, before strict comparison.
    return json.loads(json.dumps(dict(schema=SCHEMA,status='exact-current-build',nativeInputs=dict(inputs),
        capabilities=capabilities(proof['referenceReader']['targetRva'],proof['referenceReader']['equivalentMethod'][0],proof['components']),proof=proof,evidenceBoundary=BOUNDARY)))


def validate_on_image(image,inputs,*,contract=None):
    fact=contract if contract is not None else _contract()
    if fact['nativeInputs']!=inputs:raise ValueError(LABEL+'.native:component-build-mismatch')
    actual=derive(image,inputs)
    validate_claims(fact,actual,label=LABEL+'.proof')
    validate_claims(actual,fact,label=LABEL+'.declaration')
    return dict(status='validated',nativeInputs=dict(inputs),capabilities=fact['capabilities'],
        elementGrammarAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=fact['evidenceBoundary'])


def _gate(inputs,*,gameassembly=None,metadata=None,game_root=None):
    if (gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.native:both-selected-paths-required')
    if game_root is not None and gameassembly is None:
        root=Path(game_root);gameassembly=root.parent/'GameAssembly.dll'
        metadata=root/'il2cpp_data/Metadata/global-metadata.dat'
    return check_installed_native_inputs(inputs['GameAssembly.dll'],inputs['global-metadata.dat'],
        gameassembly=gameassembly,metadata=metadata)


def validate_current_native_contract(*,gameassembly=None,metadata=None,game_root=None,contract_path=CONTRACT_PATH):
    try:
        path=Path(contract_path);raw=path.read_bytes();fact=_contract(path);inputs=fact['nativeInputs']
        gate=_gate(inputs,gameassembly=gameassembly,metadata=metadata,game_root=game_root)
        if gate.status!='validated':return dict(status=gate.status,capabilities={},failedCheck='installed-native-inputs',detail=gate.detail)
        if failed:=pooled_source_helper.check_unity_input(gate.gameassembly,inputs):return dict(capabilities={},failedCheck='UnityPlayer.dll',**failed)
        result=validate_on_image(open_native_image(gate.gameassembly,gate.metadata),inputs,contract=fact)
        after=_gate(inputs,gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status!='validated':return dict(status=after.status,capabilities={},failedCheck='installed-native-inputs-bookend',detail=after.detail)
        if failed:=pooled_source_helper.check_unity_input(gate.gameassembly,inputs):return dict(capabilities={},failedCheck='UnityPlayer.dll-bookend',**failed)
        if raw!=path.read_bytes():raise ValueError(LABEL+'.contract:declaration-changed-during-validation')
        return result
    except (ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError)as error:
        return dict(capabilities={},**native_validation_failure(error,label=LABEL,source_path=contract_path))


def regenerate(*,game_root=None,gameassembly=None,metadata=None,write=False,contract_path=CONTRACT_PATH):
    path=Path(contract_path);before=path.read_bytes()if path.is_file()else None
    sources=snapshot_complete_reader_inputs()
    inputs=pooled_source_helper._contract()['nativeInputs']
    gate=_gate(inputs,game_root=game_root,gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':raise ValueError(LABEL+'.regenerate:'+gate.status+':'+gate.detail)
    if failed:=pooled_source_helper.check_unity_input(gate.gameassembly,inputs):raise ValueError(str(failed))
    candidate=derive(open_native_image(gate.gameassembly,gate.metadata),inputs)
    after=_gate(inputs,gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated'or pooled_source_helper.check_unity_input(gate.gameassembly,inputs):raise ValueError(LABEL+'.regenerate:native-input-drift')
    if before!=(path.read_bytes()if path.is_file()else None):raise ValueError(LABEL+'.regenerate:contract-declaration-drift')
    if sources!=snapshot_complete_reader_inputs():raise ValueError(LABEL+'.regenerate:reader-source-drift')
    if write:path.write_bytes((json.dumps(candidate,indent=2)+'\n').encode('utf-8'))
    return candidate


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-root',type=Path);parser.add_argument('--gameassembly',type=Path);parser.add_argument('--metadata',type=Path)
    parser.add_argument('--regenerate',action='store_true');parser.add_argument('--write',action='store_true')
    parser.add_argument('--output-json',type=Path)
    args=parser.parse_args(argv)
    if args.write and not args.regenerate:parser.error('--write requires --regenerate')
    if args.output_json and not args.output_json.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):parser.error('--output-json must be below reports/')
    selected=dict(game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata)
    result=regenerate(**selected,write=args.write)if args.regenerate else validate_current_native_contract(**selected)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True,exist_ok=True);args.output_json.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2));return 0 if result['status']in('validated','exact-current-build')else 2


if __name__=='__main__':raise SystemExit(main())

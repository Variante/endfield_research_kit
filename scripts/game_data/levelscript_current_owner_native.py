"""Selected current LevelScript/Brief source paths; child grammar is separate."""
from __future__ import annotations

import json
import argparse
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import native_validation_failure,open_native_image
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,reader_input_changes
from scripts.game_data.memorypack import levelscript_owner_sources as source,pooled_source_helper
from scripts.game_data.memorypack.levelscript_contract_provenance import (
    project_contract,expand_proof)
from scripts.game_data.memorypack.skill_contract_provenance import contract_json_bytes
from scripts.repo_paths import REPO_ROOT

SCHEMA='endfield.levelscript-current-owner-source-native.v2'
LABEL='levelscriptCurrentOwnerNative'
CONTRACT_PATH=CONTRACTS_DIR/'levelscript_current_owner_source_native.json'
BOUNDARY={
    'exact':'Current LevelScriptData28, LevelScriptBriefData9 and LevelData43 nominal metadata, initialized existing-wrapper buffered entry/header/cursor, exact ordered source and owned-store transfers and complete selected returns. Independently current pooled graph, collection, Shape44, AirWall/Mission/geometry, Brief/spawner, finite compiled host records, null/empty host, authored MC10 Patrol and bounded current NPC profiles are composed. Task retains its complete finite GameCondition and nested union records, independent actual Param children, Combine recursive list, exact TaskCondition field and both typed string-key dictionary callers; map-wide dictionary, condition and Param budgets remain distinct. Module retains its complete selected union and ordinary records, all separately typed positive collections, opaque Entity values, LangKey, raw PosRot/Quaternion and Opera/Param children, Rune raw Boolean arrays and padded raw16 key/value entries, and its own UInt64/reference root dictionary and field/frame join. The Module extended header accepts any UInt16 payload selected by its proved finite table, without a shortest-tag requirement; reserved byte markers and unknown extended tags remain refused. Root Enemy30 and Lock2/SingleLock18 keep their separately typed UInt32/reference dictionaries and actual root callers. TriggerVolume retains its own three-route abstract union, complete concrete/Shape records, independent Vector2/Kickable/Shape lists and exact root UInt32 dictionary. EnemyGroup retains its independently proved opaque Entity40 transfer; MissionArea keeps direct raw Trigger44 and independently composed TrackingRoute children; positive LevelWide retains both distinct erased dictionary source witnesses and their actual parent joins. The default ConditionRuntime routes0/12/13/18 compose their concrete sources, recursive list and actual Interactive/LevelData/FunctionArea parent joins. Only the explicitly selected LevelWide dock filter adds its independently proved tag9 leaf and transport; other positive condition tags remain closed. Every other unproved positive child remains closed.',
    'conditional':'Compatible existing wrappers/originals, initialized coherent contexts, disabled collector, sufficient stable disjoint buffered bytes/storage and normal typed child/helper ABI. Runtime provider/default/override choice is unobserved.',
    'structuralOnly':'Stored source framing only. Each child grammar and complete physical owner EOF must be proved separately before a consumer publishes any row.',
    'unresolved':'Creation, cold initialization, refill/error and active-collector paths; live activation, callback selection, playback, mission ownership and order.'}


def derive(image,pins,*,retain_traces=False):
    from scripts.game_data.memorypack.levelscript_current_children_sources import derive as derive_children
    from scripts.game_data.memorypack.levelscript_shape_sources import derive_record,derive_transfer
    from scripts.game_data.memorypack.levelscript_shape_list_sources import derive as derive_shape_list
    from scripts.game_data.memorypack.leveldata_current_components import derive as derive_leveldata
    from scripts.game_data.memorypack.levelscript_task_game_condition_sources import derive as derive_tasks
    from scripts.game_data.memorypack.levelscript_root_empty_sources import derive as derive_empty_root
    from scripts.game_data.memorypack.levelscript_module_graph_sources import derive as derive_modules
    from scripts.game_data.memorypack.levelscript_root_record_sources import derive as derive_root_records
    from scripts.game_data.memorypack.levelscript_trigger_components import derive as derive_triggers
    proof=source.derive(image,pins)
    proof['children']=derive_children(image,pins,proof)
    shape=derive_record(image,pins);transfer=derive_transfer(image,pins,shape)
    collection=derive_shape_list(image,pins,proof,shape,transfer)
    proof['shape']=dict(record=shape,transfer=transfer,collection=collection)
    proof['children']['capabilities'][collection['capability']['closedListType']]=collection['capability']
    proof['leveldata']=derive_leveldata(image,pins,proof,proof['children'])
    proof['rootRecords']=derive_root_records(image,pins,proof,proof['leveldata'])
    proof['triggers']=derive_triggers(image,pins,proof)
    proof['tasks']=derive_tasks(image,pins)
    _task_capability(proof)
    proof['rootEmpty']=derive_empty_root(image,pins,proof,proof['children'],proof['leveldata'])
    proof['modules']=derive_modules(image,pins,owners=proof)
    _module_capability(proof)
    fact=json.loads(json.dumps(dict(schema=SCHEMA,status='exact-current-build',nativeInputs=dict(pins),
        proof=proof,wholeOwnerAdmitted=False,evidenceBoundary=BOUNDARY)))
    return fact if retain_traces else project_contract(fact,image_base=image.pe.image_base)


def _contract(path):
    return _contract_and_semantic(path)[0]


def _contract_and_semantic(path):
    """One fresh read and fully validated expansion, local to this validation."""
    fact=json.loads(Path(path).read_bytes())
    if (set(fact)!={'schema','status','nativeInputs','proof','wholeOwnerAdmitted','evidenceBoundary'}
            or (fact['schema'],fact['status'])!=(SCHEMA,'exact-current-build')
            or fact['wholeOwnerAdmitted']is not False or fact['evidenceBoundary']!=BOUNDARY
            or set(fact['nativeInputs'])!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}):
        raise ValueError(LABEL+'.contract:identity-or-scope')
    # expand_proof validates the complete common graph/catalog/orphan/depth
    # rules and every Story envelope; validate_projection repeated this work.
    semantic=expand_proof(fact['proof'])
    if (semantic.get('nativeInputs')!=fact['nativeInputs']
            or set(semantic.get('owners',{}))!={source.ROOT,source.BRIEF}):
        raise ValueError(LABEL+'.contract:semantic-owner-scope')
    return fact,semantic


def _task_capability(proof):
    from scripts.game_data.memorypack.levelscript_task_game_condition_sources import SCHEMA,CAPABILITY
    from scripts.game_data.codecs.levelscript.current_task_game_conditions import validate
    component=proof.get('tasks')
    if component is None:return None
    if (component.get('schema')!=SCHEMA or component.get('status')!='validated-conditional-Task-game-condition'
            or component.get('nativeInputs')!=proof.get('nativeInputs')or component.get('holds')!=[]
            or set(component.get('capabilities',{}))!={CAPABILITY}):
        raise ValueError(LABEL+'.complete-Task-game-condition-child:'+json.dumps(component.get('holds',[]),separators=(',',':'))[:2200])
    capability=component['capabilities'][CAPABILITY];validate(capability);return capability


def _module_capability(proof):
    from scripts.game_data.memorypack.levelscript_module_public import require_component
    component=proof.get('modules')
    if component is None:return None
    return require_component(component,proof.get('nativeInputs'))


def validate_on_image(image,pins,*,contract=None):
    if contract is None:fact,semantic=_contract_and_semantic(CONTRACT_PATH)
    else:fact,semantic=contract,None
    return _validate_on_image(image,pins,fact,semantic)


def _validate_on_image(image,pins,fact,semantic):
    if fact['nativeInputs']!=pins:raise ValueError(LABEL+'.native:selected-build-mismatch')
    actual=derive(image,pins)
    validate_claims(fact,actual,label=LABEL+'.proof')
    validate_claims(actual,fact,label=LABEL+'.declaration')
    # Capabilities leave the compact declaration only after the fresh complete
    # same-image proof has matched in both directions. Omitted trace markers
    # remain provenance; they never supply a native source program to a child.
    if semantic is None:semantic=expand_proof(fact['proof'])
    return dict(status='validated',nativeInputs=dict(pins),owners={name:dict(
        memberCount=row['program']['memberCount'],orderedFields=[f['name']for f in row['fields']],
        childGrammarAdmitted=False)for name,row in semantic['owners'].items()},
        narrativeComponent=semantic['narrativeComponent'],
        paramStringType=semantic['paramStringType'],
        children=semantic.get('children',{}).get('capabilities',{}),
        leveldata=semantic.get('leveldata',{}).get('capabilities'),
        tasks=_task_capability(semantic),
        rootEmpty=semantic.get('rootEmpty',{}).get('capabilities'),
        rootRecords=semantic.get('rootRecords',{}).get('capabilities'),
        triggers=semantic.get('triggers',{}).get('capability'),
        modules=_module_capability(semantic),
        wholeOwnerAdmitted=False,evidenceBoundary=BOUNDARY)


def _gate(pins,*,game_root=None,gameassembly=None,metadata=None):
    if(gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.native:both-selected-paths-required')
    if gameassembly is None:
        if game_root is None:raise ValueError(LABEL+'.native:explicit-selected-inputs-required')
        root=Path(game_root);gameassembly=root.parent/'GameAssembly.dll';metadata=root/'il2cpp_data/Metadata/global-metadata.dat'
    return check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)


def validate_current_native_contract(*,game_root=None,gameassembly=None,metadata=None,contract_path=CONTRACT_PATH):
    try:
        before=snapshot_complete_reader_inputs();path=Path(contract_path);raw=path.read_bytes()
        fact,semantic=_contract_and_semantic(path);pins=fact['nativeInputs'];gate=_gate(pins,game_root=game_root,gameassembly=gameassembly,metadata=metadata)
        if gate.status!='validated':return dict(status=gate.status,detail=gate.detail,owners={})
        if failure:=pooled_source_helper.check_unity_input(gate.gameassembly,pins):return dict(owners={},**failure)
        result=_validate_on_image(open_native_image(gate.gameassembly,gate.metadata),pins,fact,semantic)
        after=_gate(pins,gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail,owners={})
        if failure:=pooled_source_helper.check_unity_input(gate.gameassembly,pins):return dict(owners={},**failure)
        if raw!=path.read_bytes():raise ValueError(LABEL+'.contract:declaration-drift')
        changed=snapshot_complete_reader_inputs()
        if before!=changed:raise ValueError(LABEL+'.source:reader-drift:'+str(reader_input_changes(before,changed)))
        return dict(result,nativeSources={'GameAssembly.dll':str(Path(gate.gameassembly).resolve()),
            'global-metadata.dat':str(Path(gate.metadata).resolve())})
    except(ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError)as error:
        return dict(owners={},**native_validation_failure(error,label=LABEL,source_path=contract_path))


def regenerate(*,game_root=None,gameassembly=None,metadata=None,write=False,contract_path=CONTRACT_PATH):
    path=Path(contract_path);before=path.read_bytes()if path.is_file()else None
    sources=snapshot_complete_reader_inputs();pins=pooled_source_helper._contract()['nativeInputs']
    gate=_gate(pins,game_root=game_root,gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':raise ValueError(LABEL+'.regenerate:'+gate.status+':'+gate.detail)
    if failed:=pooled_source_helper.check_unity_input(gate.gameassembly,pins):raise ValueError(str(failed))
    result=derive(open_native_image(gate.gameassembly,gate.metadata),pins)
    after=_gate(pins,gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated'or pooled_source_helper.check_unity_input(gate.gameassembly,pins):
        raise ValueError(LABEL+'.regenerate:native-input-drift')
    if before!=(path.read_bytes()if path.is_file()else None):raise ValueError(LABEL+'.regenerate:contract-declaration-drift')
    if sources!=snapshot_complete_reader_inputs():raise ValueError(LABEL+'.regenerate:reader-source-drift')
    if write:path.write_bytes(contract_json_bytes(result))
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in('game-root','gameassembly','metadata'):parser.add_argument('--'+name,type=Path)
    parser.add_argument('--regenerate',action='store_true');parser.add_argument('--write',action='store_true')
    parser.add_argument('--output-json',type=Path);args=parser.parse_args(argv)
    if args.write and not args.regenerate:parser.error('--write requires --regenerate')
    if args.output_json and not args.output_json.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):
        parser.error('--output-json must be below reports/')
    selected=dict(game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata)
    result=regenerate(**selected,write=args.write)if args.regenerate else validate_current_native_contract(**selected)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True,exist_ok=True)
        args.output_json.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],owners=list(result.get('owners',{})),wholeOwnerAdmitted=False)))
    return 0 if result['status']in('validated','exact-current-build')else 2


if __name__=='__main__':raise SystemExit(main())

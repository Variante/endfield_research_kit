"""Authenticate the selected LipSync channel reader and typed array reads."""
from __future__ import annotations
if __name__=='__main__' and not __package__:
    raise SystemExit('Run python -m scripts.game_data.lipsync_native')
import json,tempfile
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.levelscript_family_regenerate import Build,select_calls,_method_row,_window,open_selected_build
from scripts.game_data.memorypack.lipsync import LIPSYNC_FIELD_NAMES
from scripts.game_data.memorypack.pooled_source_helper import check_unity_input

SCHEMA='endfield.lipsync-native.v1'
DEFAULT_CONTRACT=CONTRACTS_DIR/'lipsync_native.json'
CLONES_CONTRACT=CONTRACTS_DIR/'memorypack_reader_clones_native.json'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_View_LipSync_LipSyncTrack_LipSyncRawDataCriwareForMemoryPack'
BOUNDARY={'direct':'Complete selected channel reader, member count, ordered named setter calls and closed ReadArray<float[]> contexts.',
    'conditional':'Compatible selected array formatter, initialized metadata and valid reader/output storage; the corpus separately proves fifteen count-framed arrays of six finite floats through physical EOF.',
    'unresolved':'Live formatter/provider selection, Keyframe consumer semantics, voice ownership and playback selection.'}


def derive(image,pins):
    build=Build(image,pins);base=image.pe.image_base;wrapper=build.wrappers[WRAPPER]
    if (wrapper.wrapped_type!='Beyond.Gameplay.View.LipSync.LipSyncTrack+LipSyncRawDataCriware' or wrapper.inherited_members
            or [(m.name,m.declared_type) for m in wrapper.members]!=[(name,'float[][]') for name in LIPSYNC_FIELD_NAMES]):
        raise ValueError('lipSyncNative.reviewed-channel-declarations')
    body=build.body.body(WRAPPER,'Deserialize')
    header,reads,setters,setups=select_calls(body.rows,len(wrapper.members),[image.method_pointer_va(image.metadata.methods[m.method_index]) for m in wrapper.members])
    rows=[]
    for member,read,setter,setup in zip(wrapper.members,reads,setters,setups,strict=True):
        loads=[r for r in setup if bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x15']
        if len(loads)!=1:raise ValueError('lipSyncNative.typed-array-context-count')
        context=derive_typed_usage_context(image,int(loads[0]['va'],16)-base,label='lipSyncNative')
        if (context['typeName'],context['methodName'],context['classArguments'],context['methodArguments'])!=('MemoryPack.MemoryPackReader','ReadArray',[],['float[]']):
            raise ValueError('lipSyncNative.closed-array-type')
        target=int(read['text'].split()[1],16);build.prove_named_target(target,'MemoryPack.MemoryPackReader','ReadArray')
        rows.append(dict(name=member.name,declaredType=member.declared_type,context=context,
            readCallRva=int(read['va'],16)-base,readTargetRva=target-base,setterCallRva=int(setter['va'],16)-base,
            setterMethod=_method_row(image,[0,member.declaring_wrapper,image.metadata.string(image.metadata.methods[member.method_index].name_index),0])))
    formatter=WRAPPER+'+'+WRAPPER.rsplit('.',1)[-1]+'Formatter'
    methods=[_method_row(image,[0,name,'Deserialize',0]) for name in (WRAPPER,formatter)]
    windows=[]
    for method in methods:
        pointer=base+method[3]
        windows.append(_window(image,pointer,build.body.extents[pointer],'complete owned reader or formatter body'))
        windows.extend(_window(image,at,at+size,'complete owned fragment') for at,size in build.body.chained_fragments.get(pointer,()))
    return dict(wrapperName=WRAPPER,wrappedType=wrapper.wrapped_type,typeDefinition=wrapper.type_definition,
        methods=methods,codeWindows=windows,memberCountInstruction={'rva':int(header['va'],16)-base,'hex':bytes.fromhex(header['bytes']).hex().upper()},fields=rows)


def validate_lipsync_native_contract(*,contract_path=DEFAULT_CONTRACT,game_root=None,gameassembly=None,metadata=None):
    try:
        path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw);pins=fact['nativeInputs']
        if set(fact)!={'schema','status','nativeInputs','proof','evidenceBoundary'} or (fact['schema'],fact['status'],fact['evidenceBoundary'])!=(SCHEMA,'exact-current-build',BOUNDARY) or set(pins)!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}:
            raise ValueError('lipSyncNative.contract-identity')
        if (gameassembly is None)!=(metadata is None):raise ValueError('lipSyncNative.both-native-paths-required')
        root=Path(game_root) if game_root is not None else None
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
            gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll' if root else None,
            metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
        if gate.status!='validated':return {'status':gate.status,'detail':gate.detail}
        failed=check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        clones=CLONES_CONTRACT.read_bytes();actual=derive(open_native_image(gate.gameassembly,gate.metadata),pins)
        validate_claims(fact['proof'],actual,label='lipSyncNative.proof');validate_claims(actual,fact['proof'],label='lipSyncNative.declaration')
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status!='validated':return {'status':after.status,'detail':'selected inputs changed during validation: '+after.detail}
        failed=check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        if path.read_bytes()!=raw or CLONES_CONTRACT.read_bytes()!=clones:raise ValueError('lipSyncNative.declaration-drift')
        return {'status':'validated','channelNames':list(LIPSYNC_FIELD_NAMES),'nativeInputs':pins,'evidenceBoundary':BOUNDARY}
    except (OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError) as error:
        return native_validation_failure(error,label='lipSyncNative',source_path=contract_path)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--regenerate',action='store_true');parser.add_argument('--write',action='store_true')
    for name in ('contract','game-root','gameassembly','metadata'):parser.add_argument('--'+name,type=Path,default=DEFAULT_CONTRACT if name=='contract' else None)
    args=parser.parse_args()
    if args.regenerate:
        if any((args.game_root,args.gameassembly,args.metadata)):parser.error('regeneration uses the selected installed build')
        image,pins=open_selected_build();fact=dict(schema=SCHEMA,status='exact-current-build',nativeInputs=pins,proof=derive(image,pins),evidenceBoundary=BOUNDARY)
        with tempfile.TemporaryDirectory() as temporary:
            draft=Path(temporary)/args.contract.name;draft.write_text(json.dumps(fact),encoding='utf8')
            result=validate_lipsync_native_contract(contract_path=draft,gameassembly=image.gameassembly,metadata=image.metadata_path)
        if args.write and result['status']=='validated':args.contract.write_bytes((json.dumps(fact,indent=2).replace('\n','\r\n')+'\r\n').encode('utf8'))
        result['written']=args.write and result['status']=='validated'
    else:
        if args.write:parser.error('--write requires --regenerate')
        result=validate_lipsync_native_contract(contract_path=args.contract,game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata)
    print(json.dumps(result,indent=2));raise SystemExit(result['status']!='validated')

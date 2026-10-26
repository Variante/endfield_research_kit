"""Authenticate named target-mutation argument claims on the selected build."""
from pathlib import Path
import hashlib
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack import buff_selector_marker_surface as selected_build

CONTRACT_PATH=CONTRACTS_DIR/'buff_selector_validator_mutation_claims.json'
LABEL='buffSelectorValidatorMutation'

def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.buff-selector-validator-mutation-claims.v1',status='reviewed',label=LABEL)
    return c

def _validate_image(image,c):
    index=BodyIndex(image);selected=NativeReferenceContext(image)
    body=index.body(c['consumer'],c['method']);unique={}
    consumers=[m for m in image.metadata.methods_for(index.types[c['consumer']])
        if image.metadata.string(m.name_index)==c['method'] and image.method_pointer_va(m)==body.pointer]
    if len(consumers)!=1 or consumers[0].flags&0x10 or selected.type_name(consumers[0].return_type)!=c['consumerReturnType']:
        raise ValueError(LABEL+'.consumer-signature')
    handles=[p for p in image.metadata.parameters_for(consumers[0]) if image.metadata.string(p.name_index)==c['incomingHandleParameter']]
    if len(handles)!=1 or selected.type_name(handles[0].type_index)!=c['incomingHandleType']:
        raise ValueError(LABEL+'.incoming-handle-type')
    if selected.is_value_type(c['incomingHandleType']) or selected.is_value_type(c['targetSourceReturnType']):
        raise ValueError(LABEL+'.reference-type-required')
    for row in index.body_with_fragments(body):
        if row['va'] in unique and (row['bytes'],row['text'])!=(unique[row['va']]['bytes'],unique[row['va']]['text']):
            raise ValueError(LABEL+'.overlapping-decode-disagreement')
        unique[row['va']]=row
    rows=sorted(unique.values(),key=lambda r:int(r['va'],16));ranges=[]
    for row in rows:
        begin=int(row['va'],16);end=begin+len(bytes.fromhex(row['bytes']))
        if ranges and ranges[-1][1]==begin:ranges[-1][1]=end
        else:ranges.append([begin,end])
    def call_for(symbol):
        matches=[(int(r['va'],16),int(r['text'][5:],16)) for r in rows
            if r['text'].startswith('call 0x') and symbol in index.names_of(int(r['text'][5:],16))]
        if len(matches)!=1:raise ValueError(LABEL+'.unique-call:'+symbol+':'+str(len(matches)))
        return matches[0]
    location=index.parameter_location(body.pointer,body.symbol,c['incomingHandleParameter'])
    if location[0]!='stack' or type(location[1])!=int:raise ValueError(LABEL+'.incoming-handle-location')
    source_site,source_target=call_for(c['targetSourceCall']);handle='parameter:'+c['incomingHandleParameter'];target_origin='return:'+c['targetSourceCall']
    source_type,source_method=c['targetSourceCall'].rsplit('.',1)
    source_methods=[m for m in image.metadata.methods_for(index.types[source_type])
        if image.metadata.string(m.name_index)==source_method and image.method_pointer_va(m)==source_target]
    if len(source_methods)!=1 or selected.type_name(source_methods[0].return_type)!=c['targetSourceReturnType']:
        raise ValueError(LABEL+'.target-source-return-type')
    proof=check_reference_origins(rows,entry=body.pointer,owned_ranges=ranges,incoming_registers={},
        incoming_stack_slots={location[1]:handle},selected_call_returns={source_site:target_origin})
    branches=[(int(r['va'],16),control_transfer(r)) for r in rows]
    mutations=[]
    for spec in c['mutations']:
        site,target=call_for(spec['method']);origins=proof['registerOrigins'][site]
        if spec['receiver']!='incomingHandleParameter' or origins['rcx']!=[handle]:raise ValueError(LABEL+'.receiver-origin')
        name,method=spec['method'].rsplit('.',1)
        methods=[m for m in image.metadata.methods_for(index.types[name])
            if image.metadata.string(m.name_index)==method and image.method_pointer_va(m)==target]
        if len(methods)!=1:raise ValueError(LABEL+'.callee-selection')
        params=[{'name':image.metadata.string(p.name_index),'type':selected.type_name(p.type_index)} for p in image.metadata.parameters_for(methods[0])]
        if methods[0].flags&0x10 or selected.type_name(methods[0].return_type)!=spec['returnType'] or params!=[{k:p[k] for k in ('name','type')} for p in spec['parameters']]:
            raise ValueError(LABEL+'.callee-signature')
        pos=next(i for i,r in enumerate(rows) if int(r['va'],16)==site)
        if spec['argumentSetup']=='three-true-booleans-and-null-method-info':
            preceding=rows[pos-4:pos]
            if len(params)!=3 or any(p['type']!='bool' or p.get('value') is not True for p in spec['parameters']):raise ValueError(LABEL+'.boolean-claim')
            expected=['41 b1 01','48 c7 44 24 20 00 00 00 00','45 0f b6 c1','41 0f b6 d1']
        elif spec['argumentSetup']=='reference-target-and-null-method-info':
            preceding=rows[pos-3:pos]
            if len(params)!=1 or spec.get('target')!='targetSourceCallReturn' or origins['rdx']!=[target_origin]:raise ValueError(LABEL+'.target-origin')
            expected=['45 33 c0','49 8b d6','48 8b cf']
        else:raise ValueError(LABEL+'.argument-setup-claim')
        if [r['bytes'] for r in preceding]!=expected:raise ValueError(LABEL+'.argument-setup-bytes')
        block=preceding+[rows[pos]]
        if any(int(a['va'],16)+len(bytes.fromhex(a['bytes']))!=int(b['va'],16) for a,b in zip(block,block[1:])):
            raise ValueError(LABEL+'.argument-setup-contiguity')
        interiors={int(r['va'],16) for r in preceding[1:]}|{site}
        if any(flow.get('target') in interiors for _,flow in branches if flow['kind'] in ('jump','conditional')):
            raise ValueError(LABEL+'.argument-setup-bypass')
        mutations.append({'method':spec['method'],'siteRva':site-image.pe.image_base,
            'receiverOrigins':origins['rcx'],'targetOrigins':origins['rdx'] if spec.get('target') else None,
            'parameters':spec['parameters'],'methodInfoArgument':0})
    return {'mutations':mutations,'instructionsChecked':proof['instructionsChecked'],'callsChecked':proof['callsChecked'],
            'condition':proof['condition'],'runtimeExecutionKnown':False,'mutationEffectsKnown':False}

def validate_current_native_contract(*,gameassembly:Path|None=None,metadata:Path|None=None):
    c=_contract();pins=selected_build._contract()['nativeInputs']
    def empty(status,detail):return {'status':status,'detail':detail,'mutationProof':None,'runtimeExecutionKnown':False}
    g=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if g.status!='validated':return empty(g.status,g.detail)
    unity=g.gameassembly.parent/'UnityPlayer.dll'
    def match():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not match():return empty('mismatched' if unity.is_file() else 'missing','UnityPlayer.dll missing or mismatched')
    proof=_validate_image(open_native_image(g.gameassembly,g.metadata),c)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=g.gameassembly,metadata=g.metadata)
    if after.status!='validated':return empty(after.status,after.detail)
    if not match():return empty('mismatched' if unity.is_file() else 'missing','UnityPlayer.dll changed during validation')
    return {'status':'validated','nativeInputs':pins,'mutationProof':proof,'evidenceBoundary':c['evidenceBoundary'],
            'runtimeExecutionKnown':False,'mutationEffectsKnown':False,'wholeRootAdmitted':False}

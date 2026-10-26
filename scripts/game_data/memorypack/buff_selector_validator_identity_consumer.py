"""Authenticate selected named cast identity fields and static branch claims."""
from pathlib import Path
import hashlib
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,validate_reference_ancestor_chain
from scripts.game_data.il2cpp.protocol import native_enum_members,field_defaults
from scripts.game_data.il2cpp.selector_identity_program import check_selector_identity_program
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack import buff_selector_marker_surface as selected_build

CONTRACT_PATH=CONTRACTS_DIR/'buff_selector_validator_identity_claims.json'
LABEL='buffSelectorValidatorIdentity'

def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.buff-selector-validator-identity-claims.v1',status='reviewed',label=LABEL)
    return c

def _rows(index,body):
    unique={}
    for row in index.body_with_fragments(body):
        if row['va'] in unique and (row['bytes'],row['text'])!=(unique[row['va']]['bytes'],unique[row['va']]['text']):
            raise ValueError(LABEL+'.overlapping-decode-disagreement')
        unique[row['va']]=row
    rows=sorted(unique.values(),key=lambda r:int(r['va'],16));ranges=[]
    for row in rows:
        start=int(row['va'],16);end=start+len(bytes.fromhex(row['bytes']))
        if ranges and ranges[-1][1]==start:ranges[-1][1]=end
        else:ranges.append([start,end])
    return rows,ranges

def _method(image,index,pointer,symbol):
    name,method=symbol.rsplit('.',1)
    indices={r['methodIndex'] for r in index.names_by_pointer.get(pointer,())
        if r.get('type')==name and r.get('method')==method and type(r.get('methodIndex'))==int}
    methods=[]
    for method_index in indices:
        if not 0<=method_index<len(image.metadata.methods):raise ValueError(LABEL+'.method-index')
        m=image.metadata.methods[method_index]
        declared=image.metadata.type_full_name(image.metadata.types[m.declaring_type])
        if declared==name and image.metadata.string(m.name_index)==method and image.method_pointer_va(m)==pointer:
            methods.append(m)
    if len(methods)!=1:raise ValueError(LABEL+'.unique-method:'+symbol)
    return methods[0]

def _validate_image(image,c):
    index=BodyIndex(image);selected=NativeReferenceContext(image,index=index);spec=c['consumer']
    body=index.body(spec['type'],spec['method']);method=_method(image,index,body.pointer,body.symbol)
    if method.flags&0x10 or selected.type_name(method.return_type)!=spec['returnType']:raise ValueError(LABEL+'.consumer-signature')
    locations={}
    for role in ('owner','action'):
        param=spec[role+'Parameter'];matches=[p for p in image.metadata.parameters_for(method) if image.metadata.string(p.name_index)==param['name']]
        if len(matches)!=1 or selected.type_name(matches[0].type_index)!=param['type'] or selected.is_value_type(param['type']):
            raise ValueError(LABEL+'.incoming-reference-parameter:'+role)
        locations[role]=index.parameter_location(body.pointer,body.symbol,param['name'])
    if locations['owner'][0]!='register' or locations['action'][0]!='stack':raise ValueError(LABEL+'.incoming-parameter-locations')
    rows,ranges=_rows(index,body);calls={};targets={}
    for role,call in c['calls'].items():
        observed=[(int(r['va'],16),int(r['text'][5:],16)) for r in rows
            if r['text'].startswith('call 0x') and call['method'] in index.names_of(int(r['text'][5:],16))]
        pointers={p for _,p in observed}
        if len(pointers)!=1 or role!='isPatched' and len(observed)!=1:raise ValueError(LABEL+'.call-selection:'+role)
        targets[role]=next(iter(pointers))
        callee=_method(image,index,targets[role],call['method'])
        if selected.type_name(callee.return_type)!=call['returnType']:raise ValueError(LABEL+'.call-return-type:'+role)
        if role in ('clear','remove','objectType','skillCastId') and callee.flags&0x10:raise ValueError(LABEL+'.instance-callee-required:'+role)
        if role!='isPatched':calls[role]=observed[0][0]
    receiver=c['calls']['lock']['returnType']
    entity=c['fields']['entity'];controller=c['fields']['controller'];cast_info=c['fields']['castInfo']
    current=c['fields']['curSkill'];ability=c['fields']['ability'];identity=c['fields']['abilityCastId']
    getter_owner=c['calls']['skillCastId']['method'].rsplit('.',1)[0]
    if (receiver!=spec['ownerParameter']['type'] or
        c['calls']['objectType']['method'].rsplit('.',1)[0]!=receiver or
        c['calls']['objectType']['returnType']!=c['objectTypeSelection']['enum'] or
        entity['type']!=controller['field'].split('::')[0] or
        controller['type']!=cast_info['field'].split('::')[0] or
        cast_info['type']!=c['castInfo']['type'] or
        current['field'].split('::')[0]!=spec['ownerParameter']['type'] or
        current['type']!=getter_owner or ability['field'].split('::')[0]!=getter_owner or
        ability['type']!=identity['field'].split('::')[0] or identity['type']!='uint'):
        raise ValueError(LABEL+'.typed-field-route')
    validate_reference_ancestor_chain(selected,receiver,c['receiverAncestorChain'],c['fields']['entity']['field'].split('::')[0])
    fields={};field_proof=[]
    for role,field in c['fields'].items():
        owner,type_name,offset=selected.field(field['field'])
        if type_name!=field['type'] or selected.is_value_type(owner):raise ValueError(LABEL+'.named-reference-field:'+role)
        fields[role]=offset;field_proof.append({'role':role,'field':field['field'],'type':type_name,'offset':offset})
    info=c['castInfo'];name=info['type'];td=index.types[name]
    if not selected.is_value_type(name) or selected.is_enum(name):raise ValueError(LABEL+'.cast-info-value-type')
    members=[]
    for member in info['members']:
        owner,type_name,offset=selected.field(name+'::'+member['name'])
        if type_name!=member['type'] or offset-info['boxedObjectHeaderBytes']!=member['inlineOffset']:raise ValueError(LABEL+'.inline-member-layout')
        members.append({'name':member['name'],'type':type_name,'boxedOffset':offset,'inlineOffset':member['inlineOffset']})
    if members[0]['type']!='uint' or members[0]['inlineOffset']!=0 or info['boxedObjectHeaderBytes']!=16 or info['copiedValueBytes']!=24:
        raise ValueError(LABEL+'.cast-info-copy-shape')
    if not 0<=td.index<int(image.registration['typeDefinitionsSizesCount']):raise ValueError(LABEL+'.size-index')
    pointer=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    if not pointer:raise ValueError(LABEL+'.size-row-missing')
    raw=image.pe.bytes_at_va(pointer,16)
    if len(raw)!=16 or int.from_bytes(raw[:4],'little')!=info['boxedObjectHeaderBytes']+info['copiedValueBytes']:
        raise ValueError(LABEL+'.boxed-size-does-not-cover-inline-copy')
    enum=c['objectTypeSelection'];values=[r for r in native_enum_members(image.metadata,field_defaults(image.metadata),image.pe,image.registration,enum['enum']) if r['name']==enum['member']]
    if len(values)!=1:raise ValueError(LABEL+'.enum-member')
    getter_name,getter_method=c['calls']['skillCastId']['method'].rsplit('.',1)
    getters=[b for b in index.overload_bodies(getter_name,getter_method) if b.pointer==targets['skillCastId']]
    if len(getters)!=1:raise ValueError(LABEL+'.getter-body')
    getter=getters[0];getter_rows,getter_ranges=_rows(index,getter)
    proof=check_selector_identity_program(rows,entry=body.pointer,owned_ranges=ranges,calls=calls,targets=targets,
        fields=fields,owner_register=locations['owner'][1],action_stack_slot=locations['action'][1],
        ability_entity_literal=values[0]['id'],getter_rows=getter_rows,getter_entry=getter.pointer,getter_ranges=getter_ranges)
    return {'program':proof,'fields':field_proof,'castInfoMembers':members,'selectedBoxedSizeBytes':int.from_bytes(raw[:4],'little'),
            'objectTypeMember':values[0],'candidateInlineScalarType':'uint','fallbackGetterReturnType':'uint',
            'runtimeExecutionKnown':False,'mutationEffectsKnown':False}

def validate_current_native_contract(*,gameassembly:Path|None=None,metadata:Path|None=None):
    c=_contract();pins=selected_build._contract()['nativeInputs']
    def empty(status,detail):return {'status':status,'detail':detail,'identityProof':None,'runtimeExecutionKnown':False}
    g=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if g.status!='validated':return empty(g.status,g.detail)
    unity=g.gameassembly.parent/'UnityPlayer.dll'
    def match():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not match():return empty('mismatched' if unity.is_file() else 'missing','UnityPlayer.dll missing or mismatched')
    proof=_validate_image(open_native_image(g.gameassembly,g.metadata),c)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=g.gameassembly,metadata=g.metadata)
    if after.status!='validated':return empty(after.status,after.detail)
    if not match():return empty('mismatched' if unity.is_file() else 'missing','UnityPlayer.dll changed during validation')
    return {'status':'validated','nativeInputs':pins,'identityProof':proof,'evidenceBoundary':c['evidenceBoundary'],
            'runtimeExecutionKnown':False,'mutationEffectsKnown':False,'wholeRootAdmitted':False}

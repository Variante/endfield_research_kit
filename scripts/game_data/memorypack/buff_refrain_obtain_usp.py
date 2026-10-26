"""Source-bound USP fields with independent GameplayTagList and target children."""
from __future__ import annotations
import hashlib,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from .action_dispatcher import load_action_routes
from .buff_actions import Reader,SEQUENCE_RECURSION_LIMIT
from . import named_native_records as named,stored_plan_values as stored,buff_aura_heal_actions as tags
from .source_bound_stored_tree import bind_source_named_tree

LABEL='buffRefrainObtainUsp';SCHEMA='endfield.buff-refrain-obtain-usp-native-contract.v1'
CONTRACT_PATH=CONTRACTS_DIR/'buff_refrain_obtain_usp_native.json'
WIDTHS={'byte':1,'scalar32':4};CHILDREN=('target','direction','selector','directionTargets','auraHeal')


def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if set(c.get('records',{}))!={'refrainObtainUsp'} or set(c.get('actionDispatch',{}).values())!={'refrainObtainUsp'} or len(c['actionDispatch'])!=1:raise ValueError(LABEL+'.contract:shape')
    r=c['records']['refrainObtainUsp'];members=r['members']
    expected=[('isEnable','byte'),('priorityLevel','scalar32'),('priorityOffset','scalar32'),('serverActionIndex','scalar32'),('clearUspOnEnd','byte'),('refrainObtainUspTags','tag-list-profile'),('targetSettings','target-profile')]
    if r['inheritedMemberCount']!=4 or [(m['fieldName'],m['kind']) for m in members]!=expected or set(c['childTypes'])!={'tagList','target'}:raise ValueError(LABEL+'.contract:parent-members')
    for m,key in zip(members[-2:],('tagList','target')):
        if m['declaredType']!=c['childTypes'][key] or type(m.get('sourceContextInstructionRva')) is not int:raise ValueError(LABEL+'.contract:typed-child')
    return c


def supported_tags():return frozenset(map(int,_contract()['actionDispatch']))
def _members(c):return {k:[{'fieldName':m['fieldName'],'kind':m['kind']} for m in r['members']] for k,r in c['records'].items()}


def _definitions(c,children):
    for key in CHILDREN:
        p=children.get(key,{})
        if p.get('status')!='validated' or p.get('nativeInputs')!=c['nativeInputs']:raise ValueError(LABEL+'.native:child-build='+key)
    registry=children['target'].get('_registry')
    if registry is None:raise ValueError(LABEL+'.native:source-bound-registry-required')
    result={}
    for key,name in c['childTypes'].items():
        selected=[d for d,n in registry.wrapped_names.items() if n==name and d in registry.plans]
        if len(selected)!=1:raise ValueError(LABEL+'.native:unique-child-wrapper='+key)
        result[key]=selected[0]
    if result['target']!=children['target'].get('targetDefinition'):raise ValueError(LABEL+'.native:target-definition')
    if children['auraHeal'].get('recordMembers')!=tags._members(tags._contract()):raise ValueError(LABEL+'.native:independent-tag-members')
    return result


def _bindings(c,runtime):
    if not isinstance(runtime,dict) or set(runtime)!=set(c['childTypes']) or any(type(v) is not int or v<0 for v in runtime.values()):raise ValueError(LABEL+'.native:complete-child-runtime-identities')
    r=c['records']['refrainObtainUsp'];source=json.loads((CONTRACTS_DIR/r['sourceContract']).read_bytes());result={}
    for m,key in zip(r['members'][-2:],('tagList','target')):
        selected=[v for v in source['nestedContexts'] if v['instructionRva']==m['sourceContextInstructionRva']]
        if len(selected)!=1 or selected[0]['typeDefinition']!=runtime[key] or selected[0]['typeName']!=m['declaredType']:raise ValueError(LABEL+'.native:parent-closed-child-context='+m['fieldName'])
        result[m['fieldName']]={'child':key,'context':selected[0]}
    return result


def validate_current_native_contract(*,children,gameassembly:Path|None=None,metadata:Path|None=None):
    c=_contract();pins=c['nativeInputs']
    if gameassembly is None or metadata is None:return {'status':'missing','detail':'Explicit selected GameAssembly and metadata required','nativeInputs':pins}
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins}
    definitions=_definitions(c,children);unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def unity_ok():
        if not unity.is_file():return False
        with unity.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest().upper()==pins['UnityPlayer.dll']
    if not unity_ok():return {'status':'mismatched' if unity.is_file() else 'missing','detail':'UnityPlayer.dll missing or mismatched','nativeInputs':pins}
    image=open_native_image(gate.gameassembly,gate.metadata)
    wrapper=definitions['target'];fields=[f for f in image.metadata.fields_for(image.metadata.types[wrapper]) if image.metadata.string(f.name_index)=='__instance']
    if len(fields)!=1:raise ValueError(LABEL+'.native:target-wrapper-instance')
    pointer=image.pe.u64_at_va(int(image.registration['types'],16)+fields[0].type_index*8);raw=image.pe.bytes_at_va(pointer,16)
    if raw[10:12]!=b'\x12\x00':raise ValueError(LABEL+'.native:target-runtime-class')
    runtime={'target':int.from_bytes(raw[:8],'little'),'tagList':tags._contract()['records']['tagList']['runtimeTypeDefinition']}
    for key,d in runtime.items():
        if image.type_name(d)!=c['childTypes'][key]:raise ValueError(LABEL+'.native:independently-owned-child-type='+key)
    record=c['records']['refrainObtainUsp'];source_path=CONTRACTS_DIR/record['sourceContract'];source=json.loads(source_path.read_bytes())
    buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,image.modules,image.owners,source=str(gate.gameassembly),contract_path=source_path, native_image=image)
    def fail(check,expected,actual,**details):raise ValueError(f'{LABEL}.native:{check}:expected={str(expected)[:1000]}; actual={str(actual)[:1000]}; details={details}')
    proved=named.validate_named_records(image,source,c['records'],label=LABEL,fail=fail);bindings=_bindings(c,runtime)
    for b in bindings.values():named.check_typed_context(image,b['context'],c['childTypes'][b['child']],label=LABEL,fail=fail)
    routes,audit=load_action_routes(gameassembly=gate.gameassembly,metadata=gate.metadata);route=routes.get(next(iter(supported_tags())))
    if audit.get('status')!='validated' or route is None or route.status!='resolved' or route.wrapper_name!=record['wrapperTypeName'] or list(route.member_order)!=[m['fieldName'] for m in record['members']] or list(route.member_declared_types)!=[m['declaredType'] for m in record['members']]:raise ValueError(LABEL+'.native:current-dispatcher')
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or not unity_ok():return {'status':after.status if after.status!='validated' else 'mismatched','detail':'Selected native inputs changed','nativeInputs':pins}
    return {'status':'validated','nativeInputs':pins,'recordMembers':proved,'actionDispatch':c['actionDispatch'],'childDefinitions':definitions,
        'childRuntimeDefinitions':runtime,'parentChildBindings':bindings,'evidenceBoundary':c['evidenceBoundary'],'runtimeExecutionKnown':False,'wholeRootAdmitted':False}


def decode_action(data,*,source,digest,start,end,tag,native_validation,target_decoder=None,depth=0):
    c=_contract();children=native_validation.get('children',{});p=children.get('refrainObtainUsp',{})
    if native_validation.get('status')!='validated' or native_validation.get('nativeInputs')!=c['nativeInputs'] or p.get('status')!='validated' or p.get('nativeInputs')!=c['nativeInputs'] or p.get('recordMembers')!=_members(c) or p.get('actionDispatch')!=c['actionDispatch']:raise ValueError(LABEL+'.decode:native-parent-required')
    definitions=_definitions(c,children)
    if p.get('childDefinitions')!=definitions or p.get('parentChildBindings')!=_bindings(c,p.get('childRuntimeDefinitions',{})):raise ValueError(LABEL+'.decode:typed-child-bindings')
    if not isinstance(data,bytes) or not source or not isinstance(digest,str) or hashlib.sha256(data).hexdigest().upper()!=digest.upper() or type(start) is not int or type(end) is not int or not 0<=start<end<=len(data) or type(tag) is not int or str(tag) not in c['actionDispatch'] or type(depth) is not int or not 0<=depth<SEQUENCE_RECURSION_LIMIT:raise ValueError(LABEL+'.decode:native-source-or-span')
    reader=Reader(data,source,end);reader.pos=start
    if reader.nested_union_tag((tag,),'refrain-obtain-usp')!=tag:raise ValueError(LABEL+'.decode:physical-union-tag')
    null=reader.peek()==255;fields=[];record=c['records']['refrainObtainUsp']
    if null:reader.take(1,'null-usp-parent')
    else:
        reader.header(len(record['members']))
        for m in record['members']:
            begin=reader.pos;kind=m['kind'];child=None;binding=None
            if kind in WIDTHS:tree=stored.fixed_node(reader.take(WIDTHS[kind],m['fieldName']))
            else:
                key=p['parentChildBindings'][m['fieldName']]['child']
                if kind=='tag-list-profile':
                    reader.tag_list_profile(reserve=1);child=tags.decode_tag_list(data,source=source,digest=digest,start=begin,end=reader.pos,native_validation=children['auraHeal'])
                elif kind=='target-profile':
                    reader.target_profile()
                    if data[begin:reader.pos]==b'\xff':child={'start':begin,'end':reader.pos,'status':'exact-null','recursiveStoredSchemaExact':True}
                    else:
                        if not callable(target_decoder):raise ValueError(LABEL+'.decode:independent-target-required')
                        child=target_decoder(data,source,digest,{'fieldName':m['fieldName'],'start':begin,'end':reader.pos},children,depth=depth)
                else:raise ValueError(LABEL+'.decode:unsupported-child')
                if child.get('recursiveStoredSchemaExact') is not True or (child.get('start'),child.get('end'))!=(begin,reader.pos):raise ValueError(LABEL+'.decode:incomplete-child-or-span='+m['fieldName'])
                tree=stored.decode_stored_plan(data,source=source,digest=digest,start=begin,end=reader.pos,definition=definitions[key],registry=children['target']['_registry'])['storedTree']
                binding=bind_source_named_tree(child,tree)
            if stored.encode_stored_node(tree)!=data[begin:reader.pos]:raise ValueError(LABEL+'.decode:field-reencode='+m['fieldName'])
            fields.append({'fieldName':m['fieldName'],'declaredType':m['declaredType'],'kind':kind,'start':begin,'end':reader.pos,'storedValue':tree,'nativeChildReceipt':child,'sourceTreeBinding':binding})
    if reader.pos!=end:raise ValueError(f'{LABEL}.decode:required-parent-end expected={end} actual={reader.pos}')
    receipt={'schema':'endfield.buff-refrain-obtain-usp-action-receipt.v1','source':source,'logicalSha256':digest.upper(),'tag':tag,
        'typeName':record['runtimeTypeName'],'start':start,'end':end,'null':null,'namedFields':fields,'recursiveStoredSchemaExact':True,
        'runtimeMeaningExact':False,'runtimeExecutionKnown':False,'wholeRootAdmitted':False}
    if encode_action(receipt)!=data[start:end]:raise ValueError(LABEL+'.decode:whole-parent-reencode')
    return receipt


def encode_action(receipt):
    c=_contract();tag=receipt['tag'];fields=receipt['namedFields']
    if type(tag) is not int or str(tag) not in c['actionDispatch']:raise ValueError(LABEL+'.encode:current-tag')
    prefix=bytes((tag,)) if tag<250 else b'\xfa'+struct.pack('<H',tag)
    if receipt.get('null') is True:
        if fields:raise ValueError(LABEL+'.encode:null-fields')
        return prefix+b'\xff'
    members=c['records']['refrainObtainUsp']['members']
    if [(f['fieldName'],f['kind']) for f in fields]!=[(m['fieldName'],m['kind']) for m in members]:raise ValueError(LABEL+'.encode:every-current-field-required')
    return prefix+bytes((len(members),))+b''.join(stored.encode_stored_node(f['storedValue']) for f in fields)

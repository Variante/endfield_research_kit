"""Owned nullable Selector postprocessor lists with selected named children.

Each selected processor owns independently proved recursive children. Raw
enum/blackboard fields do not establish that target processing executed.
"""
from __future__ import annotations
import hashlib,json,struct
from pathlib import Path
from typing import Any,Callable
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack import named_native_records as named,reference_output_sources as references
from scripts.game_data.memorypack import buff_selector_geometry as geometry
from scripts.game_data.memorypack import buff_find_settings_child_receipt as find_settings
from scripts.game_data.memorypack import buff_adding_cooldown as scalar,utf8_source_helper as strings
from scripts.game_data.memorypack.buff_direction_target_children import DEPTH_LIMIT
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError

LABEL='buffSelectorPostprocessors';CONTRACT_PATH=CONTRACTS_DIR/'buff_selector_postprocessors_native.json'

def _contract():
    c,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.buff-selector-postprocessors-native-contract.v3',status='exact-current-build',label=LABEL)
    if (set(c.get('records',{}))!={'postProjection','postShuffle','postExclude','postPriority','buffFilter','postCircular','postNavMesh'}
            or set(c.get('dispatchers',{}))!=set(c.get('postprocessorDispatch',{}))
            or set(c['postprocessorDispatch'].values())!=set(c['records'])-{'buffFilter'}
            or c['listJoin']['fieldName']!='postProcessorData'
            or [m['fieldName'] for m in c['records']['postProjection']['members']]!=['boxShape']
            or [m['fieldName'] for m in c['records']['postShuffle']['members']]!=['processTargetType','targetNumLimit']
            or c.get('blackboardIntReference')!={'contract':'buff_root_no_positive_native.json','section':'blackboardIntChild','sourceContract':'buff_16b_native.json'}
            or c.get('findSettingsReference')!={'contract':'buff_find_settings_child_native.json','recordIndex':0}
            or c.get('blackboardDoubleReference')!={'contract':'buff_adding_cooldown_ownership_native.json','sourceContract':'buff_root_prefix_native.json'}
            or c.get('stringSourceReference')!={'contract':strings.CONTRACT_PATH.name}
            or any(c['records'][k].get('setterOutputSource',{}).get('mode')!='reader-rdi-ref-wrapper-rbx' for k in ('postCircular','postNavMesh'))):
        raise ValueError(f'{LABEL}.contract:shape')
    return c

def _members(c):return {k:[{'fieldName':m['fieldName'],'kind':m['kind']} for m in r['members']] for k,r in c['records'].items()}
def _fail(check,expected,actual,**details):
    error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,**details);raise error

def validate_current_native_contract(*,children:dict[str,Any],gameassembly:Path|None=None,metadata:Path|None=None):
    c=_contract();pins=c['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins}
    for key in ('selector','selectorGeometry','target','findSettings','effectVectors'):
        if children.get(key,{}).get('status')!='validated' or children[key].get('nativeInputs')!=pins:_fail('shared-child',key,children.get(key))
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins['UnityPlayer.dll']:_fail('UnityPlayer.dll',pins['UnityPlayer.dll'],'missing-or-mismatched')
    image=open_native_image(gate.gameassembly,gate.metadata);path=CONTRACTS_DIR/c['sourceContract'];source=json.loads(path.read_bytes())
    buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,image.modules,image.owners,source=str(gate.gameassembly),contract_path=path)
    references.validate_reference_join(image,source,c['listJoin'],fail=_fail)
    selector=children['selector'];registry=selector['_registry'];plan=registry.plans[selector['selectorDefinition']]
    lists=[m for m in plan if m.name=='postProcessorData' and m.kind=='list' and m.element and m.element.kind=='union']
    if len(lists)!=1:_fail('selector-list-plan','one counted postprocessor union list',[m.row() for m in lists])
    routes=registry.union_tag_maps.get(lists[0].element.ref,{})
    proved={}
    sources={}
    for key,record in c['records'].items():
        path=CONTRACTS_DIR/record['sourceContract'];source=json.loads(path.read_bytes())
        buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,image.modules,image.owners,source=str(gate.gameassembly),contract_path=path)
        sources[key]=source
        proved.update(named.validate_named_records(image,source,{key:record},label=LABEL,fail=_fail))
    for tag,key in c['postprocessorDispatch'].items():
        record=c['records'][key];dispatch=c['dispatchers'][tag];result=image.validate_dispatcher(dispatch,label=LABEL)
        at,raw_hex=dispatch['typeLoadInstruction'];raw=bytes.fromhex(raw_hex);image.check_instruction_windows([[at,raw_hex]],label=LABEL)
        if (raw[:3]!=b'\x48\x8b\x15' or len(raw)!=7 or image.pe.image_base+at+7+struct.unpack_from('<i',raw,3)[0]!=result['usageCell']
                or routes.get(int(tag))!=record['wrapperTypeDefinition'] or registry.wrapped_names.get(routes[int(tag)])!=record['runtimeTypeName']):
            _fail('parent-union-route',record['runtimeTypeName'],routes.get(int(tag)))
    shape=geometry.checked_layout(children['selectorGeometry'],'shapeData')
    if c['records']['postProjection']['members'][0]['declaredType']!='System.Collections.Generic.List`1<'+shape['wrappedType']+'>':_fail('shape-child-type',shape['wrappedType'],c['records']['postProjection'])
    # Reference identity comes from each parent's actual closed call context,
    # independently of its child's same-named generated wrapper.
    def context(key,field):
        member=next(m for m in c['records'][key]['members'] if m['fieldName']==field)
        return next(v for v in sources[key]['nestedContexts'] if v['instructionRva']==member['sourceContextInstructionRva'])
    target_definition=children['target']['targetDefinition']
    target_name=registry.wrapped_names.get(target_definition)
    wrapper=image.metadata.types[target_definition]
    instance_fields=[f for f in image.metadata.fields_for(wrapper) if image.metadata.string(f.name_index)=='__instance']
    if len(instance_fields)!=1:_fail('target-wrapper-instance','one independently selected __instance',len(instance_fields))
    type_pointer=image.pe.u64_at_va(int(image.registration['types'],16)+instance_fields[0].type_index*8)
    raw=image.pe.bytes_at_va(type_pointer,16)
    for key,field in (('postExclude','excludedTargetSettings'),('postCircular','rangeCheckTarget')):
        target_context=context(key,field)
        if (raw[10:12]!=b'\x12\0' or struct.unpack_from('<Q',raw)[0]!=target_context['typeDefinition']
                or image.type_name(target_context['typeDefinition'])!=target_name):_fail('target-child',target_name,target_context,record=key)
    filter_record=c['records']['buffFilter'];filter_context=context('postPriority','buffFilterSettings')
    if filter_context['typeDefinition']!=filter_record['runtimeTypeDefinition']:_fail('filter-child',filter_record['runtimeTypeDefinition'],filter_context)
    ref=c['findSettingsReference'];find_contract=json.loads((CONTRACTS_DIR/ref['contract']).read_bytes())
    if find_contract['nativeInputs']!=pins:_fail('find-settings-build',pins,find_contract['nativeInputs'])
    find_record=find_contract['children'][ref['recordIndex']];find_context=context('buffFilter','buffSettings')
    if find_context['typeDefinition']!=find_record['runtimeTypeDefinition']:_fail('find-settings-child',find_record['runtimeTypeDefinition'],find_context)
    # Reuse the root's already maintained concrete BlackboardInt child proof:
    # exact inherited setter order and concrete selected reader windows.
    ref=c['blackboardIntReference'];root=json.loads((CONTRACTS_DIR/ref['contract']).read_bytes());child=root[ref['section']]
    if root['nativeInputs']!=pins:_fail('blackboard-int-build',pins,root['nativeInputs'])
    src=json.loads((CONTRACTS_DIR/ref['sourceContract']).read_bytes());wrapper=image.metadata.types[child['wrapperTypeDefinition']];base=image.metadata.types[child['baseTypeDefinition']]
    for method in src['methods'][2:]:image.validate_method_row(method,label=LABEL)
    image.check_windows(src['codeWindows'][4:],label=LABEL)
    if (image.type_name(wrapper.index)!=child['wrapperType'] or image.type_name(base.index)!=child['baseType']
            or wrapper.parent_index!=base.byval_type_index or image.setter_methods(base,parameter='typeName',label=LABEL)!=child['setterMethods']):
        _fail('blackboard-int-concrete-child',child,image.type_name(wrapper.index))
    int_names=[r[1].removeprefix('set___').removesuffix('__') for r in child['setterMethods']]
    if int_names!=['blackboardKey','useBlackboardKey','value']:_fail('blackboard-int-members',['blackboardKey','useBlackboardKey','value'],int_names)
    if context('postCircular','desireCount')['typeDefinition']!=context('postShuffle','targetNumLimit')['typeDefinition']:
        _fail('circular-int-child',context('postShuffle','targetNumLimit'),context('postCircular','desireCount'))
    ref=c['blackboardDoubleReference'];double=json.loads((CONTRACTS_DIR/ref['contract']).read_bytes())
    if double['nativeInputs']!=pins or children['effectVectors'].get('scalarNative',{}).get('status')!='validated':
        _fail('blackboard-double-child',pins,children['effectVectors'].get('scalarNative'))
    src=json.loads((CONTRACTS_DIR/ref['sourceContract']).read_bytes());double_context=src['nestedContexts'][double['rootContextIndex']]
    named.check_typed_context(image,double_context,'Beyond.Blackboard+BlackboardDouble',label=LABEL,fail=_fail)
    for key,field in (('postCircular','heightOffset'),('postCircular','rangeThreshold'),('postCircular','reverseFlag'),('postNavMesh','getNavPosInRangeRadius')):
        actual=context(key,field)
        if actual['typeDefinition']!=double_context['typeDefinition']:_fail('blackboard-double-type',double_context,actual,record=key,field=field)
    string_native=strings.validate_current_native_contract(gameassembly=gate.gameassembly,metadata=gate.metadata)
    string_member=next(m for m in c['records']['postCircular']['members'] if m['fieldName']=='indexKey')
    if string_native.get('status')!='validated' or string_native.get('nativeInputs')!=pins or string_member['sourceCall']['targetRva']not in string_native.get('sourceHelpers',[]):
        _fail('circular-string-source','independently validated nullable byte-length helper',string_native)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated':return {'status':after.status,'detail':after.detail,'nativeInputs':pins}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=pins['UnityPlayer.dll']:_fail('UnityPlayer.dll-after',pins['UnityPlayer.dll'],'mismatched')
    return {'status':'validated','nativeInputs':pins,'recordMembers':proved,'selectedTags':list(map(int,c['postprocessorDispatch'])),
            'blackboardIntMembers':int_names,'postprocessorDispatch':c['postprocessorDispatch'],
            'setterOwnedOutputs':{k:len(c['records'][k]['members']) for k in ('postCircular','postNavMesh')},
            'stringSourceHelpers':string_native['sourceHelpers'],'evidenceBoundary':c['evidenceBoundary']}

def decode_list(data,*,source,digest,start,end,children,target_decoder:Callable[...,dict]|None=None,depth=0):
    c=_contract();proof=children.get('selectorPostprocessors',{})
    if (proof.get('status')!='validated' or proof.get('nativeInputs')!=c['nativeInputs'] or proof.get('recordMembers')!=_members(c)
            or proof.get('selectedTags')!=list(map(int,c['postprocessorDispatch'])) or proof.get('postprocessorDispatch')!=c['postprocessorDispatch']
            or proof.get('blackboardIntMembers')!=['blackboardKey','useBlackboardKey','value']
            or proof.get('setterOwnedOutputs')!={k:len(c['records'][k]['members']) for k in ('postCircular','postNavMesh')}
            or next(m for m in c['records']['postCircular']['members'] if m['fieldName']=='indexKey')['sourceCall']['targetRva']not in proof.get('stringSourceHelpers',[])
            or any(children.get(k,{}).get('status')!='validated' or children[k].get('nativeInputs')!=c['nativeInputs'] for k in ('selector','selectorGeometry','target','findSettings','effectVectors'))
            or children['effectVectors'].get('scalarNative',{}).get('status')!='validated'
            or not isinstance(data,bytes) or not source or not isinstance(digest,str) or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
            or type(start)is not int or type(end)is not int or not 0<=start<end<=len(data)):
        raise ValueError(f'{LABEL}.decode:native-source-or-span')
    if type(depth)is not int or not 0<=depth<=DEPTH_LIMIT:raise ValueError(f'{LABEL}.decode:depth-limit')
    reader=Reader(data,source,end);reader.pos=start;count=reader.count(1,nullable=True);elements=[]
    def record(key):
        begin=reader.pos;fields=[];plan=c['records'][key]
        if reader.peek()==255:
            reader.take(1,'null-'+key)
            return {'start':begin,'end':reader.pos,'status':'exact-null-wrapper','namedFields':fields,'recursiveStoredSchemaExact':True}
        reader.header(len(plan['members']))
        for member in plan['members']:
            a=reader.pos;kind=member['kind'];value={}
            if kind in ('scalar32','raw4','byte'):value['rawHex']=reader.take(1 if kind=='byte' else 4,member['fieldName']).hex().upper()
            elif kind=='byte-payload':
                reader.byte_payload();value.update(rawHex=data[a:reader.pos].hex().upper(),payloadEncoding='unresolved')
            elif kind=='filter-profile':value['child']=record('buffFilter')
            elif kind=='finder-profile':
                reader.finder_profile()
                child=find_settings.decode_find_settings_child_receipt(data,source=source,logical_sha256=digest,
                    start=a,end=reader.pos,native_validation=children['findSettings'])
                if child.get('wholeChildSpanExact')is not True:raise ValueError(f'{LABEL}.decode:find-settings-child')
                value['child']={**child,'recursiveStoredSchemaExact':True}
            elif kind=='target-profile':
                reader.target_profile();span={'start':a,'end':reader.pos}
                if data[a:reader.pos]==b'\xff':child={**span,'status':'exact-null','recursiveStoredSchemaExact':True}
                else:
                    if depth==DEPTH_LIMIT:raise ValueError(f'{LABEL}.decode:depth-limit')
                    if not callable(target_decoder):raise ValueError(f'{LABEL}.decode:target-decoder-required')
                    child=target_decoder(data,source,digest,span,children,depth=depth+1)
                value['child']=child
            elif kind=='nullable-shape-list':
                n=reader.count(1,nullable=True);shapes=[geometry._shape(reader,source,digest,children) for _ in range(max(0,n))]
                if any(r.get('wholeStoredSpanExact')is not True for r in shapes):raise ValueError(f'{LABEL}.decode:shape-child')
                value['child']={'start':a,'end':reader.pos,'count':n,'elements':shapes,'recursiveStoredSchemaExact':True}
            elif kind=='scalar-payload':
                if member['declaredType']=='Beyond.Blackboard+BlackboardDouble':
                    reader.scalar_payload()
                    child=scalar.decode_adding_cooldown(data,a,reader.pos,native_validation=children['effectVectors']['scalarNative'])
                    if (child.get('wholeValueExact')is not True or child.get('startOffset')!=a or child.get('consumedEnd')!=reader.pos):
                        raise ValueError(f'{LABEL}.decode:blackboard-double-child')
                    value['child']={**child,'start':a,'end':reader.pos,'recursiveStoredSchemaExact':True,'runtimeValueKnown':False}
                else:
                    slots=[]
                    if reader.peek()==255:reader.take(1,'null-blackboard-int');child_status='exact-null'
                    else:
                        reader.header(3);child_status='named-blackboard-int-exact-span'
                        for name,read in zip(proof['blackboardIntMembers'],('byte-payload','byte','scalar32'),strict=True):
                            pos=reader.pos
                            if read=='byte-payload':reader.byte_payload()
                            else:reader.take(1 if read=='byte' else 4,name)
                            slots.append({'fieldName':name,'kind':read,'start':pos,'end':reader.pos,'rawHex':data[pos:reader.pos].hex().upper()})
                    value['child']={'start':a,'end':reader.pos,'status':child_status,'namedFields':slots,'recursiveStoredSchemaExact':True,'runtimeValueKnown':False}
            else:raise ValueError(f'{LABEL}.decode:unsupported-kind={kind}')
            if 'child' in value and (value['child'].get('recursiveStoredSchemaExact')is not True
                    or [value['child'].get('start'),value['child'].get('end')]!=[a,reader.pos]
                    or not begin<a<reader.pos<=end):raise ValueError(f'{LABEL}.decode:child-span={member["fieldName"]}')
            fields.append({'fieldName':member['fieldName'],'declaredType':member['declaredType'],'kind':kind,'start':a,'end':reader.pos,**value})
        return {'start':begin,'end':reader.pos,'status':'named-postprocessor-exact-span','typeName':plan['runtimeTypeName'],
                'namedFields':fields,'recursiveStoredSchemaExact':True}
    for _ in range(max(0,count)):
        at=reader.pos;tag=reader.nested_union_tag(proof['selectedTags'],'postprocessor')
        item=({'end':reader.pos,'status':'exact-null-union','namedFields':[],'recursiveStoredSchemaExact':True}
              if tag is None else record(c['postprocessorDispatch'][str(tag)]))
        elements.append({**item,'start':at,'tag':tag})
    if reader.pos!=end:raise ValueError(f'{LABEL}.decode:list-end={reader.pos}; expected={end}')
    return {'start':start,'end':end,'count':count,'elements':elements,'recursiveStoredSchemaExact':True,'runtimeTargetProcessingKnown':False}

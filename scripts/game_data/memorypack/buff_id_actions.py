"""Native-gated one-member BuffId values and lists in typed action fields.

The selected source and setter join names the stored string. A single value
has its own nullable member-one header; a list adds a separate signed count.
Neither format is the three-member BlackboardBuffId. Callers independently
prove the parent type before composing the original child span. Runtime ID
lookup and live formatter selection remain unresolved.
The cooldown actions' plain ``buffId`` strings remain separate from the
one-member BuffId wrapper. AddGlobalCDTimer also has an independently typed
BlackboardDouble ``cdTime`` and TargetSettings ``target``; stored fields do
not establish the evaluated duration, target selection or applied timer.
"""
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import buff_selector_shared_children as query
from scripts.game_data.memorypack import named_native_records as records_native

CONTRACT_PATH=CONTRACTS_DIR / 'buff_id_actions_native.json'
LABEL='buffIdActions'


def _contract():
    value=json.loads(CONTRACT_PATH.read_bytes())
    if value.get('schema')!='endfield.buff-buff-id-actions-native-contract.v2' or value.get('status')!='exact-current-build':
        raise ValueError(f'{LABEL}.contract:shape')
    return value


def supported_tags():
    return frozenset(row['unionTag'] for row in _contract()['routes'])


def _source_kinds(spec, source):
    aliases=spec.get('readKindAliases',{})
    allowed={'bytePayload':'byte-payload','scalarPayload':'scalar-payload','target':'target-profile'}
    if any(allowed.get(k)!=v for k,v in aliases.items()):
        fail('source-kind-alias',allowed,aliases,spec['unionTag'])
    return [aliases.get(k,k) for k in source['anonymousReadOrder'][spec['sourceReadOrder']]]


def fail(check,expected,actual,tag=None):
    def bounded(value):
        if isinstance(value,str):return value[:256]
        if isinstance(value,dict):return {str(k):bounded(v) for k,v in list(value.items())[:16]}
        if isinstance(value,(list,tuple)):return [bounded(v) for v in value[:16]]
        return value
    contract=_contract();spec=next((r for r in contract['routes'] if r['unionTag']==tag),None)
    source=CONTRACTS_DIR/spec['sourceContract'] if spec else CONTRACT_PATH
    exc=CensusGateError(f'{LABEL}.{check}',source=source.as_posix(),expected=bounded(expected),actual=bounded(actual))
    exc.diagnostic.update({'validator':LABEL,'family':'AbilityActionData','unionTag':tag,'nativeInputs':contract['nativeInputs']})
    exc.args=(json.dumps(exc.diagnostic,sort_keys=True),);raise exc


def validate_current_native_contract():
    contract=_contract();expected=contract['nativeInputs']
    gate=check_installed_native_inputs(expected['GameAssembly.dll'],expected['global-metadata.dat'])
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'nativeInputs':expected}
    if 'UnityPlayer.dll' in expected:
        unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
        actual=hashlib.sha256(unity.read_bytes()).hexdigest().upper() if unity.is_file() else 'missing'
        if actual!=expected['UnityPlayer.dll']:fail('UnityPlayer.dll',expected['UnityPlayer.dll'],actual)
    image=open_native_image(gate.gameassembly,gate.metadata)
    catalog=json.loads((CONTRACTS_DIR/contract['catalogContract']).read_bytes())
    routes,audit=load_action_routes(gameassembly=gate.gameassembly,metadata=gate.metadata)
    if audit.get('status')!='validated':fail('dispatcher-status','validated',audit.get('status'))
    native={}
    for spec in contract['routes']:
        tag=spec['unionTag'];source=json.loads((CONTRACTS_DIR/spec['sourceContract']).read_bytes())
        # Existing reviewed owner verifies native methods/windows, every generic
        # carrier/element and the shared list source proof without inventing widths.
        buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,image.modules,image.owners,
                               source=str(gate.gameassembly),contract_path=CONTRACTS_DIR/spec['sourceContract'])
        route=routes[tag];kinds=_source_kinds(spec,source)
        reviewed=catalog['families']['AbilityActionData'][tag]
        if reviewed['wrappedType']!=spec['wrappedType'] or route.wrapper_name!=reviewed['wrapperName']:
            fail('parent-type',reviewed,{'wrappedType':spec['wrappedType'],'wrapperName':route.wrapper_name},tag)
        if route.status!='resolved' or len(route.member_order)!=len(kinds) or route.inherited_member_count!=4:
            fail('parent-wrapper',{'count':len(kinds),'inherited':4},route.row(),tag)
        if [route.member_order[i] for i in spec['contextMemberIndices']]!=spec['contextFieldNames']:
            fail('parent-field-names',spec['contextFieldNames'],list(route.member_order),tag)
        contexts=source['nestedContexts']
        indices=spec.get('contextSourceIndices',list(range(len(contexts))))
        if (indices!=sorted(set(indices)) or any(type(i) is not int or not 0<=i<len(contexts) for i in indices)
            or len(indices)!=len(spec['contextMemberIndices'])):
            fail('context-count',len(spec['contextMemberIndices']),indices,tag)
        contexts=[contexts[i] for i in indices]
        joins=[]
        for context,index,name in zip(contexts,spec['contextMemberIndices'],spec['contextTypeNames'],strict=True):
            argument=image.instantiations.resolve(context['methodSpec'][2]).arguments[0]
            actual=runtime_type_name(image.pe,image.metadata,argument.type_pointer_va)
            if actual!=name or route.member_declared_types[index]!=name:
                fail('typed-source-field',name,{'context':actual,'field':route.member_declared_types[index]},tag)
            joins.append({'index':index,'fieldName':route.member_order[index],'declaredType':name})
        primitives={'byte':('bool',1),'scalar32':(None,4),'byte-payload':('string',None),
                    'counted-member1-payloads':('list',None),'target-profile':('object',None),
                    'query-profile':('object',None),'scalar-payload':('object',None)}
        for i,kind in enumerate(kinds):
            expected_kind,width=primitives[kind]
            if ((expected_kind and route.member_kinds[i]!=expected_kind) or (width and route.member_widths[i]!=width)
                or (kind=='scalar32' and route.member_kinds[i] not in ('enum','scalar32','float32'))):
                fail('source-kind',{'index':i,'kind':kind},{'kind':route.member_kinds[i],'width':route.member_widths[i]},tag)
        named={}
        if spec.get('namedRecord'):
            key=spec['namedRecord'];record=contract['namedRecords'][key]
            def named_fail(check,wanted,actual,**kw):
                try:fail(check,wanted,actual,tag)
                except CensusGateError as error:
                    error.diagnostic.update(record=key,field=kw.get('field',''))
                    error.args=(json.dumps(error.diagnostic,sort_keys=True),)
                    raise
            named=records_native.validate_named_records(image,source,{key:record},label=LABEL,fail=named_fail)
        native[tag]={'status':'validated','nativeInputs':expected,'unionTag':tag,'memberNames':list(route.member_order),
                     'readKinds':kinds,'typedChildren':joins,'wrappedType':spec['wrappedType']}
        if named:native[tag]['recordMembers']=named
    child=contract['child'];owner=image.metadata.types[child['wrapperTypeDefinition']]
    if image.metadata.type_full_name(owner)!=child['wrapperName']:fail('child-wrapper',child['wrapperName'],image.metadata.type_full_name(owner))
    expected_setter=[[child['setterMethod'][0],child['setterMethod'][2],child['setterParameterType']]]
    if image.setter_methods(owner,parameter='typeName')!=expected_setter:fail('child-setter',expected_setter,image.setter_methods(owner,parameter='typeName'))
    image.validate_method_row(child['readerMethod'],label=LABEL);image.validate_method_row(child['setterMethod'],label=LABEL)
    image.check_windows([child['setterWindow']],label=LABEL);image.check_instruction_windows(child['sourceInstructions'],label=LABEL)
    return {'status':'validated','nativeInputs':expected,'routes':native,'child':{'status':'validated','nativeInputs':expected,
            'memberName':child['memberName'],'serializedMemberCount':child['serializedMemberCount']}}


def _id_reader(data,source,digest,start,end,native,kind):
    child=_contract()['child']
    if (native.get('status')!='validated' or native.get('nativeInputs')!=_contract()['nativeInputs']
        or native.get('memberName')!=child['memberName'] or native.get('serializedMemberCount')!=1):
        raise ValueError(f'{LABEL}.{kind}:native-not-validated')
    if (not isinstance(data,bytes) or not source or not isinstance(digest,str)
        or type(start) is not int or type(end) is not int or not 0<=start<end<=len(data)
        or hashlib.sha256(data).hexdigest().upper()!=digest.upper()):
        raise ValueError(f'{LABEL}.{kind}:source')
    reader=Reader(data,source,end);reader.pos=start
    return reader,child


def _read_id_value(reader,data,child):
    begin=reader.pos
    if reader.peek()==255:
        reader.take(1,'null-buff-id');value={'status':'exact-null','namedFields':[]}
    else:
        reader.header(1);a=reader.pos;reader.byte_payload()
        value={'status':'named-one-member-exact','namedFields':[{'name':child['memberName'],'declaredType':'string',
                'start':a,'end':reader.pos,'rawHex':data[a:reader.pos].hex().upper()}]}
    return {'start':begin,'end':reader.pos,**value,'recursiveNamedSchemaExact':True}


def decode_id_value(data,source,digest,start,end,native):
    """Name one independently typed BuffId value without adding list framing."""
    reader,child=_id_reader(data,source,digest,start,end,native,'value')
    value=_read_id_value(reader,data,child)
    if reader.pos!=end:raise ValueError(f'{LABEL}.value:end')
    return {**value,'wholeStoredSpanExact':True}


def decode_id_list(data,source,digest,start,end,native):
    reader,child=_id_reader(data,source,digest,start,end,native,'list')
    count=reader.count(1,nullable=True);values=[]
    for _ in range(max(0,count)):
        values.append(_read_id_value(reader,data,child))
    if reader.pos!=end:raise ValueError(f'{LABEL}.list:end')
    return {'start':start,'end':end,'count':count,'elements':values,'wholeStoredSpanExact':True,'recursiveNamedSchemaExact':True}


def decode_action(data,*,source,digest,start,end,tag,native_validation):
    from scripts.game_data.memorypack import buff_recursive_actions as shared
    children=native_validation['children'];packet=children['buffIdActions'];native=packet['routes'][tag]
    contract=_contract();spec=next(r for r in contract['routes'] if r['unionTag']==tag)
    source_contract=json.loads((CONTRACTS_DIR/spec['sourceContract']).read_bytes())
    kinds=_source_kinds(spec,source_contract)
    reviewed=json.loads((CONTRACTS_DIR/contract['catalogContract']).read_bytes())['families']['AbilityActionData'][tag]
    expected_joins=[{'index':i,'fieldName':name,'declaredType':typ} for i,name,typ in
                    zip(spec['contextMemberIndices'],spec['contextFieldNames'],spec['contextTypeNames'],strict=True)]
    if (packet.get('status')!='validated' or packet.get('nativeInputs')!=contract['nativeInputs']
        or native.get('status')!='validated' or native.get('nativeInputs')!=contract['nativeInputs']
        or native.get('unionTag')!=tag or native.get('readKinds')!=kinds
        or len(native.get('memberNames',[]))!=reviewed['memberCount']
        or native.get('wrappedType')!=reviewed['wrappedType'] or native.get('typedChildren')!=expected_joins
        or [native['memberNames'][i] for i in spec['contextMemberIndices']]!=spec['contextFieldNames']
        or hashlib.sha256(data).hexdigest().upper()!=digest.upper() or not 0<=start<end<=len(data)):
        raise ValueError(f'{LABEL}.action:native-or-source')
    if spec.get('namedRecord'):
        key=spec['namedRecord'];record=contract['namedRecords'][key]
        names=[m['fieldName'] for m in record['members']]
        expected={key:[{'fieldName':m['fieldName'],'kind':m['kind']} for m in record['members']]}
        if (native_validation.get('status')!='validated' or native_validation.get('nativeInputs')!=contract['nativeInputs']
            or native.get('recordMembers')!=expected or native['memberNames']!=names):
            raise ValueError(f'{LABEL}.action:named-record-drift')
    reader=Reader(data,source,end);reader.pos=start
    if reader.nested_union_tag(tuple(r['unionTag'] for r in contract['routes']),'buff-id-action')!=tag:raise ValueError(f'{LABEL}:tag')
    reader.header(len(native['memberNames']));fields=[]
    for name,kind in zip(native['memberNames'],native['readKinds'],strict=True):
        a=reader.pos;value={}
        if kind in ('byte','scalar32'):value['rawHex']=reader.take(1 if kind=='byte' else 4,name).hex().upper()
        elif kind=='byte-payload':reader.byte_payload();value['rawHex']=data[a:reader.pos].hex().upper()
        elif kind=='counted-member1-payloads':
            for _ in range(max(0,reader.count(1,nullable=True))):reader.single_payload()
            value['child']=decode_id_list(data,source,digest,a,reader.pos,packet['child'])
        elif kind=='query-profile':
            reader.query_profile();value['child']=query.decode_query_value(data,source=source,digest=digest,start=a,end=reader.pos,native=children['findSettings'])
        elif kind=='target-profile':
            reader.target_profile()
            if reader.pos==a+1 and data[a]==0xFF:
                value['child']={'status':'exact-null','start':a,'end':reader.pos,'recursiveStoredSchemaExact':True}
            else:value['child']=shared.recursive_target(data,source,digest,{'start':a,'end':reader.pos},children)
            if value['child'].get('recursiveStoredSchemaExact') is not True:raise ValueError(f'{LABEL}.action:target-child')
            if spec.get('namedRecord') and [value['child'].get('start'),value['child'].get('end')]!=[a,reader.pos]:
                raise ValueError(f'{LABEL}.action:target-child-span')
        elif kind=='scalar-payload':
            reader.scalar_payload();value['child']=shared.blackboard.child.decode_adding_cooldown(data,a,reader.pos,native_validation=children['blackboard']['childNative'])
            if (value['child'].get('wholeValueExact') is not True
                or [value['child'].get('startOffset'),value['child'].get('consumedEnd')]!=[a,reader.pos]):
                raise ValueError(f'{LABEL}.action:scalar-child-span')
        else:raise ValueError(f'{LABEL}:unsupported-kind={kind}')
        fields.append({'name':name,'kind':kind,'start':a,'end':reader.pos,**value})
    if reader.pos!=end:raise ValueError(f'{LABEL}.action:end')
    return {'schema':'endfield.buff-recursive-action-receipt.v1','tag':tag,'start':start,'end':end,
            'namedFields':fields,'recursiveStoredSchemaExact':True,'runtimeMeaningExact':False}

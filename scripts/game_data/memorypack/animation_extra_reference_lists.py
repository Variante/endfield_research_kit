"""Finite animation Extra reference lists with independent element grammars.

The actual closed ReadPackable calls select the generic source again. Its
fresh/reused-empty loop has an independently checked bound. Each reference
element separately owns its canonical callback and generated wire; provider
selection, normal allocation and disabled collectors remain conditions.
"""
import json

PREFIX='Beyond.Gameplay.View.Animation.'
IDLE=PREFIX+'SpecialIdleCondition'
TYPES=(PREFIX+'CharacterSpecialDashEntry',PREFIX+'SpecialIdleEntry','string',IDLE)
SCHEMA='endfield.animation-extra-reference-lists.v1'
SOURCE_SCHEMA='endfield.animation-extra-reference-list-source.v1'
WIRE='animation-extra-reference-list'
MEMBERS={
    (PREFIX+'CharacterSpecialDashConfig',0,'entries',TYPES[0]),
    (PREFIX+'CharacterSpecialDashConfig',2,'spDashes','string'),
    (PREFIX+'CharacterSpecialIdleConfig',0,'entries',TYPES[1]),
    (PREFIX+'CharacterSpecialIdleConfig',1,'spIdles','string'),
    (PREFIX+'TransformInSightCondition',0,'targetPaths','string'),
    (PREFIX+'SpecialIdleEntry',0,'_conditions',IDLE),
}


def need(check,condition):
    if not condition:raise ValueError('animationExtraReferenceLists.'+check)


def norm(value):return json.loads(json.dumps(value))
def key(name):need('finite-own-element',name in TYPES);return WIRE+':'+name
def list_type(name):return 'System.Collections.Generic.List`1<'+name+'>'


def verify_source(actual,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack import reference_list_induction_sources as induction,pooled_string_list_sources as lists
    from scripts.game_data.memorypack import skill_cost_data_list_sources as common,lang_key_list_sources as lang
    need('own-finite-source',actual.get('schema')==SOURCE_SCHEMA and actual.get('nativeInputs')==pins
        and actual.get('elementType')in TYPES and actual.get('closedListType')==list_type(actual['elementType'])
        and actual.get('elementGrammarAdmitted')is False and actual.get('parentFieldAdmitted')is False
        and actual.get('wholeOwnerAdmitted')is False)
    p=actual['proof'];native=p['source'];w=native['witnessComponent'];base=p['imageBase']
    need('literal-selected-image-base',type(base)is int and base>=1<<32)
    need('same-native-induction-domain',native.get('status')=='validated-bounded-reference-list-induction'
        and native.get('nativeInputs')==pins and native.get('elementType')==actual['elementType']
        and w.get('nativeInputs')==pins and w.get('elementType')==actual['elementType']
        and w.get('elementRuntimeBytes')==8 and w.get('headerBytes')==4)
    rebuilt=induction._certificate(w,count_limit=4096)
    need('exact-complete-bounded-certificate',all(native.get(k)==norm(v)for k,v in rebuilt.items()))
    raw=regions(w['windows'],p['sourceRegions'],base,'extra-reference-list')
    offsets=p['readerOffsets'];symbols={k:base+v for k,v in w['symbols'].items()}
    paths=[lists.list_source(raw,w['entry']['pointer'],offsets,symbols,count=n,new=new,grow=False,count_limit=3)
        for n in range(-1,4)for new in(True,False)]
    need('every-fresh-and-reused-empty-count-path',norm(paths)==w['programs'])
    for role,windows,target,expected,canonical in(
        ('clear',w['clearWindows'],symbols['clear'],w['clearProgram'],False),
        ('canonicalClear',w['canonicalClearWindows'],w['clearEntry']['pointer'],w['canonicalClearProgram'],True)):
        own=regions(windows,p[role+'Regions'],base,'extra-reference-list-'+role)
        need('independent-'+role+'-empty-program',norm(common.reference_clear_zero(own,target,canonical=canonical))==expected)
    provider=regions(w['providerWindows'],p['providerRegions'],base,'extra-reference-list-provider')
    need('exact-own-context-and-provider',norm(lang.wrapper_provider_program(provider,symbols['provider'],{k:base+v for k,v in w['providerSymbols'].items()}))==w['providerProgram']
        and w['typedRequest']['methodSpec'][0]>=0 and w['closedCarrier'].get('name')==actual['closedListType']
        and tuple(w['typedRequest'].get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
            (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[actual['closedListType']]))
    return w,base


def derive_source(image,pins,*,typed_request,call_target,element_type):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import reference_list_induction_sources as induction,scalar_param_native as scalar
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);need('finite-actual-Extra-element',element_type in TYPES);base=image.pe.image_base
    native=induction.derive(image,pins,typed_request=typed_request,call_target=call_target,element_type=element_type,count_limit=4096)
    w=native['witnessComponent'];ctx=NativeReferenceContext(image);offsets=scalar.reader_offsets(image,'animationExtraReferenceLists')
    offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    def capture(target):return [[a-base,raw.hex()]for a,raw in owned(image,target)['regions']]
    value=dict(schema=SOURCE_SCHEMA,nativeInputs=pins,elementType=element_type,closedListType=list_type(element_type),
        proof=dict(source=native,imageBase=base,readerOffsets=offsets,sourceRegions=capture(w['entry']['pointer']),
            clearRegions=capture(base+w['symbols']['clear']),canonicalClearRegions=capture(w['clearEntry']['pointer']),
            providerRegions=capture(base+w['symbols']['provider'])),
        elementGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    value=norm(value);verify_source(value,pins);_publication_gate(image,pins);return value


def _string(callback,pins,base):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.pooled_string_list_sources import pooled_string
    need('independent-actual-STRING14-callback',callback.get('schema')=='endfield.animation-custom-pooled-string-callback.v1'
        and callback.get('status')=='validated-conditional-callback'and callback.get('nativeInputs')==pins
        and callback.get('typeName')=='string'and callback.get('wireBytes')==4 and callback.get('outputBytes')==8
        and callback.get('callbackSlot')==5 and callback.get('actualRuntimeSelectionObserved')is False)
    p=callback['proof'];raw=regions(p['windows'],p['regions'],base,'extra-list-string-callback')
    parsed=[pooled_string(raw,base+callback['callbackTargetRva'],{k:base+v for k,v in p['symbolRvas'].items()},mode=m)for m in('lookup','empty','null')]
    need('all-STRING14-pool-index-paths',norm(parsed)==p['programs'])
    return callback['callbackTargetRva'],callback['callbackMethodDefinition']


def compose(actual,child,pins):
    w,base=verify_source(actual,pins);name=actual['elementType'];ownkey=key(name)
    if name=='string':
        target,definition=_string(child,pins,base);caps={};external=['byte-payload'];element='byte-payload';shape=None
    else:
        if name==IDLE:
            from scripts.game_data.memorypack.animation_idle_condition_components import validate_component,CAPABILITY
            own=validate_component(child,pins);element=own['capability']
            need('own-independent-idle-union',element==CAPABILITY)
        else:
            from scripts.game_data.memorypack.animation_extra_record_components import validate_component,record_key
            own=validate_component(child,pins);element=own['capability'];need('own-reference-record-key',element==record_key(name))
        shape=own['capabilities'][element]
        element_raw=bytes.fromhex(w['closedCarrier']['classArguments'][0]['rawHex'])
        need('own-complete-ordinary-reference-element',shape.get('typeName')==name
            and shape.get('valueStorageKind')=='reference8'and shape.get('wholeGrammarAdmitted')is True
            and shape.get('ordinaryOriginalCallbackAdmitted')is True and shape.get('ordinaryOriginalReadValueAdmitted')is True
            and len(element_raw)==16 and element_raw[10:12]==b'\x12\x00'
            and int.from_bytes(element_raw[:8],'little')==shape['originalTypeDefinition'])
        target=shape['canonicalAdapterTargetRva'];definition=shape['formatterDeserializeMethodDefinition'];caps=dict(own['capabilities']);external=own['requiredExternalCapabilities']
    cap=dict(typeName=list_type(name),closedListType=list_type(name),elementType=name,elementValueType=False,
        elementCapability=element,elementCapabilityShape=shape,headerBytes=4,countLimit=4096,countRange=[-1,4096],nullable=True,
        positiveCountsAdmitted=True,wholeGrammarAdmitted=True,elementGrammarAdmitted=True,
        freshListsAdmitted=True,reusedListsRequireInitialCount=0,reusedListsRequireCapacityAtLeastCount=True,
        actualCallbackEqualsCanonicalRequired=True,liveFormatterSelectionObserved=False,
        canonicalAdapterTargetRva=target,formatterDeserializeMethodDefinition=definition,
        packableReaderMethodDefinition=w['typedRequest']['methodSpec'][0],packableReaderTargetRva=w['callTargetRva'],
        parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    caps[ownkey]=cap
    return dict(schema=SCHEMA,status='validated-conditional-animation-extra-reference-list',nativeInputs=pins,
        capability=ownkey,capabilities=caps,requiredExternalCapabilities=external,proof=dict(listSource=actual,element=child),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def validate_component(component,pins):
    need('own-composed-list',component.get('schema')==SCHEMA and component.get('status')=='validated-conditional-animation-extra-reference-list'
        and component.get('nativeInputs')==pins and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    checked=compose(component['proof']['listSource'],component['proof']['element'],pins)
    need('all-and-only-independently-owned-caps',all(component.get(k)==checked[k]for k in('capability','capabilities','requiredExternalCapabilities')))
    return dict(capability=checked['capability'],capabilities=checked['capabilities'],requiredExternalCapabilities=checked['requiredExternalCapabilities'])


def derive_member(image,pins,*,parent_source,member_index,element_component=None):
    """Fresh actual caller/list/child join for one finite declared field."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import derive_string
    _publication_gate(image,pins);read=parent_source['orderedSourceReads'][member_index]
    need('one-actual-declared-list-member',type(member_index)is int and read.get('memberIndex')==member_index
        and read.get('declaredType','').startswith('System.Collections.Generic.List`1<'))
    element=read['declaredType'][len('System.Collections.Generic.List`1<'):-1]
    need('exact-finite-parent-and-element',(parent_source.get('wrappedType'),member_index,read.get('fieldName'),element)in MEMBERS)
    image.validate_method_row(parent_source['method']);image.check_windows(parent_source['codeWindows'])
    usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='animationExtraReferenceLists.parent')
    actual=derive_source(image,pins,typed_request=usage,call_target=image.pe.image_base+read['sourceTargetRva'],element_type=element)
    if element=='string':
        need('independent-pooled-callback-selected-here',element_component is None);child=derive_string(image,pins)
    else:
        need('independent-concrete-element-component-required',isinstance(element_component,dict));child=element_component
    result=norm(compose(actual,child,pins))
    bind_member(parent_source,parent_source['sourceScope'],read,pins,usage,result,result['capability'])
    _publication_gate(image,pins);return result


def bind_member(full,scope,read,pins,usage,component,capability):
    own=validate_component(component,pins);cap=own['capabilities'][own['capability']];index=read['memberIndex']
    need('finite-actual-Extra-list-field',(full.get('wrappedType'),index,read.get('fieldName'),cap['elementType'])in MEMBERS
        and full.get('schema')=='endfield.generated-concrete-reader-source.v1'and full.get('nativeInputs')==pins
        and full.get('completeSelectedCallerAdmitted')is True and full.get('sourceScope')==scope
        and full['orderedSourceReads'][index]==scope['events'][index]==read and read.get('declaredType')==cap['closedListType']
        and read.get('kind')=='reference:'+cap['closedListType']and read.get('context',{}).get('methodName')=='ReadPackable'
        and read['context'].get('methodSpec')==usage.get('methodSpec')and read['context'].get('instructionRva')==usage.get('instructionRva')
        and component['proof']['listSource']['proof']['source']['witnessComponent']['typedRequest']==usage
        and capability==own['capability']and read.get('sourceTargetRva')==cap['packableReaderTargetRva'])
    raw=bytes.fromhex(read['instruction'][1]);need('actual-E8-to-own-ReadPackable',len(raw)==5 and raw[0]==232
        and read['instruction'][0]+5+int.from_bytes(raw[1:],'little',signed=True)==read['sourceTargetRva'])
    setter=full['setters'][index]
    need('whole-own-list-reference-setter',setter.get('incomingValueStoredUnchanged')is True and setter.get('storedBytes')==8
        and setter.get('targetField')==full['wrappedType']+'::'+read['fieldName'])
    if 'richProgram'in scope:
        rich=scope['richProgram'];stores=[s for s in rich.get('fieldStores',[])if s.get('memberIndex')==index]
        flows=[s for s in rich.get('sources',[])if s.get('memberIndex')==index]
        need('whole-own-list-RAX-to-named-field',rich.get('completeSelectedNormalProgram')is True and rich.get('selectedProgram')==scope.get('selectedProgram')
            and flows==[dict(memberIndex=index,instruction=read['instruction'],resultAbi='rax')]
            and len(stores)==1 and(stores[0].get('sourceOffset'),stores[0].get('storedBytes'))==(0,8)
            and stores[0]['instruction']in scope['selectedProgram']and scope['richSetters'][index]==setter)
        at,hexcode=stores[0]['instruction']
    else:
        transfers=[r for r in scope.get('setterTransfers',[])if r.get('memberIndex')==index]
        need('one-complete-ordinary-list-transfer',len(transfers)==1);transfer,=transfers
        code=scope.get('selectedProgram',[]);receiver=transfer.get('receiver');moves={'rsi':'488bce','rbx':'488bcb','rdi':'488bcf'}
        need('exact-whole-ordinary-RAX-RDX-list-transfer',transfer.get('sourceCall')==read['instruction']
            and transfer.get('returnAbi')=='rax'and receiver in moves
            and transfer.get('setterTargetRva')==setter['method'][3]
            and transfer.get('transfer',[0,''])[1].lower()=='488bd0'
            and all(transfer.get(k)in code for k in('sourceCall','transfer','setterCall','wrapperLoad')))
        position=code.index(transfer['transfer'])
        need('exact-owned-named-call-arguments',position>0 and position+2<len(code)
            and code[position-1][1].lower()=='4533c0'and code[position+1][1].lower()==moves[receiver]
            and code[position+2]==transfer['setterCall'])
        need('same-full-transfer-in-both-positive-frames',all(all(row in p.get('selectedProgram',[])for row in code)
            for p in full['programs']if not p['wrapperNull']))
        at,hexcode=transfer['setterCall']
    encoded=bytes.fromhex(hexcode)
    need('actual-complete-setter-call',len(encoded)==5 and encoded[0]in(232,233)
        and at+5+int.from_bytes(encoded[1:],'little',signed=True)==setter['method'][3])
    frames=full['programs'];need('all-four-return-frames',len(frames)==4
        and{(p.get('existing'),p.get('wrapperNull'))for p in frames}=={(False,False),(True,False),(False,True),(True,True)}
        and all(p['frame'].get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in frames))
    return dict(fieldName=read['fieldName'],typeName=cap['closedListType'],capability=capability,
        readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=read['sourceTargetRva'],allFourParentFramesProved=True)


def read(reader,capability,*,depth=0,budget=None):
    import struct
    need('bounded-depth',type(depth)is int and 0<=depth<64);cap=reader.operation.child(capability);name=cap.get('elementType')
    need('complete-own-reference-list-capability',name in TYPES and capability==key(name)
        and cap.get('closedListType')==list_type(name)and cap.get('typeName')==list_type(name)
        and cap.get('elementValueType')is False and cap.get('countLimit')==4096 and cap.get('countRange')==[-1,4096]
        and all(cap.get(k)is True for k in('nullable','positiveCountsAdmitted','wholeGrammarAdmitted','elementGrammarAdmitted',
            'freshListsAdmitted','reusedListsRequireCapacityAtLeastCount','actualCallbackEqualsCanonicalRequired'))
        and cap.get('reusedListsRequireInitialCount')==0 and cap.get('liveFormatterSelectionObserved')is False)
    child=reader.operation.child(cap['elementCapability'])
    if name=='string':need('actual-pool-capability',cap['elementCapability']=='byte-payload'and child.get('wireBytes')==4
        and child.get('wholeGrammarAdmitted')is True and child.get('encoding')=='int32-pool-index'
        and child.get('emptyIndex')==-1 and child.get('nullIndex')==-2)
    else:need('same-independent-own-element',child==cap['elementCapabilityShape']and child.get('typeName')==name
        and child.get('ordinaryOriginalCallbackAdmitted')is True and child.get('wholeGrammarAdmitted')is True)
    at=reader.pos;need('complete-count',at+4<=reader.limit);count=struct.unpack_from('<i',reader.data,at)[0]
    need('bounded-count',-1<=count<=4096)
    need('minimum-element-bytes',at+4+(4 if name=='string'else 1)*max(0,count)<=reader.limit)
    if budget is None:budget=dict(remaining=16384)
    need('shared-budget',type(budget)is dict and set(budget)=={'remaining'}and type(budget['remaining'])is int
        and 1+max(0,count)<=budget['remaining']<=16384)
    budget['remaining']-=1;reader.take(4,capability+'.count');entries=[]
    for _ in range(max(0,count)):
        if name=='string':budget['remaining']-=1;entries.append(dict(value=reader.byte_payload()))
        elif name==IDLE:
            from scripts.game_data.memorypack.animation_idle_condition_codec import read as read_idle
            entries.append(read_idle(reader,depth=depth+1,budget=budget))
        else:entries.append(reader.extra_record(cap['elementCapability'],depth=depth+1,budget=budget))
    result=dict(kind=capability,start=at,end=reader.pos,isNull=count==-1,count=count,elements=entries)
    reader.records.append(result);return result

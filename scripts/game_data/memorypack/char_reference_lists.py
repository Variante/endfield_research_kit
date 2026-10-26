"""Own CharInteract reference lists, separate from each element's wire grammar."""
import json,struct
from scripts.game_data.memorypack import reference_list_value_sources as source

PREFIX='Beyond.Gameplay.Core.CharInteractPerform.'
TYPES=(PREFIX+'CharInteractPerformActionData',PREFIX+'CharInteractPerformActor',
       PREFIX+'SubSpecialPerformEntry',PREFIX+'SpecialSubPerformCondition','string')
SCHEMA='endfield.char-interact-reference-list-components.v1'
WIRE='char-interact-reference-list'


def need(check,condition):
    if not condition:raise ValueError('charReferenceLists.'+check)


def norm(value):return json.loads(json.dumps(value))
def key(name):need('finite-own-element',name in TYPES);return WIRE+':'+name
def list_type(name):return source.list_type(name)


def _element(child,pins,name):
    if name=='string':
        from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
        from scripts.game_data.memorypack.pooled_string_list_sources import pooled_string
        need('own-string-callback-source',child.get('schema')=='endfield.animation-custom-pooled-string-callback.v1'
            and child.get('status')=='validated-conditional-callback'and child.get('nativeInputs')==pins
            and child.get('typeName')=='string'and child.get('wireBytes')==4 and child.get('outputBytes')==8
            and child.get('callbackSlot')==5 and child.get('actualRuntimeSelectionObserved')is False)
        p=child['proof'];base=p['programs'][0]['selectedBytes'][0][0]-child['callbackTargetRva']
        raw=regions(p['windows'],p['regions'],base,'char-pooled-string')
        parsed=[pooled_string(raw,base+child['callbackTargetRva'],{k:base+v for k,v in p['symbolRvas'].items()},mode=m)for m in('lookup','empty','null')]
        need('own-complete-pool-index-callback',norm(parsed)==p['programs'])
        return dict(capability='byte-payload',shape=None,capabilities={},requiredExternalCapabilities=['byte-payload'],
            target=child['callbackTargetRva'],definition=child['callbackMethodDefinition'],wire='byte-payload')
    if child.get('schema')=='endfield.char-interact-record-components.v1':
        from scripts.game_data.memorypack.char_record_components import validate_component
        wire='char-interact-record'
    else:
        from scripts.game_data.memorypack.char_union_components import validate_component
        wire='char-interact-union'
    own=validate_component(child,pins);cap=own['capabilities'][own['capability']]
    need('own-complete-reference-element',cap.get('typeName')==name and cap.get('wholeGrammarAdmitted')is True
        and cap.get('valueStorageKind')=='reference8'and cap.get('ordinaryOriginalReadValueAdmitted')is True
        and cap.get('ordinaryOriginalCallbackAdmitted')is True and type(cap.get('originalTypeDefinition'))is int
        and type(cap.get('canonicalAdapterTargetRva'))is int and type(cap.get('formatterDeserializeMethodDefinition'))is int)
    return dict(capability=own['capability'],shape=cap,capabilities=own['capabilities'],requiredExternalCapabilities=own['requiredExternalCapabilities'],
        target=cap['canonicalAdapterTargetRva'],definition=cap['formatterDeserializeMethodDefinition'],wire=wire)


def compose(native,child,pins):
    name=native.get('elementType');need('finite-own-element-source',name in TYPES)
    witness,base=source.verify_source(native,pins);element=_element(child,pins,name)
    carrier,=witness['closedCarrier']['classArguments'];raw=bytes.fromhex(carrier['rawHex'])
    need('own-nominal-reference-carrier',len(raw)==16 and carrier.get('name')==name
        and(raw[10:12]==bytes((14,0))if name=='string'else raw[10:12]==bytes((18,0))
            and int.from_bytes(raw[:8],'little')==element['shape']['originalTypeDefinition']))
    capability=key(name);caps=dict(element['capabilities'])
    caps[capability]=dict(typeName=list_type(name),closedListType=list_type(name),elementType=name,elementValueType=False,
        elementCapability=element['capability'],elementCapabilityShape=element['shape'],elementWire=element['wire'],
        headerBytes=4,countLimit=native['countLimit'],countRange=[-1,native['countLimit']],nullable=True,
        positiveCountsAdmitted=True,wholeGrammarAdmitted=True,elementGrammarAdmitted=True,
        freshListsAdmitted=True,reusedListsRequireInitialCount=0,reusedListsRequireCapacityAtLeastCount=True,
        actualCallbackEqualsCanonicalRequired=True,liveFormatterSelectionObserved=False,
        canonicalAdapterTargetRva=element['target'],formatterDeserializeMethodDefinition=element['definition'],
        sourceMethodSpec=witness['typedRequest']['methodSpec'],packableReaderMethodDefinition=witness['typedRequest']['methodSpec'][0],
        packableReaderTargetRva=witness['callTargetRva'],parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    return dict(schema=SCHEMA,status='validated-conditional-char-interact-reference-list',nativeInputs=pins,
        capability=capability,capabilities=caps,requiredExternalCapabilities=element['requiredExternalCapabilities'],
        proof=dict(listSource=native,element=child),parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def validate_component(component,pins):
    need('own-selected-list-component',component.get('schema')==SCHEMA
        and component.get('status')=='validated-conditional-char-interact-reference-list'and component.get('nativeInputs')==pins
        and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    p=component['proof'];checked=compose(p['listSource'],p['element'],pins)
    need('same-full-list-and-element-join',checked==component)
    return {k:checked[k]for k in('capability','capabilities','requiredExternalCapabilities')}


def derive(image,pins,*,typed_request,call_target,element_type,element_component=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins);need('finite-selected-reference-element',element_type in TYPES)
    native=source.derive_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=element_type)
    if element_type=='string':
        from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import derive_string
        need('string-callback-derived-in-this-operation',element_component is None)
        element_component=derive_string(image,pins)
    else:need('independent-complete-element-required',isinstance(element_component,dict))
    result=compose(native,element_component,pins);validate_component(result,pins);_publication_gate(image,pins);return result


def derive_member(image,pins,*,parent_source,member_index,element_component=None):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    read=parent_source['orderedSourceReads'][member_index];name=read['declaredType']
    matches=[t for t in TYPES if name==list_type(t)];need('own-finite-list-member',len(matches)==1)
    context=read.get('context',{});need('actual-parent-MethodInfo',type(context.get('instructionRva'))is int)
    image.check_windows(parent_source['codeWindows'],label='charReferenceList.parent')
    usage=derive_typed_usage_context(image,context['instructionRva'],label='charReferenceList.actual-parent')
    result=derive(image,pins,typed_request=usage,call_target=image.pe.image_base+read['sourceTargetRva'],
        element_type=matches[0],element_component=element_component)
    bind_member(parent_source,parent_source['sourceScope'],read,pins,usage,result,result['capability'])
    return result


def require_capability(capability,cap):
    name=cap.get('elementType')
    need('own-bounded-reference-list-cap',name in TYPES and capability==key(name)
        and cap.get('typeName')==cap.get('closedListType')==list_type(name)and cap.get('elementValueType')is False
        and type(cap.get('countLimit'))is int and 3<=cap['countLimit']<=4096
        and cap.get('countRange')==[-1,cap['countLimit']]and cap.get('reusedListsRequireInitialCount')==0
        and all(cap.get(k)is True for k in('nullable','positiveCountsAdmitted','wholeGrammarAdmitted','elementGrammarAdmitted',
            'freshListsAdmitted','reusedListsRequireCapacityAtLeastCount','actualCallbackEqualsCanonicalRequired'))
        and cap.get('liveFormatterSelectionObserved')is False and cap.get('parentFieldAdmitted')is False
        and cap.get('wholeOwnerAdmitted')is False and cap.get('elementWire')in('byte-payload','char-interact-record','char-interact-union'))
    return cap


def bind_member(parent,scope,read,pins,usage,component,capability):
    own=validate_component(component,pins);cap=require_capability(capability,own['capabilities'][capability]);index=read['memberIndex']
    need('own-complete-parent-and-list-request',parent.get('nativeInputs')==scope.get('nativeInputs')==pins
        and parent.get('schema')=='endfield.generated-concrete-reader-source.v1'and parent.get('completeSelectedCallerAdmitted')is True
        and parent.get('sourceScope')==scope and parent['orderedSourceReads'][index]==scope['events'][index]==read
        and read.get('declaredType')==cap['closedListType']and read.get('kind')=='reference:'+cap['closedListType']
        and parent.get('wrappedType','').startswith(PREFIX))
    context=read.get('context',{});raw=bytes.fromhex(read['instruction'][1])
    need('actual-parent-closed-MethodSpec-and-E8',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
        (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[cap['closedListType']])
        and usage.get('methodSpec')==context.get('methodSpec')==cap['sourceMethodSpec']
        and(context.get('instructionRva'),context.get('instructionHex'))==(usage.get('instructionRva'),usage.get('instructionHex'))
        and len(raw)==5 and raw[0]==232 and read['instruction'][0]+5+int.from_bytes(raw[1:],'little',signed=True)==
            read.get('sourceTargetRva')==cap['packableReaderTargetRva'])
    from scripts.game_data.memorypack.char_reference_field_bindings import require_transfer
    transfer=require_transfer(parent,scope,read,pins)
    return dict(fieldName=read['fieldName'],typeName=cap['closedListType'],capability=capability,
        readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'],parentTransfer=transfer)


def read(reader,capability,*,depth=0,budget=None):
    need('bounded-depth',type(depth)is int and 0<=depth<64)
    cap=require_capability(capability,reader.operation.child(capability));name=cap['elementType'];child=reader.operation.child(cap['elementCapability'])
    if name=='string':need('current-pool-cap',child.get('wholeGrammarAdmitted')is True and child.get('encoding')=='int32-pool-index'
        and child.get('wireBytes')==4 and child.get('emptyIndex')==-1 and child.get('nullIndex')==-2)
    else:need('same-whole-element-before-consumption',child==cap['elementCapabilityShape']and child.get('typeName')==name
        and child.get('wholeGrammarAdmitted')is True and child.get('ordinaryOriginalCallbackAdmitted')is True)
    at=reader.pos;need('complete-count',at+4<=reader.limit);count=struct.unpack_from('<i',reader.data,at)[0]
    need('bounded-count',-1<=count<=cap['countLimit'])
    need('minimum-remaining-element-bytes',at+4+max(0,count)*(4 if name=='string'else 1)<=reader.limit)
    if budget is None:budget=dict(remaining=16384)
    need('shared-budget-before-consumption',type(budget)is dict and set(budget)=={'remaining'}and type(budget['remaining'])is int
        and 1+max(0,count)<=budget['remaining']<=16384)
    budget['remaining']-=1;reader.take(4,capability+'.count');elements=[]
    for _ in range(max(0,count)):
        if name=='string':budget['remaining']-=1;elements.append(dict(value=reader.byte_payload()))
        elif cap['elementWire']=='char-interact-record':elements.append(reader.record(cap['elementCapability'],depth=depth+1,budget=budget))
        else:
            from scripts.game_data.memorypack.char_union_codec import read as read_union
            elements.append(read_union(reader,cap['elementCapability'],depth=depth+1,budget=budget))
    result=dict(kind=capability,typeName=cap['typeName'],start=at,end=reader.pos,isNull=count==-1,count=count,elements=elements)
    reader.records.append(result);return result

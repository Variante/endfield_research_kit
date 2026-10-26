"""CharInteract's three distinct value-list grammars and exact parent joins.

GameplayTag elements use the generated MC1/default4 adapter. Int32 and the
explicit InterruptReason enum use their own raw DWORD callbacks. No type name
or common managed width makes those three wire representations equivalent.
"""
import json,struct

TAG='Beyond.Gameplay.Core.GameplayTag'
ENUM='Beyond.Gameplay.CharInteractPerformEnums+InterruptReason'
DOMAIN='char-interact-interrupt-reasons'
TYPES=(TAG,'int',ENUM)
SCHEMA='endfield.char-interact-value-list-components.v1'
WIRE='char-interact-value-list'


def need(check,condition):
    if not condition:raise ValueError('charValueLists.'+check)


def norm(value):return json.loads(json.dumps(value))
def key(name):need('finite-own-element',name in TYPES);return WIRE+':'+name
def list_type(name):return 'System.Collections.Generic.List`1<'+name+'>'


def compose(native,pins,*,element_type,typed_request,source_target,binding=None):
    name=element_type;capability=key(name);need('same-independent-native-source',native.get('nativeInputs')==pins)
    need('actual-closed-list-request',tuple(typed_request.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
        ==(6,'MemoryPack.MemoryPackReader','ReadPackable',[],[list_type(name)])
        and isinstance(typed_request.get('methodSpec'),list)and len(typed_request['methodSpec'])==3
        and type(source_target)is int and source_target>0)
    if name==TAG:
        child_key='skill-root-gameplay-tag';source_key='skill-root-gameplay-tag-value-list'
        need('own-generated-Tag-list-source',native.get('schema')=='endfield.skill-gameplay-tag-list-components.v1'
            and native.get('status')=='validated-conditional-components')
        caps=native['capabilities'];source=caps[source_key];child=caps[child_key]
        need('generated-Tag-wire-not-raw4',source.get('elementType')==TAG and source.get('elementValueType')is True
            and source.get('elementGrammarAdmitted')is True and source.get('positiveCountsAdmitted')is True
            and source.get('elementCapability')==child_key and source.get('countLimit')==4096
            and child.get('memberCount')==1 and child.get('positiveWireBytes')==5 and child.get('nullWireBytes')==1
            and child.get('nullReturnsDefaultValue')is True and child.get('rawUnmanagedTagGrammarUsed')is False
            and native['proof']['context']['typedRequest']==typed_request)
        from scripts.game_data.memorypack.skill_root_buff_id_lists import induction
        need('same-bounded-Tag-induction',norm(induction(native['proof']['programs'],count_limit=4096))==native['proof']['induction'])
        wire='generated-gameplay-tag-MC1'
    elif name=='int':
        source=native.get('capability',{});source_key='story-int32-list';child_key=None;caps={}
        need('own-current-Int32-list-source',native.get('schema')=='endfield.story-int32-list-component.v1'
            and native.get('status')=='validated-conditional-int32-list'and source.get('capability')==source_key
            and source.get('typeName')==list_type(name)and source.get('wholeGrammarAdmitted')is True
            and source.get('elementWireBytes')==4 and source.get('rawBitsPreserved')is True
            and source.get('countRange')==[-1,4096]and source.get('countLimit')==4096
            and native['proof']['typedRequest']==typed_request)
        wire='int32-raw4'
    else:
        source_key='skill-enum-list:'+ENUM;child_key='skill-enum-callback:'+ENUM;caps=native['capabilities'];source=caps[source_key]
        need('own-explicit-InterruptReason-domain',native.get('schema')=='endfield.enum-optin-sources.v1'
            and native.get('status')=='validated-conditional-optin-enum-domain'and native.get('domain')==DOMAIN
            and native.get('domainDeclaration')==dict(nominalEnums=[ENUM],collectionEnums=[ENUM],countLimit=4096)
            and native.get('defaultSkillDomainChanged')is False and isinstance(binding,dict)
            and binding.get('sourceRequest')==typed_request and binding.get('collectionCapability')==source)
        from scripts.game_data.memorypack.nominal_enum_list_codec import require_capability
        require_capability(source,caps[child_key],name=ENUM,count_limit=4096,element_capability=child_key)
        wire='nominal-enum-raw4'
    need('same-exact-actual-reference-reader',source.get('packableReaderMethodDefinition')==typed_request['methodSpec'][0]
        and source.get('packableReaderTargetRva')==source_target and source.get('nullable')is True
        and source.get('positiveCountsAdmitted')is True)
    own=dict(typeName=list_type(name),closedListType=list_type(name),elementType=name,elementWire=wire,
        sourceCapability=source_key,elementCapability=child_key,headerBytes=4,countLimit=4096,countRange=[-1,4096],
        nullable=True,positiveCountsAdmitted=True,wholeGrammarAdmitted=True,elementGrammarAdmitted=True,
        sourceMethodSpec=typed_request['methodSpec'],packableReaderMethodDefinition=typed_request['methodSpec'][0],
        packableReaderTargetRva=source_target,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    caps=dict(caps);caps[capability]=own
    return norm(dict(schema=SCHEMA,status='validated-conditional-char-interact-value-list',nativeInputs=pins,
        capability=capability,capabilities=caps,requiredExternalCapabilities=[],
        proof=dict(source=native,typedRequest=typed_request,sourceTargetRva=source_target,binding=binding),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False))


def validate_component(component,pins):
    need('own-whole-value-list',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
        and component.get('status')=='validated-conditional-char-interact-value-list'
        and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    p=component['proof'];name=component['capabilities'][component['capability']]['elementType']
    checked=compose(p['source'],pins,element_type=name,typed_request=p['typedRequest'],source_target=p['sourceTargetRva'],binding=p['binding'])
    need('same-complete-source-composition',checked==component)
    return {k:checked[k]for k in('capability','capabilities','requiredExternalCapabilities')}


def derive(image,pins,*,element_type,typed_request,call_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins);need('finite-own-value-list',element_type in TYPES);binding=None
    if element_type==TAG:
        from scripts.game_data.memorypack.skill_gameplay_tag_lists import derive as source
        native=source(image,pins,typed_request=typed_request,call_target=call_target)
    elif element_type=='int':
        from scripts.game_data.memorypack.leveldata_int_list_sources import derive as source
        native=source(image,pins,typed_request=typed_request,call_target=call_target)
    else:
        from scripts.game_data.memorypack import enum_optin_native_sources as source
        native=source.derive(image,pins,domain=DOMAIN)
        binding=source.bind_request(image,pins,native,typed_request=typed_request,call_target=call_target,enum_type=ENUM)
    result=compose(native,pins,element_type=element_type,typed_request=typed_request,source_target=call_target-image.pe.image_base,binding=binding)
    validate_component(result,pins);_publication_gate(image,pins);return result


def require_capability(capability,cap):
    name=cap.get('elementType');need('own-exact-value-list-key',name in TYPES and capability==key(name)
        and cap.get('typeName')==cap.get('closedListType')==list_type(name)and cap.get('headerBytes')==4
        and cap.get('countLimit')==4096 and cap.get('countRange')==[-1,4096]
        and all(cap.get(k)is True for k in('nullable','positiveCountsAdmitted','wholeGrammarAdmitted','elementGrammarAdmitted'))
        and cap.get('elementWire')=={TAG:'generated-gameplay-tag-MC1','int':'int32-raw4',ENUM:'nominal-enum-raw4'}[name]
        and cap.get('parentFieldAdmitted')is False and cap.get('wholeOwnerAdmitted')is False)
    return cap


def bind_member(parent,scope,read,pins,usage,component,capability):
    own=validate_component(component,pins);cap=require_capability(capability,own['capabilities'][capability]);index=read['memberIndex']
    need('same-finite-actual-parent-member',parent.get('nativeInputs')==scope.get('nativeInputs')==pins
        and parent.get('sourceScope')==scope and parent.get('completeSelectedCallerAdmitted')is True
        and parent['orderedSourceReads'][index]==scope['events'][index]==read
        and((parent.get('wrappedType')=='Beyond.Gameplay.Core.CharInteractPerform.AddMultiTagsActData'and index in(15,16)and cap['elementType']==TAG)
            or(parent.get('wrappedType')=='Beyond.Gameplay.Core.CharInteractPerform.CharWeaponShowActData'and index==17 and cap['elementType']=='int')))
    context=read['context'];raw=bytes.fromhex(read['instruction'][1])
    need('same-exact-parent-MethodSpec-and-E8',usage.get('methodSpec')==context.get('methodSpec')==cap['sourceMethodSpec']
        and(usage.get('instructionRva'),usage.get('instructionHex'))==(context.get('instructionRva'),context.get('instructionHex'))
        and read.get('declaredType')==cap['closedListType']and read.get('kind')=='reference:'+cap['closedListType']
        and len(raw)==5 and raw[0]==232 and read['instruction'][0]+5+int.from_bytes(raw[1:],'little',signed=True)==
            read.get('sourceTargetRva')==cap['packableReaderTargetRva'])
    from scripts.game_data.memorypack.char_reference_field_bindings import require_transfer
    transfer=require_transfer(parent,scope,read,pins)
    return dict(fieldName=read['fieldName'],typeName=cap['closedListType'],capability=capability,
        readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'],parentTransfer=transfer)


def read(reader,capability,*,depth=0,budget=None):
    need('bounded-depth',type(depth)is int and 0<=depth<64)
    cap=require_capability(capability,reader.operation.child(capability));name=cap['elementType']
    if name==ENUM:
        from scripts.game_data.memorypack.nominal_enum_list_codec import read as enums
        return enums(reader,capability=cap['sourceCapability'],element_capability=cap['elementCapability'],name=ENUM,
            count_limit=4096,depth=depth,budget=budget)
    if name==TAG:
        child=reader.operation.child(cap['elementCapability']);source=reader.operation.child(cap['sourceCapability'])
        need('generated-Tag-child-before-count',child.get('memberCount')==1 and child.get('positiveWireBytes')==5
            and child.get('nullWireBytes')==1 and child.get('nullReturnsDefaultValue')is True
            and child.get('rawUnmanagedTagGrammarUsed')is False and source.get('elementCapability')==cap['elementCapability'])
    start=reader.pos;need('complete-signed-count',start+4<=reader.limit);count=struct.unpack_from('<i',reader.data,start)[0]
    need('bounded-signed-count',-1<=count<=4096)
    need('minimum-element-bytes',start+4+max(count,0)*(1 if name==TAG else 4)<=reader.limit)
    budget=dict(remaining=16384)if budget is None else budget
    need('shared-budget-before-consumption',type(budget)is dict and set(budget)=={'remaining'}and type(budget['remaining'])is int
        and 1+max(count,0)<=budget['remaining']<=16384)
    budget['remaining']-=1+max(count,0);reader.take(4,capability+'.count');rows=[]
    for _ in range(max(count,0)):
        at=reader.pos;marker=None
        if name==TAG:
            marker=reader.peek();need('generated-Tag-MC1-or-default',marker in(1,255));reader.take(1,capability+'.Tag.memberCount')
        raw=bytes(4)if marker==255 else reader.take(4,capability+'.element')
        rows.append(dict(start=at,end=reader.pos,isDefault=marker==255,rawHex=raw.hex()))
    result=dict(kind=capability,typeName=cap['typeName'],start=start,end=reader.pos,count=count,isNull=count==-1,elements=rows)
    reader.records.append(result);return result

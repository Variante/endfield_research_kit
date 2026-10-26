"""Explicit EnemyHurtAnim list source and its two actual EnemyHurt11 calls.

The default Skill enum lists and the animation dictionary-key domain are
unchanged. This owner selects a separate reviewed opt-in domain, freshly
proves the callback/list/count programs and binds each own parent MethodSpec
and E8. Complete enclosing record grammar remains the containing owner's job.
"""
import json

from scripts.game_data.memorypack import nominal_enum_list_codec as codec

SCHEMA='endfield.animation-enemy-hurt-enum-lists.v1'
DOMAIN='animation-enemy-hurt-lists'
TYPE='Beyond.Gameplay.Core.EnemyHurtAnim'
LIST='System.Collections.Generic.List`1<'+TYPE+'>'
PARENT='Beyond.Gameplay.View.Animation.EnemyAnimExtraData+EnemyHurtAnimData'
CAPABILITY='skill-enum-list:'+TYPE
ELEMENT_CAPABILITY='skill-enum-callback:'+TYPE
COUNT_LIMIT=4096
FIELDS={'fullBodyTurnList':2,'staggerTurnList':8}


def need(check,condition,detail=None):
    if not condition:raise ValueError('animationEnemyHurtEnumLists.'+check+':'+str(detail)[:800])


def require_capability(cap,element):
    return codec.require_capability(cap,element,name=TYPE,count_limit=COUNT_LIMIT,
        element_capability=ELEMENT_CAPABILITY)


def validate_component(pins,component,capability=CAPABILITY):
    need('own-component',isinstance(component,dict)and capability==CAPABILITY and component.get('schema')==SCHEMA
         and component.get('status')=='validated-conditional-enemy-hurt-enum-lists'
         and component.get('nativeInputs')==pins and component.get('domain')==DOMAIN
         and component.get('requiredExternalCapabilities')==[]
         and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    caps=component.get('capabilities',{})
    need('exact-closed-capability-set',set(caps)=={CAPABILITY,ELEMENT_CAPABILITY}
         and component.get('capability')==caps[CAPABILITY])
    cap=require_capability(caps[CAPABILITY],caps[ELEMENT_CAPABILITY])
    need('same-current-native-capabilities',cap.get('nativeInputs')==pins)
    source=component.get('proof',{}).get('source',{})
    need('fresh-explicit-optin-source',source.get('schema')=='endfield.enum-optin-sources.v1'
         and source.get('status')=='validated-conditional-optin-enum-domain'
         and source.get('nativeInputs')==pins and source.get('domain')==DOMAIN
         and source.get('domainDeclaration')==dict(nominalEnums=[TYPE],collectionEnums=[TYPE],countLimit=COUNT_LIMIT)
         and source.get('capabilities')==caps and source.get('defaultSkillDomainChanged')is False)
    bindings=component.get('actualBindings',{})
    need('two-and-only-two-parent-source-bindings',set(bindings)==set(FIELDS))
    for name,index in FIELDS.items():
        row=bindings[name];request=row.get('typedRequest',{});binding=row.get('sourceBinding',{})
        need('own-field-typed-source-binding',row.get('memberIndex')==index and row.get('fieldName')==name
             and row.get('typeName')==LIST and type(row.get('sourceTargetRva'))is int
             and row['sourceTargetRva']==cap['packableReaderTargetRva']
             and isinstance(request.get('methodSpec'),list)and len(request['methodSpec'])==3
             and request['methodSpec'][0]==cap['packableReaderMethodDefinition']
             and(request.get('tag'),request.get('typeName'),request.get('methodName'),request.get('classArguments'),request.get('methodArguments'))==
                 (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[LIST])
             and binding.get('sourceRequest')==request and binding.get('collectionCapability')==cap
             and binding.get('closedListType')==LIST and binding.get('elementType')==TYPE
             and binding.get('packableReaderMethodDefinition')==cap['packableReaderMethodDefinition']
             and binding.get('packableReaderTargetRva')==row['sourceTargetRva'])
    return cap


def derive(image,pins,*,requests):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import enum_optin_native_sources as optin,primitive_param
    from scripts.game_data.memorypack.pointer_param import owned,methods
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.unmanaged_enum_member_sources import bind_actual_call
    _publication_gate(image,pins)
    need('two-explicit-actual-parent-requests',type(requests)is list and len(requests)==2
         and {r.get('fieldName')for r in requests}==set(FIELDS))
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==PARENT]
    need('exact-parent-member-count',len(wrapper.members)==11)
    method=methods(image,wrapper)['Deserialize'];ctx=NativeReferenceContext(image)
    primitive_param.reader_abi(image,ctx,method,wrapper)
    parent=owned(image,image.method_pointer_va(method));base=image.pe.image_base
    by={int(r['va'],16):r for r in parent['rows']}
    source=optin.derive(image,pins,domain=DOMAIN);caps=source['capabilities']
    cap=require_capability(caps[CAPABILITY],caps[ELEMENT_CAPABILITY]);bindings={}
    for request in requests:
        name=request['fieldName'];index=FIELDS[name];member=wrapper.members[index]
        need('own-current-named-parent-member',member.name==name and member.declared_type==request.get('typeName')==LIST)
        usage=request.get('typedRequest',{});site=usage.get('instructionRva')
        need('owned-parent-MethodInfo-instruction',type(site)is int and base+site in by)
        current=derive_typed_usage_context(image,site,label='animationEnemyHurtEnumLists.parent')
        need('same-current-actual-MethodInfo',current==usage)
        instruction=request.get('instruction');target=request.get('sourceTargetRva')
        need('owned-parent-actual-E8',isinstance(instruction,(tuple,list))and len(instruction)==2
             and type(instruction[0])is int and base+instruction[0]in by
             and bytes.fromhex(by[base+instruction[0]]['bytes'])==bytes.fromhex(instruction[1])
             and type(target)is int and 0<target<1<<32)
        actual=bind_actual_call(current,instruction,source_target=base+target,base=base)
        image.check_instruction_windows([instruction],label='animationEnemyHurtEnumLists.parentE8')
        binding=optin.bind_request(image,pins,source,typed_request=current,call_target=base+target,enum_type=TYPE)
        bindings[name]=dict(memberIndex=index,fieldName=name,typeName=LIST,typedRequest=current,
            sourceTargetRva=target,instruction=list(instruction),actualCall=actual,sourceBinding=binding)
    result=json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-enemy-hurt-enum-lists',nativeInputs=pins,
        domain=DOMAIN,capability=cap,capabilities=caps,requiredExternalCapabilities=[],actualBindings=bindings,
        proof=dict(source=source,parentMethod=[method.index,wrapper.name,'Deserialize',parent['pointer']-base],
            parentSourceWindows=parent['windows']),parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
    validate_component(pins,result)
    _publication_gate(image,pins)
    return result


def bind(pins,join,component,capability=CAPABILITY):
    cap=validate_component(pins,component,capability)
    name=join.get('fieldName');need('own-parent-field',name in FIELDS)
    owned=component['actualBindings'][name]
    need('exact-current-parent-collection-identity',join.get('typeName')==LIST
         and join.get('typedRequest')==owned['typedRequest']and join.get('sourceTargetRva')==owned['sourceTargetRva']
         and('instruction'not in join or join['instruction']==owned['instruction'])
         and('memberIndex'not in join or join['memberIndex']==FIELDS[name]))
    return dict(fieldName=name,memberIndex=FIELDS[name],typeName=LIST,readMethod='ReadPackable',
        childCapability=capability,elementCapability=ELEMENT_CAPABILITY,
        packableReaderMethodDefinition=cap['packableReaderMethodDefinition'],
        packableReaderTargetRva=cap['packableReaderTargetRva'],collectionCapability=cap,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def bind_member(fullsource,scope,read,pins,usage,component,capability=CAPABILITY):
    need('own-complete-parent-source',fullsource.get('schema')=='endfield.generated-concrete-reader-source.v1'
         and fullsource.get('nativeInputs')==pins and fullsource.get('wrappedType')==PARENT
         and fullsource.get('completeSelectedCallerAdmitted')is True and fullsource.get('wholeOwnerAdmitted')is False
         and fullsource.get('sourceScope')==scope and scope.get('nativeInputs')==pins
         and scope.get('wrappedType')==PARENT and scope.get('memberCount')==11
         and scope.get('richProgram',{}).get('completeSelectedNormalProgram')is True)
    programs=fullsource.get('programs',[])
    need('all-four-owned-parent-frames',len(programs)==4
         and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool for p in programs)
         and {(p.get('existing'),p.get('wrapperNull'))for p in programs}=={(False,False),(True,False),(False,True),(True,True)}
         and all(p.get('frame',{}).get('entryRspRestored')is True
                 and p.get('frame',{}).get('allWin64IntegerNonvolatilesRestored')is True for p in programs))
    index=read.get('memberIndex');name=read.get('fieldName')
    need('same-own-ordered-source-and-field',name in FIELDS and index==FIELDS[name]
         and len(fullsource.get('orderedSourceReads',[]))==len(scope.get('events',[]))==len(scope.get('richSetters',[]))==11
         and fullsource.get('orderedSourceReads',[])[index]==read and scope.get('events',[])[index]==read
         and read.get('declaredType')==LIST and read.get('kind')=='reference:'+LIST
         and read.get('context',{}).get('methodName')=='ReadPackable'
         and read['context'].get('methodSpec')==usage.get('methodSpec')
         and read['context'].get('instructionRva')==usage.get('instructionRva'))
    def windows(rows):return sorted((w['startRva'],w['endRva'],w['sha256'])for w in rows)
    need('same-complete-current-parent-byte-windows',windows(scope.get('codeWindows',[]))==
         windows(component.get('proof',{}).get('parentSourceWindows',[]))
         and fullsource.get('method')==component.get('proof',{}).get('parentMethod'))
    setter=scope.get('richSetters',[])[index]
    stores=[s for s in scope['richProgram'].get('fieldStores',[])if s.get('memberIndex')==index]
    need('whole-own-list-reference-named-store',setter.get('storedBytes')==8
         and setter.get('member',{}).get('name')==name and setter['member'].get('declaredType')==LIST
         and setter.get('incomingValueStoredUnchanged')is True
         and len(stores)==1 and stores[0].get('sourceOffset')==0 and stores[0].get('storedBytes')==8)
    return bind(pins,dict(fieldName=name,memberIndex=index,typeName=LIST,typedRequest=usage,
        sourceTargetRva=read['sourceTargetRva'],instruction=read['instruction']),component,capability)


def read(reader,*,budget=None,depth=0):
    return codec.read(reader,capability=CAPABILITY,element_capability=ELEMENT_CAPABILITY,
        name=TYPE,count_limit=COUNT_LIMIT,budget=budget,depth=depth)

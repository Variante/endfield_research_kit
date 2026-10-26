"""Finite Extra value arrays: actual source, own element and parent reference.

Slot-five arrays retain an explicit compatible canonical-callback condition.
Shader's actual inline dispatcher independently compares its canonical entry.
Every element keeps its own generated wire, managed representation and default.
"""
import json
from scripts.game_data.memorypack import animation_state_array_sources as state
from scripts.game_data.memorypack import animation_extra_value_array_sources as extra
from scripts.game_data.memorypack import animation_shader_array_sources as shader

SCHEMA='endfield.animation-extra-value-array-components.v1'
WIRE='animation-extra-value-array'
TYPES=(state.TYPE,extra.PLAY,extra.RENDERER,shader.TYPE)


def need(check,condition):
    if not condition:raise ValueError('animationExtraArrayComponents.'+check)


def own_field_target(source,read,setter):
    expected=source['wrappedType']+'::'+read['fieldName']
    if setter.get('targetField')==expected:return True
    # UpperBody inherits this actual Character field and its named setter.
    # The complete reader already proves the constructed base and both exact
    # cache-refresh paths; retain that join rather than infer from a type name.
    prefix='Beyond.Gameplay.View.Animation.'
    parent=prefix+'CharacterAnimExtraData'
    wrapper='Beyond.MemoryPack.Beyond_Gameplay_View_Animation_CharacterAnimExtraDataForMemoryPack'
    getter=setter.get('getter',{});refresh=getter.get('compatibleRefresh',{})
    joins=[j for j in source.get('constructedGetterJoin',{}).get('setters',[])if j.get('method')==setter.get('method')]
    paths=refresh.get('programs',[])
    return(source.get('wrappedType')==prefix+'UpperBodyFightExtraData' and read.get('memberIndex')==28
        and read.get('fieldName')=='statePerformEntries'and read.get('declaredType')==state.TYPE+'[]'
        and setter.get('targetField')==parent+'::statePerformEntries'
        and setter.get('profile')=='cached-getter-setter'and setter.get('method',[None,None])[1]==wrapper
        and setter.get('member',{}).get('declaringWrapper')==wrapper
        and getter.get('typedCache')==[wrapper,parent,24]
        and getter.get('baseHolder')==source.get('lifecycle',{}).get('baseHolder')
        and getter.get('coherentNonNullSamePointerReturn')is True
        and refresh.get('initializedCompatibleNonNullBaseRequired')is True
        and refresh.get('emptyOrDifferentCacheAdmitted')is True and refresh.get('predicateOutcomeObserved')is False
        and len(paths)==2 and{p.get('path')for p in paths}=={'empty','different'}
        and all(p.get('program',{}).get('normalReturn')is True
            and p['program'].get('sameBaseReferenceCachedAndReturned')is True for p in paths)
        and joins==[dict(method=setter['method'],cacheOffset=24,mode='exact-compatible-refresh-from-constructed-base')])


def norm(v):return json.loads(json.dumps(v))
def key(name):need('finite-own-value-array',name in TYPES);return 'animation-extra-value-array:'+name


def _element(component,pins):
    from scripts.game_data.memorypack.animation_extra_record_components import validate_component
    own=validate_component(component,pins);cap=own['capabilities'][own['capability']];name=cap.get('typeName')
    need('independently-complete-own-value-element',name in TYPES and cap.get('wholeGrammarAdmitted')is True
        and own['capability']=='animation-extra-record:'+name and cap.get('ordinaryOriginalCallbackAdmitted')is True
        and cap.get('ordinaryOriginalReadValueAdmitted')is False and cap.get('managedBytes')in(8,24,32)
        and type(cap.get('originalTypeDefinition'))is int and cap['originalTypeDefinition']>=0
        and type(cap.get('canonicalAdapterTargetRva'))is int and cap['canonicalAdapterTargetRva']>0
        and type(cap.get('formatterDeserializeMethodDefinition'))is int and cap['formatterDeserializeMethodDefinition']>=0)
    return own,cap


def verify_source(actual,pins,element):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    own,cap=_element(element,pins);name=cap['typeName'];p=actual.get('proof',{});is_state=name==state.TYPE;is_shader=name==shader.TYPE
    owner=state if is_state else shader if is_shader else extra;status='validated-conditional-state-perform-value-array'if is_state else'verified'
    if not is_state:status='validated-conditional-shader-value-array'if is_shader else'validated-conditional-extra-value-array'
    need('own-source-not-wire-or-parent-grant',actual.get('schema')==owner.SCHEMA and actual.get('nativeInputs')==pins and actual.get('status')==status
        and actual.get('elementType')==name and actual.get('elementValueType')is True and actual.get('closedArrayType')==name+'[]'
        and actual.get('elementManagedBytes')==cap['managedBytes']and actual.get('elementWireBytes')is None
        and actual.get('countRange')==[-1,4096]and actual.get('countLimit')==4096 and actual.get('nullable')is True
        and all(actual.get(k)is True for k in('positiveCountsAdmitted','initiallyNullArrayRequired','actualSourceProved'))
        and all(actual.get(k)is False for k in('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
    nominal=p['layout'];need('same-independent-physical-layout',nominal.get('typeName')==name
        and nominal.get('typeDefinition')==cap['originalTypeDefinition']and nominal.get('managedBytes')==cap['managedBytes']
        and nominal.get('referenceLaneOffsets')==cap.get('referenceLaneOffsets'))
    pads=nominal.get('paddingByteRanges',[])
    if not is_shader:pads=[[a,b-a]for a,b in pads]
    need('explicit-own-padding-encoding',pads==cap.get('paddingByteRanges',[]))
    first=p['returnProgram']['selectedBytes'][0][0];base=first-actual['arrayReaderTargetRva']
    need('selected-image-base',type(base)is int and base>=2**32)
    raw={role:regions(p['sourceWindows'][role],[[a-base,h]for a,h in rows],base,'extra-value-array-'+role)
        for role,rows in p['actualSourceRegions'].items()}
    symbols={k:base+v for k,v in p['symbolRvas'].items()};play=name==extra.PLAY
    front=state.return_program(raw['front'],first)if is_state or is_shader else extra.return_program(raw['front'],first,play=play)
    need('complete-return-overload-owned-null-output',norm(front)==p['returnProgram']and front.get('initiallyNullOutputProved')is True)
    entry=front['byrefTargetVa']
    paths=[owner.byref_program(raw['byref'],entry,count=n,**({}if is_state or is_shader else dict(play=play)))for n in(-1,0,1,2,3)]
    need('all-five-full-count-paths',norm(paths)==p['programs'])
    if is_state:
        args=dict(initial='4533f6',increment='41ffc6',comparison='443bf6',counter='r14d',saved_count='esi')
        cb=element['proof']['source']['proof']['canonical'];offsets=p['readerOffsets']
        need('same-four-current-Reader-fields',all(offsets.get(k)==v for k,v in cb['proof']['readerOffsets'].items()))
        helpers=dict(header=state.header_program(raw['header'],symbols['header'],offsets),index=state.index_program(raw['index'],symbols['index']),
            empty=state.empty_program(raw['empty'],symbols['empty'],symbols['context']),provider=state.provider_program(raw['provider'],symbols['provider']),
            dispatch=state.dispatch_program(raw['dispatch'],symbols['dispatch']))
        induction=prove_induction(paths[1:],**args,max_count=4096,backedge_sites=[paths[-1]['actualBackedgeVa']])
    elif is_shader:
        offsets=p['readerOffsets'];args=dict(initial='33db',increment='ffc3',comparison='3bdd',counter='ebx',saved_count='ebp')
        helpers=dict(header=state.header_program(raw['header'],symbols['header'],offsets),index=shader.index_program(raw['index'],symbols['index']),
            empty=shader.empty_program(raw['empty'],symbols['empty'],symbols['context']),provider=shader.provider_program(raw['provider'],symbols['provider']))
        from scripts.game_data.memorypack.shader_property_value_components import compose
        actual_child=compose(p['callbackSource'],pins);need('actual-dispatch-to-same-independent-own-child',actual_child['capabilities']==own['capabilities'])
        source=p['callbackSource']['proof'];need('same-owned-inline-dispatch-source',source['symbolRvas']['actualDispatch']==p['symbolRvas']['dispatch']
            and source['symbolRvas']['adapter']==cap['canonicalAdapterTargetRva'])
        helpers['dispatch']=source['paths']['actualDispatch'];induction=prove_induction(paths[1:],**args,max_count=4096,mode_key='newArray',backedge_sites=[paths[-1]['actualBackedgeVa']])
    else:
        offsets=p['readerOffsets'];args=dict(initial='33ff',increment='ffc7',comparison='3bfe',counter='edi',saved_count='esi')if play else dict(initial='4533f6',increment='41ffc6',comparison='443bf6',counter='r14d',saved_count='esi')
        helpers=dict(header=state.header_program(raw['header'],symbols['header'],offsets),
            empty=extra.empty_program(raw['empty'],symbols['empty'],symbols['context'],play=play),provider=extra.provider_program(raw['provider'],symbols['provider'],play=play),
            dispatch=extra.dispatch_program(raw['dispatch'],symbols['dispatch']))
        if play:helpers['index']=state.index_program(raw['index'],symbols['index'])
        induction=prove_induction(paths[1:],**args,max_count=4096,mode_key='newArray',backedge_sites=[paths[-1]['actualBackedgeVa']])
    need('all-owned-helpers-and-bounded-induction',norm(helpers)==p['helperPrograms']and norm(induction)==p['induction'])
    usage=actual['typedRequest'];decl=p['formatterDeclaration'];context=p['arrayContext']
    need('same-owned-array-overloads-and-slot-five',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
        ==(6,'MemoryPack.MemoryPackReader','ReadArray',[],[name])and usage['methodSpec'][0]==actual['arrayReaderMethodDefinition']
        and context.get('returnOverloadDefinition')==usage['methodSpec'][0]and context.get('readArrayOverloadsReciprocallyJoined')is True
        and context.get('emptyArrayTypeProviderAndDeserializeOwned')is True and context.get('formatterSlot')==decl.get('formatterSlot')==5
        and decl.get('abstractDeclaration')is True and decl.get('sameReaderByref')is True and decl.get('ownClassVAROutputByref')is True
        and decl.get('concreteCallbackBodyProved')is False)
    return own,cap,base


def compose(array_source,element,pins):
    own,element_cap,base=verify_source(array_source,pins,element);name=element_cap['typeName'];capability=key(name)
    cap=dict(typeName=name+'[]',elementType=name,closedArrayType=name+'[]',elementCapability=own['capability'],elementValueType=True,
        managedElementBytes=element_cap['managedBytes'],elementWireBytes=None,headerBytes=4,countRange=[-1,4096],countLimit=4096,
        nullable=True,positiveCountsAdmitted=True,wholeGrammarAdmitted=True,elementGrammarAdmitted=True,initiallyNullArrayRequired=True,
        actualCallbackEqualsCanonicalRequired=True,liveFormatterSelectionObserved=False,
        canonicalAdapterTargetRva=element_cap['canonicalAdapterTargetRva'],formatterDeserializeMethodDefinition=element_cap['formatterDeserializeMethodDefinition'],
        elementCapabilityShape=element_cap,
        arrayReaderMethodDefinition=array_source['arrayReaderMethodDefinition'],arrayReaderTargetRva=array_source['arrayReaderTargetRva'],
        parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    caps=dict(own['capabilities']);caps[capability]=cap
    return dict(schema=SCHEMA,status='validated-conditional-animation-extra-value-array',nativeInputs=pins,capability=capability,capabilities=caps,
        requiredExternalCapabilities=own['requiredExternalCapabilities'],proof=dict(arraySource=array_source,element=element),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def validate_component(component,pins):
    need('own-composed-value-array',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
        and component.get('status')=='validated-conditional-animation-extra-value-array'
        and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    checked=compose(component['proof']['arraySource'],component['proof']['element'],pins)
    need('all-and-only-owned-capabilities',all(component.get(k)==checked[k]for k in('capability','capabilities','requiredExternalCapabilities')))
    return dict(capability=checked['capability'],capabilities=checked['capabilities'],requiredExternalCapabilities=checked['requiredExternalCapabilities'])


def bind_member(source,scope,read,pins,usage,component,capability):
    joined=validate_component(component,pins);cap=joined['capabilities'][joined['capability']];index=read['memberIndex'];actual=scope.get('arraySources',{}).get(str(index),{})
    context=read.get('context',{});raw=bytes.fromhex(context.get('argumentRawHex',''));typename=cap['elementType'];array=component['proof']['arraySource']
    need('exact-own-value-array-member',capability==joined['capability']==key(typename)and read.get('mode')=='typed-value-array'
        and source.get('schema')=='endfield.generated-concrete-reader-source.v1'and source.get('nativeInputs')==pins
        and source.get('completeSelectedCallerAdmitted')is True and source.get('sourceScope')==scope
        and source.get('orderedSourceReads',[])[index]==read and scope['events'][index]==read
        and read.get('declaredType')==typename+'[]'and read.get('kind')=='reference:'+typename+'[]'
        and context.get('typeKind')==17 and context.get('register')=='rdx'and context.get('methodName')=='ReadArray'
        and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('fullTypeName')==typename
        and len(raw)==16 and raw[10:12]==b'\x11\x80'and context.get('typeDefinition')==int.from_bytes(raw[:8],'little')
        and tuple(context.get(k)for k in('instructionRva','instructionHex','methodSpec'))==tuple(usage.get(k)for k in('instructionRva','instructionHex','methodSpec'))
        and actual==array and array['typedRequest']==usage and read.get('sourceTargetRva')==cap['arrayReaderTargetRva'])
    own,element_cap,base=verify_source(array,pins,component['proof']['element'])
    need('exact-own-nominal-type-definition',context['typeDefinition']==element_cap['originalTypeDefinition'])
    at,hexcode=read['instruction'];encoded=bytes.fromhex(hexcode)
    need('actual-source-E8',len(encoded)==5 and encoded[0]==232 and at+5+int.from_bytes(encoded[1:],'little',signed=True)==read['sourceTargetRva'])
    rich=scope['richProgram'];flows=[x for x in rich.get('sources',[])if x.get('memberIndex')==index];stores=[x for x in rich.get('fieldStores',[])if x.get('memberIndex')==index]
    setter=source['setters'][index]
    need('whole-array-RAX-to-own-named-field',rich.get('completeSelectedNormalProgram')is True and rich.get('selectedProgram')==scope.get('selectedProgram')
        and flows==[dict(memberIndex=index,instruction=read['instruction'],resultAbi='rax')]
        and len(stores)==1 and(stores[0].get('sourceOffset'),stores[0].get('storedBytes'))==(0,8)
        and stores[0].get('instruction')in scope['selectedProgram']and scope['richSetters'][index]==setter
        and own_field_target(source,read,setter)and setter.get('storedBytes')==8
        and setter.get('incomingValueStoredUnchanged')is True and setter.get('method',[None,None,None])[2]=='set___'+read['fieldName']+'__'
        and setter.get('codeWindows')and setter.get('profile')in('direct-base-holder-setter','cached-getter-setter','inline-coherent-cache-setter'))
    store_at,store_hex=stores[0]['instruction'];encoded=bytes.fromhex(store_hex)
    need('exact-actual-complete-setter-call',len(encoded)==5 and encoded[0]in(232,233)
        and store_at+5+int.from_bytes(encoded[1:],'little',signed=True)==setter['method'][3])
    paths=source.get('programs',[])
    need('all-four-complete-parent-frames',len(paths)==4 and{(p.get('existing'),p.get('wrapperNull'))for p in paths}=={(False,False),(True,False),(False,True),(True,True)}
        and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool and p.get('frame',{}).get('entryRspRestored')is True
            and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
    return dict(fieldName=read['fieldName'],typeName=typename+'[]',capability=capability,readerMethodDefinition=cap['arrayReaderMethodDefinition'],
        sourceTargetRva=read['sourceTargetRva'],completeOwnArrayReferenceFieldTransfer=True,allFourParentFramesProved=True,
        elementCapability=own['capability'],actualCallbackEqualsCanonicalRequired=True)

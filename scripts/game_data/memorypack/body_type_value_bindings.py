"""Finite BodyTypeDef32 field/frame plus independent MC3/default32 join.

No generic managed8/16 compiler is widened. This domain requires the actual
BodyTypeDef source, both reference lanes/padding, complete named setter replay,
once-only32-byte parent copy, hidden local and all four enclosing frames. Wire
bytes come exclusively from the separate own MC3 capability. Provider/helper
selection and runtime behavior retain the source owner's conditions.

The join also replays setter family/hash, actual ReadValue MethodSpec/E8 target
and all four restored frames. Synthetic refusal fixtures grant no actual parent:
fresh complete caller and independent MC3/default32 child remain required.
"""
from scripts.game_data.memorypack import body_type_value_components as owner
from scripts.game_data.memorypack import body_type_value_codec as codec
from scripts.game_data.memorypack import generated_body_type_field_sources as field

TYPE=owner.source.TYPE
CAPABILITY=owner.CAPABILITY


def need(check,condition):
    if not condition:raise ValueError('bodyTypeValueBindings.'+check)


def require_transfer(source,scope,read,pins):
    index=read.get('memberIndex');context=read.get('context')or{}
    closed=read.get('sourceContextMode')=='owned-closed-forwarder'
    if closed:
        from scripts.game_data.memorypack.montage_value_parent_sources import selection
        _,_,context,_=selection(scope,read,pins)
    need('complete-exact-parent-source',source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==scope.get('nativeInputs')==pins
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False and source.get('sourceScope')==scope)
    need('exact-finite-managed32-event',type(index)is int and 0<=index<len(source.get('orderedSourceReads',[]))
        and source['orderedSourceReads'][index]==read and scope.get('events')==source['orderedSourceReads']
        and read.get('kind')=='managed:'+TYPE and read.get('declaredType')==TYPE
        and read.get('mode')=='typed-managed-value'and read.get('resultAbi')=='hidden-local'
        and type(read.get('managedBytes'))is int and read['managedBytes']==32
        and read.get('referenceLaneOffsets')==[8,24]and read.get('actualSourceProved')is True
        and read.get('sourceContextMode')in(None,'owned-closed-forwarder')and'wireBytes'not in read)
    setters=source.get('setters',[]);rich_setters=scope.get('richSetters',[])
    need('same-whole-owned-named-setter',index<len(setters)and index<len(rich_setters)and setters[index]==rich_setters[index])
    setter=setters[index];field.validate_event(read,setter);field.require_setter(setter)
    method=setter['method'];member=setter['member'];layout=setter['managedValueLayout']
    need('same-named-member-metadata',method[0]==member.get('methodIndex')and method[1]==member.get('declaringWrapper')
        and method[2]=='set___'+str(read.get('fieldName'))+'__'and member.get('name')==read.get('fieldName')
        and member.get('declaredType')==TYPE and setter.get('targetField','').endswith('::'+str(read.get('fieldName')))
        and setter.get('incomingValueStoredUnchanged')is True and setter.get('childGrammarAdmitted')is False
        and setter.get('factoryAdmitted')is False and layout.get('typeDefinition')==context.get('typeDefinition')
        and layout.get('fields')==[list(r)for r in owner.source.FIELDS])
    rich=scope.get('richProgram',{});selected=rich.get('selectedProgram',[])
    need('whole-source-and-field-path',rich.get('completeSelectedNormalProgram')is True
        and rich.get('childGrammarAdmitted')is False and rich.get('wholeOwnerAdmitted')is False and bool(selected))
    actual_sources=[r for r in rich.get('sources',[])if r.get('memberIndex')==index]
    need('one-actual-hidden32-source',len(actual_sources)==1 and actual_sources[0].get('instruction')==read.get('instruction')
        and actual_sources[0].get('resultAbi')=='hidden-local'and read.get('instruction')in selected)
    stores=[r for r in rich.get('fieldStores',[])if r.get('memberIndex')==index];covered=[]
    for store in stores:
        offset=store.get('sourceOffset');width=store.get('storedBytes')
        need('literal-owned-source-slice',type(offset)is int and type(width)is int and 0<=offset<offset+width<=32
            and store.get('instruction')in selected)
        covered.extend(range(offset,offset+width))
    need('exact-once-complete32-field-copy',len(covered)==32 and sorted(covered)==list(range(32)))
    hidden=[r for r in rich.get('hiddenSourceLocals',[])if r.get('memberIndex')==index]
    need('exact-parent-owned-hidden32-local',len(hidden)==1 and type(hidden[0].get('bytes'))is int and hidden[0]['bytes']==32
        and type(hidden[0].get('displacement'))is int and 32<=hidden[0]['displacement']<4096
        and hidden[0].get('sourceInstruction')==read['instruction']
        and hidden[0].get('nominalTypeName')==TYPE and hidden[0].get('nominalTypeDefinition')==layout['typeDefinition'])
    copies=[r for r in rich.get('sourceLocalCopies',[])if r.get('memberIndex')==index]
    need('explicit-source-local-copy-domain',not copies or closed or read.get('sourceContextMode')is None)
    paths=source.get('programs',[])
    need('all-four-complete-parent-frames',len(paths)==4 and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool
        and p.get('frame',{}).get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True
        for p in paths)and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})
    frame_bytes=scope.get('headerProof',{}).get('nullFrameBytes');displacement=hidden[0]['displacement']
    need('literal-own-parent-frame-size',type(frame_bytes)is int and frame_bytes>=displacement+32)
    expected_home=[displacement-frame_bytes,32]
    need('exact-hidden32-home-in-every-positive-frame',all(expected_home in p['frame'].get('hiddenSourceLocalHomes',[])
        and all(type(x)is int for h in p['frame']['hiddenSourceLocalHomes']for x in h)
        for p in paths if not p['wrapperNull']))
    from scripts.game_data.memorypack.montage_value_parent_sources import has_argument_copy
    if copies or has_argument_copy(scope,read,stores):
        from scripts.game_data.memorypack.montage_value_parent_sources import require_copies
        require_copies(source,scope,read,pins,setter,hidden[0],copies,stores,frame_bytes)
    return dict(memberIndex=index,fieldName=read['fieldName'],typeName=TYPE,managedBytes=32,resultAbi='hidden-local',
        referenceLaneOffsets=[8,24],paddingByteRanges=[[1,7],[20,4]],sourceInstruction=read['instruction'],
        setterMethod=method,fieldOffset=setter['fieldOffset'],fieldStores=stores,hiddenSourceLocal=hidden[0],
        completeFieldTransferAndFrameProved=True,wireGrammarAdmitted=False)


def bind(source,scope,read,pins,usage,component,capability):
    need('own-independent-wire-child',capability==CAPABILITY and component.get('schema')==owner.SCHEMA
        and component.get('status')=='validated-conditional-body-type-value-components'and component.get('nativeInputs')==pins
        and component.get('requiredExternalCapabilities')==['byte-payload']
        and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    cap=codec.require_capability(component['capabilities'][capability]);child=component['proof']['source']
    need('fresh-whole-child-source-and-capability',owner.compose(child,pins)==cap)
    transfer=require_transfer(source,scope,read,pins);actual=scope.get('managedValueSources',{}).get(str(read['memberIndex']),{})
    closed=read.get('sourceContextMode')=='owned-closed-forwarder'
    if closed:
        from scripts.game_data.memorypack.montage_value_parent_sources import selection
        _,actual,context,_=selection(scope,read,pins)
    else:context=read['context']
    definition=usage.get('methodSpec',[None])[0]
    argument=bytes.fromhex(context.get('argumentRawHex',''));load=bytes.fromhex(context.get('instructionHex',''))
    instruction=read.get('instruction',[None,'']);call_rva=instruction[0];call=bytes.fromhex(instruction[1])
    need('literal-own-R8-context-and-E8-source',len(argument)==16 and argument[10:12]==bytes((17,128))
        and int.from_bytes(argument[:8],'little')==context.get('typeDefinition')
        and len(load)==7 and load[:3]==bytes.fromhex('4c8b05')
        and(context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))==
            (usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec'))
        and(closed or[context.get('instructionRva'),context.get('instructionHex')]in scope.get('selectedProgram',[]))
        and type(call_rva)is int and len(call)==5 and call[0]==0xe8
        and call_rva+5+int.from_bytes(call[1:],'little',signed=True)==read.get('sourceTargetRva'))
    need('exact-actual-hidden32-source-context',actual.get('schema')==owner.source.SCHEMA
        and actual.get('status')=='proved-conditional-nominal-managed32-source'and actual.get('nativeInputs')==pins
        and actual.get('typeName')==TYPE and actual.get('managedBytes')==32 and actual.get('actualSourceProved')is True
        and actual.get('wireGrammarAdmitted')is False and actual.get('parentFieldAdmitted')is False
        and actual.get('wholeOwnerAdmitted')is False and actual.get('referenceLaneOffsets')==[8,24]
        and actual.get('paddingByteRanges')==[[1,7],[20,4]]
        and actual.get('resultAbi')=='hidden-local'and(closed or actual.get('sourceTargetRva')==read.get('sourceTargetRva'))
        and actual.get('readerMethodDefinition')==definition==context.get('methodSpec',[None])[0]
        and actual.get('proof',{}).get('typedRequest')==usage and context.get('methodSpec')==usage.get('methodSpec')
        and actual.get('proof',{}).get('nominal')==child['proof']['nominal']
        and actual['proof'].get('adapter')==child['proof']['adapter']
        and cap['valueReaderMethodDefinition']==definition and cap['valueDispatcherTargetRva']==actual['proof']['adapter']['dispatcherTargetRva']
        and tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
            ==(6,'MemoryPack.MemoryPackReader','ReadValue',[],[TYPE]))
    return dict(fieldName=read['fieldName'],typeName=TYPE,capability=capability,readerMethodDefinition=definition,
        sourceTargetRva=read['sourceTargetRva'],managedValueTransfer=transfer,managedValueCapabilityShape=cap,
        ordinaryReferenceIdentityClaimed=False)

"""Own Envelope managed32 parent transfer joined to its independent MC7 wire.

The exact named two-curve layout, R8 request, hidden local, two raw field chunks,
lane-zero disabled barrier and complete caller frame are separate requirements.
No managed32 width is consumed as serialized bytes or ordinary reference ABI.
"""
import json
from scripts.game_data.memorypack.skill_impulse_envelope_sources import TYPE
from scripts.game_data.memorypack.skill_impulse_envelope_codec import CAPABILITY,require_capability


def need(key,condition):
    if not condition:raise ValueError('skillImpulseEnvelopeBindings.'+key)


def bind(source,scope,read,pins,usage,component,capability):
    index=read.get('memberIndex');context=read.get('context',{});actual=scope.get('managedValueSources',{}).get(str(index),{})
    need('own-complete-current-parent',source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==scope.get('nativeInputs')==actual.get('nativeInputs')==component.get('nativeInputs')==pins
        and source.get('sourceScope')==scope and source.get('completeSelectedCallerAdmitted')is True
        and source.get('childGrammarAdmitted')is False and source.get('wholeOwnerAdmitted')is False
        and type(index)is int and index>=0 and read.get('declaredType')==TYPE and read.get('kind')=='managed:'+TYPE
        and read.get('mode')=='typed-managed-value'and type(read.get('managedBytes'))is int and read['managedBytes']==32
        and read.get('resultAbi')=='hidden-local'and read.get('actualSourceProved')is True and'wireBytes'not in read
        and read.get('referenceLaneOffsets')==[0,8])
    reads=source.get('orderedSourceReads',[]);setters=source.get('setters',[])
    need('same-owned-event-and-setter',index<len(reads)and reads[index]==read and scope.get('events')==reads
        and index<len(setters)and setters==scope.get('richSetters'))
    raw=bytes.fromhex(context.get('argumentRawHex',''));load=bytes.fromhex(context.get('instructionHex',''))
    need('exact-R8-ordinary-value-request',len(raw)==16 and raw[10:12]==bytes((17,128))
        and int.from_bytes(raw[:8],'little')==context.get('typeDefinition')
        and len(load)==7 and load[:3]==bytes.fromhex('4c8b05')
        and(context.get('register'),context.get('methodOwner'),context.get('methodName'),context.get('fullTypeName'),context.get('typeKind'))==
            ('r8','MemoryPack.MemoryPackReader','ReadValue',TYPE,17)
        and(context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))==
            (usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec'))
        and(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
            (6,'MemoryPack.MemoryPackReader','ReadValue',[],[TYPE])
        and len(usage.get('methodSpec',[]))==3 and type(usage['methodSpec'][0])is int and usage['methodSpec'][0]>0)
    at,encoded=read['instruction'];call=bytes.fromhex(encoded)
    need('actual-value-E8',type(at)is int and len(call)==5 and call[0]==232
        and at+5+int.from_bytes(call[1:],'little',signed=True)==read.get('sourceTargetRva'))
    need('own-complete-actual-value32-source',actual.get('schema')=='endfield.impulse-envelope-value-transfer.v1'
        and actual.get('status')=='proved-conditional-envelope-value32-read'and actual.get('typeName')==TYPE
        and actual.get('managedBytes')==32 and actual.get('referenceLaneOffsets')==[0,8]
        and actual.get('actualSourceProved')is True and actual.get('wireGrammarAdmitted')is False
        and actual.get('sourceTargetRva')==read['sourceTargetRva']and actual.get('resultAbi')=='hidden-local'
        and actual.get('readerMethodDefinition')==usage['methodSpec'][0]and actual.get('proof',{}).get('typedRequest')==usage)
    need('own-wire-capability',capability==CAPABILITY)
    cap=require_capability(component.get('capabilities',{}).get(capability,{}))
    need('same-actual-value-reader-dispatcher',cap['valueReaderMethodDefinition']==usage['methodSpec'][0]
        and cap['valueSourceTargetRva']==read['sourceTargetRva']
        and cap['valueDispatcherTargetRva']==actual['proof']['symbolRvas']['dispatch'])
    setter=setters[index];layout=setter.get('managedValueLayout',{});nominal=actual['proof']['childSource']['layout']
    need('exact-current-nested-layout',layout==dict(nominal,typeDefinition=context['typeDefinition'])
        and layout.get('managedBytes')==32 and layout.get('referenceLaneOffsets')==[0,8]
        and layout.get('paddingByteRanges')==[[30,32]])
    method=setter.get('method',[]);member=setter.get('member',{});parameter=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('same-owned-named-value-setter',len(method)==4 and method[0]==member.get('methodIndex')
        and method[1]==source['wrapperName']==member.get('declaringWrapper')
        and method[2]=='set___'+str(read.get('fieldName'))+'__'and member.get('name')==read['fieldName']
        and member.get('declaredType')==TYPE and setter.get('targetField')==source['wrappedType']+'::'+read['fieldName']
        and len(parameter)==16 and parameter[10:12]==bytes((17,128))
        and int.from_bytes(parameter[:8],'little')==context['typeDefinition']and setter.get('storedBytes')==32
        and setter.get('profile')=='direct-base-holder-setter'and setter.get('getter')is None
        and setter.get('incomingValueStoredUnchanged')is True and setter.get('childGrammarAdmitted')is False)
    rich=scope.get('richProgram',{});selected=rich.get('selectedProgram',[])
    need('complete-owned-rich-source',rich.get('completeSelectedNormalProgram')is True and selected==scope.get('selectedProgram')
        and rich.get('childGrammarAdmitted')is False and rich.get('wholeOwnerAdmitted')is False and read['instruction']in selected)
    hidden=[x for x in rich.get('hiddenSourceLocals',[])if x.get('memberIndex')==index]
    need('exact-named-hidden-local32',len(hidden)==1 and hidden[0].get('bytes')==32
        and hidden[0].get('displacement')==32 and hidden[0].get('sourceInstruction')==read['instruction']
        and hidden[0].get('nominalTypeName')==TYPE and hidden[0].get('nominalTypeDefinition')==context['typeDefinition'])
    stores=[x for x in rich.get('fieldStores',[])if x.get('memberIndex')==index]
    need('exact-two-chunk-field-coverage',[(x.get('sourceOffset'),x.get('storedBytes'))for x in stores]==[(0,16),(16,16)]
        and all(x.get('instruction')in selected for x in stores))
    program=setter['program'];entry=program['selectedBytes'][0][0];base=entry-method[3]
    need('literal-selected-image-base',type(base)is int and base>=0)
    barrier=base+actual['proof']['symbolRvas']['barrier'];field=setter['fieldOffset']
    from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace
    from scripts.game_data.memorypack.generated_envelope_field_sources import setter_program
    norm=lambda x:json.loads(json.dumps(x))
    regions=[(a,bytes.fromhex(h))for a,h in program['selectedBytes']]
    null=program.get('ownedNullExit',{});null_bytes=bytes.fromhex(null.get('bytes',''))
    need('own-complete-nonreturning-null-bytes',len(null_bytes)==6 and null_bytes[0]==232 and null_bytes[-1]==204
        and type(null.get('nullTargetVa'))is int)
    regions.append((null['nullTargetVa'],null_bytes))
    replay=setter_program(regions,entry,field=field,barrier=barrier,
        path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,setter['codeWindows'],base))
    need('whole-own-setter-byte-replay',norm(replay)==program and program.get('referenceLaneOffsets')==[0,8]
        and program.get('barrierReferenceLaneOffset')==0 and program.get('holderOffset')==16)
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    g=_owned_setter_trace([(base+a,bytes.fromhex(h))for a,h in selected],base+context['instructionRva'],scope['codeWindows'],base)
    g.take(load.hex(),'488d4c2420','488b3f');g.call(base+read['sourceTargetRva'])
    g.take('4885ff');g.branch('74',False,1);g.take('488b4f10','4885c9');g.branch('74',False,1)
    g.take('0f10442420','0f104c2430',_displacement('0f1141',field),_displacement('0f1149',field+16))
    g.take('4883c1'+field.to_bytes(1,'little').hex()if field<128 else'4881c1'+field.to_bytes(4,'little').hex(),
        '488b5c2450','488b6c2458','488b742460','4883c440','5f')
    need('exact-restored-parent-tail-barrier',g.relative('e9')==barrier)
    paths=source.get('programs',[])
    need('all-four-owned-frame-paths',len(paths)==4
        and{(p.get('existing'),p.get('wrapperNull'))for p in paths}=={(False,False),(True,False),(False,True),(True,True)}
        and all(p.get('frame',{}).get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and all(any(type(h[0])is int and h[1]==32 for h in p['frame'].get('hiddenSourceLocalHomes',[]))for p in paths if not p['wrapperNull']))
    transfer=dict(memberIndex=index,fieldName=read['fieldName'],typeName=TYPE,managedBytes=32,resultAbi='hidden-local',
        referenceLaneOffsets=[0,8],paddingByteRanges=[[30,32]],sourceInstruction=read['instruction'],setterMethod=method,
        fieldOffset=field,fieldStores=stores,hiddenSourceLocal=hidden[0],completeFieldTransferAndFrameProved=True,wireGrammarAdmitted=False)
    return dict(fieldName=read['fieldName'],typeName=TYPE,capability=capability,readerMethodDefinition=usage['methodSpec'][0],
        sourceTargetRva=read['sourceTargetRva'],managedValueTransfer=transfer,managedValueCapabilityShape=cap,ordinaryReferenceIdentityClaimed=False)

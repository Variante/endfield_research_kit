"""Finite SmartTarget managed40 parent/local/setter and independent MC4 join.

This nominal owner deliberately does not widen the shared managed8/16 gate.
Source and wire proofs must be fresh on the same selected image. Conditional
callback selection and disabled collector remain explicit; no reference ABI or
forty-byte wire record is inferred from the managed representation.
"""
import json
from scripts.game_data.memorypack.skill_smart_target_value_sources import TYPE,CAPABILITY
from scripts.game_data.memorypack.skill_smart_target_value_codec import require_capability
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='skillSmartTargetValueBindings'


def need(key,condition):
    if not condition:raise ValueError(LABEL+'.'+key)


def norm(value):return json.loads(json.dumps(value))


def parent_field_program(g,*,profile,load,source_target,getter,barrier,field):
    """Two literal current callers; holder/Reader roles never interchange."""
    profiles={('rsi','rbx'):('488b3b','488bd6','4885ff','488bcf','74',1),
        ('rdi','rbx'):('488b33','488bd7','4885f6','488bce','0f84',4)}
    need('finite-parent-Reader-output-profile',profile in profiles)
    holder,reader,test,receiver,edge,width=profiles[profile]
    g.take(load.hex(),'488d4c2420',holder,reader);g.call(source_target)
    g.take(test);g.branch(edge,False,width);g.take('33d2',receiver);g.call(getter)
    g.take('4885c0');g.branch(edge,False,width)
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    g.take('0f10442420',_displacement('488d48',field+8),'0f104c2430',_displacement('0f1140',field),
        'f20f10442440',_displacement('0f1148',field+16),_displacement('f20f1140',field+32));g.call(barrier)


def bind(source,scope,read,pins,usage,component,capability):
    from scripts.game_data.memorypack.generated_smart_target_field_sources import setter_program
    index=read.get('memberIndex');context=read.get('context',{});actual=scope.get('managedValueSources',{}).get(str(index),{})
    need('own-current-complete-parent',source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==scope.get('nativeInputs')==actual.get('nativeInputs')==component.get('nativeInputs')==pins
        and source.get('sourceScope')==scope and source.get('completeSelectedCallerAdmitted')is True
        and source.get('childGrammarAdmitted')is False and source.get('wholeOwnerAdmitted')is False
        and type(index)is int and index>=0 and read.get('declaredType')==TYPE
        and read.get('kind')=='managed:'+TYPE and read.get('mode')=='typed-managed-value'
        and type(read.get('managedBytes'))is int and read['managedBytes']==40 and'wireBytes'not in read
        and read.get('resultAbi')=='hidden-local'and read.get('actualSourceProved')is True
        and read.get('referenceLaneOffsets')==[8,24,32])
    reads=source.get('orderedSourceReads',[])
    need('same-owned-ordered-event',index<len(reads)and reads[index]==read and scope.get('events')==reads)
    raw=bytes.fromhex(context.get('argumentRawHex',''));load=bytes.fromhex(context.get('instructionHex',''))
    need('own-R8-value-MethodInfo',len(raw)==16 and raw[10:12]==bytes((17,128))
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
    need('own-complete-actual40-transfer',actual.get('schema')=='endfield.skill-smart-target-value-transfer.v1'
        and actual.get('status')=='proved-conditional-smart-target-value40-read'and actual.get('typeName')==TYPE
        and actual.get('managedBytes')==40 and actual.get('referenceLaneOffsets')==[8,24,32]
        and actual.get('actualSourceProved')is True and actual.get('wireGrammarAdmitted')is False
        and actual.get('sourceTargetRva')==read['sourceTargetRva']and actual.get('resultAbi')=='hidden-local'
        and actual.get('readerMethodDefinition')==usage['methodSpec'][0]and actual.get('proof',{}).get('typedRequest')==usage)
    need('own-wire-capability',capability==CAPABILITY)
    cap=require_capability(component.get('capabilities',{}).get(capability,{}))
    need('same-own-value-reader-and-dispatch',cap['valueReaderMethodDefinition']==usage['methodSpec'][0]
        and cap['valueSourceTargetRva']==read['sourceTargetRva']
        and cap['valueDispatcherTargetRva']==actual['proof']['symbolRvas']['dispatch'])
    setters=source.get('setters',[])
    need('same-complete-own-setter',index<len(setters)and setters==scope.get('richSetters'))
    setter=setters[index];layout=setter.get('managedValueLayout',{});nominal=actual['proof']['childSource']['layout']
    need('exact-current-nested-layout',layout==dict(nominal,typeDefinition=context['typeDefinition'])
        and layout.get('managedBytes')==40 and layout.get('referenceLaneOffsets')==[8,24,32]
        and layout.get('paddingByteRanges')==[[4,8],[20,24]])
    method=setter.get('method',[]);member=setter.get('member',{});parameter=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('same-named-value-setter',len(method)==4 and method[0]==member.get('methodIndex')
        and method[1]==source['wrapperName']==member.get('declaringWrapper')
        and method[2]=='set___'+str(read.get('fieldName'))+'__'and member.get('name')==read['fieldName']
        and member.get('declaredType')==TYPE and setter.get('targetField')==source['wrappedType']+'::'+read['fieldName']
        and len(parameter)==16 and parameter[10:12]==bytes((17,128))
        and int.from_bytes(parameter[:8],'little')==context['typeDefinition']and setter.get('storedBytes')==40
        and setter.get('incomingValueStoredUnchanged')is True and setter.get('childGrammarAdmitted')is False)
    rich=scope.get('richProgram',{});selected=rich.get('selectedProgram',[])
    need('complete-owned-rich-source',rich.get('completeSelectedNormalProgram')is True and selected==scope.get('selectedProgram')
        and rich.get('childGrammarAdmitted')is False and rich.get('wholeOwnerAdmitted')is False and read['instruction']in selected)
    hidden=[x for x in rich.get('hiddenSourceLocals',[])if x.get('memberIndex')==index]
    need('exact-named-hidden-local40',len(hidden)==1 and hidden[0].get('bytes')==40
        and hidden[0].get('displacement')==32 and hidden[0].get('sourceInstruction')==read['instruction']
        and hidden[0].get('nominalTypeName')==TYPE and hidden[0].get('nominalTypeDefinition')==context['typeDefinition'])
    stores=[x for x in rich.get('fieldStores',[])if x.get('memberIndex')==index]
    need('exact16-16-8-field-coverage',[(x.get('sourceOffset'),x.get('storedBytes'))for x in stores]==[(0,16),(16,16),(32,8)]
        and all(x.get('instruction')in selected for x in stores))
    program=setter['program'];entry=program['selectedBytes'][0][0];base=entry-method[3]
    need('actual-native-base',type(base)is int and base>=0)
    barrier=base+actual['proof']['symbolRvas']['barrier'];getter=base+setter['getter']['method'][3];field=setter['fieldOffset']
    regions=[(a,bytes.fromhex(h))for a,h in program['selectedBytes']]
    regions.append((program['ownedNullExit']['instructionVa'],bytes.fromhex(program['ownedNullExit']['bytes'])))
    need('whole-own-setter-byte-replay',norm(setter_program(regions,entry,getter=getter,field=field,barrier=barrier))==program)
    life=source.get('lifecycle',{});own_getter=setter['getter']
    need('same-complete-coherent-holder',own_getter.get('method')==life.get('coherentGetter',{}).get('method')
        and own_getter.get('baseHolder')==life.get('baseHolder')and own_getter.get('typedCache')==life.get('typedCache')
        and own_getter.get('coherentNonNullSamePointerReturn')is True and own_getter.get('refreshAdmitted')is True)
    from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace
    g=_owned_setter_trace([(base+a,bytes.fromhex(h))for a,h in selected],base+context['instructionRva'],scope['codeWindows'],base)
    header=scope.get('headerProof',{})
    parent_field_program(g,profile=(header.get('readerRegister'),header.get('outputRegister')),load=load,
        source_target=base+read['sourceTargetRva'],getter=getter,barrier=barrier,field=field)
    paths=source.get('programs',[])
    need('all-four-owned-frame-paths',len(paths)==4
        and{(p.get('existing'),p.get('wrapperNull'))for p in paths}=={(False,False),(True,False),(False,True),(True,True)}
        and all(p.get('frame',{}).get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and all(any(type(h[0])is int and h[1]==40 for h in p['frame'].get('hiddenSourceLocalHomes',[]))for p in paths if not p['wrapperNull']))
    transfer=dict(memberIndex=index,fieldName=read['fieldName'],typeName=TYPE,managedBytes=40,resultAbi='hidden-local',
        referenceLaneOffsets=[8,24,32],paddingByteRanges=layout['paddingByteRanges'],sourceInstruction=read['instruction'],
        setterMethod=method,fieldOffset=field,fieldStores=stores,hiddenSourceLocal=hidden[0],
        completeFieldTransferAndFrameProved=True,wireGrammarAdmitted=False)
    return dict(fieldName=read['fieldName'],typeName=TYPE,capability=capability,
        readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=read['sourceTargetRva'],
        managedValueTransfer=transfer,managedValueCapabilityShape=cap,ordinaryReferenceIdentityClaimed=False)

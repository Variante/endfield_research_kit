"""Own Int3 raw capture/Advance, integer layout, field stores and caller frame.

The twelve input bytes are established by literal guard/capture instructions.
SSE moves preserve the low eight bytes without floating interpretation;
the high four travel in EBP. Own Int32 axes and nominal setter remain separate
from the source, actual Advance and exact local/field/full-frame proofs.
"""
import json
from scripts.game_data.memorypack import generated_integer_vector_capture_sources as capture
from scripts.game_data.memorypack.generated_called_advance_components import verify_advance
from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace

LABEL='generatedIntegerVectorComponents'


def need(key,condition):
    if not condition:raise ValueError(LABEL+'.'+key)


def norm(value):return json.loads(json.dumps(value))


def _compile_member(owner,scope,read,pins):
    index=read['memberIndex'];macro=read.get('inlineSourceProgram',{});advance=read.get('inlineAdvanceSource',{})
    value=scope.get('valueTypeSources',{}).get(str(index),{});layout=value.get('layout',{});name=capture.TYPE
    need('same-current-owned-Int3-event',type(index)is int and 0<=index<len(scope.get('events',[]))
        and owner.get('nativeInputs')==scope.get('nativeInputs')==pins and owner.get('sourceScope')==scope
        and owner.get('orderedSourceReads',[])[index]==scope['events'][index]==read
        and read.get('declaredType')==name and read.get('kind')=='value12:'+name
        and read.get('mode')=='buffered-called-advance-int-vector12'and read.get('actualSourceProved')is True
        and type(read.get('wireBytes'))is int and read['wireBytes']==12)
    need('own-three-Int32-axes-layout',value.get('typeName')==name and value.get('actualSourceProved')is True
        and value.get('wireBytes')==12 and value.get('resultAbi')=='inline-bits-to-owned-field'
        and layout==read.get('inlineNominalLayout')and layout.get('schema')=='endfield.story-integer-vector-layout.v1'
        and layout.get('typeName')==name and layout.get('managedBytes')==12 and layout.get('fieldCount')==3
        and type(layout.get('typeDefinition'))is int and layout['typeDefinition']>=0
        and layout.get('referenceLaneOffsets')==layout.get('paddingByteRanges')==[]
        and layout.get('wireGrammarAdmitted')is False and[(f.get('name'),f.get('declaredType'),f.get('managedOffset'),f.get('rawKind'))
            for f in layout.get('fields',[])]==[('m_X','int',0,8),('m_Y','int',4,8),('m_Z','int',8,8)])
    at,encoded=read['instruction'];base=macro['guardInstructionVa']-at;selected=scope.get('selectedProgram',[]);header=scope['headerProof']
    need('own-literal-guard-and-register-roles',type(base)is int and base>=0 and bool(selected)
        and(header.get('readerRegister'),header.get('outputRegister'))==('rbx','rdi')
        and bytes.fromhex(encoded)==bytes((131,123,macro['readerOffsets']['bufferLength'],12)))
    regions=[(base+a,bytes.fromhex(h))for a,h in selected]
    replay=capture.program(regions,macro['guardInstructionVa'],macro['readerOffsets'],reader='rbx',output='rdi',
        path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,scope['codeWindows'],base))
    wrapper=macro.get('wrapperLoad',{}).get('register');high=macro.get('capturedSourceSlices',[{},{}])[1].get('register')
    profile=(wrapper,high)
    need('finite-owned-wrapper-and-high-register-profile',profile in(('rsi','rbp'),('rdi','rsi'))
        and(profile!=('rdi','rsi')or index==len(scope['events'])-1))
    need('complete-capture-low-spill-high-integer-and-E8-replayed',norm(replay)==macro
        and macro.get('completeSourceBitsCaptured')is True and macro.get('completeLowEightSpilledBeforeAdvance')is True
        and macro.get('managedLayoutUsedForWidth')is False and macro.get('typedReadUnmanagedClaimed')is False
        and macro.get('preservedCaptureRegistersRequired')==[high])
    verify_advance(advance,macro,pins,base)
    rich=scope.get('richProgram',{});sources=[s for s in rich.get('sources',[])if s.get('memberIndex')==index]
    stores=[s for s in rich.get('fieldStores',[])if s.get('memberIndex')==index]
    locals_=[s for s in rich.get('sourceLocalValues',[])if s.get('memberIndex')==index];flow=value.get('sourceProgram',{})
    need('complete-once-source-local-field-coverage',rich.get('completeSelectedNormalProgram')is True
        and rich.get('selectedProgram')==selected and len(sources)==len(locals_)==1 and len(stores)==2
        and sources[0].get('instruction')==read['instruction']and sources[0].get('mode')==read['mode']
        and sources[0].get('program')==macro and sources[0].get('actualAdvanceSource')==advance
        and value.get('advanceSource')==advance and all(flow.get(k)==v for k,v in macro.items())
        and flow.get('sourceBytes')==macro['selectedBytes']and flow.get('storedBytes')==12
        and flow.get('fullValueBitsStoredUnchanged')is True and flow.get('fieldStoreProgram')==stores
        and[(s.get('sourceOffset'),s.get('storedBytes'))for s in stores]==[(0,8),(8,4)]
        and all(s.get('instruction')in selected for s in stores))
    local=locals_[0];spill=macro['sourceLocalValues'][0]
    need('own-low8-local-before-Advance',local.get('displacement')==spill.get('displacement')==48
        and local.get('bytes')==spill.get('bytes')==8 and local.get('fieldBytes')==12
        and local.get('storeInstruction')==[spill['storeInstructionVa']-base,'F20F11442430'])
    setter=owner['setters'][index];field=setter['fieldOffset'];parameter=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('own-named-ordinary-Int3-setter',setter==scope['richSetters'][index]and setter.get('nominalValueLayout')==layout
        and setter.get('profile')=='direct-base-holder-setter'and setter.get('getter')is None and setter.get('storedBytes')==12
        and setter.get('incomingValueStoredUnchanged')is True and setter.get('member',{}).get('declaredType')==name
        and setter.get('targetField')==owner['wrappedType']+'::'+read['fieldName']
        and len(parameter)==16 and parameter[10:12]==bytes((17,128))and int.from_bytes(parameter[:8],'little')==layout['typeDefinition'])
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    from scripts.game_data.memorypack.generated_vector_member_sources import nonnull
    g=_owned_setter_trace(regions,macro['advanceCallInstructionVa']+5,scope['codeWindows'],base)
    g.take('4885ff'if wrapper=='rdi'else'4885f6');nonnull(g)
    g.take('488b4710'if wrapper=='rdi'else'488b4610','4885c0');nonnull(g)
    area_bound=owner.get('wrappedType')=='Beyond.Gameplay.LevelFactoryRegionAreaBound'
    if area_bound:
        need('exact-two-Int3-AreaBound-profile',scope.get('memberCount')==2
            and [(r.get('fieldName'),r.get('declaredType'))for r in scope['events']]==
                [('size',name),('start',name)]and (index,profile)in((0,('rsi','rbp')),(1,('rdi','rsi'))))
    g.take('f20f10442430')
    if profile==('rsi','rbp')and not area_bound:g.take('488bcb')
    if area_bound and index==1:
        # RBP's old caller value is restored after its last high-word use; the
        # current high word is independently held in RSI. The exact home is
        # checked in both complete positive frames below.
        g.take('488b6c2438')
    g.take(_displacement('f20f1140',field),_displacement('8970'if high=='rsi'else'8968',field+8))
    need('same-actual-integer-field-stores',[norm(s['instruction'])for s in stores]==
        [[a-base,h.upper()]for a,h in g.seen[-2:]])
    program=setter['program'];null=program.get('ownedNullExit',{});null_bytes=bytes.fromhex(null.get('bytes',''))
    need('own-setter-whole-slices-frame-and-null',program.get('sourceSlices')==[[0,8],[8,4]]
        and program.get('completeSourceBitsStoredUnchanged')is True and program.get('normalFrameAndReturn')is True
        and program.get('holderOffset')==16 and len(null_bytes)==6 and null_bytes[0]==232 and null_bytes[-1]==204)
    from scripts.game_data.memorypack.generated_vector_member_sources import base_vector_setter_program
    body=[(a,bytes.fromhex(h))for a,h in program['selectedBytes']];body.append((null['instructionVa'],null_bytes))
    need('actual-named-setter-entry',body[0][0]==base+setter['method'][3])
    actual=base_vector_setter_program(body,body[0][0],holder=16,field=field,width=12)
    actual['ownedNullExit']['bytes']=null_bytes.hex().upper()
    need('exact-whole-named-setter-byte-replay',norm(actual)==program)
    paths=owner.get('programs',[])
    need('all-four-complete-parent-frames',len(paths)==4 and{(p.get('existing'),p.get('wrapperNull'))for p in paths}==
        {(False,False),(True,False),(False,True),(True,True)}and all(p.get('frame',{}).get('entryRspRestored')is True
        and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
    for path in paths:
        if path['wrapperNull']:continue
        frame=path['frame']
        if area_bound:
            frame_bytes=header.get('nullFrameBytes')
            need('exact-AreaBound-saved-RBP-and-low-local-homes',type(frame_bytes)is int
                and dict(frame.get('savedHomes',[])).get('rbp')==56-frame_bytes
                and [48-frame_bytes,8]in frame.get('sourceValueLocalHomes',[]))
        need('own-high-capture-and-low-local-lifetimes',high in dict(frame.get('savedHomes',[]))
            and any(width==8 for _,width in frame.get('sourceValueLocalHomes',[]))
            and any(all(l.get(k)==local[k]for k in('memberIndex','displacement','bytes','storeInstruction','fieldBytes'))and l.get('fieldStores')==stores
                and l.get('liveThroughInstruction')==stores[-1]['instruction']for l in frame.get('sourceValueLocalLifetimes',[])))
        if header.get('headerLocalDisplacement')==local['displacement']:
            retirement_member=index;retirement_local=local;retirement_stores=stores
            if area_bound and index==1:
                # The header was retired once by member0. Reprove that entire
                # field before accepting the later source's reuse of its dead
                # low8 home; selected-program order, never RVA ordering, owns
                # the lifetime boundary.
                need('prior-AreaBound-source-reproved',_compile_member(owner,scope,scope['events'][0],pins)=='unity-vector3-int-raw12')
                retirement_member=0
                prior=[r for r in rich['sourceLocalValues']if r.get('memberIndex')==0]
                retirement_stores=[r for r in rich['fieldStores']if r.get('memberIndex')==0]
                need('same-AreaBound-low8-home-reuse',len(prior)==1 and prior[0].get('displacement')==local['displacement']
                    and prior[0].get('bytes')==local['bytes']==8 and prior[0].get('fieldBytes')==local['fieldBytes']==12)
                retirement_local=prior[0]
                need('prior-field-dead-in-selected-program-before-reuse',retirement_stores[-1]['instruction']in selected
                    and local['storeInstruction']in selected
                    and selected.index(retirement_stores[-1]['instruction'])<selected.index(local['storeInstruction']))
            retired=[r for r in frame.get('retiredHeaderLocalLifetimes',[])if r.get('sourceMemberIndex')==retirement_member]
            need('exact-dead-header-home-retirement',len(retired)==1
                and retired[0].get('headerResultLoad')==header.get('resultLoad')
                and retired[0].get('replacementStore')==retirement_local['storeInstruction']
                and retired[0].get('headerLocalDisplacement')==local['displacement']
                and retired[0].get('headerBytes')==1 and retired[0].get('replacementBytes')==8
                and all(retired[0].get(k)is True for k in('headerValueCopiedBeforeReplacement',
                    'noInterveningHeaderMemoryAccess','selectedStackStable','completeIndependentReplacementSourceFlowRequired'))
                and retired[0].get('fieldLifetime',{}).get('liveThroughInstruction')==retirement_stores[-1]['instruction'])
    return 'unity-vector3-int-raw12'


def compile_member(owner,scope,read,pins):
    try:return _compile_member(owner,scope,read,pins)
    except(ValueError,KeyError,IndexError,TypeError)as error:
        from scripts.game_data.memorypack.corpus_gate import CensusGateError
        failure=CensusGateError(LABEL+'.field',source='scripts/game_data/memorypack/generated_integer_vector_components.py',
            expected='Own Int32 axes, exact8+4 capture/spill/actual Advance, whole named field/setter and full parent/local frames.',
            actual=dict(wrapperName=owner.get('wrapperName'),fieldName=read.get('fieldName'),memberIndex=read.get('memberIndex'),failedGate=str(error)[:1000]))
        failure.diagnostic.update(validator=LABEL,nativeMethod=owner.get('method'),nativeInputs=pins,sourceInstruction=read.get('instruction'),
            sourceWindows=scope.get('codeWindows',[])[:4],helperCodeWindows=read.get('inlineAdvanceSource',{}).get('codeWindows',[])[:3])
        failure.args=(json.dumps(failure.diagnostic,ensure_ascii=False),);raise failure from error

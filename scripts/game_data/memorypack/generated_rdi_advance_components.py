"""Finite RDI capture/actual Advance and complete Vector3 or DWORD transfer.

Raw input widths come from the selected instructions. Vector3 and LayerMask
retain their independently proved nominal layouts; every captured register,
named setter and full caller frame remains an explicit gate.
"""
import json
from scripts.game_data.memorypack import generated_rdi_advance_capture_sources as capture
from scripts.game_data.memorypack.generated_called_advance_components import verify_advance
from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace,_cached_scalar_setter
from scripts.game_data.memorypack.generated_vector_member_sources import setter_program

LABEL='generatedRdiAdvanceComponents'


def need(key,condition):
    if not condition:raise ValueError(LABEL+'.'+key)


def norm(value):return json.loads(json.dumps(value))


def _compile_member(owner,scope,read,pins):
    index=read['memberIndex'];kind=read['kind'];macro=read.get('inlineSourceProgram',{});advance=read.get('inlineAdvanceSource',{})
    vector=kind=='value12:UnityEngine.Vector3';width=12 if vector else 4
    need('finite-own-current-event',type(index)is int and 0<=index<len(scope.get('events',[]))
        and owner.get('sourceScope')==scope and owner.get('nativeInputs')==scope.get('nativeInputs')==pins
        and owner.get('orderedSourceReads',[])[index]==scope['events'][index]==read
        and(kind in('scalar32','value4:UnityEngine.LayerMask')or vector)
        and read.get('mode')==('buffered-called-advance-value12'if vector else'buffered-called-advance-scalar')
        and read.get('actualSourceProved')is True and type(read.get('wireBytes'))is int and read['wireBytes']==width)
    instruction,h=read['instruction'];base=macro['guardInstructionVa']-instruction;offsets=macro['readerOffsets']
    selected=scope.get('selectedProgram',[]);header=scope.get('headerProof',{})
    profile=(header.get('readerRegister'),header.get('outputRegister'))
    need('literal-RDI-guard-and-output',type(base)is int and base>=0 and bool(selected)
        and profile in(('rdi','rsi'),('rdi','r14'))
        and bytes.fromhex(h)==bytes((131,127,offsets['bufferLength'],width)))
    regions=[(base+at,bytes.fromhex(raw))for at,raw in selected]
    replay=capture.program(regions,macro['guardInstructionVa'],offsets,reader=profile[0],output=profile[1],
        path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,scope['codeWindows'],base))
    need('whole-literal-capture-and-actual-E8',norm(replay)==macro and macro.get('wireBytes')==width
        and macro.get('completeSourceBitsCaptured')is True and macro.get('managedLayoutUsedForWidth')is False)
    verify_advance(advance,macro,pins,base)
    rich=scope.get('richProgram',{});flows=[x for x in rich.get('sources',[])if x.get('memberIndex')==index]
    stores=[x for x in rich.get('fieldStores',[])if x.get('memberIndex')==index];setter=owner['setters'][index]
    need('complete-owned-source-to-field',rich.get('completeSelectedNormalProgram')is True and rich.get('selectedProgram')==selected
        and len(flows)==1 and flows[0].get('program')==macro and flows[0].get('actualAdvanceSource')==advance
        and flows[0].get('instruction')==read['instruction']and flows[0].get('mode')==read['mode']
        and [(x.get('sourceOffset'),x.get('storedBytes'))for x in stores]==([(0,8),(8,4)]if vector else[(0,4)])
        and all(x.get('instruction')in selected for x in stores)
        and setter==scope.get('richSetters',[])[index]and setter.get('storedBytes')==width
        and setter.get('incomingValueStoredUnchanged')is True and setter.get('member',{}).get('declaredType')==read['declaredType']
        and setter.get('targetField')==owner['wrappedType']+'::'+read['fieldName'])
    from scripts.game_data.memorypack.generated_member_sources import _displacement,_store_encoding
    field=setter['fieldOffset'];high='rsi'if profile==('rdi','r14')else'r14'
    named_scalar=not vector and profile==('rdi','r14')
    if named_scalar:
        # This profile keeps the DWORD in EBX, then supplies exactly that
        # value and the earlier loaded wrapper to its actual named setter.
        at,encoded=stores[0]['instruction'];raw=bytes.fromhex(encoded)
        positions=[i for i,row in enumerate(selected)if row==stores[0]['instruction']]
        need('actual-named-scalar-call',len(positions)==1 and len(raw)==5 and raw[0]==232
            and base+at+5+int.from_bytes(raw[1:],'little',signed=True)==base+setter['method'][3]
            and stores[0]['instruction']in rich.get('actualCalls',[]))
        position=positions[0]
        need('exact-captured-EBX-wrapper-arguments',position>=3
            and[bytes.fromhex(h)for _,h in selected[position-3:position]]==
                [bytes.fromhex(h)for h in('4533c0','8bd3','488bce')]
            and macro.get('wrapperLoad',{}).get('register')=='rsi'
            and macro.get('capturedSourceSlices')==[dict(register='rbx',sourceOffset=0,bytes=4,
                loadInstructionVa=macro['capturedSourceSlices'][0]['loadInstructionVa'],kind='integer')])
    else:
        expected=[bytes.fromhex(_displacement('f20f1170',field)),_store_encoding('rax',high,field+8,4)]if vector else[bytes.fromhex(_displacement('8998',field))]
        need('actual-captured-registers-reach-whole-field',all(bytes.fromhex(row['instruction'][1])==raw for row,raw in zip(stores,expected,strict=True)))
    paths=owner.get('programs',[]);positive=[p for p in paths if p.get('wrapperNull')is False]
    need('all-four-complete-caller-frames',len(paths)==4 and{(p.get('existing'),p.get('wrapperNull'))for p in paths}==
        {(False,False),(True,False),(False,True),(True,True)}and all(p.get('frame',{}).get('entryRspRestored')is True
        and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
    for path in positive:
        frame=path['frame'];homes=dict(frame.get('savedHomes',[]))
        need('captured-nonvolatiles-owned-by-frame',all(reg in homes for reg in((high,)if vector else('rbx',))))
        if vector:need('whole-XMM6-frame-preserved','xmm6'in frame.get('restoredVectorHomes',{}))
    if vector:
        value=scope.get('valueTypeSources',{}).get(str(index),{});layout=value.get('layout',{});flow=value.get('sourceProgram',{})
        need('own-current-Vector3-layout-and-source',value.get('typeName')==read.get('declaredType')=='UnityEngine.Vector3'
            and value.get('actualSourceProved')is True and value.get('wireBytes')==12
            and value.get('resultAbi')=='inline-bits-to-owned-field'and value.get('advanceSource')==advance
            and layout.get('typeName')=='UnityEngine.Vector3'and layout.get('managedBytes')==12
            and layout.get('wireReadAdmitted')is False and layout.get('fields')==[[axis,'float',16+4*i]for i,axis in enumerate('xyz')]
            and all(flow.get(k)==v for k,v in macro.items())and flow.get('sourceBytes')==macro['selectedBytes']
            and flow.get('storedBytes')==12 and flow.get('fullValueBitsStoredUnchanged')is True and flow.get('fieldStoreProgram')==stores)
        life=owner.get('lifecycle',{});getter=setter.get('getter',{});program=setter.get('program',{});method=setter.get('method',[])
        need('own-coherent-named-Vector3-setter',setter.get('profile')=='cached-getter-setter'
            and getter.get('method')==life.get('coherentGetter',{}).get('method')
            and getter.get('baseHolder')==life.get('baseHolder')and getter.get('typedCache')==life.get('typedCache')
            and getter.get('coherentNonNullSamePointerReturn')is True and program.get('storedBytes')==12
            and program.get('fullValueStoredUnchanged')is True and program.get('normalFrameAndReturn')is True)
        raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
        need('own-nominal-value-parameter',len(raw)==16 and raw[10:12]==bytes((17,128))
            and int.from_bytes(raw[:8],'little')==layout.get('typeDefinition'))
        body=program['selectedBytes'];need('actual-owned-setter-entry',body[0][0]==base+method[3])
        actual=setter_program([(a,bytes.fromhex(h))for a,h in body],base+method[3],getter=base+getter['method'][3],field=field,width=12,
            path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,setter['codeWindows'],base))
        need('whole-named-Vector3-setter-byte-replay',norm(actual)==program)
        return 'unity-vector3-raw12'
    proof=scope.get('inlinePrimitiveSources',{}).get(str(index),{})
    need('same-independent-scalar-capture-and-helper',proof.get('program')==macro and proof.get('advanceSource')==advance and proof.get('wireBytes')==4)
    _cached_scalar_setter(owner,setter,dict(read,kind='scalar32'),base)
    if kind=='value4:UnityEngine.LayerMask':
        nominal=read.get('inlineNamedValueSource',{});raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
        need('own-current-LayerMask-nominal',nominal==proof.get('namedValueSource')and nominal.get('nativeInputs')==pins
            and nominal.get('status')=='validated'and nominal.get('typeName')==read.get('declaredType')=='UnityEngine.LayerMask'
            and nominal.get('wireBytes')==4 and nominal.get('resultRegister')=='eax'and len(raw)==16
            and raw[10:12]==bytes((17,128))and int.from_bytes(raw[:8],'little')==nominal.get('typeDefinition'))
        return 'layer-mask-raw4'
    return 'scalar32'


def compile_member(owner,scope,read,pins):
    try:return _compile_member(owner,scope,read,pins)
    except(ValueError,KeyError,IndexError,TypeError)as error:
        from scripts.game_data.memorypack.corpus_gate import CensusGateError
        failure=CensusGateError(LABEL+'.field',source=owner.get('wrapperName','unknown')+'::Deserialize',
            expected='Exact RDI capture, independently owned actual Advance, nominal field/setter and all caller frames.',
            actual=dict(fieldName=read.get('fieldName'),memberIndex=read.get('memberIndex'),failedGate=str(error)[:600]))
        failure.diagnostic.update(validator=LABEL,nativeInputs=pins,sourceInstruction=read.get('instruction'))
        failure.args=(json.dumps(failure.diagnostic,ensure_ascii=False),);raise failure from error

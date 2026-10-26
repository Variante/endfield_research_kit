"""Pure exact raw8 marker source/nominal/named-field/frame composition."""
import hashlib
import json

from scripts.game_data.memorypack import skill_ai_marker_value_sources as source

LABEL='generatedAiMarkerComponents'


def need(key,valid):
    if not valid:raise ValueError(LABEL+'.'+key)


def norm(value):return json.loads(json.dumps(value))


def _verify_source(proof,pins,base,offsets):
    from scripts.game_data.memorypack.generated_called_advance_components import verify_advance
    regions=proof.get('sourceRegions',[]);windows=proof.get('codeWindows',[])
    need('exact-source-owned-regions',bool(regions)and len(regions)==len(windows)
        and len({at for at,h in regions})==len(regions))
    for at,h in regions:
        raw=bytes.fromhex(h);matching=[w for w in windows if base+w.get('startRva',-base)==at
            and w.get('endRva',0)-w.get('startRva',0)==len(raw)]
        need('exact-current-source-region-hash',len(matching)==1
            and hashlib.sha256(raw).hexdigest().upper()==matching[0].get('sha256'))
    program=source.source_program([(at,bytes.fromhex(h))for at,h in regions],base+proof['targetRva'],offsets)
    need('complete-source-QWORD-frame-replayed',norm(program)==proof.get('program')
        and proof.get('completeBufferedProgram')is True and proof.get('entryRspRestored')is True
        and proof.get('nonvolatilesRestored')is True)
    verify_advance(proof['advanceSource'],dict(advanceTargetVa=program['advanceTargetVa'],readerOffsets=offsets),pins,base)


def _compile_member(owner,scope,read,pins):
    index=read.get('memberIndex');proof=scope.get('primitiveSources',{}).get(str(index),{})
    need('same-current-complete-parent',owner.get('nativeInputs')==scope.get('nativeInputs')==proof.get('nativeInputs')==pins
        and owner.get('sourceScope')==scope and owner.get('completeSelectedCallerAdmitted')is True
        and type(index)is int and 0<=index<len(owner.get('orderedSourceReads',[]))
        and owner['orderedSourceReads'][index]==scope['events'][index]==read
        and read.get('kind')=='value8:'+source.TYPE and read.get('declaredType')==source.TYPE)
    context=read.get('context',{});usage=proof.get('proof',{}).get('typedRequest',{})
    need('same-own-context-identity',context.get('instructionRva')==usage.get('instructionRva')
        and context.get('instructionHex')==usage.get('instructionHex')and context.get('methodSpec')==usage.get('methodSpec')
        and len(usage.get('methodSpec',[]))==3)
    actual=proof['proof']['actualSource'];registered=proof['proof']['registeredSource']
    program=actual['program'];base=program['selectedBytes'][0][0]-proof['targetRva']
    source.bind(context,base+read['sourceTargetRva'],proof,base=base)
    raw=bytes.fromhex(context.get('argumentRawHex',''));layout=proof['proof']['layout']
    need('own-Bool-GameplayTag-padded-layout',layout.get('typeName')==source.TYPE
        and layout.get('managedBytes')==8 and layout.get('boxedBytes')==24
        and layout.get('referenceLaneOffsets')==[]and layout.get('paddingByteRanges')==[[1,4]]
        and layout.get('wireReadAdmitted')is False and len(raw)==16 and raw[10:12]==bytes((17,128))
        and int.from_bytes(raw[:8],'little')==layout.get('typeDefinition')==proof['typeDefinition']
        and[(f.get('name'),f.get('typeName'),f.get('managedOffset'),f.get('bytes'))for f in layout.get('fields',[])]==
            [('invert','bool',0,1),('marker',source.TAG,4,4)])
    need('own-registered-source-not-pointer-alias',proof['proof'].get('pointerAliasInferred')is False
        and proof['proof']['closedRegistration']['pointer']==base+registered['targetRva']
        and proof['proof'].get('actualPointerEqualsRegistered')is(actual['targetRva']==registered['targetRva'])
        and actual['targetRva']==proof['targetRva'])
    offsets=scope['headerProof']['readerOffsets']if'readerOffsets'in scope['headerProof']else actual['advanceSource']['readerOffsets']
    _verify_source(actual,pins,base,offsets)
    if registered!=actual:_verify_source(registered,pins,base,offsets)
    at,h=read['instruction'];raw=bytes.fromhex(h)
    need('actual-field-source-E8',len(raw)==5 and raw[0]==232
        and at+5+int.from_bytes(raw[1:],'little',signed=True)==proof['targetRva'])
    setter=owner['setters'][index];method=setter.get('method',[]);getter=setter.get('getter')or{};life=owner['lifecycle']
    parameter=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('own-nominal-cached-setter-and-lifecycle',setter.get('member',{}).get('name')==read['fieldName']
        and setter.get('member',{}).get('declaredType')==source.TYPE
        and setter.get('nominalValueLayout')==layout and setter.get('profile')=='cached-getter-setter'
        and setter.get('storedBytes')==8 and setter.get('incomingValueStoredUnchanged')is True
        and setter.get('targetField')==owner['wrappedType']+'::'+read['fieldName']
        and len(parameter)==16 and parameter[10:12]==bytes((17,128))
        and int.from_bytes(parameter[:8],'little')==layout['typeDefinition']
        and len(method)==4 and method[1]==owner['wrapperName']
        and getter.get('method')==life.get('coherentGetter',{}).get('method')
        and getter.get('baseHolder')==life.get('baseHolder')and getter.get('typedCache')==life.get('typedCache')
        and getter.get('coherentNonNullSamePointerReturn')is True)
    transfers=[row for row in scope.get('setterTransfers',[])if row.get('memberIndex')==index]
    need('one-own-ordinary-parent-transfer',len(transfers)==1)
    transfer=transfers[0];store=transfer.get('transfer',[]);call=transfer.get('setterCall',[])
    need('same-actual-QWORD-return-to-named-setter',transfer.get('sourceCall')==read['instruction']
        and transfer.get('returnAbi')=='rax'and transfer.get('setterTargetRva')==method[3]
        and len(store)==2 and store[1].upper()=='488BD0'and len(call)==2)
    call_at,call_hex=call;call_raw=bytes.fromhex(call_hex)
    need('own-parent-E8-to-same-named-setter',len(call_raw)==5 and call_raw[0]==232
        and call_at+5+int.from_bytes(call_raw[1:],'little',signed=True)==method[3])
    positive=[path for path in owner.get('programs',[])if path.get('wrapperNull')is False]
    need('actual-parent-transfer-in-both-complete-positive-programs',len(positive)==2
        and all(all(site in path.get('selectedProgram',[])for site in(read['instruction'],store,call))for path in positive))
    from scripts.game_data.memorypack.generated_member_sources import cached_qword_setter_program
    selected=setter['program']['selectedBytes']
    replay=cached_qword_setter_program([(a,bytes.fromhex(h))for a,h in selected],base+method[3],
        getter=base+getter['method'][3],field=setter['fieldOffset'])
    need('own-complete-QWORD-setter-replay',norm(replay)==setter['program'])
    paths=owner.get('programs',[])
    need('four-complete-field-frames',len(paths)==4
        and{(p.get('existing'),p.get('wrapperNull'))for p in paths}=={(False,False),(True,False),(False,True),(True,True)}
        and all(p.get('frame',{}).get('entryRspRestored')is True
            and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
    return source.WIRE


def compile_member(owner,scope,read,pins):
    try:return _compile_member(owner,scope,read,pins)
    except(ValueError,KeyError,IndexError,TypeError)as error:
        from scripts.game_data.memorypack.corpus_gate import CensusGateError
        failure=CensusGateError(LABEL+'.field',source='scripts/game_data/memorypack/generated_ai_marker_components.py',
            expected='exact own raw8 source/Advance, nominal Boolean/GameplayTag layout, named cached setter and full parent frames',
            actual=dict(reason=str(error)[:1200],wrapperName=owner.get('wrapperName'),fieldName=read.get('fieldName')))
        failure.diagnostic.update(validator=LABEL,nativeInputs=pins,memberIndex=read.get('memberIndex'),
            sourceInstruction=read.get('instruction'),sourceWindows=scope.get('codeWindows',[])[:4])
        failure.args=(json.dumps(failure.diagnostic,sort_keys=True),);raise failure from error

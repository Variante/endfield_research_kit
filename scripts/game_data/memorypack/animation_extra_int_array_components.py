"""The two generated Extra Int32 arrays, including their complete field joins.

The source owner proves the actual closed bulk reader. This finite domain
retains its signed count bound and independently replays its bytes, copy and
Advance programs. It never selects an array source by a matching width.
"""
import json

from scripts.game_data.memorypack import module_unmanaged_array_sources as source

SCHEMA='endfield.animation-extra-int-array-components.v1'
CAPABILITY='animation-extra-int32-array'
WIRE=CAPABILITY
MEMBERS={
    ('Beyond.Gameplay.View.Animation.CharacterSpecialDashEntry',1,'performSpDashIndexes'),
    ('Beyond.Gameplay.View.Animation.SpecialIdleEntry',2,'performSpIdleIndexes'),
}


def need(check,condition):
    if not condition:raise ValueError('animationExtraIntArray.'+check)


def norm(value):return json.loads(json.dumps(value))


def compose(actual,pins,*,offsets,advance,copy):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.generated_called_advance_sources import advance_program
    from scripts.game_data.il2cpp.bounded_copy_sources import prove_bounded_copy
    from scripts.game_data.memorypack import npc_array_sources as arrays
    need('exact-own-bulk-source',actual.get('schema')=='endfield.module-unmanaged-array-source.v1'
        and actual.get('status')=='validated-conditional-source'and actual.get('nativeInputs')==pins
        and actual.get('typeName')=='int[]'and actual.get('elementType')=='int'
        and actual.get('headerBytes')==4 and actual.get('elementWireBytes')==4
        and actual.get('countLimit')==64 and actual.get('collectionCounts')==[-1,0]
        and actual.get('resultRegister')=='rax'and actual.get('positiveCountsAdmitted')is True
        and all(actual.get(k)is True for k in('rawBitsPreserved','completeBufferedSourceProved','entryRspRestored','allNonvolatilesRestored'))
        and all(actual.get(k)is False for k in('elementCallbackUsed','booleanNormalizationClaimed','parentFieldAdmitted','wholeOwnerAdmitted')))
    p=actual['proof'];entry=p['programs'][0]['program']['selectedBytes'][0][0];base=entry-actual['targetRva']
    need('literal-selected-image-and-offsets',type(base)is int and base>=1<<32 and set(offsets)==
        {'currentPtr','bufferLength','advancedCount','consumed','totalLength'}and all(type(v)is int and 0<=v<128 for v in offsets.values()))
    raw=regions(p['sourceWindows'],[[a-base,h]for a,h in p['sourceRegions']],base,'extra-int-source')
    caller=regions(p['callerSourceWindows'],[[a-base,h]for a,h in p['callerSourceRegions']],base,'extra-int-caller')
    need('actual-int-body-is-the-called-frontdoor',raw==caller and p.get('forwarder')is None)
    symbols={k:base+v for k,v in p['symbolRvas'].items()}
    parsed=[source.int32_program(raw,entry,offsets,symbols,count=n)for n in(-1,0,1)]
    need('all-complete-buffered-count-paths',norm(parsed)==p['programs'])
    helpers={k:regions(v['windows'],[[a-base,h]for a,h in v['regions']],base,'extra-int-'+k)for k,v in p['helperBodies'].items()}
    expected=dict(empty=source.empty_program(helpers['empty'],symbols['empty'],symbols,element_type='int'),
        allocate=arrays.int_allocate(helpers['allocate'],symbols['allocate'],symbols),
        dataReference=arrays.int_data_reference(helpers['dataReference'],symbols['dataReference'],symbols),
        asSpan=arrays.array_as_span(helpers['asSpan'],symbols['asSpan'],symbols),
        spanConstructor=arrays.array_span_constructor(helpers['spanConstructor'],symbols['spanConstructor']))
    need('exact-all-typed-allocation-and-span-helpers',norm(expected)==p['helpers'])
    ar=regions(advance['windows'],advance['regions'],base,'extra-int-advance')
    advances=[advance_program(ar,symbols['advance'],offsets,zero=z)for z in(False,True)]
    need('all-four-Reader-Advance-fields',norm(advances)==norm(advance['programs']))
    cr=regions(copy['windows'],copy['regions'],base,'extra-int-copy')
    rows=copy['rows'];need('complete-copy-byte-partition',all(b''.join(bytes.fromhex(r['bytes'])for r in rows
        if base+w['startRva']<=int(r['va'],16)<base+w['endRva'])==raw_bytes for w,(_,raw_bytes)in zip(copy['windows'],cr,strict=True)))
    tables={t['startRva']:bytes.fromhex(t['raw'])for t in copy['tables']}
    cp=prove_bounded_copy(cr,symbols['copy'],rows=rows,tables=tables,image_base=base)
    need('every-possible-Int32-payload-copied-unchanged',norm(cp)==p['copy']and cp['maxBytes']==64*4)
    request=p['context']['typedRequest'];call=p['actualCall'];raw_call=bytes.fromhex(call['sourceInstruction'][1])
    need('exact-actual-typed-call',tuple(request.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
        (6,'MemoryPack.MemoryPackReader','ReadUnmanagedArray',[],['int'])and request['methodSpec'][0]==actual['readerMethodDefinition']
        and len(raw_call)==5 and raw_call[0]==232 and call['sourceInstruction'][0]+5+int.from_bytes(raw_call[1:],'little',signed=True)==actual['targetRva'])
    cap=dict(typeName='int[]',elementType='int',headerBytes=4,elementWireBytes=4,countLimit=64,countRange=[-1,64],
        nullable=True,positiveCountsAdmitted=True,rawBitsPreserved=True,booleanNormalizationClaimed=False,
        wholeGrammarAdmitted=True,elementCallbackUsed=False,readerMethodDefinition=actual['readerMethodDefinition'],
        sourceTargetRva=actual['targetRva'],parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    return dict(schema=SCHEMA,status='validated-conditional-animation-extra-int-array',nativeInputs=pins,
        capability=CAPABILITY,capabilities={CAPABILITY:cap},requiredExternalCapabilities=[],
        proof=dict(arraySource=actual,readerOffsets=offsets,advanceSource=advance,copySource=copy),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def validate_component(component,pins):
    need('own-native-component',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
        and component.get('status')=='validated-conditional-animation-extra-int-array'
        and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    p=component['proof'];checked=compose(p['arraySource'],pins,offsets=p['readerOffsets'],advance=p['advanceSource'],copy=p['copySource'])
    need('exact-only-owned-capability',all(component.get(k)==checked[k]for k in('capability','capabilities','requiredExternalCapabilities')))
    return dict(capability=CAPABILITY,capabilities=checked['capabilities'],requiredExternalCapabilities=[])


def derive(image,pins,*,typed_request,call_target,source_instruction):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.generated_called_advance_sources import advance_program
    from scripts.game_data.il2cpp.memory_moves import decode_memory_move_instructions
    from scripts.game_data.contracts import CONTRACTS_DIR
    _publication_gate(image,pins);base=image.pe.image_base
    actual=source.derive(image,pins,typed_request=typed_request,call_target=call_target,source_instruction=source_instruction,element_type='int',count_limit=64)
    offsets=scalar.reader_offsets(image,'animationExtraIntArray');ctx=NativeReferenceContext(image)
    offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    target=base+actual['proof']['symbolRvas']['advance'];body=owned(image,target)
    advance=dict(windows=body['windows'],regions=[[a-base,b.hex()]for a,b in body['regions']],
        programs=[advance_program(body['regions'],target,offsets,zero=z)for z in(False,True)])
    fact=json.loads((CONTRACTS_DIR/'memory_copy_bounded_native.json').read_bytes())
    need('selected-copy-contract-inputs',fact['nativeInputs']==pins and base+fact['entryRva']==base+actual['proof']['symbolRvas']['copy'])
    rows=[];values=[]
    for w in fact['ownedWindows']:
        raw=image.window_bytes(w);values.append([w['startRva'],raw.hex()]);rows+=decode_memory_move_instructions(image.mapper,raw,base+w['startRva'])
    copy=dict(windows=fact['ownedWindows'],regions=values,rows=rows,tables=fact['tables'])
    result=norm(compose(actual,pins,offsets=offsets,advance=advance,copy=copy));_publication_gate(image,pins);return result


def bind_member(full,scope,read,pins,usage,component,capability=CAPABILITY):
    own=validate_component(component,pins);index=read['memberIndex'];actual=component['proof']['arraySource']
    need('two-and-only-two-declared-Extra-array-fields',(full.get('wrappedType'),index,read.get('fieldName'))in MEMBERS
        and read.get('declaredType')=='int[]'and read.get('mode')=='typed-unmanaged-primitive-array'
        and full.get('schema')=='endfield.generated-concrete-reader-source.v1'and full.get('nativeInputs')==pins
        and full.get('completeSelectedCallerAdmitted')is True and full.get('sourceScope')==scope
        and full['orderedSourceReads'][index]==scope['events'][index]==read and scope['arraySources'][str(index)]==actual
        and usage==actual['proof']['context']['typedRequest']and capability==own['capability'])
    setter=scope['richSetters'][index];source.bind_member(actual,read['context'],read,setter,pins,owner=full['wrappedType'])
    rich=scope['richProgram'];stores=[r for r in rich.get('fieldStores',[])if r.get('memberIndex')==index]
    flows=[r for r in rich.get('sources',[])if r.get('memberIndex')==index]
    need('whole-exact-RAX-array-to-named-field',rich.get('completeSelectedNormalProgram')is True
        and rich.get('selectedProgram')==scope.get('selectedProgram')and flows==[dict(memberIndex=index,instruction=read['instruction'],resultAbi='rax')]
        and len(stores)==1 and(stores[0].get('sourceOffset'),stores[0].get('storedBytes'))==(0,8)
        and stores[0]['instruction']in scope['selectedProgram']and full['setters'][index]==setter
        and setter.get('incomingValueStoredUnchanged')is True and setter.get('targetField')==full['wrappedType']+'::'+read['fieldName'])
    at,hexcode=stores[0]['instruction'];raw=bytes.fromhex(hexcode)
    need('same-whole-owned-named-setter-call',len(raw)==5 and raw[0]in(232,233)and at+5+int.from_bytes(raw[1:],'little',signed=True)==setter['method'][3])
    frames=full['programs'];need('all-four-complete-caller-frames',len(frames)==4
        and{(p.get('existing'),p.get('wrapperNull'))for p in frames}=={(False,False),(True,False),(False,True),(True,True)}
        and all(p.get('frame',{}).get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in frames))
    return dict(fieldName=read['fieldName'],typeName='int[]',capability=capability,
        readerMethodDefinition=actual['readerMethodDefinition'],sourceTargetRva=actual['targetRva'],allFourParentFramesProved=True)

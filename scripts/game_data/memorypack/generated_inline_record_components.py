"""Compile current inline captures only with their complete owned field flow.

The native source owner proves each buffered macro, full source-to-store VM,
setter, lifecycle and caller frame. This pure join retains those independent
identities. Neither a managed layout nor a declarative width grants wire bytes.
"""
LABEL='generatedInlineRecordComponents'
SCALARS={
    'raw-byte':('byte',1),'scalar32':('scalar32',4),'scalar64':('scalar64-bits',8),
    'raw4':('float32-bits',4),'float64':('float64-bits',8),
}
VECTORS={
    'value8:UnityEngine.Vector2':('UnityEngine.Vector2','vector2-raw8',8,('x','y')),
    'value12:UnityEngine.Vector3':('UnityEngine.Vector3','unity-vector3-raw12',12,('x','y','z')),
    'value16:UnityEngine.Quaternion':('UnityEngine.Quaternion','unity-quaternion-raw16',16,('x','y','z','w')),
}


def need(check,valid):
    if not valid:raise ValueError(LABEL+'.'+check)


def _coverage(rows,width,offset_key,size_key):
    need('literal-nonempty-slices',bool(rows)and all(type(r.get(offset_key))is int
        and type(r.get(size_key))is int and 0<=r[offset_key]<width
        and 0<r[size_key]<=width-r[offset_key] for r in rows))
    return sorted(i for r in rows for i in range(r[offset_key],r[offset_key]+r[size_key]))==list(range(width))


def _owned_setter_trace(regions,entry,windows,base):
    """Replay selected bytes; untaken edges prove ownership, never cold bodies."""
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    ranges=[]
    for window in windows:
        begin,end=window.get('startRva'),window.get('endRva')
        need('literal-owned-setter-window',type(begin)is int and type(end)is int and 0<=begin<end)
        ranges.append((base+begin,base+end))
    need('owned-nonempty-setter-trace',bool(ranges)and bool(regions)
        and all(type(at)is int and bool(raw)and any(begin<=at<at+len(raw)<=end for begin,end in ranges)for at,raw in regions))
    seen=set()
    for at,raw in regions:
        need('unique-setter-trace-bytes',not seen.intersection(range(at,at+len(raw))))
        seen.update(range(at,at+len(raw)))
    class OwnedTrace(BytesPath):
        def branch(self,prefix,taken,width=4):
            target=self.relative(prefix,width)
            need('setter-branch-target-owned',any(begin<=target<end for begin,end in ranges))
            if taken:
                need('setter-selected-edge-has-actual-bytes',target in self.bytes)
                self.at=target
    return OwnedTrace(regions,entry)


def _cached_scalar_setter(source,setter,read,base):
    """Join a source-owned cached setter to this caller's actual lifecycle."""
    life=source.get('lifecycle',{});getter=setter.get('getter')or{};program=setter.get('program',{})
    method=setter.get('method',[]);getter_method=getter.get('method',[])
    mode={'raw-byte':'normalized-byte-return','scalar32':'int32-return','scalar64':'qword-return',
        'raw4':'single-return','float64':'double-return'}[read['kind']]
    need('cached-scalar-own-lifecycle',len(method)==len(getter_method)==4
        and getter.get('baseHolder')==life.get('baseHolder')and getter.get('typedCache')==life.get('typedCache')
        and isinstance(life.get('typedCache'),list)and len(life['typedCache'])==3
        and life['typedCache'][:2]==[source['wrapperName'],source['wrappedType']]
        and method[1]==getter_method[1]==source['wrapperName']
        and getter.get('coherentNonNullSamePointerReturn')is True
        and getter.get('program',{}).get('fullSameReferenceReturned')is True
        and getter['program'].get('entryRspRestored')is True and getter['program'].get('normalReturn')is True
        and setter.get('targetField')==source['wrappedType']+'::'+read['fieldName']
        and program.get('fieldOffset')==setter.get('fieldOffset'))
    if setter['profile']=='inline-coherent-cache-setter':
        from scripts.game_data.memorypack.generated_member_sources import inline_cached_setter_program
        selected=program.get('selectedBytes',[])
        need('cached-inline-complete-program',bool(selected)and selected[0][0]==base+method[3]
            and program.get('baseSlot')==life['baseHolder'][2]
            and program.get('cacheSlot')==life['typedCache'][2]
            and program.get('normalIncomingValueStoredUnchanged')is True
            and program.get('entryRspRestored')is True and program.get('nonvolatilesRestored')is True
            and program.get('refreshAdmitted')is False and program.get('normalReturnViaBarrier')is False)
        replay=inline_cached_setter_program([(at,bytes.fromhex(raw))for at,raw in selected],base+method[3],
            field=setter['fieldOffset'],mode=mode,base_slot=life['baseHolder'][2],cache_slot=life['typedCache'][2],barrier=0,image_base=base,
            path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,setter.get('codeWindows',[]),base))
        replay['selectedBytes']=[[at,raw]for at,raw in replay['selectedBytes']]
        need('cached-inline-exact-replayed-program',replay==program)
    else:
        call=program.get('getterCall',{});raw=bytes.fromhex(call.get('bytes',''))
        at=int(call.get('va','0'),16)
        need('cached-called-complete-scalar-program',setter['profile']=='cached-getter-setter'
            and program.get('completeCachedSetterChecked')is True
            and program.get('conditionalParameterStoredToGetterReturnedData')is True
            and program.get('mode')==mode and type(call.get('offset'))is int
            and at==base+method[3]+call['offset']and len(raw)==5 and raw[0]==232
            and at+5+int.from_bytes(raw[1:],'little',signed=True)==base+getter_method[3]
            and any(window['startRva']<=at-base<at-base+5<=window['endRva']for window in setter.get('codeWindows',[])))


def _compile_inline_member(source,scope,read,pins):
    index=read['memberIndex'];kind=read['kind'];macro=read.get('inlineSourceProgram',{})
    value=kind in VECTORS
    need('finite-source-owned-kind',kind in SCALARS or value)
    wire,width=(VECTORS[kind][1:3]if value else SCALARS[kind])
    need('same-native-source-and-mode',source.get('nativeInputs')==scope.get('nativeInputs')==pins
        and read.get('mode')==('buffered-inline-value'if value else'buffered-inline-scalar')
        and type(read.get('wireBytes'))is int and read['wireBytes']==width
        and type(macro.get('wireBytes'))is int and macro['wireBytes']==width
        and macro.get('allFourReaderUpdatesProved')is True and macro.get('completeSourceBitsCaptured')is True
        and macro.get('managedLayoutUsedForWidth')is False and bool(macro.get('selectedBytes')))
    captures=macro.get('capturedSourceSlices',[])
    need('all-and-only-native-captured-bytes',_coverage(captures,width,'sourceOffset','bytes')
        and all(isinstance(r.get('register'),str)for r in captures)
        and len({r.get('register')for r in captures})==len(captures))
    offsets=macro.get('readerOffsets',{})
    keys=('currentPtr','bufferLength','advancedCount','consumed')
    need('four-literal-distinct-reader-offsets',all(type(offsets.get(k))is int and 0<=offsets[k]<128 for k in keys)
        and len({offsets[k]for k in keys})==4)
    instruction,encoded=read['instruction'];raw=bytes.fromhex(encoded)
    rdi=scope.get('headerProof',{}).get('readerRegister')=='rdi'
    need('finite-RDI-DWORD-source',not rdi or kind=='scalar32'and width==4
        and scope['headerProof'].get('outputRegister')=='rsi')
    need('actual-literal-buffer-guard',type(instruction)is int and raw==bytes((131,127 if rdi else 123,offsets['bufferLength'],width))
        and type(macro.get('guardInstructionVa'))is int)
    base=macro['guardInstructionVa']-instruction
    selected=scope.get('selectedProgram',[])
    need('complete-owned-selected-byte-program',bool(selected)and type(base)is int and base>=0)
    owned={base+at+i:b for at,h in selected for i,b in enumerate(bytes.fromhex(h))}
    if rdi:
        import json
        from scripts.game_data.memorypack.generated_rdi_scalar_capture_sources import program
        replay=program([(base+at,bytes.fromhex(h))for at,h in selected],base+instruction,offsets,reader='rdi',output='rsi',
            path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,scope.get('codeWindows',[]),base))
        need('exact-replayed-RDI-capture-and-four-updates',json.loads(json.dumps(replay))==macro)
        positive=[p for p in source['programs']if p.get('wrapperNull')is False]
        need('whole-RDI-captured-integer-frame',len(positive)==2
            and {p.get('existing')for p in positive}=={False,True}
            and all(p['frame'].get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True
                and {r['register']for r in captures}<={register for register,home in p['frame'].get('savedHomes',[])}for p in positive))
    seen=set()
    for at,h in macro['selectedBytes']:
        for i,b in enumerate(bytes.fromhex(h)):
            need('actual-inline-byte-in-caller',type(at)is int and at+i not in seen and owned.get(at+i)==b)
            seen.add(at+i)
    rich=scope.get('richProgram',{});sources=[r for r in rich.get('sources',[])if r.get('memberIndex')==index]
    stores=[r for r in rich.get('fieldStores',[])if r.get('memberIndex')==index]
    need('complete-source-to-owned-field-bits',rich.get('completeSelectedNormalProgram')is True
        and rich.get('selectedProgram')==selected and len(sources)==1
        and sources[0].get('instruction')==read['instruction']and sources[0].get('mode')==read['mode']
        and sources[0].get('wireBytes')==width and sources[0].get('program')==macro
        and _coverage(stores,width,'sourceOffset','storedBytes'))
    for store in stores:
        at,h=store['instruction']
        need('actual-field-store-in-caller',type(at)is int
            and all(owned.get(base+at+i)==b for i,b in enumerate(bytes.fromhex(h))))
    nonvolatile={r['register']for r in captures if r['register'].startswith('xmm')and int(r['register'][3:])>=6}
    need('captured-XMM-frame-restored',all(nonvolatile<=set(p['frame'].get('restoredVectorHomes',{}))
        for p in source['programs']if not p['wrapperNull']))
    setter=source['setters'][index];program=setter.get('program',{})
    if rdi:
        from scripts.game_data.memorypack.generated_member_sources import _store_encoding
        need('own-RDI-captured-DWORD-to-named-field',len(stores)==1
            and bytes.fromhex(stores[0]['instruction'][1])==_store_encoding('rax',captures[0]['register'],setter['fieldOffset'],4)
            and setter.get('member',{}).get('name')==read['fieldName']
            and setter.get('member',{}).get('methodIndex')==setter.get('method',[None])[0]
            and setter.get('targetField','').endswith('::'+read['fieldName'])
            and program.get('fieldOffset')==setter['fieldOffset'])
    need('own-complete-incoming-field-setter',setter.get('incomingValueStoredUnchanged')is True
        and type(setter.get('storedBytes'))is int and setter['storedBytes']==width
        and setter.get('member',{}).get('declaredType')==read['declaredType'])
    if value:
        typename,_,_,axes=VECTORS[kind];proof=scope.get('valueTypeSources',{}).get(str(index),{})
        layout=proof.get('layout',{});flow=proof.get('sourceProgram',{})
        need('independent-nominal-inline-layout',read['declaredType']==typename and proof.get('typeName')==typename
            and proof.get('actualSourceProved')is True and proof.get('wireBytes')==width
            and proof.get('resultAbi')=='inline-bits-to-owned-field'
            and layout.get('typeName')==typename and layout.get('managedBytes')==width
            and layout.get('wireReadAdmitted')is False
            and layout.get('fields')==[[axis,'float',16+4*i]for i,axis in enumerate(axes)]
            and all(flow.get(k)==v for k,v in macro.items())and flow.get('sourceBytes')==macro['selectedBytes']
            and flow.get('storedBytes')==width and flow.get('fullValueBitsStoredUnchanged')is True
            and flow.get('fieldStoreProgram')==stores)
        need('whole-inline-vector-setter',program.get('normalFrameAndReturn')is True
            and(program.get('completeSourceBitsStoredUnchanged')is True or program.get('fullValueStoredUnchanged')is True))
    else:
        need('same-independent-inline-scalar',scope.get('inlinePrimitiveSources',{}).get(str(index))==macro)
        if setter.get('profile')in('inline-coherent-cache-setter','cached-getter-setter'):
            _cached_scalar_setter(source,setter,read,base)
        else:
            need('whole-inline-scalar-setter',setter.get('profile')=='direct-base-holder-setter'
                and program.get('completeOriginalProgram')is True
                and program.get('normalIncomingValueStoredUnchanged')is True and program.get('ordinaryFrameRestored')is True)
    return wire


def compile_inline_member(source,scope,read,pins):
    """Expose a bounded source/field diagnostic for every failed inline gate."""
    try:return _compile_inline_member(source,scope,read,pins)
    except (ValueError,KeyError,IndexError)as error:
        from scripts.game_data.memorypack.corpus_gate import CensusGateError
        index=read.get('memberIndex');setters=source.get('setters',[])
        setter=setters[index]if type(index)is int and 0<=index<len(setters)else{}
        program=setter.get('program',{})
        actual=dict(wrapperName=source.get('wrapperName'),fieldName=read.get('fieldName'),memberIndex=index,
            failedGate=str(error)[:500],setterProfile=setter.get('profile'),kind=read.get('kind'),
            mode=read.get('mode'),wireBytes=read.get('wireBytes'),storedBytes=setter.get('storedBytes'),
            setterProgramFlags={key:program.get(key)for key in('completeOriginalProgram','ordinaryFrameRestored',
                'completeCachedSetterChecked','normalIncomingValueStoredUnchanged','entryRspRestored','nonvolatilesRestored')})
        failure=CensusGateError(LABEL+'.inline-field',source=source.get('wrapperName','unknown')+'::Deserialize',
            expected='Complete actual inline capture/store plus the exact owned direct or coherent-cache scalar/vector setter.',actual=actual)
        failure.diagnostic.update(validator=LABEL,wrapperName=source.get('wrapperName'),wrappedType=source.get('wrappedType'),
            memberIndex=index,fieldName=read.get('fieldName'),failedGate=str(error)[:500],sourceInstruction=read.get('instruction'),
            nativeInputs=pins,setterCodeWindows=setter.get('codeWindows',[])[:2])
        import json
        failure.args=(json.dumps(failure.diagnostic,ensure_ascii=False),)
        raise failure from error

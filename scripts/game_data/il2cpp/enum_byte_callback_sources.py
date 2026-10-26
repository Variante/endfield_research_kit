"""Own ByteEnum slot-five raw-byte source and actual dictionary dispatch.

This owner proves the separately registered System.ByteEnum callback, never an
Int32Enum/byte alias. Original concrete enum-to-code/MethodInfo selection is a
separate required join. An actual compared callback address alone does not
establish that selection. No nominal enum grammar is admitted here.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-byte-callback-source.v1'
TYPE='System.ByteEnum'
FORMATTER='MemoryPack.Formatters.UnmanagedFormatter`1'
LABEL='enumByteCallbackSource'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def callback_program(regions,entry,*,refill=False):
    need('literal-refill-case',type(refill)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20','837a3001','498bf8','488bda');g.branch('0f8c',refill)
    refill_target=None
    if refill:
        g.take('4533c0','ba01000000','488bcb');refill_target=g.relative('e8');g.take('90');g.jump('e9')
    else:g.take('488b4250')
    load=g.at;g.take('0fb600','ba01000000','488bcb','8807','488b5c2430','4883c420','5f')
    tail=g.at;advance=g.relative('e9')
    return dict(selectedBytes=g.seen,entry=entry,refill=refill,wireBytes=1,
        sourceLoadInstruction=load,sourceLoadBytes=1,outputStoreBytes=1,
        output='unchanged incoming R8',valueOperation='zero-extend byte to EAX then store unchanged AL',
        advanceTailInstruction=tail,advanceTarget=advance,advanceReader='unchanged incoming RDX',advanceCount=1,
        refillTarget=refill_target,refillArguments=dict(rcx='unchanged Reader',edx=1,r8d=0)if refill else None,
        entryRspRestoredBeforeTail=True,nonvolatilesRestoredBeforeTail=['rbx','rdi'],
        independentAdvanceSourceRequired=True,normalRefillPointerEffectsRequired=refill,
        nominalEnumOrMethodInfoSelectionProved=False)


def dispatch_program(regions,entry,*,prepare,callback,refill=False,indirect=False):
    need('literal-dispatch-cases',type(refill)is bool and type(indirect)is bool and not(refill and indirect))
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20','488b0a','498bf9','498bd8','488bf2');g.call(prepare)
    g.take('488b06','4c8b9090010000','4c8b8898010000');compared=g.relative('488d05');g.take('4c3bd0')
    need('independently-registered-selected-byte-callback',compared==callback)
    g.branch('0f85',indirect)
    refill_target=None;advance=None
    if indirect:
        g.take('4c8bc7','488bd3','488bce','41ffd2','90');g.jump('e9')
    else:
        g.take('837b3001');g.branch('0f8c',refill)
        if refill:
            g.take('4533c0','ba01000000','488bcb');refill_target=g.relative('e8');g.take('90');g.jump('e9')
        else:g.take('488b4350')
        g.take('0fb600','ba01000000','488bcb','8807');advance=g.relative('e8')
    g.take('488b5c2430','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,entry=entry,selectedCallback=callback,slot=5,callbackOffset=400,methodInfoOffset=408,
        selectedPath='indirect-slot-five'if indirect else'matched-inline-raw1',refill=refill,wireBytes=None if indirect else 1,
        prepareTarget=prepare,advanceTarget=advance,refillTarget=refill_target,
        sameReaderAndOutput=True,readerRegister='incoming R8',outputRegister='incoming R9',
        incomingRcxUnused=True,entryRspRestored=True,allNonvolatilesRestored=True,
        independentlySelectedNominalCallbackAndMethodInfoRequired=True)


def primitive_kind5_program(regions,entry,*,image_base):
    """The actual primitive method-selection normalizer's separate byte arm."""
    g=BytesPath(regions,entry)
    g.take('4055','4156','4157','4883ec20','488d6c2420','48895d20','48897528','488bf1','48897d30','4885c9');g.branch('75',True,1)
    g.take('8b01','48c1e003','488d480f','483bc8');g.branch('77',True,1)
    g.take('4883e1f0','488bc1');probe=g.relative('e8');g.take('482be1','33ff','4c8d742420','393e');g.branch('0f86',False)
    need('selected-image-origin',g.relative('4c8d3d')==image_base);g.take('0f1f840000000000');iteration=g.at
    g.take('488b4608','488d0cfd00000000','488b0c01','4885c9');g.branch('74',False,1)
    for kind in(14,29,18,28,20):g.take('80790a'+bytes((kind,)).hex());g.branch('0f84',False)
    g.take('80790a15');g.branch('75',True,1)
    g.take('488b5e08','488d04fd00000000','488b1c18');options=g.relative('488b05');g.take('803800');g.branch('0f84',False)
    g.take('807b0a11');g.branch('75',False,1);g.take('4885db');g.branch('75',True,1)
    g.take('488b0b');class_api=g.relative('e8');g.take('f6803801000004');g.branch('75',True,1)
    g.take('488bcb');underlying=g.relative('e8')
    g.take('0fbe480a','83c1fc','83f907');g.branch('77',False,1)
    g.take('4863c1','418b8c87');table=image_base+int.from_bytes(g.read(4),'little',signed=True)
    g.take('4903cf','ffe1');slot=table+4
    need('owned-kind5-switch-word',all(slot+i in g.bytes for i in range(4)))
    raw=bytes(g.bytes[slot+i]for i in range(4));target=image_base+int.from_bytes(raw,'little',signed=True)
    need('owned-kind5-switch-code',target in g.bytes);g.at=target
    cell=g.relative('488b1d');g.jump('eb',1);g.take('4883c320','807b0a15');g.branch('75',True,1)
    g.take('488d04fd00000000','ffc7','4a891c30','3b3e');back=g.relative('0f82')
    need('same-owned-loop-backedge',back==iteration)
    g.take('8b16','498bce');interner=g.relative('e8')
    g.take('488b5d20','488b7528','488b7d30','488be5','415f','415e','5d','c3')
    return dict(selectedBytes=g.seen,inputKind=17,underlyingKind=5,placeholderCell=cell,
        optionsCell=options,optionsNonzeroRequired=True,classApiTarget=class_api,underlyingTarget=underlying,
        dispatchSlot=slot,dispatchHex=raw.hex().upper(),dispatchTarget=target,internerTarget=interner,probeTarget=probe,
        inputCount=1,bufferValue='fresh separately selected ByteEnum class-cell value +32',
        returnedInternerResultUnchanged=True,entryRspRestored=True,allNonvolatilesRestored=True,
        placeholderClassIdentityProved=False,canonicalInternerIdentityProved=False,nominalCallbackSelected=False)


def class_normalizer_kind5_program(regions,entry,*,image_base):
    """The distinct class-initialization normalizer's actual byte switch arm."""
    g=BytesPath(regions,entry)
    g.take('4055','4156','4157','4883ec20','488d6c2420','48895d20','488bd9',
        '48897528','48897d30','4c896538','4885c9');g.branch('0f84',False)
    g.take('8b11','48c1e203','488d420f','483bc2');g.branch('77',True,1)
    g.take('4883e0f0');probe=g.relative('e8');g.take('482be0','33f6','4c8d742420','3931');g.branch('76',False,1)
    need('class-normalizer-image-origin',g.relative('4c8d25')==image_base)
    iteration=g.at;g.take('488b4b08','488b0cf1');reference=g.relative('e8')
    g.take('4c8d3cf500000000','84c0');g.branch('74',True,1)
    g.take('488b4308','498b3c07');configuration=g.relative('488b05');g.take('803800');g.branch('74',False,1)
    g.take('488bcf');predicate=g.relative('e8');g.take('84c0');g.branch('75',True,1)
    g.take('488bcf');underlying=g.relative('e8');g.take('0fbe480a','83f908');g.branch('75',True,1)
    g.take('83e904','83f907');g.branch('77',False,1)
    g.take('4863c1','418b8c84');table=image_base+int.from_bytes(g.read(4),'little',signed=True)
    g.take('4903cc','ffe1');slot=table+4
    need('owned-class-kind5-switch-word',all(slot+i in g.bytes for i in range(4)))
    raw=bytes(g.bytes[slot+i]for i in range(4));target=image_base+int.from_bytes(raw,'little',signed=True)
    need('owned-class-kind5-code',target in g.bytes);g.at=target
    cell=g.relative('488b3d');g.take('4883c720')
    g.jump('eb',1)if g.bytes.get(g.at)==0xeb else g.jump('e9')
    g.take('807f0a15');g.branch('75',True,1)
    g.take('ffc6','4b893c37','3b33');back=g.relative('72',1)
    need('same-class-normalizer-backedge',back==iteration)
    g.take('8b13','498bce');interner=g.relative('e8')
    g.take('488b5d20','488b7528','488b7d30','4c8b6538','488be5','415f','415e','5d','c3')
    return dict(selectedBytes=g.seen,inputCount=1,inputKind=17,underlyingKind=5,placeholderCell=cell,
        configurationCell=configuration,optionsNonzeroRequired=True,dispatchSlot=slot,dispatchHex=raw.hex().upper(),
        dispatchTarget=target,actualCalls=dict(probe=probe,referencePredicate=reference,enumPredicate=predicate,
            underlyingType=underlying,internArguments=interner),
        placeholderClassInitializedRequired=True,placeholderTypeKind17Required=True,
        referencePredicateMustReturnFalse=True,enumPredicateMustReturnTrue=True,underlyingKind5Required=True,
        bufferValue='fresh separately selected ByteEnum class-cell value +32',returnedInternerResultUnchanged=True,
        entryRspRestored=True,allNonvolatilesRestored=True,placeholderClassIdentityProved=False,
        canonicalInternerIdentityProved=False,nominalCallbackSelected=False)


def derive_source(image,pins,*,dispatch_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.context import type_parameter_owner
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import _vtable
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.enum_constructed_class_paths import _json_set
    from scripts.game_data.memorypack.enum_list_native_sources import full_source,tail_control
    from scripts.game_data.memorypack.generated_called_advance_sources import derive as derive_advance
    from scripts.game_data.memorypack.scalar_param_native import reader_offsets
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    formatter=ctx.index.types[FORMATTER];method,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize']
    need('own-instance-void-slot-five',not method.flags&16 and method.slot==5 and method.parameter_count==2
        and ctx.type_name(method.return_type)=='void');_vtable(image,formatter.index,5,method.index,LABEL)
    params=list(md.parameters_for(method));reader,out=[image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)for p in params]
    need('actual-Reader-byref-and-output-VAR-byref',ctx.type_name(params[0].type_index)=='MemoryPack.MemoryPackReader'
        and reader[10:12]==b'\x11\x20'and out[10:12]==b'\x13\x20')
    variable=type_parameter_owner(md.buf,int.from_bytes(out[:8],'little'),[t.generic_container_index for t in md.types],source=LABEL)
    need('same-owned-class-VAR-zero',variable['typeIndex']==formatter.index and variable['ordinal']==0)
    selected=GenericEntries(image).resolve(method.index,[TYPE],[]);argument,=selected['classInstantiation']['arguments']
    td=ctx.index.types[TYPE];raw=image.pe.bytes_at_va(ctx.type_pointer(td.byval_type_index),16)
    need('own-exact-ByteEnum-argument',argument['type_pointer_va']==ctx.type_pointer(td.byval_type_index)
        and argument['raw_type_record_hex']==raw.hex().upper()and raw[10:12]==b'\x11\x80'
        and int.from_bytes(raw[:8],'little')==td.index and ctx.is_enum(TYPE)
        and ctx.field(TYPE+'::value__')[1:]==('byte',16))
    body,full=full_source(image,selected['pointer']);paths=[callback_program(body['regions'],body['pointer'],refill=c)for c in(False,True)]
    need('same-actual-advance-tail',paths[0]['advanceTarget']==paths[1]['advanceTarget'])
    graph=tail_control(body['rows'],body['pointer'],{paths[0]['advanceTailInstruction']:dict(target=paths[0]['advanceTarget'])})
    offsets=reader_offsets(image,LABEL);advance=derive_advance(image,pins,target=paths[0]['advanceTarget'],offsets=offsets)
    dispatch,dispatch_full=full_source(image,dispatch_target)
    calls=[control_transfer(r)['target']for r in dispatch['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
    need('actual-dispatch-prepare-call',bool(calls))
    dp=[dispatch_program(dispatch['regions'],dispatch_target,prepare=calls[0],callback=selected['pointer'],**case)
        for case in(dict(),dict(refill=True),dict(indirect=True))]
    need('same-independent-actual-Advance-and-refill',dp[0]['advanceTarget']==dp[1]['advanceTarget']==paths[0]['advanceTarget']
        and dp[1]['refillTarget']==paths[1]['refillTarget'])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-placeholder-and-dispatch-source-only',nativeInputs=pins,
        typeName=TYPE,wireBytes=1,callbackTargetRva=selected['pointer']-base,sourceTargetRva=dispatch_target-base,
        proof=dict(registration=selected,typeDefinition=td.index,rawTypeHex=raw.hex().upper(),readerParameterHex=reader.hex().upper(),
            readerTypeDefinition=ctx.index.types['MemoryPack.MemoryPackReader'].index,
            formatterTypeDefinition=formatter.index,formatterMethodDefinition=method.index,namedReaderOffsets=offsets,
            outputParameterHex=out.hex().upper(),outputVariable=variable,callbackFamily=full,callbackPrograms=paths,
            callbackRegions=[[at-base,data.hex()]for at,data in body['regions']],callbackControl=graph,advanceSource=advance,
            dispatchFamily=dispatch_full,dispatchRegions=[[at-base,data.hex()]for at,data in dispatch['regions']],dispatchPrograms=dp),
        actualNominalCallbackSelectionProved=False,parentOrCollectionGrammarAdmitted=False,
        evidenceBoundary=dict(exact='Own separately registered ByteEnum slot-five ABI/raw1 source, independently owned Advance1 and actual key-dispatch compared/indirect paths.',
            conditional='Sufficient disjoint buffered storage, normal actual refill/prepare/helper effects and an independently selected original nominal callback/MethodInfo.',
            structuralOnly='Raw byte transport; no Int32Enum or byte primitive alias.',
            unresolved=['actual original enum class/MethodInfo to selected ByteEnum code/interner/method-table join','runtime provider/registry state','parent/EOF'])),default=_json_set))

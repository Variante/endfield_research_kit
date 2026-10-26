"""Own registered Int32Enum formatter source, never a nominal enum alias.

The exact independently selected UnmanagedFormatter<System.Int32Enum>
Deserialize registration has an owned slot5/Reader-byref/own-VAR-byref ABI.
Its full current instruction partition, control flow and normal frames are
checked. The buffered path copies one raw DWORD to the unchanged output and
updates all four named Reader fields by four. Separate refill/negative-advance
paths preserve the actual pointer, requested amount and helper return choices;
their helper effects remain conditions. The source has no record header or
FF/null shortcut, and never interprets the four-byte value as another nominal.

The current registered placeholder carrier is joined to its actual metadata
record and selected class-inst argument. No concrete enum MethodInfo, live
receiver/provider choice or nominal-to-placeholder equality is supplied by
that registration. Initialized compatible context and helper/storage/cursor
conditions remain explicit. This owner proves placeholder source bytes only;
concrete enum wire/list/parent/whole owner admission remains false.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-placeholder-callback-paths.v1'
LABEL='enumPlaceholderCallbackPaths'
TYPE='System.Int32Enum'
FORMATTER='MemoryPack.Formatters.UnmanagedFormatter`1'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def program(regions,entry,*,refill=False,negative_advance=False,advance_return=None):
    need('literal-current-callback-path',type(refill)is bool and type(negative_advance)is bool
        and (type(advance_return)is bool if negative_advance else advance_return is None)
        and (refill or not negative_advance))
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','837a3004','498bf8','488bda')
    g.branch('0f8c',refill);refill_call=None
    if refill:
        g.take('4533c0','ba04000000','488bcb');refill_call=g.relative('e8');g.take('90');g.jump('e9')
    else:g.take('488b4250')
    source=g.at;g.take('8b00','8907','8b7b30','83c7fc');g.branch('0f88',negative_advance)
    advance_call=None
    if negative_advance:
        g.take('ba04000000','488bcb');advance_call=g.relative('e8');g.take('84c0');g.branch('0f85',advance_return)
        if not advance_return:g.jump('e9')
    if not negative_advance or not advance_return:
        g.take('4883435004','83434004','83434404','897b30')
    g.take('488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,entry=entry,refill=refill,negativeAdvance=negative_advance,
        advanceReturnedNonzero=advance_return,actualRefillTarget=refill_call,actualAdvanceTarget=advance_call,
        refillArguments=dict(rcx='unchanged incoming Reader RDX',edx=4,r8=0)if refill else None,
        advanceArguments=dict(rcx='unchanged incoming Reader RDX',edx=4)if negative_advance else None,
        sourceLoadInstruction=source,sourceLoadBytes=4,outputStoreBytes=4,output='unchanged incoming R8 address',
        headerOrNullMarkerConsumed=False,wireValueInterpretationAdmitted=False,
        inlineCursorUpdate=not negative_advance or not advance_return,
        inlineReaderEffects=dict(currentPtr=4,bufferLength=-4,advancedCount=4,consumed=4)
            if not negative_advance or not advance_return else None,
        compatibleRefillPointerAndCursorEffectsRequired=refill,compatibleAdvanceEffectsRequired=negative_advance,
        stableDisjointReaderOutputSourceAndFrameRequired=True,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rdi'],normalReturn=True)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.context import type_parameter_owner
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import _vtable
    from scripts.game_data.il2cpp.enum_reflection_dispatch_paths import decode
    from scripts.game_data.il2cpp.enum_instantiation_seed_paths import complete_program
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack import scalar_param_native as scalar
    _publication_gate(image,pins);ctx=NativeReferenceContext(image);md=image.metadata;owner=ctx.index.types[FORMATTER]
    methods=[m for m in md.methods_for(owner)if md.string(m.name_index)=='Deserialize']
    need('one-exact-formatter-method',len(methods)==1);method,=methods
    need('owned-instance-void-slot5',not method.flags&0x10 and method.slot==5 and method.parameter_count==2
        and ctx.type_name(method.return_type)=='void'and not ctx.is_value_type(FORMATTER))
    _vtable(image,owner.index,5,method.index,LABEL);scalar.ordinary(image,ctx.type_pointer(method.return_type),1,LABEL)
    parameters=list(md.parameters_for(method));need('two-actual-parameters',len(parameters)==2)
    reader,output=[image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)for p in parameters]
    reader_type=ctx.index.types['MemoryPack.MemoryPackReader']
    need('exact-owned-Reader-byref',ctx.type_name(parameters[0].type_index)=='MemoryPack.MemoryPackReader'
        and reader[10:12]==b'\x11\x20'and int.from_bytes(reader[:8],'little')==reader_type.index)
    need('own-class-VAR-byref',output[10:12]==b'\x13\x20')
    parameter=type_parameter_owner(md.buf,int.from_bytes(output[:8],'little'),
        [t.generic_container_index for t in md.types],source=LABEL)
    need('same-owned-output-VAR0',parameter['typeIndex']==owner.index and parameter['ordinal']==0)
    selected=GenericEntries(image).resolve(method.index,[TYPE],[]);argument,=selected['classInstantiation']['arguments']
    td=ctx.index.types[TYPE];pointer=ctx.type_pointer(td.byval_type_index);raw=image.pe.bytes_at_va(pointer,16)
    need('exact-own-placeholder-registration-argument',argument['type_pointer_va']==pointer
        and argument['raw_type_record_hex']==raw.hex().upper()and raw[10:12]==b'\x11\x80'
        and int.from_bytes(raw[:8],'little')==td.index and ctx.is_enum(TYPE))
    offsets=scalar.reader_offsets(image,LABEL)
    need('same-owned-four-Reader-fields',offsets==dict(currentPtr=80,bufferLength=48,advancedCount=64,consumed=68))
    body=owned(image,selected['pointer']);rows=[]
    for at,data in body['regions']:rows+=checked_rows(decode(image.mapper,data,at),data,LABEL)
    rows.sort(key=lambda r:int(r['va'],16));graph,padding=complete_program(body['regions'],rows,body['pointer'])
    paths=[program(body['regions'],body['pointer'],**p)for p in(dict(),dict(refill=True),
        dict(refill=True,negative_advance=True,advance_return=False),dict(refill=True,negative_advance=True,advance_return=True))]
    need('same-actual-refill-and-negative-advance-helpers',len({p['actualRefillTarget']for p in paths if p['refill']})==1
        and len({p['actualAdvanceTarget']for p in paths if p['negativeAdvance']})==1)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-placeholder-source-only',nativeInputs=pins,
        proof=dict(typeName=TYPE,typeDefinition=td.index,registeredTypePointer=pointer,registeredTypeRawHex=raw.hex().upper(),
            formatterType=FORMATTER,formatterDefinition=owner.index,methodDefinition=method.index,registration=selected,
            abi=dict(slot=5,readerByrefRawHex=reader.hex().upper(),outputVarByrefRawHex=output.hex().upper(),outputParameter=parameter),
            namedReaderOffsets=offsets,callbackWindows=body['windows'],callbackCfg=graph,callbackPadding=padding,selectedPaths=paths),
        placeholderBufferedDwordSourceProved=True,actualConcreteEnumCallbackOrMethodInfoIdentityProved=False,
        concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own selected placeholder registration, slot5/own VAR/Reader ABI, full source/CFG/frame and four selected raw DWORD/cursor/refill/advance paths.',
            conditional=__doc__,structuralOnly='Placeholder callback source and actual Reader/output transfers.',
            unresolved=['actual nominal-to-placeholder selection and incoming MethodInfo/RGCTX','live receiver/provider/cache and helper effects',
                'concrete enum wire/list/parent/EOF']))))

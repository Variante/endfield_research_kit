"""Separate current primitive generic normalizer's exact kind17/count1 arm.

This is independently selected from the second actual Int32Enum class-cell
reader. Its inlined kind17/reference tests, raw class enum bit, underlying
kind8 switch word, same initialized placeholder cell plus32, unchanged buffer
and count into the actual interner, and complete restored return are proved.
It is distinct from the previously proved class-initialization normalizer;
neither a similar name nor a common placeholder selects an enclosing caller.

Coherent initialized type/class state, the selected static options publication,
normal class/underlying helpers and disjoint stable storage remain conditions.
The enclosing method-pointer selection and cache/table population are separate
joins. No concrete formatter, MethodInfo/callback, collection or wire grammar
is admitted by this source path.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-primitive-normalizer-paths.v1'
LABEL='enumPrimitiveNormalizerPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def program(regions,entry,*,image_base):
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
    g.take('4903cf','ffe1');slot=table+4*4
    need('owned-kind8-switch-word',all(slot+i in g.bytes for i in range(4)))
    raw=bytes(g.bytes[slot+i]for i in range(4));target=image_base+int.from_bytes(raw,'little',signed=True)
    need('owned-kind8-switch-code',target in g.bytes);g.at=target
    cell=g.relative('488b1d');g.jump('eb',1);g.take('4883c320','807b0a15');g.branch('75',True,1)
    g.take('488d04fd00000000','ffc7','4a891c30','3b3e');back=g.relative('0f82')
    need('same-owned-counted-loop-backedge',back==iteration)
    g.take('8b16','498bce');interner=g.relative('e8')
    g.take('488b5d20','488b7528','488b7d30','488be5','415f','415e','5d','c3')
    return dict(selectedBytes=g.seen,inputCount=1,inputKind=17,inputNonnullRequired=True,inputByrefBitClearRequired=True,
        optionsCell=options,optionsByteNonzeroRequired=True,classApiTarget=class_api,classArgument='unchanged input type first QWORD',
        classFlagsOffset=312,classEnumMask=4,classEnumFlagSetRequired=True,underlyingTarget=underlying,
        underlyingKind=8,kindSubtract=4,dispatchSlot=slot,dispatchHex=raw.hex().upper(),dispatchTarget=target,
        placeholderCell=cell,placeholderClassNonnullAndInitializedRequired=True,
        bufferValue='fresh placeholder class-cell value +32',bufferAlignment=16,bufferBytesForCount1=16,
        internerTarget=interner,internerArguments=dict(rcx='owned buffer',edx='unchanged incoming count1'),
        returnedInternerResultUnchanged=True,probeTarget=probe,entryRspRestored=True,normalReturn=True,
        nonvolatilesRestored=['rbx','rbp','rsi','rdi','r14','r15'],
        enclosingMethodPointerSelectionProved=False,actualConcreteCallbackSelected=False)


def null_program(regions,entry):
    """Complete null-instantiation return, independently of the count1 path."""
    g=BytesPath(regions,entry)
    g.take('4055','4156','4157','4883ec20','488d6c2420','48895d20','48897528','488bf1','48897d30','4885c9');g.branch('75',False,1)
    g.take('33c0');g.jump('e9')
    g.take('488b5d20','488b7528','488b7d30','488be5','415f','415e','5d','c3')
    return dict(selectedBytes=g.seen,inputInstantiation=None,returnedRax=0,opaqueCalls=0,
        entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rsi','rdi','r14','r15'],normalReturn=True)


def derive(image,pins,*,entry,**key_arguments):
    from scripts.game_data.il2cpp.enum_source_variants import select,BYTE_CONDITION
    enum_variant=key_arguments.get("enum_variant");variant=select(enum_variant)
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_name_lookup_paths import derive as name_source
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);base=image.pe.image_base
    prior=name_source(image,pins,**key_arguments)
    interner=prior['proof']['internerSource'];placeholder=interner['proof']['placeholderTypeSource']
    keys=placeholder['proof']['argumentKeySource'];selection=keys['proof']['normalizerSelection'];normal=selection['proof']['normalizer']
    need('distinct-actual-normalizer-entry',type(entry)is int and entry!=selection['proof']['normalizerWindows'][0]['startRva']+base)
    body=owned(image,entry);
    if enum_variant is None:source=program(body['regions'],entry,image_base=base)
    else:
        from scripts.game_data.il2cpp.enum_byte_callback_sources import primitive_kind5_program
        source=primitive_kind5_program(body['regions'],entry,image_base=base)
        source=dict(source,optionsCell=source['optionsCell'],optionsByteNonzeroRequired=True)
    null=null_program(body['regions'],entry)
    need('same-actual-placeholder-options-underlying-and-interner',source['placeholderCell']==normal['placeholderCell']
        and source['optionsCell']==normal['configurationCell']and source['underlyingTarget']==normal['actualCalls']['underlyingType']
        and source['internerTarget']==normal['actualCalls']['internArguments']and source['probeTarget']==normal['actualCalls']['probe'])
    need('same-independent-actual-first-qword-class-resolver',all(source['classApiTarget']==base+c['classHelperTargets']['firstQwordClassLookupRva']
        for c in selection['cases']))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(nameAndInternerSource=prior,primitiveNormalizerWindows=body['windows'],selectedKind17Path=source,nullInstantiationPath=null),
        **({"primitiveKind8SelectsExactInt32EnumCellConditional":True}if enum_variant is None else{"primitiveKind5SelectsExactByteEnumCellConditional":True}),enclosingMethodPointerSelectionProved=False,
        initializedInternerResultIdentityProved=False,concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Separate actual primitive normalizer selected count1/nonbyref-kind17/enum/kind8 switch word, actual helper/cell/interner identities and full return frame.'if enum_variant is None else'Distinct actual primitive normalizer selected count1/nonbyref-kind17/enum/kind5 switch, same independently selected ByteEnum cell/interner and complete restored frame.',
            conditional=__doc__ if enum_variant is None else BYTE_CONDITION,structuralOnly='Native primitive generic normalization and placeholder representation.',
            unresolved=['actual enclosing method-pointer resolver/caller','initialized table/cache/static registration identity',
                'actual nominal provider/formatter/MethodInfo callback selection','wire/parent/EOF']))))

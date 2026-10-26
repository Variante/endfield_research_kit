"""Source-only Int32 enum normalization, class-cell and interner transfers.

Actual normalizer E8s select the independently proved kind17 reference/enum
predicate and underlying helpers. Under the explicit positive class-flag,
underlying kind8 and initialized placeholder conditions, one complete count1
normalizer path writes the freshly loaded Int32Enum class cell plus32 into its
owned aligned buffer and passes that buffer/count unchanged to its actual
interner. The returned interner value is forwarded unchanged after restoring
the original frame. The primitive class helper's kind8 path and the startup
name-request/result-cell store are independently selected from current bytes.

These are conditional native source transfers. Startup execution, coherent
live type/class caches, opaque class lookup/interner returns, aliases across
children and actual concrete nominal formatter/MethodInfo selection remain
unresolved. No Int32/Int32Enum substitution, collection counts, wire grammar,
parent or physical EOF follows from a shared placeholder or scalar width.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='enumNormalizerSelectionPaths'
SCHEMA='endfield.enum-normalizer-selection-paths.v1'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def reference_kind17_program(regions,entry):
    g=BytesPath(regions,entry);g.take('4883ec28','4885c9');g.branch('74',False,1)
    for kind in(18,29,20,14,28,21):
        g.take('80790a'+bytes((kind,)).hex());g.branch('74',False,1)
    g.take('32c0','4883c428','c3')
    return dict(selectedBytes=g.seen,inputKind=17,inputNonnullRequired=True,returnedLowByte=0,
        normalReturn=True,entryRspRestored=True,nonvolatilesUnchanged=True,noCalls=True)


def probe_program(regions,entry):
    """Own complete register-preserving stack-probe loop and both exits."""
    g=BytesPath(regions,entry)
    g.take('4883ec10','4c891424','4c895c2408','4d33db','4c8d542418','4c2bd0','4d0f42d3',
        '654c8b1c2510000000','4d3bd3');restore=g.relative('73',1)
    g.take('664181e200f0');loop=g.at
    g.take('4d8d9b00f0ffff','41c60300','4d3bd3');back=g.relative('75',1)
    need('exact-stack-page-backedge',back==loop);need('exact-stack-probe-restore',g.at==restore)
    g.take('4c8b1424','4c8b5c2408','4883c410','c3')
    return dict(selectedBytes=g.seen,entryRspRestored=True,preservedRegisters=['rax','rcx','rdx','r8','r9','r10','r11'],
        allWin64NonvolatilesUnchanged=True,opaqueCalls=0,pageStride=4096,pageTargetRuntime=True,
        pageTouchesRequireFiniteNormalReturn=True,GSBaseAndPageAvailabilityObserved=False)


def _class_kind_program(regions,entry,*,image_base,input_kind=8):
    """Complete selected nonnull primitive class-cell return, not class identity."""
    need("explicit-primitive-class-kind",type(input_kind)is int and input_kind in(5,8))
    g=BytesPath(regions,entry)
    g.take('4053','4883ec20','0fbe410a');need('actual-class-image-base',g.relative('4c8d05')==image_base)
    g.take('488bd9','83f80f');g.branch('7c',True,1)
    g.take('ffc8','3dfe000000');g.branch('77',False,1)
    g.take('4863c8','410fb68408');selector=image_base+int.from_bytes(g.read(4),'little',signed=True)
    g.take('418b8c80');table=image_base+int.from_bytes(g.read(4),'little',signed=True)
    g.take('4903c8','ffe1')
    need('owned-primitive-selector',selector+input_kind-1 in g.bytes)
    index=g.bytes[selector+input_kind-1];slot=table+index*4
    need('owned-primitive-target',all(slot+i in g.bytes for i in range(4)))
    raw=bytes(g.bytes[slot+i]for i in range(4));target=image_base+int.from_bytes(raw,'little',signed=True)
    need('owned-primitive-code-target',target in g.bytes);g.at=target;cell=g.relative('488b05')
    if g.bytes[g.at]==0xeb:g.jump('eb',1)
    else:g.jump('e9')
    g.take('4885c0');g.branch('75',True,1);g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,inputKind=input_kind,selectorAddress=selector+input_kind-1,selectorByte=index,
        tableSlot=slot,tableHex=raw.hex().upper(),selectedTarget=target,classCell=cell,
        classCellNonnullRequired=True,returnedValue='fresh QWORD class-cell value',classIdentityProved=False,
        normalReturn=True,entryRspRestored=True,nonvolatileRbxRestored=True)


def class_kind8_program(regions,entry,*,image_base):
    return _class_kind_program(regions,entry,image_base=image_base)


def normalizer_program(regions,entry,*,image_base):
    """Complete count1 concrete enum path with explicit fresh raw predicates."""
    g=BytesPath(regions,entry)
    g.take('4055','4156','4157','4883ec20','488d6c2420','48895d20','488bd9',
        '48897528','48897d30','4c896538','4885c9');g.branch('0f84',False)
    g.take('8b11','48c1e203','488d420f','483bc2');g.branch('77',True,1)
    g.take('4883e0f0');probe=g.relative('e8');g.take('482be0','33f6','4c8d742420','3931');g.branch('76',False,1)
    need('actual-normalizer-image-base',g.relative('4c8d25')==image_base)
    iteration=g.at;g.take('488b4b08','488b0cf1');reference=g.relative('e8')
    g.take('4c8d3cf500000000','84c0');g.branch('74',True,1)
    g.take('488b4308','498b3c07');configuration=g.relative('488b05');g.take('803800');g.branch('74',False,1)
    g.take('488bcf');predicate=g.relative('e8');g.take('84c0');g.branch('75',True,1)
    g.take('488bcf');underlying=g.relative('e8');g.take('0fbe480a','83f908');g.branch('75',False,1)
    placeholder=g.relative('488b3d');g.take('4883c720');g.jump('eb',1)
    g.take('807f0a15');g.branch('75',True,1)
    g.take('ffc6','4b893c37','3b33');back=g.relative('72',1)
    need('same-owned-normalizer-loop-backedge',back==iteration)
    g.take('8b13','498bce');intern=g.relative('e8')
    g.take('488b5d20','488b7528','488b7d30','4c8b6538','488be5','415f','415e','5d','c3')
    return dict(selectedBytes=g.seen,count=1,configurationCell=configuration,configurationByteNonzeroRequired=True,
        placeholderCell=placeholder,placeholderClassInitializedRequired=True,placeholderTypeKind17Required=True,
        referencePredicateMustReturnFalse=True,enumPredicateMustReturnTrue=True,underlyingKind8Required=True,
        actualCalls=dict(probe=probe,referencePredicate=reference,enumPredicate=predicate,underlyingType=underlying,internArguments=intern),
        bufferAlignment=16,bufferBytesForCount1=16,storedTypePointer='fresh placeholder class-cell value +32',
        internerArguments=dict(rcx='owned buffer',edx='unchanged input count1'),returnedInternerResultUnchanged=True,
        entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r14','r15'],
        placeholderClassIdentityProved=False,internerResultIdentityProved=False)


def publication_program(regions,entry):
    g=BytesPath(regions,entry);name=g.relative('4c8d05');namespace=g.relative('488d15');assembly=g.relative('488b0d')
    lookup=g.relative('e8');cell=g.relative('488905')
    return dict(selectedBytes=g.seen,end=g.at,nameAddress=name,namespaceAddress=namespace,assemblyCell=assembly,
        classLookup=lookup,resultCell=cell,returnedLookupValueStoredUnchanged=True,
        lookupResultIdentityProved=False,completeStartupControlProved=False)


def derive(image,pins,*,enum_requests,normalizer_entry,publication_entry,fixup_arguments,enum_variant=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp import enum_class_field_paths,enum_normalization_value_paths
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.il2cpp.enum_source_variants import select,BYTE_CONDITION
    variant=select(enum_variant)
    _publication_gate(image,pins);base=image.pe.image_base
    need('bounded-explicit-enum-requests',type(enum_requests)is list and 0<len(enum_requests)<=32)
    need('literal-selected-source-entries',all(type(p)is int and p>base for p in(normalizer_entry,publication_entry)))
    body=owned(image,normalizer_entry)
    if enum_variant is None:normal=normalizer_program(body['regions'],normalizer_entry,image_base=base)
    else:
        from scripts.game_data.il2cpp.enum_byte_callback_sources import class_normalizer_kind5_program
        normal=class_normalizer_kind5_program(body['regions'],normalizer_entry,image_base=base)
    calls=normal['actualCalls'];probe=owned(image,calls['probe']);probe_source=probe_program(probe['regions'],calls['probe'])
    reference=owned(image,calls['referencePredicate']);reference_source=reference_kind17_program(reference['regions'],calls['referencePredicate'])
    cases=[enum_normalization_value_paths.derive(image,pins,enum_type=name,typed_request=request,
        predicate_target=calls['enumPredicate'],underlying_target=calls['underlyingType'],enum_variant=enum_variant)for name,request in enum_requests]
    need('bounded-distinct-current-enum-requests',0<len(cases)<=32 and len({json.dumps(c['typedParentRequest'],sort_keys=True)for c in cases})==len(cases))
    need('fresh-class-fixup-arguments',type(fixup_arguments)is dict and 'enum_requests'not in fixup_arguments)
    own_fixup=dict(fixup_arguments)
    if enum_variant is not None:own_fixup['enum_variant']=enum_variant
    fields=enum_class_field_paths.derive(image,pins,enum_requests=enum_requests,**own_fixup)
    api=fields['proof'];api_entry=base+api['namedApiEntryRva'];api_raw=bytes.fromhex(api['namedApiRawHex'])
    need('actual-owned-class-helper-tail',len(api_raw)==7 and api_raw[:3]==bytes.fromhex('b201e9'))
    class_helper_entry=api_entry+7+int.from_bytes(api_raw[3:],'little',signed=True)
    need('actual-enum-element-callback-is-selected-class-helper',
        fields['proof']['constructor']['elements'][1]['helperTarget']==class_helper_entry)
    class_body=owned(image,class_helper_entry);primitive=_class_kind_program(class_body['regions'],class_helper_entry,image_base=base,input_kind=variant['underlyingKind'])
    prefix=image.pe.bytes_at_va(publication_entry,64);publication=publication_program([(publication_entry,prefix)],publication_entry)
    need('same-selected-placeholder-cell',publication['resultCell']==normal['placeholderCell'])
    need('actual-selected-placeholder-name',image.pe.bytes_at_va(publication['nameAddress'],len(variant['placeholderName'])+1)==variant['placeholderName']+b'\0')
    need('actual-selected-placeholder-namespace',image.pe.bytes_at_va(publication['namespaceAddress'],7)==b'System\0')
    lookup=owned(image,publication['classLookup']);intern=owned(image,calls['internArguments'])
    from scripts.game_data.levelscript_two_routes_native import _window
    publication_window=_window(image,publication_entry,publication['end'],'Exact selected name/namespace/assembly request and unchanged result-cell store; enclosing startup/control unproved')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,cases=cases,
        proof=dict(classFieldSource=fields,normalizer=normal,normalizerWindows=body['windows'],stackProbe=probe_source,stackProbeWindows=probe['windows'],
            referencePredicate=reference_source,referencePredicateWindows=reference['windows'],primitiveClass=primitive,primitiveClassWindows=class_body['windows'],
            placeholderPublication=publication,placeholderPublicationWindow=publication_window,opaqueLookupWindows=lookup['windows'],opaqueInternerWindows=intern['windows']),
        runtimeConfigurationObserved=False,placeholderClassIdentityProved=False,actualEnumClassResultIdentityProved=False,
        genericInternedIdentityProved=False,concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Fresh nominal enum caller inputs and complete selected actual count1 normalizer/probe/predicate/class-kind8 programs; actual Int32Enum/System request, result cell and buffer/count interner transfers.'if enum_variant is None else'Fresh byte-backed nominal requests and distinct class-normalizer kind5 switch, underlying class-kind5 program, actual ByteEnum/System request/result-cell and buffer/count interner transfers.',
            conditional=__doc__ if enum_variant is None else BYTE_CONDITION,structuralOnly='Runtime type/class representation transfers.',
            unresolved=['coherent initialized class/cache results and opaque child/alias effects','startup name lookup result identity',
                'generic interner/cache/result identity','actual nominal provider/formatter/MethodInfo callback selection','collection/wire/parent/EOF']))))

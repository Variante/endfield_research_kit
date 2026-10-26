"""Finite cached access with RSI zero, RBP image base and inline collector.

Only initialized, compatible nonnull paths and the independently proved
disabled collector are selected. The metadata initializer, active collector,
predicate outcome and runtime invocation are not claimed by these programs.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='generatedLargeCachedSource'


def need(key,condition):
    if not condition:raise ValueError(LABEL+'.'+key)


def _prefix(g,*,image_base):
    g.take('48895c2410','48896c2418','4889742420','57','4883ec40','33f6')
    need('literal-RBP-image-base',g.relative('488d2d')==image_base)
    flag=g.relative('403835');g.take('488bd9');g.branch('0f85',True)
    return flag


def _finish(g,cache_slot):
    g.take('488b43'+bytes((cache_slot,)).hex(),'488b5c2458','488b6c2460','488b742468','4883c440','5f','c3')


def getter_program(regions,entry,*,base_slot,cache_slot,image_base,refresh=None,disabled=None):
    need('literal-distinct-current-slots',type(base_slot)is int and type(cache_slot)is int
        and 16<=base_slot<cache_slot<128 and type(image_base)is int and image_base>=0)
    need('finite-selected-path',refresh in(None,'empty','different'))
    g=BytesPath(regions,entry);flag=_prefix(g,image_base=image_base)
    b,c=bytes((base_slot,)).hex(),bytes((cache_slot,)).hex()
    g.take('483973'+c);g.branch('74',refresh=='empty',1)
    if refresh!='empty':
        g.take('488b43'+b,'483943'+c);g.branch('74',refresh is None,1)
    classes=[];predicate=None
    if refresh is not None:
        need('independently-selected-disabled-collector',type(disabled)is int and disabled>0)
        g.take('488b7b'+b,'4885ff');g.branch('75',True,1)
        for ordinal in range(2):
            site=g.at;cell=g.relative('488b15');g.take('488b0f');target=g.relative('e8')
            classes.append(dict(instructionVa=site,cellVa=cell))
            if ordinal==0:
                predicate=target;g.take('84c0');g.branch('74',False,1)
                g.take('488bf7','488973'+c)
            else:need('same-actual-compatible-predicate',target==predicate)
        need('same-exact-class-cell',classes[0]['cellVa']==classes[1]['cellVa'])
        need('same-disabled-collector-flag',g.relative('833d')+1==disabled);g.take('00');g.branch('74',True,1)
    _finish(g,cache_slot)
    return dict(selectedBytes=g.seen,getterProfile='rsi-zero-rbp-image-base-inline-collector',initializedFlag=flag,baseSlot=base_slot,cacheSlot=cache_slot,
        fullSameReferenceReturned=True,normalReturn=True,entryRspRestored=True,
        nonvolatileRegistersRestored=['rbx','rbp','rsi','rdi'],refresh=refresh,
        classUsages=classes,predicateTarget=predicate,disabledCollectorCell=disabled if refresh is not None else None,
        sameBaseReferenceCachedAndReturned=refresh is not None,
        initializedMetadataRequired=True,compatiblePredicateTrueRequired=refresh is not None,
        metadataInitializerExecutionClaimed=False,activeCollectorAdmitted=False)


def reference_setter_program(regions,entry,*,getter,field,disabled):
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    need('literal-owned-reference-setter',all(type(n)is int and n>0 for n in(getter,disabled))
        and type(field)is int and field>=16)
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488bda','33d2');g.call(getter);g.take('4885c0')
    null=g.relative('74',1)
    need('owned-nonreturning-null',g.bytes.get(null)==232 and g.bytes.get(null+5)==204)
    need('same-disabled-collector-flag',g.relative('833d')+1==disabled)
    g.take('00',_displacement('488958',field));g.branch('74',True,1)
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,storedBytes=8,fieldOffset=field,incomingValueStoredUnchanged=True,
        wholeReferenceBitsStoredUnchanged=True,normalFrameAndReturn=True,entryRspRestored=True,
        nonvolatileRbxRestored=True,disabledCollectorCell=disabled,activeCollectorAdmitted=False,
        ownedNullExit=dict(instructionVa=null,bytes=bytes(g.bytes[null+i]for i in range(6)).hex().upper()))


def prehook_program(regions,entry,*,cache_slot,image_base):
    need('literal-own-prehook-roles',type(cache_slot)is int and 16<=cache_slot<128
        and type(image_base)is int and image_base>=0)
    g=BytesPath(regions,entry)
    g.take('48895c2410','48896c2418','4889742420','57','4883ec40','33ff')
    need('prehook-literal-RBP-image-base',g.relative('488d2d')==image_base)
    flag=g.relative('40383d');g.take('488bf1');g.branch('0f85',True)
    g.take('48397e'+bytes((cache_slot,)).hex());g.branch('75',True,1)
    g.take('488b5c2458','488b6c2460','488b742468','4883c440','5f','c3')
    return dict(selectedBytes=g.seen,initializedFlag=flag,cacheSlot=cache_slot,serializedFieldWrites=0,
        entryRspRestored=True,nonvolatileRegistersRestored=['rbx','rbp','rsi','rdi'],
        compatibleNonnullOwnCacheRequired=True,metadataInitializerExecutionClaimed=False)


def factory_program(regions,entry,*,ctor,original_ctor,base_slot,cache_slot,image_base,disabled,original_initializers=None):
    from scripts.game_data.memorypack.generated_lifecycle_sources import _nonnull
    inlined=original_ctor is None
    need('literal-factory-roles',type(ctor)is bool and all(type(n)is int and n>0 for n in(image_base,disabled))
        and(inlined or type(original_ctor)is int and original_ctor>0)
        and type(base_slot)is int and type(cache_slot)is int and 16<=base_slot<cache_slot<128)
    if inlined:
        need('one-owned-inlined-enable-default',type(original_initializers)is list and len(original_initializers)==1
            and original_initializers[0].get('offset')==16 and original_initializers[0].get('bytes')==1
            and original_initializers[0].get('constantHex','').lower()=='01')
    b,c=bytes((base_slot,)).hex(),bytes((cache_slot,)).hex();g=BytesPath(regions,entry)
    if ctor:g.take('4053','55','56','57','4883ec48')
    else:g.take('48895c2410','48896c2420','56','4883ec40')
    flag=g.relative('803d')+1;g.take('00')
    need('factory-literal-RBP-image-base',g.relative('488d2d')==image_base)
    g.take('488bf1');g.branch('0f85',True);ancestor=None
    if ctor:
        site=g.at;cell=g.relative('488b0d');ancestor=dict(site=site,cell=cell)
        g.take('83b9e000000000');g.branch('75',True,1)
    site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);allocate=g.relative('e8')
    if inlined:
        g.take('4885c0');_nonnull(g);g.take('4533c0')
        if ctor:g.take('c6401001','488bd0')
        else:g.take('48897c2450','488bd0','c6401001')
        g.take('488bce');setter=g.relative('e8')
    else:
        g.take('488bd8','4885c0');_nonnull(g);g.take('33d2')
        if not ctor:g.take('48897c2450')
        g.take('488bc8');g.call(original_ctor);g.take('4533c0','488bd3','488bce');setter=g.relative('e8')
    g.take('488b5e'+b);classes=[];predicates=[]
    site=g.at;cell=g.relative('488b3d');classes.append(dict(site=site,cell=cell))
    g.take('4885db');_nonnull(g)
    for ordinal in range(2):
        g.take('488b0b','488bd7');predicates.append(g.relative('e8'));g.take('84c0');g.branch('74',False,1)
        if ordinal==0:
            g.take('48895e'+c);site=g.at;cell=g.relative('488b3d');classes.append(dict(site=site,cell=cell))
    need('same-current-class-and-compatible-predicate',predicates[0]==predicates[1]
        and all(u['cell']==allocation['cell']for u in classes))
    g.jump('e9');need('factory-same-disabled-collector',g.relative('833d')+1==disabled)
    g.take('00');g.branch('74',True,1)
    if ctor:g.take('4883c448','5f','5e','5d','5b','c3');restored=['rbx','rbp','rsi','rdi']
    else:g.take('488b7c2450','488b5c2458','488b6c2468','4883c440','5e','c3');restored=['rbx','rbp','rsi','rdi']
    return dict(selectedBytes=g.seen,factoryProfile='rsi-wrapper-rbp-image-base-inline-collector',initializedFlag=flag,constructor=ctor,allocation=allocation,allocationTarget=allocate,
        baseClassUsage=ancestor,baseReady=None,instanceSetter=setter,strictCast=None,classUsages=classes,
        inlineStrictCasts=dict(sameBaseReferenceCached=True,successfulPredicateConditional=True,
            runtimePredicateOutcomeObserved=False,predicateTarget=predicates[0],entryRspRestored=True,nonvolatilesRestored=restored),
        baseHolderOffset=base_slot,typedCacheOffset=cache_slot,originalConstructorCalled=not inlined,
        originalConstructorTarget=original_ctor,originalConstructorEffectsProved=False,normalReturnViaBarrier=False,
        disabledCollectorCell=disabled,disabledCollectorRequired=True,entryRspRestored=True,
        nonvolatileRegistersRestored=restored,metadataInitializerExecutionClaimed=False,
        **(dict(inlinedOriginalInitializers=original_initializers,sameIndependentEnableDefault=True)if inlined else{}))


def holder_program(regions,entry,*,base_slot,cache_slot,disabled):
    need('literal-dual-holder-roles',base_slot==16 and type(cache_slot)is int and 16<cache_slot<128
        and type(disabled)is int and disabled>0)
    c=bytes((cache_slot,)).hex();g=BytesPath(regions,entry)
    need('holder-first-same-disabled-flag',g.relative('8b05')==disabled)
    unused_card_root=g.relative('4c8d1d')
    g.take('488951'+c,'4c8bd2','4c8bc9','85c0');g.branch('74',True,1)
    g.take('4d895110','85c0');g.branch('74',True,1);g.take('c3')
    return dict(selectedBytes=g.seen,holderOffsets=[cache_slot,base_slot],storedBytesPerHolder=8,
        sameFullReferenceStored=True,normalReturnViaBarrier=False,disabledCollectorRequired=True,
        disabledCollectorCell=disabled,unusedCardRootAddress=unused_card_root,entryRspUnchanged=True,
        integerNonvolatilesUnchanged=True,sameZeroEaxReachesBothCollectorGuards=True,
        normalReturn=True,activeCollectorAdmitted=False,
        physicalFunctionExtentProved=False)


def holder_source(image,pins,entry,*,base_slot,cache_slot,barrier):
    """Hash only the complete selected conditional leaf path, never its padding."""
    import hashlib
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    _publication_gate(image,pins);base=image.pe.image_base;collector=_barrier(image,barrier)
    program=holder_program([(entry,image.pe.bytes_at_va(entry,256))],entry,base_slot=base_slot,
        cache_slot=cache_slot,disabled=base+collector['result']['disabledFlagRva'])
    windows=[]
    for at,encoded in program['selectedBytes']:
        raw=bytes.fromhex(encoded)
        need('same-current-selected-holder-bytes',image.pe.bytes_at_va(at,len(raw))==raw)
        windows.append(dict(startRva=at-base,endRva=at-base+len(raw),sha256=hashlib.sha256(raw).hexdigest().upper(),
            boundary='complete selected disabled-collector dual-holder leaf path; physical function extent unproved'))
    _publication_gate(image,pins)
    return dict(pointer=entry,family=dict(schema='endfield.selected-conditional-leaf-program.v1',
        selectedEntryRva=entry-base,physicalFunctionExtentProved=False),windows=windows,
        program=program,disabledCollector=collector)


def formatter_program(regions,entry,*,reader):
    need('literal-owned-reader-tail',type(reader)is int and reader>0)
    g=BytesPath(regions,entry);g.take('4055','56','4883ec48')
    flag=g.relative('803d')+1;g.take('00','498bf0','488bea');g.branch('0f85',True)
    site=g.at;cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('75',True,1)
    g.take('4533c0','488bd6','488bcd','4883c448','5e','5d')
    need('same-actual-static-reader-tail',g.relative('e9')==reader)
    return dict(selectedBytes=g.seen,initializedFlag=flag,classUsage=dict(site=site,cell=cell),readerTarget=reader,
        sameIncomingReaderAndOutput=True,zeroReaderMethodInfo=True,entryRspRestored=True,
        nonvolatileRegistersRestored=['rbp','rsi'],otherIntegerNonvolatilesUnchanged=True,
        normalReturnViaReaderTail=True,metadataInitializerExecutionClaimed=False,
        initializedMetadataAndClassRequired=True,childGrammarAdmitted=False)


def formatter_source(image,wrapper,reader,method,body):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    program=formatter_program(body['regions'],body['pointer'],reader=image.method_pointer_va(reader))
    usage=derive_typed_usage_context(image,program['classUsage']['site']-image.pe.image_base,label=LABEL+'.formatterClass')
    need('same-current-wrapper-static-class',(usage.get('tag'),usage.get('typeName'))==(1,wrapper.name))
    return dict(program=program,classUsage=usage,completeSelectedFormatterAdmitted=True,
        childGrammarAdmitted=False,programs=[program])


def compatible_refresh(image,body,*,base_slot,cache_slot,original,barrier):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    collector=_barrier(image,barrier);base=image.pe.image_base
    disabled=base+collector['result']['disabledFlagRva'];programs=[]
    for role in('empty','different'):
        program=getter_program(body['regions'],body['pointer'],base_slot=base_slot,cache_slot=cache_slot,
            image_base=base,refresh=role,disabled=disabled)
        classes=[]
        for row in program['classUsages']:
            usage=derive_typed_usage_context(image,row['instructionVa']-base,label=LABEL+'.refreshClass')
            need('same-current-named-Original-class',(usage.get('tag'),usage.get('typeName'))==(1,original))
            classes.append(usage)
        programs.append(dict(path=role,program=program,classUsages=classes))
    return dict(profile='rsi-zero-rbp-image-base-inline-collector',programs=programs,
        disabledCollector=collector,initializedCompatibleNonNullBaseRequired=True,
        emptyOrDifferentCacheAdmitted=True,predicateOutcomeObserved=False,barrierTargetRva=barrier-base)

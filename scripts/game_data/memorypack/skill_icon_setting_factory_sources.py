"""Owned BuffIconDurationSourceSetting direct construction and defaults.

Two private informational string fields are initialized at Original offsets16
and24. They are independent of the MC2 serialized duration selector and marker
ID. The wrapper constructor inlines those two exact metadata literal loads;
CreateInstance calls the named Original constructor. Both store the same typed
fresh allocation into the sole wrapper holder16 and restore the entire frame.
The actual disabled collector path preserves R9/R10 used by these source
programs. No literal text or constructor field supplies serialized framing.
Initialized literal/metadata cells, compatible zeroed allocation, disabled
collector, disjoint storage and normal noninterfering helpers are conditions;
live allocation, formatting, duration evaluation and whole owners stay open.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPE='Beyond.Gameplay.Core.BuffIconDurationSourceSetting'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_BuffIconDurationSourceSettingForMemoryPack'
FIELDS=(('m_abilityEntityTypeInfo',16),('m_timedMarkerInfo',24))


def disabled_barrier_program(regions,entry,disabled):
    g=BytesPath(regions,entry);need('icon-disabled-collector-cell',disabled,flag(g,prefix='833d'))
    g.take('4c8bc1');g.branch('74',True,1);g.take('c3')
    return dict(selectedBytes=g.seen,preservedRegisters=['r9','r10'],normalReturn=True,
        disabledCollectorRequired=True,physicalExtentProved=False)


def original_constructor_program(regions,entry,barrier):
    g=BytesPath(regions,entry);g.take('4883ec28');first=g.at;first_cell=g.relative('488b05')
    g.take('4c8bd1','48894110','4883c110');g.call(barrier)
    second=g.at;second_cell=g.relative('4c8b0d')
    g.take('498d4a18','4d894a18','4883c428');need('icon-original-same-barrier',barrier,g.relative('e9'))
    return dict(selectedBytes=g.seen,literalUsages=[dict(site=first,cell=first_cell,offset=16),dict(site=second,cell=second_cell,offset=24)],
        receiver='same incoming RCX retained R10',requiredPreservedAcrossDisabledBarrier=['r10'],
        entryRspRestored=True,allNonvolatilesRestored=True,normalReturnViaBarrier=True,
        fieldStoreBytes=8,serializedFieldWrites=False)


def wrapper_constructor_program(regions,entry,s):
    g=BytesPath(regions,entry);g.take('4053','4883ec20');ready=flag(g)
    g.take('488bd9');g.branch('74',False,1);at=g.at;cell=g.relative('488b0d');g.call(s['allocate'])
    g.take('4c8bc8','4885c0');g.branch('74',False,1)
    first=g.at;first_cell=g.relative('488b05');g.take('498d4910','49894110');g.call(s['barrier'])
    second=g.at;second_cell=g.relative('4c8b15');g.take('498d4918','4d895118');g.call(s['barrier'])
    g.take('488d4b10','4c894b10','4883c420','5b');need('icon-wrapper-same-barrier',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,initializedFlag=ready,allocation=dict(site=at,cell=cell),allocationTarget=s['allocate'],
        literalUsages=[dict(site=first,cell=first_cell,offset=16),dict(site=second,cell=second_cell,offset=24)],
        baseHolderOffset=16,typedCacheOffset=None,inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)],
        sameAllocatedOriginalStored=True,requiredPreservedAcrossDisabledBarrier=['r9','r10'],
        originalConstructorInvoked=False,entryRspRestored=True,allNonvolatilesRestored=True,normalReturnViaBarrier=True)


def _literal(image,site):
    from scripts.game_data.il2cpp.context import unresolved_usage_index,literal_record
    raw=image.pe.bytes_at_va(site['cell'],8);md=image.metadata
    table=md.sections['stringLiteral'];data=md.sections['stringLiteralData']
    index=unresolved_usage_index(raw,table.size//8,tag=5,source='iconSettingFactory.literal',offset=site['cell'])
    offset,length=literal_record(md.buf[table.offset+index*8:table.offset+(index+1)*8],data.size,
        source='iconSettingFactory.literal',offset=index*8)
    return dict(instructionRva=site['site']-image.pe.image_base,usageCellRva=site['cell']-image.pe.image_base,
        usageRawHex=raw.hex().upper(),literalIndex=index,literalPoolOffset=offset,literalBytes=length,
        literalHex=md.buf[data.offset+offset:data.offset+offset+length].hex().upper(),
        runtimeLiteralCellInitializationRequired=True)


def prove(image,ctx,wrapper,body,symbols,original_ctor):
    """Callable-only finite lifecycle hook; data can never select this proof."""
    if wrapper.wrapped_type!=TYPE or wrapper.name!=WRAPPER:return NotImplemented
    from scripts.game_data.memorypack import generated_member_sources as members,generated_lifecycle_sources as lifecycle
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    md=image.metadata;base=image.pe.image_base;td=ctx.index.types[TYPE]
    need('icon-named-owned-original-constructor',True,original_ctor is not None and original_ctor.declaring_type==td.index
        and md.string(original_ctor.name_index)=='.ctor'and original_ctor.generic_container_index<0)
    scalar.owned_method_abi(image,ctx,original_ctor.index,td.index,('void',1,False),[],'iconSettingFactory.originalCtor')
    fields=[]
    for name,offset in FIELDS:
        need('icon-exact-private-string-default-field',(TYPE,'string',offset),ctx.field(TYPE+'::'+name))
        fd,=[f for f in md.fields_for(td)if md.string(f.name_index)==name]
        scalar.ordinary(image,ctx.type_pointer(fd.type_index),14,'iconSettingFactory.string',reference=True)
        need('icon-private-nonserialized-default-field',1,ctx.field_attributes(fd.type_index))
        need('icon-default-field-not-a-serialized-member',True,all(member.name!=name for member in wrapper.members))
        fields.append(dict(fieldName=name,fieldOffset=offset,typeName='string',storedBytes=8,serializedMember=False))
    original=members._body(image,image.method_pointer_va(original_ctor))
    ctor=original_constructor_program(original['regions'],original['pointer'],symbols['barrier'])
    originals={site['offset']:dict(cell=site['cell'],literal=_literal(image,site))for site in ctor['literalUsages']}
    method,=[m for m in md.methods_for(md.types[wrapper.type_definition])if image.method_pointer_va(m)==body['pointer']
        and md.string(m.name_index)in('.ctor','CreateInstance')]
    name=md.string(method.name_index)
    if name=='.ctor':
        program=wrapper_constructor_program(body['regions'],body['pointer'],symbols)
        for site in program['literalUsages']:
            need('icon-inline-default-same-Original-literal',originals[site['offset']]['cell'],site['cell'])
            need('icon-inline-default-literal-binding',originals[site['offset']]['literal']['literalIndex'],_literal(image,site)['literalIndex'])
    else:
        program=lifecycle.called_original_factory_program(body['regions'],body['pointer'],dict(symbols,constructor=original['pointer']))
        program.update(sameAllocatedOriginalStored=True,entryRspRestored=True,allNonvolatilesRestored=True)
    barrier_windows,barrier,_=_fast_barrier(image,symbols['barrier'])
    windows=barrier_windows['codeWindows']
    registers=disabled_barrier_program([(base+w['startRva'],image.window_bytes(w))for w in windows],symbols['barrier'],symbols['disabled'])
    constructor=dict(method=[original_ctor.index,TYPE,'.ctor',original['pointer']-base],sourceFamily=original['family'],
        codeWindows=original['windows'],program=ctor,fieldBindings=fields,literalBindings=originals)
    return dict(program=program,originalConstructor=constructor,proof=dict(typeName=TYPE,wrapperName=WRAPPER,
        method=[method.index,WRAPPER,name,body['pointer']-base],completeSelectedFactoryAdmitted=True,childGrammarAdmitted=False,
        originalConstructor=constructor,barrierWindows=barrier_windows,barrierProgram=barrier,preservedRegisterProgram=registers,
        zeroedFreshAllocationRequired=True,privateDefaultsSupplyWireFraming=False,condition=__doc__))

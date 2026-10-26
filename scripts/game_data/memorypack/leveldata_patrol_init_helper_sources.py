"""Offline normal Init helper sources, separate from live Patrol selection.

The exact named virtual callbacks, initialized class preparation and stable
typed lookup storage are conditions. No controller is invoked, and no source
proof observes a selected receiver, replacement, table contents or playback.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.leveldata_patrol_config_prefix_sources import CONTROLLER,CORE

SCHEMA='endfield.story-patrol-init-helper-sources.v2'


def need(check,condition):
    if not condition:raise ValueError('storyPatrolInitHelpers.'+check)


def norm(value):return json.loads(json.dumps(value))


def virtual_set_program(regions,entry,*,prepare,callback,slot=6):
    need('exact-doPatrol-setter-slot',type(slot)is int and slot==6)
    g=BytesPath(regions,entry)
    g.take('48895c2418','4889742420','57','4883ec30','0fb7d9','410fb6f0','488b0a','488bfa');g.call(prepare)
    g.take('488d4b14','48c1e104','48030f','488b01','4c8b4108')
    excluded=[g.relative('488d0d')];g.take('483bc1');g.branch('74',False,1)
    excluded.append(g.relative('488d0d'));g.take('48896c2440','4c89742448','483bc1');g.branch('74',False,1)
    excluded.append(g.relative('488d0d'));g.take('483bc1');g.branch('0f84',False)
    need('own-bool-setter-enters-proved-direct-slot-path',callback not in excluded)
    g.take('400fb6d6','488bcf','ffd0','488b6c2440','4c8b742448','488b5c2450','488b742458','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,selector=slot,callbackByteOffset=320+slot*16,methodInfoByteOffset=328+slot*16,
        excludedInlineCallbacks=excluded,selectedCallbackRequired=callback,
        callbackArguments=dict(rcx='same incoming RDX controller',edx='same incoming R8B zero-extended',r8='same selected slot MethodInfo'),
        boolByteUnchanged=True,entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14'],
        frameBytes=56,callShadow=[0,32],runtimeSelectionObserved=False)


def virtual_bool_get_program(regions,entry,*,prepare,callback,slot=5):
    need('exact-doPatrol-getter-slot',type(slot)is int and slot==5)
    g=BytesPath(regions,entry)
    g.take('48895c2408','55','56','57','4154','4155','4156','4157','488d6c24d9','4881ec90000000',
        '4c8bf2','0fb7d9','488b0a');g.call(prepare)
    g.take('488d4b14','48c1e104','49030e','488b01','488b5108')
    excluded=[g.relative('488d0d')];g.take('483bc1');g.branch('74',False,1)
    excluded.append(g.relative('488d0d'));g.take('483bc1');g.branch('74',False,1)
    excluded.append(g.relative('488d0d'));g.take('483bc1');g.branch('0f84',False)
    need('own-bool-getter-enters-proved-direct-slot-path',callback not in excluded)
    g.take('498bce','ffd0','488b9c24d0000000','4881c490000000','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,selector=slot,callbackByteOffset=320+slot*16,methodInfoByteOffset=328+slot*16,
        excludedInlineCallbacks=excluded,selectedCallbackRequired=callback,
        callbackArguments=dict(rcx='same incoming RDX controller',rdx='same selected slot MethodInfo'),
        returnedBoolBitsUnchanged=True,entryRspRestored=True,restoredNonvolatiles=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
        frameBytes=200,callShadow=[0,32],runtimeSelectionObserved=False)


def bool_field_program(regions,entry,*,field_offset,setter):
    need('own-bool-field-offset',type(field_offset)is int and 16<=field_offset<2**31 and type(setter)is bool)
    g=BytesPath(regions,entry);offset=field_offset.to_bytes(4,'little').hex()
    g.take(('8891'if setter else'0fb681')+offset,'c3')
    return dict(selectedBytes=g.seen,fieldOffset=field_offset,storedBytes=1 if setter else 0,
        returnedBits=0 if setter else 8,sameBoolByte=True,otherMemoryWrites=0,
        entryRspAndNonvolatilesUntouched=True,normalReturn=True,physicalFunctionExtentProved=False)


def entity_lookup_program(regions,entry,*,barrier,table_lookup,replacement_present=False):
    """Nonzero key and successful table row; replacement callback is absent."""
    need('literal-replacement-mode',type(replacement_present)is bool)
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec30');root=g.relative('488b05')
    g.take('8bf9','488bda','488b4860','4885c9');g.branch('0f85',replacement_present)
    if replacement_present:
        g.take('488b81b0870000','4885c0');g.branch('0f84',True)
    g.take('488bcb','48c70200000000');g.call(barrier);g.take('85ff');g.branch('0f84',False)
    table_class=g.relative('488b05');g.take('488b88b8000000','488b8900020000','4885c9');g.branch('74',False,1)
    g.take('4533c0','8bd7');g.call(table_lookup);g.take('4885c0');g.branch('0f84',False)
    g.take('488b4040','488bcb','488903');g.call(barrier)
    g.take('b001','488b5c2440','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,replacementRootCellVa=root,tableClassCellVa=table_class,
        selectedReplacementAbsentRequired=True,nonzeroEntityKeyRequired=True,tableStaticFieldOffset=512,rowConfigFieldOffset=64,
        originalKeyInt32PassedUnchanged=True,outputReferenceInitiallyCleared=True,tableRowNonnullRequired=True,
        sameRowConfigReferenceStored=True,returnsLiteralTrue=True,entryRspRestored=True,
        restoredNonvolatiles=['rbx','rdi'],tableLookupEffectsProved=False,runtimeSelectionObserved=False)


def cached_config_program(regions,entry,*,lookup,replacement_present=False):
    """Existing own dictionary branch; no lazy construction or enumeration."""
    from scripts.game_data.memorypack.pooled_string_list_sources import flag
    need('literal-replacement-mode',type(replacement_present)is bool)
    g=BytesPath(regions,entry)
    g.take('4c89442418','89542410','48894c2408','53','56','57','4156','4157','4883ec70',
        '498bd9','4d8bf0','448bfa','488bf9');ready=flag(g);g.branch('0f85',True)
    root=g.relative('488b05');g.take('488b08','4885c9');g.branch('74',not replacement_present,1)
    if replacement_present:
        g.take('488b8150bf0000','4885c0');g.branch('74',True,1)
    g.take('0f57c0','33c0','0f11442450','4889442460','483987f8010000');g.branch('0f85',True)
    g.take('488b8ff8010000','4885c9');g.branch('74',False,1)
    context_site=g.at;context=g.relative('4c8b0d')
    g.take('4d8bc6','418bd7');g.call(lookup)
    g.take('4883c470','415f','415e','5f','5e','5b','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlagVa=ready,replacementRootCellVa=root,
        selectedReplacementAbsentRequired=True,existingConfigDictionaryRequired=True,configDictionaryFieldOffset=504,
        contextInstructionVa=context_site,contextCellVa=context,sameDictionaryKeyAndOutputPassed=True,
        lookupArguments=dict(rcx='same receiver cached dictionary',edx='same incoming Int32 key',r8='same incoming reference out',r9='actual closed TryGetValue context'),
        lookupBoolReturnUnchanged=True,entryRspRestored=True,restoredNonvolatiles=['rbx','rsi','rdi','r14','r15'],
        lazyDictionaryConstructionProved=False,lookupEffectsProved=False,runtimeSelectionObserved=False)


def _packet(image,at,*,leaf=False):
    import hashlib
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry
    base=image.pe.image_base
    if not leaf:
        b=owned(image,at);return dict(entryRva=at-base,windows=b['windows'],regions=[[a-base,r.hex().upper()]for a,r in b['regions']],boundary='complete-native-owned-family')
    rows=decode_closed_leaf_entry(image.mapper,image.pe.bytes_at_va(at,64),at)['rows'];raw=b''.join(bytes.fromhex(r['bytes'])for r in rows)
    need('actual-selected-leaf-bytes',image.pe.bytes_at_va(at,len(raw))==raw)
    return dict(entryRva=at-base,windows=[dict(startRva=at-base,endRva=at-base+len(raw),sha256=hashlib.sha256(raw).hexdigest().upper())],
        regions=[[at-base,raw.hex().upper()]],boundary='declared-closed-leaf-span-no-physical-extent')


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import _vtable,derive_typed_usage_context
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack import leveldata_patrol_initializer_sources as initial,pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack.leveldata_patrol_helper_sources import lookup_program,getter_program
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    initializer=initial.derive(image,pins);owner=ctx.index.types[CONTROLLER]
    methods={md.string(m.name_index):m for m in md.methods_for(owner)}
    selected={name:_packet(image,base+initializer['proof']['actualTargets'][name])for name in
        ('set-doPatrol-slot6','get-doPatrol-slot5','lookup-entity-config','lookup-patrol-config','get-patrolData-slot7')}
    def raw(packet):return [(base+a,bytes.fromhex(h))for a,h in packet['regions']]
    own={name:_packet(image,image.method_pointer_va(methods[name]),leaf=True)for name in('get_doPatrol','set_doPatrol','get_patrolData')}
    fields={};method_rows=[]
    for name,slot,result,args in(('get_doPatrol',5,('bool',2,False),[]),('set_doPatrol',6,('void',1,False),[('bool',2,False)]),
        ('get_patrolData',7,(CORE,18,False),[])):
        method=methods[name];scalar.owned_method_abi(image,ctx,method.index,owner.index,result,args,'PatrolInitHelpers.'+name)
        need('own-exact-virtual-slot-'+name,method.slot==slot);_vtable(image,owner.index,slot,method.index,'PatrolInitHelpers.'+name)
        method_rows.append(dict(method=[method.index,CONTROLLER,name,image.method_pointer_va(method)-base],slot=slot))
    # Read the literal offset, then resolve the unique actual declaration and
    # ordinary Boolean ABI. The accessor name supplies the semantic join.
    offset=int.from_bytes(bytes.fromhex(own['get_doPatrol']['regions'][0][1])[3:7],'little')
    candidates=[]
    for f in md.fields_for(owner):
        if ctx.field_attributes(f.type_index)&16:continue
        field=list(ctx.field(CONTROLLER+'::'+md.string(f.name_index)))
        if field[2]==offset:candidates.append((f,field,md.string(f.name_index)))
    need('unique-owned-doPatrol-storage',len(candidates)==1);f,field,name=candidates[0]
    scalar.ordinary(image,ctx.type_pointer(f.type_index),2,'PatrolInitHelpers.boolField');need('named-bool-storage',field[:2]==[CONTROLLER,'bool'])
    fields['doPatrol']=dict(name=name,field=field)
    core=list(ctx.field(CONTROLLER+'::<patrolData>k__BackingField'));need('own-Core-reference-field',core[:2]==[CONTROLLER,CORE]);fields['patrolData']=dict(name='<patrolData>k__BackingField',field=core)
    s={name:base+p['entryRva']for name,p in own.items()};helpers={}
    for name,packet in selected.items():
        rows=pointer.owned(image,base+packet['entryRva'])['rows']
        calls=[control_transfer(r)['target']for r in rows if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==0xe8]
        helpers[name]=dict(packet=packet,calls=calls)
    prepare=helpers['get-doPatrol-slot5']['calls'][0]
    need('same-three-preparation-targets',helpers['set-doPatrol-slot6']['calls'][0]==helpers['get-patrolData-slot7']['calls'][0]==prepare)
    setter=virtual_set_program(raw(selected['set-doPatrol-slot6']),base+selected['set-doPatrol-slot6']['entryRva'],prepare=prepare,callback=s['set_doPatrol'])
    getter=virtual_bool_get_program(raw(selected['get-doPatrol-slot5']),base+selected['get-doPatrol-slot5']['entryRva'],prepare=prepare,callback=s['get_doPatrol'])
    core_dispatch=lookup_program(raw(selected['get-patrolData-slot7']),base+selected['get-patrolData-slot7']['entryRva'],prepare=prepare,selector=7)
    bool_programs={name:bool_field_program(raw(own[name]),s[name],field_offset=offset,setter=name.startswith('set'))for name in('get_doPatrol','set_doPatrol')}
    core_program=getter_program(raw(own['get_patrolData']),s['get_patrolData'],field_offset=core[2])
    entity_calls=helpers['lookup-entity-config']['calls'];need('entity-clear-and-success-use-same-barrier',entity_calls[0]==entity_calls[2])
    entity_programs=[entity_lookup_program(raw(selected['lookup-entity-config']),base+selected['lookup-entity-config']['entryRva'],barrier=entity_calls[0],table_lookup=entity_calls[1],replacement_present=r)for r in(False,True)]
    config_rows=pointer.owned(image,base+selected['lookup-patrol-config']['entryRva'])['rows']
    usage_row=[r for r in config_rows if bytes.fromhex(r['bytes'])[:3]==bytes.fromhex('4c8b0d')][-1]
    usage=derive_typed_usage_context(image,int(usage_row['va'],16)-base,label='PatrolInitHelpers.configTryGet')
    following=config_rows[config_rows.index(usage_row)+1:];lookup=next(control_transfer(r)['target']for r in following if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==0xe8)
    need('own-closed-config-Int32-reference-TryGet',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
        (6,'System.Collections.Generic.Dictionary`2','TryGetValue',['int','Beyond.Gameplay.AI.Config.NpcPatrolData'],[]))
    config_programs=[cached_config_program(raw(selected['lookup-patrol-config']),base+selected['lookup-patrol-config']['entryRva'],lookup=lookup,replacement_present=r)for r in(False,True)]
    need('actual-same-cached-TryGet-MethodInfo',all(p['contextCellVa']==base+usage['usageCellRva']and p['contextInstructionVa']==base+usage['instructionRva']for p in config_programs))
    from scripts.game_data.memorypack import leveldata_patrol_init_lookup_sources as lookup_source
    lookup_closure=lookup_source.derive(image,pins,prepare=prepare,entity_table=entity_calls[1],try_get=lookup,config_usage=usage)
    result=norm(dict(schema=SCHEMA,status='validated-conditional-init-helper-source-slices',nativeInputs=pins,
        proof=dict(initializerSource=initializer,imageBase=base,methods=method_rows,fields=fields,ownMethods=own,helpers=selected,
            preparationTargetRva=prepare-base,programs=dict(boolFields=bool_programs,boolSetterDispatch=setter,boolGetterDispatch=getter,CoreGetter=core_program,CoreGetterDispatch=core_dispatch,
                entityHit=entity_programs,cachedConfig=config_programs),lookupSymbols=dict(barrierRva=entity_calls[0]-base,entityTableLookupRva=entity_calls[1]-base,configTryGetRva=lookup-base),configTryGetUsage=usage,lookupClosure=lookup_closure),
        eligibilitySetterAndGetterByteEffectsProved=True,selectedCoreGetterFieldReadProved=True,
        selectedEntityHitCopyAndTrueReturnProved=True,cachedConfigLookupArgumentAndReturnSourceProved=True,
        warmPreparationAndCachedLookupEffectsProved=True,finiteDictionaryCollisionChainLimit=4096,
        wholeInitializerProved=False,lookupTableSemanticsProved=False,runtimeInvocationObserved=False,playbackProved=False,
        residualNativeSourceFrontiers=[
            dict(role='lookup-context-and-comparer',required='Actual coherent closed dictionary/comparer contexts must supply the exact selected current Int32 equality callback; compatible typed storage and stable valid acyclic hash chains within the finite bound remain conditions. No live table or comparer state is observed.'),
            dict(role='lazy-config-index-and-failure-alternatives',required='Config dictionary construction/enumeration, lookup miss logging, replacement and exceptional paths remain separate source obligations.')],
        conditions=['Selected same receiver slots equal the independently proved own callbacks and have coherent MethodInfo pairs; no intervening writes to the receiver fields.',
            'Ready initialized metadata, absent selected replacements, stable compatible nonnull/disjoint storage and normal noninterfering helpers; entity hit selects a nonzero key and nonnull row.',
            'Existing cached Config dictionary and actual selected lookup state are conditions, not runtime observations.']))
    validate(result,pins);_publication_gate(image,pins);return result


def validate(component,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.leveldata_patrol_helper_sources import lookup_program,getter_program
    need('own-source-envelope',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
        and component.get('status')=='validated-conditional-init-helper-source-slices'
        and component.get('wholeInitializerProved')is False and component.get('lookupTableSemanticsProved')is False
        and component.get('runtimeInvocationObserved')is False and component.get('playbackProved')is False
        and all(component.get(k)is True for k in('eligibilitySetterAndGetterByteEffectsProved','selectedCoreGetterFieldReadProved',
            'selectedEntityHitCopyAndTrueReturnProved','cachedConfigLookupArgumentAndReturnSourceProved')))
    p=component['proof'];base=p['imageBase'];need('selected-image-base',type(base)is int and base>=1<<32)
    def raw(packet,label):return regions(packet['windows'],packet['regions'],base,label)
    own=p['ownMethods'];helpers=p['helpers'];programs=p['programs'];prepare=base+p['preparationTargetRva']
    for name in('get_doPatrol','set_doPatrol'):
        need('own-bool-byte-leaf-'+name,norm(bool_field_program(raw(own[name],name),base+own[name]['entryRva'],field_offset=p['fields']['doPatrol']['field'][2],setter=name.startswith('set')))==programs['boolFields'][name])
    need('full-own-setter-dispatch',norm(virtual_set_program(raw(helpers['set-doPatrol-slot6'],'boolSetter'),base+helpers['set-doPatrol-slot6']['entryRva'],prepare=prepare,callback=base+own['set_doPatrol']['entryRva']))==programs['boolSetterDispatch'])
    need('full-own-bool-getter-dispatch',norm(virtual_bool_get_program(raw(helpers['get-doPatrol-slot5'],'boolGetter'),base+helpers['get-doPatrol-slot5']['entryRva'],prepare=prepare,callback=base+own['get_doPatrol']['entryRva']))==programs['boolGetterDispatch'])
    need('full-own-Core-getter',norm(getter_program(raw(own['get_patrolData'],'CoreGetter'),base+own['get_patrolData']['entryRva'],field_offset=p['fields']['patrolData']['field'][2]))==programs['CoreGetter'])
    need('full-own-Core-getter-dispatch',norm(lookup_program(raw(helpers['get-patrolData-slot7'],'CoreDispatch'),base+helpers['get-patrolData-slot7']['entryRva'],prepare=prepare,selector=7))==programs['CoreGetterDispatch'])
    s={k:base+v for k,v in p['lookupSymbols'].items()}
    need('entity-both-absent-replacement-hit-paths',norm([entity_lookup_program(raw(helpers['lookup-entity-config'],'entityLookup'),base+helpers['lookup-entity-config']['entryRva'],barrier=s['barrierRva'],table_lookup=s['entityTableLookupRva'],replacement_present=r)for r in(False,True)])==programs['entityHit'])
    need('config-both-cached-absent-replacement-paths',norm([cached_config_program(raw(helpers['lookup-patrol-config'],'configLookup'),base+helpers['lookup-patrol-config']['entryRva'],lookup=s['configTryGetRva'],replacement_present=r)for r in(False,True)])==programs['cachedConfig'])
    initial=p['initializerSource'];need('same-fresh-initializer-and-actual-helper-targets',initial.get('nativeInputs')==pins
        and initial.get('schema')=='endfield.story-patrol-initializer-control-source.v1'
        and initial.get('selectedCompleteCallerControlProved')is True
        and all(initial['proof']['actualTargets'][k]==v['entryRva']for k,v in helpers.items()))
    need('same-fresh-own-virtual-methods-and-installation-field',p['methods']==[
        {k:r[k]for k in('method','slot')}for name in('get_doPatrol','set_doPatrol','get_patrolData')
        for r in initial['proof']['ownSelectedVirtualMethods']if r['method'][2]==name]
        and all(own[r['method'][2]]['entryRva']==r['method'][3]for r in p['methods'])
        and p['fields']['doPatrol']['field'][:2]==[CONTROLLER,'bool']
        and p['fields']['patrolData']['field']==initial['proof']['installation']['proof']['nominalField'])
    usage=p['configTryGetUsage']
    need('same-own-closed-Config-dictionary-context',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
        (6,'System.Collections.Generic.Dictionary`2','TryGetValue',['int','Beyond.Gameplay.AI.Config.NpcPatrolData'],[])
        and all(v['contextInstructionVa']==base+usage['instructionRva']and v['contextCellVa']==base+usage['usageCellRva']for v in programs['cachedConfig']))
    from scripts.game_data.memorypack import leveldata_patrol_init_lookup_sources as lookup_source
    lookup_source.validate(p['lookupClosure'],pins,base=base,config_usage=usage)
    need('same-normal-helper-and-lookup-target-seams',p['lookupClosure']['symbolRvas']['preparationRva']==p['preparationTargetRva']
        and p['lookupClosure']['symbolRvas']['tryGetRva']==p['lookupSymbols']['configTryGetRva']
        and p['lookupClosure']['symbolRvas']['entityTableRva']==p['lookupSymbols']['entityTableLookupRva']
        and component.get('warmPreparationAndCachedLookupEffectsProved')is True
        and type(component.get('finiteDictionaryCollisionChainLimit'))is int and component['finiteDictionaryCollisionChainLimit']==4096)
    return dict(eligibilitySetterAndGetterByteEffectsProved=True,selectedCoreGetterFieldReadProved=True,
        selectedEntityHitCopyAndTrueReturnProved=True,cachedConfigLookupArgumentAndReturnSourceProved=True,
        wholeInitializerProved=False,runtimeInvocationObserved=False,playbackProved=False)

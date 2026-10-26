"""Current FunctionAreaSpecificData's exact 18-case wrapper transport.

This family independently joins its current table, actual reference-result
ReadPackable clone, closed concrete wrapper contexts and base adapter/holder/
inherited conversion. Positive wrapper output initially null, coherent ready
contexts and exact compatible callbacks remain conditions. No concrete Original
adapter is invented for a path that reads the concrete generated wrapper.
Concrete reader/factory/field/wire grammars and the actual enclosing list remain
separate. Existing-output byref-reader paths and runtime selection are closed.
"""
import json
import struct

TYPE='Beyond.Gameplay.LevelFunctionAreaData+FunctionAreaSpecificData'
CAP='story-function-specific'
LABEL='storyFunctionSpecific'
CHILD_NAMES=('AmbienceCameraData','BlightMiasmaAreaData','BlockAIBarkData','CameraAddControlStateData',
    'CameraLookAtData','CameraVolumeData','CarryTagZoneData','DitherFactoryZoneData','ForbidGeneralAbilityZoneData',
    'HideEntityByTypeParams','HideNpcInRangeParams','RadioTriggerZoneData','RepatriateZoneData','RopeCameraData',
    'SceneToastUIData','StopTeammateFollowZoneData','StorySafeZone','VisitLocStatData')
CHILDREN={tag:'Beyond.Gameplay.LevelFunctionAreaData+'+name for tag,name in enumerate(CHILD_NAMES)}


def derive_transport(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.formatter_composition import _vtable,derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.levelscript_family_regenerate import Build
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar,reference_adapter_sources
    from scripts.game_data.memorypack.current_reference_union_sources import table_program,_header_target,_lineage
    from scripts.game_data.memorypack.module_structure_models import enclosing_header
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _wrapper_holder
    from scripts.game_data.memorypack.union_dispatch import read_union_switch
    need=lambda k,e,a:scalar.need(LABEL,k,e,a)
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    wrappers=image.memorypack_wrappers;by_name={w.name:w for w in wrappers.values()}
    wrapper,=[w for w in wrappers.values()if w.wrapped_type==TYPE]
    formatter_name=wrapper.name+'+'+wrapper.name.rsplit('.',1)[-1]+'Formatter'
    formatter,=image.named_type_definitions[formatter_name]
    fm,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize'and not m.flags&16 and m.slot==5]
    need('actual-slot5-void-two-byrefs',('void',2),(ctx.type_name(fm.return_type),fm.parameter_count))
    _vtable(image,formatter.index,5,fm.index,LABEL+'.slot5');scalar.ordinary(image,ctx.type_pointer(fm.return_type),1,LABEL+'.void')
    for parameter,name,kind in zip(md.parameters_for(fm),('MemoryPack.MemoryPackReader',wrapper.name),(17,18),strict=True):
        raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
        need('owned-slot5-byref',(name,bytes((kind,32))),(ctx.type_name(parameter.type_index),raw[10:12]))
    entry=image.method_pointer_va(fm);body=pointer.owned(image,entry)
    switch=read_union_switch(image,wrapper.name,wrappers=wrappers)
    need('actual-slot5-and-switch',entry,int(switch['dispatcherVa'],16))
    need('exact-nominal-family',list(range(18)),[r['tag']for r in switch['entries']])
    need('exact-tag-to-original',list(CHILDREN.values()),[by_name[r['wrapperName']].wrapped_type for r in switch['entries']])
    table=int(switch['tableVa'],16);header=_header_target(body,'table-rdi');hs=pointer.owned(image,header)
    headers={m:enclosing_header(hs['regions'],header,scalar.reader_offsets(image,LABEL),marker=m)for m in('short','false')}
    # Select only direct reference-result calls whose full RAX is stored in
    # this same output. Existing-output byref calls are deliberately excluded.
    actual_targets={control_transfer(r)['target']for i,r in enumerate(body['rows'])if 0<i<len(body['rows'])-1
        and bytes.fromhex(r['bytes'])[:1]==b'\xe8'and body['rows'][i-1]['text']=='mov rcx, rbx'
        and body['rows'][i+1]['text']in('mov [rsi], rax','mov rcx, rsi')}
    need('one-actual-reference-result-source',1,len(actual_targets));packable,=actual_targets
    path=CONTRACTS_DIR/'memorypack_reader_clones_native.json';raw_clone=path.read_bytes();clone_fact=json.loads(raw_clone)
    need('selected-clone-build',pins,clone_fact['nativeInputs'])
    clone,=[c for c in clone_fact['clones']if c['claim']=='MemoryPack.MemoryPackReader.ReadPackable'
        and c.get('resultAbi')=='reference'and base+c['targetRva']==packable]
    Build(image,pins).prove_reader_clone_target(packable,'MemoryPack.MemoryPackReader.ReadPackable',result_abi='reference')
    collector_path=CONTRACTS_DIR/'model_view_state_controller_native.json';raw_collector=collector_path.read_bytes();model=json.loads(raw_collector)
    need('selected-collector-build',pins,model['nativeInputs']);barrier=base+model['collector']['entryRva']
    symbols=dict(imageBase=base,header=header,packable=packable,barrier=barrier);programs=[]
    for selected in switch['entries']:
        tag=selected['tag'];child=by_name[selected['wrapperName']];slot=table+4*tag;word=image.pe.u32_at_va(slot)
        need('unsigned-table-target:'+str(tag),base+word,int(selected['targetVa'],16))
        need('direct-owned-case-target',selected['targetVa'],selected['bodyVa'])
        program=table_program(body['regions'],entry,symbols,profile='table-rdi',tag=tag,count=18,
            hot=12,table=table,selected=int(selected['bodyVa'],16))
        usage=derive_typed_usage_context(image,program['childUsage']['instruction']-base,label=LABEL+'.closedWrapper')
        typed=bind_typed_read(image,usage,method_name='ReadPackable',argument=child.name,kind=18,reference=True)
        need('same-reviewed-actual-reference-source-definition',clone['equivalentMethod'][0],typed['methodDefinition'])
        programs.append(dict(tag=tag,wrapperName=child.name,wrappedType=child.wrapped_type,source=program,
            typedRequest=usage,typedArgument=typed,tableEntry=dict(rva=slot-base,rawHex=word.to_bytes(4,'little').hex().upper(),targetRva=word),
            originalLineage=_lineage(ctx,md,child.wrapped_type,TYPE),wrapperLineage=_lineage(ctx,md,child.name,wrapper.name),
            concreteOriginalAdapterUsed=False,concreteChildGrammarAdmitted=False))
    null=table_program(body['regions'],entry,symbols,profile='table-rdi',tag=0,count=18,
        hot=12,table=table,selected=int(switch['entries'][0]['bodyVa'],16),ff=True)
    pair=derive_pair(image,TYPE,wrapper.name)
    def forwarder(selected_image,selected_pair,selected_wrapper):
        face,=selected_pair['composition']['interfaces']
        need('own-union-slot5',(wrapper.name,fm.index),(selected_wrapper.name,face['formatterDeserializeMethodIndex']))
        return dict(ownedWindows=body['windows'],programs=programs,canonicalFF=null,readerTargetMode='independently-proved-inline')
    adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=forwarder)
    getter=pointer.methods(image,wrapper)['GetValue'];getter_entry=image.method_pointer_va(getter)
    getter_proof=pointer.leaf(image,getter_entry,['488B4110','C3']);holder=_wrapper_holder(ctx,image,wrapper)
    need('base-holder',(TYPE,16),(holder['declaredType'],holder['offset']))
    need('abstract-base-wrapper',128,md.types[wrapper.type_definition].flags&128)
    face,=pair['composition']['interfaces'];section=md.sections['interfaceOffsets'];joins=[]
    conversion_entry=base+adapter['canonicalRoutes']['symbolRvas']['conversion'];conversion=pointer.owned(image,conversion_entry)
    for route in programs:
        child=by_name[route['wrapperName']];td=md.types[child.type_definition];child_holder=_wrapper_holder(ctx,image,child)
        need('inherited-base-holder',(TYPE,16),(child_holder['declaredType'],child_holder['offset']))
        start=section.offset+td.interface_offsets_start*8
        interfaces=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8]))
        found=[(ordinal,offset)for ordinal,(index,offset)in enumerate(interfaces)if index==face['interfaceTypeIndex']]
        need('one-inherited-base-interface',1,len(found));ordinal,offset=found[0]
        _vtable(image,child.type_definition,offset,getter.index,LABEL+'.baseGetter')
        transfer=reference_adapter_sources.conversion(conversion['regions'],conversion_entry,
            base+adapter['canonicalRoutes']['conversionPrepareRva'],getter_entry,ordinal=ordinal)
        joins.append(dict(wrapperName=child.name,interfaceOrdinal=ordinal,interfaceOffset=offset,
            interfaceTypeIndex=face['interfaceTypeIndex'],baseGetValueMethod=getter.index,holder=child_holder,conversion=transfer))
    _publication_gate(image,pins)
    need('reviewed-clone-declaration-bookend',raw_clone,path.read_bytes())
    need('reviewed-collector-declaration-bookend',raw_collector,collector_path.read_bytes())
    return json.loads(json.dumps(dict(schema='endfield.story-function-specific-transport.v1',status='validated-current-wrapper-transport',
        nativeInputs=pins,typeName=TYPE,wrapperName=wrapper.name,slot5Method=[fm.index,formatter_name,'Deserialize',entry-base],
        switch=switch,ownedWindows=body['windows'],programs=programs,canonicalFF=null,headerWindows=hs['windows'],headerPrograms=headers,
        reviewedReferenceReader=clone,barrier=_barrier(image,barrier),pair=pair,adapter=adapter,
        baseHolder=holder,baseGetValue=getter_proof,inheritedConversions=joins,
        concreteOriginalAdapterRequired=False,concreteOriginalAdapterUsed=False,
        concreteChildGrammarAdmitted=False,wholeUnionAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own current 18-case short-tag/FF source, actual closed concrete wrapper requests, reviewed actual reference-result clone, complete output/store/return programs and nominal base adapter/inherited conversion.',
            conditional=__doc__,unresolved=['concrete wrapper readers/factories and child grammars','actual enclosing list/source',
                'existing-output byref reader','reserved/extended tags','runtime callback/provider selection','physical EOF/whole owner']))))

"""Current ConditionRuntime transport under independently selected nominal joins.

The shared warmed Finder byte program also describes this actual dispatcher.
Its algorithm supplies no Selector identity or child grammar: this owner binds
the ConditionRuntime table, each exact cast and closed typed reader, base pair,
holder, inherited conversion and complete selected return on the same image.
Positive wrapper output initially null and matching live callbacks remain
explicit conditions. Concrete leaf grammars and parent calls compose later.
"""
import copy
import json
import struct

TYPE='Beyond.Gameplay.ConditionRuntimeBase'
CAP='story-condition-runtime'
TAGS=(0,12,13,18)
CHILDREN={0:'Beyond.Gameplay.CombinedConditionRuntime',12:'Beyond.Gameplay.SimpleConditionCheckMissionNotPaused',13:'Beyond.Gameplay.SimpleConditionCheckMissionState',
    18:'Beyond.Gameplay.SimpleConditionCheckQuestState'}
LABEL='storyConditionRuntime'


def _one_call(image,body,pattern,label):
    found=[]
    for at,raw in body['regions']:
        pos=raw.find(pattern)
        while pos>=0:
            site=at+pos+len(pattern)-1
            encoded=image.pe.bytes_at_va(site,5)
            if encoded[:1]!=b'\xe8':raise ValueError(LABEL+'.'+label+':direct-E8')
            found.append(site+5+int.from_bytes(encoded[1:],'little',signed=True))
            pos=raw.find(pattern,pos+1)
    if len(found)!=1:raise ValueError(LABEL+'.'+label+':one-actual-call:'+str(len(found)))
    return found[0]


def derive_transport(image,pins):
    """Fresh bounded nominal union source; no concrete or enclosing admission."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.formatter_composition import _vtable,derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack import reference_adapter_sources,modelview_packable_sources
    from scripts.game_data.memorypack.current_reference_union_sources import _lineage
    from scripts.game_data.memorypack.module_structure_models import enclosing_header
    from scripts.game_data.memorypack.pooled_string_list_sources import compatible_list_cast
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_action_union_sources import original_lineage
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_selector_union_sources import finder_program,closed_packable_thunk_program
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _wrapper_holder
    from scripts.game_data.memorypack.union_dispatch import read_union_switch
    need=lambda k,e,a:scalar.need(LABEL,k,e,a)
    _publication_gate(image,pins)
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    wrappers=image.memorypack_wrappers;by_name={w.name:w for w in wrappers.values()}
    wrapper,=[w for w in wrappers.values()if w.wrapped_type==TYPE]
    switch=read_union_switch(image,wrapper.name,wrappers=wrappers)
    need('complete-nominal-table',list(range(50)),[r['tag']for r in switch['entries']])
    entry=int(switch['dispatcherVa'],16);table=int(switch['tableVa'],16);body=pointer.owned(image,entry)
    formatter_name=wrapper.name+'+'+wrapper.name.rsplit('.',1)[-1]+'Formatter'
    formatter,=image.named_type_definitions[formatter_name]
    method,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize'and not m.flags&16 and m.slot==5]
    need('actual-owned-slot5',entry,image.method_pointer_va(method));_vtable(image,formatter.index,5,method.index,LABEL)
    need('actual-instance-void-byrefs',('void',2),(ctx.type_name(method.return_type),method.parameter_count))
    scalar.ordinary(image,ctx.type_pointer(method.return_type),1,LABEL+'.void')
    for p,name,kind in zip(md.parameters_for(method),('MemoryPack.MemoryPackReader',wrapper.name),(17,18),strict=True):
        raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)
        need('actual-nominal-byref',(name,bytes((kind,32))),(ctx.type_name(p.type_index),raw[10:12]))
    header=_one_call(image,body,bytes.fromhex('488d55386644896538488bcfe8'),'header')
    barrier=_one_call(image,body,bytes.fromhex('4c8923488bcbe8'),'barrier')
    header_source=pointer.owned(image,header);offsets=scalar.reader_offsets(image,LABEL)
    headers={marker:enclosing_header(header_source['regions'],header,offsets,marker=marker)for marker in('short','false')}
    first=int(switch['entries'][TAGS[0]]['bodyVa'],16)
    raw=image.pe.bytes_at_va(first+10,5);need('actual-cast-E8',b'\xe8',raw[:1])
    cast=first+15+int.from_bytes(raw[1:],'little',signed=True)
    cast_source=pointer.owned(image,cast)
    cast_program=compatible_list_cast(cast_source['regions'],cast,0,null=True)
    core=json.loads((CONTRACTS_DIR/'npc_runtime_native.json').read_bytes())
    generic=json.loads((CONTRACTS_DIR/'leveldata_npc_patrol_native.json').read_bytes())
    need('current-reference-packable-build',pins,core['nativeInputs']);need('current-reference-routes-build',pins,generic['nativeInputs'])
    routes=copy.deepcopy(generic['declarations']['adapters']['referenceRoutes']);routes['wrappers']=[]
    reference=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)
    packable=base+core['readPackable']['entryRva'];symbols=dict(imageBase=base,header=header,packable=packable,cast=cast,barrier=barrier)
    programs=[]
    for tag in TAGS:
        selected=switch['entries'][tag];child=by_name[selected['wrapperName']]
        need('exact-selected-nominal-leaf:'+str(tag),CHILDREN[tag],child.wrapped_type)
        need('direct-indexed-table-case',selected['targetVa'],selected['bodyVa'])
        at=int(selected['bodyVa'],16);thunk=None;selected_symbols=dict(symbols)
        if image.pe.bytes_at_va(at+23,3)!=bytes.fromhex('488b15'):
            raw=image.pe.bytes_at_va(at+23,5)
            need('actual-closed-reader-E8',b'\xe8',raw[:1]);actual=at+28+int.from_bytes(raw[1:],'little',signed=True)
            thunk=closed_packable_thunk_program(image.pe.bytes_at_va(actual,12),actual,packable)
            selected_symbols['closedPackable']=actual
        program=finder_program(body['regions'],entry,selected_symbols,tag=tag,count=50,table=table,selected=at)
        context=program['childUsage']['instruction']if program['childUsage']is not None else thunk['contextInstruction']
        usage=derive_typed_usage_context(image,context-base,label=LABEL+'.child')
        typed=bind_typed_read(image,usage,method_name='ReadPackable',argument=child.name,kind=18,reference=True)
        need('owned-packable-definition',reference['packableContext']['packableDefinition'],typed['methodDefinition'])
        cast_usage=derive_typed_usage_context(image,program['castUsage']['instruction']-base,label=LABEL+'.cast')
        need('actual-selected-cast',(1,child.name),(cast_usage['tag'],cast_usage['typeName']))
        word=image.pe.u32_at_va(table+4*tag);need('actual-unsigned-table-word',at,base+word)
        programs.append(dict(tag=tag,wrapperName=child.name,wrappedType=child.wrapped_type,source=program,
            typedRequest=usage,typedArgument=typed,closedPackableThunk=thunk,nullableCast=cast_usage,
            originalLineage=original_lineage(image,ctx,child,TYPE),wrapperLineage=_lineage(ctx,md,child.name,wrapper.name),
            tableEntry=dict(rva=table+4*tag-base,rawHex=word.to_bytes(4,'little').hex().upper(),unsignedTargetRva=word),
            concreteChildGrammarAdmitted=False))
    null=finder_program(body['regions'],entry,symbols,tag=TAGS[0],count=50,table=table,selected=first,ff=True)
    pair=derive_pair(image,TYPE,wrapper.name)
    def forwarder(selected_image,selected_pair,selected_wrapper):
        face,=selected_pair['composition']['interfaces']
        need('exact-union-pair-slot5',(wrapper.name,method.index),(selected_wrapper.name,face['formatterDeserializeMethodIndex']))
        return dict(ownedWindows=body['windows'],programs=programs,canonicalFF=null)
    adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=forwarder)
    getter=pointer.methods(image,wrapper)['GetValue'];getter_entry=image.method_pointer_va(getter)
    getter_proof=pointer.leaf(image,getter_entry,['488B4110','C3']);holder=_wrapper_holder(ctx,image,wrapper)
    need('nominal-base-holder',(TYPE,16),(holder['declaredType'],holder['offset']))
    need('abstract-union-wrapper',128,md.types[wrapper.type_definition].flags&128)
    face,=pair['composition']['interfaces'];section=md.sections['interfaceOffsets'];joins=[]
    conversion_entry=base+adapter['canonicalRoutes']['symbolRvas']['conversion'];conversion=pointer.owned(image,conversion_entry)
    for program in programs:
        child=by_name[program['wrapperName']];child_holder=_wrapper_holder(ctx,image,child)
        need('exact-inherited-base-holder',(TYPE,16),(child_holder['declaredType'],child_holder['offset']))
        td=md.types[child.type_definition];start=section.offset+td.interface_offsets_start*8
        faces=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8]))
        selected=[(ordinal,offset)for ordinal,(index,offset)in enumerate(faces)if index==face['interfaceTypeIndex']]
        need('one-owned-base-interface:'+child.name,1,len(selected));ordinal,offset=selected[0]
        _vtable(image,child.type_definition,offset,getter.index,LABEL+'.baseGetter')
        converted=reference_adapter_sources.conversion(conversion['regions'],conversion_entry,
            base+adapter['canonicalRoutes']['conversionPrepareRva'],getter_entry,ordinal=ordinal)
        joins.append(dict(wrapperName=child.name,interfaceOrdinal=ordinal,interfaceOffset=offset,
            interfaceTypeIndex=face['interfaceTypeIndex'],baseGetValueMethod=getter.index,holder=child_holder,conversion=converted))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.story-condition-runtime-transport.v1',nativeInputs=pins,
        status='validated-bounded-current-condition-transport',typeName=TYPE,wrapperName=wrapper.name,
        slot5Method=[method.index,formatter_name,'Deserialize',entry-base],switch=switch,ownedWindows=body['windows'],
        programs=programs,canonicalFF=null,headerWindows=header_source['windows'],headerPrograms=headers,
        referencePackable=reference,nullableCast=dict(windows=cast_source['windows'],program=cast_program),
        barrier=_barrier(image,barrier),pair=pair,adapter=adapter,baseHolder=holder,baseGetValue=getter_proof,
        inheritedConversions=joins,concreteChildGrammarAdmitted=False,wholeUnionAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Selected nominal current ConditionRuntime table and bounded warm null-output callers, exact closed child contexts, canonical adapter and inherited Original transfer.',
            conditional=__doc__,unresolved=['concrete leaf grammars','other condition tags','actual parent source joins',
                'live callback/provider selection','existing-output alternative','refill/cold/malformed paths','runtime condition evaluation']))))

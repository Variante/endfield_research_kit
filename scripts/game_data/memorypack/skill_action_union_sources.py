"""Current AbilityActionData caller and base-reference transport, without children.

The selected formatter's large DWORD jump table is distinct from the small
reference-union profiles. Exact warmed programs own canonical short/extended
headers, each concrete nullable cast, closed ReadPackable MethodInfo thunk,
complete reference store/barrier and restored frame. Positive output starts
null. Each table word and both actual typed requests are independently joined.

The ordinary base adapter/GetValue and inherited concrete-to-base conversions
are source transport only. Concrete generated caches/factories, their wire
grammars and enclosing action lists/Skill owners require separate components.
Runtime callback/provider/cache/inflation selection, uninitialized/refill/error
paths and existing output alternatives remain conditional or unresolved.
"""
import copy
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='skillActionUnionSources'
TYPE='Beyond.Gameplay.Core.AbilityAction+AbilityActionData'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack'
SCHEMA='endfield.skill-action-union-source.v1'


def union_program(regions,entry,s,*,tag,count,table,selected,ff=False):
    """Full selected caller; count/addresses are supplied by fresh owned source."""
    if (type(ff)is not bool or any(type(v)is not int for v in(tag,count,table,selected))
            or not 0<=tag<count<=65536 or not 0<table-s['imageBase']<1<<32):
        raise ValueError(LABEL+'.caller:literal-tag-table-domain')
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742418','57','4883ec20')
    flag=g.relative('803d')+1;g.take('00','498bd8','488bfa');g.branch('0f85',True)
    g.take('33f6','488d542438','4533c0','6689742438','488bcf');g.call(s['header'])
    g.take('84c0');g.branch('0f84',ff)
    cast_usage=child_usage=None
    if ff:g.take('488933','33d2')
    else:
        g.take('0fb7742438','81fe'+(count-1).to_bytes(4,'little').hex());g.branch('0f87',False)
        if g.relative('488d15')!=s['imageBase']:raise ValueError(LABEL+'.caller:image-base')
        g.take('8b8cb2'+(table-s['imageBase']).to_bytes(4,'little').hex(),'4803ca','ffe1')
        try:word=bytes(g.bytes[table+tag*4+i]for i in range(4))
        except KeyError as error:raise ValueError(LABEL+'.caller:unowned-table-word')from error
        if s['imageBase']+int.from_bytes(word,'little')!=selected:
            raise ValueError(LABEL+'.caller:indexed-table-target')
        if selected not in g.bytes:raise ValueError(LABEL+'.caller:unowned-selected-case')
        g.at=selected
        at=g.at;cast_usage=dict(instruction=at,cell=g.relative('488b15'))
        g.take('488b0b');g.call(s['cast']);g.take('488bcf','4885c0');g.branch('75',False,1)
        at=g.at;child_usage=dict(instruction=at,cell=g.relative('488b15'))
        g.call(s['closedPackable']);g.take('488903','488bd0')
        if g.bytes.get(g.at)==0xeb:g.jump('eb',1)
        else:g.jump('e9')
    g.take('488bcb');g.call(s['barrier'])
    g.take('488b5c2430','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,initializedFlag=flag,tag=None if ff else tag,
        canonicalFF=ff,tagOutputBits=16,tableIndexBits=32,
        castUsage=cast_usage,childUsage=child_usage,headerTarget=s['header'],
        castTarget=None if ff else s['cast'],childTarget=None if ff else s['closedPackable'],
        barrierTarget=s['barrier'],outputInitiallyNull=not ff,clearedOutputBytes=8 if ff else 0,
        sameReader=True,sameOutput=True,unchangedCompleteReference=True,normalReturn=True,
        entryRspRestored=True,nonvolatilesRestored=['rbx','rsi','rdi'],
        concreteChildGrammarAdmitted=False)


def _direct(image,site,opcode=0xe8):
    raw=image.pe.bytes_at_va(site,5)
    if raw[0]!=opcode:raise ValueError(LABEL+'.actual-direct-transfer:'+hex(site))
    return site+5+int.from_bytes(raw[1:],'little',signed=True)


def original_lineage(image,ctx,wrapper,ancestor):
    """Follow owned type records, including an independently closed reference.

    A generic spelling never supplies its definition. Its actual wrapper
    instance field and selected carrier own that join. This bounded profile
    refuses parents containing unresolved VARs instead of substituting them.
    """
    from scripts.game_data.il2cpp.reference_layouts import closed_generic_reference_extent
    from scripts.game_data.memorypack.wrapper_members import INSTANCE_FIELD_NAMES
    md=image.metadata
    fields=[f for f in md.fields_for(md.types[wrapper.type_definition])
        if md.string(f.name_index)in INSTANCE_FIELD_NAMES and not ctx.field_attributes(f.type_index)&16
        and ctx.type_name(f.type_index)==wrapper.wrapped_type]
    if len(fields)!=1:raise ValueError(LABEL+'.original-lineage:one-owned-instance-field')
    index=fields[0].type_index;chain=[];seen=set()
    for _ in range(32):
        name=ctx.type_name(index);raw=image.pe.bytes_at_va(ctx.type_pointer(index),16)
        if index in seen or len(raw)!=16 or raw[11]!=0 or 'VAR['in name:
            raise ValueError(LABEL+'.original-lineage:cycle-or-undecorated-closed-reference')
        seen.add(index);generic=None
        if raw[10]==18:
            definition=int.from_bytes(raw[:8],'little')
            if not 0<=definition<len(md.types)or md.type_full_name(md.types[definition])!=name or ctx.is_value_type(name):
                raise ValueError(LABEL+'.original-lineage:ordinary-owned-reference')
        elif raw[10]==21:
            generic=closed_generic_reference_extent(ctx,index);definition=generic['definitionTypeIndex']
            if generic['type']!=name:raise ValueError(LABEL+'.original-lineage:closed-carrier-identity')
        else:raise ValueError(LABEL+'.original-lineage:reference-type-kind')
        chain.append(dict(typeName=name,typeIndex=index,rawTypeHex=raw.hex().upper(),
            definitionTypeIndex=definition,closedGenericReference=generic))
        if name==ancestor:return chain
        index=md.types[definition].parent_index
        if index<0:break
    raise ValueError(LABEL+'.original-lineage:missing-owned-ancestor:'+wrapper.wrapped_type+':'+ancestor)


def derive(image,pins):
    """Fresh complete transport for every current case, with no child admission."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.formatter_composition import _vtable,derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import modelview_packable_sources,pointer_param as pointer
    from scripts.game_data.memorypack import reference_adapter_sources as adapters,scalar_param_native as scalar
    from scripts.game_data.memorypack.current_reference_union_sources import _lineage
    from scripts.game_data.memorypack.module_structure_models import enclosing_header
    from scripts.game_data.memorypack.pooled_string_list_sources import compatible_list_cast
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_selector_union_sources import closed_packable_thunk_program
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _wrapper_holder
    from scripts.game_data.memorypack.union_dispatch import read_union_switch
    need=lambda k,e,a:scalar.need(LABEL,k,e,a)
    _publication_gate(image,pins)
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    wrappers=image.memorypack_wrappers;by_name={w.name:w for w in wrappers.values()};wrapper=by_name[WRAPPER]
    need('actual-original',TYPE,wrapper.wrapped_type)
    switch=read_union_switch(image,WRAPPER,wrappers=wrappers);entry=int(switch['dispatcherVa'],16)
    body=pointer.owned(image,entry);table=int(switch['tableVa'],16);count=switch['entryCount']
    need('complete-finite-unsigned16-domain',list(range(count)),[r['tag']for r in switch['entries']])
    formatter_name=WRAPPER+'+'+WRAPPER.rsplit('.',1)[-1]+'Formatter'
    formatter,=image.named_type_definitions[formatter_name]
    fm,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize']
    need('actual-slot5-entry',entry,image.method_pointer_va(fm));_vtable(image,formatter.index,5,fm.index,LABEL)
    need('instance-void-slot5',(False,'void',5,2),(bool(fm.flags&16),ctx.type_name(fm.return_type),fm.slot,fm.parameter_count))
    scalar.ordinary(image,ctx.type_pointer(fm.return_type),1,LABEL+'.void')
    for p,name,kind in zip(md.parameters_for(fm),('MemoryPack.MemoryPackReader',WRAPPER),(17,18),strict=True):
        raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)
        need('actual-owned-byrefs',(name,bytes((kind,32))),(ctx.type_name(p.type_index),raw[10:12]))
    pattern=bytes.fromhex('33f6488d5424384533c06689742438488bcfe8');headers=[]
    for at,raw in body['regions']:
        pos=raw.find(pattern)
        while pos>=0:
            headers.append(_direct(image,at+pos+len(pattern)-1));pos=raw.find(pattern,pos+1)
    need('one-actual-header-call',1,len(headers));header=headers[0];header_source=pointer.owned(image,header)
    header_programs={marker:enclosing_header(header_source['regions'],header,scalar.reader_offsets(image,LABEL),marker=marker)
        for marker in('short','extended','false')}
    first=int(switch['entries'][0]['bodyVa'],16);cast=_direct(image,first+10)
    finish=_direct(image,first+41,0xe9);need('actual-finish-receiver',b'\x48\x8b\xcb',image.pe.bytes_at_va(finish,3))
    barrier=_direct(image,finish+3);barrier_proof=_barrier(image,barrier)
    cast_source=pointer.owned(image,cast);cast_proof=compatible_list_cast(cast_source['regions'],cast,0,null=True)
    core=json.loads((CONTRACTS_DIR/'npc_runtime_native.json').read_bytes())
    generic=json.loads((CONTRACTS_DIR/'leveldata_npc_patrol_native.json').read_bytes())
    for name,fact in(('packable',core),('reference',generic)):need(name+'-selected-build',pins,fact['nativeInputs'])
    routes=copy.deepcopy(generic['declarations']['adapters']['referenceRoutes']);routes['wrappers']=[]
    reference=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)
    packable=base+core['readPackable']['entryRva'];symbols=dict(imageBase=base,header=header,cast=cast,barrier=barrier)
    programs=[]
    for selected in switch['entries']:
        child=by_name[selected['wrapperName']];at=int(selected['bodyVa'],16);tag=selected['tag']
        # Only the exact current no-thunk case shape is selected by this
        # profile. A future case trampoline requires its own transfer proof.
        need('direct-owned-table-case',selected['targetVa'],selected['bodyVa'])
        actual=_direct(image,at+30)
        thunk=closed_packable_thunk_program(image.pe.bytes_at_va(actual,12),actual,packable)
        program=union_program(body['regions'],entry,dict(symbols,closedPackable=actual),tag=tag,
            count=count,table=table,selected=int(selected['targetVa'],16))
        parent=derive_typed_usage_context(image,program['childUsage']['instruction']-base,label=LABEL+'.parent')
        usage=derive_typed_usage_context(image,thunk['contextInstruction']-base,label=LABEL+'.thunk')
        need('same-actual-parent-and-thunk-MethodSpec',parent['methodSpec'],usage['methodSpec'])
        typed=bind_typed_read(image,usage,method_name='ReadPackable',argument=child.name,kind=18,reference=True)
        need('actual-reference-reader-definition',reference['packableContext']['packableDefinition'],typed['methodDefinition'])
        cast_usage=derive_typed_usage_context(image,program['castUsage']['instruction']-base,label=LABEL+'.cast')
        need('actual-nominal-nullable-cast',(1,child.name),(cast_usage['tag'],cast_usage['typeName']))
        slot=table+tag*4;word=image.pe.u32_at_va(slot)
        need('indexed-unsigned-table-target',int(selected['targetVa'],16),base+word)
        programs.append(dict(family='AbilityActionData',tag=tag,wrapperName=child.name,wrappedType=child.wrapped_type,
            source=program,nullableCast=cast_usage,parentTypedRequest=parent,typedRequest=usage,typedArgument=typed,
            closedPackableThunk=thunk,tableEntry=dict(rva=slot-base,rawHex=word.to_bytes(4,'little').hex().upper(),unsignedTargetRva=word),
            originalLineage=original_lineage(image,ctx,child,TYPE),wrapperLineage=_lineage(ctx,md,child.name,WRAPPER),
            concreteChildGrammarAdmitted=False))
    null=union_program(body['regions'],entry,symbols,tag=0,count=count,table=table,
        selected=int(switch['entries'][0]['targetVa'],16),ff=True)
    pair=derive_pair(image,TYPE,WRAPPER)
    def forwarder(selected_image,selected_pair,selected_wrapper):
        face,=selected_pair['composition']['interfaces']
        need('same-selected-base-slot5',(WRAPPER,fm.index),(selected_wrapper.name,face['formatterDeserializeMethodIndex']))
        return dict(ownedWindows=body['windows'],programs=programs,canonicalFF=null)
    adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=forwarder)
    getter=pointer.methods(image,wrapper)['GetValue'];getter_entry=image.method_pointer_va(getter)
    getter_proof=pointer.leaf(image,getter_entry,['488B4110','C3']);holder=_wrapper_holder(ctx,image,wrapper)
    need('actual-base-holder',(TYPE,16),(holder['declaredType'],holder['offset']))
    need('abstract-base-wrapper',128,md.types[wrapper.type_definition].flags&128)
    face,=pair['composition']['interfaces'];section=md.sections['interfaceOffsets'];joins=[]
    conversion_entry=base+adapter['canonicalRoutes']['symbolRvas']['conversion'];conversion=pointer.owned(image,conversion_entry)
    for route in programs:
        child=by_name[route['wrapperName']];td=md.types[child.type_definition];child_holder=_wrapper_holder(ctx,image,child)
        need('same-inherited-base-holder',(TYPE,16),(child_holder['declaredType'],child_holder['offset']))
        start=section.offset+td.interface_offsets_start*8
        faces=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8]))
        found=[(ordinal,offset)for ordinal,(index,offset)in enumerate(faces)if index==face['interfaceTypeIndex']]
        need('one-concrete-base-interface:'+child.name,1,len(found));ordinal,offset=found[0]
        _vtable(image,child.type_definition,offset,getter.index,LABEL+'.baseGetter')
        converted=adapters.conversion(conversion['regions'],conversion_entry,
            base+adapter['canonicalRoutes']['conversionPrepareRva'],getter_entry,ordinal=ordinal)
        joins.append(dict(wrapperName=child.name,interfaceOrdinal=ordinal,interfaceOffset=offset,
            interfaceTypeIndex=face['interfaceTypeIndex'],baseGetValueMethod=getter.index,holder=child_holder,conversion=converted))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-current-action-union-transport',nativeInputs=pins,
        typeName=TYPE,wrapperName=WRAPPER,slot5Method=[fm.index,formatter_name,'Deserialize',entry-base],
        switch=switch,ownedWindows=body['windows'],programs=programs,canonicalFF=null,
        headerWindows=header_source['windows'],headerPrograms=header_programs,referencePackable=reference,
        nullableCast=dict(windows=cast_source['windows'],program=cast_proof),barrier=barrier_proof,
        pair=pair,adapter=adapter,baseHolder=holder,baseGetValue=getter_proof,derivedOriginalConversions=joins,
        baseGetterSemanticsAdmitted=True,concreteGetterSemanticsAdmitted=False,concreteFactorySemanticsAdmitted=False,
        concreteChildGrammarAdmitted=False,wholeUnionAdmitted=False,wholeSkillDataAdmitted=False,
        evidenceBoundary=dict(exact='Fresh current action table/wrapper bijection and complete warmed canonical short/extended/FF caller paths, actual nullable casts, closed MethodSpec thunks, owned reference ReadPackable source, full output/barrier/RET and base adapter/inherited GetValue conversions.',
            conditional=__doc__+' Buffered nonwrapping disjoint storage, initialized coherent MethodInfos, initially null positive wrapper output, matching canonical callbacks and normal helper/provider/cache/collector effects are required.',
            structuralOnly='Serialized action configuration; action execution/order and runtime selection are unobserved.',
            unresolved=['each concrete child grammar/cache/factory','existing output alternatives','reserved union markers',
                'cold/refill/malformed paths','runtime callback/provider/cache/default/inflation choice','enclosing lists and whole owners']))))

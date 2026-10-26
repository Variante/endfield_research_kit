"""Selected current selector union transfers and their original caller frames.

This owns the current warm dispatcher programs. The tag table, closed child
requests, actual helper bodies and concrete wrapper grammars must all be joined
on one selected image. A table row or type name supplies none of those joins.
"""
import copy
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='skillSelectorUnionSources'


def peek(g,n=1):return bytes(g.bytes[g.at+i]for i in range(n))


def branch(g,code,taken):
    if peek(g)==bytes((0x70+code,)):g.branch(f'{0x70+code:02x}',taken,1)
    else:g.branch('0f'+f'{0x80+code:02x}',taken)


def jump(g):
    if peek(g)==b'\xeb':g.jump('eb',1)
    else:g.jump('e9')


def _table(g,tag,count,table,image_base,selected,*,finder=False):
    if type(tag)is not int or not 0<=tag<count<128:raise ValueError(LABEL+'.tag-range')
    rva=table-image_base
    if not 0<rva<1<<32:raise ValueError(LABEL+'.table-rva')
    if finder:g.take('418b8cb7'+rva.to_bytes(4,'little').hex(),'4903cf','ffe1')
    else:
        if g.relative('488d15')!=image_base:raise ValueError(LABEL+'.image-base')
        g.take('8b84b2'+rva.to_bytes(4,'little').hex(),'4803c2','ffe0')
    if selected not in g.bytes:raise ValueError(LABEL+'.unowned-selected-case')
    g.at=selected
    if peek(g)==b'\xe9':jump(g)


def small_program(regions,entry,s,*,tag,count,table,selected,ff=False):
    """Exact Validator/PostProcessor selected null-output child or FF path."""
    if type(ff)is not bool:raise ValueError(LABEL+'.small:mode')
    if type(tag)is not int or not 0<=tag<count<128:raise ValueError(LABEL+'.small:tag')
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742418','57','4883ec20')
    flag=g.relative('803d')+1;g.take('00','498bf8','488bda');g.branch('0f84',False)
    g.take('33f6','488d542438','488bcb','6689742438');g.call(s['header'])
    g.take('84c0');g.branch('0f84',ff)
    child=None
    if ff:
        g.take('488937');jump(g)
    else:
        g.take('0fb7742438')
        if peek(g,2)==b'\x8b\xc6':
            g.take('8bc6','83fe0a');g.branch('75',tag!=10,1)
            if tag!=10:
                g.take('83f8'+bytes((count-1,)).hex());g.branch('0f87',False)
                _table(g,tag,count,table,s['imageBase'],selected)
            elif g.at!=selected:raise ValueError(LABEL+'.small:hot-case-identity')
        else:
            g.take('83fe'+bytes((count-1,)).hex());g.branch('0f87',False)
            _table(g,tag,count,table,s['imageBase'],selected)
        g.take('488b0f','4885c9');branch(g,4,True)
        site=g.at;cell=g.relative('488b15');child=dict(instruction=site,cell=cell)
        g.take('488bcb');g.call(s['packable'])
        if peek(g,3)==b'\x48\x8b\xcf':g.take('488bcf','488907')
        else:g.take('488907')
        if peek(g)in(b'\xe9',b'\xeb'):jump(g)
    # The returned full reference (or literal zero) reaches the same output
    # barrier. The bounded selected path then restores the original frame.
    if peek(g,3)==b'\x48\x8b\xcf':g.take('488bcf')
    g.call(s['barrier'])
    if peek(g)in(b'\xe9',b'\xeb'):jump(g)
    g.take('488b5c2430','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,initializedFlag=flag,tag=None if ff else tag,
        canonicalFF=ff,childUsage=child,headerTarget=s['header'],
        childTarget=None if ff else s['packable'],barrierTarget=s['barrier'],
        outputInitiallyNull=not ff,clearedOutputBytes=8 if ff else 0,
        sameReader=True,sameOutput=True,normalReturn=True,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rsi','rdi'],
        condition='Initialized matching union; selected canonical short tag or FF; header/typed child/helper ABI and source-disjoint effects; positive path starts with null wrapper output. Current table word, child context and complete child grammar are independently required.')


def finder_program(regions,entry,s,*,tag,count,table,selected,ff=False):
    """Warm Finder source skips only the actual initialized cold metadata arm."""
    if type(ff)is not bool or type(tag)is not int or not 0<=tag<count<128:
        raise ValueError(LABEL+'.finder:mode-or-tag')
    g=BytesPath(regions,entry)
    g.take('488bc4','48895820','55','56','57','4154','4157','488bec','4883ec70','4533e4')
    if g.relative('4c8d3d')!=s['imageBase']:raise ValueError(LABEL+'.finder:image-base')
    flag=g.relative('443825');g.take('498bd8','488bfa');g.branch('0f85',True)
    g.take('488d5538','6644896538','488bcf');g.call(s['header'])
    g.take('84c0');g.branch('0f84',ff)
    child=cast_usage=None
    if ff:g.take('4c8923')
    else:
        g.take('0fb77538','83fe'+bytes((count-1,)).hex());g.branch('0f87',False)
        _table(g,tag,count,table,s['imageBase'],selected,finder=True)
        site=g.at;cell=g.relative('488b15');cast_usage=dict(instruction=site,cell=cell)
        g.take('488b0b');g.call(s['cast']);g.take('488bcf','4885c0');g.branch('75',False,1)
        if peek(g,3)==bytes.fromhex('488b15'):
            site=g.at;cell=g.relative('488b15');child=dict(instruction=site,cell=cell)
            g.call(s['packable'])
        else:
            g.call(s['closedPackable'])
        g.take('488903');jump(g)
    g.take('488bcb');g.call(s['barrier'])
    g.take('488b9c24b8000000','4883c470','415f','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,initializedFlag=flag,tag=None if ff else tag,
        canonicalFF=ff,childUsage=child,castUsage=cast_usage,headerTarget=s['header'],
        childTarget=None if ff else s['packable']if child is not None else s['closedPackable'],barrierTarget=s['barrier'],
        outputInitiallyNull=not ff,clearedOutputBytes=8 if ff else 0,
        sameReader=True,sameOutput=True,normalReturn=True,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r15'],
        condition='Actual metadata flag is warmed; current initialized union short header or FF; positive output initially null and exact nullable cast returns null, matching typed child/helper callbacks, normal disabled barrier and disjoint storage. Cold metadata effects, R13/R14 cold-only save/restore paths and runtime provider/default choice remain separate.')


def closed_packable_thunk_program(raw,entry,target):
    """Exact closed MethodInfo load and tail; RCX/source and RSP are untouched."""
    if not isinstance(raw,bytes)or len(raw)!=12:raise ValueError(LABEL+'.closed-thunk:extent')
    g=BytesPath([(entry,raw)],entry);cell=g.relative('488b15')
    if g.relative('e9')!=target:raise ValueError(LABEL+'.closed-thunk:tail-target')
    return dict(selectedBytes=g.seen,contextInstruction=entry,contextCell=cell,
        tailTarget=target,sourceReaderRCXPreserved=True,tailEntryRspPreserved=True,
        physicalExtentProved=False,condition='Actual selected direct E8 enters this exact twelve-byte leaf prefix. The independently owned generic reader receives the same RCX and caller frame with the owned closed MethodInfo in RDX; its complete selected return is independently required.')


def derive_dispatches(image,pins,*,include_nonzero=False):
    """Current typed union callers; each concrete grammar composes later."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,_vtable
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack import modelview_packable_sources
    from scripts.game_data.memorypack.module_structure_models import enclosing_header
    from scripts.game_data.memorypack.pooled_string_list_sources import compatible_list_cast
    from scripts.game_data.memorypack.skill_selector_current_sources import FAMILIES
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.union_dispatch import read_union_switch
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    need=lambda k,e,a:scalar.need(LABEL,k,e,a)
    if type(include_nonzero)is not bool:raise ValueError(LABEL+'.dispatch-mode')
    _publication_gate(image,pins)
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    wrappers=derive_from_image(image);by_name={w.name:w for w in wrappers.values()}
    core=json.loads((CONTRACTS_DIR/'npc_runtime_native.json').read_bytes())
    generic=json.loads((CONTRACTS_DIR/'leveldata_npc_patrol_native.json').read_bytes())
    need('packable-declaration-build',pins,core['nativeInputs'])
    need('reference-declaration-build',pins,generic['nativeInputs'])
    routes=copy.deepcopy(generic['declarations']['adapters']['referenceRoutes']);routes['wrappers']=[]
    reference=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)
    packable=base+core['readPackable']['entryRva'];offsets=scalar.reader_offsets(image,LABEL)
    results={}
    for family,name in FAMILIES.items():
        switch=read_union_switch(image,name,wrappers=wrappers);entry=int(switch['dispatcherVa'],16)
        body=pointer.owned(image,entry);table=int(switch['tableVa'],16)
        wrapper=by_name[name];formatter_name=name+'+'+name.rsplit('.',1)[-1]+'Formatter'
        formatter,=image.named_type_definitions[formatter_name]
        method,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize']
        need('own-union-entry',entry,image.method_pointer_va(method));_vtable(image,formatter.index,5,method.index,LABEL)
        need('own-instance-slot5',(False,5,'void',2),(bool(method.flags&16),method.slot,ctx.type_name(method.return_type),method.parameter_count))
        scalar.ordinary(image,ctx.type_pointer(method.return_type),1,LABEL+'.unionReturn')
        for parameter,type_name,kind in zip(md.parameters_for(method),('MemoryPack.MemoryPackReader',name),(17,18),strict=True):
            raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
            need('owned-union-byrefs',(type_name,bytes((kind,32))),(ctx.type_name(parameter.type_index),raw[10:12]))
        finder=family=='SelectorFinder'
        pattern=bytes.fromhex('488d55386644896538488bcfe8'if finder else'488d542438488bcb6689742438e8')
        candidates=[]
        for at,raw in body['regions']:
            pos=raw.find(pattern)
            while pos>=0:
                call=at+pos+len(pattern)-1
                candidates.append(call+5+int.from_bytes(image.pe.bytes_at_va(call+1,4),'little',signed=True))
                pos=raw.find(pattern,pos+1)
        need('one-actual-union-header',1,len(candidates));header=candidates[0]
        header_source=pointer.owned(image,header)
        headers={marker:enclosing_header(header_source['regions'],header,offsets,marker=marker)
            for marker in('short','false')}
        # Recover the actual output barrier from the FF selected source, then
        # let the exact caller program own the whole path to it and RET.
        rows=body['rows'];barriers=[]
        for index,row in enumerate(rows):
            raw=bytes.fromhex(row['bytes']);site=int(row['va'],16)
            if len(raw)==5 and raw[0]==0xe8 and index and bytes.fromhex(rows[index-1]['bytes'])in(b'\x48\x8b\xcb',b'\x48\x8b\xcf'):
                target=site+5+int.from_bytes(raw[1:],'little',signed=True)
                if image.pe.bytes_at_va(target,2)in(b'\x83\x3d',b'\xe9\x00')or image.pe.bytes_at_va(target,1)==b'\xe9':barriers.append(target)
        barriers=list(dict.fromkeys(barriers));need('one-actual-union-output-barrier',1,len(barriers));barrier=barriers[0]
        symbols=dict(imageBase=base,header=header,packable=packable,barrier=barrier)
        cast_source=cast_program=None
        if finder:
            first=int(switch['entries'][0]['bodyVa'],16)
            # Exact common first-case prefix owns this E8 position. Each
            # selected case model below checks the same direct call target.
            cast_site=first+10;raw=image.pe.bytes_at_va(cast_site,5)
            need('finder-actual-null-cast-call',(5,b'\xe8'),(len(raw),raw[:1]))
            cast=cast_site+5+int.from_bytes(raw[1:],'little',signed=True);symbols['cast']=cast
            cast_source=pointer.owned(image,cast)
            cast_program=compatible_list_cast(cast_source['regions'],cast,0,null=True)
        programs=[]
        function=finder_program if finder else small_program
        for selected in switch['entries']:
            child=by_name[selected['wrapperName']]
            if child.members and not include_nonzero:continue
            slot=table+4*selected['tag'];word=image.pe.u32_at_va(slot)
            need('current-indexed-tag-case',base+word,int(selected['targetVa'],16))
            selected_symbols=dict(symbols);thunk=None
            if finder:
                first=int(selected['bodyVa'],16)
                case=image.pe.bytes_at_va(first,24)
                if case[:3]==bytes.fromhex('488b15')and case[7:11]==bytes.fromhex('488b0be8')and case[15:24]==bytes.fromhex('488bcf4885c0750de8'):
                    site=first+23;raw=image.pe.bytes_at_va(site,5)
                    actual=site+5+int.from_bytes(raw[1:],'little',signed=True)
                    selected_symbols['closedPackable']=actual
                    thunk=closed_packable_thunk_program(image.pe.bytes_at_va(actual,12),actual,packable)
            program=function(body['regions'],entry,selected_symbols,tag=selected['tag'],count=switch['entryCount'],
                table=table,selected=int(selected['bodyVa'],16))
            context=program['childUsage']['instruction']if program['childUsage']is not None else thunk['contextInstruction']
            usage=derive_typed_usage_context(image,context-base,label=LABEL)
            typed=bind_typed_read(image,usage,method_name='ReadPackable',argument=child.name,kind=18,reference=True)
            need('same-owned-packable-definition',reference['packableContext']['packableDefinition'],typed['methodDefinition'])
            cast_usage=None
            if finder:
                cast_usage=derive_typed_usage_context(image,program['castUsage']['instruction']-base,label=LABEL)
                need('finder-same-concrete-wrapper-cast',(1,child.name),(cast_usage['tag'],cast_usage['typeName']))
            item=dict(family=family,tag=selected['tag'],wrapperName=child.name,wrappedType=child.wrapped_type,
                tableEntry=dict(rva=slot-base,rawHex=word.to_bytes(4,'little').hex().upper(),unsignedTargetRva=word),
                source=program,typedRequest=usage,typedArgument=typed,nullableCast=cast_usage)
            if thunk is not None:item['closedPackableThunk']=thunk
            programs.append(item)
        selected=switch['entries'][0]
        null=function(body['regions'],entry,symbols,tag=selected['tag'],count=switch['entryCount'],table=table,
            selected=int(selected['bodyVa'],16),ff=True)
        results[family]=dict(switch=switch,slot5Method=[method.index,formatter_name,'Deserialize',entry-base],
            wrapperName=name,wrappedType=wrapper.wrapped_type,ownedWindows=body['windows'],programs=programs,
            canonicalFF=null,headerWindows=header_source['windows'],headerPrograms=headers,barrier=_barrier(image,barrier),
            nullableCast=dict(windows=cast_source['windows'],program=cast_program)if finder else None)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(status='validated-all-selector-dispatches'if include_nonzero else'validated-zero-selector-dispatches',nativeInputs=pins,
        families=results,referencePackable=reference,concreteChildGrammarAdmitted=False,
        originalBaseAdapterAdmitted=False,wholeSkillDataAdmitted=False,
        evidenceBoundary=dict(exact='Current short/FF union-header source, complete warm indexed dispatch caller and selected null-output typed ReadPackable<ConcreteWrapper> paths through full output/barrier/RET; exact table words and method-context arguments, independently complete reference helper source and slot5 ABI.',
            conditional='Matching selected concrete generated callbacks and initialized inflated contexts, normal helper/collector effects, sufficient nonwrapping buffered disjoint storage; positive incoming wrapper output null, nullable Finder cast null branch. Runtime provider/default selection remains unobserved.',
            unresolved=['concrete child grammar composition','base original adapter/conversion/GetValue composition']+
                ([]if include_nonzero else['nonzero selector callers'])+
                ['existing-output alternative','reserved markers','refill/malformed paths','whole owners']))))


def _derive_with_ec(image,pins,ec_component=None,*,buff_find_component=None,buff_filter_component=None,nested_component=None,geometry_component=None,selected_nonzero_wrappers=None):
    """Compose finite closed children, base Original conversion and lists."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.formatter_composition import _vtable,derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec,pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack import reference_adapter_sources as adapter_source
    from scripts.game_data.memorypack.skill_selector_current_sources import derive_zero_components
    from scripts.game_data.memorypack.skill_selector_nonzero_components import _derive_with_dispatches
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _wrapper_holder
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.reference_list_induction_sources import derive as derive_list_induction
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack.skill_timeline_current_sequence import validate_program
    need=lambda k,e,a:scalar.need(LABEL,k,e,a)
    _publication_gate(image,pins)
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    wrappers={w.name:w for w in derive_from_image(image).values()}
    dispatches=derive_dispatches(image,pins,include_nonzero=True);children=derive_zero_components(image,pins)
    nonzero=_derive_with_dispatches(image,pins,dispatches,ec_component=ec_component,
        buff_find_component=buff_find_component,buff_filter_component=buff_filter_component,nested_component=nested_component,
        geometry_component=geometry_component,wrapper_names=selected_nonzero_wrappers)
    source_children={(r['family'],r['tag']):r for r in children['components']}
    callers={(family,row['tag']):row for family,body in dispatches['families'].items()for row in body['programs']}
    zero_callers={key for key,row in callers.items()if not wrappers[row['wrapperName']].members and not wrappers[row['wrapperName']].abstract}
    need('complete-zero-child-caller-bijection',set(source_children),zero_callers)
    nonzero_rows={(r['family'],r['tag']):r for r in nonzero['programs']}
    nonzero_sources={r['wrapperName']:r for r in nonzero['proof']['concreteReaders']}
    need('disjoint-finite-child-programs',set(),set(source_children)&set(nonzero_rows))
    need('nonzero-current-caller-join',True,set(nonzero_rows)<=set(callers))
    base_adapters={};programs=[];capabilities={}
    for family,body in dispatches['families'].items():
        wrapper=wrappers[body['wrapperName']];original=wrapper.wrapped_type
        pair=derive_pair(image,original,wrapper.name)
        def prove_forwarder(selected_image,selected_pair,selected_wrapper):
            face,=selected_pair['composition']['interfaces']
            need('same-selected-union-base',wrapper.name,selected_wrapper.name)
            need('same-base-slot5-source',body['slot5Method'][0],face['formatterDeserializeMethodIndex'])
            return body
        adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=prove_forwarder)
        getter=pointer.methods(image,wrapper)['GetValue'];getter_entry=image.method_pointer_va(getter)
        getter_proof=pointer.leaf(image,getter_entry,['488B4110','C3'])
        base_holder=_wrapper_holder(ctx,image,wrapper)
        need('own-base-holder',(original,16),(base_holder['declaredType'],base_holder['offset']))
        need('abstract-base-wrapper',128,md.types[wrapper.type_definition].flags&128)
        face,=pair['composition']['interfaces'];section=md.sections['interfaceOffsets'];joins=[]
        conversion_entry=base+adapter['canonicalRoutes']['symbolRvas']['conversion']
        conversion=pointer.owned(image,conversion_entry)
        for route in body['programs']:
            identity=(family,route['tag'])
            if identity not in source_children and identity not in nonzero_rows:continue
            child=wrappers[route['wrapperName']]
            if identity in source_children:
                component=source_children[identity]
                need('selected-child-identity',(child.name,child.wrapped_type),(component['wrapperName'],component['wrappedType']))
                need('same-base-typed-holder',original,component['holder']['declaredType'])
                row=dict(family=family,tag=route['tag'],wrapperName=child.name,wrappedType=child.wrapped_type,
                    memberCount=0,sourceOwner='skill_timeline_current_sequence_native.json',reads=[],wrapperNullAdmitted=True)
            else:
                component=nonzero_sources[child.name];row=nonzero_rows[identity]
                need('selected-nonzero-child-identity',(child.name,child.wrapped_type),(row['wrapperName'],row['wrappedType']))
                holder=component['lifecycle']['baseHolder']
                need('same-nonzero-base-typed-holder',(original,16),(holder[1],holder[2]))
            td=md.types[child.type_definition];start=section.offset+td.interface_offsets_start*8
            faces=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8]))
            found=[(ordinal,offset)for ordinal,(index,offset)in enumerate(faces)if index==face['interfaceTypeIndex']]
            need('one-derived-base-interface:'+child.name,1,len(found));ordinal,offset=found[0]
            _vtable(image,child.type_definition,offset,getter.index,LABEL+'.baseGetter')
            converted=adapter_source.conversion(conversion['regions'],conversion_entry,
                base+adapter['canonicalRoutes']['conversionPrepareRva'],getter_entry,ordinal=ordinal)
            joins.append(dict(wrapperName=child.name,interfaceOrdinal=ordinal,interfaceOffset=offset,
                interfaceTypeIndex=face['interfaceTypeIndex'],baseGetValueMethod=getter.index,conversion=converted))
            validate_program(row);programs.append(row)
        base_adapters[family]=dict(adapter=adapter,getter=getter_proof,holder=base_holder,derivedOriginalConversions=joins)
        capabilities[family]=dict(nullAdmitted=True,wholeGrammarAdmitted=False,
            admittedRouteTags=sorted(r['tag']for r in programs if r['family']==family),positiveRoutesRequireExplicitProgram=True)
    # Authenticate the existing EC SelectorData role before reading its actual
    # finder/provider and list call sites. A context copied from a declaration
    # cannot supply an enclosing source transfer by itself.
    role=ec.validate_on_image(image,pins);fact=json.loads(ec.CONTRACT_PATH.read_bytes());clones=ec.clone_facts(image,pins)
    for family,selected in capabilities.items():
        selected.update(typeName=base_adapters[family]['adapter']['typeName'],
            referenceReaderMethodDefinition=clones['ReadValue']['equivalentMethod'][0],
            referenceReaderTargetRva=clones['ReadValue']['targetRva'])
    profile,=[p for p in fact['proof']['profiles']if p['profile']=='member3']
    finder_event,=[e for e in profile['events']if e['kind']=='delegated-finder']
    finder_usage=derive_typed_usage_context(image,finder_event['context']['instructionRva'],label=LABEL)
    finder_type=base_adapters['SelectorFinder']['adapter']['typeName']
    finder_typed=bind_typed_read(image,finder_usage,method_name='ReadValue',argument=finder_type,kind=18,reference=True)
    need('finder-owned-read-definition',dispatches['referencePackable']['valueContext']['readerMethodDefinition'],finder_typed['methodDefinition'])
    events=[e for e in profile['events']if e['kind']=='delegated-list'];lists={}
    declared=[('target-postprocessor-list','SelectorPostProcessor'),('target-validator-list','SelectorValidator')]
    need('two-actual-selector-list-sources',2,len(events))
    for event,(capability,family)in zip(events,declared,strict=True):
        usage=derive_typed_usage_context(image,event['context']['instructionRva'],label=LABEL)
        at,encoded=event['instruction'];raw=bytes.fromhex(encoded)
        need('actual-selector-list-e8',(5,b'\xe8'),(len(raw),raw[:1]))
        target=base+at+5+int.from_bytes(raw[1:],'little',signed=True)
        element=base_adapters[family]['adapter']['typeName']
        listing=derive_list_induction(image,pins,typed_request=usage,call_target=target,
            element_type=element,count_limit=10000)
        need('same-selector-list-build',pins,listing['nativeInputs'])
        need('bounded-selector-list-induction',('validated-bounded-reference-list-induction',element,[-1,10000],False,False,False),
            tuple(listing[k]for k in('status','elementType','countRange','elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
        lists[capability]=listing
        capabilities[capability]=dict(elementType=element,closedListType='System.Collections.Generic.List`1<'+element+'>',
            collectionCounts=[-1,0],nullable=True,positiveCountsAdmitted=True,countLimit=10000,
            elementCapability=family,elementGrammarAdmitted=True,
            admittedRouteTags=capabilities[family]['admittedRouteTags'],
            referenceReaderTargetRva=clones['ReadValue']['targetRva'],
            referenceReaderMethodDefinition=clones['ReadValue']['equivalentMethod'][0],
            packableReaderTargetRva=target-base,packableReaderMethodDefinition=usage['methodSpec'][0])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(status='validated-finite-current-selector-routes',nativeInputs=pins,
        programs=programs,capabilities=capabilities,nullUnions={family:True for family in dispatches['families']},
        requiredExternalCapabilityIdentities=nonzero['requiredExternalCapabilityIdentities'],
        requiredExternalManagedValueIdentities=nonzero['requiredExternalManagedValueIdentities'],
        requiredExternalCollectionIdentities=nonzero['requiredExternalCollectionIdentities'],
        proof=dict(dispatches=dispatches,zeroChildren=children,nonzeroChildren=nonzero,baseAdapters=base_adapters,
            selectorParentRole=role,finderTypedRequest=finder_usage,finderTypedArgument=finder_typed,positiveLists=lists),
        wholeSkillDataAdmitted=False,evidenceBoundary=dict(
            exact='Finite current selector routes compose their actual short/FF union programs, indexed cases and typed ReadPackable<ConcreteWrapper> source with their own concrete slot5/readers/factories. Nonzero routes additionally compose complete initialized new/existing/FF callers, all selected member sources and exact named setter implementations; unsupported children remain pending. Each derived wrapper separately retains the base interface/vtable GetValue at holder16; base eager adapter/context/conversion is re-proved. EC parent role and distinct positive PostProcessor/Validator reference-list loops/counts independently join their exact current children.',
            conditional='Ready matching canonical base adapters and concrete generated/list callbacks; initialized coherent closed MethodInfos and typed compatible storage, normal allocations/casts/provider/preparation/barrier effects, collector disabled and buffered nonwrapping disjoint source/output/frame. List output starts null, or reused list count zero with sufficient capacity. Union wrapper output starts null. Live provider/default/override/inflation selection unobserved.',
            structuralOnly='Stored selectors do not prove runtime entity selection or validation outcomes.',
            unresolved=['listed unsupported selector children/source profiles','unknown tags and reserved markers','existing union output alternatives','list counts beyond10000','refill/malformed paths','whole enclosing owner']))))


def derive(image,pins):
    """Fresh public composition; no saved EC component is accepted here."""
    return _derive_with_ec(image,pins)

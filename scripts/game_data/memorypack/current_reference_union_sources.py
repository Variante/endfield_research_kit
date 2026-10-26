"""Owned current reference-union callers, separate from concrete child grammar.

Each finite family selects its actual nominal formatter. Complete initialized
caller paths prove short tags and FF, typed ReadPackable requests and output
transfers. Positive output starts null. Existing-output alternatives, runtime
callback choice, concrete children and enclosing owners remain separate.
"""
import copy
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.skill_selector_union_sources import branch,jump,peek

LABEL='currentReferenceUnionSources'
FAMILIES={
 'CalculationBase':('Beyond.Gameplay.Core.CalculationBase','table-rsi',6,2),
 'DamageProcessorBase':('Beyond.Gameplay.Core.DamageProcessorBase','table-rdi',11,5),
 'BuffInputBase':('Beyond.Gameplay.Core.BuffInputBase','pair-bpl',2,None),
 'AbilityCondition':('Beyond.Gameplay.Core.Abilities.Condition.ConditionBase','pair-edi',2,None),
}


def _finish(g,s,profile,ff,prepared=False):
    out='rsi'if profile=='table-rdi'else'rbx'
    if ff:g.take({'table-rsi':'488933','table-rdi':'48893e','pair-bpl':'48892b','pair-edi':'48893b'}[profile])
    if peek(g)in(b'\xe9',b'\xeb'):jump(g)
    setup='488bce'if out=='rsi'else'488bcb'
    if peek(g,3)==bytes.fromhex(setup):g.take(setup);prepared=True
    if not prepared:raise ValueError(LABEL+'.barrier:unproved-output-receiver')
    g.call(s['barrier'])
    if peek(g)in(b'\xe9',b'\xeb'):jump(g)
    g.take('488b5c2430','488b6c2440'if profile=='pair-bpl'else'488b742440','4883c420','5f','c3')


def _new_child(g,s,profile):
    out='rsi'if profile=='table-rdi'else'rbx'
    reader='rdi'if profile in('table-rsi','pair-bpl')else'rbx'if profile=='table-rdi'else'rsi'
    g.take('488b0e'if out=='rsi'else'488b0b','4885c9');branch(g,4,True)
    site=g.at;cell=g.relative('488b15')
    if peek(g)in(b'\xe9',b'\xeb'):jump(g)
    g.take({'rdi':'488bcf','rbx':'488bcb','rsi':'488bce'}[reader]);g.call(s['packable'])
    setup='488bce'if out=='rsi'else'488bcb';prepared=False
    if peek(g,3)==bytes.fromhex(setup):g.take(setup);prepared=True
    g.take('488906'if out=='rsi'else'488903')
    return dict(instruction=site,cell=cell,barrierReceiverPrepared=prepared)


def table_program(regions,entry,s,*,profile,tag,count,hot,table,selected,ff=False):
    if (profile not in('table-rsi','table-rdi')or type(ff)is not bool
            or any(type(value)is not int for value in(tag,count,hot,table,selected))
            or not 0<=tag<count<128 or not 0<=hot<count):
        raise ValueError(LABEL+'.table:selection')
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742418','57','4883ec20')
    flag=g.relative('803d')+1;g.take('00')
    g.take('498bd8','488bfa')if profile=='table-rsi'else g.take('498bf0','488bda')
    g.branch('0f84',False)
    if profile=='table-rsi':g.take('33f6','488d542438','488bcf','6689742438')
    else:g.take('33ff','488d542438','488bcb','66897c2438')
    g.call(s['header']);g.take('84c0');g.branch('0f84',ff)
    child=None
    if not ff:
        if profile=='table-rsi':g.take('0fb7742438','8bc6','83fe'+bytes((hot,)).hex())
        else:g.take('0fb77c2438','8bc7','83ff'+bytes((hot,)).hex())
        g.branch('75',tag!=hot,1)
        if tag!=hot:
            g.take('83f8'+bytes((count-1,)).hex());g.branch('0f87',False)
            if g.relative('488d15')!=s['imageBase']:raise ValueError(LABEL+'.table:image-base')
            rva=table-s['imageBase']
            if not 0<rva<1<<32:raise ValueError(LABEL+'.table:unsigned-rva')
            g.take(('8b8cb2'if profile=='table-rsi'else'8b84ba')+rva.to_bytes(4,'little').hex(),
                '4803ca'if profile=='table-rsi'else'4803c2','ffe1'if profile=='table-rsi'else'ffe0')
            if selected not in g.bytes:raise ValueError(LABEL+'.table:unowned-target')
            g.at=selected
        elif g.at!=selected:raise ValueError(LABEL+'.table:hot-target')
        child=_new_child(g,s,profile)
    _finish(g,s,profile,ff,child['barrierReceiverPrepared']if child else False)
    return dict(selectedBytes=g.seen,profile=profile,initializedFlag=flag,tag=None if ff else tag,
        canonicalFF=ff,childUsage=child,headerTarget=s['header'],childTarget=None if ff else s['packable'],
        barrierTarget=s['barrier'],outputInitiallyNull=not ff,clearedOutputBytes=8 if ff else 0,
        sameReader=True,sameOutput=True,normalReturn=True,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rsi','rdi'],concreteGrammarAdmitted=False)


def pair_program(regions,entry,s,*,profile,tag,ff=False):
    if profile not in('pair-bpl','pair-edi')or type(ff)is not bool or type(tag)is not int or tag not in(0,1):
        raise ValueError(LABEL+'.pair:selection')
    g=BytesPath(regions,entry);bpl=profile=='pair-bpl'
    g.take('48895c2408','48896c2418'if bpl else'4889742418','57','4883ec20')
    if bpl:
        g.take('33ed','498bd8');flag=g.relative('40382d');g.take('488bfa');g.branch('75',True,1)
        g.take('488d542438','66896c2438','488bcf')
    else:
        flag=g.relative('803d')+1;g.take('00','498bd8','488bf2');g.branch('0f84',False)
        g.take('33ff','488d542438','488bce','66897c2438')
    g.call(s['header']);g.take('84c0');g.branch('0f84',ff)
    child=None
    if not ff:
        if bpl:
            g.take('66396c2438');g.branch('75',tag!=0,1)
            if tag==1:g.take('66837c243801');g.branch('75',False,1)
        else:
            g.take('0fb77c2438','6685ff');g.branch('0f84',tag==0)
            if tag==1:g.take('6683ff01');g.branch('0f85',False)
        child=_new_child(g,s,profile)
    _finish(g,s,profile,ff,child['barrierReceiverPrepared']if child else False)
    return dict(selectedBytes=g.seen,profile=profile,initializedFlag=flag,tag=None if ff else tag,
        canonicalFF=ff,childUsage=child,headerTarget=s['header'],childTarget=None if ff else s['packable'],
        barrierTarget=s['barrier'],outputInitiallyNull=not ff,clearedOutputBytes=8 if ff else 0,
        sameReader=True,sameOutput=True,normalReturn=True,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rbp'if bpl else'rsi','rdi'],concreteGrammarAdmitted=False)


def _header_target(body,profile):
    patterns={'table-rsi':'488d542438488bcf6689742438e8',
        'table-rdi':'488d542438488bcb66897c2438e8',
        'pair-bpl':'488d54243866896c2438488bcfe8',
        'pair-edi':'488d542438488bce66897c2438e8'}
    pattern=bytes.fromhex(patterns[profile]);found=[]
    for at,raw in body['regions']:
        pos=raw.find(pattern)
        while pos>=0:
            site=at+pos+len(pattern)-1;start=pos+len(pattern)
            found.append(site+5+int.from_bytes(raw[start:start+4],'little',signed=True))
            pos=raw.find(pattern,pos+1)
    if len(found)!=1:raise ValueError(LABEL+'.header:one-actual-call-required:'+profile)
    return found[0]


def _lineage(ctx,metadata,child,ancestor):
    current=child;result=[]
    for _ in range(32):
        if current in result:raise ValueError(LABEL+'.inheritance:cycle')
        result.append(current)
        if current==ancestor:return result
        td=ctx.index.types[current]
        if td.parent_index<0:break
        current=ctx.type_name(td.parent_index)
        if current not in ctx.index.types:break
    raise ValueError(LABEL+'.inheritance:missing-owned-ancestor:'+child+':'+ancestor)


def derive(image,pins,*,families=None):
    """Fresh callers and abstract-base conversions; concrete children stay closed."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.formatter_composition import _vtable,derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import modelview_packable_sources
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack import reference_adapter_sources as adapters
    from scripts.game_data.memorypack.module_structure_models import enclosing_header
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _wrapper_holder
    from scripts.game_data.memorypack.union_dispatch import read_union_switch
    need=lambda k,e,a:scalar.need(LABEL,k,e,a)
    names=list(FAMILIES)if families is None else list(families)
    need('finite-distinct-owned-families',True,bool(names)and len(names)==len(set(names))and set(names)<=set(FAMILIES))
    _publication_gate(image,pins)
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    wrappers=image.memorypack_wrappers;by_name={w.name:w for w in wrappers.values()}
    core=json.loads((CONTRACTS_DIR/'npc_runtime_native.json').read_bytes())
    generic=json.loads((CONTRACTS_DIR/'leveldata_npc_patrol_native.json').read_bytes())
    model=json.loads((CONTRACTS_DIR/'model_view_state_controller_native.json').read_bytes())
    for name,fact in(('packable',core),('reference',generic),('collector',model)):
        need(name+'-declaration-build',pins,fact['nativeInputs'])
    routes=copy.deepcopy(generic['declarations']['adapters']['referenceRoutes']);routes['wrappers']=[]
    reference=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)
    packable=base+core['readPackable']['entryRva'];barrier=base+model['collector']['entryRva']
    barrier_proof=_barrier(image,barrier);offsets=scalar.reader_offsets(image,LABEL);result={}
    for family in names:
        original,profile,count,hot=FAMILIES[family]
        wrapper,=[w for w in wrappers.values()if w.wrapped_type==original]
        formatter_name=wrapper.name+'+'+wrapper.name.rsplit('.',1)[-1]+'Formatter'
        formatter,=image.named_type_definitions[formatter_name]
        fm,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize'
            and not m.flags&16 and m.slot==5 and m.parameter_count==2 and ctx.type_name(m.return_type)=='void']
        entry=image.method_pointer_va(fm);body=pointer.owned(image,entry)
        _vtable(image,formatter.index,5,fm.index,LABEL+'.slot5')
        scalar.ordinary(image,ctx.type_pointer(fm.return_type),1,LABEL+'.void')
        for parameter,type_name,kind in zip(md.parameters_for(fm),('MemoryPack.MemoryPackReader',wrapper.name),(17,18),strict=True):
            raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
            need('actual-instance-slot5-byrefs',(type_name,bytes((kind,32))),(ctx.type_name(parameter.type_index),raw[10:12]))
        header=_header_target(body,profile);hs=pointer.owned(image,header)
        headers={marker:enclosing_header(hs['regions'],header,offsets,marker=marker)for marker in('short','false')}
        symbols=dict(imageBase=base,header=header,packable=packable,barrier=barrier)
        switch=None
        if profile.startswith('table'):
            switch=read_union_switch(image,wrapper.name,wrappers=wrappers)
            need('actual-slot5-dispatcher',entry,int(switch['dispatcherVa'],16))
            need('bounded-table-entry-domain',list(range(count)),[r['tag']for r in switch['entries']])
            cases=switch['entries'];table=int(switch['tableVa'],16)
        else:cases=[dict(tag=tag)for tag in range(count)]
        programs=[]
        for selected in cases:
            tag=selected['tag'];table_entry=None
            if switch is not None:
                slot=table+4*tag;word=image.pe.u32_at_va(slot)
                need('actual-unsigned-table-target',base+word,int(selected['targetVa'],16))
                table_entry=dict(rva=slot-base,rawHex=word.to_bytes(4,'little').hex().upper(),targetRva=word)
                program=table_program(body['regions'],entry,symbols,profile=profile,tag=tag,count=count,
                    hot=hot,table=table,selected=int(selected['bodyVa'],16))
            else:program=pair_program(body['regions'],entry,symbols,profile=profile,tag=tag)
            usage=derive_typed_usage_context(image,program['childUsage']['instruction']-base,label=LABEL+'.child')
            arguments=usage['methodArguments'];need('one-actual-child-argument',1,len(arguments))
            child=by_name[arguments[0]]
            if switch is not None:need('same-table-and-source-wrapper',selected['wrapperName'],child.name)
            typed=bind_typed_read(image,usage,method_name='ReadPackable',argument=child.name,kind=18,reference=True)
            need('actual-owned-packable-definition',reference['packableContext']['packableDefinition'],typed['methodDefinition'])
            programs.append(dict(tag=tag,wrapperName=child.name,wrappedType=child.wrapped_type,
                source=program,typedRequest=usage,typedArgument=typed,tableEntry=table_entry,
                originalLineage=_lineage(ctx,md,child.wrapped_type,original),
                wrapperLineage=_lineage(ctx,md,child.name,wrapper.name),concreteGrammarAdmitted=False))
        options=dict(profile=profile,tag=0,ff=True)
        if switch is not None:
            options.update(count=count,hot=hot,table=table,selected=int(cases[0]['bodyVa'],16))
        null=(table_program if switch is not None else pair_program)(body['regions'],entry,symbols,**options)
        pair=derive_pair(image,original,wrapper.name)
        def prove_forwarder(selected_image,selected_pair,selected_wrapper):
            face,=selected_pair['composition']['interfaces']
            need('selected-owned-base-formatter',(wrapper.name,fm.index),(selected_wrapper.name,face['formatterDeserializeMethodIndex']))
            return dict(ownedWindows=body['windows'],slot5Method=fm.index,programs=programs,canonicalFF=null)
        adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=prove_forwarder)
        getter=pointer.methods(image,wrapper)['GetValue'];getter_entry=image.method_pointer_va(getter)
        getter_proof=pointer.leaf(image,getter_entry,['488B4110','C3'])
        holder=_wrapper_holder(ctx,image,wrapper)
        need('base-original-holder',(original,16),(holder['declaredType'],holder['offset']))
        need('abstract-union-wrapper',128,md.types[wrapper.type_definition].flags&128)
        face,=pair['composition']['interfaces'];section=md.sections['interfaceOffsets'];joins=[]
        conversion_entry=base+adapter['canonicalRoutes']['symbolRvas']['conversion'];conversion=pointer.owned(image,conversion_entry)
        for route in programs:
            child=by_name[route['wrapperName']];td=md.types[child.type_definition]
            child_holder=_wrapper_holder(ctx,image,child)
            need('same-derived-base-holder',(original,16),(child_holder['declaredType'],child_holder['offset']))
            start=section.offset+td.interface_offsets_start*8
            interfaces=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8]))
            found=[(ordinal,offset)for ordinal,(index,offset)in enumerate(interfaces)if index==face['interfaceTypeIndex']]
            need('one-derived-base-interface',1,len(found));ordinal,offset=found[0]
            _vtable(image,child.type_definition,offset,getter.index,LABEL+'.baseGetter')
            converted=adapters.conversion(conversion['regions'],conversion_entry,
                base+adapter['canonicalRoutes']['conversionPrepareRva'],getter_entry,ordinal=ordinal)
            joins.append(dict(wrapperName=child.name,interfaceOrdinal=ordinal,interfaceOffset=offset,
                interfaceTypeIndex=face['interfaceTypeIndex'],baseGetValueMethod=getter.index,
                holder=child_holder,conversion=converted))
        result[family]=dict(typeName=original,wrapperName=wrapper.name,slot5Method=[fm.index,formatter_name,'Deserialize',entry-base],
            ownedWindows=body['windows'],programs=programs,canonicalFF=null,switch=switch,
            headerWindows=hs['windows'],headerPrograms=headers,pair=pair,adapter=adapter,baseHolder=holder,
            baseGetValue=getter_proof,derivedOriginalConversions=joins,baseGetterSemanticsAdmitted=True,
            concreteGetterSemanticsAdmitted=False,concreteFactorySemanticsAdmitted=False,
            concreteChildGrammarAdmitted=False,wholeUnionAdmitted=False)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(status='validated-reference-union-callers-and-base-adapters',nativeInputs=pins,
        families=result,referencePackable=reference,barrier=barrier_proof,concreteChildGrammarAdmitted=False,
        wholeSkillDataAdmitted=False,evidenceBoundary=dict(exact='Selected current initialized short-tag/FF callers, actual closed ReadPackable requests, complete output/barrier/return paths, base adapter/slot5/holder GetValue and each derived inherited-interface conversion.',
            conditional=__doc__+' Matching initialized canonical base adapters, concrete/list callbacks and coherent MethodInfos; normal helper/provider/collector effects and valid disjoint buffered storage.',
            unresolved=['concrete child grammars','existing-output alternatives','reserved markers','runtime provider/inflation selection','refill/malformed paths','whole owners']))))

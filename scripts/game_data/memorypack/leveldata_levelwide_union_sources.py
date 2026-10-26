"""Exact two-route LevelWide source and inherited reference conversion."""
import json,struct
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.leveldata_levelwide_records import DOCK_CONFIG,RAFT_CONFIG

TYPE='Beyond.Gameplay.LevelWideConfig'
CHILDREN={0:DOCK_CONFIG,1:RAFT_CONFIG}


def need(check,condition):
    if not condition:raise ValueError('levelwideUnion.'+check)


def program(regions,entry,*,tag=0,existing=False,ff=False):
    need('literal-finite-path',type(tag)is int and tag in(0,1)and type(existing)is type(ff)is bool)
    g=BytesPath(regions,entry);symbols={}
    def call(role):
        target=g.relative('e8');need('same-helper-'+role,role not in symbols or symbols[role]==target);symbols[role]=target
    g.take('48895c2408','4889742418','57','4883ec20');ready=g.relative('803d');g.take('00','498bf0','488bda');g.branch('0f84',False)
    g.take('33ff','488d542438','488bcb','66897c2438');call('header');g.take('84c0');g.branch('0f84',ff)
    comparison=None;usage=None
    if ff:
        g.take('48893e');g.jump('e9');g.take('488bce');call('barrier');g.jump('eb',1)
    else:
        g.take('0fb77c2438','6685ff');g.branch('75',tag==1,1)
        if tag==1:g.take('6683ff01');g.branch('0f85',False)
        g.take('488b0e','4885c9');g.branch('74',not existing,1)
        if existing:
            at=g.at;comparison=dict(instruction=at,cell=g.relative('488b15'))
            g.take('488b09');call('assignable');g.take('84c0');g.branch('74',True,1)
        at=g.at;usage=dict(instruction=at,cell=g.relative('488b15'))
        g.take('488bcb');call('packable')
        if tag==0:g.take('488906','488bce')
        else:g.take('488bce','488906')
        call('barrier')
        if tag==0:g.jump('eb',1)
        else:g.jump('e9')
    g.take('488b5c2430','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyCell=ready,tag=None if ff else tag,canonicalFF=ff,
        existingIncompatibleWrapper=existing,childUsage=usage,comparisonTypeUsage=comparison,symbols=symbols,
        sameReader=True,sameOutput=True,outputInitiallyNull=not existing and not ff,clearedOutputBytes=8 if ff else 0,
        entryRspRestored=True,normalReturn=True,compatibleExistingOutputAdmitted=False,concreteGrammarAdmitted=False)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,_vtable
    from scripts.game_data.memorypack import pointer_param as pointer,reference_adapter_sources as reference
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _wrapper_holder,_fast_barrier
    from scripts.game_data.memorypack.scalar_param_native import reader_offsets
    from scripts.game_data.memorypack.module_structure_models import enclosing_header
    from scripts.game_data.memorypack.union_dispatch import read_union_switch
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()};wrapper=wrappers[TYPE]
    switch=read_union_switch(image,wrapper.name,wrappers={w.type_definition:w for w in wrappers.values()})
    need('exact-two-nominal-routes',switch['entryCount']==2 and [(r['tag'],r['wrapperName'])for r in switch['entries']]==
        [(tag,wrappers[name].name)for tag,name in CHILDREN.items()])
    entry=int(switch['dispatcherVa'],16);body=pointer.owned(image,entry);paths=[]
    core=json.loads((CONTRACTS_DIR/'npc_runtime_native.json').read_bytes());need('same-packable-native-inputs',core['nativeInputs']==pins)
    packable=base+core['readPackable']['entryRva']
    for tag,name in CHILDREN.items():
        for existing in(False,True):
            p=program(body['regions'],entry,tag=tag,existing=existing)
            usage=derive_typed_usage_context(image,p['childUsage']['instruction']-base,label='levelwideUnion.child')
            typed=bind_typed_read(image,usage,method_name='ReadPackable',argument=wrappers[name].name,kind=18,reference=True)
            need('same-actual-typed-reader',p['symbols']['packable']==packable)
            if existing:
                compared=derive_typed_usage_context(image,p['comparisonTypeUsage']['instruction']-base,label='levelwideUnion.comparison')
                need('same-actual-typed-comparison',compared.get('tag')==1 and compared.get('typeName')==wrappers[name].name)
            paths.append(dict(tag=tag,typeName=name,wrapperName=wrappers[name].name,source=p,typedRequest=usage,typedArgument=typed))
    null=program(body['regions'],entry,ff=True);symbols=paths[0]['source']['symbols'];header=pointer.owned(image,symbols['header'])
    need('same-all-actual-header-and-barrier',all(
        p['source']['symbols']['header']==symbols['header']and p['source']['symbols']['barrier']==symbols['barrier']for p in paths)
        and null['symbols']['header']==symbols['header']and null['symbols']['barrier']==symbols['barrier'])
    headers={mode:enclosing_header(header['regions'],header['pointer'],reader_offsets(image,'levelwideUnion'),marker=mode)for mode in('short','false')}
    barrier=_fast_barrier(image,symbols['barrier'])
    pair=derive_pair(image,TYPE,wrapper.name)
    def forwarder(selected_image,selected_pair,selected_wrapper):
        face,=selected_pair['composition']['interfaces'];method=md.methods[face['formatterDeserializeMethodIndex']]
        need('actual-owned-union-slot5',selected_wrapper.name==wrapper.name and image.method_pointer_va(method)==entry)
        return dict(ownedWindows=body['windows'],programs=paths,canonicalFF=null)
    adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=forwarder)
    getter=pointer.methods(image,wrapper)['GetValue'];getter_entry=image.method_pointer_va(getter)
    getter_proof=pointer.leaf(image,getter_entry,['488B4110','C3']);holder=_wrapper_holder(ctx,image,wrapper)
    need('own-base-holder',holder['declaredType']==TYPE and holder['offset']==16)
    face,=pair['composition']['interfaces'];section=md.sections['interfaceOffsets'];conversions=[]
    conversion_entry=base+adapter['canonicalRoutes']['symbolRvas']['conversion'];conversion=pointer.owned(image,conversion_entry)
    for tag,name in CHILDREN.items():
        child=wrappers[name];td=md.types[child.type_definition];start=section.offset+td.interface_offsets_start*8
        interfaces=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8]))
        matches=[(ordinal,offset)for ordinal,(index,offset)in enumerate(interfaces)if index==face['interfaceTypeIndex']]
        need('one-owned-inherited-interface',len(matches)==1);ordinal,offset=matches[0]
        _vtable(image,child.type_definition,offset,getter.index,'levelwideUnion.baseGetter')
        transferred=reference.conversion(conversion['regions'],conversion_entry,
            base+adapter['canonicalRoutes']['conversionPrepareRva'],getter_entry,ordinal=ordinal)
        child_holder=_wrapper_holder(ctx,image,child)
        need('derived-same-base-holder',child_holder['declaredType']==TYPE and child_holder['offset']==16)
        conversions.append(dict(tag=tag,typeName=name,interfaceOrdinal=ordinal,interfaceOffset=offset,holder=child_holder,program=transferred))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(nativeInputs=pins,typeName=TYPE,wrapperName=wrapper.name,
        switch=switch,programs=paths,canonicalFF=null,codeWindows=body['windows'],
        sourceRegions=[[at-base,raw.hex()]for at,raw in body['regions']],headerPrograms=headers,headerWindows=header['windows'],
        pair=pair,adapter=adapter,baseGetter=getter_proof,baseHolder=holder,conversions=conversions,barrier=barrier,
        concreteGrammarAdmitted=False,wholeOwnerAdmitted=False)))

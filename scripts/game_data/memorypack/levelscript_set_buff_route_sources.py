"""Set<BuffPtr>'s actual nested SetBuff union and complete concrete source.

The outer ActionBase tag selects a nominal Set wrapper, whose own slot-five
formatter reads another union header. Only the actual tag-zero SetBuff child
and canonical FF paths are admitted, with initially null output, independent
child grammar, nominal carrier/ancestry and canonical base conversion proof.
"""
import json,struct
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.Actions.Set`1<Beyond.Gameplay.Core.BuffPtr>'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Actions_Set_Beyond_Gameplay_Core_BuffPtr_ForMemoryPack'
CHILD='Beyond.MemoryPack.Beyond_Gameplay_Actions_SetBuffForMemoryPack'
CAP_SCHEMA='endfield.generated-actionmap-nested-set-route-capability.v1'


def need(check,condition):
    if not condition:raise ValueError('nestedSetBuff.'+check)


def select(image,family,tag):
    if family!='ActionBase':return None
    from scripts.game_data.memorypack.union_dispatch import read_union_switch
    wrappers={w.type_definition:w for w in image.memorypack_wrappers.values()}
    switch=read_union_switch(image,'Beyond_Gameplay_Actions_ActionBaseForMemoryPack',wrappers=wrappers)
    entries=[r for r in switch['entries']if r['tag']==tag]
    if len(entries)!=1 or entries[0]['wrapperName']!=WRAPPER:return None
    entry=entries[0];wrapper=wrappers[entry['typeDefinition']]
    need('actual-finite-outer-case',wrapper.wrapped_type==TYPE)
    from scripts.game_data.memorypack.levelscript_action_route_sources import _declaration
    return dict(family=family,tag=tag,**_declaration(wrapper),unionIdentity=dict(dispatcherVa=switch['dispatcherVa'],
        tableVa=switch['tableVa'],entryCount=switch['entryCount'],**entry))


def union_program(regions,entry,*,ff,child_null=False):
    need('literal-path',type(ff)is bool and type(child_null)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2418','56','4883ec20','33ed','498bd8');flag=g.relative('40382d')
    g.take('488bf2');g.branch('75',True,1)
    g.take('488d542438','66896c2438','488bce');header=g.relative('e8');g.take('84c0');g.branch('74',ff,1)
    usage=child=hook=None
    if ff:g.take('48892b')
    else:
        g.take('66396c2438');g.branch('74',True,1)
        g.take('488b0b','4885c9');g.branch('74',True,1)
        usage=g.at;g.relative('488b15');g.take('488bce');child=g.relative('e8');g.take('488903');g.jump('eb',1)
    g.take('488bcb');barrier=g.relative('e8')
    g.take('488b0b','4885c9');g.branch('74',ff or child_null,1)
    if not(ff or child_null):g.take('33d2');hook=g.relative('e8')
    g.take('488b5c2430','488b6c2440','4883c420','5e','c3')
    return dict(selectedBytes=g.seen,canonicalFF=ff,childNull=child_null,childContextSite=usage,
        childTarget=child,headerTarget=header,barrierTarget=barrier,hookTarget=hook,
        initializedFlag=flag,initiallyNullOutputRequired=True,sameReaderAndOutput=True,
        entryRspRestored=True,allNonvolatilesRestored=True)


def hook_program(regions,entry,s,*,cached,base_null):
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20','33db','488bf9');flag=g.relative('381d');g.branch('75',True,1)
    g.take('48395f20');g.branch('75',cached,1);usages=[]
    if not cached:
        g.take('48395f10');g.branch('74',base_null,1)
        if not base_null:
            g.take('488b5f10');at=g.at;cell=g.relative('488b15');usages.append((at,cell))
            g.take('488bcb');g.call(s['cast']);g.take('48894720','488bcb');at=g.at;cell=g.relative('488b15');usages.append((at,cell))
            need('same-nominal-hook-cast-class',usages[0][1]==cell)
            g.call(s['cast']);g.take('488d4f20');g.call(s['barrier'])
    g.take('488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,cached=cached,baseNull=base_null,classUsages=usages,
        initializedFlag=flag,serializedFieldWrites=0,baseHolderWrites=0,cacheOffset=32,completeFrameRestored=True)


def derive(image,pins,route):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_extent
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,_vtable
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack.levelscript_action_route_components import compile_route,SCHEMA
    from scripts.game_data.memorypack import generated_reader_sources,levelscript_action_param_registry as registry_owner,pooled_source_helper
    from scripts.game_data.memorypack.levelscript_action_route_sources import _declaration
    from scripts.game_data.memorypack.module_structure_models import enclosing_header
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack import reference_adapter_sources as adapters
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    wrappers={w.name:w for w in image.memorypack_wrappers.values()};wrapper=wrappers[WRAPPER];child=wrappers[CHILD]
    mm=pointer.methods(image,wrapper)
    need('actual-nested-reference-wrapper',wrapper.wrapped_type==TYPE and child.wrapped_type=='Beyond.Gameplay.Actions.SetBuff'
        and ctx.parent(CHILD)==WRAPPER and not wrapper.wrapped_is_value_type)
    carrier=closed_generic_reference_extent(ctx,mm['GetValue'].return_type)
    child_td=ctx.index.types[child.wrapped_type];parent=closed_generic_reference_extent(ctx,child_td.parent_index)
    need('exact-nominal-constructed-parent',parent['type']==carrier['type']==TYPE
        and parent['argumentTypes']==carrier['argumentTypes']==['Beyond.Gameplay.Core.BuffPtr'])
    formatter,=image.named_type_definitions[WRAPPER+'+'+WRAPPER.rsplit('.',1)[-1]+'Formatter']
    fm,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize']
    need('own-slot5-ABI',not fm.flags&16 and fm.slot==5 and fm.parameter_count==2 and ctx.type_name(fm.return_type)=='void')
    _vtable(image,formatter.index,5,fm.index,'nestedSetBuff')
    for p,n,k in zip(md.parameters_for(fm),('MemoryPack.MemoryPackReader',WRAPPER),(17,18),strict=True):
        need('own-slot5-byrefs',ctx.type_name(p.type_index)==n and image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)[10:12]==bytes((k,32)))
    body=pointer.owned(image,image.method_pointer_va(fm))
    paths=[union_program(body['regions'],body['pointer'],ff=True),
        *[union_program(body['regions'],body['pointer'],ff=False,child_null=v)for v in(False,True)]]
    actual=paths[1];usage=derive_typed_usage_context(image,actual['childContextSite']-base,label='nestedSetBuff.child')
    typed=bind_typed_read(image,usage,method_name='ReadPackable',argument=CHILD,kind=18,reference=True)
    readers=reference_reader_abi(image,pins)
    from scripts.game_data.contracts import CONTRACTS_DIR
    core=json.loads((CONTRACTS_DIR/'npc_runtime_native.json').read_bytes())
    need('own-actual-reference-packable',core['nativeInputs']==pins
        and actual['childTarget']-base==core['readPackable']['entryRva']
        and typed['methodDefinition']==readers['genericReaders']['packableContext']['packableDefinition'])
    header=pointer.owned(image,actual['headerTarget']);offsets=scalar.reader_offsets(image,'nestedSetBuff')
    headers=[enclosing_header(header['regions'],header['pointer'],offsets,marker=v)for v in('short','extended','false')]
    barrier,barrier_proof,_=_fast_barrier(image,actual['barrierTarget'])
    need('actual-own-hook-call',actual['hookTarget']==image.method_pointer_va(mm['OnDeserialized']))
    hook=pointer.owned(image,actual['hookTarget']);cast=next(control_transfer(r)['target']for r in hook['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8'and r['text'].startswith('call ')and int(r['va'],16)>hook['pointer']+60)
    hooks=[hook_program(hook['regions'],hook['pointer'],dict(cast=cast,barrier=actual['barrierTarget']),cached=c,base_null=n)
        for c,n in((True,False),(False,True),(False,False))]
    for hp in hooks:
        for site,cell in hp['classUsages']:
            cu=derive_typed_usage_context(image,site-base,label='nestedSetBuff.hookClass')
            need('hook-cast-exact-closed-Original',cu['tag']==1 and cu['typeName']==TYPE)
    pair=derive_pair(image,TYPE,WRAPPER)
    def forwarder(selected_image,selected_pair,selected_wrapper):
        face,=selected_pair['composition']['interfaces']
        need('same-own-registered-formatter',selected_image is image and selected_wrapper.name==WRAPPER and face['formatterDeserializeMethodIndex']==fm.index)
        return dict(ownedWindows=body['windows'],slot5Method=fm.index,programs=paths,headers=headers)
    adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=forwarder)
    source_batch=generated_reader_sources.derive_many(image,pins,[CHILD]);outcome,=source_batch['owners']
    need('complete-own-concrete-child',outcome['status']=='complete-reader-source-proved');source=outcome['proof']
    getter=mm['GetValue']
    from scripts.game_data.memorypack.reference_param_profile import _getter_windows
    from scripts.game_data.memorypack.modelview_reference_sources import get_value
    windows,entry_proof=_getter_windows(image,md.types[wrapper.type_definition],getter)
    own_getter=mm['get___instance'];own_target=image.method_pointer_va(own_getter)
    need('actual-own-GetValue-getter-tail',entry_proof['kind']=='owned-zero-context-getter-tail'
        and entry_proof['targetMethod'][0]==own_getter.index and entry_proof['targetMethod'][3]+base==own_target)
    scalar.owned_method_abi(image,ctx,own_getter.index,wrapper.type_definition,(TYPE,21,True),[],'nestedSetBuff.getter')
    owned_getters=[s['getter']for s in source['setters']if s['method'][1]==WRAPPER]
    need('complete-own-constructed-getter',len(owned_getters)==2 and all(g['method'][0]==own_getter.index
        and g['baseHolder'][2]==16 and g['typedCache'][2]==32 and g['refreshAdmitted']is True
        and g['closedReferenceCarrier']['type']==TYPE for g in owned_getters))
    need('hook-same-independently-proved-compatible-cast',all(
        g['compatibleRefresh']['cast']['targetRva']+base==cast
        and g['compatibleRefresh']['cast']['program']['conditionalUnchangedCompatibleReference']is True
        and g['compatibleRefresh']['barrierTargetRva']+base==actual['barrierTarget']for g in owned_getters))
    getter_proof=dict(windows=windows,entry=entry_proof,ownedGetter=owned_getters[0],program=get_value(
        [(image.method_pointer_va(getter),bytes.fromhex(entry_proof['instructionHex']))],image.method_pointer_va(getter),getter=own_target))
    face,=pair['composition']['interfaces'];section=md.sections['interfaceOffsets'];td=md.types[child.type_definition]
    start=section.offset+td.interface_offsets_start*8;interfaces=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8]))
    matches=[(i,off)for i,(index,off)in enumerate(interfaces)if index==face['interfaceTypeIndex']]
    need('one-derived-base-interface',len(matches)==1);ordinal,slot=matches[0]
    _vtable(image,child.type_definition,slot,getter.index,'nestedSetBuff.derivedBaseGetter')
    conversion_target=base+adapter['canonicalRoutes']['symbolRvas']['conversion'];conversion=pointer.owned(image,conversion_target)
    converted=adapters.conversion(conversion['regions'],conversion_target,base+adapter['canonicalRoutes']['conversionPrepareRva'],image.method_pointer_va(getter),ordinal=ordinal)
    names=sorted({r['declaredType']for r in source['orderedSourceReads']if r['declaredType'].startswith('Beyond.Gameplay.Actions.Param`1<')})
    registry=registry_owner.derive(image,pins,parameter_types=names)
    children,requests=registry_owner.bind_parents(image,pins,source,registry)
    pooled={str(r['memberIndex']):pooled_source_helper.validate_on_image(image,base+r['sourceTargetRva'],pins)
        for r in source['orderedSourceReads']if r['kind']=='byte-payload'}
    child_route=dict(family=route['family'],tag=0,**_declaration(child),
        unionIdentity=dict(dispatcherVa=hex(body['pointer']),tag=0,wrapperName=CHILD,typedRequest=usage,
            initializedTagZeroProgram=actual))
    cap,pending=compile_route(route,source,pins,param_children=children,typed_requests=requests,pooled_sources=pooled,source_route=child_route)
    need('all-child-grammars-closed',cap is not None and not pending)
    cap.update(schema=CAP_SCHEMA,nestedUnion=dict(tag=0,wrapperName=CHILD,typeName=child.wrapped_type,canonicalFFAdmitted=True,
        shortAndExtendedTagsAdmitted=True,initiallyNullOutputRequired=True))
    from scripts.game_data.codecs.levelscript.current_set_buff_route import validate
    validate(cap);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated',nativeInputs=pins,family=route['family'],tag=route['tag'],
        wrapperName=WRAPPER,capability=cap,wholeOwnerAdmitted=False,
        proof=dict(outerUnionCase=route['unionIdentity'],closedCarrier=carrier,childParent=parent,typedRequest=usage,typedChild=typed,
            ownFormatter=dict(method=fm.index,windows=body['windows'],programs=paths),headerWindows=header['windows'],headerPrograms=headers,
            hookWindows=hook['windows'],hooks=hooks,baseAdapter=adapter,baseGetValue=getter_proof,derivedConversion=converted,
            referenceReader=readers,barrier=barrier,barrierProgram=barrier_proof,concreteSource=source,paramChildren=children))))

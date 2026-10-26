"""Actual typed BuffId8/Query16 ReadValue sources, separate from wire grammar.

Only the two exact selected nominal values below enter this component. BuffId
returns a complete QWORD in RAX; Query uses a hidden16 result and reference lane8,
including its independently owned enum padding. Actual Reader/provider bodies,
closed MVAR contexts, selected canonical adapter comparison and complete
getter/default transfers are freshly joined. Neither an actual source entry
nor a registered entry is assigned another pointer's body. Normal compatible
ready contexts, matching canonical callbacks, noninterfering helpers and
disjoint buffered storage remain conditions. The caller still proves its
argument last-writes, field transfer, frame and separate nominal wire child;
runtime provider choice and enclosing framing/EOF remain unresolved.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

BUFF_ID='Beyond.Gameplay.Core.BuffId'
QUERY='Beyond.Gameplay.Core.GameplayTagQuery'
TYPES={BUFF_ID:(8,'rax','488B15'),QUERY:(16,'hidden-local','4C8B05')}


def request_shape(usage):
    args=usage.get('methodArguments',[])
    need('nominal-value-read-finite-type',True,isinstance(args,list)and len(args)==1 and args[0]in TYPES)
    name=args[0];size,result,prefix=TYPES[name]
    need('nominal-value-read-actual-ReadValue',(6,'MemoryPack.MemoryPackReader','ReadValue',[]),
        tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments')))
    need('nominal-value-read-literal-definition',True,isinstance(usage.get('methodSpec'),list)and len(usage['methodSpec'])==3
        and type(usage['methodSpec'][0])is int and usage['methodSpec'][0]>0)
    raw=bytes.fromhex(usage.get('instructionHex',''))
    need('nominal-value-read-owned-MethodInfo-register',True,len(raw)==7 and raw[:3].hex().upper()==prefix)
    return name,size,result


def _provider(image,body,s,*,inline_only=False):
    """Three exact existing byte profiles; no registration/body alias."""
    from scripts.game_data.memorypack import buff_ptr_sources,managed_value16_read_sources as hidden
    from scripts.game_data.memorypack.skill_root_buff_id_transfer import provider_program
    from scripts.game_data.memorypack import pooled_global_buff_id_sources as value8
    candidates=[]
    profiles=[('inline-short',dict(typeHandle=52,backend=79,indexed=96,assignable=116),hidden.provider_program)]
    if not inline_only:profiles.extend((
        ('inline-near',dict(typeHandle=56,backend=87,indexed=104,assignable=120),provider_program),
        ('called-cast',dict(typeHandle=52,backend=79,indexed=96,cast=107),value8.compared_provider)))
    errors=[]
    for name,offsets,program in profiles:
        try:
            symbols=dict(s)
            for role,offset in offsets.items():
                actual=buff_ptr_sources._call(body,offset)
                if role=='typeHandle':need('nominal-provider-same-TypeFromHandle',s['typeHandle'],actual)
                symbols[role]=actual
            proof=program(body['regions'],body['pointer'],symbols)
            candidates.append(dict(profile=name,program=proof,symbols=symbols))
        except (ValueError,KeyError,IndexError)as error:errors.append(dict(profile=name,reason=str(error)[:500]))
    if len(candidates)!=1:raise ValueError('nominalValueRead.provider-profile: expected=one exact profile actual='+str(dict(matches=len(candidates),profiles=errors))[:1800])
    return candidates[0]


def _selected_classes(image,body,program):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    chosen={at for at,h in program['selectedBytes']};uses=[]
    for row in body['rows']:
        at=int(row['va'],16);raw=bytes.fromhex(row['bytes'])
        if at in chosen and len(raw)==7 and raw[:3]==b'\x48\x8b\x0d':
            uses.append(derive_typed_usage_context(image,at-image.pe.image_base,label='nominalValueRead.class'))
    return uses


def derive(image,pins,*,typed_request,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources
    from scripts.game_data.memorypack import pooled_global_buff_id_sources as value8
    from scripts.game_data.memorypack import managed_value16_read_sources as hidden
    from scripts.game_data.memorypack.skill_root_buff_id_transfer import adapter8_program
    _publication_gate(image,pins);name,size,result=request_shape(typed_request);base=image.pe.image_base
    need('nominal-value-literal-source-target',True,type(source_target)is int and source_target>base)
    typed=buff_ptr_sources._typed_context(image,typed_request,name,GenericEntries(image));read=pointer.owned(image,source_target)
    if name==QUERY:
        from scripts.game_data.memorypack.skill_root_tag_query_sources import derive as child_source
        from scripts.game_data.memorypack.skill_root_tag_query_transfer import derive as transfer_source
        child=child_source(image,pins);provider_target=buff_ptr_sources._call(read,60);dispatch_target=buff_ptr_sources._call(read,79)
        adapter=transfer_source(image,pins,typed_request=typed_request,dispatcher_target=dispatch_target,child=child)
    else:
        from scripts.game_data.memorypack.skill_root_buff_id_sources import derive as child_source
        from scripts.game_data.memorypack.skill_root_buff_id_transfer import derive as transfer_source
        child=child_source(image,pins);adapter=transfer_source(image,pins,child=child)
        calls=[]
        for i,row in enumerate(read['rows']):
            if i and bytes.fromhex(row['bytes'])[:1]==b'\xe8':calls.append((bytes.fromhex(read['rows'][i-1]['bytes']).hex(),control_transfer(row)['target']))
        providers=[target for previous,target in calls if previous=='488b09'];dispatchers=[target for previous,target in calls if previous=='488bd0']
        need('nominal-buffid-one-provider-source',1,len(providers));need('nominal-buffid-one-dispatch-source',1,len(dispatchers))
        provider_target,=providers;dispatch_target,=dispatchers
    need('nominal-value-own-child-type',name,child['typeName']);need('nominal-value-owned-managed-layout',size,child['layout']['managedBytes'])
    need('nominal-value-own-transfer-type',name,adapter['typeName']);need('nominal-value-own-transfer-inputs',pins,adapter['nativeInputs'])
    sources=dict(read=read,provider=pointer.owned(image,provider_target),dispatch=pointer.owned(image,dispatch_target))
    symbols={role:base+rva for role,rva in adapter['symbolRvas'].items()};symbols.update(provider=provider_target,dispatch=dispatch_target)
    if name==QUERY:
        actual_read=buff_ptr_sources.read16_program(read['regions'],source_target,symbols)
        need('nominal-query-same-dispatch-prepare',symbols['prepare'],buff_ptr_sources._call(sources['dispatch'],37))
        paths=adapter['paths']['dispatch']
    else:
        actual_read=value8.value8_program(read['regions'],source_target,symbols)
        need('nominal-buffid-same-dispatch-prepare',symbols['prepare'],buff_ptr_sources._call(sources['dispatch'],33))
        paths=[adapter8_program(sources['dispatch']['regions'],dispatch_target,symbols,dispatch=True,**path)
            for path in({},{'create':False},{'null':True})]
    provider=_provider(image,sources['provider'],symbols,inline_only=name==QUERY)
    if provider['profile']=='called-cast':
        cast=pointer.owned(image,provider['symbols']['cast'])
        targets={control_transfer(r)['target']for r in cast['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8'}
        need('nominal-value-one-compatible-cast-predicate',1,len(targets));predicate,=targets
        provider['castPrograms']=[value8.successful_cast(cast['regions'],cast['pointer'],predicate,null=n)for n in(False,True)]
        provider['castWindows']=cast['windows']
    read_classes=_selected_classes(image,read,actual_read)
    need('nominal-value-actual-reader-provider-class',[(1,'MemoryPack.MemoryPackFormatterProvider')],[(c['tag'],c['typeName'])for c in read_classes])
    provider_classes=_selected_classes(image,sources['provider'],provider['program'])
    need('nominal-value-actual-provider-class-roles',[(1,'System.Type'),(1,'MemoryPack.MemoryPackFormatterProvider')],
        [(c['tag'],c['typeName'])for c in provider_classes])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-nominal-value-read-sources.v1',status='proved-conditional-typed-nominal-value-read',
        nativeInputs=pins,typeName=name,wrapperName=child['wrapperName'],managedBytes=size,readMethod='ReadValue',
        readerMethodDefinition=typed_request['methodSpec'][0],sourceTargetRva=source_target-base,
        actualSourceProved=True,resultAbi=result,resultRegister='rax',referenceLaneOffset=0 if name==BUFF_ID else 8,
        wireGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,providerSelectionObserved=False,
        proof=dict(typedRequest=typed_request,typedContext=typed,childSource=child,adapter=adapter,readerProgram=actual_read,
            providerProgram=provider,dispatchPaths=paths,readerProviderClasses=read_classes,providerClasses=provider_classes,
            actualSourceWindows={role:body['windows']for role,body in sources.items()},
            actualComparedCanonicalAdapterRva=adapter['symbolRvas']['adapter'],actualReaderRegisteredPointerEqualityInferred=False),
        evidenceBoundary=dict(exact='Fresh exact BuffId8/RAX or padded Query16/hidden ABI, typed ReadValue context and actual complete source/provider/dispatcher programs, nominal canonical adapter/default/GetValue conversion.',
            conditional=__doc__,structuralOnly='Nominal managed output representation only.',
            unresolved=['separate child wire grammar','actual enclosing argument/field/frame transfer','live provider/callback selection','cold/refill/error paths','whole owner/physical EOF']))))

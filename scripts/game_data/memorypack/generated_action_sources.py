"""Current generated action source scopes with explicit unproved child joins.

Names/order come from current generated metadata; read ABI and call/setter flow
come from complete selected native families. Historical tags/windows/read-order
labels are never inputs. A source scope does not by itself admit a child,
entry/factory/setter implementation, an action union route or a whole owner.
"""
from __future__ import annotations
import json
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
from scripts.game_data.buff_frontiers_regenerate import _method_row,_static_usage_bytes
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import buff_ec_profiles_native as ec,generated_header_sources,generated_member_sources,generated_primitive_sources,pooled_source_helper,primitive_param,scalar_param_native as scalar
from scripts.game_data.skill_timeline_routes_regenerate import reference_primitives

LABEL='generatedActionSource'


def need(k,e,a):scalar.need(LABEL,k,e,a)


def _contexts(image,rows):
    """All register loads; only complete mapped virtual-only cells are skipped."""
    chosen=[];skipped=[];custom=[];base=image.pe.image_base
    for row in rows:
        raw=ec.raw(row)
        if len(raw)==7 and raw[0]in(0x48,0x4c)and raw[1]==0x8b and raw[2]&0xc7==5:
            cell=ec.va(row)+7+int.from_bytes(raw[3:],'little',signed=True)
            if _static_usage_bytes(image.pe,cell)is None:
                skipped.append(dict(instructionRva=ec.va(row)-base,cellRva=cell-base,
                    reason='complete mapped virtual-only cell has no static MethodSpec token'))
                continue
            usage_raw=_static_usage_bytes(image.pe,cell)
            try:ec.method_spec_usage_index(usage_raw,image.registration['methodSpecsCount'],source=LABEL,offset=cell)
            except ValueError:usage_raw=None
            if raw[:3]==bytes.fromhex('4c8b05')and usage_raw is not None:
                from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
                usage=derive_typed_usage_context(image,ec.va(row)-base,label=LABEL+'.context')
                if(usage.get('typeName'),usage.get('methodName'))==('Beyond.SerializeFieldDictionary`2','DeserializeV2'):
                    from scripts.game_data.memorypack import animation_extra_dictionary_sources as extra
                    if tuple(usage.get('classArguments',[]))in extra.DOMAINS:
                        request_context=extra.request_context
                    else:
                        from scripts.game_data.memorypack.skill_gait_dictionary_sources import request_context
                    custom.append(request_context(image,ec.va(row)-base));continue
        chosen.append(row)
    return sorted(ec.contexts(image,chosen,allow_value_generic_arguments=True)+custom,key=lambda c:c['instructionRva']),skipped


def _claim(image,wrapper):
    ctx=NativeReferenceContext(image);members=[];order=[];enum_proofs=[]
    for member in wrapper.members:
        name,declared=member.name,member.declared_type
        if declared=='bool':kind='byte'
        elif declared in('int','uint'):kind='scalar32'
        elif declared in('long','ulong'):kind='scalar64'
        elif declared=='byte':kind='raw-byte'
        elif declared=='float':kind='raw4'
        elif declared=='double':kind='float64'
        elif declared=='string':kind='byte-payload'
        elif ctx.is_enum(declared):
            td=ctx.index.types[declared]
            fields=[f for f in image.metadata.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
            need('enum-one-instance-backing',1,len(fields));field=fields[0]
            backing=ctx.type_name(field.type_index)
            enum_kinds={'int':(8,'scalar32'),'uint':(9,'scalar32'),'long':(10,'scalar64'),
                'ulong':(11,'scalar64'),'byte':(5,'raw-byte')}
            need('enum-owned-supported-backing',True,image.metadata.string(field.name_index)=='value__'and backing in enum_kinds)
            scalar.ordinary(image,ctx.type_pointer(field.type_index),enum_kinds[backing][0],LABEL+'.enum')
            enum_proofs.append(dict(typeName=declared,typeDefinition=td.index,backingType=backing,
                backingTypeRawHex=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16).hex().upper()))
            kind=enum_kinds[backing][1]
        elif declared in('UnityEngine.LayerMask','Beyond.Gameplay.Core.GameplayTag','Beyond.Audio.AudioId'):kind='value4:'+declared
        elif declared in('UnityEngine.Vector2','UnityEngine.Vector2Int','Beyond.Gameplay.AI.EnemyCheckAIMarker+EnemyCheckAIMarkerInfo','Beyond.Gameplay.Core.CharInteractPerform.HandIKParams'):kind='value8:'+declared
        elif declared in('UnityEngine.Vector3','UnityEngine.Vector3Int'):kind='value12:'+declared
        elif declared=='UnityEngine.Quaternion':kind='value16:'+declared
        elif declared=='UnityEngine.Color':kind='value16:'+declared
        elif declared=='Beyond.AABB':
            from scripts.game_data.memorypack.generated_aabb_field_sources import owns_member
            need('exact-own-AABB-field',True,owns_member(wrapper.wrapped_type,name,declared))
            kind='value16:'+declared
        elif declared in('Beyond.Gameplay.View.CameraControlStateInitialParam','Beyond.PosRot'):kind='value24:'+declared
        elif declared in('Beyond.Montage.AnimationClipAsyncInfo','Beyond.Gameplay.TrackingBounds'):kind='value36:'+declared
        elif declared=='Beyond.Gameplay.Core.TriggerShapeData':kind='value44:'+declared
        elif declared in('Beyond.Gameplay.Core.BuffId','Beyond.Gameplay.Core.GlobalBuffId','Beyond.Gameplay.Core.GameplayTagQuery','Beyond.LangKey','Beyond.Gameplay.Core.SmartTargetSelectSetting','Cinemachine.CinemachineImpulseManager+EnvelopeDefinition','Beyond.Gameplay.BodyTypeDef','Beyond.Gameplay.View.Animation.AlphaBlend','Beyond.FAnimationCurve','Beyond.Gameplay.Core.EntityPtr','Beyond.Gameplay.Core.SkMorphPlaySetting'):kind='managed:'+declared
        elif declared=='System.Nullable`1<float>':kind='constructed:'+declared
        elif declared in('sbyte','short','ushort','char'):raise ValueError(LABEL+'.unsupported-primitive-source:'+declared)
        elif not ctx.is_value_type(declared):kind='reference:'+declared
        else:raise ValueError(LABEL+'.unsupported-value-source:'+declared)
        members.append(dict(name=name,declaredType=declared));order.append(kind)
    return dict(profile=wrapper.name,ownerType=wrapper.name,methodName='Deserialize',
        members=members,anonymousReadOrder=order),enum_proofs


def _events(image,claim,path,contexts,reader,targets):
    base=image.pe.image_base;by_context={base+c['instructionRva']:c for c in contexts}
    calls=[];used=set();events=[];requirements=[]
    for i,row in enumerate(path):
        if row['text']==f'mov rax, [{reader}+{ec.source_offsets(image)["currentPtr"]:#x}]':
            raise ValueError(LABEL+'.unsupported-inline-source')
        flow=control_transfer(row);argument=ec.last_write(path,i,'rcx')
        if argument and argument['text']==f'mov rcx, {reader}'and flow['kind']in('call','indirectCall','registerCall'):
            need('direct-reader-call','call',flow['kind']);calls.append((i,row,flow['target']))
    need('one-source-per-current-member',len(claim['members']),len(calls))
    for index,((i,row,target),member,kind)in enumerate(zip(calls,claim['members'],claim['anonymousReadOrder'])):
        load=ec.last_write(path,i,'rdx');context=by_context.get(ec.va(load))if load else None
        declared=member['declaredType'];expected=None;width=None
        primitive=targets.get('_memberPrimitive',{}).get(index)
        if primitive is not None:expected=base+primitive['targetRva'];width=primitive['wireBytes']
        elif kind=='byte':expected=targets['bool'];width=1
        elif kind=='scalar32':expected=targets['int32'];width=4
        elif kind=='raw4':expected=targets['float32'];width=4
        elif kind=='byte-payload':expected=targets['string'];width=4
        elif kind.startswith('value4:'):
            fact=targets['value4'][declared];expected=base+fact['targetRva'];width=4
            need('value4-owned-context',True,context is not None)
            need('value4-reader-definition',fact['readerMethodDefinition'],context['methodSpec'][0])
        else:
            need('reference-owned-context',True,context is not None)
            need('reference-context-kind',True,context['typeKind']in(18,21))
            need('reference-ordinary-reference',False,bool(bytes.fromhex(context['argumentRawHex'])[11]&0x80))
            need('reference-reader-method',True,context['methodName']in('ReadValue','ReadPackable'))
            expected=base+targets[context['methodName']]['targetRva']
            requirements.append(dict(memberIndex=index,fieldName=member['name'],typeName=declared,
                readMethod=context['methodName'],methodDefinition=context['methodSpec'][0],
                sourceTargetRva=target-base,context=context,positiveGrammarAdmitted=False))
        need('actual-source-target',expected,target)
        if context is not None:
            need('typed-context-full-owner-and-type',('MemoryPack.MemoryPackReader',declared),
                (context['methodOwner'],context['fullTypeName']))
            if width is not None:
                declared_kinds={'bool':2,'byte':5,'int':8,'uint':9,'long':10,'ulong':11,'float':12,'double':13}
                expected_kind=declared_kinds.get(declared,17)
                need('primitive-context',('ReadUnmanaged',expected_kind),(context['methodName'],context['typeKind']))
            used.add(context['instructionRva'])
        elif NativeReferenceContext(image).is_enum(declared):
            raise ValueError(LABEL+'.enum-requires-owned-context:'+declared)
        event=dict(memberIndex=index,fieldName=member['name'],declaredType=declared,kind=kind,
            instruction=ec.site(row,base),sourceTargetRva=target-base)
        if width is not None:event['wireBytes']=width
        if context is not None:event['context']=context
        events.append(event)
    need('all-owned-contexts-bound',{c['instructionRva']for c in contexts},used)
    return events,requirements


def _prepare(image,pins):
    base=image.pe.image_base
    reference=json.loads((CONTRACTS_DIR/'skill_custom_root_motion_native.json').read_bytes())
    need('primitive-source-build',pins,reference['nativeInputs'])
    primitive=reference_primitives(reference);targets=ec.clone_facts(image,pins)
    targets.update(bool=base+primitive['bool'],int32=base+primitive['int32'],string=base+primitive['bytes'])
    targets['_primitiveCache']={}
    targets['_richScopeCache']={}
    for key,kind in(('bool','bool'),('int32','int32')):
        targets['_primitiveCache'][(kind,targets[key])]=generated_primitive_sources.derive(image,targets[key],kind,ec.source_offsets(image))
    pooled_source_helper.validate_on_image(image,targets['string'],pins)
    ec.validate_on_image(image,pins)
    fact=json.loads(ec.CONTRACT_PATH.read_bytes())
    barrier={p['headerProof']['referenceBarrierTargetRva']for p in fact['proof']['profiles']}
    need('one-current-null-barrier',1,len(barrier))
    barrier=next(iter(barrier))
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack import buff_gameplay_tag_native,buff_layer_mask_native
    collector=_barrier(image,base+barrier)
    targets['_disabledCollectorFlagRva']=collector['result']['disabledFlagRva']
    targets['value4']={}
    for owner in(buff_gameplay_tag_native,buff_layer_mask_native):
        proved=owner.validate_on_image(image,pins)
        need('atomic4-source',('validated',4,'eax'),tuple(proved[k]for k in('status','wireBytes','resultRegister')))
        targets['value4'][proved['typeName']]=proved
    return targets,barrier,collector['result']['disabledFlagRva']


def _primitive_sources(image,claim,path,reader,targets,offsets,*,contexts=None,pins=None):
    """Each current member is joined to the actual complete primitive callee."""
    calls=[]
    for i,row in enumerate(path):
        if ec.raw(row)[:1]!=b'\xe8':continue
        argument=ec.last_write(path,i,'rcx')
        if argument is not None and argument['text']==f'mov rcx, {reader}':
            calls.append(row)
    need('primitive-member-call-count',len(claim['members']),len(calls))
    modes={'byte':'bool','raw-byte':'raw-byte','scalar32':'int32','scalar64':'int64','raw4':'float32','float64':'float64'}
    proved={};cache=targets['_primitiveCache']
    for index,(kind,row)in enumerate(zip(claim['anonymousReadOrder'],calls)):
        if kind in('value8:UnityEngine.Vector2','value8:Beyond.Gameplay.AI.EnemyCheckAIMarker+EnemyCheckAIMarkerInfo','value4:Beyond.Audio.AudioId'):
            from scripts.game_data.memorypack import skill_vector2_source,nominal_int32_value_sources,skill_ai_marker_value_sources
            position=next(i for i,r in enumerate(path)if ec.va(r)==ec.va(row))
            load=ec.last_write(path,position,'rdx')
            request=next((c for c in contexts or[]if load is not None and
                image.pe.image_base+c['instructionRva']==ec.va(load)),None)
            need('named-value-current-context',True,request is not None and pins is not None)
            target=control_transfer(row)['target']
            derive=(skill_vector2_source.derive if kind=='value8:UnityEngine.Vector2'else
                skill_ai_marker_value_sources.derive if kind=='value8:'+skill_ai_marker_value_sources.TYPE else nominal_int32_value_sources.derive)
            proved[index]=derive(image,pins,context=request,source_target=target)
            continue
        if kind not in modes:continue
        mode=modes[kind];target=control_transfer(row)['target'];key=(mode,target)
        if key not in cache:cache[key]=generated_primitive_sources.derive(image,target,mode,offsets)
        proved[index]=cache[key]
    return proved


def _derive_ec_rich_scope(image,pins,wrapper,targets,barrier,disabled_flag,claim,enums,method,family,windows,rows,header_proof,path,error):
    """Fresh reviewed EC source kinds plus complete generic field/program flow."""
    from scripts.game_data.memorypack.generated_inline_reader_sources import complete_program
    base=image.pe.image_base;reviewed=json.loads(ec.CONTRACT_PATH.read_bytes())
    selected=[c for c in reviewed['claims']if c['ownerType']==wrapper.name and c['profile']in('member13','member8','member3')]
    if len(selected)!=1:raise error
    need('rich-reviewed-current-members',selected[0]['members'],claim['members'])
    cache=targets['_richScopeCache']
    if not cache:
        projection=json.loads(ec.PROJECTION_PATH.read_bytes());actual,projected=ec.derive(image,pins,reviewed,projection)
        need('rich-current-role-proof',reviewed,actual);need('rich-current-role-projection',projection,projected)
        cache.update({p['method'][1]:p for p in actual['proof']['profiles']})
    profile=cache[wrapper.name]
    need('rich-same-owned-source',True,profile['method']==method and profile['family']==family and profile['selectedProgram']==[ec.site(r,base)for r in path])
    contexts,skipped=_contexts(image,rows);events=[];requirements=[]
    for index,(member,kind,event)in enumerate(zip(claim['members'],claim['anonymousReadOrder'],profile['events'],strict=True)):
        event=dict(event,memberIndex=index,fieldName=member['name'],declaredType=member['declaredType'])
        if kind.startswith('reference:'):
            event['kind']=kind;context=event['context'];raw=bytes.fromhex(context['argumentRawHex'])
            need('rich-ordinary-reference',True,context['typeKind']in(18,21)and not raw[11]&128 and context['fullTypeName']==member['declaredType'])
            target=control_transfer(next(r for r in path if ec.site(r,base)==event['instruction']))['target'];event['sourceTargetRva']=target-base
            requirement=dict(memberIndex=index,fieldName=member['name'],typeName=member['declaredType'],readMethod=context['methodName'],methodDefinition=context['methodSpec'][0],sourceTargetRva=target-base,context=context,positiveGrammarAdmitted=False,sourceMode=event['mode'])
            if event['mode']=='typed-provider-slot-five':requirement.update(dispatchTargetRva=target-base,providerCallTargetRva=event['providerCallTargetRva'])
            requirements.append(requirement)
        else:need('rich-exact-primitive-source-kind',kind,event['kind'])
        events.append(event)
    inventory=list(image.memorypack_wrappers.values());wrappers={w.name:w for w in inventory};need('rich-unique-wrapper-inventory',len(inventory),len(wrappers));getter_cache={}
    setters=[generated_member_sources.direct_field_binding(image,m,wrappers)for m in wrapper.members]
    program=complete_program(rows,path,events,setters,contexts,reader=header_proof['readerRegister'],output=header_proof['outputRegister'],offsets=ec.source_offsets(image),base=base,disabled_flag=disabled_flag,provider=targets['providerTarget'],dispatch=targets['dispatchTarget'])
    return dict(schema='endfield.generated-action-source-scope.v2',nativeInputs=dict(pins),wrapperName=wrapper.name,wrappedType=wrapper.wrapped_type,memberCount=len(events),claim=claim,method=method,family=family,codeWindows=windows,headerProof=header_proof,enumBackings=enums,contexts=contexts,skippedRuntimeCells=skipped,events=events,childRequirements=requirements,
        primitiveSources={},setterTransfers=[],richProgram=program,richSetters=setters,
        sourceRoleContract=ec.CONTRACT_PATH.name,selectedProgram=[ec.site(r,base)for r in path],selectedConditions=profile['selectedConditions'],
        sourceScopeAdmitted=True,wholeWrapperAdmitted=False,positiveGrammarAdmitted=False,
        evidenceBoundary='Fresh required EC semantic role proves actual selected source kinds/context/read order. Complete generic selected instruction/value flow independently joins every field to current metadata-owned setter and conditional disabled collector. Entry/allocation/lifecycle, child grammar and ordinary original adapter/provider selection remain independent.')


def _derive(image,pins,wrapper_name,targets,barrier,disabled_flag):
    base=image.pe.image_base;wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==wrapper_name]
    claim,enums=_claim(image,wrapper);need('nonempty-byte-member-count',True,0<len(claim['members'])<250)
    targets=dict(targets);offsets=ec.source_offsets(image)
    method=_method_row(image,[0,wrapper_name,'Deserialize',1])
    primitive_param.reader_abi(image,NativeReferenceContext(image),image.metadata.methods[method[0]],wrapper)
    from scripts.game_data.memorypack.generated_owned_code_sources import source_family
    family,windows,rows,partition=source_family(image,pins,entry_rva=method[3])
    need('complete-family-decoded',False,any(r['text'].startswith('db ')for r in rows))
    result=_derive_current_family(image,pins,wrapper,targets,barrier,disabled_flag,claim,enums,method,family,windows,rows,offsets,owned_partition=partition)
    if partition is not None:result['ownedCodePartition']=partition
    return result


def _derive_current_family(image,pins,wrapper,targets,barrier,disabled_flag,claim,enums,method,family,windows,rows,offsets,*,owned_partition=None):
    base=image.pe.image_base;wrapper_name=wrapper.name;count=len(claim['members'])
    header_proof,header=generated_header_sources.derive(image,rows,base+method[3],count,offsets,barrier,disabled_flag=disabled_flag,owned_partition=owned_partition)
    reader=header_proof['readerRegister']
    if any(kind.startswith(('managed:','constructed:','value36:','value44:'))or kind in('value8:UnityEngine.Vector2Int','value24:Beyond.PosRot')
            or member['declaredType']=='Beyond.SerializeFieldDictionary`2<Beyond.Gameplay.Core.MovementComponent+GroundedMoveGait,float>'
            for kind,member in zip(claim['anonymousReadOrder'],claim['members'],strict=True)):
        from scripts.game_data.memorypack.generated_inline_value_scope import derive_scope as inline_scope
        from scripts.game_data.memorypack.generated_value_programs import complete_program
        return inline_scope(image,pins,wrapper,targets,barrier,claim,enums,method,family,windows,rows,header_proof,header,program_prover=complete_program)
    if any(kind.startswith(('value12:','value16:','value24:'))for kind in claim['anonymousReadOrder']):
        from scripts.game_data.memorypack.generated_vector_member_sources import derive_scope
        return derive_scope(image,pins,wrapper,targets,barrier,claim,enums,method,family,windows,rows,header_proof,header)
    try:path,choices=ec.fast_path(rows,header,reader,offsets,terminal_target=base+barrier)
    except ValueError:
        from scripts.game_data.memorypack.generated_inline_value_scope import derive_scope as inline_scope
        from scripts.game_data.memorypack.generated_value_programs import complete_program
        return inline_scope(image,pins,wrapper,targets,barrier,claim,enums,method,family,windows,rows,header_proof,header,program_prover=complete_program)
    try:
        contexts,skipped=_contexts(image,rows)
        targets['_memberPrimitive']=_primitive_sources(image,claim,path,reader,targets,offsets,contexts=contexts,pins=pins)
        events,requirements=_events(image,claim,path,contexts,reader,targets)
    except ValueError as error:
        try:return _derive_ec_rich_scope(image,pins,wrapper,targets,barrier,disabled_flag,claim,enums,method,family,windows,rows,header_proof,path,error)
        except(ValueError,KeyError,IndexError):
            from scripts.game_data.memorypack.generated_inline_value_scope import derive_scope as inline_scope
            from scripts.game_data.memorypack.generated_value_programs import complete_program
            return inline_scope(image,pins,wrapper,targets,barrier,claim,enums,method,family,windows,rows,header_proof,header,program_prover=complete_program)
    setter_targets=[image.method_pointer_va(image.metadata.methods[m.method_index])for m in wrapper.members]
    try:
        transfers=generated_member_sources.call_transfers(rows,events,setter_targets,base,
            normal_path=path,reader=reader,output=header_proof['outputRegister'])
    except(ValueError,KeyError,IndexError):
        inventory=list(image.memorypack_wrappers.values());wrappers={w.name:w for w in inventory}
        need('unique-inline-transfer-wrapper-inventory',len(inventory),len(wrappers));getter_cache={}
        setter_proofs=[generated_member_sources._derive_setter(image,m,wrappers,barrier,getter_cache,pins=pins)for m in wrapper.members]
        try:
            transfers=generated_member_sources.call_transfers(rows,events,setter_targets,base,
                normal_path=path,reader=reader,output=header_proof['outputRegister'],setter_proofs=setter_proofs,barrier=base+barrier)
        except(ValueError,KeyError,IndexError):
            from scripts.game_data.memorypack.generated_value_programs import complete_program
            terminal=base+barrier if control_transfer(path[-1])['kind']=='jump'else None
            program=complete_program(rows,path,events,setter_proofs,contexts,reader=reader,output=header_proof['outputRegister'],base=base,barrier=base+barrier,terminal_target=terminal,disabled_collector=base+disabled_flag)
            result=dict(schema='endfield.generated-action-source-scope.v2',nativeInputs=dict(pins),wrapperName=wrapper.name,wrappedType=wrapper.wrapped_type,
                memberCount=count,claim=claim,method=method,family=family,codeWindows=windows,headerProof=header_proof,enumBackings=enums,contexts=contexts,skippedRuntimeCells=skipped,
                events=events,childRequirements=requirements,primitiveSources={str(i):p for i,p in targets['_memberPrimitive'].items()},
                setterTransfers=[],richProgram=program,richSetters=setter_proofs,selectedProgram=[ec.site(r,base)for r in path],
                sourceScopeAdmitted=True,wholeWrapperAdmitted=False,positiveGrammarAdmitted=False,
                evidenceBoundary='Every current selected read/argument/getter/source-bit-slice/named-field/barrier/return instruction is independently owned by the complete symbolic source program. Each actual source and named setter is freshly derived. Entry/lifecycle, full nonvolatile frame and child grammar remain separate required joins.')
            if terminal is not None:result['referenceBarrierTargetRva']=barrier
            return result
    sites={base+e['instruction'][0]for e in events}
    for transfer in transfers:
        sites.update(base+site[0]for site in transfer.get('actualCalls',[transfer['setterCall']]if 'setterCall'in transfer else[]))
    need('complete-normal-source-setter-call-set',sites,{ec.va(r)for r in path if control_transfer(r)['kind']in('call','indirectCall','registerCall')})
    result=dict(schema='endfield.generated-action-source-scope.v1',nativeInputs=dict(pins),wrapperName=wrapper_name,
        wrappedType=wrapper.wrapped_type,memberCount=count,claim=claim,method=method,family=family,
        codeWindows=windows,headerProof=header_proof,enumBackings=enums,contexts=contexts,
        skippedRuntimeCells=skipped,events=events,childRequirements=requirements,
        setterMethods=image.setter_methods(image.metadata.types[wrapper.type_definition],parameter='typeName',label=LABEL),
        primitiveSources={str(i):p for i,p in targets['_memberPrimitive'].items()},setterTransfers=transfers,
        selectedProgram=[ec.site(r,base)for r in path],
        selectedConditions=[dict(instruction=ec.site(c['instruction'],base),condition=c['condition'],taken=c['taken'])for c in choices],
        sourceScopeAdmitted=True,wholeWrapperAdmitted=False,positiveGrammarAdmitted=False,
        pendingReasons=['entry/factory and named setter implementations require independent ownership proof']+
            ['member='+str(r['memberIndex'])+':child='+r['typeName']for r in requirements],
        evidenceBoundary='Exact current complete native source families and selected existing-wrapper member/read/typed-context/return-to-setter scope, plus actual header FF helper/clear/return. Child grammar, complete entry/allocation/factory/setter implementations, enclosing union selection and whole owners remain unproved. No historical windows, anonymous read order, numeric tag or original-pair registration selects this scope.')
    if control_transfer(path[-1])['kind']=='jump':result.update(schema='endfield.generated-action-source-scope.v2',referenceBarrierTargetRva=barrier)
    return result


def derive(image,pins,wrapper_name):
    _publication_gate(image,pins);targets,barrier,disabled_flag=_prepare(image,pins)
    result=_derive(image,pins,wrapper_name,targets,barrier,disabled_flag)
    _publication_gate(image,pins)
    return json.loads(json.dumps(result))


def derive_many(image,pins,wrapper_names):
    """One same-image source preparation; retain exact per-owner refusals."""
    if len(wrapper_names)!=len(set(wrapper_names))or len(wrapper_names)>512:
        raise ValueError(LABEL+'.unique-bounded-owners-required')
    _publication_gate(image,pins);targets,barrier,disabled_flag=_prepare(image,pins);rows=[]
    for name in wrapper_names:
        try:rows.append(dict(status='source-scope-proved',proof=_derive(image,pins,name,targets,barrier,disabled_flag)))
        except(ValueError,KeyError,IndexError,TypeError)as error:
            rows.append(dict(status='pendingReview',wrapperName=name,reason=str(error)[:2400]))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(nativeInputs=pins,owners=rows,wholeCatalogAdmitted=False)))

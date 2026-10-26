"""Interleaved current inline value macros and typed Reader member calls.

The caller supplies the common complete source-to-field program prover. Macro
capture is independently checked here, while source-bit transfer, lifecycle,
full frame and child byte grammar remain separately composed obligations.
"""
from scripts.game_data.memorypack import generated_inline_value_sources as inline

LABEL='generatedInlineValueScope'

def need(k,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+k+':'+str(detail)[:800])

def nominal_layout(image,ctx,name):
    from scripts.game_data.memorypack import generated_vector_member_sources as vectors,scalar_param_native as scalar
    if name=='Beyond.AABB':
        from scripts.game_data.memorypack.generated_aabb_field_sources import layout
        return layout(image,ctx)
    if name=='Beyond.PosRot':
        from scripts.game_data.memorypack.generated_posrot_field_sources import layout
        return layout(image,ctx)
    if name in('Beyond.Gameplay.TrackingBounds','Beyond.Gameplay.Core.TriggerShapeData'):
        from scripts.game_data.memorypack.generated_outer_value_field_sources import layout
        return layout(image,ctx,name)
    if name=='UnityEngine.Color':
        from scripts.game_data.memorypack.unity_color_sources import layout
        return layout(image,ctx)
    if name=='Beyond.Gameplay.View.CameraControlStateInitialParam':
        from scripts.game_data.memorypack.skill_camera_initial_raw_sources import layout
        return layout(image,ctx)
    if name=='Beyond.Montage.AnimationClipAsyncInfo':
        from scripts.game_data.memorypack.generated_animation_clip_field_sources import layout
        return layout(image,ctx)
    if name!='UnityEngine.Vector2':return vectors.layout(image,ctx,name)
    td=ctx.index.types[name];md=image.metadata
    need('current-vector2-value',ctx.is_value_type(name)and td.generic_container_index<0)
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[(md.string(f.name_index),*ctx.field(name+'::'+md.string(f.name_index))[1:])for f in fields]
    need('current-vector2-axes',actual==[('x','float',16),('y','float',20)])
    for f in fields:scalar.ordinary(image,ctx.type_pointer(f.type_index),12,LABEL+'.layout')
    need('current-vector2-size-index',0<=td.index<image.registration['typeDefinitionsSizesCount'])
    at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    need('current-vector2-size',(image.pe.u32_at_va(at),image.pe.u32_at_va(at+4))==(24,8))
    return dict(typeName=name,typeDefinition=td.index,fields=actual,managedBytes=8,wireReadAdmitted=False)


def bind_vector2_source(event,setter,source,layout,pins,*,base):
    from scripts.game_data.memorypack.skill_vector2_source import bind
    context=event.get('context',{});raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('own-typed-Vector2-register-source',event.get('kind')=='value8:UnityEngine.Vector2'
        and event.get('declaredType')==layout.get('typeName')=='UnityEngine.Vector2'
        and event.get('mode')=='typed-register-vector2'and event.get('resultAbi')=='rax'
        and event.get('actualSourceProved')is True and event.get('wireBytes')==layout.get('managedBytes')==setter.get('storedBytes')==8
        and layout.get('fields')==[('x','float',16),('y','float',20)]
        and type(layout.get('typeDefinition'))is int and context.get('typeDefinition')==layout['typeDefinition']
        and len(raw)==16 and raw[10:12]==bytes((17,128))and int.from_bytes(raw[:8],'little')==layout['typeDefinition']
        and source.get('nativeInputs')==pins and source.get('typeDefinition')==layout['typeDefinition']
        and source.get('proof',{}).get('layout')==dict(fields=[dict(name=n,typeName='float',boxedOffset=o)
            for n,o in(('x',16),('y',20))],nativeBytes=8,boxedBytes=24))
    bind(context,base+event['sourceTargetRva'],source,base=base)
    return True

def vector_param_array_source(image,pins,wrapper,member,event,context,target):
    """Only the actual MakeList<Vector3> Param-reference array request."""
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import levelscript_vector_param_array_sources as arrays
    base=image.pe.image_base;raw=bytes.fromhex(context.get('argumentRawHex',''))
    need('finite-vector-Param-array-member',wrapper.wrapped_type==arrays.PARENT and wrapper.name==arrays.WRAPPER
        and member.name=='_list'and member.declared_type==arrays.TYPE and event.get('memberIndex')==7
        and event.get('kind')=='reference:'+arrays.TYPE
        and(context.get('methodOwner'),context.get('methodName'),context.get('fullTypeName'),context.get('typeKind'),context.get('register'))==
            ('MemoryPack.MemoryPackReader','ReadArray',arrays.ELEMENT,21,'rdx')
        and len(raw)==16 and raw[10:12]==bytes((21,0)))
    usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL+'.vectorParamArray')
    need('same-actual-vector-Param-array-usage',all(usage.get(k)==context.get(k)for k in('instructionRva','instructionHex','methodSpec')))
    at,h=event['instruction'];call=bytes.fromhex(h)
    need('actual-vector-Param-array-E8',len(call)==5 and call[0]==232
        and at+5+int.from_bytes(call[1:],'little',signed=True)==target-base)
    source=arrays.derive_source(image,pins,typed_request=usage,call_target=target,count_limit=4096)
    need('independent-vector-Param-array-source',arrays.validate_source(source,pins)==base
        and source['typedRequest']==usage and source['arrayReaderTargetRva']==target-base
        and source['arrayReaderMethodDefinition']==context['methodSpec'][0])
    return source


def derive_scope(image,pins,wrapper,targets,barrier,claim,enums,method,family,windows,rows,header_proof,header,*,program_prover):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import generated_action_sources as actions,generated_member_sources as members
    from scripts.game_data.memorypack import generated_primitive_sources as primitives,generated_vector3_source as vector3
    from scripts.game_data.memorypack import generated_cached_access_sources as cached
    ec=members.ec;base=image.pe.image_base;ctx=NativeReferenceContext(image);offsets=ec.source_offsets(image)
    reader=header_proof['readerRegister'];output=header_proof['outputRegister']
    inventory={w.name:w for w in image.memorypack_wrappers.values()};cache={}
    setters=[members._derive_setter(image,m,inventory,barrier,cache,pins=pins)for m in wrapper.members]
    accesses=cached.collect_programs(rows,setters)
    last_setter_target=base+setters[-1]['method'][3]
    zero_prover=None
    if header_proof.get('ordinaryZeroFamily')is not None:
        from scripts.game_data.memorypack.generated_header_sources import _owned_zero_source
        def zero_prover(sites,register):
            return _owned_zero_source(rows,base+method[3],sites,register,base,header_proof['ordinaryZeroFamily'])
    path,choices,macros=inline.fast_path(rows,header,reader,offsets,output=output,terminal_target=base+barrier,
        cached_accesses=accesses,final_setter_target=last_setter_target,zero_prover=zero_prover,
        disabled_collector=base+targets['_disabledCollectorFlagRva'])
    by_macro={p['guardInstructionVa']:p for p in macros}
    macro_instructions={ec.va(row)for macro in macros for row in inline.selected_rows(rows,macro)}
    contexts,skipped=actions._contexts(image,rows)
    by_context={base+c['instructionRva']:c for c in contexts};candidates=[]
    from scripts.game_data.memorypack import generated_module_frame_sources as module_frames
    module_frame=module_frames.descriptor(wrapper.wrapped_type,header_proof)if module_frames.owns(wrapper.wrapped_type)else None
    module_sources={displacement for register,displacement in module_frames.source_addresses(module_frame)if register=='rcx'}if module_frame else set()
    for i,row in enumerate(path):
        if ec.va(row)in by_macro:candidates.append((i,row,by_macro[ec.va(row)]));continue
        if ec.va(row)in macro_instructions:continue
        if members.control_transfer(row)['kind']!='call':continue
        rcx=ec.last_write(path,i,'rcx');rdx=ec.last_write(path,i,'rdx')
        trigger='value44:Beyond.Gameplay.Core.TriggerShapeData'in claim['anonymousReadOrder']
        module_source=module_frame is not None and rcx is not None and rcx['text']in{
            'lea rcx, [rbp'+('+'if n>=0 else'-')+hex(abs(n))+']'for n in module_sources}
        if rcx is not None and(rcx['text']==f'mov rcx, {reader}'or(rcx['text'].startswith('lea rcx, [rsp+')or trigger and rcx['text']in('lea rcx, [rbp-0x9]','lea rcx, [rbp-0x19]')or module_source)and rdx is not None and rdx['text']==f'mov rdx, {reader}'):
            candidates.append((i,row,None))
    need('exact-member-source-bijection',len(candidates)==len(wrapper.members),(len(candidates),len(wrapper.members)))
    primitive_modes={'byte':'bool','raw-byte':'raw-byte','scalar32':'int32','scalar64':'int64','raw4':'float32','float64':'float64'}
    inline_widths={'raw-byte':1,'scalar32':4,'scalar64':8,'raw4':4,'float64':8,'value4:Beyond.Gameplay.Core.GameplayTag':4,'value4:UnityEngine.LayerMask':4,
        'value8:UnityEngine.Vector2':8,'value12:UnityEngine.Vector3':12,'value12:UnityEngine.Vector3Int':12,'value16:UnityEngine.Quaternion':16,'value16:UnityEngine.Color':16,
        'value24:Beyond.Gameplay.View.CameraControlStateInitialParam':24,'value24:Beyond.PosRot':24,'value36:Beyond.Montage.AnimationClipAsyncInfo':36}
    events=[];requirements=[];primitive_sources={};inline_sources={};array_sources={};values={};managed_values={};constructed_values={};static_references={};used=set()
    for n,((position,row,macro),member,kind)in enumerate(zip(candidates,wrapper.members,claim['anonymousReadOrder'],strict=True)):
        event=dict(memberIndex=n,fieldName=member.name,declaredType=member.declared_type,kind=kind,instruction=ec.site(row,base))
        if macro is not None:
            need('explicit-inline-nominal-kind',kind in inline_widths and macro['wireBytes']==inline_widths[kind]and setters[n]['storedBytes']==macro['wireBytes'],(n,kind,macro['wireBytes']))
            event.update(mode='buffered-inline-value'if kind.startswith('value')else'buffered-inline-scalar',wireBytes=macro['wireBytes'],inlineSourceProgram=macro)
            if macro.get('independentAdvanceSourceRequired'):
                from scripts.game_data.memorypack.generated_called_advance_sources import derive as derive_advance
                color=kind=='value16:UnityEngine.Color'
                vector=kind=='value12:UnityEngine.Vector3'
                integer_vector=kind=='value12:UnityEngine.Vector3Int'
                initial24=kind=='value24:Beyond.Gameplay.View.CameraControlStateInitialParam'
                posrot24=kind=='value24:Beyond.PosRot'
                clip36=kind=='value36:Beyond.Montage.AnimationClipAsyncInfo'
                need('finite-called-advance-kind',kind in('scalar32','value4:Beyond.Gameplay.Core.GameplayTag','value4:UnityEngine.LayerMask')and macro['wireBytes']==4
                    or color and macro['wireBytes']==16 and macro.get('completeSourceBitsSpilledBeforeAdvance')is True
                    or vector and macro['wireBytes']==12 and(macro.get('preservedCaptureRegistersRequired')==['xmm6','r14']
                        or macro.get('preservedCaptureRegistersRequired')==['xmm6','rsi']and macro.get('actualReaderArgument')=='rdi'
                            and macro.get('wrapperLoad',{}).get('outputRegister')=='r14')
                    or integer_vector and macro['wireBytes']==12 and macro.get('preservedCaptureRegistersRequired')in(['rbp'],['rsi'])
                        and macro.get('completeLowEightSpilledBeforeAdvance')is True
                    or initial24 and macro['wireBytes']==24 and macro.get('preservedCaptureRegistersRequired')==['xmm6','xmm7']
                    or posrot24 and wrapper.wrapped_type=='Beyond.Gameplay.EncounterData+IntroPart'
                        and macro['wireBytes']==24 and macro.get('preservedCaptureRegistersRequired')==['xmm6','xmm7']
                    or clip36 and macro['wireBytes']==36 and macro.get('preservedCaptureRegistersRequired')==['xmm6','rbp','xmm7'])
                cache=targets.setdefault('_actualAdvanceCache',{});target=macro['advanceTargetVa']
                if target not in cache:cache[target]=derive_advance(image,pins,target=target,offsets=offsets)
                event.update(mode='buffered-called-advance-posrot24'if posrot24 else'buffered-called-advance-clip36'if clip36 else'buffered-called-advance-color16'if color else'buffered-called-advance-value12'if vector else'buffered-called-advance-int-vector12'if integer_vector else'buffered-called-advance-initial24'if initial24 else'buffered-called-advance-scalar',actualSourceProved=True,inlineAdvanceSource=cache[target])
                if posrot24:
                    from scripts.game_data.memorypack.generated_posrot_field_sources import validate_event
                    layout=nominal_layout(image,ctx,member.declared_type);event['inlineNominalLayout']=layout
                    validate_event(event,setters[n])
                if clip36:
                    from scripts.game_data.memorypack.generated_animation_clip_field_sources import validate_event
                    layout=nominal_layout(image,ctx,member.declared_type);event['inlineNominalLayout']=layout
                    validate_event(event,setters[n])
                if initial24:
                    from scripts.game_data.memorypack.generated_initial24_capture_sources import validate_nominal
                    layout=nominal_layout(image,ctx,member.declared_type);event['inlineNominalLayout']=layout
                    validate_nominal(event,setters[n])
                if color:
                    layout=nominal_layout(image,ctx,member.declared_type)
                    need('independent-current-Color-setter-layout',layout==setters[n].get('nominalValueLayout')and layout['managedBytes']==16
                        and layout['referenceLaneOffsets']==layout['paddingByteRanges']==[])
                    event['inlineNominalLayout']=layout
                if vector:
                    layout=nominal_layout(image,ctx,member.declared_type)
                    raw=bytes.fromhex(setters[n]['parameterTypeRecordHex'])
                    need('independent-current-called-Vector3-layout',layout['managedBytes']==12 and len(raw)==16
                        and raw[10:12]==bytes((17,128))and int.from_bytes(raw[:8],'little')==layout['typeDefinition'])
                    event['inlineNominalLayout']=layout
                if integer_vector:
                    layout=setters[n].get('nominalValueLayout',{});raw=bytes.fromhex(setters[n]['parameterTypeRecordHex'])
                    need('independent-current-called-Int3-layout',layout.get('schema')=='endfield.story-integer-vector-layout.v1'
                        and layout.get('typeName')==member.declared_type=='UnityEngine.Vector3Int'and layout.get('managedBytes')==12
                        and layout.get('referenceLaneOffsets')==layout.get('paddingByteRanges')==[]and layout.get('fieldCount')==3
                        and[(f['name'],f['declaredType'],f['managedOffset'],f['rawKind'])for f in layout.get('fields',[])]==
                            [('m_X','int',0,8),('m_Y','int',4,8),('m_Z','int',8,8)]
                        and len(raw)==16 and raw[10:12]==bytes((17,128))and int.from_bytes(raw[:8],'little')==layout['typeDefinition'])
                    event['inlineNominalLayout']=layout
                if kind.startswith('value4:'):
                    cap=targets['value4'][member.declared_type]
                    need('independent-current-inlined-named-four-byte-source',cap['nativeInputs']==pins and cap['typeName']==member.declared_type
                        and cap['status']=='validated'and cap['wireBytes']==4 and cap['resultRegister']=='eax'
                        and setters[n]['parameterTypeRecordHex'][20:24].upper()=='1180'
                        and int.from_bytes(bytes.fromhex(setters[n]['parameterTypeRecordHex'])[:8],'little')==cap['typeDefinition'])
                    event['inlineNamedValueSource']=cap
            if kind=='value16:UnityEngine.Color'or kind in('value12:UnityEngine.Vector3','value12:UnityEngine.Vector3Int','value24:Beyond.Gameplay.View.CameraControlStateInitialParam','value24:Beyond.PosRot','value36:Beyond.Montage.AnimationClipAsyncInfo')and macro.get('independentAdvanceSourceRequired'):
                values[str(n)]=dict(typeName=member.declared_type,layout=layout,sourceProgram=macro,advanceSource=event['inlineAdvanceSource'],
                    actualSourceProved=True,wireBytes=macro['wireBytes'],resultAbi='inline-bits-to-owned-field')
            elif kind.startswith('value')and not macro.get('independentAdvanceSourceRequired'):
                layout=nominal_layout(image,ctx,member.declared_type)
                need('separate-source-layout-width',macro['wireBytes']==layout['managedBytes'])
                values[str(n)]=dict(typeName=member.declared_type,layout=layout,sourceProgram=macro,actualSourceProved=True,wireBytes=macro['wireBytes'],resultAbi='inline-bits-to-owned-field')
            else:
                inline_sources[str(n)]=dict(program=macro,advanceSource=event['inlineAdvanceSource'],wireBytes=macro['wireBytes'])if macro.get('independentAdvanceSourceRequired')else macro
                if 'inlineNamedValueSource'in event:inline_sources[str(n)]['namedValueSource']=event['inlineNamedValueSource']
            events.append(event);continue
        target=members.control_transfer(row)['target'];event['sourceTargetRva']=target-base
        hidden=kind in('value12:UnityEngine.Vector3','value16:UnityEngine.Quaternion','value16:Beyond.AABB','value24:Beyond.Gameplay.View.CameraControlStateInitialParam','managed:Beyond.LangKey','managed:Beyond.Gameplay.Core.GameplayTagQuery','managed:Beyond.Gameplay.Core.SmartTargetSelectSetting','managed:Cinemachine.CinemachineImpulseManager+EnvelopeDefinition','managed:Beyond.Gameplay.BodyTypeDef','managed:Beyond.Gameplay.View.Animation.AlphaBlend','managed:Beyond.FAnimationCurve','value36:Beyond.Montage.AnimationClipAsyncInfo','managed:Beyond.Gameplay.Core.EntityPtr','value36:Beyond.Gameplay.TrackingBounds','value44:Beyond.Gameplay.Core.TriggerShapeData','managed:Beyond.Gameplay.Core.SkMorphPlaySetting')
        from scripts.game_data.memorypack import skill_gait_dictionary_sources as gait,animation_extra_dictionary_sources as extra_static
        static_owner=gait if member.declared_type==gait.TYPE else extra_static if member.declared_type in extra_static.TYPES else None
        static_out=static_owner is not None
        argument=ec.last_write(path,position,'r8'if hidden or static_out else'rdx');context=by_context.get(ec.va(argument))if argument is not None else None
        reference_array=context is not None and context['methodName']=='ReadArray'and member.declared_type==context['fullTypeName']+'[]'
        from scripts.game_data.memorypack.module_unmanaged_array_sources import owns_member as owns_primitive_array
        primitive_array=(owns_primitive_array(wrapper.wrapped_type,n,member.name,member.declared_type)and context is not None
            and context['methodName']=='ReadUnmanagedArray'and member.declared_type in('int[]','bool[]')
            and member.declared_type==context['fullTypeName']+'[]')
        if context is not None:
            need('exact-source-context-owner-type',context['methodOwner']==('Beyond.SerializeFieldDictionary`2'if static_out else'MemoryPack.MemoryPackReader')and(context['fullTypeName']==member.declared_type or reference_array or primitive_array),
                dict(memberIndex=n,fieldName=member.name,declaredType=member.declared_type,call=ec.site(row,base),context=context))
            event['context']=context;used.add(context['instructionRva'])
        if static_out:
            expected_mode='owned-static-out-gait-dictionary'if static_owner is gait else'owned-static-out-animation-extra-dictionary'
            need('explicit-owned-static-reference-context',context is not None and context.get('contextMode')==expected_mode
                and kind=='reference:'+member.declared_type and setters[n]['storedBytes']==8)
            cap=static_owner.derive(image,pins,context=context,source_target=target)
            event.update(mode='typed-static-out-reference',resultAbi='out-reference-local',actualSourceProved=True,referenceBytes=8,
                staticOutSourceBinding=dict(typeName=member.declared_type,sourceTargetRva=target-base,readerMethodDefinition=context['methodSpec'][0],
                    context=context,resultAbi=cap['resultAbi'],referenceBytes=8,actualSourceProved=True))
            static_owner.validate_event(event,setters[n]);static_references[str(n)]=cap
            requirements.append(dict(memberIndex=n,fieldName=member.name,typeName=member.declared_type,readMethod='DeserializeV2',
                methodDefinition=context['methodSpec'][0],sourceTargetRva=target-base,context=context,positiveGrammarAdmitted=False,
                sourceMode='typed-static-out-reference'))
        elif kind=='constructed:System.Nullable`1<float>':
            from scripts.game_data.memorypack.generated_nullable_value_sources import read_source
            cap=read_source(image,pins,context=context,source_target=target);layout=setters[n]['constructedValueLayout']
            need('same-constructed-source-and-owned-setter',cap['typeName']==layout['typeName']==member.declared_type and
                cap['managedBytes']==layout['managedBytes']==setters[n]['storedBytes']==8 and cap['referenceLaneOffsets']==layout['referenceLaneOffsets']==[]
                and cap['paddingByteRanges']==layout['paddingByteRanges']==[[1,3]])
            event.update(mode='typed-constructed-value',resultAbi='rax',actualSourceProved=True,managedBytes=8,concreteTypeKind=21,referenceLaneOffsets=[],paddingByteRanges=[[1,3]])
            constructed_values[str(n)]=cap
            requirements.append(dict(memberIndex=n,fieldName=member.name,typeName=member.declared_type,readMethod='ReadValue',methodDefinition=context['methodSpec'][0],
                sourceTargetRva=target-base,context=context,managedBytes=8,concreteTypeKind=21,positiveGrammarAdmitted=False))
        elif kind.startswith('managed:'):
            closed_query=context is None and member.declared_type=='Beyond.Gameplay.Core.GameplayTagQuery'
            from scripts.game_data.memorypack.generated_module_value_forwarder_sources import owns_closed_member
            closed_module=context is None and member.declared_type in('Beyond.LangKey','Beyond.Gameplay.Core.EntityPtr')and(
                module_frame is not None or owns_closed_member(wrapper.wrapped_type,member.name,member.declared_type))
            closed_body=context is None and member.declared_type=='Beyond.Gameplay.BodyTypeDef'
            closed_alpha=context is None and member.declared_type=='Beyond.Gameplay.View.Animation.AlphaBlend'
            if closed_query:
                from scripts.game_data.memorypack.generated_managed_forwarder_sources import derive as query_forwarder
                cap=query_forwarder(image,pins,source_target=target,type_name=member.declared_type)
                need('same-owned-closed-Query-forwarder',cap.get('sourceContextMode')=='owned-closed-forwarder'
                    and cap.get('actualSourceProved')is True and cap.get('resultAbi')=='hidden-local'and cap.get('managedBytes')==16
                    and cap.get('sourceTargetRva')==target-base and cap.get('typeName')==member.declared_type)
                event['sourceContextMode']='owned-closed-forwarder'
            elif closed_body:
                from scripts.game_data.memorypack.body_type_closed_value_sources import derive as closed_body_source
                cap=closed_body_source(image,pins,source_target=target)
                event.update(sourceContextMode='owned-closed-forwarder',bodyTypeClosedForwarderSource=cap)
            elif closed_alpha:
                from scripts.game_data.memorypack.alpha_blend_closed_value_sources import derive as closed_alpha_source
                cap=closed_alpha_source(image,pins,source_target=target)
                event.update(sourceContextMode='owned-closed-forwarder',alphaBlendClosedForwarderSource=cap)
            elif closed_module:
                from scripts.game_data.memorypack.generated_module_value_forwarder_sources import derive as module_forwarder
                cap=module_forwarder(image,pins,source_target=target,type_name=member.declared_type)
                event.update(sourceContextMode='owned-closed-forwarder',moduleClosedForwarderSource=cap)
            elif member.declared_type=='Beyond.Gameplay.Core.SmartTargetSelectSetting':
                from scripts.game_data.memorypack.generated_smart_target_field_sources import read_source
            elif member.declared_type=='Cinemachine.CinemachineImpulseManager+EnvelopeDefinition':
                from scripts.game_data.memorypack.generated_envelope_field_sources import read_source
            elif member.declared_type=='Beyond.Gameplay.BodyTypeDef':
                from scripts.game_data.memorypack.generated_body_type_field_sources import read_source
            elif member.declared_type=='Beyond.Gameplay.Core.EntityPtr':
                from scripts.game_data.memorypack.generated_entity_ptr_field_sources import read_source
            elif member.declared_type=='Beyond.Gameplay.Core.SkMorphPlaySetting':
                from scripts.game_data.memorypack.generated_sk_morph_field_sources import read_source
            elif member.declared_type=='Beyond.FAnimationCurve':
                from scripts.game_data.memorypack.generated_beyond_curve_field_sources import read_source
            elif member.declared_type=='Beyond.Gameplay.View.Animation.AlphaBlend':
                from scripts.game_data.memorypack.generated_alpha_blend_field_sources import read_source
            else:
                from scripts.game_data.memorypack.generated_managed_value_sources import read_source
            if not(closed_query or closed_module or closed_body or closed_alpha):cap=read_source(image,pins,context=context,source_target=target)
            layout=setters[n]['managedValueLayout']
            need('same-managed-source-and-owned-setter',cap['typeName']==layout['typeName']==member.declared_type and cap['managedBytes']==layout['managedBytes']==setters[n]['storedBytes'])
            if member.declared_type in('Beyond.Gameplay.Core.SmartTargetSelectSetting','Cinemachine.CinemachineImpulseManager+EnvelopeDefinition'):
                import json
                need('same-complete-named-managed-layout',json.loads(json.dumps(cap['proof']['childSource']['layout']))==
                    json.loads(json.dumps({k:v for k,v in layout.items()if k!='typeDefinition'})))
            elif member.declared_type=='Beyond.Gameplay.BodyTypeDef':
                import json
                need('same-complete-Body32-nominal-layout',json.loads(json.dumps(cap['proof']['nominal']))==json.loads(json.dumps(layout)))
            elif member.declared_type=='Beyond.Gameplay.Core.EntityPtr':
                import json
                need('same-complete-opaque-Entity40-layout',json.loads(json.dumps(cap['proof']['layout']))==json.loads(json.dumps(layout)))
            elif member.declared_type=='Beyond.Gameplay.Core.SkMorphPlaySetting':
                import json
                need('same-complete-SkMorph40-layout',json.loads(json.dumps(cap['proof']['layout']))==json.loads(json.dumps(layout)))
            elif member.declared_type=='Beyond.Gameplay.View.Animation.AlphaBlend':
                import json
                own=cap['proof']['childSource']['proof']['layout']
                need('same-complete-Alpha56-nominal-layout',own['typeDefinition']==layout['typeDefinition']
                    and json.loads(json.dumps(own['fields']))==json.loads(json.dumps(layout['fields']))
                    and cap['referenceLaneOffsets']==layout['referenceLaneOffsets']==[8]
                    and cap['paddingByteRanges']==layout['paddingByteRanges']==[[52,56]])
            event.update(mode='typed-managed-value',resultAbi=cap['resultAbi'],actualSourceProved=True,managedBytes=cap['managedBytes'])
            if member.declared_type=='Beyond.Gameplay.Core.EntityPtr':
                from scripts.game_data.memorypack.generated_entity_ptr_field_sources import validate_event
                event.update({k:layout[k]for k in('knownPaddingByteRanges','opaqueRuntimeStorageRanges','selectedBarrierValueOffsets',
                    'runtimeReferenceLayoutAdmitted','completeRuntimePaddingMapAdmitted')})
                validate_event(event,setters[n])
            else:event['referenceLaneOffsets']=layout['referenceLaneOffsets']
            if member.declared_type=='Beyond.Gameplay.BodyTypeDef':
                from scripts.game_data.memorypack.generated_body_type_field_sources import validate_event
                validate_event(event,setters[n])
            if member.declared_type=='Beyond.FAnimationCurve':
                from scripts.game_data.memorypack.generated_beyond_curve_field_sources import validate_event
                validate_event(event,setters[n])
            if member.declared_type=='Beyond.Gameplay.Core.SkMorphPlaySetting':
                from scripts.game_data.memorypack.generated_sk_morph_field_sources import validate_event
                validate_event(event,setters[n])
            if member.declared_type=='Beyond.Gameplay.View.Animation.AlphaBlend':
                from scripts.game_data.memorypack.generated_alpha_blend_field_sources import validate_event
                validate_event(event,setters[n])
            managed_values[str(n)]=cap
            requirements.append(dict(memberIndex=n,fieldName=member.name,typeName=member.declared_type,readMethod='ReadValue',methodDefinition=cap['readerMethodDefinition'],
                sourceTargetRva=target-base,context=context,managedBytes=cap['managedBytes'],positiveGrammarAdmitted=False))
        elif hidden:
            outer_raw=member.declared_type in('Beyond.Gameplay.TrackingBounds','Beyond.Gameplay.Core.TriggerShapeData')
            if outer_raw:
                from scripts.game_data.memorypack.generated_outer_value_field_sources import read_source
                need('exact-typed-outer-raw-source-context',context is not None)
                cap=read_source(image,pins,context=context,source_target=target,source_instruction=event['instruction'])
                event['nominalHiddenSource']=cap
            elif kind=='value24:Beyond.Gameplay.View.CameraControlStateInitialParam':
                from scripts.game_data.memorypack import skill_camera_initial_raw_sources as initial
                cap=initial.derive(image,pins,context=context,source_target=target)if context is not None else initial.derive_forwarder(image,pins,source_target=target)
                initial.verify(cap,pins);event['nominalHiddenSource']=cap
            elif kind=='value36:Beyond.Montage.AnimationClipAsyncInfo':
                from scripts.game_data.memorypack.generated_animation_clip_field_sources import read_source
                need('exact-typed-Clip36-source-context',context is not None)
                cap=read_source(image,pins,context=context,source_target=target);event['nominalHiddenSource']=cap
            elif kind=='value16:UnityEngine.Quaternion':
                from scripts.game_data.memorypack.leveldata_quaternion_value_sources import derive as quaternion_source
                if context is None:
                    from scripts.game_data.memorypack import leveldata_quaternion_forwarder_sources as closed_quaternion
                    need('exact-closed-Quaternion-member',closed_quaternion.owns_member(wrapper.wrapped_type,member.name,member.declared_type))
                    cap=closed_quaternion.derive(image,pins,source_target=target)
                else:cap=quaternion_source(image,pins,context=context,source_target=target)
            elif kind=='value16:Beyond.AABB':
                from scripts.game_data.memorypack.leveldata_aabb_raw_sources import derive as aabb_source
                from scripts.game_data.memorypack.generated_aabb_field_sources import owns_member
                need('exact-own-Node-AABB-request',context is not None and owns_member(wrapper.wrapped_type,member.name,member.declared_type))
                cap=aabb_source(image,pins,context=context,source_target=target)
            else:cap=vector3.derive(image,pins,context=context,source_target=target)if context is not None else vector3.derive_forwarder(image,pins,source_target=target)
            layout=nominal_layout(image,ctx,member.declared_type);need('typed-hidden-width',cap['wireBytes']==setters[n]['storedBytes']==layout['managedBytes'])
            if kind=='value16:UnityEngine.Quaternion'and context is None:
                event['nominalValueLayout']=dict(layout,referenceLaneOffsets=cap['referenceLaneOffsets'],paddingByteRanges=cap['paddingByteRanges'])
            if kind=='value16:Beyond.AABB':event['nominalValueLayout']=layout
            event.update(mode='typed-hidden-value',resultAbi='hidden-local',actualSourceProved=True,wireBytes=cap['wireBytes'])
            if context is None:event['sourceContextMode']='owned-closed-forwarder'
            if kind=='value36:Beyond.Montage.AnimationClipAsyncInfo':
                from scripts.game_data.memorypack.generated_animation_clip_field_sources import validate_event
                validate_event(event,setters[n])
            if outer_raw:
                from scripts.game_data.memorypack.generated_outer_value_field_sources import validate_event
                validate_event(event,setters[n])
            values[str(n)]=dict(typeName=member.declared_type,layout=layout,sourceProgram=cap['proof'].get('actualProgram',cap['proof'].get('program')),typedSource=cap,actualSourceProved=True,wireBytes=cap['wireBytes'],resultAbi='hidden-local-to-owned-field')
        elif kind=='value8:UnityEngine.Vector2':
            from scripts.game_data.memorypack.skill_vector2_source import derive as derive_vector2
            need('typed-Vector2-owned-context',context is not None)
            cap=derive_vector2(image,pins,context=context,source_target=target)
            layout=nominal_layout(image,ctx,member.declared_type)
            event.update(mode='typed-register-vector2',resultAbi='rax',actualSourceProved=True,wireBytes=8)
            bind_vector2_source(event,setters[n],cap,layout,pins,base=base)
            event['nominalValueLayout']=layout
            primitive_sources[str(n)]=cap
        elif kind=='value8:Beyond.Gameplay.Core.CharInteractPerform.HandIKParams':
            from scripts.game_data.memorypack.char_hand_ik_sources import derive as derive_hand
            cap=derive_hand(image,pins,context=context,source_target=target)
            need('same-own-HandIK-setter-layout',cap['wireBytes']==setters[n]['storedBytes']==8
                and cap['proof']['layout']==setters[n].get('nominalValueLayout'))
            primitive_sources[str(n)]=cap;event.update(wireBytes=8,actualSourceProved=True,resultAbi='rax')
        elif kind=='value8:UnityEngine.Vector2Int':
            from scripts.game_data.memorypack.leveldata_int2_read_sources import derive as derive_int2
            from scripts.game_data.memorypack.generated_int2_member_sources import bind_event
            need('typed-Int2-owned-context',context is not None)
            cap=derive_int2(image,pins,context=context,source_target=target)
            values[str(n)]=bind_event(event,setters[n],cap,base=base,pins=pins)
        elif kind=='value8:Beyond.Gameplay.AI.EnemyCheckAIMarker+EnemyCheckAIMarkerInfo':
            from scripts.game_data.memorypack.skill_ai_marker_value_sources import derive as derive_marker
            need('typed-marker-context',context is not None)
            cap=derive_marker(image,pins,context=context,source_target=target)
            need('same-own-marker-setter-layout',cap['wireBytes']==setters[n]['storedBytes']==8
                and cap['proof']['layout']==setters[n].get('nominalValueLayout'))
            primitive_sources[str(n)]=cap;event['wireBytes']=8
        elif kind=='value4:Beyond.Audio.AudioId':
            from scripts.game_data.memorypack.nominal_int32_value_sources import derive as derive_nominal4
            need('typed-nominal4-context',context is not None)
            cap=derive_nominal4(image,pins,context=context,source_target=target)
            need('same-nominal4-setter-width',cap['wireBytes']==setters[n]['storedBytes']==4)
            primitive_sources[str(n)]=cap;event['wireBytes']=4
        elif kind in('value4:UnityEngine.LayerMask','value4:Beyond.Gameplay.Core.GameplayTag'):
            cap=targets['value4'][member.declared_type]
            need('same-current-atomic4-request',context is not None and context['methodName']=='ReadUnmanaged'and context['typeKind']==17 and context['register']=='rdx'
                and cap['typeDefinition']==context['typeDefinition']and cap['readerMethodDefinition']==context['methodSpec'][0]and cap['targetRva']==target-base)
            need('same-current-atomic4-setter',cap['wireBytes']==setters[n]['storedBytes']==4 and cap['resultRegister']=='eax')
            primitive_sources[str(n)]=cap;event['wireBytes']=4
        elif kind in primitive_modes:
            mode=primitive_modes[kind];key=(mode,target)
            if key not in targets['_primitiveCache']:targets['_primitiveCache'][key]=primitives.derive(image,target,mode,offsets)
            primitive_sources[str(n)]=targets['_primitiveCache'][key];event['wireBytes']=primitive_sources[str(n)]['wireBytes']
            if context is not None:need('current-typed-primitive-method',context['methodName']=='ReadUnmanaged')
            elif ctx.is_enum(member.declared_type):raise ValueError(LABEL+'.enum-owned-context-missing:'+member.declared_type)
        elif kind=='byte-payload':need('current-pool-source',target==targets['string']);event['wireBytes']=4
        elif primitive_array:
            from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
            from scripts.game_data.memorypack import module_unmanaged_array_sources as primitive_arrays
            usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL+'.primitiveArray')
            cap=primitive_arrays.derive(image,pins,typed_request=usage,call_target=target,
                source_instruction=event['instruction'],element_type=context['fullTypeName'])
            binding=primitive_arrays.bind_member(cap,context,event,setters[n],pins,owner=wrapper.wrapped_type)
            array_sources[str(n)]=cap
            event.update(mode='typed-unmanaged-primitive-array',actualSourceProved=True)
            requirements.append(dict(memberIndex=n,fieldName=member.name,typeName=member.declared_type,
                elementType=binding['elementType'],readMethod=binding['readMethod'],
                methodDefinition=binding['readerMethodDefinition'],sourceTargetRva=target-base,
                context=context,countLimit=binding['countLimit'],positiveGrammarAdmitted=False))
        elif(reference_array and context['fullTypeName']=='Beyond.Gameplay.EncounterData+OperaSegment'
                and wrapper.wrapped_type in('Beyond.Gameplay.EncounterData+IntroPart','Beyond.Gameplay.EncounterData+TailPart')
                and member.name=='operaSegments'):
            from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
            from scripts.game_data.memorypack.levelscript_opera_array_sources import derive as opera_array_source,bind_call
            need('finite-Opera-value17-array',context['typeKind']==17
                and bytes.fromhex(context['argumentRawHex'])[10:12]==bytes.fromhex('1180')
                and kind=='reference:Beyond.Gameplay.EncounterData+OperaSegment[]')
            usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL+'.operaArray')
            cap=opera_array_source(image,pins,typed_request=usage,call_target=target,count_limit=4096)
            binding=bind_call(context,target,cap,pins,base=base)
            array_sources[str(n)]=cap;event.update(mode='typed-value-array',actualSourceProved=True)
            requirements.append(dict(memberIndex=n,fieldName=member.name,typeName=member.declared_type,
                elementType=context['fullTypeName'],readMethod='ReadArray',methodDefinition=binding['readerMethodDefinition'],
                sourceTargetRva=target-base,context=context,positiveGrammarAdmitted=False))
        elif reference_array and member.declared_type=='string[]':
            from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
            from scripts.game_data.memorypack.leveldata_string_array_sources import derive as string_array_source
            need('explicit-STRING14-array-element',context is not None and context['typeKind']==14 and
                bytes.fromhex(context['argumentRawHex'])[10:12]==bytes((14,0))and kind=='reference:string[]')
            usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL+'.stringArray')
            need('same-actual-STRING-array-usage',usage['methodSpec']==context['methodSpec']and usage['instructionHex']==context['instructionHex'])
            cap=string_array_source(image,pins,typed_request=usage,call_target=target,count_limit=4096);owned=cap.get('capability',{})
            need('independent-current-STRING-array-source',cap.get('nativeInputs')==pins and cap.get('status')=='validated-conditional-pooled-string-array'
                and owned.get('typeName')=='string[]'and owned.get('elementType')=='string'and owned.get('elementRawKind')==14
                and owned.get('arrayReaderTargetRva')==target-base and owned.get('arrayReaderMethodDefinition')==context['methodSpec'][0]
                and owned.get('actualCallbackEqualsPooledStringRequired')is True and owned.get('liveFormatterSelectionObserved')is False)
            array_sources[str(n)]=cap;event['mode']='typed-pooled-string-array'
            requirements.append(dict(memberIndex=n,fieldName=member.name,typeName='string[]',elementType='string',readMethod='ReadArray',
                methodDefinition=context['methodSpec'][0],sourceTargetRva=target-base,context=context,positiveGrammarAdmitted=False))
        elif reference_array and context['fullTypeName']=='Beyond.Gameplay.View.Animation.StatePerformConfig':
            from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
            from scripts.game_data.memorypack.animation_state_array_sources import derive as state_array_source,bind_call
            need('explicit-StatePerformConfig-value-array',context['typeKind']==17
                and bytes.fromhex(context['argumentRawHex'])[10:12]==bytes.fromhex('1180')
                and kind=='reference:Beyond.Gameplay.View.Animation.StatePerformConfig[]')
            usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL+'.stateArray')
            cap=state_array_source(image,pins,typed_request=usage,call_target=target,count_limit=4096)
            binding=bind_call(context,target,cap,pins,base=base)
            array_sources[str(n)]=cap;event.update(mode='typed-value-array',actualSourceProved=True)
            requirements.append(dict(memberIndex=n,fieldName=member.name,typeName=member.declared_type,
                elementType=context['fullTypeName'],readMethod='ReadArray',methodDefinition=binding['readerMethodDefinition'],
                sourceTargetRva=target-base,context=context,positiveGrammarAdmitted=False))
        elif reference_array and context['fullTypeName']=='Beyond.Gameplay.View.Animation.AnimationConfigExtraData+ShaderPropertyEntry':
            from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
            from scripts.game_data.memorypack.animation_shader_array_sources import derive as shader_array_source,bind_call
            need('explicit-ShaderPropertyEntry-value-array',context['typeKind']==17
                and bytes.fromhex(context['argumentRawHex'])[10:12]==bytes.fromhex('1180')
                and kind=='reference:'+context['fullTypeName']+'[]')
            usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL+'.shaderArray')
            cap=shader_array_source(image,pins,typed_request=usage,call_target=target,count_limit=4096)
            binding=bind_call(context,target,cap,pins,base=base)
            array_sources[str(n)]=cap;event.update(mode='typed-value-array',actualSourceProved=True)
            requirements.append(dict(memberIndex=n,fieldName=member.name,typeName=member.declared_type,
                elementType=context['fullTypeName'],readMethod='ReadArray',methodDefinition=binding['readerMethodDefinition'],
                sourceTargetRva=target-base,context=context,positiveGrammarAdmitted=False))
        elif reference_array and context['fullTypeName']in(
            'Beyond.Gameplay.View.Animation.AnimationConfigExtraData+AnimationEventRendererVisibilityEntry',
            'Beyond.Gameplay.View.Animation.AnimationConfigExtraData+AnimationEventPlayEffectEntry'):
            from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
            from scripts.game_data.memorypack.animation_extra_value_array_sources import derive as extra_array_source,bind_call
            need('explicit-Extra-value-array',context['typeKind']==17
                and bytes.fromhex(context['argumentRawHex'])[10:12]==bytes.fromhex('1180')
                and kind=='reference:'+context['fullTypeName']+'[]')
            usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL+'.extraValueArray')
            cap=extra_array_source(image,pins,typed_request=usage,call_target=target,element_type=context['fullTypeName'],count_limit=4096)
            binding=bind_call(context,target,cap,pins,base=base)
            array_sources[str(n)]=cap;event.update(mode='typed-value-array',actualSourceProved=True)
            requirements.append(dict(memberIndex=n,fieldName=member.name,typeName=member.declared_type,
                elementType=context['fullTypeName'],readMethod='ReadArray',methodDefinition=binding['readerMethodDefinition'],
                sourceTargetRva=target-base,context=context,positiveGrammarAdmitted=False))
        elif(reference_array and wrapper.wrapped_type=='Beyond.Gameplay.Actions.ListMakeVector3'
                and member.name=='_list'and member.declared_type=='Beyond.Gameplay.Actions.Param`1<UnityEngine.Vector3>[]'):
            cap=vector_param_array_source(image,pins,wrapper,member,event,context,target)
            array_sources[str(n)]=cap;event.update(mode='typed-Param-reference-array',actualSourceProved=True)
            requirements.append(dict(memberIndex=n,fieldName=member.name,typeName=member.declared_type,
                elementType=context['fullTypeName'],readMethod='ReadArray',methodDefinition=cap['arrayReaderMethodDefinition'],
                sourceTargetRva=target-base,context=context,countLimit=4096,positiveGrammarAdmitted=False))
        elif reference_array:
            from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
            from scripts.game_data.memorypack.skill_reference_array_sources import derive as array_source
            need('explicit-reference-array-element',context['typeKind']==18 and not bytes.fromhex(context['argumentRawHex'])[11]&128 and kind=='reference:'+member.declared_type,
                dict(memberIndex=n,fieldName=member.name,declaredType=member.declared_type,context=context,sourceTargetRva=target-base))
            usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL+'.array')
            need('same-actual-array-method-usage',usage['methodSpec']==context['methodSpec']and usage['instructionHex']==context['instructionHex'])
            cap=array_source(image,pins,typed_request=usage,call_target=target,element_type=context['fullTypeName'],count_limit=10000)
            need('same-current-actual-array-source',cap['nativeInputs']==pins and cap['closedArrayType']==member.declared_type and cap['arrayReaderTargetRva']==target-base and cap['arrayReaderMethodDefinition']==context['methodSpec'][0])
            array_sources[str(n)]=cap;event['mode']='typed-reference-array'
            requirements.append(dict(memberIndex=n,fieldName=member.name,typeName=member.declared_type,elementType=context['fullTypeName'],readMethod='ReadArray',methodDefinition=context['methodSpec'][0],sourceTargetRva=target-base,context=context,positiveGrammarAdmitted=False))
        elif kind.startswith('reference:'):
            need('current-ordinary-reference-context',context is not None and context['typeKind']in(18,21)and not bytes.fromhex(context['argumentRawHex'])[11]&128 and context['methodName']in('ReadValue','ReadPackable'))
            need('current-actual-reference-source',target==base+targets[context['methodName']]['targetRva'])
            requirements.append(dict(memberIndex=n,fieldName=member.name,typeName=member.declared_type,readMethod=context['methodName'],methodDefinition=context['methodSpec'][0],sourceTargetRva=target-base,context=context,positiveGrammarAdmitted=False))
        else:raise ValueError(LABEL+'.unsupported-direct-kind:'+kind)
        events.append(event)
    need('all-current-contexts-bound',used=={c['instructionRva']for c in contexts})
    ending=members.control_transfer(path[-1]);setter_tail=ending['kind']=='jump'and ending['target']==last_setter_target
    terminal=base+barrier if ending['kind']=='jump'and not setter_tail else None
    bound_accesses=cached.bind_programs(image,pins,source_target=base+method[3],accesses=accesses,path=path,events=events,setters=setters)
    options=dict(cached_accesses=bound_accesses)if bound_accesses else{}
    if module_frame is not None:options['source_frame_alias']=module_frame
    if 'value44:Beyond.Gameplay.Core.TriggerShapeData'in claim['anonymousReadOrder']:
        address=header_proof.get('headerAddress',{})
        need('same-owned-Trigger44-RBP-frame',address.get('baseAliasProfile')=='entry-RAX-RBP-95-header.v1'
            and header_proof.get('nullFrameBytes')==168 and address.get('displacement')==103
            and address.get('entryRspOffset')==8 and address.get('rspDisplacement')==176)
        options['source_frame_alias']=dict(profile='mission-trigger44-RAX-RBP-frame.v1',baseRegister='rbp',entryRspOffset=-95,
            currentRspBytes=168,rspRelativeBaseOffset=73,baseAliasInstruction=address['baseAliasInstruction'],
            entryRspAliasInstruction=address['entryRspAliasInstruction'])
    if static_references:
        if all(e['declaredType']==gait.TYPE for e in events if e.get('mode')=='typed-static-out-reference'):
            options['static_out_parent']=gait.parent_setup(image,rows,path,events,header_proof,base=base)
        else:
            from scripts.game_data.memorypack import animation_extra_parent_sources as extra_parent
            options['static_out_parent']=extra_parent.parent_setup(image,rows,path,events,header_proof,base=base,parent_type=wrapper.wrapped_type)
            if options['static_out_parent']['sourceFrameAlias']is not None:
                options['source_frame_alias']=options['static_out_parent']['sourceFrameAlias']
    if setter_tail:options['terminal_setter']=last_setter_target
    program=program_prover(rows,path,events,setters,contexts,reader=reader,output=output,base=base,barrier=base+barrier,inline_offsets=offsets,terminal_target=terminal,
        disabled_collector=base+targets['_disabledCollectorFlagRva'],**options)
    for event in events:
        n=event['memberIndex']
        if str(n)in values and event.get('mode')in('buffered-inline-value','buffered-called-advance-color16','buffered-called-advance-value12','buffered-called-advance-int-vector12','buffered-called-advance-initial24','buffered-called-advance-posrot24'):
            source=values[str(n)]['sourceProgram'];values[str(n)]['sourceProgram']=dict(source,sourceBytes=source['selectedBytes'],storedBytes=event['wireBytes'],
                fullValueBitsStoredUnchanged=True,fieldStoreProgram=[s for s in program['fieldStores']if s['memberIndex']==n])
    result=dict(schema='endfield.generated-action-source-scope.v2',nativeInputs=dict(pins),wrapperName=wrapper.name,wrappedType=wrapper.wrapped_type,
        memberCount=len(events),claim=claim,method=method,family=family,codeWindows=windows,headerProof=header_proof,enumBackings=enums,
        contexts=contexts,skippedRuntimeCells=skipped,events=events,childRequirements=requirements,primitiveSources=primitive_sources,
        inlinePrimitiveSources=inline_sources,arraySources=array_sources,valueTypeSources=values,setterTransfers=[],richProgram=program,richSetters=setters,
        selectedProgram=[ec.site(r,base)for r in path],selectedConditions=[dict(instruction=ec.site(c['instruction'],base),condition=c['condition'],taken=c['taken'])for c in choices],
        sourceScopeAdmitted=True,wholeWrapperAdmitted=False,positiveGrammarAdmitted=False,
        evidenceBoundary='Every literal current inline macro and direct typed source is joined to an independently current named field/setter, exact captured bit slices, all four Reader updates and complete selected source-to-field program. Lifecycle, full frame and child grammar remain independent.')
    if ending['kind']=='jump':
        if setter_tail:result['namedSetterTail']=dict(memberIndex=len(events)-1,method=setters[-1]['method'],instruction=ec.site(path[-1],base),
            completeSourceAndArgumentTransferProved=True,fullRestoredCallerFrameRequired=True)
        else:result['referenceBarrierTargetRva']=barrier
    if managed_values:result['managedValueSources']=managed_values
    if constructed_values:result['constructedValueSources']=constructed_values
    if static_references:result['staticReferenceSources']=static_references
    return result

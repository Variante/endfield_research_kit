"""Compile finite generated record members from source-proved callers.

This pure compiler grants no native admission. A domain owner must freshly
prove each complete concrete source/lifecycle on its selected image, name its
finite child semantics and compose enclosing union/adapter/parent evidence.
Managed type names and widths never supply an unsupported child grammar.
"""

LABEL='generatedRecordComponents'
ATOMS={
    'byte':('bool-byte','bool',1,'al-normalized'),
    'raw-byte':('byte','raw-byte',1,'al'),
    'scalar32':('scalar32','int32',4,'eax'),
    'scalar64':('scalar64-bits','int64',8,'rax'),
    'raw4':('float32-bits','float32',4,'xmm0-low32'),
    'float64':('float64-bits','float64',8,'xmm0-low64'),
}
VALUE4={'UnityEngine.LayerMask':'layer-mask-raw4','Beyond.Gameplay.Core.GameplayTag':'gameplay-tag32'}
INLINE_VALUES={
    'value12:UnityEngine.Vector3':('UnityEngine.Vector3','unity-vector3-raw12',12,('x','y','z')),
    'value16:UnityEngine.Quaternion':('UnityEngine.Quaternion','unity-quaternion-raw16',16,('x','y','z','w')),
}


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def _closed_hidden_vector3_context(read,typed,pins):
    """The actual outer helper owns its internal typed R8 request and E8."""
    from scripts.game_data.memorypack.generated_vector3_source import forwarder_program
    proof=typed.get('proof',{});forward=proof.get('forwarderProgram',{});nested=proof.get('nestedSource',{})
    request=proof.get('typedRequest',{});selected=forward.get('selectedBytes',[])
    need('closed-hidden-context-owner',read.get('sourceContextMode')=='owned-closed-forwarder'
        and read.get('context')is None and typed.get('contextMode')=='owned-closed-forwarder'
        and typed.get('contextRegister')is None and bool(selected)
        and nested.get('status')=='validated'and nested.get('nativeInputs')==pins
        and nested.get('typeName')=='UnityEngine.Vector3'and nested.get('readMethod')=='ReadUnmanaged'
        and nested.get('contextRegister')=='r8'and nested.get('resultAbi')=='hidden-local'
        and nested.get('wireBytes')==nested.get('managedBytes')==12
        and nested.get('actualSourceProved')is True and nested.get('pointerAliasClaimed')is False
        and nested.get('readerMethodDefinition')==typed.get('readerMethodDefinition')
        and nested.get('proof',{}).get('typedRequest')==request
        and nested.get('proof',{}).get('actualProgram')==proof.get('actualProgram')
        and type(request.get('instructionRva'))is int and type(forward.get('contextInstructionVa'))is int)
    base=forward['contextInstructionVa']-request['instructionRva']
    need('closed-hidden-owned-source-entries',type(base)is int and base>=0
        and type(nested.get('targetRva'))is int and nested['targetRva']>0
        and selected[0][0]==base+typed['targetRva']
        and forward.get('nestedTargetVa')==base+nested['targetRva']
        and nested['proof']['actualProgram']['selectedBytes'][0][0]==forward['nestedTargetVa']
        and proof.get('actualFamily',{}).get('selectedPrimaryRva')==typed['targetRva'])
    actual=forwarder_program([(at,bytes.fromhex(raw))for at,raw in selected],base+typed['targetRva'])
    actual['selectedBytes']=[[at,raw]for at,raw in actual['selectedBytes']]
    need('complete-closed-hidden-forwarder-program',actual==forward
        and all(forward.get(k)is True for k in('sameIncomingReaderRdx','sameIncomingOutputRcx',
            'sameOutputReturnedInRax','fullFrameAndNonvolatilesRestored')))
    at=forward['contextInstructionVa'];chunks=dict(selected)
    need('actual-internal-typed-context-bytes',chunks.get(at)=='4c8b05'
        and (chunks[at]+chunks.get(at+3,'')).upper()==request.get('instructionHex'))
    need('same-internal-reader-method',typed['readerMethodDefinition']==request.get('methodSpec',[None])[0])


def _typed_hidden_vector3(source,scope,read,pins):
    """Actual ReadUnmanaged hidden12 and complete source-local/field transfer."""
    index=read['memberIndex'];typename='UnityEngine.Vector3'
    proof=scope.get('valueTypeSources',{}).get(str(index),{});typed=proof.get('typedSource',{})
    program=proof.get('sourceProgram',{});layout=proof.get('layout',{});context=read.get('context',{})
    request=typed.get('proof',{}).get('typedRequest',{})
    need('exact-typed-hidden-Vector3:'+str(index),scope.get('nativeInputs')==pins
        and read.get('declaredType')==typename and read.get('resultAbi')=='hidden-local'and read.get('actualSourceProved')is True
        and type(read.get('wireBytes'))is int and read['wireBytes']==12
        and proof.get('typeName')==typename and proof.get('actualSourceProved')is True
        and proof.get('wireBytes')==12 and proof.get('resultAbi')=='hidden-local-to-owned-field'
        and layout.get('typeName')==typename and layout.get('managedBytes')==12 and layout.get('wireReadAdmitted')is False
        and layout.get('fields')==[[axis,'float',16+4*i]for i,axis in enumerate(('x','y','z'))]
        and typed.get('status')=='validated'and typed.get('nativeInputs')==pins and typed.get('typeName')==typename
        and typed.get('readMethod')=='ReadUnmanaged'and typed.get('wireBytes')==typed.get('managedBytes')==12
        and typed.get('resultAbi')=='hidden-local'and typed.get('actualSourceProved')is True
        and typed.get('pointerAliasClaimed')is False and typed.get('targetRva')==read['sourceTargetRva']
        and type(typed.get('readerMethodDefinition'))is int and typed['readerMethodDefinition']>=0
        and(request.get('typeName'),request.get('methodName'),request.get('classArguments'),request.get('methodArguments'))==
            ('MemoryPack.MemoryPackReader','ReadUnmanaged',[],[typename])
        and program==typed.get('proof',{}).get('actualProgram')and program.get('wireBytes')==program.get('managedOutputBytes')==12
        and(program.get('hiddenOutputRegister'),program.get('readerRegister'),program.get('methodInfoRegister'))==('rcx','rdx','r8')
        and program.get('capturedSourceSlices')==program.get('storedOutputSlices')==[[0,8],[8,4]]
        and all(program.get(k)is True for k in('sameOutputReturnedInRax','allFourReaderUpdatesProved',
            'fullFrameAndNonvolatilesRestored','normalReturn'))and bool(program.get('selectedBytes')))
    if read.get('sourceContextMode')=='owned-closed-forwarder':
        _closed_hidden_vector3_context(read,typed,pins)
    else:
        need('actual-caller-hidden-context:'+str(index),read.get('sourceContextMode')is None
            and typed.get('contextMode')is None and typed.get('contextRegister')=='r8'
            and typed['readerMethodDefinition']==context.get('methodSpec',[None])[0]
            and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadUnmanaged'
            and context.get('fullTypeName')==typename and type(context.get('typeKind'))is int and context['typeKind']==17
            and request.get('instructionRva')==context.get('instructionRva')and request.get('methodSpec')==context.get('methodSpec'))
    at,encoded=read['instruction'];raw=bytes.fromhex(encoded)
    need('actual-typed-hidden-source-call:'+str(index),type(at)is int and len(raw)==5 and raw[0]==232
        and at+5+int.from_bytes(raw[1:],'little',signed=True)==typed['targetRva'])
    rich=scope.get('richProgram',{});locals_=[r for r in rich.get('hiddenSourceLocals',[])if r.get('memberIndex')==index]
    sources=[r for r in rich.get('sources',[])if r.get('memberIndex')==index]
    stores=[r for r in rich.get('fieldStores',[])if r.get('memberIndex')==index]
    setters=source.get('setters',[]);setter=setters[index]if index<len(setters)else{}
    need('literal-hidden-field-slices:'+str(index),all(type(r.get('sourceOffset'))is int
        and type(r.get('storedBytes'))is int for r in stores))
    slices=sorted((r.get('sourceOffset'),r.get('storedBytes'))for r in stores)
    named_call=False
    if slices==[(0,12)]and setter.get('profile')in('direct-base-holder-setter','cached-getter-setter'):
        store=stores[0];site,encoded=store['instruction'];raw=bytes.fromhex(encoded)
        named_call=(type(site)is int and len(raw)==5 and raw[0]==232
            and site+5+int.from_bytes(raw[1:],'little',signed=True)==setter.get('method',[None]*4)[3]
            and (setter.get('profile')=='cached-getter-setter'
                or setter.get('program',{}).get('sourceSlices')==[[0,8],[8,4]])
            and setter.get('program',{}).get('storedBytes')==12)
    need('complete-hidden-local-transfer:'+str(index),rich.get('completeSelectedNormalProgram')is True
        and rich.get('selectedProgram')==scope.get('selectedProgram')and len(locals_)==len(sources)==1
        and locals_[0].get('bytes')==12 and type(locals_[0].get('displacement'))is int
        and 32<=locals_[0]['displacement']<256 and locals_[0].get('sourceInstruction')==read['instruction']
        and sources[0].get('instruction')==read['instruction']and sources[0].get('resultAbi')=='hidden-local'
        and all(type(r.get('sourceOffset'))is int and type(r.get('storedBytes'))is int for r in stores)
        and (slices==[(0,8),(8,4)]or named_call)
        and all(any(type(offset)is int and type(width)is int and width==12
            for offset,width in p['frame'].get('hiddenSourceLocalHomes',[]))for p in source['programs']if not p['wrapperNull']))
    if setter.get('profile')=='cached-getter-setter':
        from scripts.game_data.memorypack.generated_hidden_vector_components import cached_setter
        cached_setter(source,scope,read,setter,pins)
    else:
        need('own-hidden-vector-setter:'+str(index),setter.get('profile')=='direct-base-holder-setter'
            and setter.get('storedBytes')==12 and setter.get('member',{}).get('declaredType')==typename
            and setter.get('incomingValueStoredUnchanged')is True
            and setter.get('program',{}).get('completeSourceBitsStoredUnchanged')is True
            and setter.get('program',{}).get('normalFrameAndReturn')is True)
    return 'unity-vector3-raw12'


def typed_hidden_vector3(source,scope,read,pins):
    """Keep every hidden-value refusal attributable before another full run."""
    try:return _typed_hidden_vector3(source,scope,read,pins)
    except ValueError as error:
        from scripts.game_data.memorypack.corpus_gate import CensusGateError
        index=read.get('memberIndex');setters=source.get('setters',[])
        setter=setters[index]if type(index)is int and 0<=index<len(setters)else{}
        diagnostic=CensusGateError('generatedRecordComponents.hidden-vector-field',
            source='scripts/game_data/memorypack/generated_record_components.py',
            expected='exact source-owned hidden Vector3 context, complete12 field/local/frame transfer and own selected setter profile',
            actual=dict(reason=str(error)[:1400],setterProfile=setter.get('profile'),
                storedBytes=setter.get('storedBytes'),setterMethod=setter.get('method')))
        diagnostic.diagnostic.update(validator=LABEL,failedGate=str(error).split(':',1)[0],
            wrapperName=source.get('wrapperName'),typeName=source.get('wrappedType'),
            fieldName=read.get('fieldName'),memberIndex=index,nativeInputs=pins,
            sourceWindows=source.get('codeWindows',[])[:8],setterWindows=setter.get('codeWindows',[])[:8])
        import json
        diagnostic.args=(json.dumps(diagnostic.diagnostic,sort_keys=True),)
        raise diagnostic from error


def compile_member_program(source,pins,*,wrapper_name,type_name,value4,value8=None,references=None,reference_children=None,typed_requests=None,
        collections=None,collection_children=None,collection_binder=None,reference_binder=None,
        arrays=None,array_children=None,array_binder=None,
        typed_values=None,value_children=None,value_binder=None,
        static_references=None,static_reference_children=None):
    """Pure shape/compiler check; only derive freshly authenticates the source.

    Optional typed_values maps an exact nominal to (capability, wire operation,
    required operation capability). Per-member value_children and a callable
    value_binder own the independent managed-value source/field/frame/wire join.
    With no explicit hook, managed values remain pending as before.
    """
    need('nominal-source-identity',source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and(source.get('wrapperName'),source.get('wrappedType'))==
        (wrapper_name,type_name)and source.get('completeSelectedCallerAdmitted')is True
        and source.get('childGrammarAdmitted')is False and source.get('wholeOwnerAdmitted')is False)
    life=source['lifecycle'];reads=source['orderedSourceReads']
    if source.get('memberCount')==0 and type(source['memberCount'])is int:
        need('complete-zero-reader-and-source',source['method']==life['readerMethod']and reads==[]and source['childRequirements']==[]and source['setters']==[])
        count=0;scope=None
    else:
        scope=source['sourceScope'];count=scope['memberCount']
        need('own-reader-and-source-order',source['method']==life['readerMethod']==scope['method']
            and source['wrapperName']==scope['wrapperName']and source['wrappedType']==scope['wrappedType']
            and scope.get('sourceScopeAdmitted')is True and source['childRequirements']==scope['childRequirements']
            and reads==scope['events']and type(count)is int and 0<count<250 and len(reads)==count
            and [r['memberIndex']for r in reads]==list(range(count))
            and all(type(r['memberIndex'])is int for r in reads))
    paths=source['programs']
    need('four-complete-caller-paths',len(paths)==4 and all(type(p.get('existing'))is bool and
        type(p.get('wrapperNull'))is bool and p['frame'].get('entryRspRestored')is True and
        p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and {(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)})
    references={}if references is None else references
    reference_children={}if reference_children is None else reference_children
    typed_requests={}if typed_requests is None else typed_requests
    value8={}if value8 is None else value8
    collections={}if collections is None else collections
    collection_children={}if collection_children is None else collection_children
    arrays={}if arrays is None else arrays
    array_children={}if array_children is None else array_children
    typed_values={}if typed_values is None else typed_values
    value_children={}if value_children is None else value_children
    static_references={}if static_references is None else static_references
    static_reference_children={}if static_reference_children is None else static_reference_children
    need('callable-collection-binder',collection_binder is None or callable(collection_binder))
    need('callable-reference-binder',reference_binder is None or callable(reference_binder))
    need('callable-array-binder',array_binder is None or callable(array_binder))
    need('callable-value-binder',value_binder is None or callable(value_binder))
    program=[];pending=[];requirements=set();bindings=[]
    for read in reads:
        index=read['memberIndex'];kind=read['kind'];child=None
        if kind=='value24:Beyond.PosRot':
            from scripts.game_data.memorypack.generated_posrot_components import compile_member
            wire=compile_member(source,scope,read,pins)
        elif read.get('mode')=='buffered-called-advance-initial24':
            from scripts.game_data.memorypack.generated_initial24_components import compile_member
            wire=compile_member(source,scope,read,pins)
        elif kind=='value36:Beyond.Montage.AnimationClipAsyncInfo':
            from scripts.game_data.memorypack.skill_animation_clip_components import compile_member
            wire=compile_member(source,scope,read,pins)
        elif(kind=='value44:Beyond.Gameplay.Core.TriggerShapeData'
                and source.get('wrappedType')=='Beyond.Gameplay.MissionAreaData'
                and read.get('fieldName')=='shape'):
            from scripts.game_data.memorypack.leveldata_trigger_shape_raw_components import compile_member
            wire=compile_member(source,scope,read,pins)
        elif(kind=='value36:Beyond.Gameplay.TrackingBounds'
                and source.get('wrappedType')=='Beyond.Gameplay.TrackingRouteInfo'
                and read.get('fieldName')=='boundingBox'):
            from scripts.game_data.memorypack.leveldata_tracking_raw_components import compile_member
            wire=compile_member(source,scope,read,pins)
        elif kind=='constructed:System.Nullable`1<float>':
            from scripts.game_data.memorypack.generated_nullable_value_components import compile_member
            wire=compile_member(source,scope,read,pins)
        elif kind=='value8:UnityEngine.Vector2Int':
            from scripts.game_data.memorypack.generated_int2_components import compile_member
            wire=compile_member(source,scope,read,pins)
        elif read.get('mode')=='buffered-called-advance-int-vector12':
            from scripts.game_data.memorypack.generated_integer_vector_components import compile_member
            wire=compile_member(source,scope,read,pins)
        elif kind=='value8:Beyond.Gameplay.AI.EnemyCheckAIMarker+EnemyCheckAIMarkerInfo':
            from scripts.game_data.memorypack.generated_ai_marker_components import compile_member
            wire=compile_member(source,scope,read,pins)
        elif kind=='value8:Beyond.Gameplay.Core.CharInteractPerform.HandIKParams':
            from scripts.game_data.memorypack.char_hand_ik_components import compile_member
            wire=compile_member(source,scope,read,pins)
        elif read.get('mode')=='buffered-called-advance-color16':
            from scripts.game_data.memorypack.generated_color_components import compile_member
            wire=compile_member(source,scope,read,pins)
        elif read.get('mode')in('buffered-called-advance-value12','buffered-called-advance-scalar')and scope.get('headerProof',{}).get('readerRegister')=='rdi':
            from scripts.game_data.memorypack.generated_rdi_advance_components import compile_member
            wire=compile_member(source,scope,read,pins)
        elif read.get('mode')=='buffered-called-advance-scalar':
            from scripts.game_data.memorypack.generated_called_advance_components import compile_member
            wire=compile_member(source,scope,read,pins)
        elif read.get('mode')=='buffered-inline-scalar'or read.get('mode')=='buffered-inline-value'and'inlineSourceProgram'in read:
            from scripts.game_data.memorypack.generated_inline_record_components import compile_inline_member
            wire=compile_inline_member(source,scope,read,pins)
        elif kind in ATOMS:
            wire,primitive,width,result=ATOMS[kind];proof=scope['primitiveSources'].get(str(index),{})
            need('member-primitive-source:'+str(index),read.get('wireBytes')==width
                and proof.get('kind')==primitive and proof.get('targetRva')==read['sourceTargetRva']
                and proof.get('wireBytes')==width and proof.get('resultRegister')==result
                and proof.get('completeBufferedProgram')is True and proof.get('entryRspRestored')is True
                and proof.get('nonvolatilesRestored')is True
                and proof.get('boolNormalized')is(kind=='byte'))
        elif kind=='byte-payload':
            need('pooled-index-width',type(read.get('wireBytes'))is int and read['wireBytes']==4)
            wire='byte-payload';child='byte-payload';requirements.add(child)
        elif read.get('mode')=='typed-static-out-reference'and read['declaredType']in static_references and index in static_reference_children:
            capability,wire,child=static_references[read['declaredType']]
            from scripts.game_data.memorypack import animation_extra_dictionary_components as extra
            if read['declaredType']in extra.CAPABILITIES:
                from scripts.game_data.memorypack.animation_extra_dictionary_bindings import bind
                selected=extra.CAPABILITIES[read['declaredType']]
                need('separate-own-animation-extra-static-operation:'+str(index),(capability,wire,child)==(selected,extra.WIRE,selected))
                binding=bind(source,scope,read,pins,typed_requests.get(index,{}),static_reference_children[index],capability,value_binder=value_binder)
            else:
                from scripts.game_data.memorypack import skill_gait_dictionary_sources as gait
                from scripts.game_data.memorypack.skill_gait_dictionary_components import WIRE
                from scripts.game_data.memorypack.skill_gait_dictionary_bindings import bind
                need('separate-own-static-reference-operation:'+str(index),read['declaredType']==gait.TYPE
                    and(capability,wire,child)==(gait.CAPABILITY,WIRE,gait.CAPABILITY))
                binding=bind(source,scope,read,pins,typed_requests.get(index,{}),static_reference_children[index],capability)
            bindings.append(binding);requirements.add(child)
        elif kind.startswith('managed:')and read['declaredType']in typed_values and index in value_children:
            from scripts.game_data.memorypack.generated_managed_value_components import bind_member
            capability,wire,child=typed_values[read['declaredType']]
            need('literal-managed-value-operation:'+str(index),all(isinstance(v,str)and bool(v)for v in(capability,wire,child)))
            binding=bind_member(source,scope,read,pins,typed_requests.get(index,{}),value_children[index],capability,binder=value_binder)
            bindings.append(binding);requirements.add(child)
        elif kind=='value12:UnityEngine.Vector3'and read.get('mode')=='typed-hidden-value':
            wire=typed_hidden_vector3(source,scope,read,pins)
        elif kind=='value16:UnityEngine.Quaternion'and read.get('mode')=='typed-hidden-value':
            from scripts.game_data.memorypack.generated_hidden_quaternion_components import compile_member
            wire=compile_member(source,scope,read,pins)
        elif kind=='value16:Beyond.AABB'and read.get('mode')=='typed-hidden-value':
            from scripts.game_data.memorypack.generated_aabb_components import compile_member
            wire=compile_member(source,scope,read,pins)
        elif kind=='value24:Beyond.Gameplay.View.CameraControlStateInitialParam'and read.get('mode')=='typed-hidden-value':
            from scripts.game_data.memorypack.generated_camera_initial_components import compile_member
            wire=compile_member(source,scope,read,pins)
        elif kind in INLINE_VALUES:
            typename,wire,width,axes=INLINE_VALUES[kind];proof=scope.get('valueTypeSources',{}).get(str(index),{})
            layout=proof.get('layout',{});program_proof=proof.get('sourceProgram',{})
            setters=source.get('setters',[]);setter=setters[index]if index<len(setters)else{}
            need('exact-current-inline-value:'+str(index),scope.get('nativeInputs')==pins
                and read.get('declaredType')==typename and read.get('mode')=='buffered-inline-value'
                and type(read.get('wireBytes'))is int and read['wireBytes']==width
                and proof.get('typeName')==typename and proof.get('actualSourceProved')is True
                and proof.get('resultAbi')=='inline-bits-to-owned-field'and proof.get('wireBytes')==width
                and layout.get('typeName')==typename and layout.get('managedBytes')==width
                and layout.get('wireReadAdmitted')is False
                and layout.get('fields')==[[axis,'float',16+4*i]for i,axis in enumerate(axes)]
                and program_proof.get('wireBytes')==width and program_proof.get('storedBytes')==width
                and program_proof.get('fullValueBitsStoredUnchanged')is True
                and bool(program_proof.get('selectedBytes'))and bool(program_proof.get('sourceBytes'))
                and setter.get('storedBytes')==width and setter.get('member',{}).get('declaredType')==typename
                and setter.get('program',{}).get('fullValueStoredUnchanged')is True
                and setter.get('program',{}).get('normalFrameAndReturn')is True)
        elif kind=='value4:Beyond.Audio.AudioId':
            from scripts.game_data.memorypack.generated_nominal_value_components import audio_id
            wire=audio_id(source,scope,read,pins)
        elif kind.startswith('value4:'):
            typename=kind[len('value4:'):];proof=value4.get(typename,{})
            need('named-four-byte-source:'+str(index),typename in VALUE4 and proof.get('status')=='validated'
                and proof.get('nativeInputs')==pins and proof.get('typeName')==typename
                and proof.get('wireBytes')==4 and proof.get('resultRegister')=='eax'
                and proof.get('targetRva')==read['sourceTargetRva']
                and proof.get('readerMethodDefinition')==read['context']['methodSpec'][0])
            wire=VALUE4[typename]
        elif kind=='value8:UnityEngine.Vector2'and 'UnityEngine.Vector2'in value8:
            typename='UnityEngine.Vector2';selected=value8[typename]
            proof=selected if selected.get('status')=='validated'else selected.get(str(index),{})
            context=read.get('context',{})
            need('exact-named-eight-byte-source:'+str(index),proof==scope['primitiveSources'].get(str(index))
                and read.get('declaredType')==typename and proof.get('status')=='validated'and proof.get('nativeInputs')==pins
                and proof.get('typeName')==typename and proof.get('readMethod')=='ReadUnmanaged'
                and type(proof.get('wireBytes'))is int and proof['wireBytes']==8 and proof.get('resultRegister')=='rax'
                and proof.get('completeBufferedProgram')is True and proof.get('entryRspRestored')is True
                and proof.get('nonvolatilesRestored')is True and proof.get('targetRva')==read['sourceTargetRva']
                and type(proof.get('targetRva'))is int and proof['targetRva']>0
                and type(proof.get('readerMethodDefinition'))is int and proof['readerMethodDefinition']>=0
                and proof.get('readerMethodDefinition')==context.get('methodSpec',[None])[0]
                and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadUnmanaged'
                and context.get('fullTypeName')==typename and type(context.get('typeKind'))is int and context['typeKind']==17)
            wire='vector2-raw8'
        elif kind=='reference:string[]'and read['declaredType']=='string[]'and read.get('mode')=='typed-pooled-string-array'and'string[]'in arrays and index in array_children:
            from scripts.game_data.memorypack.leveldata_string_array_sources import CAP,bind_array
            capability,wire,child=arrays['string[]'];context=read.get('context',{});usage=typed_requests.get(index,{})
            raw_type=bytes.fromhex(context.get('argumentRawHex',''));native_array=scope.get('arraySources',{}).get(str(index),{})
            component=array_children[index]
            need('separate-owned-STRING14-array-source:'+str(index),(capability,wire,child)==(CAP,'pooled-string-array',CAP)
                and(array_binder is None or callable(array_binder))and len(raw_type)==16 and raw_type[10:12]==bytes((14,0))
                and(context.get('methodOwner'),context.get('methodName'),context.get('fullTypeName'),context.get('typeKind'),context.get('register'))==
                    ('MemoryPack.MemoryPackReader','ReadArray','string',14,'rdx')
                and(context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))==
                    (usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec'))
                and native_array.get('proof',{}).get('typedRequest')==usage)
            rich=scope.get('richProgram',{});flows=[x for x in rich.get('sources',[])if x.get('memberIndex')==index]
            stores=[x for x in rich.get('fieldStores',[])if x.get('memberIndex')==index]
            need('whole-STRING14-array-reference-field:'+str(index),rich.get('completeSelectedNormalProgram')is True
                and rich.get('selectedProgram')==scope.get('selectedProgram')
                and flows==[dict(memberIndex=index,instruction=read['instruction'],resultAbi='rax')]
                and len(stores)==1 and(stores[0].get('sourceOffset'),stores[0].get('storedBytes'))==(0,8)
                and stores[0].get('instruction')in scope['selectedProgram']
                and source['setters'][index].get('targetField')==source['wrappedType']+'::'+read['fieldName']
                and source['setters'][index].get('incomingValueStoredUnchanged')is True and source['setters'][index].get('storedBytes')==8)
            binding=bind_array(pins,dict(fieldName=read['fieldName'],typeName='string[]',typedRequest=usage,
                sourceTargetRva=read['sourceTargetRva'],arraySource=native_array),component,capability)
            need('same-owned-STRING14-array-binding:'+str(index),(binding.get('fieldName'),binding.get('typeName'),binding.get('capability'),
                binding.get('readerMethodDefinition'),binding.get('sourceTargetRva'))==
                    (read['fieldName'],'string[]',CAP,usage['methodSpec'][0],read['sourceTargetRva']))
            bindings.append(binding);requirements.add(child)
        elif(read.get('mode')=='typed-value-array'
                and source.get('wrappedType')in('Beyond.Gameplay.EncounterData+IntroPart','Beyond.Gameplay.EncounterData+TailPart')
                and read.get('fieldName')=='operaSegments'
                and read.get('declaredType')=='Beyond.Gameplay.EncounterData+OperaSegment[]'
                and read['declaredType']in arrays and index in array_children):
            from scripts.game_data.memorypack import levelscript_opera_array_components as opera
            capability,wire,child=arrays[read['declaredType']]
            need('finite-owned-Module-Opera-value-array:'+str(index),
                (capability,wire,child)==(opera.CAPABILITY,opera.WIRE,opera.CAPABILITY))
            binding=opera.bind_member(source,scope,read,pins,typed_requests.get(index,{}),array_children[index],capability)
            bindings.append(binding);requirements.add(child)
        elif read.get('mode')=='typed-value-array'and read['declaredType']in arrays and index in array_children:
            from scripts.game_data.memorypack import animation_extra_array_components as owned_arrays
            typename=read['declaredType'];capability,wire,child=arrays[typename]
            context=read.get('context',{});usage=typed_requests.get(index,{})
            need('finite-owned-Extra-value-array:'+str(index),typename in tuple(t+'[]'for t in owned_arrays.TYPES)
                and(capability,wire,child)==(owned_arrays.key(typename[:-2]),owned_arrays.WIRE,owned_arrays.key(typename[:-2])))
            binding=owned_arrays.bind_member(source,scope,read,pins,usage,array_children[index],capability)
            bindings.append(binding);requirements.add(child)
        elif(read.get('mode')=='typed-unmanaged-primitive-array'
                and source.get('wrappedType')=='Beyond.Gameplay.RunePuzzleData'
                and read['declaredType']in('int[]','bool[]')and read['declaredType']in arrays and index in array_children):
            from scripts.game_data.memorypack import levelscript_rune_array_components as rune_array
            capability,wire,child=arrays[read['declaredType']];selected=rune_array.key(read['declaredType'][:-2])
            need('finite-owned-Rune-primitive-array-operation:'+str(index),(capability,wire,child)==(selected,rune_array.WIRE,selected))
            binding=rune_array.bind_member(source,scope,read,pins,typed_requests.get(index,{}),array_children[index],capability)
            bindings.append(binding);requirements.add(child)
        elif read.get('mode')=='typed-unmanaged-primitive-array'and read['declaredType']=='int[]'and'int[]'in arrays and index in array_children:
            from scripts.game_data.memorypack import animation_extra_int_array_components as int_array
            capability,wire,child=arrays['int[]']
            need('finite-owned-Extra-Int32-array-operation:'+str(index),
                (capability,wire,child)==(int_array.CAPABILITY,int_array.WIRE,int_array.CAPABILITY))
            binding=int_array.bind_member(source,scope,read,pins,typed_requests.get(index,{}),array_children[index],capability)
            bindings.append(binding);requirements.add(child)
        elif(kind=='reference:Beyond.Gameplay.Actions.Param`1<UnityEngine.Vector3>[]'
                and read.get('mode')=='typed-Param-reference-array'and read['declaredType']in arrays and index in array_children):
            from scripts.game_data.memorypack import levelscript_vector_param_array_sources as vector_params
            capability,wire,child=arrays[read['declaredType']]
            need('finite-owned-vector-Param-array-operation:'+str(index),
                (capability,wire,child)==(vector_params.CAPABILITY,vector_params.WIRE,vector_params.CAPABILITY))
            binding=vector_params.bind_member(source,scope,read,pins,typed_requests.get(index,{}),array_children[index],capability)
            bindings.append(binding);requirements.add(child)
        elif kind.startswith('reference:')and read['declaredType']in arrays and index in array_children:
            typename=read['declaredType'];capability,wire,child=arrays[typename]
            context=read.get('context',{});usage=typed_requests.get(index,{})
            component=array_children[index];cap=component.get('capabilities',{}).get(capability,{})
            raw_type=bytes.fromhex(context.get('argumentRawHex',''))
            native_array=scope.get('arraySources',{}).get(str(index),{})
            need('same-owned-reference-array-usage:'+str(index),read.get('mode')=='typed-reference-array'
                and kind=='reference:'+typename and typename==cap.get('elementType','')+'[]'
                and component.get('nativeInputs')==pins and callable(array_binder)
                and context.get('methodSpec')==usage.get('methodSpec')
                and type(context.get('instructionRva'))is int and context['instructionRva']==usage.get('instructionRva')
                and context.get('instructionHex')==usage.get('instructionHex')
                and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadArray'
                and context.get('fullTypeName')==cap.get('elementType')and context.get('typeKind')==18
                and len(raw_type)==16 and raw_type[10:12]==bytes((18,0))
                and native_array.get('nativeInputs')==pins and native_array.get('typedRequest')==usage
                and native_array.get('closedArrayType')==typename
                and native_array.get('arrayReaderMethodDefinition')==usage['methodSpec'][0]
                and native_array.get('arrayReaderTargetRva')==read.get('sourceTargetRva'))
            binding=array_binder(pins,dict(fieldName=read['fieldName'],typeName=typename,typedRequest=usage,
                sourceTargetRva=read['sourceTargetRva'],arraySource=native_array),component,capability)
            need('same-array-binding-result:'+str(index),isinstance(binding,dict)
                and(binding.get('fieldName'),binding.get('typeName'),binding.get('capability'))==(read['fieldName'],typename,capability)
                and type(binding.get('readerMethodDefinition'))is int and binding['readerMethodDefinition']==usage['methodSpec'][0]
                and type(binding.get('sourceTargetRva'))is int and binding['sourceTargetRva']==read['sourceTargetRva'])
            bindings.append(binding);requirements.add(child)
        elif kind.startswith('reference:')and read['declaredType']in collections and index in collection_children:
            from scripts.game_data.memorypack.skill_root_child_bindings import bind_read_packable_list
            typename=read['declaredType'];capability,wire,child=collections[typename]
            context=read.get('context',{});usage=typed_requests.get(index,{})
            need('same-owned-collection-usage:'+str(index),context.get('methodSpec')==usage.get('methodSpec')
                and type(context.get('instructionRva'))is int and context['instructionRva']==usage.get('instructionRva')
                and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadPackable'
                and context.get('fullTypeName')==typename and type(context.get('typeKind'))is int and context['typeKind']==21
                and kind=='reference:'+typename)
            binder=bind_read_packable_list if collection_binder is None else collection_binder
            binding=binder(pins,dict(fieldName=read['fieldName'],typeName=typename,typedRequest=usage,
                sourceTargetRva=read['sourceTargetRva']),collection_children[index],capability)
            need('same-collection-binding-result:'+str(index),isinstance(binding,dict)
                and(binding.get('fieldName'),binding.get('typeName'),binding.get('capability'))==(read['fieldName'],typename,capability))
            bindings.append(binding);requirements.add(child)
        elif(kind=='reference:System.Collections.Generic.Dictionary`2<string,Beyond.Gameplay.Core.GameplayTag>'
                and source.get('wrappedType')=='Beyond.Gameplay.Core.CharInteractPerform.CharNpcMontageActionData'
                and index==21 and read.get('fieldName')=='template2Tag'
                and read['declaredType']in references and read['declaredType']in reference_children):
            from scripts.game_data.memorypack import char_tag_dictionary_components as tags
            typename=read['declaredType'];capability,wire,child=references[typename]
            component=reference_children[typename];context=read.get('context',{});usage=typed_requests.get(index,{})
            need('finite-own-NPC-Tag-dictionary:'+str(index),component.get('schema')==tags.SCHEMA
                and component.get('nativeInputs')==pins and (capability,wire,child)==(tags.CAPABILITY,tags.WIRE,tags.CAPABILITY)
                and callable(reference_binder))
            need('exact-NPC-Tag-dictionary-ReadPackable:'+str(index),type(context.get('typeKind'))is int
                and context['typeKind']==21 and(context.get('methodOwner'),context.get('methodName'),context.get('fullTypeName'),context.get('register'))==
                    ('MemoryPack.MemoryPackReader','ReadPackable',typename,'rdx')
                and(context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))==
                    (usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec')))
            tags.validate_component(component,pins)
            binding=reference_binder(pins,dict(fieldName=read['fieldName'],typeName=typename,typedRequest=usage,
                sourceContext=context,sourceInstruction=read['instruction'],sourceTargetRva=read['sourceTargetRva']),component,capability)
            need('same-NPC-Tag-dictionary-binding:'+str(index),isinstance(binding,dict)
                and(binding.get('fieldName'),binding.get('typeName'),binding.get('capability'))==(read['fieldName'],typename,capability)
                and type(binding.get('readerMethodDefinition'))is int and binding['readerMethodDefinition']==usage['methodSpec'][0]
                and type(binding.get('sourceTargetRva'))is int and binding['sourceTargetRva']==read['sourceTargetRva'])
            bindings.append(binding);requirements.add(child)
        elif(kind.startswith('reference:')and read['declaredType']in references
                and read['declaredType']in reference_children
                and reference_children[read['declaredType']].get('schema')=='endfield.levelscript-action-output-components.v1'):
            from scripts.game_data.memorypack.levelscript_action_output_components import CAP_PREFIX as OUTPUT_PREFIX,WIRE as OUTPUT_WIRE
            from scripts.game_data.memorypack.levelscript_action_output_bindings import _capability
            typename=read['declaredType'];capability,wire,child=references[typename]
            component=reference_children[typename];cap,_=_capability(component,capability)
            context=read.get('context',{});usage=typed_requests.get(index,{})
            raw_type=bytes.fromhex(context.get('argumentRawHex',''))
            need('finite-owned-Output21-reference-child:'+str(index),component.get('nativeInputs')==pins
                and cap.get('typeName')==typename and(capability,wire,child)==(OUTPUT_PREFIX+typename,OUTPUT_WIRE,OUTPUT_PREFIX+typename)
                and cap.get('typeArgumentSerialized')is False and callable(reference_binder))
            need('same-owned-constructed-Output-usage:'+str(index),kind=='reference:'+typename
                and type(context.get('typeKind'))is int and context['typeKind']==21
                and len(raw_type)==16 and raw_type[10:12]==bytes((21,0))
                and(context.get('methodOwner'),context.get('methodName'),context.get('fullTypeName'),context.get('register'))==
                    ('MemoryPack.MemoryPackReader','ReadValue',typename,'rdx')
                and type(context.get('instructionRva'))is int
                and(context['instructionRva'],context.get('instructionHex'),context.get('methodSpec'))==
                    (usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec')))
            binding=reference_binder(pins,dict(fieldName=read['fieldName'],typeName=typename,typedRequest=usage,
                sourceContext=context,sourceInstruction=read['instruction'],sourceTargetRva=read['sourceTargetRva']),component,capability)
            need('same-Output-reference-binding-result:'+str(index),isinstance(binding,dict)
                and(binding.get('fieldName'),binding.get('typeName'),binding.get('capability'))==(read['fieldName'],typename,capability)
                and type(binding.get('readerMethodDefinition'))is int and binding['readerMethodDefinition']==usage['methodSpec'][0]
                and type(binding.get('sourceTargetRva'))is int and binding['sourceTargetRva']==read['sourceTargetRva'])
            bindings.append(binding);requirements.add(child)
        elif(kind.startswith('reference:')and read['declaredType']in references
                and read['declaredType']in reference_children and read.get('context',{}).get('typeKind')==21):
            from scripts.game_data.memorypack.levelscript_condition_param_sources import SCHEMA,CAP_PREFIX
            from scripts.game_data.memorypack.levelscript_condition_enum_param_components import SCHEMA as ENUM_SCHEMA
            from scripts.game_data.memorypack.levelscript_condition_storage_param_components import SCHEMA as STORAGE_SCHEMA
            from scripts.game_data.memorypack.levelscript_int2_param_sources import SCHEMA as INT2_SCHEMA
            from scripts.game_data.memorypack.levelscript_condition_list_param_components import SCHEMA as LIST_SCHEMA
            from scripts.game_data.memorypack.levelscript_script_task_param_sources import SCHEMA as TASK_SCHEMA
            from scripts.game_data.memorypack.levelscript_action_dedicated_param_components import SCHEMA as DEDICATED_SCHEMA
            typename=read['declaredType'];capability,wire,child=references[typename]
            component=reference_children[typename];cap=component.get('capabilities',{}).get(capability,{})
            context=read['context'];usage=typed_requests.get(index,{})
            raw_type=bytes.fromhex(context.get('argumentRawHex',''))
            need('finite-owned-Param-reference-child:'+str(index),component.get('schema')in(SCHEMA,ENUM_SCHEMA,STORAGE_SCHEMA,INT2_SCHEMA,LIST_SCHEMA,TASK_SCHEMA,DEDICATED_SCHEMA)
                and component.get('nativeInputs')==pins and cap.get('typeName')==typename
                and(capability,wire,child)==(CAP_PREFIX+typename,'condition-param',CAP_PREFIX+typename)
                and cap.get('sourceReferenceKind')==21 and cap.get('closedCarrierProved')is True
                and callable(reference_binder))
            need('same-owned-constructed-Param-usage:'+str(index),kind=='reference:'+typename
                and type(context.get('typeKind'))is int and len(raw_type)==16 and raw_type[10:12]==bytes((21,0))
                and(context.get('methodOwner'),context.get('methodName'),context.get('fullTypeName'),context.get('register'))==
                    ('MemoryPack.MemoryPackReader','ReadValue',typename,'rdx')
                and type(context.get('instructionRva'))is int
                and(context['instructionRva'],context.get('instructionHex'),context.get('methodSpec'))==
                    (usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec')))
            binding=reference_binder(pins,dict(fieldName=read['fieldName'],typeName=typename,typedRequest=usage,
                sourceContext=context,sourceInstruction=read['instruction'],sourceTargetRva=read['sourceTargetRva']),component,capability)
            need('same-Param-reference-binding-result:'+str(index),isinstance(binding,dict)
                and(binding.get('fieldName'),binding.get('typeName'),binding.get('capability'))==(read['fieldName'],typename,capability)
                and type(binding.get('readerMethodDefinition'))is int and binding['readerMethodDefinition']==usage['methodSpec'][0]
                and type(binding.get('sourceTargetRva'))is int and binding['sourceTargetRva']==read['sourceTargetRva'])
            bindings.append(binding);requirements.add(child)
        elif kind.startswith('reference:')and read['declaredType']in references and read['declaredType']in reference_children:
            from scripts.game_data.memorypack.skill_root_child_bindings import bind_read_value
            typename=read['declaredType'];capability,wire,child=references[typename]
            need('same-nominal-reference-source:'+str(index),kind=='reference:'+typename)
            context=read.get('context',{});usage=typed_requests.get(index,{})
            need('same-owned-reference-usage:'+str(index),context.get('methodSpec')==usage.get('methodSpec')
                and type(context.get('instructionRva'))is int and context['instructionRva']==usage.get('instructionRva')
                and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadValue'
                and context.get('fullTypeName')==typename and context.get('typeKind')==18
                and kind=='reference:'+typename)
            need('same-reference-child-inputs:'+str(index),reference_children[typename].get('nativeInputs')==pins)
            need('same-reference-child-nominal:'+str(index),reference_children[typename].get('capabilities',{}).get(capability,{}).get('typeName')==typename)
            binder=bind_read_value if reference_binder is None else reference_binder
            binding=binder(pins,dict(fieldName=read['fieldName'],typeName=typename,typedRequest=usage,
                sourceTargetRva=read['sourceTargetRva']),reference_children[typename],capability)
            need('same-reference-binding-result:'+str(index),isinstance(binding,dict)
                and(binding.get('fieldName'),binding.get('typeName'),binding.get('capability'))==(read['fieldName'],typename,capability)
                and type(binding.get('readerMethodDefinition'))is int and binding['readerMethodDefinition']==usage['methodSpec'][0]
                and type(binding.get('sourceTargetRva'))is int and binding['sourceTargetRva']==read['sourceTargetRva'])
            bindings.append(binding);requirements.add(child)
        else:
            pending.append(dict(memberIndex=index,fieldName=read['fieldName'],typeName=read['declaredType'],
                kind=kind,reason='independent child grammar and actual typed parent join required'))
            continue
        program.append(dict(memberIndex=index,fieldName=read['fieldName'],kind=wire,childCapability=child))
    if pending:return None,pending
    return dict(memberCount=count,reads=program,requiredCapabilities=sorted(requirements),childBindings=bindings),[]

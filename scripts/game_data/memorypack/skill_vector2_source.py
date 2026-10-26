"""Exact nominal Vector2 ReadUnmanaged source returning eight raw bits bytes.

The actual current caller contributes its typed MethodInfo load and E8 target.
Its closed Vector2 context, x/y Single fields, boxed/native sizes and exact
generic registration are independently selected. The actual caller clone and
registered canonical source are distinct explicitly proved programs: both load
two Single bit lanes and UNPCKLPS/MOVQ returns the complete pair in RAX; the
actual source owns four inline cursor updates while canonical uses its actual
Advance(8) callee. That callee's complete counter/return program is independently
proved; it is not assigned the managed Advance method's entry by pointer alias.
Neither pointer alias nor layout/managed size admits wire8.
The enclosing caller must separately prove RAX to
its owned setter and complete frame. Ready coherent selected contexts, enough
contiguous disjoint input and normal invocation are conditions; refill, runtime
meaning, ordinary formatter selection and owner/EOF remain unresolved.
"""
from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPE='UnityEngine.Vector2'


def vector2_program(regions,entry,offsets,*,profile,advance=None):
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    need('Vector2-explicit-source-profile',True,profile in('inline-counters','canonical-advance'))
    g=BytesPath(regions,entry);cur,rem,adv,used=(bytes((offsets[n],)).hex()
        for n in('currentPtr','bufferLength','advancedCount','consumed'))
    if profile=='inline-counters':
        need('Vector2-inline-has-no-Advance',None,advance)
        g.take('48895c2408','57','4883ec40','8379'+rem+'08','488bd9','0f29742430','0f297c2420')
        g.branch('0f8c',False)
        g.take('488b43'+cur,'f30f1030','f30f107804','8b7b'+rem,'83c7f8');g.branch('0f88',False)
        g.take('488343'+cur+'08','8343'+adv+'08','8343'+used+'08','897b'+rem,
            '488b5c2450','0f28c6','0f28742430','0f14c7','0f287c2420','66480f7ec0','4883c440','5f','c3')
    else:
        need('Vector2-canonical-actual-Advance',True,type(advance)is int and advance>0)
        g.take('4053','4883ec40','8379'+rem+'08','488bd9','0f29742430','0f297c2420');g.branch('7d',True,1)
        g.take('488b43'+cur,'ba08000000','488bcb','f30f1030','f30f107804');g.call(advance)
        g.take('0f14f7','0f287c2420','66480f7ef0','0f28742430','4883c440','5b','c3')
    return dict(profile=profile,selectedBytes=g.seen,wireBytes=8,resultRegister='rax',
        sourceLaneOffsets=[0,4],resultLaneBits=[[0,31],[32,63]],rawSingleBitsUnchanged=True,
        advanceTarget=advance,advanceArgument=8 if advance is not None else None,
        fourCursorUpdatesProved=advance is None,normalReturn=True,entryRspRestored=True,
        restoredXmmNonvolatiles=['xmm6','xmm7'],restoredIntegerNonvolatiles=['rbx','rdi']if advance is None else['rbx'])


def bind(context,source_target,proof,*,base):
    need('Vector2-actual-nominal-context',True,context.get('methodOwner')=='MemoryPack.MemoryPackReader'
        and context.get('methodName')=='ReadUnmanaged'and context.get('fullTypeName')==TYPE
        and type(context.get('typeKind'))is int and context['typeKind']==17 and context.get('register')=='rdx')
    need('Vector2-complete-source',True,proof.get('typeName')==TYPE and proof.get('status')=='validated'
        and proof.get('readMethod')=='ReadUnmanaged'and proof.get('resultRegister')=='rax'
        and type(proof.get('wireBytes'))is int and proof['wireBytes']==8)
    need('Vector2-literal-native-identities',True,all(type(proof.get(k))is int and proof[k]>0
        for k in('readerMethodDefinition','targetRva'))and type(source_target)is int)
    need('Vector2-actual-formal-and-target',(context['methodSpec'][0],source_target-base),
        (proof['readerMethodDefinition'],proof['targetRva']))
    return dict(typeName=TYPE,readerMethodDefinition=proof['readerMethodDefinition'],targetRva=proof['targetRva'],wireBytes=8,resultRegister='rax')


def derive(image,pins,*,context,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import scalar_param_native as scalar,pointer_param as pointer
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    from scripts.game_data.memorypack.vector_layout import vector_context,vector_recorder
    _publication_gate(image,pins);base=image.pe.image_base
    usage=derive_typed_usage_context(image,context['instructionRva'],label='skillVector2')
    need('Vector2-same-actual-usage-spec',context['methodSpec'],usage['methodSpec'])
    need('Vector2-same-actual-usage-bytes',context['instructionHex'],usage['instructionHex'])
    selected=NativeReferenceContext(image);definition=selected.index.types[TYPE].index
    need('Vector2-current-nominal-definition',definition,context['typeDefinition'])
    argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
    need('Vector2-current-argument-bytes',argument.raw_type_record_hex.upper(),context['argumentRawHex'].upper())
    entry=vector_context(image,usage,2,label='skillVector2')
    actual=pointer.owned(image,source_target);canonical=pointer.owned(image,entry['pointer'])
    offsets=scalar.reader_offsets(image,'skillVector2')
    advance=BytesPath(canonical['regions'],canonical['pointer']+59).relative('e8')
    canonical_program=vector2_program(canonical['regions'],canonical['pointer'],offsets,profile='canonical-advance',advance=advance)
    actual_program=(canonical_program if source_target==entry['pointer']else
        vector2_program(actual['regions'],source_target,offsets,profile='inline-counters'))
    methods=[m for m in image.metadata.methods_for(selected.index.types['MemoryPack.MemoryPackReader'])
        if image.metadata.string(m.name_index)=='Advance'and m.parameter_count==1 and not m.flags&16]
    need('Vector2-one-named-Advance-ABI',1,len(methods));method=methods[0]
    parameters=list(image.metadata.parameters_for(method))
    need('Vector2-Advance-value-receiver',True,selected.is_value_type('MemoryPack.MemoryPackReader'))
    need('Vector2-Advance-formal-ABI',('void',['int'],-1),(selected.type_name(method.return_type),
        [selected.type_name(p.type_index)for p in parameters],method.generic_container_index))
    scalar.ordinary(image,selected.type_pointer(method.return_type),1,'skillVector2.Advance.return')
    scalar.ordinary(image,selected.type_pointer(parameters[0].type_index),8,'skillVector2.Advance.count')
    advanced=vector_recorder(image)(advance-base,fragments=True)
    scalar.advance_source(image,advanced,offsets,'skillVector2.Advance8')
    proof=dict(status='validated',nativeInputs=dict(pins),typeName=TYPE,readMethod='ReadUnmanaged',
        typeDefinition=context['typeDefinition'],contextTypeKind=17,readerMethodDefinition=usage['methodSpec'][0],
        targetRva=source_target-base,wireBytes=8,resultRegister='rax',wholeGrammarAdmitted=True,
        completeBufferedProgram=True,entryRspRestored=True,nonvolatilesRestored=True,
        proof=dict(typedRequest=usage,registration=entry,actualFamily=image.unwind_index.family(source_target-base),actualWindows=actual['windows'],
            canonicalFamily=image.unwind_index.family(entry['pointer']-base),canonicalWindows=canonical['windows'],
            actualProgram=actual_program,canonicalProgram=canonical_program,advance=advanced,readerOffsets=offsets,
            namedAdvanceMethod=[method.index,image.type_name(method.declaring_type),'Advance',image.method_pointer_va(method)-base],
            actualAdvanceTargetRva=advance-base,actualAdvanceManagedEntryIdentityClaimed=False,
            actualEqualsRegisteredPointer=source_target==entry['pointer'],pointerAliasClaimed=False,
            canonicalAndActualProgramsIndependentlyProved=True,
            layout=dict(fields=[dict(name=n,typeName='float',boxedOffset=o)
                for n,o in(('x',16),('y',20))],nativeBytes=8,boxedBytes=24)),
        evidenceBoundary=dict(exact='Closed nominal Vector2 ReadUnmanaged registration, distinct complete actual/canonical two-Single/UNPCKLPS/MOVQ RAX programs, inline counters and actual Advance(8) source, independent x/y float layout; no pointer or managed-entry alias.',
            conditional=__doc__,structuralOnly='Stored Vector2 bits.',unresolved=['enclosing setter/frame','refill','runtime meaning','owner/EOF']))
    proof['parentBinding']=bind(context,source_target,proof,base=base)
    _publication_gate(image,pins);return proof
